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