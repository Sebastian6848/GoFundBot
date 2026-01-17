from flask import Flask, request, jsonify, g
from flask_cors import CORS
from database import init_db, SessionLocal
from models import FundBasicInfo, FundTrend, FundEstimate, FundPortfolio, FundExtraData, FundWatchlist, FundWatchlistGroup, FundRiskMetrics
from fund_api import FundAPI
from fund_list_cache import get_fund_list_cache
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import math

app = Flask(__name__)
CORS(app)  # 允许跨域请求

def get_db():
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db

@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

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
    db = get_db() # 获取数据库会话
    
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

    db = get_db()
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

    db = get_db()
    trend = db.query(FundTrend).filter(FundTrend.fund_code == fund_code).first()
    if trend:
        return jsonify({
            "net_worth_trend": _json_loads(trend.net_worth_trend_json, []),
            "accumulated_net_worth": _json_loads(trend.accumulated_net_worth_json, [])
        })

    return jsonify({"error": "Fund trend data not found"}), 404


# ==================== 自选基金 API ====================

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """获取自选基金列表（按分组和排序顺序）"""
    db = get_db()
    
    # 获取所有分组
    groups = db.query(FundWatchlistGroup).order_by(FundWatchlistGroup.sort_order).all()
    
    # 获取所有基金
    watchlist = db.query(FundWatchlist).order_by(FundWatchlist.sort_order).all()
    
    # 构建分组数据
    groups_data = []
    for group in groups:
        groups_data.append({
            'id': group.id,
            'name': group.name,
            'sort_order': group.sort_order
        })
    
    # 构建基金数据
    funds_data = []
    for item in watchlist:
        estimate = db.query(FundEstimate).filter(FundEstimate.fund_code == item.fund_code).first()
        
        fund_data = {
            'fund_code': item.fund_code,
            'fund_name': item.fund_name,
            'fund_type': item.fund_type,
            'group_id': item.group_id,
            'sort_order': item.sort_order,
            'created_time': item.created_time.isoformat() if item.created_time else None,
            'net_worth': estimate.net_worth if estimate else None,
            'net_worth_date': estimate.net_worth_date if estimate else None,
            'estimate_value': estimate.estimate_value if estimate else None,
            'estimate_change': estimate.estimate_change if estimate else None,
            'estimate_time': estimate.estimate_time if estimate else None
        }
        funds_data.append(fund_data)
    
    return jsonify({
        'groups': groups_data,
        'data': funds_data
    })


@app.route('/api/watchlist/<fund_code>', methods=['GET'])
def check_watchlist(fund_code):
    """检查基金是否在自选列表中"""
    db = get_db()
    exists = db.query(FundWatchlist).filter(FundWatchlist.fund_code == fund_code).first() is not None
    return jsonify({'in_watchlist': exists})


