import requests
import json
import re
from datetime import datetime

class FundAPI:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def get_fund_basic_info(self, fund_code):
        """
        获取基金综合信息，包括实时估值、基本资料、持仓等
        """
        info = {}
        
        # 1. 获取实时估值信息
        try:
            # 天天基金实时估值接口
            real_time_url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
            response = requests.get(real_time_url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                content = response.text
                # 提取 jsonpgz({...}) 中的 json 部分
                match = re.search(r"jsonpgz\((.*?)\);", content)
                if match:
                    real_time_data = json.loads(match.group(1))
                    info.update(real_time_data)
        except Exception as e:
            print(f"获取实时估值信息失败: {e}")

        # 2. 获取基本资料
        try:
            basic_url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
            response = requests.get(basic_url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                content = response.text
                
                # 基金名称
                if 'name' not in info:
                    name_match = re.search(r'var fS_name\s*=\s*"(.*?)";', content)
                    if name_match:
                        info['name'] = name_match.group(1)
                
                # 现费率
                rate_match = re.search(r'var fund_Rate\s*=\s*"(.*?)";', content)
                if rate_match:
                    info['fund_rate'] = rate_match.group(1)

                # 最小申购金额
                min_match = re.search(r'var fund_minsg\s*=\s*"(.*?)";', content)
                if min_match:
                    info['fund_min_subscription'] = min_match.group(1)
                
                # 前十大持仓
                stock_codes_match = re.search(r'var stockCodes\s*=\s*(\[.*?\]);', content)
                if stock_codes_match:
                    try:
                        codes_raw = json.loads(stock_codes_match.group(1))
                        # 天天基金返回的code有时候带有交易所后缀（如0025580），取前6位
                        info['stock_codes'] = [code[:6] for code in codes_raw]
                    except:
                        info['stock_codes'] = []

                # 基金经理
                manager_match = re.search(r'var Data_currentFundManager\s*=\s*(\[.*?\]);', content, re.DOTALL)
                if manager_match:
                    try:
                        managers = json.loads(manager_match.group(1))
                        info['managers'] = managers
                    except:
                        pass
                        
                # 基金规模
                asset_alloc_match = re.search(r'var Data_assetAllocation\s*=\s*(\{.*?\});', content, re.DOTALL)
                if asset_alloc_match:
                    try:
                        asset_data = json.loads(asset_alloc_match.group(1))
                        net_asset_series = next((s for s in asset_data.get('series', []) if s.get('name') == '净资产'), None)
                        if net_asset_series and net_asset_series.get('data'):
                            info['fund_size'] = net_asset_series['data'][-1]
                    except:
                        info['fund_size'] = None

        except Exception as e:
            print(f"获取基本资料失败: {e}")
            
        return info if info else None
    
    def get_fund_detail(self, fund_code):
        """获取基金详细信息，包括净值走势等"""
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return self._parse_fund_js(response.text, fund_code)
            return None
        except Exception as e:
            print(f"Error fetching detail for {fund_code}: {e}")
            return None
            
    def search_funds(self, keyword):
        """
        搜索基金
        """
        url = "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
        params = {
            'm': 1,
            'key': keyword
        }
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'Datas' in data:
                    # 过滤只保留基金类型的条目 (CATEGORYDESC == '基金')
                    funds = [item for item in data['Datas'] if item.get('CATEGORYDESC') == '基金']
                    return funds
            return []
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def _parse_fund_js(self, js_content, fund_code):
        """解析基金详细数据的JS文件"""
        data = {
            'fund_code': fund_code,
            'net_worth_trend': [],
            'ac_worth_trend': [],
            'stock_codes': [],
            'update_time': datetime.now().isoformat()
        }
        
        try:
            # 解析单位净值走势Data_netWorthTrend
            net_worth_match = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', js_content, re.DOTALL)
            if net_worth_match:
                try:
                    data['net_worth_trend'] = json.loads(net_worth_match.group(1))
                except:
                    pass
            
            # 解析累计净值走势Data_ACWorthTrend
            ac_worth_match = re.search(r'var Data_ACWorthTrend\s*=\s*(\[.*?\]);', js_content, re.DOTALL)
            if ac_worth_match:
                try:
                    data['ac_worth_trend'] = json.loads(ac_worth_match.group(1))
                except:
                    pass
            
            # 解析股票代码 stockCodes
            stock_codes_match = re.search(r'var stockCodes\s*=\s*(\[.*?\]);', js_content)
            if stock_codes_match:
                try:
                    codes_raw = json.loads(stock_codes_match.group(1))
                    # 天天基金返回的code有时候带有交易所后缀（如0025580），取前6�?
                    data['stock_codes'] = [code[:6] for code in codes_raw]
                except:
                    data['stock_codes'] = []
                    
        except Exception as e:
            print(f"解析JS数据失败: {e}")
            
        return data
