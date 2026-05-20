#config_selenium.py
# -*- coding: utf-8 -*-
"""智联招聘爬虫配置 - Selenium版"""

CITY_CODES = {
    "北京": "530",  # ✅ 只保留数字编码
}

POSITION_CODES = {
    "技术": {
        "后端开发": {
            "Python": {
                "code": "1000004,2000021,9000300160000",  # ✅ 纯数字+逗号
                "label": "Python"
            },
        },
    },
}

CRAWL_STRATEGY = {
    "enabled_combinations": [
        ("技术", "后端开发", ["Python"]),  # ✅ 只测这一组
    ],
    "cities": ["北京"],
    "max_pages": 2,  # ✅ 测试2页
    "delay_range": (2, 4),
}

OUTPUT_CONFIG = {
    "filename": "data/job_data_test.csv",
    "encoding": "utf-8-sig",
    "fields": [
        "job_name", "job_salary", "job_area", "com_name",
        "com_type", "com_size", "education", "work_year",
        "job_benefits", "category_path", "crawl_time",
    ]
} 