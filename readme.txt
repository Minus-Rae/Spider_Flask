flask可视化第一次运行需要创建虚拟环境
>> python -m venv venv
（创建出venv文件夹，这个不要提交到git）

激活虚拟环境
>> # Windows:
>> venv\Scripts\activate
【如果报错禁止运行脚本可以运行：Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force】
>> # Mac/Linux:
>> source venv/bin/activate

安装依赖
>> pip install -r requirements.txt

启动服务
>> python app.py

之后启动激活+运行即可
venv\Scripts\activate

python app.py
