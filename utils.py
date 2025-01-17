import os
import uuid
import re

import aiomysql
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union
import asyncio

def extract_salary_info(salary_str: str) -> tuple[int, int, int]:
    """
    从薪资字符串中提取最低月薪、最高月薪和薪资倍数

    Args:
        salary_str: 薪资字符串，支持以下格式：
            - "13-21K·13薪"
            - "13-21K"
            - "200-300元/天"
            - "500-5000元/月"

    Returns:
        tuple[int, int, int]: (最低月薪(元), 最高月薪(元), 薪资倍数)
            如果解析失败返回 (0, 0, 0)
    """
    # 去除所有空格
    salary_str = salary_str.replace(' ', '')

    # 匹配 K 形式的月薪 (例如: 13-21K·13薪)
    k_match = re.search(r"(\d+)-(\d+)K(?:·(\d+)薪)?", salary_str)
    if k_match:
        min_salary = int(k_match.group(1)) * 1000
        max_salary = int(k_match.group(2)) * 1000
        multiplier = int(k_match.group(3)) if k_match.group(3) else 12
        return min_salary, max_salary, multiplier

    # 匹配日薪 (例如: 200-300元/天)
    day_match = re.search(r"(\d+)-(\d+)元/天", salary_str)
    if day_match:
        min_salary = int(day_match.group(1)) * 21  # 每月按21天计算
        max_salary = int(day_match.group(2)) * 21
        return min_salary, max_salary, 12  # 日薪默认12个月

    # 匹配普通月薪 (例如: 500-5000元/月)
    month_match = re.search(r"(\d+)-(\d+)元/月", salary_str)
    if month_match:
        min_salary = int(month_match.group(1))
        max_salary = int(month_match.group(2))
        return min_salary, max_salary, 12  # 月薪默认12个月

    # 无法匹配任何格式时返回零值
    return 0, 0, 0


# 单元测试
def test_salary_extractor():
    test_cases = [
        ("13-21K·13薪", (13000, 21000, 13)),
        ("13-21K", (13000, 21000, 12)),
        ("200-300元/天", (4200, 6300, 12)),  # 200*21=4200, 300*21=6300
        ("500-5000元/月", (500, 5000, 12)),
        ("非法格式", (0, 0, 0)),
        ("", (0, 0, 0))
    ]

    for test_input, expected in test_cases:
        result = extract_salary_info(test_input)
        assert result == expected, f"Test failed for {test_input}. Expected {expected}, got {result}"
        print(f"Test passed for {test_input}: {result}")



# # 单元测试
# def test_salary_extractor():
#     test_cases = [
#         ("13-21K·13薪", (13000, 21000, 13)),
#         ("13-21K", (13000, 21000, 12)),
#         ("200-300元/天", (4200, 6300, 12)),  # 200*21=4200, 300*21=6300
#         ("500-5000元/月", (500, 5000, 12)),
#         ("非法格式", (0, 0, 0)),
#         ("", (0, 0, 0))
#     ]
#
#     for test_input, expected in test_cases:
#         result = extract_salary_info(test_input)
#         assert result == expected, f"Test failed for {test_input}. Expected {expected}, got {result}"
#         print(f"Test passed for {test_input}: {result}")