@app.route('/api/watchlist', methods=['POST'])
def add_to_watchlist():
    """添加基金到自选列表"""
    data = request.get_json()
    fund_code = data.get('fund_code')
    fund_name = data.get('fund_name', '')
    fund_type = data.get('fund_type', '')
    group_id = data.get('group_id')  # 可选的分组ID
    
    if not fund_code:
        return jsonify({'error': 'Fund code is required'}), 400
    
    db = get_db()
    
    # 检查是否已存在
    existing = db.query(FundWatchlist).filter(FundWatchlist.fund_code == fund_code).first()
    if existing:
        return jsonify({'error': 'Fund already in watchlist', 'fund_code': fund_code}), 409
    
    # 获取当前最大排序值（在同一分组内）
    query = db.query(FundWatchlist)
    if group_id:
        query = query.filter(FundWatchlist.group_id == group_id)
    max_order = query.order_by(FundWatchlist.sort_order.desc()).first()
    new_order = (max_order.sort_order + 1) if max_order else 0
    
    # 创建新记录
    new_item = FundWatchlist(
        fund_code=fund_code,
        fund_name=fund_name,
        fund_type=fund_type,
        group_id=group_id,
        sort_order=new_order
    )
    
    try:
        db.add(new_item)
        db.commit()
        return jsonify({
            'message': 'Fund added to watchlist',
            'fund_code': fund_code,
            'sort_order': new_order
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist/<fund_code>', methods=['DELETE'])
def remove_from_watchlist(fund_code):
    """从自选列表移除基金"""
    db = get_db()
    
    item = db.query(FundWatchlist).filter(FundWatchlist.fund_code == fund_code).first()
    if not item:
        return jsonify({'error': 'Fund not in watchlist'}), 404
    
    try:
        db.delete(item)
        db.commit()
        return jsonify({'message': 'Fund removed from watchlist', 'fund_code': fund_code})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist/batch-delete', methods=['POST'])
def batch_delete_from_watchlist():
    """批量删除自选基金"""
    data = request.get_json()
    fund_codes = data.get('fund_codes', [])
    
    if not fund_codes:
        return jsonify({'error': 'Fund codes are required'}), 400
    
    db = get_db()
    
    try:
        deleted_count = db.query(FundWatchlist).filter(
            FundWatchlist.fund_code.in_(fund_codes)
        ).delete(synchronize_session=False)
        db.commit()
        return jsonify({
            'message': f'Deleted {deleted_count} funds from watchlist',
            'deleted_count': deleted_count
        })
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist/reorder', methods=['PUT'])
def reorder_watchlist():
    """
    更新自选基金排序
    请求体格式: { "order": ["000001", "000002", "000003"], "group_id": 1 }
    数组顺序即为排序顺序，索引值作为 sort_order
    group_id 可选，用于同时更新基金的分组
    """
    data = request.get_json()
    order = data.get('order', [])
    group_id = data.get('group_id')  # 可选，移动到某个分组
    
    if not order:
        return jsonify({'error': 'Order array is required'}), 400
    
    db = get_db()
    
    try:
        for index, fund_code in enumerate(order):
            update_data = {'sort_order': index}
            if group_id is not None:
                update_data['group_id'] = group_id if group_id > 0 else None
            db.query(FundWatchlist).filter(
                FundWatchlist.fund_code == fund_code
            ).update(update_data)
        db.commit()
        return jsonify({'message': 'Watchlist reordered successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== 分组管理 API ====================

@app.route('/api/watchlist/groups', methods=['GET'])
def get_groups():
    """获取所有分组"""
    db = get_db()
    groups = db.query(FundWatchlistGroup).order_by(FundWatchlistGroup.sort_order).all()
    
    result = [{
        'id': g.id,
        'name': g.name,
        'sort_order': g.sort_order
    } for g in groups]
    
    return jsonify({'data': result})


@app.route('/api/watchlist/groups', methods=['POST'])
def create_group():
    """创建新分组"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'Group name is required'}), 400
    
    db = get_db()
    
    # 获取最大排序值
    max_order = db.query(FundWatchlistGroup).order_by(FundWatchlistGroup.sort_order.desc()).first()
    new_order = (max_order.sort_order + 1) if max_order else 0
    
    new_group = FundWatchlistGroup(name=name, sort_order=new_order)
    
    try:
        db.add(new_group)
        db.commit()
        return jsonify({
            'message': 'Group created',
            'group': {
                'id': new_group.id,
                'name': new_group.name,
                'sort_order': new_group.sort_order
            }
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    """更新分组（重命名）"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'Group name is required'}), 400
    
    db = get_db()
    group = db.query(FundWatchlistGroup).filter(FundWatchlistGroup.id == group_id).first()
    
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    try:
        group.name = name
        db.commit()
        return jsonify({'message': 'Group updated', 'group': {'id': group.id, 'name': group.name}})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """删除分组（分组内的基金会变为未分组）"""
    db = get_db()
    group = db.query(FundWatchlistGroup).filter(FundWatchlistGroup.id == group_id).first()
    
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    try:
        # 将该分组的基金设为未分组
        db.query(FundWatchlist).filter(FundWatchlist.group_id == group_id).update({'group_id': None})
        db.delete(group)
        db.commit()
        return jsonify({'message': 'Group deleted'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist/groups/reorder', methods=['PUT'])
def reorder_groups():
    """更新分组排序"""
    data = request.get_json()
    order = data.get('order', [])  # [group_id1, group_id2, ...]
    
    if not order:
        return jsonify({'error': 'Order array is required'}), 400
    
    db = get_db()
    
    try:
        for index, group_id in enumerate(order):
            db.query(FundWatchlistGroup).filter(
                FundWatchlistGroup.id == group_id
            ).update({'sort_order': index})
        db.commit()
        return jsonify({'message': 'Groups reordered successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist/move', methods=['PUT'])
def move_fund_to_group():
    """移动基金到指定分组"""
    data = request.get_json()
    fund_code = data.get('fund_code')
    group_id = data.get('group_id')  # None 或 0 表示移到未分组
    
    if not fund_code:
        return jsonify({'error': 'Fund code is required'}), 400
    
    db = get_db()
    fund = db.query(FundWatchlist).filter(FundWatchlist.fund_code == fund_code).first()
    
    if not fund:
        return jsonify({'error': 'Fund not in watchlist'}), 404
    
    try:
        fund.group_id = group_id if group_id and group_id > 0 else None
        db.commit()
        return jsonify({'message': 'Fund moved successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== 风险指标计算 ====================

def calculate_risk_metrics(net_worth_trend):
    """
    计算基金风险指标：最大回撤、夏普比率、年化波动率、年化收益率
    net_worth_trend: [{'date': '2024-01-01', 'net_worth': 1.0}, ...]
    """
    if not net_worth_trend or len(net_worth_trend) < 30:
        return None
    
    # 按日期排序
    sorted_data = sorted(net_worth_trend, key=lambda x: x.get('date', ''))
    
    # 转换为净值数组和日期数组
    dates = []
    values = []
    for item in sorted_data:
        if item.get('net_worth') is not None:
            dates.append(item.get('date'))
            values.append(float(item.get('net_worth')))
    
    if len(values) < 30:
        return None
    
    now = datetime.now()
    
    def get_period_data(months):
        """获取指定时间段的数据"""
        if months == 'all':
            return values, dates
        
        cutoff_date = (now - timedelta(days=months * 30)).strftime('%Y-%m-%d')
        period_values = []
        period_dates = []
        for i, d in enumerate(dates):
            if d >= cutoff_date:
                period_values.append(values[i])
                period_dates.append(d)
        return period_values, period_dates
    
    def calc_max_drawdown(period_values):
        """计算最大回撤"""
        if len(period_values) < 2:
            return None
        
        peak = period_values[0]
        max_dd = 0
        
        for value in period_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_dd:
                max_dd = drawdown
        
        return round(max_dd, 2)
    
    def calc_daily_returns(period_values):
        """计算日收益率序列"""
        if len(period_values) < 2:
            return []
        returns = []
        for i in range(1, len(period_values)):
            if period_values[i-1] != 0:
                ret = (period_values[i] - period_values[i-1]) / period_values[i-1]
                returns.append(ret)
        return returns
    
    def calc_annual_return(period_values, trading_days):
        """计算年化收益率"""
        if len(period_values) < 2 or period_values[0] == 0:
            return None
        total_return = (period_values[-1] - period_values[0]) / period_values[0]
        if trading_days <= 0:
            return None
        annual_return = ((1 + total_return) ** (252 / trading_days) - 1) * 100
        return round(annual_return, 2)
    
    def calc_volatility(daily_returns):
        """计算年化波动率"""
        if len(daily_returns) < 10:
            return None
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        daily_vol = math.sqrt(variance)
        annual_vol = daily_vol * math.sqrt(252) * 100
        return round(annual_vol, 2)
    
    def calc_sharpe_ratio(annual_return, volatility, risk_free_rate=2.0):
        """计算夏普比率，假设无风险利率为2%"""
        if volatility is None or volatility == 0 or annual_return is None:
            return None
        sharpe = (annual_return - risk_free_rate) / volatility
        return round(sharpe, 2)
    
    result = {}
    
    # 计算不同时间段的最大回撤
    for period, months in [('3m', 3), ('6m', 6), ('1y', 12), ('3y', 36), ('all', 'all')]:
        period_values, _ = get_period_data(months)
        result[f'max_drawdown_{period}'] = calc_max_drawdown(period_values)
    
    # 计算1年和3年的年化收益率、波动率、夏普比率
    for period, months in [('1y', 12), ('3y', 36)]:
        period_values, period_dates = get_period_data(months)
        trading_days = len(period_values)
        
        daily_returns = calc_daily_returns(period_values)
        annual_return = calc_annual_return(period_values, trading_days)
        volatility = calc_volatility(daily_returns)
        sharpe = calc_sharpe_ratio(annual_return, volatility)
        
        result[f'annual_return_{period}'] = annual_return
        result[f'volatility_{period}'] = volatility
        result[f'sharpe_ratio_{period}'] = sharpe
    
    return result


def is_data_fresh(updated_time, days=7):
    """检查数据是否在指定天数内"""
    if not updated_time:
        return False
    return (datetime.now() - updated_time).days < days


@app.route('/api/fund/<fund_code>/compare-data', methods=['GET'])
def get_fund_compare_data(fund_code):
    """
    获取基金对比数据，优先使用数据库缓存（1周内）
    返回完整的基金详情数据和风险指标
    """
    db = get_db()
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        # 检查缓存数据是否新鲜（1周内）
        trend_record = db.query(FundTrend).filter(FundTrend.fund_code == fund_code).first()
        risk_record = db.query(FundRiskMetrics).filter(FundRiskMetrics.fund_code == fund_code).first()
        
        use_cache = (
            not force_refresh and 
            trend_record and 
            is_data_fresh(trend_record.updated_time, days=7)
        )
        
        if use_cache:
            # 使用缓存数据
            data = _build_cached_response(db, fund_code)
            if data:
                # 检查风险指标是否存在且新鲜
                risk_data_valid = (
                    risk_record and 
                    is_data_fresh(risk_record.updated_time, days=7) and
                    risk_record.sharpe_ratio_1y is not None
                )
                
                if risk_data_valid:
                    data['risk_metrics'] = {
                        'max_drawdown_3m': risk_record.max_drawdown_3m,
                        'max_drawdown_6m': risk_record.max_drawdown_6m,
                        'max_drawdown_1y': risk_record.max_drawdown_1y,
                        'max_drawdown_3y': risk_record.max_drawdown_3y,
                        'max_drawdown_all': risk_record.max_drawdown_all,
                        'sharpe_ratio_1y': risk_record.sharpe_ratio_1y,
                        'sharpe_ratio_3y': risk_record.sharpe_ratio_3y,
                        'volatility_1y': risk_record.volatility_1y,
                        'volatility_3y': risk_record.volatility_3y,
                        'annual_return_1y': risk_record.annual_return_1y,
                        'annual_return_3y': risk_record.annual_return_3y,
                    }
                else:
                    # 风险指标缺失，从缓存的净值数据计算
                    net_worth_trend = data.get('net_worth_trend', [])
                    risk_metrics = calculate_risk_metrics(net_worth_trend)
                    
                    if risk_metrics:
                        # 保存到数据库
                        if risk_record:
                            for key, value in risk_metrics.items():
                                setattr(risk_record, key, value)
                            risk_record.updated_time = datetime.now()
                        else:
                            risk_record = FundRiskMetrics(
                                fund_code=fund_code,
                                **risk_metrics
                            )
                            db.add(risk_record)
                        db.commit()
                        data['risk_metrics'] = risk_metrics
                    else:
                        data['risk_metrics'] = {}
                
                data['data_source'] = 'cache'
                data['cache_time'] = trend_record.updated_time.isoformat() if trend_record.updated_time else None
                return jsonify(data)
        
        # 从API获取新数据
        api_data = fund_api.get_fund_data(fund_code)
        if not api_data:
            # 如果API失败，尝试返回缓存数据
            if trend_record:
                data = _build_cached_response(db, fund_code)
                if data:
                    # 即使API失败，也尝试计算风险指标
                    if risk_record and risk_record.sharpe_ratio_1y is not None:
                        data['risk_metrics'] = {
                            'max_drawdown_3m': risk_record.max_drawdown_3m,
                            'max_drawdown_6m': risk_record.max_drawdown_6m,
                            'max_drawdown_1y': risk_record.max_drawdown_1y,
                            'max_drawdown_3y': risk_record.max_drawdown_3y,
                            'max_drawdown_all': risk_record.max_drawdown_all,
                            'sharpe_ratio_1y': risk_record.sharpe_ratio_1y,
                            'sharpe_ratio_3y': risk_record.sharpe_ratio_3y,
                            'volatility_1y': risk_record.volatility_1y,
                            'volatility_3y': risk_record.volatility_3y,
                            'annual_return_1y': risk_record.annual_return_1y,
                            'annual_return_3y': risk_record.annual_return_3y,
                        }
                    else:
                        # 从缓存净值数据计算
                        net_worth_trend = data.get('net_worth_trend', [])
                        risk_metrics = calculate_risk_metrics(net_worth_trend)
                        if risk_metrics:
                            # 保存到数据库
                            if risk_record:
                                for key, value in risk_metrics.items():
                                    setattr(risk_record, key, value)
                                risk_record.updated_time = datetime.now()
                            else:
                                risk_record = FundRiskMetrics(fund_code=fund_code, **risk_metrics)
                                db.add(risk_record)
                            db.commit()
                        data['risk_metrics'] = risk_metrics or {}
                    data['data_source'] = 'stale_cache'
                    return jsonify(data)
            return jsonify({'error': 'Failed to fetch fund data'}), 500
        
        # 计算风险指标
        net_worth_trend = api_data.get('net_worth_trend', [])
        risk_metrics = calculate_risk_metrics(net_worth_trend)
        
        # 保存到数据库
        _save_fund_data_to_db(db, fund_code, api_data)
        
        # 保存风险指标
        if risk_metrics:
            if risk_record:
                for key, value in risk_metrics.items():
                    setattr(risk_record, key, value)
                risk_record.updated_time = datetime.now()
            else:
                risk_record = FundRiskMetrics(
                    fund_code=fund_code,
                    **risk_metrics
                )
                db.add(risk_record)
            db.commit()
        
        # 返回数据
        api_data['risk_metrics'] = risk_metrics or {}
        api_data['data_source'] = 'api'
        return jsonify(api_data)
        
    except Exception as e:
        print(f"Error fetching fund compare data: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500



def _save_fund_data_to_db(db: Session, fund_code: str, data: dict):
    """保存基金数据到数据库"""
    try:
        # 保存基本信息
        basic_info = data.get('basic_info', {})
        basic_record = db.query(FundBasicInfo).filter(FundBasicInfo.fund_code == fund_code).first()
        if basic_record:
            basic_record.fund_name = basic_info.get('fund_name', '')
            basic_record.fund_type = basic_info.get('fund_type', '')
            basic_record.basic_json = _json_dumps(basic_info)
            basic_record.performance_json = _json_dumps(data.get('performance', {}))
            basic_record.updated_time = datetime.now()
        else:
            basic_record = FundBasicInfo(
                fund_code=fund_code,
                fund_name=basic_info.get('fund_name', ''),
                fund_type=basic_info.get('fund_type', ''),
                basic_json=_json_dumps(basic_info),
                performance_json=_json_dumps(data.get('performance', {}))
            )
            db.add(basic_record)
        
        # 保存走势数据
        trend_record = db.query(FundTrend).filter(FundTrend.fund_code == fund_code).first()
        if trend_record:
            trend_record.net_worth_trend_json = _json_dumps(data.get('net_worth_trend', []))
            trend_record.accumulated_net_worth_json = _json_dumps(data.get('accumulated_net_worth', []))
            trend_record.position_trend_json = _json_dumps(data.get('position_trend', []))
            trend_record.total_return_trend_json = _json_dumps(data.get('total_return_trend', []))
            trend_record.ranking_trend_json = _json_dumps(data.get('ranking_trend', []))
            trend_record.ranking_percentage_json = _json_dumps(data.get('ranking_percentage', []))
            trend_record.scale_fluctuation_json = _json_dumps(data.get('scale_fluctuation', {}))
            trend_record.updated_time = datetime.now()
        else:
            trend_record = FundTrend(
                fund_code=fund_code,
                net_worth_trend_json=_json_dumps(data.get('net_worth_trend', [])),
                accumulated_net_worth_json=_json_dumps(data.get('accumulated_net_worth', [])),
                position_trend_json=_json_dumps(data.get('position_trend', [])),
                total_return_trend_json=_json_dumps(data.get('total_return_trend', [])),
                ranking_trend_json=_json_dumps(data.get('ranking_trend', [])),
                ranking_percentage_json=_json_dumps(data.get('ranking_percentage', [])),
                scale_fluctuation_json=_json_dumps(data.get('scale_fluctuation', {}))
            )
            db.add(trend_record)
        
        # 保存额外数据
        extra_record = db.query(FundExtraData).filter(FundExtraData.fund_code == fund_code).first()
        if extra_record:
            extra_record.holder_structure_json = _json_dumps(data.get('holder_structure', {}))
            extra_record.asset_allocation_json = _json_dumps(data.get('asset_allocation', {}))
            extra_record.performance_evaluation_json = _json_dumps(data.get('performance_evaluation', {}))
            extra_record.fund_managers_json = _json_dumps(data.get('fund_managers', []))
            extra_record.subscription_redemption_json = _json_dumps(data.get('subscription_redemption', {}))
            extra_record.same_type_funds_json = _json_dumps(data.get('same_type_funds', []))
            extra_record.updated_time = datetime.now()
        else:
            extra_record = FundExtraData(
                fund_code=fund_code,
                holder_structure_json=_json_dumps(data.get('holder_structure', {})),
                asset_allocation_json=_json_dumps(data.get('asset_allocation', {})),
                performance_evaluation_json=_json_dumps(data.get('performance_evaluation', {})),
                fund_managers_json=_json_dumps(data.get('fund_managers', [])),
                subscription_redemption_json=_json_dumps(data.get('subscription_redemption', {})),
                same_type_funds_json=_json_dumps(data.get('same_type_funds', []))
            )
            db.add(extra_record)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving fund data to db: {e}")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)