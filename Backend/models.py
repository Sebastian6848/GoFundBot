from sqlalchemy import Column, String, Float, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

"""
数据库表结构设计说明
====================

核心原则：一份数据只存储一次，通过 JOIN 关联查询

数据表分类：
1. 原始数据表 - 存储从API获取的原始数据
   - FundBasicInfo: 基本信息、业绩数据
   - FundTrend: 净值走势、排名趋势
   - FundExtraData: 持有人结构、资产配置、基金经理
   - FundEstimate: 实时估值
   - FundPortfolio: 持仓信息

2. 计算指标表 - 基于原始数据计算
   - FundRiskMetrics: 风险指标（回撤、波动率、夏普等）

3. 筛选专用表 - 存储同类排名等筛选特有数据
   - FundScreeningRank: 同类排名百分位、4433标记

4. 用户数据表
   - FundWatchlist: 自选基金
   - FundWatchlistGroup: 自选分组

使用方式：
- 基金详情：FundBasicInfo + FundTrend + FundExtraData + FundRiskMetrics
- 基金对比：同上
- 基金筛选：FundBasicInfo + FundRiskMetrics + FundScreeningRank
"""


# ==================== 原始数据表 ====================

class FundBasicInfo(Base):
    """
    基金基础信息表
    数据来源: pingzhongdata.js API
    """
    __tablename__ = 'fund_basic_info'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    fund_name = Column(String(100), nullable=False)
    fund_type = Column(String(50), index=True)      # 基金类型
    original_rate = Column(Float)                    # 原始费率
    current_rate = Column(Float)                     # 当前费率
    min_subscription_amount = Column(String(50))     # 最低申购金额
    is_hb = Column(String(10))                       # 是否货币基金
    return_1y = Column(Float)                        # 近1年收益率（用于排序）
    basic_json = Column(Text)                        # 完整基本信息JSON
    performance_json = Column(Text)                  # 业绩数据JSON (收益率)
    created_time = Column(DateTime, default=datetime.now)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundTrend(Base):
    """
    基金走势数据表
    数据来源: pingzhongdata.js API
    """
    __tablename__ = 'fund_trend'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    net_worth_trend_json = Column(Text)              # 单位净值走势
    accumulated_net_worth_json = Column(Text)        # 累计净值走势
    position_trend_json = Column(Text)               # 仓位变动趋势
    total_return_trend_json = Column(Text)           # 总收益率走势
    ranking_trend_json = Column(Text)                # 同类排名走势
    ranking_percentage_json = Column(Text)           # 排名百分位走势
    scale_fluctuation_json = Column(Text)            # 规模变动数据
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundEstimate(Base):
    """
    基金实时估值表
    数据来源: fundgz.js API
    """
    __tablename__ = 'fund_estimate'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(100))
    net_worth = Column(String(50))          # 最新净值
    net_worth_date = Column(String(50))     # 净值日期
    estimate_value = Column(String(50))     # 估算净值
    estimate_change = Column(String(50))    # 估算涨跌幅
    estimate_time = Column(String(50))      # 估算时间
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundPortfolio(Base):
    """
    基金持仓表
    数据来源: pingzhongdata.js API
    """
    __tablename__ = 'fund_portfolio'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    stock_codes_json = Column(Text)         # 股票持仓
    bond_codes_json = Column(Text)          # 债券持仓
    stock_codes_new_json = Column(Text)     # 最新股票持仓
    bond_codes_new_json = Column(Text)      # 最新债券持仓
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundExtraData(Base):
    """
    基金扩展数据表
    数据来源: pingzhongdata.js API
    """
    __tablename__ = 'fund_extra_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    holder_structure_json = Column(Text)         # 持有人结构
    asset_allocation_json = Column(Text)         # 资产配置
    performance_evaluation_json = Column(Text)   # 业绩评价
    fund_managers_json = Column(Text)            # 基金经理信息
    subscription_redemption_json = Column(Text)  # 申购赎回状态
    same_type_funds_json = Column(Text)          # 同类型基金
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ==================== 计算指标表 ====================

class FundRiskMetrics(Base):
    """
    基金风险指标表
    数据来源: 根据 FundTrend.net_worth_trend 计算
    """
    __tablename__ = 'fund_risk_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    
    # 最大回撤（百分比）
    max_drawdown_3m = Column(Float)     # 近3月
    max_drawdown_6m = Column(Float)     # 近6月
    max_drawdown_1y = Column(Float)     # 近1年
    max_drawdown_3y = Column(Float)     # 近3年
    max_drawdown_all = Column(Float)    # 成立以来
    
    # 夏普比率
    sharpe_ratio_1y = Column(Float)     # 近1年
    sharpe_ratio_3y = Column(Float)     # 近3年
    
    # 年化波动率（百分比）
    volatility_1y = Column(Float)       # 近1年
    volatility_3y = Column(Float)       # 近3年
    
    # 年化收益率（百分比）
    annual_return_1y = Column(Float)    # 近1年
    annual_return_3y = Column(Float)    # 近3年
    
    # 卡玛比率
    calmar_ratio_1y = Column(Float)     # 近1年
    calmar_ratio_3y = Column(Float)     # 近3年
    
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ==================== 筛选专用表 ====================

class FundScreeningRank(Base):
    """
    基金筛选排名表
    只存储筛选功能特有的数据：同类排名百分位、4433标记
    其他数据通过 JOIN 查询 FundBasicInfo、FundRiskMetrics
    """
    __tablename__ = 'fund_screening_rank'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    
    # 同类排名百分位（值越小越好，前10%=10）
    rank_pct_1m = Column(Float)         # 近1月
    rank_pct_3m = Column(Float)         # 近3月
    rank_pct_6m = Column(Float)         # 近6月
    rank_pct_1y = Column(Float)         # 近1年
    rank_pct_2y = Column(Float)         # 近2年
    rank_pct_3y = Column(Float)         # 近3年
    
    # 筛选标记
    pass_4433 = Column(Integer, default=0)  # 是否通过4433法则
    
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ==================== 用户数据表 ====================

class FundWatchlistGroup(Base):
    """自选分组表"""
    __tablename__ = 'fund_watchlist_group'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    sort_order = Column(Integer, default=0)
    created_time = Column(DateTime, default=datetime.now)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundWatchlist(Base):
    """基金自选表"""
    __tablename__ = 'fund_watchlist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, index=True)
    fund_name = Column(String(100), nullable=False)
    fund_type = Column(String(50))
    group_id = Column(Integer, default=None)
    sort_order = Column(Integer, default=0)
    created_time = Column(DateTime, default=datetime.now)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
