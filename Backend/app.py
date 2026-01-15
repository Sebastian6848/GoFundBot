from flask import Flask, request, jsonify
from flask_cors import CORS
from database import init_db, get_db
from models import FundBasicInfo, FundDetail
from fund_api import FundAPI
from sqlalchemy.orm import Session
import json

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化数据库
init_db()
fund_api = FundAPI()

@app.route('/')
def hello():
    return jsonify({"message": "Fund Analysis API is running!"})

@app.route('/api/fund/search', methods=['GET'])
def search_funds():
    """搜索基金"""
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({"error": "Keyword is required"}), 400
    
    funds = fund_api.search_funds(keyword)
    return jsonify({"data": funds})

@app.route('/api/fund/<fund_code>', methods=['GET'])
def get_fund_detail(fund_code):
    """获取基金详细信息"""
    if not fund_code:
        return jsonify({"error": "Fund code is required"}), 400
    
    db = next(get_db())
    
    # 直接从API获取最新数据
    detail_data = fund_api.get_fund_detail(fund_code)
    basic_info = fund_api.get_fund_basic_info(fund_code)
    
    if detail_data and basic_info:
        # 合并数据
        detail_data['basic_info'] = basic_info
        
        # 检查数据库是否存在记录
        cached_fund = db.query(FundDetail).filter(FundDetail.fund_code == fund_code).first()
        
        # 更新或新增记录
        if cached_fund:
            cached_fund.data_json = json.dumps(detail_data, ensure_ascii=False)
            cached_fund.net_worth_trend = json.dumps(detail_data.get('net_worth_trend', []), ensure_ascii=False)
            cached_fund.basic_info = json.dumps(basic_info, ensure_ascii=False)
        else:
            fund_detail = FundDetail(
                fund_code=fund_code,
                data_json=json.dumps(detail_data, ensure_ascii=False),
                net_worth_trend=json.dumps(detail_data.get('net_worth_trend', []), ensure_ascii=False),
                basic_info=json.dumps(basic_info, ensure_ascii=False)
            )
            db.add(fund_detail)
        
        try:
            db.commit()
        except Exception as e:
            print(f"Error saving to database: {e}")
            db.rollback()
        
        return jsonify(detail_data)
    
    # 如果API获取失败，尝试从数据库获取缓存数据作为兜底
    cached_fund = db.query(FundDetail).filter(FundDetail.fund_code == fund_code).first()
    if cached_fund:
        try:
            data = json.loads(cached_fund.data_json)
            return jsonify(data)
        except:
            pass

    return jsonify({"error": "Fund not found"}), 404

@app.route('/api/fund/<fund_code>/basic', methods=['GET'])
def get_fund_basic(fund_code):
    """获取基金基础信息"""
    if not fund_code:
        return jsonify({"error": "Fund code is required"}), 400
    
    basic_info = fund_api.get_fund_basic_info(fund_code)
    if basic_info:
        return jsonify(basic_info)
    else:
        return jsonify({"error": "Fund basic info not found"}), 404

@app.route('/api/fund/<fund_code>/trend', methods=['GET'])
def get_fund_trend(fund_code):
    """获取基金走势数据"""
    if not fund_code:
        return jsonify({"error": "Fund code is required"}), 400
    
    detail_data = fund_api.get_fund_detail(fund_code)
    if detail_data and 'net_worth_trend' in detail_data:
        return jsonify({
            "net_worth_trend": detail_data['net_worth_trend'],
            "ac_worth_trend": detail_data.get('ac_worth_trend', [])
        })
    else:
        return jsonify({"error": "Fund trend data not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)