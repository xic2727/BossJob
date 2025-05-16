-- 删除数据库，如果存在
DROP DATABASE IF EXISTS jobs_db;
-- 创建数据库
CREATE DATABASE jobs_db
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;

# -- 创建数据库
# CREATE DATABASE IF NOT EXISTS jobs_db
# DEFAULT CHARACTER SET utf8mb4
# DEFAULT COLLATE utf8mb4_unicode_ci;

USE jobs_db;


-- 创建职位信息表
CREATE TABLE job_postings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '职位ID',
    job_id VARCHAR(100) NOT NULL UNIQUE COMMENT '职位编号',
    job_title VARCHAR(100) NOT NULL COMMENT '职位名称',
    job_category_1 VARCHAR(100) COMMENT '职位大类',
    job_category_2 VARCHAR(100) COMMENT '职位二类',
    job_category_3 VARCHAR(100) COMMENT '职位三类',
    company_id  VARCHAR(50) COMMENT '公司ID',
    company_name VARCHAR(100) NOT NULL COMMENT '公司名称',
    company_size VARCHAR(20) COMMENT '公司规模',
    company_stage VARCHAR(20) COMMENT '融资阶段',
    company_industry VARCHAR(50) COMMENT '公司行业',
    business_detail_user VARCHAR(20) COMMENT '公司法人',
    business_detail_time VARCHAR(20) COMMENT '成立时间',
    business_detail_type VARCHAR(50) COMMENT '公司类型',
    business_detail_status VARCHAR(10) COMMENT '公司状态',
    business_detail_money VARCHAR(20) COMMENT '注册资本',
    business_detail_location VARCHAR(200) COMMENT '注册地址',
    company_jobs INT DEFAULT 0 COMMENT '公司招聘职位',
    work_time VARCHAR(20) COMMENT '工作时间',
    job_time VARCHAR(20) COMMENT '工休时间',
    work_tag TEXT COMMENT '工作标签',
    job_update_time VARCHAR(20) COMMENT '职位更新时间',
    job_description TEXT COMMENT '职位描述',
    job_requirements TEXT COMMENT '职位要求',
    job_skills TEXT COMMENT '职位技能要求',
    job_description_detail TEXT COMMENT '职位原始数据',
    salary_min DECIMAL(12,2) COMMENT '最低薪资',
    salary_max DECIMAL(12,2) COMMENT '最高薪资',
    salary_count INT DEFAULT 12 COMMENT '年薪次数',
    work_experience VARCHAR(50) COMMENT '工作经验要求',
    education_level VARCHAR(50) COMMENT '学历要求',
    city_name VARCHAR(100) COMMENT '城市',
    area_detail VARCHAR(100) COMMENT '区域',
    business_circle VARCHAR(100) COMMENT '商圈',
    work_address VARCHAR(255) COMMENT '工作地址',
    job_benefits TEXT COMMENT '职位福利',
    source_platform TINYINT DEFAULT 1 COMMENT '来源平台(1:boss, 2:智联, 3.猎聘)',
    boss_name VARCHAR(100) COMMENT 'boss名称',
    boss_title VARCHAR(100) COMMENT 'boss职位',
    source_url VARCHAR(512) COMMENT '原始链接',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_company_id (company_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='职位信息表';


-- 创建数据统计表
CREATE TABLE job_statistics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '统计ID',
    job_id BIGINT NOT NULL COMMENT '职位ID',
    job_category_1 VARCHAR(100) NOT NULL COMMENT '职位大类',
    job_category_2 VARCHAR(100) NOT NULL COMMENT '职位二类',
    job_category_3 VARCHAR(100) NOT NULL COMMENT '职位三类',
    job_name VARCHAR(100) NOT NULL COMMENT '职位名称',
    daily_add INT DEFAULT 0 COMMENT '日新增',
    total_count INT DEFAULT 0 COMMENT '累计数量',
    stat_date DATE NOT NULL COMMENT '统计日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE INDEX uk_job_date (job_id, stat_date),
    INDEX idx_stat_date (stat_date),

    FOREIGN KEY (job_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='职位统计表';