class MySQLUtils:
    def __init__(self):
        """初始化数据库连接"""
        # 加载.env文件
        load_dotenv()
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME')
            )

            if self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True)
                print("Successfully connected to MySQL database")
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise

    def check_duplicate(self, table: str, conditions: Dict[str, Any]) -> bool:
        """
        检查记录是否已存在

        Args:
            table: 表名
            conditions: 查重条件，格式为 {字段名: 值}

        Returns:
            bool: 如果记录存在返回True，否则返回False
        """
        where_clause = " AND ".join([f"{k} = %s" for k in conditions.keys()])
        query = f"SELECT COUNT(*) as count FROM {table} WHERE {where_clause}"

        try:
            self.cursor.execute(query, tuple(conditions.values()))
            result = self.cursor.fetchone()
            return result['count'] > 0
        except Error as e:
            print(f"Error checking duplicate: {e}")
            return False

    def insert_data(self, table: str, data: Dict[str, Any], check_fields: List[str] = None) -> bool:
        """
        插入数据（可选查重）

        Args:
            table: 表名
            data: 要插入的数据，格式为 {字段名: 值}
            check_fields: 需要查重的字段列表，如果为None则不查重

        Returns:
            bool: 插入成功返回True，否则返回False
        """
        try:
            # 如果指定了查重字段，先进行查重
            if check_fields:
                check_data = {k: data[k] for k in check_fields if k in data}
                if self.check_duplicate(table, check_data):
                    print("Duplicate record found, skipping insertion")
                    return False

            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

            self.cursor.execute(query, tuple(data.values()))
            self.connection.commit()
            print("Data inserted successfully")
            return True

        except Error as e:
            print(f"Error inserting data: {e}")
            self.connection.rollback()
            return False

    def update_data(self, table: str, data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """
        更新数据

        Args:
            table: 表名
            data: 要更新的数据，格式为 {字段名: 新值}
            conditions: 更新条件，格式为 {字段名: 值}

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        try:
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            where_clause = " AND ".join([f"{k} = %s" for k in conditions.keys()])
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

            values = tuple(data.values()) + tuple(conditions.values())
            self.cursor.execute(query, values)
            self.connection.commit()
            print("Data updated successfully")
            return True

        except Error as e:
            print(f"Error updating data: {e}")
            self.connection.rollback()
            return False

    def query_data(self,
                   table: str,
                   conditions: Optional[Dict[str, Any]] = None,
                   fields: Optional[List[str]] = None,
                   order_by: Optional[str] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        根据条件查询数据

        Args:
            table: 表名
            conditions: 查询条件，格式为 {字段名: 值}，可选
            fields: 需要返回的字段列表，如果为None则返回所有字段
            order_by: 排序字段，格式为 "field_name ASC/DESC"，可选
            limit: 返回记录的最大数量，可选

        Returns:
            List[Dict[str, Any]]: 查询结果列表，每个记录为一个字典
        """
        try:
            # 构建SELECT子句
            select_clause = "*" if not fields else ", ".join(fields)

            # 构建基础查询
            query = f"SELECT {select_clause} FROM {table}"

            # 添加WHERE子句（如果有条件）
            values = ()
            if conditions:
                where_clause = " AND ".join([f"{k} = %s" for k in conditions.keys()])
                query += f" WHERE {where_clause}"
                values = tuple(conditions.values())

            # 添加ORDER BY子句（如果指定）
            if order_by:
                query += f" ORDER BY {order_by}"

            # 添加LIMIT子句（如果指定）
            if limit:
                query += f" LIMIT {limit}"

            # 执行查询
            self.cursor.execute(query, values)
            results = self.cursor.fetchall()

            print(f"Query executed successfully, returned {len(results)} records")
            return results

        except Error as e:
            print(f"Error querying data: {e}")
            return []

    #
    # def __del__(self):
    #     """析构函数，确保关闭数据库连接"""
    #     if hasattr(self, 'connection') and self.connection.is_connected():
    #         self.cursor.close()
    #         self.connection.close()
    #         print("MySQL connection closed")



class AsyncMySQLUtils:
    def __init__(self):
        """初始化数据库连接配置"""
        # 加载.env文件
        load_dotenv()
        self.config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT')),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'db': os.getenv('DB_NAME'),
            'autocommit': True
        }
        self.pool = None

    async def create_pool(self):
        """创建连接池"""
        if self.pool is None:
            try:
                self.pool = await aiomysql.create_pool(**self.config)
                print("Successfully connected to MySQL database")
            except Exception as e:
                print(f"Error connecting to MySQL: {e}")
                raise

    async def close_pool(self):
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def check_duplicate(self, table: str, conditions: Dict[str, Any]) -> bool:
        """
        检查记录是否已存在

        Args:
            table: 表名
            conditions: 查重条件，格式为 {字段名: 值}

        Returns:
            bool: 如果记录存在返回True，否则返回False
        """
        where_clause = " AND ".join([f"{k} = %s" for k in conditions.keys()])
        query = f"SELECT COUNT(*) as count FROM {table} WHERE {where_clause}"

        try:
            await self.create_pool()
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, tuple(conditions.values()))
                    result = await cursor.fetchone()
                    return result['count'] > 0
        except Exception as e:
            print(f"Error checking duplicate: {e}")
            return False

    async def insert_data(self, table: str, data: Dict[str, Any], check_fields: Optional[List[str]] = None) -> bool:
        """
        插入数据（可选查重）

        Args:
            table: 表名
            data: 要插入的数据，格式为 {字段名: 值}
            check_fields: 需要查重的字段列表，如果为None则不查重

        Returns:
            bool: 插入成功返回True，否则返回False
        """
        try:
            await self.create_pool()
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 如果指定了查重字段，先进行查重
                    if check_fields:
                        check_data = {k: data[k] for k in check_fields if k in data}
                        if await self.check_duplicate(table, check_data):
                            print("Duplicate record found, skipping insertion")
                            return False

                    columns = ", ".join(data.keys())
                    placeholders = ", ".join(["%s"] * len(data))
                    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

                    await cursor.execute(query, tuple(data.values()))
                    await conn.commit()
                    print("Data inserted successfully")
                    return True

        except Exception as e:
            print(f"Error inserting data: {e}")
            return False

    async def update_data(self, table: str, data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """
        更新数据

        Args:
            table: 表名
            data: 要更新的数据，格式为 {字段名: 新值}
            conditions: 更新条件，格式为 {字段名: 值}

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        try:
            await self.create_pool()
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
                    where_clause = " AND ".join([f"{k} = %s" for k in conditions.keys()])
                    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

                    values = tuple(data.values()) + tuple(conditions.values())
                    await cursor.execute(query, values)
                    await conn.commit()
                    print("Data updated successfully")
                    return True

        except Exception as e:
            print(f"Error updating data: {e}")
            return False

    async def query_data(self,
                        table: str,
                        conditions: Optional[Dict[str, Any]] = None,
                        fields: Optional[List[str]] = None,
                        order_by: Optional[str] = None,
                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        根据条件查询数据

        Args:
            table: 表名
            conditions: 查询条件，格式为 {字段名: 值}，可选
            fields: 需要返回的字段列表，如果为None则返回所有字段
            order_by: 排序字段，格式为 "field_name ASC/DESC"，可选
            limit: 返回记录的最大数量，可选

        Returns:
            List[Dict[str, Any]]: 查询结果列表，每个记录为一个字典
        """
        try:
            await self.create_pool()
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 构建SELECT子句
                    select_clause = "*" if not fields else ", ".join(fields)

                    # 构建基础查询
                    query = f"SELECT {select_clause} FROM {table}"

                    # 添加WHERE子句（如果有条件）
                    values = ()
                    if conditions:
                        where_clause = " AND ".join([f"{k} = %s" for k in conditions.keys()])
                        query += f" WHERE {where_clause}"
                        values = tuple(conditions.values())

                    # 添加ORDER BY子句（如果指定）
                    if order_by:
                        query += f" ORDER BY {order_by}"

                    # 添加LIMIT子句（如果指定）
                    if limit:
                        query += f" LIMIT {limit}"

                    # 执行查询
                    await cursor.execute(query, values)
                    results = await cursor.fetchall()

                    print(f"Query executed successfully, returned {len(results)} records")
                    return results

        except Exception as e:
            print(f"Error querying data: {e}")
            return []

# 使用示例
async def main():
    db = AsyncMySQLUtils()
    try:
        # 插入示例
        data = {
            "job_id": uuid.uuid4().hex,
            "job_title": "高级Python开发工程师",
            "job_category_1": "技术",
            "job_category_2": "后端开发",
            "job_category_3": "Python开发",
            "company_id": "C10086",
            "company_name": "智能科技有限公司",
            "job_description": "负责公司核心业务系统的设计和开发，参与架构优化和性能调优",
            "job_requirements": "精通Python编程，熟悉Django/Flask等主流框架，具备良好的系统设计能力",
            "job_skills": "Python,Django,Flask,Redis,MySQL,MongoDB",
            "job_description_detail": "",
            "salary_min": 25000,
            "salary_max": 35000,
            "salary_count": 13,
            "work_experience": "3-5年",
            "education_level": "本科",
            "city_name": "北京",
            "area_detail": "朝阳区",
            "business_circle": "望京",
            "work_address": "北京市朝阳区望京科技园A座",
            "job_benefits": "五险一金,年终奖,带薪年假,定期体检,免费工作餐",
            "source_platform": 1,
            "boss_name": "张总",
            "boss_title": "技术总监",
            "source_url": "https://www.zhipin.com/job/12345",
            "created_at": "2024-01-14 10:00:00",
            "updated_at": "2024-01-14 10:00:00"
        }
        success = await db.insert_data('job_postings', data, ['job_id'])
        print(f"Insert success: {success}")

        # 查询示例
        results = await db.query_data(
            table='job_postings',
            conditions={"job_description_detail": ""},
            fields=["job_id", "job_title", "company_name", "salary_min", "salary_max"],
            order_by='salary_max DESC',
            limit=10
        )
        print(f"Query results: {results}")

    finally:
        await db.close_pool()


if __name__ == "__main__":

    # print("Starting test...")
    # # 创建工具类实例
    # db = MySQLUtils()

    # # 插入数据（带查重）
    # sample_job = {
    #     "job_id": uuid.uuid4().hex,
    #     "job_title": "高级Python开发工程师",
    #     "job_category_1": "技术",
    #     "job_category_2": "后端开发",
    #     "job_category_3": "Python开发",
    #     "company_id": "C10086",
    #     "company_name": "智能科技有限公司",
    #     "job_description": "负责公司核心业务系统的设计和开发，参与架构优化和性能调优",
    #     "job_requirements": "精通Python编程，熟悉Django/Flask等主流框架，具备良好的系统设计能力",
    #     "job_skills": "Python,Django,Flask,Redis,MySQL,MongoDB",
    #     "job_description_detail": "",
    #     "salary_min": 25000,
    #     "salary_max": 35000,
    #     "salary_count": 13,
    #     "work_experience": "3-5年",
    #     "education_level": "本科",
    #     "city_name": "北京",
    #     "area_detail": "朝阳区",
    #     "business_circle": "望京",
    #     "work_address": "北京市朝阳区望京科技园A座",
    #     "job_benefits": "五险一金,年终奖,带薪年假,定期体检,免费工作餐",
    #     "source_platform": 1,
    #     "boss_name": "张总",
    #     "boss_title": "技术总监",
    #     "source_url": "https://www.zhipin.com/job/12345",
    #     "created_at": "2024-01-14 10:00:00",
    #     "updated_at": "2024-01-14 10:00:00"
    # }
    # db.insert_data("job_postings", sample_job, check_fields=["job_id"])
    #
    # # 更新数据
    # update_data = {"job_description": "xxxxxxx", "job_requirements": "yyyyyyy"}
    # conditions = {"job_id": "JP202401140001"}
    # db.update_data("job_postings", update_data, conditions)

    #
    # # 测试查询数据
    # # 1. 简单查询
    # conditions = {"city_name": "北京", "job_category_1": "技术"}
    # results = db.query_data("job_postings", conditions=conditions)
    # print(results)
    # print("\nQuery results for jobs in Beijing tech category:", len(results))
    #
    # # 2. 查询特定字段
    # fields = ["job_id", "job_title", "company_name", "salary_min", "salary_max"]
    # results = db.query_data("job_postings", fields=fields, order_by="salary_max DESC", limit=5)
    # print(results)
    # print("\nTop 5 jobs by salary:", len(results))


    # 2. 查询字段值为空
    # conditions = {"job_description_detail": ""}
    # fields = ["job_id"]
    # results = db.query_data("job_postings", conditions, fields, limit=5)
    # print(results)
    # print(len(results))

    asyncio.run(main())
