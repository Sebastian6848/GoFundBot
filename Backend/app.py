from flask import Flask, request, jsonify, g
from flask_cors import CORS
from database import init_db, SessionLocal
from models import (FundBasicInfo, FundTrend, FundEstimate, FundPortfolio, 
                    FundExtraData, FundWatchlist, FundWatchlistGroup, 
                    FundRiskMetrics, FundScreeningRank)
from fund_api import FundAPI
from fund_list_cache import get_fund_list_cache
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_, func
from datetime import datetime, timedelta
import json
import math
import threading
import time
import re
import requests

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
    """
    获取基金详细信息
    
    数据一致性策略：
    - 每次访问都从API获取最新数据
    - 同时更新所有相关表（FundBasicInfo, FundTrend, FundRiskMetrics等）
    - 确保详情、对比、筛选三个模块的数据源统一
    """
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
            # 设置可排序的收益率字段
            try:
                basic_record.return_1y = float(performance.get('1_year_return')) if performance.get('1_year_return') else None
            except (ValueError, TypeError):
                basic_record.return_1y = None
        else:
            # 解析收益率用于排序
            return_1y_val = None
            try:
                return_1y_val = float(performance.get('1_year_return')) if performance.get('1_year_return') else None
            except (ValueError, TypeError):
                pass
            basic_record = FundBasicInfo(
                fund_code=fund_code,
                fund_name=basic_info.get('fund_name') or fund_code,
                fund_type=basic_info.get('fund_type'),
                original_rate=basic_info.get('original_rate'),
                current_rate=basic_info.get('current_rate'),
                min_subscription_amount=basic_info.get('min_subscription_amount'),
                is_hb=basic_info.get('is_hb'),
                return_1y=return_1y_val,
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

        # 【数据一致性】同时更新风险指标，确保详情/对比/筛选数据统一
        net_worth_trend = fund_data.get('net_worth_trend', [])
        if net_worth_trend and len(net_worth_trend) >= 30:
            risk_metrics = calculate_risk_metrics(net_worth_trend)
            if risk_metrics:
                _save_risk_metrics(db, fund_code, risk_metrics)
                # 将风险指标也附加到返回数据中
                fund_data['risk_metrics'] = risk_metrics

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


@app.route('/api/watchlist/refresh-estimates', methods=['POST'])
def refresh_watchlist_estimates():
    """
    批量刷新自选基金的实时估值数据
    此接口专门用于快速获取实时估值，不涉及完整基金数据更新
    """
    db = get_db()
    
    # 获取所有自选基金代码
    watchlist = db.query(FundWatchlist).all()
    if not watchlist:
        return jsonify({'message': 'Watchlist is empty', 'updated': 0})
    
    fund_codes = [item.fund_code for item in watchlist]
    updated_count = 0
    results = []
    
    for fund_code in fund_codes:
        try:
            # 只获取实时估值数据（轻量级请求）
            real_time_url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
            response = requests.get(real_time_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=3)
            
            if response.status_code == 200:
                match = re.search(r"jsonpgz\((.*?)\);", response.text)
                if match:
                    rt_data = json.loads(match.group(1))
                    if rt_data:
                        # 更新数据库中的估值信息
                        estimate_record = db.query(FundEstimate).filter(
                            FundEstimate.fund_code == fund_code
                        ).first()
                        
                        if estimate_record:
                            estimate_record.name = rt_data.get('name')
                            estimate_record.net_worth = rt_data.get('dwjz')
                            estimate_record.net_worth_date = rt_data.get('jzrq')
                            estimate_record.estimate_value = rt_data.get('gsz')
                            estimate_record.estimate_change = rt_data.get('gszzl')
                            estimate_record.estimate_time = rt_data.get('gztime')
                        else:
                            estimate_record = FundEstimate(
                                fund_code=fund_code,
                                name=rt_data.get('name'),
                                net_worth=rt_data.get('dwjz'),
                                net_worth_date=rt_data.get('jzrq'),
                                estimate_value=rt_data.get('gsz'),
                                estimate_change=rt_data.get('gszzl'),
                                estimate_time=rt_data.get('gztime')
                            )
                            db.add(estimate_record)
                        
                        updated_count += 1
                        results.append({
                            'fund_code': fund_code,
                            'estimate_value': rt_data.get('gsz'),
                            'estimate_change': rt_data.get('gszzl'),
                            'estimate_time': rt_data.get('gztime'),
                            'net_worth': rt_data.get('dwjz'),
                            'net_worth_date': rt_data.get('jzrq')
                        })
        except Exception as e:
            # 单个基金失败不影响其他
            print(f"刷新 {fund_code} 估值失败: {e}")
            continue
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    
    return jsonify({
        'message': f'Updated {updated_count} funds',
        'updated': updated_count,
        'total': len(fund_codes),
        'data': results
    })


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
    
    # 过滤首日异常数据（如面值1.0与实际净值100+差异巨大）
    # 这种情况会导致波动率和回撤计算极其离谱
    if len(values) >= 2:
        v0 = values[0]
        v1 = values[1]
        if v0 > 0 and abs((v1 - v0) / v0) > 0.5:
            values.pop(0)
            dates.pop(0)
    
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
    # 重要：对于数据不足的周期，不计算指标（返回None），避免年化放大产生误导性数据
    min_trading_days = {
        '1y': 200,  # 至少200个交易日才计算1年期指标（约10个月）
        '3y': 600,  # 至少600个交易日才计算3年期指标（约2.5年）
    }
    
    for period, months in [('1y', 12), ('3y', 36)]:
        period_values, period_dates = get_period_data(months)
        trading_days = len(period_values)
        
        # 检查数据是否充足
        min_days = min_trading_days.get(period, 30)
        if trading_days < min_days:
            # 数据不足，不计算该周期的指标
            result[f'annual_return_{period}'] = None
            result[f'volatility_{period}'] = None
            result[f'sharpe_ratio_{period}'] = None
            result[f'calmar_ratio_{period}'] = None
            continue
        
        daily_returns = calc_daily_returns(period_values)
        annual_return = calc_annual_return(period_values, trading_days)
        volatility = calc_volatility(daily_returns)
        sharpe = calc_sharpe_ratio(annual_return, volatility)
        
        # 额外检查：如果波动率异常大（>500%），说明数据有问题，放弃该计算结果
        if volatility is not None and volatility > 500:
            result[f'annual_return_{period}'] = None
            result[f'volatility_{period}'] = None
            result[f'sharpe_ratio_{period}'] = None
            result[f'calmar_ratio_{period}'] = None
            continue
        
        result[f'annual_return_{period}'] = annual_return
        result[f'volatility_{period}'] = volatility
        result[f'sharpe_ratio_{period}'] = sharpe
        
        # 计算卡玛比率
        max_dd = result.get(f'max_drawdown_{period}')
        if annual_return is not None and max_dd is not None and max_dd > 0:
            result[f'calmar_ratio_{period}'] = round(annual_return / max_dd, 2)
        else:
            result[f'calmar_ratio_{period}'] = None
    
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
    
    数据来源（统一）：
    - 基本信息、业绩: FundBasicInfo
    - 走势数据: FundTrend
    - 扩展数据: FundExtraData
    - 风险指标: FundRiskMetrics
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

                # 额外检查：如果波动率异常大（>1000%），说明之前计算时受到了脏数据影响，需要重算
                if risk_data_valid and risk_record.volatility_1y and risk_record.volatility_1y > 1000:
                    risk_data_valid = False
                
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
                        'calmar_ratio_1y': risk_record.calmar_ratio_1y,
                        'calmar_ratio_3y': risk_record.calmar_ratio_3y,
                    }
                else:
                    # 风险指标缺失，从缓存的净值数据计算
                    net_worth_trend = data.get('net_worth_trend', [])
                    risk_metrics = calculate_risk_metrics(net_worth_trend)
                    
                    if risk_metrics:
                        # 保存到 FundRiskMetrics
                        _save_risk_metrics(db, fund_code, risk_metrics)
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
                            'calmar_ratio_1y': risk_record.calmar_ratio_1y,
                            'calmar_ratio_3y': risk_record.calmar_ratio_3y,
                        }
                    else:
                        net_worth_trend = data.get('net_worth_trend', [])
                        risk_metrics = calculate_risk_metrics(net_worth_trend)
                        if risk_metrics:
                            _save_risk_metrics(db, fund_code, risk_metrics)
                            db.commit()
                        data['risk_metrics'] = risk_metrics or {}
                    data['data_source'] = 'stale_cache'
                    return jsonify(data)
            return jsonify({'error': 'Failed to fetch fund data'}), 500
        
        # 计算风险指标
        net_worth_trend = api_data.get('net_worth_trend', [])
        risk_metrics = calculate_risk_metrics(net_worth_trend)
        
        # 保存到数据库（所有相关表）
        _save_fund_data_to_db(db, fund_code, api_data)
        if risk_metrics:
            _save_risk_metrics(db, fund_code, risk_metrics)
        db.commit()
        
        # 返回数据
        api_data['risk_metrics'] = risk_metrics or {}
        api_data['data_source'] = 'api'
        return jsonify(api_data)
        
    except Exception as e:
        print(f"Error fetching fund compare data: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500


def _save_risk_metrics(db: Session, fund_code: str, risk_metrics: dict):
    """保存风险指标到 FundRiskMetrics 表"""
    if not risk_metrics:
        return
    
    risk_record = db.query(FundRiskMetrics).filter(FundRiskMetrics.fund_code == fund_code).first()
    
    if risk_record:
        for key, value in risk_metrics.items():
            if hasattr(risk_record, key):
                setattr(risk_record, key, value)
        risk_record.updated_time = datetime.now()
    else:
        risk_record = FundRiskMetrics(
            fund_code=fund_code,
            **{k: v for k, v in risk_metrics.items() if hasattr(FundRiskMetrics, k)}
        )
        db.add(risk_record)


def _save_fund_data_to_db(db: Session, fund_code: str, data: dict):
    """保存基金数据到数据库"""
    try:
        # 保存基本信息
        basic_info = data.get('basic_info', {})
        performance = data.get('performance', {})
        # 解析收益率用于排序
        return_1y_val = None
        try:
            return_1y_val = float(performance.get('1_year_return')) if performance.get('1_year_return') else None
        except (ValueError, TypeError):
            pass
        
        basic_record = db.query(FundBasicInfo).filter(FundBasicInfo.fund_code == fund_code).first()
        if basic_record:
            basic_record.fund_name = basic_info.get('fund_name', '')
            basic_record.fund_type = basic_info.get('fund_type', '')
            basic_record.return_1y = return_1y_val
            basic_record.basic_json = _json_dumps(basic_info)
            basic_record.performance_json = _json_dumps(performance)
            basic_record.updated_time = datetime.now()
        else:
            basic_record = FundBasicInfo(
                fund_code=fund_code,
                fund_name=basic_info.get('fund_name', ''),
                fund_type=basic_info.get('fund_type', ''),
                return_1y=return_1y_val,
                basic_json=_json_dumps(basic_info),
                performance_json=_json_dumps(performance)
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


# ==================== 基金筛选功能 ====================

# 全局变量：批量更新状态
screening_update_status = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current_fund': '',
    'success_count': 0,
    'fail_count': 0,
    'start_time': None,
    'message': ''
}


def calculate_calmar_ratio(annual_return, max_drawdown):
    """计算卡玛比率"""
    if max_drawdown is None or max_drawdown == 0 or annual_return is None:
        return None
    return round(annual_return / max_drawdown, 2)


def check_4433_rule(rank_1y, rank_2y, rank_3y, rank_5y, rank_6m, rank_3m):
    """
    检查是否符合4433法则
    4433法则：
    - 近1年、2年、3年、5年排名在同类前1/4 (25%)
    - 近6个月、3个月排名在前1/3 (33.33%)
    注意：这里的排名应该是同类型基金中的排名百分位
    """
    # 长期排名：1年必须有，2年3年至少有一个
    if rank_1y is None or rank_1y > 25:
        return False
    
    # 检查2年和3年排名（如果有数据）
    long_term_available = [r for r in [rank_2y, rank_3y] if r is not None]
    if long_term_available:
        for rank in long_term_available:
            if rank > 25:
                return False
    
    # 如果有5年数据，也需要在前25%
    if rank_5y is not None and rank_5y > 25:
        return False
    
    # 短期排名：6个月和3个月都必须在前33.33%
    if rank_6m is None or rank_6m > 33.33:
        return False
    if rank_3m is None or rank_3m > 33.33:
        return False
    
    return True


# ==================== 基金筛选功能 ====================

def check_4433_rule(rank_1y, rank_2y, rank_3y, rank_5y, rank_6m, rank_3m):
    """
    检查是否符合4433法则
    4433法则：
    - 近1年、2年、3年排名在同类前1/4 (25%)
    - 近6个月、3个月排名在前1/3 (33.33%)
    """
    # 长期排名：1年必须有，2年3年至少有一个
    if rank_1y is None or rank_1y > 25:
        return False
    
    # 检查2年和3年排名（如果有数据）
    long_term_available = [r for r in [rank_2y, rank_3y] if r is not None]
    if long_term_available:
        for rank in long_term_available:
            if rank > 25:
                return False
    
    # 如果有5年数据，也需要在前25%
    if rank_5y is not None and rank_5y > 25:
        return False
    
    # 短期排名：6个月和3个月都必须在前33.33%
    if rank_6m is None or rank_6m > 33.33:
        return False
    if rank_3m is None or rank_3m > 33.33:
        return False
    
    return True


def calculate_same_type_rankings(db):
    """
    计算同类型基金的排名百分位
    基于 FundBasicInfo 中的收益数据计算排名，保存到 FundScreeningRank
    """
    # 获取所有有效的基金类型
    fund_types = db.query(FundBasicInfo.fund_type).filter(
        FundBasicInfo.fund_type.isnot(None),
        FundBasicInfo.fund_type != ''
    ).distinct().all()
    
    fund_types = [ft[0] for ft in fund_types]
    print(f"[同类排名] 发现 {len(fund_types)} 种基金类型")
    
    for fund_type in fund_types:
        # 获取该类型的所有基金（包含业绩数据）
        funds = db.query(FundBasicInfo).filter(
            FundBasicInfo.fund_type == fund_type,
            FundBasicInfo.performance_json.isnot(None)
        ).all()
        
        if len(funds) < 2:
            continue
        
        print(f"[同类排名] 处理 {fund_type}: {len(funds)} 只基金")
        
        # 解析业绩数据
        fund_performances = []
        for fund in funds:
            perf = _json_loads(fund.performance_json, {})
            fund_performances.append({
                'fund_code': fund.fund_code,
                'return_1m': perf.get('1_month_return'),
                'return_3m': perf.get('3_month_return'),
                'return_6m': perf.get('6_month_return'),
                'return_1y': perf.get('1_year_return'),
                'return_2y': perf.get('2_year_return'),
                'return_3y': perf.get('3_year_return'),
            })
        
        # 为每个时间段计算排名
        periods = [
            ('return_1m', 'rank_pct_1m'),
            ('return_3m', 'rank_pct_3m'),
            ('return_6m', 'rank_pct_6m'),
            ('return_1y', 'rank_pct_1y'),
            ('return_2y', 'rank_pct_2y'),
            ('return_3y', 'rank_pct_3y'),
        ]
        
        # 为每只基金创建或更新排名记录
        fund_ranks = {}  # fund_code -> rank data
        for fp in fund_performances:
            fund_ranks[fp['fund_code']] = {}
        
        for return_field, rank_field in periods:
            # 获取有该时段收益数据的基金
            # 重要：排除收益率为 0、"0.00"、None 的基金
            # 这些通常是成立时间不足导致的缺失数据，而非真实的0%收益
            def is_valid_return(val):
                if val is None:
                    return False
                try:
                    num_val = float(val)
                    # 真实0%收益极其罕见，0值通常表示数据缺失
                    # 允许一个很小的误差范围（如 -0.01% ~ 0.01%）视为可能的真实数据
                    if abs(num_val) < 0.01:
                        return False
                    return True
                except (ValueError, TypeError):
                    return False
            
            funds_with_data = [(fp['fund_code'], float(fp[return_field])) for fp in fund_performances 
                               if is_valid_return(fp[return_field])]
            
            if len(funds_with_data) < 2:
                continue
            
            # 按收益率降序排序（收益高排名靠前）
            funds_with_data.sort(key=lambda x: x[1], reverse=True)
            total = len(funds_with_data)
            
            # 计算每只基金的排名百分位
            for rank_idx, (fund_code, _) in enumerate(funds_with_data, 1):
                rank_pct = round((rank_idx / total) * 100, 2)
                fund_ranks[fund_code][rank_field] = rank_pct
        
        # 更新数据库
        for fund_code, ranks in fund_ranks.items():
            rank_record = db.query(FundScreeningRank).filter(
                FundScreeningRank.fund_code == fund_code
            ).first()
            
            if not rank_record:
                rank_record = FundScreeningRank(fund_code=fund_code)
                db.add(rank_record)
            
            for field, value in ranks.items():
                setattr(rank_record, field, value)
            
            # 计算4433法则
            pass_4433 = check_4433_rule(
                ranks.get('rank_pct_1y'),
                ranks.get('rank_pct_2y'),
                ranks.get('rank_pct_3y'),
                None,
                ranks.get('rank_pct_6m'),
                ranks.get('rank_pct_3m')
            )
            rank_record.pass_4433 = 1 if pass_4433 else 0
            rank_record.updated_time = datetime.now()
    
    db.commit()
    print("[同类排名] 同类型排名计算完成")


# 全局变量：批量更新状态
screening_update_status = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current_fund': '',
    'success_count': 0,
    'fail_count': 0,
    'start_time': None,
    'message': ''
}
screening_stop_flag = False


