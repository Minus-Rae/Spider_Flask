<img width="803" height="578" alt="image" src="https://github.com/user-attachments/assets/a4bf6aa6-8fcd-46d6-9527-cda7d13c2051" />

基于 Python 的招聘市场数据采集、清洗与可视化分析平台。项目通过 Selenium 爬取智联招聘岗位数据，使用 Pandas 对薪资、城市、学历、经验、岗位类别和技能标签进行清洗与结构化处理，并基于 Flask + ECharts 构建交互式招聘市场数据分析大屏。

## 项目简介

本项目面向招聘市场信息冗余、求职者难以快速了解岗位薪资与技能需求的问题，构建了一个轻量级的数据分析系统。项目采集了智联招聘中的多个城市和多个 IT 相关岗位方向数据。由于招聘网站中同一岗位可能在不同搜索关键词、分页或推荐区域中重复出现，因此分析阶段会对岗位名称、公司名称、薪资、地点和岗位分类等字段进行去重处理。最终通过 Web 可视化大屏展示岗位数量、薪资分布、城市分布、学历经验要求、技能词云以及多维交叉分析结果。

本项目适合作为 Python 数据分析、网络爬虫、Flask Web 开发和 ECharts 可视化的综合实践案例。

## 功能特性

- Selenium 自动化爬虫：支持按城市和岗位方向采集招聘信息
- 数据清洗与标准化：处理薪资格式、地区字段、岗位类别、学历经验等字段
- 薪资解析：将“10-15K·14薪”“1.5-2万”“200-300元/天”等格式统一转换为 K/月
- Flask 后端接口：提供岗位统计、薪资分布、城市分布、技能词云等 JSON API
- ECharts 可视化大屏：展示多维招聘市场分析结果
- 深度交叉分析：支持按岗位、城市、学历、经验等维度进行对比分析

## 技术栈

- Python
- Selenium
- Pandas
- Flask
- ECharts
- HTML / CSS / JavaScript

## 项目结构

```text
flask_visualization/
├── app.py                  # Flask 后端主程序
├── spider.py               # Selenium 爬虫脚本
├── data_cleaning.py        # 数据清洗脚本
├── config.py               # 城市、岗位、爬取策略等配置
├── requirements.txt        # Python 依赖
├── templates/
│   └── dashboard.html      # 可视化大屏页面
└── data/
    ├── job_data.csv        # 原始采集数据
    └── clean_job_data.csv  # 清洗后的分析数据

## 快速启动

1\. 安装依赖环境

确保您的电脑上已安装 Python 环境（建议 Python 3.8 及以上）。打开终端或命令行，在项目根目录下运行以下命令安装所需依赖：

pip install -r requirements.txt



2\. 运行可视化大屏

由于爬取全量数据耗时较长，项目 data/ 目录下已内置了清洗完毕的完整数据集 clean\_job\_data.csv。您可以直接启动后端服务查看可视化成果：

python app.py

启动成功后，在浏览器中访问以下地址即可查看动态可视化大屏：

&#x20;http://127.0.0.1:5000



3\. 运行爬虫与清洗模块

如果您希望重新爬取数据并体验完整的数据流转过程，可按以下顺序执行：

运行爬虫脚本抓取最新数据：python spider.py

运行数据清洗脚本处理原始数据：python data\_cleaning.py



