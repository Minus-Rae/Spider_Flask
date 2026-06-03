# -*- coding: utf-8 -*-
"""
智联招聘数据清洗工具
- 输入：spider.py 输出的 job_data.csv
- 输出：clean_job_data.csv
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

SIZE_PATTERN = re.compile(r"(20人以下|20-99人|100-299人|300-499人|500-999人|1000-9999人|10000人以上)")
EDU_ORDER = ["学历不限", "初中及以下", "高中", "中专/中技", "大专", "本科", "硕士", "博士"]
WORK_ORDER = ["经验不限", "应届", "1-3年", "3-5年", "5-10年", "10年以上"]


def parse_salary(s: object) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[int], Optional[float], str]:
    """解析智联薪资字符串。

    返回：min_k, max_k, avg_k, salary_months, annual_avg_k, salary_type
    - min/max/avg 单位为 K/月
    - annual_avg_k 单位为 K/年
    """
    if pd.isna(s):
        return None, None, None, None, None, "unknown"
    text = str(s).strip()
    if not text or "面议" in text:
        return None, None, None, None, None, "negotiable"

    months = 12
    m_months = re.search(r"·\s*(\d+)\s*薪", text)
    if m_months:
        months = int(m_months.group(1))

    # 日薪：如 200-300元/天，按 21.75 个工作日/月折算
    if "元/天" in text:
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
        if not nums:
            return None, None, None, months, None, "daily"
        if len(nums) == 1:
            min_k = max_k = nums[0] * 21.75 / 1000
        else:
            min_k, max_k = nums[0] * 21.75 / 1000, nums[1] * 21.75 / 1000
        avg_k = (min_k + max_k) / 2
        return round(min_k, 2), round(max_k, 2), round(avg_k, 2), months, round(avg_k * months, 2), "daily"

    # 月薪：元 或 万
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if not nums:
        return None, None, None, months, None, "unknown"

    unit = "wan" if "万" in text else "yuan"
    factor = 10 if unit == "wan" else 1 / 1000
    if len(nums) == 1:
        min_k = max_k = nums[0] * factor
    else:
        min_k, max_k = nums[0] * factor, nums[1] * factor
    avg_k = (min_k + max_k) / 2
    return round(min_k, 2), round(max_k, 2), round(avg_k, 2), months, round(avg_k * months, 2), "monthly"


def split_area(area: object) -> tuple[str, str, str]:
    parts = [p.strip() for p in str(area).split("·") if p.strip()] if not pd.isna(area) else []
    city = parts[0] if len(parts) >= 1 else "未知"
    district = parts[1] if len(parts) >= 2 else "未知"
    business_area = parts[2] if len(parts) >= 3 else ""
    return city, district, business_area


def fix_company_fields(row: pd.Series) -> tuple[str, str, str]:
    """修正 com_type / com_size / industry 错位。

    爬虫里 company_tags[0] 和 company_tags[1] 固定映射，实际页面上可能是：
    公司性质、公司规模、行业；也可能缺少公司性质，导致规模/行业前移。
    """
    raw_type = "" if pd.isna(row.get("com_type")) else str(row.get("com_type")).strip()
    raw_size = "" if pd.isna(row.get("com_size")) else str(row.get("com_size")).strip()
    values = [x for x in [raw_type, raw_size] if x]

    company_size = next((x for x in values if SIZE_PATTERN.fullmatch(x)), "未知")
    company_type = next((x for x in values if x != company_size and not SIZE_PATTERN.fullmatch(x)), "未知")

    # 如果一个字段是规模、另一个字段是行业，那么公司性质缺失；将非规模字段放入 industry 更合理
    industry = "未知"
    if raw_type and not SIZE_PATTERN.fullmatch(raw_type) and raw_type != company_type:
        industry = raw_type
    if raw_size and not SIZE_PATTERN.fullmatch(raw_size) and raw_size != company_type:
        industry = raw_size
    if company_type == "未知":
        # 没有明确公司性质时，把非规模字段作为行业，不硬塞到公司性质
        non_size = [x for x in values if not SIZE_PATTERN.fullmatch(x)]
        if non_size:
            industry = non_size[0]

    return company_type, company_size, industry


def split_category(path: object) -> tuple[str, str, str]:
    parts = str(path).split("-") if not pd.isna(path) else []
    while len(parts) < 3:
        parts.append("未知")
    return parts[0], parts[1], "-".join(parts[2:])


def clean_jobs(input_csv: str | Path, output_csv: str | Path | None = None) -> pd.DataFrame:
    input_csv = Path(input_csv)
    df = pd.read_csv(input_csv, encoding="utf-8-sig")

    # 基础去重与空值整理
    text_cols = ["job_name", "job_salary", "job_area", "com_name", "com_type", "com_size", "education", "work_year", "job_benefits", "category_path"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    df = df.drop_duplicates(subset=["job_name", "job_salary", "job_area", "com_name", "category_path"], keep="first").copy()
    #df = df.drop_duplicates().copy()

    # 薪资标准化
    salary_cols = df["job_salary"].apply(parse_salary).apply(pd.Series)
    salary_cols.columns = ["salary_min_k", "salary_max_k", "salary_avg_k", "salary_months", "annual_salary_avg_k", "salary_type"]
    df = pd.concat([df, salary_cols], axis=1)

    # 地区拆分
    area_cols = df["job_area"].apply(split_area).apply(pd.Series)
    area_cols.columns = ["city", "district", "business_area"]
    df = pd.concat([df, area_cols], axis=1)

    # 公司字段修正
    company_cols = df.apply(fix_company_fields, axis=1).apply(pd.Series)
    company_cols.columns = ["company_type_clean", "company_size_clean", "industry"]
    df = pd.concat([df, company_cols], axis=1)

    # 分类路径拆分
    cat_cols = df["category_path"].apply(split_category).apply(pd.Series)
    cat_cols.columns = ["category", "subcategory", "position"]
    df = pd.concat([df, cat_cols], axis=1)

    # 缺失值补全
    df["education"] = df["education"].replace("", "未知")
    df["work_year"] = df["work_year"].replace("", "经验不限")
    df["job_benefits"] = df["job_benefits"].replace("", "")

    # 时间字段
    df["crawl_time"] = pd.to_datetime(df["crawl_time"], errors="coerce")

    # 排序：方便人工查看
    df = df.sort_values(["city", "category", "subcategory", "position", "salary_avg_k"], ascending=[True, True, True, True, False])

    if output_csv is not None:
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清洗智联招聘爬虫数据")
    parser.add_argument("--input", default="data/job_data.csv", help="原始 CSV 路径")
    parser.add_argument("--output", default="data/clean_job_data_1.csv", help="清洗后 CSV 路径")
    args = parser.parse_args()

    cleaned = clean_jobs(args.input, args.output)
    print(f"清洗完成：{len(cleaned)} 条 -> {args.output}")