def update_single_fund_data(fund_code, db):
    """
    更新单只基金的完整数据（简化版）
    直接获取详情数据，更新所有相关表
    """
    try:
        # 获取完整的基金数据
        fund_data = fund_api.get_fund_data(fund_code)
        if not fund_data:
            return False
        
        # 保存到所有相关表
        _save_fund_data_to_db(db, fund_code, fund_data)
        
        # 计算并保存风险指标
        net_worth_trend = fund_data.get('net_worth_trend', [])
        if net_worth_trend and len(net_worth_trend) >= 30:
            risk_metrics = calculate_risk_metrics(net_worth_trend)
            if risk_metrics:
                _save_risk_metrics(db, fund_code, risk_metrics)
        
        return True
    except Exception as e:
        print(f"Error updating data for {fund_code}: {e}")
        return False


def batch_update_fund_data(fund_types=None, limit=None):
    """
    批量更新基金数据（简化版）
    直接获取每只基金的完整详情数据
    """
    global screening_update_status, screening_stop_flag
    
    if screening_update_status['running']:
        return {'error': '更新任务正在进行中'}
    
    screening_update_status['running'] = True
    screening_update_status['start_time'] = datetime.now()
    screening_update_status['message'] = '正在获取基金列表...'
    screening_stop_flag = False
    
    try:
        # 获取基金列表
        fund_list = fund_list_cache.fund_list
        
        # 按类型筛选
        if fund_types:
            fund_list = [f for f in fund_list if any(t in f.get('TYPE', '') for t in fund_types)]
        
        # 限制数量
        if limit:
            fund_list = fund_list[:limit]
        
        screening_update_status['total'] = len(fund_list)
        screening_update_status['progress'] = 0
        screening_update_status['success_count'] = 0
        screening_update_status['fail_count'] = 0
        
        db = SessionLocal()
        
        for i, fund in enumerate(fund_list):
            # 检查停止标志
            if screening_stop_flag:
                screening_update_status['message'] = f"已手动停止。成功: {screening_update_status['success_count']}, 失败: {screening_update_status['fail_count']}"
                break
            
            fund_code = fund.get('CODE', '')
            screening_update_status['progress'] = i + 1
            screening_update_status['current_fund'] = f"{fund_code} - {fund.get('NAME', '')}"
            screening_update_status['message'] = f"正在处理: {screening_update_status['current_fund']}"
            
            if update_single_fund_data(fund_code, db):
                screening_update_status['success_count'] += 1
            else:
                screening_update_status['fail_count'] += 1
            
            # 每10只基金提交一次
            if (i + 1) % 10 == 0:
                db.commit()
            
            # 添加延迟，避免请求过于频繁
            time.sleep(0.3)
        
        db.commit()
        
        if not screening_stop_flag:
            # 计算同类型排名
            screening_update_status['message'] = '正在计算同类型排名...'
            calculate_same_type_rankings(db)
            screening_update_status['message'] = f"更新完成！成功: {screening_update_status['success_count']}, 失败: {screening_update_status['fail_count']}"
        
        db.close()
        
    except Exception as e:
        screening_update_status['message'] = f"更新失败: {str(e)}"
    finally:
        screening_update_status['running'] = False
    
    return {
        'success': True,
        'total': screening_update_status['total'],
        'success_count': screening_update_status['success_count'],
        'fail_count': screening_update_status['fail_count']
    }


