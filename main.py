import asyncio

from boss_crawler import BossCrawler, JobCrawler
from utils import MySQLUtils, AsyncMySQLUtils, extract_salary_info
import json

sample_job = {
    "job_id": "",
    "job_title": "",
    "job_category_1": "",
    "job_category_2": "",
    "job_category_3": "",
    "company_id": "",
    "company_name": "",
    "job_description": "",
    "job_requirements": "",
    "job_skills": "",
    "job_description_detail": "",
    "salary_min": 0,
    "salary_max": 0,
    "salary_count": 0,
    "work_experience": "",
    "education_level": "",
    "city_name": "",
    "area_detail": "",
    "business_circle": "",
    "work_address": "",
    "job_benefits": "",
    "source_platform": 1,
    "boss_name": "",
    "boss_title": "",
    "source_url": ""
}

job_count = 0

# db = MySQLUtils()
db = AsyncMySQLUtils()


async def insert_job_to_db(city=101010100, job_crawler: JobCrawler = None, all_page=False):
    with open('it_jobs.json', 'r', encoding='utf-8') as f:
        jobs_code = json.load(f)
        for job_code in jobs_code:
            print(f"正在获取{job_code['position']}-{job_code['subLevel']}-{job_code['jos']}({job_code['jos_code']})岗位招聘信息...")

            boss = BossCrawler(city=city, position=job_code['jos_code'], all_page=all_page)
            jobs = await boss.get_jobs()
            print(f"共获取{job_code['position']}-{job_code['subLevel']}-{job_code['jos']}({job_code['jos_code']})共{len(jobs)}个岗位")
            for job in jobs:
                print(f"正在获取{job['jobName']} (https://www.zhipin.com/job_detail/{job['encryptJobId']}.html)岗位招聘信息...")
                sample_job['job_id'] = job['encryptJobId']


                sample_job['job_title'] = job['jobName']
                sample_job['job_category_1'] = job_code['position']
                sample_job['job_category_2'] = job_code['subLevel']
                sample_job['job_category_3'] = job_code['jos']
                sample_job['company_id'] = job['encryptBrandId']
                sample_job['company_name'] = job['brandName']
                sample_job['job_description'] = ""
                sample_job['job_requirements'] = ""
                sample_job['job_skills'] = ",".join(job['skills'])
                sample_job['job_description_detail'] = ""

                min_salary, max_salary, multiplier = extract_salary_info(job['salaryDesc'])
                sample_job['salary_min'] = min_salary
                sample_job['salary_max'] = max_salary
                sample_job['salary_count'] = multiplier


                sample_job['work_experience'] = job['jobExperience']
                sample_job['education_level'] = job['jobDegree']
                sample_job['city_name'] = job['cityName']
                sample_job['area_detail'] = job['areaDistrict']
                sample_job['business_circle'] = job['businessDistrict']

                sample_job['work_address'] = ""
                sample_job['job_benefits'] = ','.join(job['welfareList'])
                sample_job['source_platform'] = 1
                sample_job['boss_name'] = job['bossName']
                sample_job['boss_title'] = job['bossTitle']
                sample_job['source_url'] = f"https://www.zhipin.com/job_detail/{job['encryptJobId']}.html"

                job_description_detail, location_address, company_size, company_stage, company_industry = await job_crawler.get_job_detail(job_id=job['encryptJobId'])

                sample_job['job_description_detail'] = job_description_detail
                sample_job['work_address'] = location_address
                sample_job['company_size'] = company_size
                sample_job['company_stage'] = company_stage
                sample_job['company_industry'] = company_industry

                try:

                    company_detail = await job_crawler.get_company_detail(company_id=job['encryptBrandId'])

                    sample_job.update(company_detail)

                    await db.insert_data("job_postings", sample_job, check_fields=["job_id"])
                    global job_count
                    job_count += 1

                except Exception as e:
                    print(f"{job['encryptBrandId']}(https://www.zhipin.com/gongsi/{job['encryptBrandId']}.html) 公司信息解析失败，错误信息：{e}")

    await db.close_pool()


async def main():
    cities = [
        # 101010100,  # 北京
        # 101020100,  # 上海
        # 101210100,  # 杭州
        # 101280600,  # 深圳
        101280100   # 广州
    ]
    job_crawler = JobCrawler()
    tasks = [insert_job_to_db(city=city, job_crawler=job_crawler, all_page=False) for city in cities]
    await asyncio.gather(*tasks)
    print("*" * 50)
    print("*" * 50)
    print(f"共获取{job_count}个岗位")
    print("*" * 50)
    print("*" * 50)

if __name__ == '__main__':
    asyncio.run(main())