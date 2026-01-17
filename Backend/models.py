from sqlalchemy import Column, String, Float, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class FundBasicInfo(Base):
    __tablename__ = 'fund_basic_info'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False)
    fund_name = Column(String(100), nullable=False)
    fund_type = Column(String(50))
    original_rate = Column(Float)
    current_rate = Column(Float)
    min_subscription_amount = Column(String(50))
    is_hb = Column(String(10))
    basic_json = Column(Text)
    performance_json = Column(Text)
    created_time = Column(DateTime, default=datetime.now)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundTrend(Base):
    __tablename__ = 'fund_trend'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False)
    net_worth_trend_json = Column(Text)
    accumulated_net_worth_json = Column(Text)
    position_trend_json = Column(Text)
    total_return_trend_json = Column(Text)
    ranking_trend_json = Column(Text)
    ranking_percentage_json = Column(Text)
    scale_fluctuation_json = Column(Text)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundEstimate(Base):
    __tablename__ = 'fund_estimate'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False)
    name = Column(String(100))
    net_worth = Column(String(50))
    net_worth_date = Column(String(50))
    estimate_value = Column(String(50))
    estimate_change = Column(String(50))
    estimate_time = Column(String(50))
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundPortfolio(Base):
    __tablename__ = 'fund_portfolio'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False)
    stock_codes_json = Column(Text)
    bond_codes_json = Column(Text)
    stock_codes_new_json = Column(Text)
    bond_codes_new_json = Column(Text)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundExtraData(Base):
    __tablename__ = 'fund_extra_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False)
    holder_structure_json = Column(Text)
    asset_allocation_json = Column(Text)
    performance_evaluation_json = Column(Text)
    fund_managers_json = Column(Text)
    subscription_redemption_json = Column(Text)
    same_type_funds_json = Column(Text)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundWatchlistGroup(Base):
    """自选分组表"""
    __tablename__ = 'fund_watchlist_group'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    sort_order = Column(Integer, default=0)  # 分组排序
    created_time = Column(DateTime, default=datetime.now)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundWatchlist(Base):
    """基金自选表 - 存储用户自选的基金列表"""
    __tablename__ = 'fund_watchlist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False)
    fund_name = Column(String(100), nullable=False)
    fund_type = Column(String(50))
    group_id = Column(Integer, default=None)  # 所属分组ID，None表示未分组
    sort_order = Column(Integer, default=0)  # 排序顺序，数字越小越靠前
    created_time = Column(DateTime, default=datetime.now)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundRiskMetrics(Base):
    """基金风险指标表 - 存储计算的夏普比率、最大回撤等"""
    __tablename__ = 'fund_risk_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False)
    # 最大回撤（百分比）
    max_drawdown_3m = Column(Float)  # 近3月
    max_drawdown_6m = Column(Float)  # 近6月
    max_drawdown_1y = Column(Float)  # 近1年
    max_drawdown_3y = Column(Float)  # 近3年
    max_drawdown_all = Column(Float)  # 成立来
    # 夏普比率（年化）
    sharpe_ratio_1y = Column(Float)  # 近1年
    sharpe_ratio_3y = Column(Float)  # 近3年
    # 年化波动率
    volatility_1y = Column(Float)  # 近1年
    volatility_3y = Column(Float)  # 近3年
    # 年化收益率
    annual_return_1y = Column(Float)  # 近1年
    annual_return_3y = Column(Float)  # 近3年
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)