@app.route('/api/screening/status', methods=['GET'])
def get_screening_status():
    """获取筛选数据库状态"""
    db = get_db()
    
    # 统计各表数量
    basic_count = db.query(FundBasicInfo).count()
    risk_count = db.query(FundRiskMetrics).filter(
        FundRiskMetrics.sharpe_ratio_1y.isnot(None)
    ).count()
    rank_count = db.query(FundScreeningRank).count()
    pass_4433_count = db.query(FundScreeningRank).filter(
        FundScreeningRank.pass_4433 == 1
    ).count()
    
    # 获取最新更新时间
    latest = db.query(FundBasicInfo).order_by(
        desc(FundBasicInfo.updated_time)
    ).first()
    latest_update = latest.updated_time.isoformat() if latest and latest.updated_time else None
    
    # 获取各类型数量
    type_counts = {}
    types = db.query(FundBasicInfo.fund_type, func.count(FundBasicInfo.fund_code)).group_by(
        FundBasicInfo.fund_type
    ).all()
    for t, c in types:
        if t:
            type_counts[t] = c
    
    return jsonify({
        'basic_count': basic_count,
        'risk_metrics_count': risk_count,
        'ranking_count': rank_count,
        'pass_4433_count': pass_4433_count,
        'latest_update': latest_update,
        'type_counts': type_counts,
        'update_status': {
            'running': screening_update_status['running'],
            'progress': screening_update_status['progress'],
            'total': screening_update_status['total'],
            'current_fund': screening_update_status['current_fund'],
            'message': screening_update_status['message']
        }
    })


