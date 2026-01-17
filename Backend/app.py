from flask import Flask, request, jsonify
from flask_cors import CORS
from database import init_db, get_db
from models import FundBasicInfo, FundTrend, FundEstimate, FundPortfolio, FundExtraData
from fund_api import FundAPI
from fund_list_cache import get_fund_list_cache
from sqlalchemy.orm import Session
import json

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化数据库
init_db()
fund_api = FundAPI()
fund_list_cache = get_fund_list_cache()

def _json_dumps(data):
    return json.dumps(data, ensure_ascii=False) if data is not None else None

def _json_loads(data, default):
    if not data:
        return default
    try:
        return json.loads(data)
    except Exception:
        return default

def _build_cached_response(db: Session, fund_code: str):
    basic = db.query(FundBasicInfo).filter(FundBasicInfo.fund_code == fund_code).first()
    trend = db.query(FundTrend).filter(FundTrend.fund_code == fund_code).first()
    estimate = db.query(FundEstimate).filter(FundEstimate.fund_code == fund_code).first()
    portfolio = db.query(FundPortfolio).filter(FundPortfolio.fund_code == fund_code).first()
    extra = db.query(FundExtraData).filter(FundExtraData.fund_code == fund_code).first()

    if not any([basic, trend, estimate, portfolio, extra]):
        return None

    data = {}

    if basic:
        data['basic_info'] = _json_loads(basic.basic_json, {})
        data['performance'] = _json_loads(basic.performance_json, {})

    if trend:
        data['net_worth_trend'] = _json_loads(trend.net_worth_trend_json, [])
        data['accumulated_net_worth'] = _json_loads(trend.accumulated_net_worth_json, [])
        data['position_trend'] = _json_loads(trend.position_trend_json, [])
        data['total_return_trend'] = _json_loads(trend.total_return_trend_json, [])
        data['ranking_trend'] = _json_loads(trend.ranking_trend_json, [])
        data['ranking_percentage'] = _json_loads(trend.ranking_percentage_json, [])
        data['scale_fluctuation'] = _json_loads(trend.scale_fluctuation_json, {})

    if estimate:
        data['realtime_estimate'] = {
            'name': estimate.name,
            'fund_code': fund_code,
            'net_worth': estimate.net_worth,
            'net_worth_date': estimate.net_worth_date,
            'estimate_value': estimate.estimate_value,
            'estimate_change': estimate.estimate_change,
            'estimate_time': estimate.estimate_time
        }

    if portfolio:
        data['portfolio'] = {
            'stock_codes': _json_loads(portfolio.stock_codes_json, []),
            'bond_codes': _json_loads(portfolio.bond_codes_json, []),
            'stock_codes_new': _json_loads(portfolio.stock_codes_new_json, []),
            'bond_codes_new': _json_loads(portfolio.bond_codes_new_json, [])
        }

    if extra:
        data['holder_structure'] = _json_loads(extra.holder_structure_json, {})
        data['asset_allocation'] = _json_loads(extra.asset_allocation_json, {})
        data['performance_evaluation'] = _json_loads(extra.performance_evaluation_json, {})
        data['fund_managers'] = _json_loads(extra.fund_managers_json, [])
        data['subscription_redemption'] = _json_loads(extra.subscription_redemption_json, {})
        data['same_type_funds'] = _json_loads(extra.same_type_funds_json, [])

    return data

@app.route('/')
def hello():
    """测试接口是否可用"""
    return jsonify({"message": "Fund Analysis API is running!"})

@app.route('/api/fund/search', methods=['GET'])
def search_funds():
    """根据关键词搜索基金列表（使用本地缓存）"""
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({"error": "Keyword is required"}), 400
    
    # 使用本地缓存搜索
    funds = fund_list_cache.search(keyword, limit=20)
    return jsonify({"data": funds})

@app.route('/api/fund/search/status', methods=['GET'])
def get_search_status():
    """获取搜索数据库状态"""
    status = fund_list_cache.get_status()
    return jsonify(status)

