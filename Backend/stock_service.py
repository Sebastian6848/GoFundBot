import requests
import json
import threading
import time
import os

class StockService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(StockService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.stock_details = {} # Map code -> {name, market}
        self.last_update = 0
        self.cache_ttl = 24 * 3600 * 10  # 10 days
        self.cache_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "Data", "stock_list_cache.json")
        )
        self._load_data()
        self._initialized = True

    def _load_data(self):
        """Load stock data from local cache; refresh if missing or expired."""
        loaded = self._load_from_cache()

        if not loaded or self._is_cache_expired():
            threading.Thread(target=self._refresh_cache, daemon=True).start()

    def _load_from_cache(self):
        if not os.path.exists(self.cache_file):
            return False

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.last_update = data.get("last_update", 0)
            self.stock_details = data.get("stock_details", {})
            return bool(self.stock_details)
        except Exception as e:
            print(f"Error loading stock cache: {e}")
            return False

    def _is_cache_expired(self):
        if not self.last_update:
            return True
        return (time.time() - self.last_update) > self.cache_ttl

    def _save_to_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "last_update": self.last_update,
                    "stock_details": self.stock_details
                }, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving stock cache: {e}")

    def _refresh_cache(self):
        """Download stock list and save to local cache."""
        self._fetch_all()
        self._save_to_cache()

    def _fetch_all(self):
        self._fetch_hk_stocks()
        self._fetch_ashare_stocks()
        self.last_update = time.time()
        print(f"Stock data loaded. Total: {len(self.stock_details)}")

    def _fetch_hk_stocks(self):
        url = "https://api.biyingapi.com/hk/list/all/biyinglicence"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    # dm format: "00001.HK"
                    full_code = str(item.get('dm', ''))
                    name = item.get('mc', '')
                    if full_code and name:
                        code = full_code.split('.')[0]
                        self.stock_details[code] = {
                            'name': name,
                            'market': '港交所'
                        }
        except Exception as e:
            print(f"Error fetching HK stocks: {e}")

    def _fetch_ashare_stocks(self):
        url = "https://api.mairuiapi.com/hslt/list/LICENCE-66D8-9F96-0C7F0FBCD073"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    # dm format: "000001.SZ"
                    full_code = str(item.get('dm', ''))
                    name = item.get('mc', '')
                    jys = item.get('jys', '')
                    
                    market = 'A股'
                    if jys == 'SZ':
                        market = '深交所'
                    elif jys == 'SH' or full_code.endswith('.SH'):
                        market = '上交所'
                    # Fallback based on code prefix if JYS not clear
                    elif full_code.startswith('6') or full_code.startswith('9'):
                        market = '上交所'
                    elif full_code.startswith('0') or full_code.startswith('3'):
                        market = '深交所'
                    elif full_code.startswith('4') or full_code.startswith('8'):
                        market = '北交所'

                    if full_code and name:
                        code = full_code.split('.')[0]
                        self.stock_details[code] = {
                            'name': name,
                            'market': market
                        }
        except Exception as e:
            print(f"Error fetching A-Share stocks: {e}")


    def normalize_code(self, internal_code):
        """
        Normalize internal EastMoney code to standard stock code.
        - HK: 6990116 -> 06990
        - A: 0025580 -> 002558, 6034861 -> 603486
        """
        if not internal_code:
            return ""

        str_code = str(internal_code)
        
        # Check if HK stock
        if str_code.endswith("116") and len(str_code) > 3:
            raw_code = str_code[:-3]
            return raw_code.zfill(5)
        
        # Assume A-Share (remove last digit suffix)
        if len(str_code) > 1:
            raw_code = str_code[:-1]
        else:
            raw_code = str_code
            
        return raw_code.zfill(6)

    def get_stock_name(self, internal_code):
        """
        Convert internal code to name. (Backward compatibility)
        """
        info = self.get_stock_info(internal_code)
        return info.get('name', str(internal_code)) if info else str(internal_code)

    def get_stock_info(self, internal_code):
        """
        Convert internal code to full info {name, market}.
        """
        search_code = self.normalize_code(internal_code)
        
        if search_code in self.stock_details:
            return self.stock_details[search_code]
            
        return {'name': search_code, 'market': '--'}