@app.route('/api/screening/update', methods=['POST'])
def start_screening_update():
    """启动基金数据批量更新"""
    data = request.get_json() or {}
    fund_types = data.get('fund_types', ['混合型-偏股', '混合型-灵活', '股票型'])
    limit = data.get('limit')  # 可选：限制更新数量（测试用）
    
    if screening_update_status['running']:
        return jsonify({
            'error': '更新任务正在进行中',
            'status': screening_update_status
        }), 409
    
    # 在后台线程执行更新
    thread = threading.Thread(
        target=batch_update_fund_data, 
        args=(fund_types, limit)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': '更新任务已启动',
        'fund_types': fund_types,
        'limit': limit
    })


@app.route('/api/screening/stop', methods=['POST'])
def stop_screening_update():
    """停止基金数据更新"""
    global screening_stop_flag
    screening_stop_flag = True
    return jsonify({'message': '已发送停止信号'})


@app.route('/api/screening/recalculate-rankings', methods=['POST'])
def recalculate_rankings():
    """重新计算同类型排名和4433法则标记"""
    db = get_db()
    try:
        calculate_same_type_rankings(db)
        
        # 统计结果
        stats = db.query(
            FundBasicInfo.fund_type,
            func.count(FundScreeningRank.fund_code).label('total'),
            func.sum(FundScreeningRank.pass_4433).label('pass_count')
        ).join(
            FundScreeningRank, FundBasicInfo.fund_code == FundScreeningRank.fund_code
        ).group_by(FundBasicInfo.fund_type).all()
        
        type_stats = {}
        for fund_type, total, pass_count in stats:
            if fund_type:
                type_stats[fund_type] = {
                    'total': total,
                    'pass_4433': pass_count or 0,
                    'pass_rate': round((pass_count or 0) / total * 100, 2) if total > 0 else 0
                }
        
        return jsonify({
            'success': True,
            'message': '同类型排名计算完成',
            'stats': type_stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/screening/available-types', methods=['POST'])
def get_available_fund_types():
    """获取符合当前筛选条件的所有基金类型（用于快速筛选）"""
    data = request.get_json() or {}
    strategy = data.get('strategy')
    filters = data.get('filters', {})
    
    db = get_db()
    
    # 基础查询
    query = db.query(FundBasicInfo.fund_type).distinct()
    
    # 关联排名表（用于4433筛选）
    if strategy == '4433':
        query = query.join(
            FundScreeningRank, FundBasicInfo.fund_code == FundScreeningRank.fund_code
        ).filter(FundScreeningRank.pass_4433 == 1)
    
    # 关联风险指标表（用于其他策略）
    if strategy in ['high_sharpe', 'low_volatility', 'anti_fragile']:
        query = query.join(
            FundRiskMetrics, FundBasicInfo.fund_code == FundRiskMetrics.fund_code
        )
        
        if strategy == 'high_sharpe':
            query = query.filter(
                FundRiskMetrics.sharpe_ratio_1y > 2,
                FundRiskMetrics.volatility_1y < 25
            )
        elif strategy == 'low_volatility':
            query = query.filter(
                FundRiskMetrics.volatility_1y < 15,
                FundRiskMetrics.max_drawdown_1y < 15
            )
        elif strategy == 'anti_fragile':
            query = query.filter(
                FundRiskMetrics.max_drawdown_1y < 20,
                FundRiskMetrics.annual_return_1y > 0
            )
    
    # 应用自定义类型筛选
    if filters.get('fund_types'):
        type_conditions = []
        for t in filters['fund_types']:
            type_conditions.append(FundBasicInfo.fund_type.like(f'%{t}%'))
        if type_conditions:
            query = query.filter(or_(*type_conditions))
    
    # 获取所有符合条件的类型
    result = query.filter(FundBasicInfo.fund_type != None).all()
    types = sorted([r[0] for r in result if r[0]])
    
    return jsonify({'types': types})


@app.route('/api/screening/query', methods=['POST'])
def query_screening_funds():
    """
    高级基金筛选查询（使用 JOIN 关联查询）
    数据来源：FundBasicInfo + FundRiskMetrics + FundScreeningRank
    """
    data = request.get_json() or {}
    
    # 筛选条件
    filters = data.get('filters', {})
    
    # 排序
    sort_by = data.get('sort_by', 'sharpe_ratio_1y')
    sort_order = data.get('sort_order', 'desc')
    
    # 分页
    page = data.get('page', 1)
    page_size = data.get('page_size', 20)
    
    # 预设策略
    strategy = data.get('strategy')
    
    db = get_db()
    
    # 基础查询：JOIN 三个表
    query = db.query(
        FundBasicInfo,
        FundRiskMetrics,
        FundScreeningRank
    ).outerjoin(
        FundRiskMetrics, FundBasicInfo.fund_code == FundRiskMetrics.fund_code
    ).outerjoin(
        FundScreeningRank, FundBasicInfo.fund_code == FundScreeningRank.fund_code
    )
    
    # 应用预设策略
    if strategy == '4433':
        query = query.filter(FundScreeningRank.pass_4433 == 1)
    
    elif strategy == 'high_sharpe':
        query = query.filter(
            FundRiskMetrics.sharpe_ratio_1y > 2,
            FundRiskMetrics.volatility_1y < 25
        )
    
    elif strategy == 'low_volatility':
        query = query.filter(
            FundRiskMetrics.volatility_1y < 15,
            FundRiskMetrics.max_drawdown_1y < 15
        )
    
    elif strategy == 'anti_fragile':
        query = query.filter(
            FundRiskMetrics.max_drawdown_1y < 20,
            FundRiskMetrics.annual_return_1y > 0
        )
    
    # 应用自定义筛选条件
    if filters.get('fund_types'):
        type_conditions = []
        for t in filters['fund_types']:
            type_conditions.append(FundBasicInfo.fund_type.like(f'%{t}%'))
        if type_conditions:
            query = query.filter(or_(*type_conditions))
    
    # 快速类型筛选（精确匹配）
    if filters.get('quick_fund_type'):
        query = query.filter(FundBasicInfo.fund_type == filters['quick_fund_type'])
    
    # 风险指标筛选
    if filters.get('sharpe_min') is not None:
        query = query.filter(FundRiskMetrics.sharpe_ratio_1y >= filters['sharpe_min'])
    
    if filters.get('volatility_max') is not None:
        query = query.filter(FundRiskMetrics.volatility_1y <= filters['volatility_max'])
    
    if filters.get('max_drawdown_max') is not None:
        query = query.filter(FundRiskMetrics.max_drawdown_1y <= filters['max_drawdown_max'])
    
    if filters.get('calmar_min') is not None:
        query = query.filter(FundRiskMetrics.calmar_ratio_1y >= filters['calmar_min'])
    
    # 排名筛选
    if filters.get('rank_1y_max') is not None:
        query = query.filter(FundScreeningRank.rank_pct_1y <= filters['rank_1y_max'])
    if filters.get('rank_3m_max') is not None:
        query = query.filter(FundScreeningRank.rank_pct_3m <= filters['rank_3m_max'])
    
    # 排序（根据排序字段选择对应的表）
    sort_map = {
        'sharpe_ratio_1y': FundRiskMetrics.sharpe_ratio_1y,
        'sharpe_ratio_3y': FundRiskMetrics.sharpe_ratio_3y,
        'return_1y': FundBasicInfo.return_1y,
        'volatility_1y': FundRiskMetrics.volatility_1y,
        'max_drawdown_1y': FundRiskMetrics.max_drawdown_1y,
        'calmar_ratio_1y': FundRiskMetrics.calmar_ratio_1y,
        'rank_pct_1y': FundScreeningRank.rank_pct_1y,
        'rank_pct_3m': FundScreeningRank.rank_pct_3m,
        'fund_name': FundBasicInfo.fund_name,
        'updated_time': FundBasicInfo.updated_time,
    }
    
    sort_column = sort_map.get(sort_by, FundRiskMetrics.sharpe_ratio_1y)
    if sort_order == 'desc':
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # 计算总数
    total_count = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()
    
    # 构建返回数据
    fund_list = []
    
    # 脏数据自动清理标记（不立即清理，而是返回NULL，防止展示离谱数据）
    # 如果用户需要修复，可以点击“更新数据”
    for basic, risk, rank in results:
        # 解析业绩数据
        perf = _json_loads(basic.performance_json, {}) if basic else {}
        
        # 脏数据检测：如果波动率 > 1000%，视为无效数据
        is_dirty_risk = risk and risk.volatility_1y and risk.volatility_1y > 1000
        
        fund_list.append({
            'fund_code': basic.fund_code if basic else None,
            'fund_name': basic.fund_name if basic else None,
            'fund_type': basic.fund_type if basic else None,
            # 业绩数据（来自 FundBasicInfo.performance_json）
            'return_1m': perf.get('1_month_return'),
            'return_3m': perf.get('3_month_return'),
            'return_6m': perf.get('6_month_return'),
            # 如果近1年收益率为 "0.00" 且实际上可能是空数据，则转为 None 或 "--"
            'return_1y': perf.get('1_year_return') if perf.get('1_year_return') not in ['0.00', 0.0, 0, ''] else None,
            'return_3y': perf.get('3_year_return') if perf.get('3_year_return') not in ['0.00', 0.0, 0, ''] else None,
            # 风险指标（来自 FundRiskMetrics），如果脏数据则隐藏
            'max_drawdown_1y': (risk.max_drawdown_1y if risk else None) if not is_dirty_risk else None,
            'max_drawdown_3y': (risk.max_drawdown_3y if risk else None) if not is_dirty_risk else None,
            'volatility_1y': (risk.volatility_1y if risk else None) if not is_dirty_risk else None,
            'volatility_3y': (risk.volatility_3y if risk else None) if not is_dirty_risk else None,
            'sharpe_ratio_1y': (risk.sharpe_ratio_1y if risk else None) if not is_dirty_risk else None,
            'sharpe_ratio_3y': (risk.sharpe_ratio_3y if risk else None) if not is_dirty_risk else None,
            'calmar_ratio_1y': (risk.calmar_ratio_1y if risk else None) if not is_dirty_risk else None,
            'calmar_ratio_3y': (risk.calmar_ratio_3y if risk else None) if not is_dirty_risk else None,
            # 排名数据（来自 FundScreeningRank）
            'rank_pct_1m': rank.rank_pct_1m if rank else None,
            'rank_pct_3m': rank.rank_pct_3m if rank else None,
            'rank_pct_6m': rank.rank_pct_6m if rank else None,
            'rank_pct_1y': rank.rank_pct_1y if rank else None,
            'pass_4433': (rank.pass_4433 == 1) if rank else False,
            # 时间戳
            'updated_time': basic.updated_time.isoformat() if basic and basic.updated_time else None
        })
    
    return jsonify({
        'total': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': math.ceil(total_count / page_size) if total_count > 0 else 0,
        'data': fund_list
    })


@app.route('/api/screening/strategies', methods=['GET'])
def get_screening_strategies():
    """获取预设筛选策略列表"""
    strategies = [
        {
            'id': '4433',
            'name': '4433法则',
            'description': '同类型基金中：近1/2/3年排名前25%，近3/6个月排名前33%',
            'tags': ['经典策略', '同类排名', '业绩稳定']
        },
        {
            'id': 'high_sharpe',
            'name': '高夏普比率',
            'description': '夏普比率 > 2，单位风险收益最优',
            'tags': ['风险调整', '收益优化']
        },
        {
            'id': 'low_volatility',
            'name': '低波动策略',
            'description': '波动率 < 15%，最大回撤 < 15%，稳健型',
            'tags': ['低风险', '稳健']
        },
        {
            'id': 'anti_fragile',
            'name': '反脆弱策略',
            'description': '在极端行情中表现稳健的基金',
            'tags': ['抗跌', '极端行情']
        },
        {
            'id': 'high_calmar',
            'name': '高卡玛比率',
            'description': '年化收益/最大回撤比值高，性价比最优',
            'tags': ['风险调整', '性价比']
        }
    ]
    return jsonify({'strategies': strategies})


@app.route('/api/screening/fund/<fund_code>', methods=['GET'])
def get_screening_fund_detail(fund_code):
    """获取单只基金的筛选详情数据（JOIN 查询）"""
    db = get_db()
    
    # JOIN 查询
    result = db.query(
        FundBasicInfo,
        FundRiskMetrics,
        FundScreeningRank,
        FundExtraData
    ).outerjoin(
        FundRiskMetrics, FundBasicInfo.fund_code == FundRiskMetrics.fund_code
    ).outerjoin(
        FundScreeningRank, FundBasicInfo.fund_code == FundScreeningRank.fund_code
    ).outerjoin(
        FundExtraData, FundBasicInfo.fund_code == FundExtraData.fund_code
    ).filter(
        FundBasicInfo.fund_code == fund_code
    ).first()
    
    if not result:
        return jsonify({'error': 'Fund not found'}), 404
    
    basic, risk, rank, extra = result
    perf = _json_loads(basic.performance_json, {})
    
    return jsonify({
        'fund_code': basic.fund_code,
        'fund_name': basic.fund_name,
        'fund_type': basic.fund_type,
        'returns': {
            '1m': perf.get('1_month_return'),
            '3m': perf.get('3_month_return'),
            '6m': perf.get('6_month_return'),
            '1y': perf.get('1_year_return'),
            '2y': perf.get('2_year_return'),
            '3y': perf.get('3_year_return'),
        },
        'risk_metrics': {
            'max_drawdown_1y': risk.max_drawdown_1y if risk else None,
            'max_drawdown_3y': risk.max_drawdown_3y if risk else None,
            'volatility_1y': risk.volatility_1y if risk else None,
            'volatility_3y': risk.volatility_3y if risk else None,
            'sharpe_ratio_1y': risk.sharpe_ratio_1y if risk else None,
            'sharpe_ratio_3y': risk.sharpe_ratio_3y if risk else None,
            'calmar_ratio_1y': risk.calmar_ratio_1y if risk else None,
            'calmar_ratio_3y': risk.calmar_ratio_3y if risk else None
        },
        'rankings': {
            '1m': rank.rank_pct_1m if rank else None,
            '3m': rank.rank_pct_3m if rank else None,
            '6m': rank.rank_pct_6m if rank else None,
            '1y': rank.rank_pct_1y if rank else None,
            '2y': rank.rank_pct_2y if rank else None,
            '3y': rank.rank_pct_3y if rank else None,
        },
        'pass_4433': (rank.pass_4433 == 1) if rank else False,
        'updated_time': basic.updated_time.isoformat() if basic.updated_time else None
    })


@app.route('/api/screening/update-single/<fund_code>', methods=['POST'])
def update_single_fund(fund_code):
    """更新单只基金数据"""
    db = get_db()
    
    success = update_single_fund_data(fund_code, db)
    db.commit()
    
    if success:
        return jsonify({'message': f'Fund {fund_code} updated successfully'})
    else:
        return jsonify({'error': f'Failed to update fund {fund_code}'}), 500


@app.route('/api/fund/<fund_code>/data-versions', methods=['GET'])
def get_fund_data_versions(fund_code):
    """
    获取单只基金各数据源的版本时间
    用于前端检测数据一致性
    """
    db = get_db()
    
    basic = db.query(FundBasicInfo).filter(FundBasicInfo.fund_code == fund_code).first()
    trend = db.query(FundTrend).filter(FundTrend.fund_code == fund_code).first()
    risk = db.query(FundRiskMetrics).filter(FundRiskMetrics.fund_code == fund_code).first()
    rank = db.query(FundScreeningRank).filter(FundScreeningRank.fund_code == fund_code).first()
    
    return jsonify({
        'fund_code': fund_code,
        'basic_info': {
            'exists': basic is not None,
            'updated_time': basic.updated_time.isoformat() if basic and basic.updated_time else None
        },
        'trend': {
            'exists': trend is not None,
            'updated_time': trend.updated_time.isoformat() if trend and trend.updated_time else None
        },
        'risk_metrics': {
            'exists': risk is not None,
            'updated_time': risk.updated_time.isoformat() if risk and risk.updated_time else None,
            'has_valid_data': risk.sharpe_ratio_1y is not None if risk else False
        },
        'screening_rank': {
            'exists': rank is not None,
            'updated_time': rank.updated_time.isoformat() if rank and rank.updated_time else None,
            'pass_4433': (rank.pass_4433 == 1) if rank else None
        }
    })


@app.route('/api/data/stats', methods=['GET'])
def get_data_stats():
    """获取数据库统计信息"""
    db = get_db()
    
    stats = {
        'fund_basic_info': db.query(FundBasicInfo).count(),
        'fund_trend': db.query(FundTrend).count(),
        'fund_risk_metrics': db.query(FundRiskMetrics).filter(
            FundRiskMetrics.sharpe_ratio_1y.isnot(None)
        ).count(),
        'fund_screening_rank': db.query(FundScreeningRank).count(),
        'fund_watchlist': db.query(FundWatchlist).count(),
        'pass_4433_count': db.query(FundScreeningRank).filter(
            FundScreeningRank.pass_4433 == 1
        ).count(),
    }
    
    # 按类型统计
    type_stats = db.query(
        FundBasicInfo.fund_type,
        func.count(FundBasicInfo.fund_code)
    ).group_by(FundBasicInfo.fund_type).all()
    
    stats['by_type'] = {t: c for t, c in type_stats if t}
    
    return jsonify(stats)


# ==================== 基金回测功能 ====================

@app.route('/api/backtest/fixed-investment', methods=['POST'])
def backtest_fixed_investment():
    """
    基金定投回测
    
    请求参数：
    {
        "fund_code": "000001",
        "start_date": "2020-01-01",
        "end_date": "2023-12-31",
        "investment_type": "monthly",  // monthly, weekly, lump_sum
        "amount": 1000,  // 每期投资金额
        "initial_amount": 0, // 初始资金（可选）
        "fee_rate": 0.15,  // 手续费率（百分比）
        "take_profit_rate": 20, // 止盈率（百分比，可选）
        "stop_loss_rate": 10 // 止损率（百分比，可选，正数）
    }
    """
    data = request.get_json()
    
    try:
        fund_code = data.get('fund_code')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        investment_type = data.get('investment_type', 'monthly')
        
        # 处理可能为空的数值输入
        def safe_float(val, default):
            if val is None or val == '':
                return default
            return float(val)

        amount = safe_float(data.get('amount'), 1000)
        initial_amount = safe_float(data.get('initial_amount'), 0)
        fee_rate = safe_float(data.get('fee_rate'), 0.15) / 100
        
        take_profit_rate = data.get('take_profit_rate')
        if take_profit_rate is not None and take_profit_rate != '':
            take_profit_rate = float(take_profit_rate) / 100
        else:
            take_profit_rate = None
            
        stop_loss_rate = data.get('stop_loss_rate')
        if stop_loss_rate is not None and stop_loss_rate != '':
            stop_loss_rate = float(stop_loss_rate) / 100
        else:
            stop_loss_rate = None
    
        if not all([fund_code, start_date, end_date]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        db = get_db()
        
        # 获取净值数据
        trend = db.query(FundTrend).filter(FundTrend.fund_code == fund_code).first()
        if not trend:
            # 尝试从API获取并保存数据
            # 注意：这里需要在引入 update_single_fund_data 之前确保其可用
            # 由于 update_single_fund_data 可能定义在其他地方或需要导入
            # 这里假设它不可用或逻辑复杂，暂时只依赖已有数据
            # 或者如果 update_single_fund_data 是在 fund_api 中封装的方法
            try:
                # 尝试使用 FundAPI 实例的 update 方法，如果存在的话
                # 这里假设直接访问数据库查不到就是没有
                pass 
            except Exception as e:
                print(f"Error auto-updating fund: {e}")

        if not trend:
            return jsonify({'error': f'Fund data not found for code {fund_code}'}), 404
        
        net_worth_data = _json_loads(trend.net_worth_trend_json, [])
        if not net_worth_data:
            return jsonify({'error': 'No net worth data available'}), 404
        
        # 转换日期格式并排序
        nav_dict = {}
        for item in net_worth_data:
            date_str = item.get('date')
            nav = item.get('net_worth')
            # 修改判断逻辑，允许 net_worth 为 0 (虽然少见) 但不能为空
            if date_str and nav is not None:
                try:
                    nav_dict[date_str] = float(nav)
                except (ValueError, TypeError):
                    continue
        
        # 按日期排序
        sorted_dates = sorted(nav_dict.keys())
        
        if not sorted_dates:
             return jsonify({'error': 'Valid net worth data is empty'}), 404

        # 辅助日期解析函数
        def parse_date(date_str):
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unknown date format: {date_str}")

        # 过滤日期范围
        try:
            # 只取日期部分进行比较
            start_dt = parse_date(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = parse_date(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError as e:
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        filtered_dates = []
        for d in sorted_dates:
            try:
                current_dt = datetime.strptime(d, '%Y-%m-%d')
                if start_dt <= current_dt <= end_dt:
                    filtered_dates.append(d)
            except ValueError:
                continue

        if len(filtered_dates) < 2:
            return jsonify({'error': f'Insufficient data in range {start_date} to {end_date}. Found {len(filtered_dates)} records.'}), 400
        
        # 执行回测
        result = _run_backtest(
            nav_dict=nav_dict,
            dates=filtered_dates,
            investment_type=investment_type,
            amount=amount,
            initial_amount=initial_amount,
            fee_rate=fee_rate,
            take_profit_rate=take_profit_rate,
            stop_loss_rate=stop_loss_rate
        )
        
        if 'error' in result:
             return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Backtest execution failed: {str(e)}'}), 500


def _run_backtest(nav_dict, dates, investment_type, amount, initial_amount, fee_rate, take_profit_rate=None, stop_loss_rate=None):
    """
    执行回测计算
    """
    timeline = []
    total_invested = 0
    total_shares = 0
    
    # 确定投资日期
    investment_dates = []
    
    if investment_type == 'lump_sum':
        # 一次性投资：只在第一天
        investment_dates = [dates[0]]
    elif investment_type == 'monthly':
        # 每月定投：每月第一个交易日
        current_month = None
        for date in dates:
            dt = datetime.strptime(date, '%Y-%m-%d')
            month_key = (dt.year, dt.month)
            if month_key != current_month:
                investment_dates.append(date)
                current_month = month_key
    elif investment_type == 'weekly':
        # 每周定投：每周第一个交易日
        current_week = None
        for date in dates:
            dt = datetime.strptime(date, '%Y-%m-%d')
            week_key = (dt.year, dt.isocalendar()[1])
            if week_key != current_week:
                investment_dates.append(date)
                current_week = week_key
    
    # 状态标记
    sold_out = False
    exit_reason = None
    exit_date = None
    cash = 0
    
    # 遍历所有日期，计算持仓
    for i, date in enumerate(dates):
        nav = nav_dict[date]
        
        # 如果已经清仓止盈止损，后续只计算现金价值（假设不重新买入）
        if sold_out:
            timeline.append({
                'date': date,
                'invested': round(total_invested, 2),
                'shares': 0,
                'nav': round(nav, 4),
                'value': round(cash, 2),
                'return': round(cash - total_invested, 2),
                'return_rate': round((cash - total_invested) / total_invested * 100, 2) if total_invested > 0 else 0,
                'is_investment_day': False,
                'status': 'sold',
                'exit_reason': exit_reason
            })
            continue

        # 1. 处理初始资金 (仅第一天)
        if i == 0 and initial_amount > 0:
            actual_amount = initial_amount * (1 - fee_rate)
            shares_bought = actual_amount / nav
            total_shares += shares_bought
            total_invested += initial_amount
            
        # 2. 处理定投
        is_invest_day = False
        if investment_type != 'lump_sum' and date in investment_dates:
            actual_amount = amount * (1 - fee_rate)
            shares_bought = actual_amount / nav
            total_shares += shares_bought
            total_invested += amount
            is_invest_day = True
        elif investment_type == 'lump_sum' and i == 0 and amount > 0:
             # 如果是 lump_sum 且 amount > 0，视为第一天投入
             # 叠加 initial_amount
             actual_amount = amount * (1 - fee_rate)
             shares_bought = actual_amount / nav
             total_shares += shares_bought
             total_invested += amount
             is_invest_day = True
        
        # 计算当前市值
        current_value = total_shares * nav
        total_return = current_value - total_invested
        return_rate = (total_return / total_invested * 100) if total_invested > 0 else 0
        
        # 3. 检查止盈止损
        triggered = False
        if total_invested > 0:
            if take_profit_rate and return_rate >= (take_profit_rate * 100):
                sold_out = True
                exit_reason = 'take_profit'
                triggered = True
            elif stop_loss_rate and return_rate <= -(stop_loss_rate * 100):
                sold_out = True
                exit_reason = 'stop_loss'
                triggered = True
        
        if triggered:
            exit_date = date
            cash = current_value 
            
            timeline.append({
                'date': date,
                'invested': round(total_invested, 2),
                'shares': 0,
                'nav': round(nav, 4),
                'value': round(cash, 2),
                'return': round(cash - total_invested, 2),
                'return_rate': round((cash - total_invested) / total_invested * 100, 2),
                'is_investment_day': is_invest_day,
                'status': 'sold',
                'exit_reason': exit_reason
            })
            continue

        timeline.append({
            'date': date,
            'invested': round(total_invested, 2),
            'shares': round(total_shares, 4),
            'nav': round(nav, 4),
            'value': round(current_value, 2),
            'return': round(total_return, 2),
            'return_rate': round(return_rate, 2),
            'is_investment_day': is_invest_day,
            'status': 'holding'
        })
    
    # 计算汇总指标
    if len(timeline) == 0:
        return {'error': 'No data to backtest'}
    
    final_record = timeline[-1]
    
    # 计算最大回撤
    max_drawdown = 0
    peak_value = 0
    for record in timeline:
        value = record['value']
        if value > peak_value:
            peak_value = value
        if peak_value > 0:
            drawdown = (peak_value - value) / peak_value * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    # 计算年化收益率
    start_date = datetime.strptime(timeline[0]['date'], '%Y-%m-%d')
    end_date = datetime.strptime(timeline[-1]['date'], '%Y-%m-%d')
    days = (end_date - start_date).days
    years = days / 365.25
    
    total_return_rate = final_record['return_rate'] / 100
    annual_return = 0
    if years > 0 and total_return_rate > -1:
        annual_return = (pow(1 + total_return_rate, 1 / years) - 1) * 100
    
    # 计算夏普比率（简化版，假设无风险利率2%）
    returns = []
    for i in range(1, len(timeline)):
        if timeline[i-1]['value'] > 0:
            daily_return = (timeline[i]['value'] - timeline[i-1]['value']) / timeline[i-1]['value']
            returns.append(daily_return)
    
    sharpe_ratio = 0
    if len(returns) > 0:
        mean_return = sum(returns) / len(returns)
        if len(returns) > 1:
            variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = math.sqrt(variance)
            if std_dev > 0:
                # 年化夏普比率
                risk_free_rate = 0.02 / 252  # 日无风险利率
                sharpe_ratio = (mean_return - risk_free_rate) / std_dev * math.sqrt(252)
    
    summary = {
        'total_invested': round(final_record['invested'], 2),
        'final_value': round(final_record['value'], 2),
        'total_return': round(final_record['return'], 2),
        'return_rate': round(final_record['return_rate'], 2),
        'annual_return': round(annual_return, 2),
        'max_drawdown': round(-max_drawdown, 2),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'investment_count': len(investment_dates) + (1 if initial_amount > 0 else 0),
        'days': days,
        'exit_reason': exit_reason,
        'exit_date': exit_date
    }
    
    return {
        'summary': summary,
        'timeline': timeline
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)