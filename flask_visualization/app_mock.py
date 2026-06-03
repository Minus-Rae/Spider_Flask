# -*- coding: utf-8 -*-
"""
Flask + ECharts 可视化后端
科研原型版：模拟数据测试
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import random
import datetime

# 初始化 App
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # ✅ 关键：让JSON返回中文/表情而不是 \uXXXX
CORS(app)  # ✅ 允许跨域，方便前后端分离开发

# ==================== 页面路由 ====================
@app.route('/')
def dashboard():
    """返回可视化大屏页面"""
    return render_template('dashboard.html')

# ==================== 数据接口 ====================

# 📊 接口1：岗位薪资分布（柱状图数据）
@app.route('/api/salary_data')
def get_salary_data():
    """模拟：不同薪资区间的岗位数量"""
    return jsonify({
        "success": True,
        "data": {
            "categories": ["5-10K", "10-20K", "20-30K", "30-50K", "50K+"],
            "values": [120, 200, 150, 80, 30],
            "unit": "个岗位"
        }
    })

# 🌍 接口2：城市岗位分布（饼图数据）
@app.route('/api/city_data')
def get_city_data():
    """模拟：热门城市岗位占比"""
    return jsonify({
        "success": True,
        "data": [
            {"name": "北京", "value": 350},
            {"name": "上海", "value": 280},
            {"name": "深圳", "value": 260},
            {"name": "杭州", "value": 180},
            {"name": "成都", "value": 150},
            {"name": "其他", "value": 200}
        ]
    })

# 📈 接口3：技能要求词云（词频数据）
@app.route('/api/skill_cloud')
def get_skill_cloud():
    """模拟：岗位技能关键词词频"""
    return jsonify({
        "success": True,
        "data": [
            {"name": "Python", "value": 150},
            {"name": "数据分析", "value": 120},
            {"name": "机器学习", "value": 100},
            {"name": "SQL", "value": 90},
            {"name": "可视化", "value": 80},
            {"name": "Pandas", "value": 70},
            {"name": "Flask", "value": 50},
            {"name": "爬虫", "value": 45},
            {"name": "深度学习", "value": 40},
            {"name": "NLP", "value": 35}
        ]
    })


# 🔧 接口4：健康检查（用于监控）
@app.route('/api/health')
def health_check():
    """服务健康状态"""
    return jsonify({
        "status": "ok",
        "service": "flask-visualization",
        "version": "1.0.0",
        "timestamp": datetime.datetime.now().isoformat()
    })

# ==================== 启动服务 ====================
if __name__ == '__main__':
    print("🚀 Flask 服务启动: http://127.0.0.1:5000")
    print("📊 可视化大屏: http://127.0.0.1:5000/")
    print("🔧 健康检查: http://127.0.0.1:5000/api/health")
    app.run(host='127.0.0.1', port=5000, debug=True)