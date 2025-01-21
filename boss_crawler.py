import asyncio
import re
import time
from typing import List
from playwright.async_api import async_playwright, Response
from bs4 import BeautifulSoup


class BossCrawler:
    def __init__(self, city: int, position: int, all_page: bool):
        self.city: int = city
        self.position: int = position
        self.url: str = f"https://www.zhipin.com/web/geek/job?query=&city={self.city}&position={self.position}&page="
        self.jsonobj = {}
        self.jobs = []
        self.max_page = 10
        self.page_number = 1
        self.browser = None
        self.page = None
        self.all_page = all_page

    async def browser_init(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        )

        # Create context
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
            has_touch=True,
            locale='zh-CN'
        )
        await context.grant_permissions(['geolocation'])

        # Create new page and inject JavaScript
        self.page = await context.new_page()
        with open('stealth.min.js', 'r') as f:
            js = f.read()
        await self.page.add_init_script(js)

    async def handle_response(self, response):
        if "/wapi/zpgeek/search/joblist.json" in response.url:
            # print(f"Intercepted response from: {response.url}")
            try:
                self.jsonobj = await response.json()
                self.jobs.extend(self.jsonobj['zpData']['jobList'])
                resCount = self.jsonobj['zpData']['resCount']

                max_page = resCount // 30
                self.max_page = min(10, max_page)
                print(f"当前岗位最大岗位数: resCount: {resCount}, 当前分类最大页数 max_page: {self.max_page}")
            except Exception as e:
                pass

    async def get_jobs(self):
        await self.browser_init()
        if self.all_page is False:
            self.max_page = 3
            url_list = [self.url + str(page) for page in range(1, self.max_page + 1)]
        else:
            url_list = [self.url + str(page) for page in range(1, self.max_page + 1)]

        for url in url_list:
            print(url)
            self.page_number = self.page_number + 1
            try:
                if self.page_number > self.max_page:
                    break

                self.page.on("response", self.handle_response)
                await self.page.goto(url)
                await self.page.wait_for_selector('.job-list-box', timeout=10000)
                if self.jobs:
                    # print(self.jobs[-1])
                    pass
            except Exception as e:
                print(f"元素未出现或等待超时: {e}")

        await self.browser.close()
        return self.jobs


