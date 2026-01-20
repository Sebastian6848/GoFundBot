import sqlite3
import os
import json
import math
from datetime import datetime, timedelta

# Database path
DB_PATH = r'c:\Users\Sebastian\Desktop\GoFundBot\MyBot\Data\funds.db'


def migrate_database():
    """执行数据库迁移"""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Check/Add columns to fund_risk_metrics
        print("Checking fund_risk_metrics table...")
        cursor.execute("PRAGMA table_info(fund_risk_metrics)")
        columns = [row[1] for row in cursor.fetchall()]
        
        columns_to_add = [
            ('calmar_ratio_1y', 'FLOAT'),
            ('calmar_ratio_3y', 'FLOAT'),
            ('annual_return_1y', 'FLOAT'),
            ('annual_return_3y', 'FLOAT')
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in columns:
                print(f"Adding column {col_name} to fund_risk_metrics...")
                cursor.execute(f"ALTER TABLE fund_risk_metrics ADD COLUMN {col_name} {col_type}")
        
        # 2. Check/Create fund_screening_rank table
        print("Checking fund_screening_rank table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fund_screening_rank'")
        if not cursor.fetchone():
            print("Creating fund_screening_rank table...")
            cursor.execute("""
                CREATE TABLE fund_screening_rank (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code VARCHAR(6) NOT NULL UNIQUE,
                    rank_pct_1m FLOAT,
                    rank_pct_3m FLOAT,
                    rank_pct_6m FLOAT,
                    rank_pct_1y FLOAT,
                    rank_pct_2y FLOAT,
                    rank_pct_3y FLOAT,
                    rank_pct_5y FLOAT,
                    pass_4433 INTEGER DEFAULT 0,
                    updated_time DATETIME
                )
            """)
            cursor.execute("CREATE INDEX ix_fund_screening_rank_fund_code ON fund_screening_rank (fund_code)")
        else:
             print("fund_screening_rank table already exists.")

        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


def clean_dirty_data():
    """
    清理脏数据：
    1. 清理波动率 > 500% 的异常数据（通常是数据不足导致的年化放大）
    2. 清理夏普比率绝对值 > 50 的异常数据
    3. 清理基于错误0%收益率计算的指标
    """
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("=" * 60)
        print("开始清理脏数据...")
        print("=" * 60)
        
        # 1. 统计脏数据数量
        cursor.execute("""
            SELECT COUNT(*) FROM fund_risk_metrics 
            WHERE volatility_1y > 500 
               OR volatility_3y > 500 
               OR ABS(sharpe_ratio_1y) > 50
               OR ABS(sharpe_ratio_3y) > 50
        """)
        dirty_count = cursor.fetchone()[0]
        print(f"发现 {dirty_count} 条疑似脏数据")
        
        # 2. 将脏数据的相关字段置为 NULL
        cursor.execute("""
            UPDATE fund_risk_metrics 
            SET 
                volatility_1y = NULL,
                sharpe_ratio_1y = NULL,
                annual_return_1y = NULL,
                calmar_ratio_1y = NULL
            WHERE volatility_1y > 500 OR ABS(sharpe_ratio_1y) > 50
        """)
        print(f"已清理 1年期脏数据")
        
        cursor.execute("""
            UPDATE fund_risk_metrics 
            SET 
                volatility_3y = NULL,
                sharpe_ratio_3y = NULL,
                annual_return_3y = NULL,
                calmar_ratio_3y = NULL
            WHERE volatility_3y > 500 OR ABS(sharpe_ratio_3y) > 50
        """)
        print(f"已清理 3年期脏数据")
        
        conn.commit()
        print("脏数据清理完成！")
        
    except Exception as e:
        print(f"Error during cleaning: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


def recalculate_all_risk_metrics():
    """
    重新计算所有基金的风险指标
    基于 fund_trend 表中的净值数据
    """
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("=" * 60)
        print("开始重新计算风险指标...")
        print("=" * 60)
        
        # 获取所有有净值数据的基金
        cursor.execute("""
            SELECT fund_code, net_worth_trend_json 
            FROM fund_trend 
            WHERE net_worth_trend_json IS NOT NULL
        """)
        funds = cursor.fetchall()
        
        print(f"共有 {len(funds)} 只基金需要计算")
        
        success_count = 0
        skip_count = 0
        
        for i, (fund_code, trend_json) in enumerate(funds, 1):
            if i % 100 == 0:
                print(f"进度: {i}/{len(funds)} ({i*100//len(funds)}%)")
            
            try:
                net_worth_trend = json.loads(trend_json) if trend_json else []
                if not net_worth_trend or len(net_worth_trend) < 30:
                    skip_count += 1
                    continue
                
                # 计算风险指标
                risk_metrics = _calculate_risk_metrics(net_worth_trend)
                if not risk_metrics:
                    skip_count += 1
                    continue
                
                # 更新数据库
                cursor.execute("""
                    INSERT OR REPLACE INTO fund_risk_metrics 
                    (fund_code, max_drawdown_3m, max_drawdown_6m, max_drawdown_1y, max_drawdown_3y, max_drawdown_all,
                     sharpe_ratio_1y, sharpe_ratio_3y, volatility_1y, volatility_3y,
                     annual_return_1y, annual_return_3y, calmar_ratio_1y, calmar_ratio_3y, updated_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fund_code,
                    risk_metrics.get('max_drawdown_3m'),
                    risk_metrics.get('max_drawdown_6m'),
                    risk_metrics.get('max_drawdown_1y'),
                    risk_metrics.get('max_drawdown_3y'),
                    risk_metrics.get('max_drawdown_all'),
                    risk_metrics.get('sharpe_ratio_1y'),
                    risk_metrics.get('sharpe_ratio_3y'),
                    risk_metrics.get('volatility_1y'),
                    risk_metrics.get('volatility_3y'),
                    risk_metrics.get('annual_return_1y'),
                    risk_metrics.get('annual_return_3y'),
                    risk_metrics.get('calmar_ratio_1y'),
                    risk_metrics.get('calmar_ratio_3y'),
                    datetime.now().isoformat()
                ))
                success_count += 1
                
            except Exception as e:
                print(f"Error processing {fund_code}: {e}")
                skip_count += 1
        
        conn.commit()
        print("=" * 60)
        print(f"风险指标计算完成！成功: {success_count}, 跳过: {skip_count}")
        
    except Exception as e:
        print(f"Error during recalculation: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


def recalculate_all_rankings():
    """
    重新计算所有基金的同类型排名百分位和4433法则
    """
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("=" * 60)
        print("开始重新计算同类型排名...")
        print("=" * 60)
        
        # 获取所有基金类型
        cursor.execute("""
            SELECT DISTINCT fund_type FROM fund_basic_info 
            WHERE fund_type IS NOT NULL AND fund_type != ''
        """)
        fund_types = [row[0] for row in cursor.fetchall()]
        
        print(f"发现 {len(fund_types)} 种基金类型")
        
        for fund_type in fund_types:
            # 获取该类型的所有基金
            cursor.execute("""
                SELECT fund_code, performance_json 
                FROM fund_basic_info 
                WHERE fund_type = ? AND performance_json IS NOT NULL
            """, (fund_type,))
            funds = cursor.fetchall()
            
            if len(funds) < 2:
                continue
            
            print(f"处理 {fund_type}: {len(funds)} 只基金")
            
            # 解析业绩数据
            fund_performances = []
            for fund_code, perf_json in funds:
                try:
                    perf = json.loads(perf_json) if perf_json else {}
                    fund_performances.append({
                        'fund_code': fund_code,
                        'return_1m': perf.get('1_month_return'),
                        'return_3m': perf.get('3_month_return'),
                        'return_6m': perf.get('6_month_return'),
                        'return_1y': perf.get('1_year_return'),
                        'return_2y': perf.get('2_year_return'),
                        'return_3y': perf.get('3_year_return'),
                    })
                except:
                    pass
            
            # 计算排名
            periods = [
                ('return_1m', 'rank_pct_1m'),
                ('return_3m', 'rank_pct_3m'),
                ('return_6m', 'rank_pct_6m'),
                ('return_1y', 'rank_pct_1y'),
                ('return_2y', 'rank_pct_2y'),
                ('return_3y', 'rank_pct_3y'),
            ]
            
            fund_ranks = {fp['fund_code']: {} for fp in fund_performances}
            
            for return_field, rank_field in periods:
                # 排除无效数据（None, 0, "0.00" 等）
                def is_valid_return(val):
                    if val is None:
                        return False
                    try:
                        num_val = float(val)
                        if abs(num_val) < 0.01:  # 接近0视为缺失数据
                            return False
                        return True
                    except:
                        return False
                
                funds_with_data = [(fp['fund_code'], float(fp[return_field])) for fp in fund_performances 
                                   if is_valid_return(fp[return_field])]
                
                if len(funds_with_data) < 2:
                    continue
                
                # 按收益率降序排序
                funds_with_data.sort(key=lambda x: x[1], reverse=True)
                total = len(funds_with_data)
                
                # 计算排名百分位
                for rank_idx, (fc, _) in enumerate(funds_with_data, 1):
                    rank_pct = round((rank_idx / total) * 100, 2)
                    fund_ranks[fc][rank_field] = rank_pct
            
            # 更新数据库
            for fund_code, ranks in fund_ranks.items():
                # 计算4433法则
                pass_4433 = _check_4433_rule(
                    ranks.get('rank_pct_1y'),
                    ranks.get('rank_pct_2y'),
                    ranks.get('rank_pct_3y'),
                    None,
                    ranks.get('rank_pct_6m'),
                    ranks.get('rank_pct_3m')
                )
                
                cursor.execute("""
                    INSERT OR REPLACE INTO fund_screening_rank 
                    (fund_code, rank_pct_1m, rank_pct_3m, rank_pct_6m, rank_pct_1y, rank_pct_2y, rank_pct_3y, pass_4433, updated_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fund_code,
                    ranks.get('rank_pct_1m'),
                    ranks.get('rank_pct_3m'),
                    ranks.get('rank_pct_6m'),
                    ranks.get('rank_pct_1y'),
                    ranks.get('rank_pct_2y'),
                    ranks.get('rank_pct_3y'),
                    1 if pass_4433 else 0,
                    datetime.now().isoformat()
                ))
        
        conn.commit()
        
        # 统计结果
        cursor.execute("SELECT COUNT(*) FROM fund_screening_rank WHERE pass_4433 = 1")
        pass_4433_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM fund_screening_rank")
        total_count = cursor.fetchone()[0]
        
        print("=" * 60)
        print(f"排名计算完成！共 {total_count} 只基金，{pass_4433_count} 只通过4433法则")
        
    except Exception as e:
        print(f"Error during ranking calculation: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


def _calculate_risk_metrics(net_worth_trend):
    """计算基金风险指标（独立版本，用于批量计算）"""
    if not net_worth_trend or len(net_worth_trend) < 30:
        return None
    
    # 按日期排序
    sorted_data = sorted(net_worth_trend, key=lambda x: x.get('date', ''))
    
    dates = []
    values = []
    for item in sorted_data:
        if item.get('net_worth') is not None:
            dates.append(item.get('date'))
            values.append(float(item.get('net_worth')))
    
    # 过滤首日异常数据
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
        if len(period_values) < 2:
            return []
        returns = []
        for i in range(1, len(period_values)):
            if period_values[i-1] != 0:
                ret = (period_values[i] - period_values[i-1]) / period_values[i-1]
                returns.append(ret)
        return returns
    
    def calc_annual_return(period_values, trading_days):
        if len(period_values) < 2 or period_values[0] == 0 or trading_days <= 0:
            return None
        total_return = (period_values[-1] - period_values[0]) / period_values[0]
        annual_return = ((1 + total_return) ** (252 / trading_days) - 1) * 100
        return round(annual_return, 2)
    
    def calc_volatility(daily_returns):
        if len(daily_returns) < 10:
            return None
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        daily_vol = math.sqrt(variance)
        annual_vol = daily_vol * math.sqrt(252) * 100
        return round(annual_vol, 2)
    
    def calc_sharpe_ratio(annual_return, volatility, risk_free_rate=2.0):
        if volatility is None or volatility == 0 or annual_return is None:
            return None
        sharpe = (annual_return - risk_free_rate) / volatility
        return round(sharpe, 2)
    
    result = {}
    
    # 计算不同时间段的最大回撤
    for period, months in [('3m', 3), ('6m', 6), ('1y', 12), ('3y', 36), ('all', 'all')]:
        period_values, _ = get_period_data(months)
        result[f'max_drawdown_{period}'] = calc_max_drawdown(period_values)
    
    # 计算1年和3年的指标（需要足够的数据）
    min_trading_days = {'1y': 200, '3y': 600}
    
    for period, months in [('1y', 12), ('3y', 36)]:
        period_values, period_dates = get_period_data(months)
        trading_days = len(period_values)
        
        min_days = min_trading_days.get(period, 30)
        if trading_days < min_days:
            result[f'annual_return_{period}'] = None
            result[f'volatility_{period}'] = None
            result[f'sharpe_ratio_{period}'] = None
            result[f'calmar_ratio_{period}'] = None
            continue
        
        daily_returns = calc_daily_returns(period_values)
        annual_return = calc_annual_return(period_values, trading_days)
        volatility = calc_volatility(daily_returns)
        sharpe = calc_sharpe_ratio(annual_return, volatility)
        
        # 检查异常值
        if volatility is not None and volatility > 500:
            result[f'annual_return_{period}'] = None
            result[f'volatility_{period}'] = None
            result[f'sharpe_ratio_{period}'] = None
            result[f'calmar_ratio_{period}'] = None
            continue
        
        result[f'annual_return_{period}'] = annual_return
        result[f'volatility_{period}'] = volatility
        result[f'sharpe_ratio_{period}'] = sharpe
        
        max_dd = result.get(f'max_drawdown_{period}')
        if annual_return is not None and max_dd is not None and max_dd > 0:
            result[f'calmar_ratio_{period}'] = round(annual_return / max_dd, 2)
        else:
            result[f'calmar_ratio_{period}'] = None
    
    return result


def _check_4433_rule(rank_1y, rank_2y, rank_3y, rank_5y, rank_6m, rank_3m):
    """检查是否符合4433法则"""
    if rank_1y is None or rank_1y > 25:
        return False
    
    long_term_available = [r for r in [rank_2y, rank_3y] if r is not None]
    if long_term_available:
        for rank in long_term_available:
            if rank > 25:
                return False
    
    if rank_5y is not None and rank_5y > 25:
        return False
    
    if rank_6m is None or rank_6m > 33.33:
        return False
    if rank_3m is None or rank_3m > 33.33:
        return False
    
    return True


def print_data_stats():
    """打印数据库统计信息"""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("=" * 60)
        print("数据库统计信息")
        print("=" * 60)
        
        # 各表统计
        tables = [
            ('fund_basic_info', '基础信息'),
            ('fund_trend', '净值走势'),
            ('fund_risk_metrics', '风险指标'),
            ('fund_screening_rank', '排名数据'),
        ]
        
        for table, name in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{name}: {count} 条记录")
        
        # 4433法则通过数
        cursor.execute("SELECT COUNT(*) FROM fund_screening_rank WHERE pass_4433 = 1")
        pass_4433 = cursor.fetchone()[0]
        print(f"通过4433法则: {pass_4433} 只")
        
        # 脏数据统计
        cursor.execute("""
            SELECT COUNT(*) FROM fund_risk_metrics 
            WHERE volatility_1y > 500 OR ABS(sharpe_ratio_1y) > 50
        """)
        dirty_count = cursor.fetchone()[0]
        print(f"疑似脏数据: {dirty_count} 条")
        
        # 有效1年期数据
        cursor.execute("""
            SELECT COUNT(*) FROM fund_risk_metrics 
            WHERE sharpe_ratio_1y IS NOT NULL 
              AND volatility_1y IS NOT NULL 
              AND volatility_1y < 500
        """)
        valid_1y = cursor.fetchone()[0]
        print(f"有效1年期风险指标: {valid_1y} 条")
        
        # 基金类型分布
        print("\n基金类型分布:")
        cursor.execute("""
            SELECT fund_type, COUNT(*) 
            FROM fund_basic_info 
            GROUP BY fund_type 
            ORDER BY COUNT(*) DESC
            LIMIT 15
        """)
        for fund_type, count in cursor.fetchall():
            print(f"  {fund_type or '未知'}: {count}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()


def update_fund_types_from_cache():
    """
    从本地缓存更新所有基金的类型信息
    """
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    # 加载本地基金缓存
    cache_path = os.path.join(os.path.dirname(DB_PATH), 'fund_list_cache.json')
    if not os.path.exists(cache_path):
        print(f"Fund list cache not found at {cache_path}")
        return
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            funds = cache_data.get('funds', [])
            # 构建 fund_code -> fund_type 的映射
            fund_type_map = {f.get('CODE'): f.get('TYPE') for f in funds if f.get('CODE') and f.get('TYPE')}
    except Exception as e:
        print(f"Error loading cache: {e}")
        return
    
    print(f"从缓存中加载了 {len(fund_type_map)} 只基金的类型信息")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("=" * 60)
        print("开始更新基金类型...")
        print("=" * 60)
        
        # 获取所有基金代码
        cursor.execute("SELECT fund_code FROM fund_basic_info")
        db_fund_codes = [row[0] for row in cursor.fetchall()]
        
        updated_count = 0
        for fund_code in db_fund_codes:
            fund_type = fund_type_map.get(fund_code)
            if fund_type:
                cursor.execute(
                    "UPDATE fund_basic_info SET fund_type = ? WHERE fund_code = ?",
                    (fund_type, fund_code)
                )
                updated_count += 1
        
        conn.commit()
        print(f"成功更新了 {updated_count} 只基金的类型信息")
        
        # 显示更新后的类型分布
        print("\n更新后的基金类型分布:")
        cursor.execute("""
            SELECT fund_type, COUNT(*) 
            FROM fund_basic_info 
            GROUP BY fund_type 
            ORDER BY COUNT(*) DESC
            LIMIT 15
        """)
        for fund_type, count in cursor.fetchall():
            print(f"  {fund_type or '未知'}: {count}")
        
    except Exception as e:
        print(f"Error updating fund types: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


def migrate_add_return_1y():
    """添加 return_1y 字段到 fund_basic_info 表并更新现有数据"""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("=" * 60)
        print("添加 return_1y 字段并更新数据...")
        print("=" * 60)
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(fund_basic_info)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'return_1y' not in columns:
            print("添加 return_1y 字段...")
            cursor.execute("ALTER TABLE fund_basic_info ADD COLUMN return_1y FLOAT")
        else:
            print("return_1y 字段已存在")
        
        # 从 performance_json 中提取 1_year_return 并更新 return_1y
        print("更新 return_1y 数据...")
        cursor.execute("SELECT fund_code, performance_json FROM fund_basic_info WHERE performance_json IS NOT NULL")
        rows = cursor.fetchall()
        
        updated = 0
        for fund_code, perf_json in rows:
            try:
                perf = json.loads(perf_json) if perf_json else {}
                return_1y = perf.get('1_year_return')
                if return_1y is not None:
                    try:
                        return_1y_float = float(return_1y)
                        cursor.execute(
                            "UPDATE fund_basic_info SET return_1y = ? WHERE fund_code = ?",
                            (return_1y_float, fund_code)
                        )
                        updated += 1
                    except (ValueError, TypeError):
                        pass
            except json.JSONDecodeError:
                pass
        
        conn.commit()
        print(f"已更新 {updated} 条记录的 return_1y 字段")
        print("迁移完成！")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'migrate':
            migrate_database()
        elif command == 'clean':
            clean_dirty_data()
        elif command == 'recalc-risk':
            recalculate_all_risk_metrics()
        elif command == 'recalc-rank':
            recalculate_all_rankings()
        elif command == 'update-types':
            update_fund_types_from_cache()
        elif command == 'stats':
            print_data_stats()
        elif command == 'all':
            # 执行完整修复流程
            print("开始执行完整数据修复流程...")
            migrate_database()
            clean_dirty_data()
            update_fund_types_from_cache()  # 先更新类型
            recalculate_all_risk_metrics()
            recalculate_all_rankings()
            print_data_stats()
        elif command == 'fix-rank':
            # 仅修复排名（更新类型后重算排名）
            print("开始修复排名数据...")
            update_fund_types_from_cache()
            recalculate_all_rankings()
            print_data_stats()
        elif command == 'add-return':
            # 添加 return_1y 字段
            migrate_add_return_1y()
        else:
            print(f"未知命令: {command}")
            print("可用命令:")
            print("  migrate      - 执行数据库迁移")
            print("  clean        - 清理脏数据")
            print("  recalc-risk  - 重新计算风险指标")
            print("  recalc-rank  - 重新计算排名")
            print("  update-types - 从缓存更新基金类型")
            print("  stats        - 查看数据统计")
            print("  all          - 执行完整修复流程")
            print("  fix-rank     - 修复排名（更新类型+重算排名）")
            print("  add-return   - 添加return_1y字段用于排序")
    else:
        # 默认执行迁移
        migrate_database()
        print("\n提示: 可使用以下命令执行其他操作:")
        print("  python migrate_db.py clean       - 清理脏数据")
        print("  python migrate_db.py recalc-risk - 重新计算风险指标")
        print("  python migrate_db.py recalc-rank - 重新计算排名")
        print("  python migrate_db.py update-types- 从缓存更新基金类型")
        print("  python migrate_db.py stats       - 查看数据统计")
        print("  python migrate_db.py all         - 执行完整修复流程")
        print("  python migrate_db.py fix-rank    - 修复排名数据")
        print("  python migrate_db.py add-return  - 添加return_1y字段")