@app.route('/api/fund/search/update', methods=['POST'])
def update_search_database():
    """更新本地基金搜索数据库"""
    result = fund_list_cache.update_from_api()
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/api/fund/<fund_code>', methods=['GET'])
def get_fund_detail(fund_code):
    """获取基金详细信息"""
    if not fund_code:
        return jsonify({"error": "Fund code is required"}), 400    
    db = next(get_db()) # 获取数据库会话
    
    # 使用新的 get_fund_data 方法获取清洗后的完整数据
    fund_data = fund_api.get_fund_data(fund_code)
    
    if fund_data:
        basic_info = fund_data.get('basic_info', {})
        performance = fund_data.get('performance', {})
        trend = {
            'net_worth_trend': fund_data.get('net_worth_trend', []),
            'accumulated_net_worth': fund_data.get('accumulated_net_worth', []),
            'position_trend': fund_data.get('position_trend', []),
            'total_return_trend': fund_data.get('total_return_trend', []),
            'ranking_trend': fund_data.get('ranking_trend', []),
            'ranking_percentage': fund_data.get('ranking_percentage', []),
            'scale_fluctuation': fund_data.get('scale_fluctuation', {})
        }
        estimate = fund_data.get('realtime_estimate', {})
        portfolio = fund_data.get('portfolio', {})
        extra = {
            'holder_structure': fund_data.get('holder_structure', {}),
            'asset_allocation': fund_data.get('asset_allocation', {}),
            'performance_evaluation': fund_data.get('performance_evaluation', {}),
            'fund_managers': fund_data.get('fund_managers', []),
            'subscription_redemption': fund_data.get('subscription_redemption', {}),
            'same_type_funds': fund_data.get('same_type_funds', [])
        }

        basic_record = db.query(FundBasicInfo).filter(FundBasicInfo.fund_code == fund_code).first()
        if basic_record:
            basic_record.fund_name = basic_info.get('fund_name')
            basic_record.fund_type = basic_info.get('fund_type')
            basic_record.original_rate = basic_info.get('original_rate')
            basic_record.current_rate = basic_info.get('current_rate')
            basic_record.min_subscription_amount = basic_info.get('min_subscription_amount')
            basic_record.is_hb = basic_info.get('is_hb')
            basic_record.basic_json = _json_dumps(basic_info)
            basic_record.performance_json = _json_dumps(performance)
        else:
            basic_record = FundBasicInfo(
                fund_code=fund_code,
                fund_name=basic_info.get('fund_name') or fund_code,
                fund_type=basic_info.get('fund_type'),
                original_rate=basic_info.get('original_rate'),
                current_rate=basic_info.get('current_rate'),
                min_subscription_amount=basic_info.get('min_subscription_amount'),
                is_hb=basic_info.get('is_hb'),
                basic_json=_json_dumps(basic_info),
                performance_json=_json_dumps(performance)
            )
            db.add(basic_record)

        trend_record = db.query(FundTrend).filter(FundTrend.fund_code == fund_code).first()
        if trend_record:
            trend_record.net_worth_trend_json = _json_dumps(trend['net_worth_trend'])
            trend_record.accumulated_net_worth_json = _json_dumps(trend['accumulated_net_worth'])
            trend_record.position_trend_json = _json_dumps(trend['position_trend'])
            trend_record.total_return_trend_json = _json_dumps(trend['total_return_trend'])
            trend_record.ranking_trend_json = _json_dumps(trend['ranking_trend'])
            trend_record.ranking_percentage_json = _json_dumps(trend['ranking_percentage'])
            trend_record.scale_fluctuation_json = _json_dumps(trend['scale_fluctuation'])
        else:
            trend_record = FundTrend(
                fund_code=fund_code,
                net_worth_trend_json=_json_dumps(trend['net_worth_trend']),
                accumulated_net_worth_json=_json_dumps(trend['accumulated_net_worth']),
                position_trend_json=_json_dumps(trend['position_trend']),
                total_return_trend_json=_json_dumps(trend['total_return_trend']),
                ranking_trend_json=_json_dumps(trend['ranking_trend']),
                ranking_percentage_json=_json_dumps(trend['ranking_percentage']),
                scale_fluctuation_json=_json_dumps(trend['scale_fluctuation'])
            )
            db.add(trend_record)

        estimate_record = db.query(FundEstimate).filter(FundEstimate.fund_code == fund_code).first()
        if estimate_record:
            estimate_record.name = estimate.get('name')
            estimate_record.net_worth = estimate.get('net_worth')
            estimate_record.net_worth_date = estimate.get('net_worth_date')
            estimate_record.estimate_value = estimate.get('estimate_value')
            estimate_record.estimate_change = estimate.get('estimate_change')
            estimate_record.estimate_time = estimate.get('estimate_time')
        else:
            estimate_record = FundEstimate(
                fund_code=fund_code,
                name=estimate.get('name'),
                net_worth=estimate.get('net_worth'),
                net_worth_date=estimate.get('net_worth_date'),
                estimate_value=estimate.get('estimate_value'),
                estimate_change=estimate.get('estimate_change'),
                estimate_time=estimate.get('estimate_time')
            )
            db.add(estimate_record)

        portfolio_record = db.query(FundPortfolio).filter(FundPortfolio.fund_code == fund_code).first()
        if portfolio_record:
            portfolio_record.stock_codes_json = _json_dumps(portfolio.get('stock_codes', []))
            portfolio_record.bond_codes_json = _json_dumps(portfolio.get('bond_codes', []))
            portfolio_record.stock_codes_new_json = _json_dumps(portfolio.get('stock_codes_new', []))
            portfolio_record.bond_codes_new_json = _json_dumps(portfolio.get('bond_codes_new', []))
        else:
            portfolio_record = FundPortfolio(
                fund_code=fund_code,
                stock_codes_json=_json_dumps(portfolio.get('stock_codes', [])),
                bond_codes_json=_json_dumps(portfolio.get('bond_codes', [])),
                stock_codes_new_json=_json_dumps(portfolio.get('stock_codes_new', [])),
                bond_codes_new_json=_json_dumps(portfolio.get('bond_codes_new', []))
            )
            db.add(portfolio_record)

        extra_record = db.query(FundExtraData).filter(FundExtraData.fund_code == fund_code).first()
        if extra_record:
            extra_record.holder_structure_json = _json_dumps(extra['holder_structure'])
            extra_record.asset_allocation_json = _json_dumps(extra['asset_allocation'])
            extra_record.performance_evaluation_json = _json_dumps(extra['performance_evaluation'])
            extra_record.fund_managers_json = _json_dumps(extra['fund_managers'])
            extra_record.subscription_redemption_json = _json_dumps(extra['subscription_redemption'])
            extra_record.same_type_funds_json = _json_dumps(extra['same_type_funds'])
        else:
            extra_record = FundExtraData(
                fund_code=fund_code,
                holder_structure_json=_json_dumps(extra['holder_structure']),
                asset_allocation_json=_json_dumps(extra['asset_allocation']),
                performance_evaluation_json=_json_dumps(extra['performance_evaluation']),
                fund_managers_json=_json_dumps(extra['fund_managers']),
                subscription_redemption_json=_json_dumps(extra['subscription_redemption']),
                same_type_funds_json=_json_dumps(extra['same_type_funds'])
            )
            db.add(extra_record)

        try:
            db.commit()
        except Exception as e:
            print(f"Error saving to database: {e}")
            db.rollback()

        return jsonify(fund_data)
    
    # 如果API获取失败，尝试从数据库获取缓存数据作为兜底
    cached_data = _build_cached_response(db, fund_code)
    if cached_data:
        return jsonify(cached_data)

    return jsonify({"error": "Fund not found"}), 404

