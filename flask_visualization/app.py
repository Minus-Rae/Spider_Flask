#app_connected.py - 连接 Flask 可视化后端与智联招聘爬虫数据
# -*- coding: utf-8 -*-
"""
Flask + ECharts 可视化后端：接入智联招聘真实爬虫数据

"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import datetime
import re

import pandas as pd
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from data_cleaning import clean_jobs

# 初始化 App
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
RAW_CSV_CANDIDATES = [
    BASE_DIR / "clean_job_data.csv",      # 优先使用已清洗数据
    BASE_DIR / "data" / "clean_job_data.csv",
    BASE_DIR / "job_data.csv",            # 没有清洗数据时自动清洗原始数据
    BASE_DIR / "data" / "job_data.csv",
]


def find_data_file() -> Path:
    for path in RAW_CSV_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "未找到数据文件。请将 job_data.csv 或 clean_job_data.csv 放到项目根目录或 data/ 目录。"
    )


def load_data() -> pd.DataFrame:
    """加载数据；如果是原始 job_data.csv，则自动清洗并缓存。"""
    data_path = find_data_file()
    if data_path.name == "clean_job_data.csv":
        df = pd.read_csv(data_path, encoding="utf-8-sig")
    else:
        clean_path = data_path.with_name("clean_job_data.csv")
        df = clean_jobs(data_path, clean_path)

    # 确保关键字段存在，避免前端请求时报错
    for col in ["city", "district", "position", "category", "subcategory", "salary_avg_k", "job_benefits"]:
        if col not in df.columns:
            df[col] = "" if col != "salary_avg_k" else pd.NA
    return df


def filtered_data() -> pd.DataFrame:
    """按 URL 参数过滤数据：?city=北京&position=Python&keyword=工程师"""
    df = load_data()
    city = request.args.get("city", "").strip()
    position = request.args.get("position", "").strip()
    category = request.args.get("category", "").strip()
    keyword = request.args.get("keyword", "").strip()

    if city:
        df = df[df["city"].astype(str) == city]
    if position:
        df = df[df["position"].astype(str).str.contains(position, case=False, na=False)]
    if category:
        df = df[df["category"].astype(str) == category]
    if keyword:
        mask = (
            df["job_name"].astype(str).str.contains(keyword, case=False, na=False)
            | df["com_name"].astype(str).str.contains(keyword, case=False, na=False)
            | df["job_benefits"].astype(str).str.contains(keyword, case=False, na=False)
        )
        df = df[mask]
    return df


# ==================== 页面路由 ====================
@app.route("/")
def dashboard():
    """返回可视化大屏页面"""
    return render_template("dashboard.html")


# ==================== 数据接口 ====================
@app.route("/api/summary")
def get_summary():
    """核心指标卡：岗位数、城市数、平均薪资等。"""
    df = filtered_data()
    salary = pd.to_numeric(df["salary_avg_k"], errors="coerce")
    return jsonify({
        "success": True,
        "data": {
            "job_count": int(len(df)),
            "city_count": int(df["city"].nunique()),
            "company_count": int(df["com_name"].nunique()),
            "avg_salary_k": round(float(salary.mean()), 2) if salary.notna().any() else None,
            "median_salary_k": round(float(salary.median()), 2) if salary.notna().any() else None,
            "unit": "K/月"
        }
    })


@app.route("/api/salary_data")
def get_salary_data():
    """岗位薪资分布：兼容原柱状图接口格式。"""
    df = filtered_data()
    salary = pd.to_numeric(df["salary_avg_k"], errors="coerce").dropna()
    bins = [0, 5, 10, 20, 30, 50, float("inf")]
    labels = ["5K以下", "5-10K", "10-20K", "20-30K", "30-50K", "50K+"]
    counts = pd.cut(salary, bins=bins, labels=labels, right=False).value_counts().reindex(labels, fill_value=0)
    return jsonify({
        "success": True,
        "data": {
            "categories": labels,
            "values": [int(v) for v in counts.tolist()],
            "unit": "个岗位"
        }
    })


@app.route("/api/city_data")
def get_city_data():
    """城市岗位分布：兼容原饼图接口格式。"""
    df = filtered_data()
    counts = df["city"].fillna("未知").replace("", "未知").value_counts().head(10)
    return jsonify({
        "success": True,
        "data": [{"name": str(k), "value": int(v)} for k, v in counts.items()]
    })


@app.route("/api/skill_cloud")
def get_skill_cloud():
    """技能要求词云：从 job_benefits 标签中统计词频。"""
    df = filtered_data()
    stop_words = {"", "无", "不限", "其他", "岗位职责", "任职要求"}
    counter = Counter()

    for text in df["job_benefits"].fillna("").astype(str):
        # 兼容英文逗号、中文逗号、顿号、斜杠、空格等分隔
        tokens = re.split(r"[,，、/|;；\s]+", text)
        for token in tokens:
            token = token.strip()
            if len(token) < 2 or token in stop_words:
                continue
            # 常见技能大小写归一
            upper_map = {
                "python": "Python", "java": "Java", "javascript": "JavaScript",
                "sql": "SQL", "mysql": "MySQL", "redis": "Redis", "vue": "Vue",
                "spring": "Spring", "linux": "Linux", "docker": "Docker",
                "node.js": "Node.js", "golang": "Golang", "php": "PHP"
            }
            token = upper_map.get(token.lower(), token)
            counter[token] += 1

    return jsonify({
        "success": True,
        "data": [{"name": k, "value": int(v)} for k, v in counter.most_common(80)]
    })


@app.route("/api/education_data")
def get_education_data():
    """学历要求分布。"""
    df = filtered_data()
    counts = df["education"].fillna("未知").replace("", "未知").value_counts()
    return jsonify({
        "success": True,
        "data": [{"name": str(k), "value": int(v)} for k, v in counts.items()]
    })


@app.route("/api/work_year_data")
def get_work_year_data():
    """工作经验要求分布。"""
    df = filtered_data()
    counts = df["work_year"].fillna("经验不限").replace("", "经验不限").value_counts()
    return jsonify({
        "success": True,
        "data": [{"name": str(k), "value": int(v)} for k, v in counts.items()]
    })


@app.route("/api/category_salary")
def get_category_salary():
    """不同职位方向的平均薪资。"""
    df = filtered_data().copy()
    df["salary_avg_k"] = pd.to_numeric(df["salary_avg_k"], errors="coerce")
    grouped = (
        df.dropna(subset=["salary_avg_k"])
        .groupby("position", as_index=False)
        .agg(avg_salary_k=("salary_avg_k", "mean"), job_count=("job_name", "count"))
        .sort_values("avg_salary_k", ascending=False)
        .head(20)
    )
    return jsonify({
        "success": True,
        "data": [
            {"name": row["position"], "value": round(float(row["avg_salary_k"]), 2), "job_count": int(row["job_count"])}
            for _, row in grouped.iterrows()
        ],
        "unit": "K/月"
    })


@app.route("/api/job_list")
def get_job_list():
    """岗位明细表，可用于前端表格。"""
    df = filtered_data().copy()
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
    start = (page - 1) * page_size
    end = start + page_size

    cols = [
        "job_name", "job_salary", "salary_avg_k", "city", "district", "com_name",
        "company_type_clean", "company_size_clean", "education", "work_year",
        "job_benefits", "category", "subcategory", "position"
    ]
    cols = [c for c in cols if c in df.columns]
    records = df.iloc[start:end][cols].where(pd.notna(df.iloc[start:end][cols]), None).to_dict(orient="records")
    return jsonify({
        "success": True,
        "data": records,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": int(len(df))
        }
    })




# ==================== 深度分析接口：岗位、薪资、技能、要求 ====================

def _num(series):
    return pd.to_numeric(series, errors="coerce")


def _clean_label(value, default="未知"):
    if pd.isna(value):
        return default
    text = str(value).strip()
    return text if text else default


def extract_skill_counter(df: pd.DataFrame, top_n: int = 50) -> Counter:
    """从 job_benefits 中提取技能/标签词频。"""
    stop_words = {
        "", "无", "不限", "其他", "岗位职责", "任职要求", "职位描述", "工作内容",
        "五险一金", "周末双休", "绩效奖金", "餐补", "通讯补助", "交通补助",
        "带薪年假", "节日福利", "定期体检", "加班补助", "包吃", "包住",
    }
    upper_map = {
        "python": "Python", "java": "Java", "javascript": "JavaScript",
        "js": "JavaScript", "sql": "SQL", "mysql": "MySQL", "redis": "Redis",
        "vue": "Vue", "react": "React", "spring": "Spring", "linux": "Linux",
        "docker": "Docker", "node.js": "Node.js", "nodejs": "Node.js",
        "golang": "Golang", "go": "Golang", "php": "PHP", "c++": "C++",
        "c#": "C#", "html5": "HTML5", "css": "CSS", "pytorch": "PyTorch",
        "tensorflow": "TensorFlow", "nlp": "NLP", "aigc": "AIGC",
    }
    counter = Counter()
    for text in df.get("job_benefits", pd.Series(dtype=str)).fillna("").astype(str):
        tokens = re.split(r"[,，、/|;；\s]+", text)
        for token in tokens:
            token = token.strip()
            if len(token) < 2 or token in stop_words:
                continue
            token = upper_map.get(token.lower(), token)
            counter[token] += 1
    return Counter(dict(counter.most_common(top_n)))


@app.route("/api/position_salary")
def get_position_salary():
    """
    不同岗位平均薪资对比。
    适合：横向柱状图 / 排名条形图。
    参数：
      top_n=20
      min_count=5
      sort=avg_salary_k|job_count
    """
    df = filtered_data().copy()
    top_n = int(request.args.get("top_n", 20))
    min_count = int(request.args.get("min_count", 5))
    sort_field = request.args.get("sort", "avg_salary_k")
    df["salary_avg_k"] = _num(df["salary_avg_k"])
    grouped = (
        df.dropna(subset=["salary_avg_k"])
        .assign(position=df["position"].apply(_clean_label))
        .groupby("position", as_index=False)
        .agg(
            job_count=("job_name", "count"),
            avg_salary_k=("salary_avg_k", "mean"),
            median_salary_k=("salary_avg_k", "median"),
            min_salary_k=("salary_avg_k", "min"),
            max_salary_k=("salary_avg_k", "max"),
        )
    )
    grouped = grouped[grouped["job_count"] >= min_count]
    if sort_field not in grouped.columns:
        sort_field = "avg_salary_k"
    grouped = grouped.sort_values(sort_field, ascending=False).head(top_n)
    return jsonify({
        "success": True,
        "data": [
            {
                "name": row["position"],
                "job_count": int(row["job_count"]),
                "avg_salary_k": round(float(row["avg_salary_k"]), 2),
                "median_salary_k": round(float(row["median_salary_k"]), 2),
                "min_salary_k": round(float(row["min_salary_k"]), 2),
                "max_salary_k": round(float(row["max_salary_k"]), 2),
            }
            for _, row in grouped.iterrows()
        ],
        "unit": "K/月"
    })


@app.route("/api/position_requirement")
def get_position_requirement():
    """
    不同岗位的人员要求分布。
    适合：堆叠柱状图。
    参数：
      dimension=education 或 work_year
      top_n=12
    """
    df = filtered_data().copy()
    dimension = request.args.get("dimension", "education")
    if dimension not in {"education", "work_year"}:
        dimension = "education"
    top_n = int(request.args.get("top_n", 12))

    df["position"] = df["position"].apply(_clean_label)
    df[dimension] = df[dimension].apply(lambda x: _clean_label(x, "经验不限" if dimension == "work_year" else "未知"))
    top_positions = df["position"].value_counts().head(top_n).index.tolist()
    sub = df[df["position"].isin(top_positions)]

    table = pd.crosstab(sub["position"], sub[dimension])
    table = table.reindex(top_positions).fillna(0).astype(int)
    legends = table.columns.tolist()

    return jsonify({
        "success": True,
        "data": {
            "positions": top_positions,
            "legends": legends,
            "series": [
                {
                    "name": legend,
                    "values": [int(v) for v in table[legend].tolist()]
                }
                for legend in legends
            ]
        }
    })


@app.route("/api/position_skill_heatmap")
def get_position_skill_heatmap():
    """
    岗位-技能热力图。
    适合：ECharts heatmap，展示不同岗位高频技能要求。
    参数：
      top_positions=12
      top_skills=20
    """
    df = filtered_data().copy()
    top_positions = int(request.args.get("top_positions", 12))
    top_skills = int(request.args.get("top_skills", 20))

    df["position"] = df["position"].apply(_clean_label)
    positions = df["position"].value_counts().head(top_positions).index.tolist()
    sub = df[df["position"].isin(positions)]
    skills = [k for k, _ in extract_skill_counter(sub, top_skills).most_common(top_skills)]

    matrix = []
    for p_idx, pos in enumerate(positions):
        pos_texts = sub[sub["position"] == pos]["job_benefits"].fillna("").astype(str)
        joined = "，".join(pos_texts)
        for s_idx, skill in enumerate(skills):
            # 按岗位中包含该技能的岗位记录数统计，而不是简单字符串总出现次数
            count = int(pos_texts.str.contains(re.escape(skill), case=False, na=False).sum())
            matrix.append([s_idx, p_idx, count])

    return jsonify({
        "success": True,
        "data": {
            "skills": skills,
            "positions": positions,
            "matrix": matrix
        }
    })


@app.route("/api/city_salary")
def get_city_salary():
    """
    城市平均薪资与岗位数量。
    适合：柱状图 + 折线图双轴。
    """
    df = filtered_data().copy()
    df["salary_avg_k"] = _num(df["salary_avg_k"])
    grouped = (
        df.dropna(subset=["salary_avg_k"])
        .assign(city=df["city"].apply(_clean_label))
        .groupby("city", as_index=False)
        .agg(avg_salary_k=("salary_avg_k", "mean"), median_salary_k=("salary_avg_k", "median"), job_count=("job_name", "count"))
        .sort_values("avg_salary_k", ascending=False)
    )
    return jsonify({
        "success": True,
        "data": [
            {
                "name": row["city"],
                "avg_salary_k": round(float(row["avg_salary_k"]), 2),
                "median_salary_k": round(float(row["median_salary_k"]), 2),
                "job_count": int(row["job_count"]),
            }
            for _, row in grouped.iterrows()
        ],
        "unit": "K/月"
    })


@app.route("/api/company_size_salary")
def get_company_size_salary():
    """
    公司规模与平均薪资。
    适合：柱状图 / 散点图。
    """
    df = filtered_data().copy()
    size_col = "company_size_clean" if "company_size_clean" in df.columns else "com_size"
    df["salary_avg_k"] = _num(df["salary_avg_k"])
    grouped = (
        df.dropna(subset=["salary_avg_k"])
        .assign(company_size=df[size_col].apply(_clean_label))
        .groupby("company_size", as_index=False)
        .agg(avg_salary_k=("salary_avg_k", "mean"), median_salary_k=("salary_avg_k", "median"), job_count=("job_name", "count"))
    )
    order = ["20人以下", "20-99人", "100-299人", "300-499人", "500-999人", "1000-9999人", "10000人以上", "未知"]
    grouped["order"] = grouped["company_size"].apply(lambda x: order.index(x) if x in order else len(order))
    grouped = grouped.sort_values("order")
    return jsonify({
        "success": True,
        "data": [
            {
                "name": row["company_size"],
                "avg_salary_k": round(float(row["avg_salary_k"]), 2),
                "median_salary_k": round(float(row["median_salary_k"]), 2),
                "job_count": int(row["job_count"]),
            }
            for _, row in grouped.iterrows()
        ],
        "unit": "K/月"
    })


@app.route("/api/education_salary")
def get_education_salary():
    """
    学历要求与平均薪资。
    适合：柱状图，解释学历门槛和薪资水平关系。
    """
    df = filtered_data().copy()
    df["salary_avg_k"] = _num(df["salary_avg_k"])
    grouped = (
        df.dropna(subset=["salary_avg_k"])
        .assign(education=df["education"].apply(_clean_label))
        .groupby("education", as_index=False)
        .agg(avg_salary_k=("salary_avg_k", "mean"), median_salary_k=("salary_avg_k", "median"), job_count=("job_name", "count"))
    )
    order = ["学历不限", "高中", "中专/中技", "大专", "本科", "硕士", "博士", "未知"]
    grouped["order"] = grouped["education"].apply(lambda x: order.index(x) if x in order else len(order))
    grouped = grouped.sort_values("order")
    return jsonify({
        "success": True,
        "data": [
            {
                "name": row["education"],
                "avg_salary_k": round(float(row["avg_salary_k"]), 2),
                "median_salary_k": round(float(row["median_salary_k"]), 2),
                "job_count": int(row["job_count"]),
            }
            for _, row in grouped.iterrows()
        ],
        "unit": "K/月"
    })


@app.route("/api/work_year_salary")
def get_work_year_salary():
    """
    工作经验要求与平均薪资。
    适合：柱状图，展示经验年限对薪资的影响。
    """
    df = filtered_data().copy()
    df["salary_avg_k"] = _num(df["salary_avg_k"])
    grouped = (
        df.dropna(subset=["salary_avg_k"])
        .assign(work_year=df["work_year"].apply(lambda x: _clean_label(x, "经验不限")))
        .groupby("work_year", as_index=False)
        .agg(avg_salary_k=("salary_avg_k", "mean"), median_salary_k=("salary_avg_k", "median"), job_count=("job_name", "count"))
    )
    order = ["经验不限", "无经验", "在校/应届", "1年以内", "1-3年", "3-5年", "5-10年", "10年以上", "未知"]
    grouped["order"] = grouped["work_year"].apply(lambda x: order.index(x) if x in order else len(order))
    grouped = grouped.sort_values("order")
    return jsonify({
        "success": True,
        "data": [
            {
                "name": row["work_year"],
                "avg_salary_k": round(float(row["avg_salary_k"]), 2),
                "median_salary_k": round(float(row["median_salary_k"]), 2),
                "job_count": int(row["job_count"]),
            }
            for _, row in grouped.iterrows()
        ],
        "unit": "K/月"
    })


@app.route("/api/position_overview")
def get_position_overview():
    """
    岗位综合概览：岗位数量、平均薪资、平均年薪。
    适合：散点图。x=岗位数量，y=平均薪资，气泡大小=平均年薪或岗位数量。
    """
    df = filtered_data().copy()
    df["salary_avg_k"] = _num(df["salary_avg_k"])
    if "annual_salary_avg_k" in df.columns:
        df["annual_salary_avg_k"] = _num(df["annual_salary_avg_k"])
    else:
        df["annual_salary_avg_k"] = df["salary_avg_k"] * 12

    grouped = (
        df.dropna(subset=["salary_avg_k"])
        .assign(position=df["position"].apply(_clean_label))
        .groupby("position", as_index=False)
        .agg(
            job_count=("job_name", "count"),
            avg_salary_k=("salary_avg_k", "mean"),
            annual_salary_avg_k=("annual_salary_avg_k", "mean"),
        )
        .sort_values("job_count", ascending=False)
    )
    return jsonify({
        "success": True,
        "data": [
            {
                "name": row["position"],
                "job_count": int(row["job_count"]),
                "avg_salary_k": round(float(row["avg_salary_k"]), 2),
                "annual_salary_avg_k": round(float(row["annual_salary_avg_k"]), 2),
            }
            for _, row in grouped.iterrows()
        ],
        "unit": {
            "avg_salary_k": "K/月",
            "annual_salary_avg_k": "K/年"
        }
    })


@app.route("/api/skill_position")
def get_skill_position():
    """
    指定技能在不同岗位中的需求情况。
    参数：skill=Python
    适合：点击词云后联动展示。
    """
    df = filtered_data().copy()
    skill = request.args.get("skill", "").strip()
    if not skill:
        return jsonify({"success": False, "message": "请提供 skill 参数，例如 /api/skill_position?skill=Python"}), 400

    df["position"] = df["position"].apply(_clean_label)
    sub = df[df["job_benefits"].fillna("").astype(str).str.contains(re.escape(skill), case=False, na=False)]
    grouped = (
        sub.groupby("position", as_index=False)
        .agg(job_count=("job_name", "count"))
        .sort_values("job_count", ascending=False)
    )
    return jsonify({
        "success": True,
        "skill": skill,
        "data": [{"name": row["position"], "value": int(row["job_count"])} for _, row in grouped.iterrows()]
    })


@app.route("/api/chart_suggestions")
def get_chart_suggestions():
    """返回推荐图表清单，方便前端动态生成菜单。"""
    return jsonify({
        "success": True,
        "data": [
            {"title": "不同岗位平均薪资排行", "api": "/api/position_salary", "chart": "横向柱状图", "analysis": "比较算法、后端、前端、测试、产品等岗位的薪资差异。"},
            {"title": "不同岗位学历要求分布", "api": "/api/position_requirement?dimension=education", "chart": "堆叠柱状图", "analysis": "观察不同岗位对本科、硕士、大专等学历的要求差异。"},
            {"title": "不同岗位经验要求分布", "api": "/api/position_requirement?dimension=work_year", "chart": "堆叠柱状图", "analysis": "观察应届、1-3年、3-5年、5-10年等经验门槛。"},
            {"title": "岗位-技能需求热力图", "api": "/api/position_skill_heatmap", "chart": "热力图", "analysis": "展示不同岗位高频技能，如 Python、Java、MySQL、Vue、PyTorch 等。"},
            {"title": "城市平均薪资对比", "api": "/api/city_salary", "chart": "柱状图 + 折线图", "analysis": "比较不同城市岗位数量和平均薪资。"},
            {"title": "公司规模与薪资关系", "api": "/api/company_size_salary", "chart": "柱状图", "analysis": "分析不同规模公司给出的薪资水平差异。"},
            {"title": "学历要求与薪资关系", "api": "/api/education_salary", "chart": "柱状图", "analysis": "分析学历门槛是否对应更高薪资。"},
            {"title": "经验要求与薪资关系", "api": "/api/work_year_salary", "chart": "柱状图", "analysis": "分析工作经验年限对薪资的影响。"},
            {"title": "岗位数量-薪资综合气泡图", "api": "/api/position_overview", "chart": "散点/气泡图", "analysis": "同时展示岗位热度和薪资水平，找出高需求高薪方向。"},
        ]
    })


@app.route("/api/health")
def health_check():
    """服务健康状态"""
    try:
        df = load_data()
        data_status = {"loaded": True, "rows": int(len(df))}
    except Exception as exc:
        data_status = {"loaded": False, "error": str(exc)}

    return jsonify({
        "status": "ok" if data_status["loaded"] else "error",
        "service": "flask-zhaopin-visualization",
        "version": "2.0.0",
        "data": data_status,
        "timestamp": datetime.datetime.now().isoformat()
    })


if __name__ == "__main__":
    print("🚀 Flask 服务启动: http://127.0.0.1:5000")
    print("📊 可视化大屏: http://127.0.0.1:5000/")
    print("🔧 健康检查: http://127.0.0.1:5000/api/health")
    app.run(host="127.0.0.1", port=5000, debug=True)
