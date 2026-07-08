app.py：Flask 后端主程序，负责提供 JSON 数据接口及页面渲染。

spider.py：Selenium 爬虫核心脚本，负责自动化抓取原始数据。

data\_cleaning.py：数据清洗脚本，负责处理缺失值并将非标准薪资转化为标准数值。

config.py：项目配置文件。

templates/dashboard.html：前端 ECharts 数据可视化大屏页面。

data/：数据存储文件夹。

&#x09;job\_data.csv：爬虫抓取到的 1.2万余条原始数据集。

&#x09;clean\_job\_data.csv：经过清洗和标准化后，供前端大屏调用的干净数据集。

requirements.txt：项目运行所需的 Python 依赖库列表。



快速启动

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