@app.route('/api/fund/<fund_code>/basic', methods=['GET'])
def get_fund_basic(fund_code):
    """获取基金基础信息 实时调用API"""
    if not fund_code:
        return jsonify({"error": "Fund code is required"}), 400
    fund_data = fund_api.get_fund_data(fund_code)
    if fund_data and fund_data.get('basic_info'):
        result = {
            **fund_data.get('basic_info', {}),
            **fund_data.get('performance', {})
        }
        return jsonify(result)

    db = next(get_db())
    basic = db.query(FundBasicInfo).filter(FundBasicInfo.fund_code == fund_code).first()
    if basic:
        basic_info = _json_loads(basic.basic_json, {})
        performance = _json_loads(basic.performance_json, {})
        return jsonify({**basic_info, **performance})

    return jsonify({"error": "Fund basic info not found"}), 404

@app.route('/api/fund/<fund_code>/trend', methods=['GET'])
def get_fund_trend(fund_code):
    """获取基金走势数据 实时调用API"""
    if not fund_code:
        return jsonify({"error": "Fund code is required"}), 400
    
    fund_data = fund_api.get_fund_data(fund_code)
    if fund_data and 'net_worth_trend' in fund_data:
        return jsonify({
            "net_worth_trend": fund_data['net_worth_trend'],
            "accumulated_net_worth": fund_data.get('accumulated_net_worth', [])
        })

    db = next(get_db())
    trend = db.query(FundTrend).filter(FundTrend.fund_code == fund_code).first()
    if trend:
        return jsonify({
            "net_worth_trend": _json_loads(trend.net_worth_trend_json, []),
            "accumulated_net_worth": _json_loads(trend.accumulated_net_worth_json, [])
        })

    return jsonify({"error": "Fund trend data not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)