class JobCrawler:
    def __init__(self):
        self.browser = None
        self.page = None

    async def browser_init(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        )

        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
            has_touch=True,
            locale='zh-CN'
        )
        await context.grant_permissions(['geolocation'])

        self.page = await context.new_page()
        with open('stealth.min.js', 'r') as f:
            js = f.read()
        await self.page.add_init_script(js)

        # 定义请求处理函数

    async def handle_route(self, route):
        # 获取请求URL
        request = route.request
        url = request.url

        # 检查是否为图片请求
        image_patterns = [r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$', r'\.webp$']
        is_image = any(re.search(pattern, url, re.IGNORECASE) for pattern in image_patterns)

        if is_image:
            # print(f"已拦截普通图片: {url}")
            await route.abort()
        else:
            # 非图片请求直接放行
            await route.continue_()

    async def get_job_detail(self, job_id: str):
        if not self.page:
            await self.browser_init()

        url: str = f"https://www.zhipin.com/job_detail/{job_id}.html"
        try:
            await self.page.route("**/*", self.handle_route)
            await self.page.goto(url)
            html = await self.page.content()
            if "当前 IP 地址可能存在异常访问行为，完成验证后即可正常使用." not in html:
                await self.page.wait_for_selector('.job-sec-text', timeout=15000)
            else:
                print("当前 IP 地址可能存在异常访问行为，完成验证后即可正常使用.")
        except Exception as e:
            print(f"元素未出现或等待超时: {e}")
            return '', '', '', '', ''

        soup = BeautifulSoup(html, 'html.parser')
        job_description_detail = soup.find('div', class_='job-sec-text').get_text(separator='\n') if soup.find('div',
                                                                                                               class_='job-sec-text') else ''
        location_address = soup.find('div', class_='location-address').get_text() if soup.find('div',
                                                                                               class_='location-address') else ''
        company_size = soup.find('i', class_='icon-scale').parent.get_text() if soup.find('i',
                                                                                          class_='icon-scale') else ''
        company_stage = soup.find('i', class_='icon-stage').parent.get_text() if soup.find('i',
                                                                                           class_='icon-stage') else ''
        company_industry = soup.select_one('a[ka="job-detail-brandindustry"]').get_text() if soup.select_one(
            'a[ka="job-detail-brandindustry"]') else ''
        # soup.find('a', attrs={'ka': 'job-detail-brandindustry'})
        return job_description_detail, location_address, company_size, company_stage, company_industry

    async def get_company_detail(self, company_id: str):
        if not self.page:
            await self.browser_init()

        url: str = f"https://www.zhipin.com/gongsi/{company_id}.html"
        try:
            await self.page.goto(url)
            await self.page.wait_for_selector('.business-detail', timeout=30000)
        except:
            await self.page.screenshot(path=f"./logs/error_{company_id}_{time.time()}.png", full_page=True)
            await self.page.reload()

        # html = await self.page.content()
        # soup = BeautifulSoup(html, 'html.parser')
        # job_detail = soup.find('div', class_='job-sec-text').get_text(separator='\n') if soup.find('div',
        #                                                                                            class_='job-sec-text') else ''
        # location_address = soup.find('div', class_='location-address').get_text() if soup.find('div',
        #                                                                                        class_='location-address') else ''
        try:
            business_detail_user = await self.page.locator('li.business-detail-user').text_content()
            business_detail_time = await self.page.locator('li.business-detail-time').text_content()
            business_detail_type = await self.page.locator('li.business-detail-type').text_content()
            business_detail_status = await self.page.locator('li.business-detail-status').text_content()
            business_detail_money = await self.page.locator('li.business-detail-money').text_content()
            business_detail_location = await self.page.locator('li.business-detail-location').text_content()
        except:
            business_detail_user = ''
            business_detail_time = ''
            business_detail_type = ''
            business_detail_status = ''
            business_detail_money = ''
            business_detail_location = ''

        company_jobs = await self.page.locator('a[ka="company-jobs"]').nth(0).text_content()
        try:
            work_time = await self.page.locator('//div[@class="job-sec work-time"]/p').nth(0).text_content()
        except:
            work_time = ''
        try:
            job_time = await self.page.locator('//div[@class="job-sec work-time"]/p').nth(1).text_content()
        except:
            job_time = ''

        work_tag = await self.page.locator('li.work-tag-item').all_text_contents()

        update_time = await self.page.locator('div.update-time').text_content()

        return {
            'business_detail_user': business_detail_user.replace('法定代表人：', ''),
            'business_detail_time': business_detail_time.replace('成立时间：', ''),
            'business_detail_type': business_detail_type.replace('企业类型：', ''),
            'business_detail_status': business_detail_status.replace('经营状态：', ''),
            'business_detail_money': business_detail_money.replace('注册资本：', ''),
            'business_detail_location': business_detail_location.replace('注册地址：', ''),
            'company_jobs': company_jobs.split('(')[1].replace(')', ''),
            'work_time': work_time,
            'job_time': job_time,
            'work_tag': ','.join(work_tag),
            'job_update_time': update_time.replace('职位列表第一个职位更新时间:', '')
        }

    async def close(self):
        if self.browser:
            await self.browser.close()


async def main():
    # Test BossCrawler
    boss = BossCrawler(city=101010100, position=100101)
    jobs = await boss.get_jobs()
    #
    # # Print job details
    # for job in jobs:
    #     print(job['jobName'], job['salaryDesc'], job['encryptJobId'])

    # Test JobCrawler
    job_crawler = JobCrawler()

    # Test a few job details
    job_ids = [
        "6c9265a50eea11bd1HR729y9ElpX",
        "a1a202b852a7d2061H1939q_FVtR",
        "313f372eb7c845041H1y29q0FVpX"
    ]

    company_ids = [
        "e9a19e67cc19cc111nd-2N64FVo~",
        "a67b361452e384e71XV82N4~",
        "6b46ec00bb8068171X162tm9Fg~~",
        "f9a5b0b441e187631nJ_2dy8FVs~",
        "fa2f92669c66eee31Hc~",
        "ab0ee64deb5cf6fe1HB609u5FFc~"
    ]

    for job_id in job_ids:
        job_detail = await job_crawler.get_job_detail(job_id=job_id)
        print(job_detail)

    # for company_id in company_ids:
    #     company_detail = await job_crawler.get_company_detail(company_id=company_id)
    #     print(company_detail)

    await job_crawler.close()


if __name__ == '__main__':
    asyncio.run(main())
