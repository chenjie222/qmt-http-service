"""xtquant data service wrapper"""
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

try:
    from qmt_server.config import get_config
except ImportError:
    from config import get_config

logger = logging.getLogger(__name__)

# Module-level xtdata reference
xtdata = None
_xtquant_available = False


def _inject_xtquant_path():
    """Inject xtquant path to sys.path"""
    config = get_config()
    if config.xtquant_path and config.xtquant_path not in sys.path:
        sys.path.append(config.xtquant_path)
        logger.info(f"Added xtquant path: {config.xtquant_path}")


def _ensure_xtdata():
    """Ensure xtdata is imported"""
    global xtdata, _xtquant_available

    if xtdata is not None:
        return

    _inject_xtquant_path()

    try:
        from xtquant import xtdata as xtdata_module
        xtdata = xtdata_module
        _xtquant_available = True
        logger.info("xtdata imported successfully")
    except ImportError as e:
        logger.error(f"Failed to import xtdata: {e}")
        _xtquant_available = False
        raise


def is_xtquant_available() -> bool:
    """Check if xtquant is available (triggers import if not already)"""
    try:
        _ensure_xtdata()
    except Exception:
        pass
    return _xtquant_available


class XTQuantService:
    """Service wrapper for xtquant market data"""

    def __init__(self):
        self._connected = False
        self._stock_cache: Dict[str, Dict] = {}
        self._last_sector_sync: Optional[datetime] = None

    def connect(self) -> bool:
        """Test connection to QMT"""
        try:
            _ensure_xtdata()
            # Test by getting a simple quote
            test_data = xtdata.get_market_data_ex(
                field_list=['close'],
                stock_list=['000001.SH'],
                period='1d',
                count=1
            )
            self._connected = True
            logger.info("QMT connection verified")
            return True
        except Exception as e:
            logger.error(f"QMT connection failed: {e}")
            self._connected = False
            return False

    def is_ready(self) -> bool:
        """Check if service is ready"""
        return _xtquant_available and self._connected

    def _resolve_code(self, code: str) -> str:
        """Resolve 6-digit code to full code format"""
        if '.' in code:
            return code

        # Determine exchange based on code prefix
        prefix = code[:3] if len(code) >= 3 else code

        if prefix.startswith('6'):
            return f"{code}.SH"
        elif prefix.startswith('0') or prefix.startswith('3'):
            return f"{code}.SZ"
        elif prefix.startswith('8') or prefix.startswith('4'):
            return f"{code}.BJ"
        elif code == '000001':  # Special case for 上证指数
            return f"{code}.SH"
        else:
            return f"{code}.SZ"  # Default

    def _code_from_full(self, full_code: str) -> str:
        """Extract 6-digit code from full code"""
        return full_code.split('.')[0]

    def download_sector_data(self) -> bool:
        """Download sector data from QMT"""
        try:
            _ensure_xtdata()
            xtdata.download_sector_data()
            self._last_sector_sync = datetime.now()
            logger.info("Sector data downloaded")
            return True
        except Exception as e:
            logger.error(f"Failed to download sector data: {e}")
            return False

    def get_stock_list(self, sync: bool = True) -> List[Dict]:
        """Get all stocks via sector traversal"""
        _ensure_xtdata()

        if sync or self._last_sector_sync is None:
            self.download_sector_data()

        sectors = xtdata.get_sector_list()
        seen_codes = set()
        stocks = []

        # Filter sectors to only include stock-related ones
        stock_sectors = ['上证A股', '上证B股', '深证A股', '深证B股', '京市A股', '创业板', '科创板']
        filtered_sectors = [s for s in sectors if s in stock_sectors or any(k in s for k in ['A股', 'B股', '创业板', '科创板'])]

        for sector in filtered_sectors:
            try:
                sector_stocks = xtdata.get_stock_list_in_sector(sector)
                for full_code in sector_stocks:
                    # Filter to only include SH, SZ, BJ market stocks
                    if '.' not in full_code:
                        continue
                    exchange = full_code.split('.')[1]
                    if exchange not in ['SH', 'SZ', 'BJ']:
                        continue

                    code = self._code_from_full(full_code)
                    if code not in seen_codes:
                        seen_codes.add(code)
                        stocks.append({
                            'code': code,
                            'fullCode': full_code,
                            'name': '',  # Name lookup requires additional API call
                            'market': exchange,
                            'marketName': self._get_market_name(full_code)
                        })
            except Exception as e:
                logger.warning(f"Failed to get stocks from sector {sector}: {e}")

        return stocks

    def _get_market_name(self, full_code: str) -> str:
        """Get market name from code"""
        exchange = full_code.split('.')[1]
        names = {
            'SH': '上海证券交易所',
            'SZ': '深圳证券交易所',
            'BJ': '北京证券交易所'
        }
        return names.get(exchange, '未知交易所')

    def get_instrument_detail(self, code: str) -> Optional[Dict]:
        """Get instrument detail including 流通股本 (FloatVolume) and 总股本 (TotalVolume)

        Args:
            code: 6-digit stock code or full code (e.g., '000001' or '000001.SZ')

        Returns:
            Dict with instrument details including floatVolume/totalVolume,
            or None if lookup fails.
        """
        _ensure_xtdata()

        full_code = self._resolve_code(code)

        try:
            detail = xtdata.get_instrument_detail(full_code)

            if detail is None:
                logger.warning(f"Instrument detail returned None for {full_code}")
                return None

            return {
                'code': code,
                'fullCode': full_code,
                'name': detail.get('InstrumentName', ''),
                'type': detail.get('InstrumentType', ''),
                'exchange': detail.get('ExchangeID', full_code.split('.')[1]),
                'exchangeName': self._get_market_name(full_code),
                'listedDate': str(detail.get('ListedDate', '')) if detail.get('ListedDate') else None,
                'delisted': bool(detail.get('IsDelisting', False)),
                'floatVolume': float(detail['FloatVolume']) if detail.get('FloatVolume', 0) > 0 else None,
                'totalVolume': float(detail['TotalVolume']) if detail.get('TotalVolume', 0) > 0 else None,
            }
        except Exception as e:
            logger.error(f"Failed to get instrument detail for {code}: {e}")
            return None

    def get_quote(self, code: str) -> Optional[Dict]:
        """Get single stock quote"""
        _ensure_xtdata()

        full_code = self._resolve_code(code)

        try:
            data = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'preClose',
                           'volume', 'amount'],
                stock_list=[full_code],
                period='1d',
                count=1
            )

            if data is None:
                return None

            row_data = None

            # Handle dict return type from xtdata
            if isinstance(data, dict):
                if full_code not in data:
                    return None
                df = data[full_code]
                if hasattr(df, 'empty') and df.empty:
                    # DataFrame is empty, try getting data from full_tick
                    return self._get_quote_from_tick(code, full_code)
                if hasattr(df, 'iterrows') and not df.empty:
                    row_data = df.iloc[0] if len(df) > 0 else None
                elif isinstance(df, dict):
                    row_data = df
            elif hasattr(data, 'index') and full_code in data.index:
                row_data = data.loc[full_code]

            if row_data is None:
                return None

            # Extract values based on row_data type
            if hasattr(row_data, 'get'):
                close = float(row_data.get('close', 0))
                pre_close = float(row_data.get('preClose', 0))
                open_price = float(row_data.get('open', 0))
                high = float(row_data.get('high', 0))
                low = float(row_data.get('low', 0))
                volume = int(row_data.get('volume', 0))
                amount = float(row_data.get('amount', 0))
            else:
                return None

            change = close - pre_close if pre_close else 0
            change_pct = (change / pre_close * 100) if pre_close else 0

            return {
                'code': code,
                'fullCode': full_code,
                'name': '',
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'preClose': pre_close,
                'change': change,
                'changePct': round(change_pct, 2),
                'volume': volume,
                'amount': amount
            }
        except Exception as e:
            logger.error(f"Failed to get quote for {code}: {e}")
            return None

    def _get_quote_from_tick(self, code: str, full_code: str) -> Optional[Dict]:
        """Get quote from tick data as fallback"""
        try:
            tick_data = xtdata.get_full_tick([full_code])
            if not tick_data or full_code not in tick_data:
                return None

            tick = tick_data[full_code]
            close = tick.get('lastPrice', 0)
            pre_close = tick.get('lastClose', 0)
            change = close - pre_close if pre_close else 0
            change_pct = (change / pre_close * 100) if pre_close else 0

            return {
                'code': code,
                'fullCode': full_code,
                'name': '',
                'open': tick.get('open', 0),
                'high': tick.get('high', 0),
                'low': tick.get('low', 0),
                'close': close,
                'preClose': pre_close,
                'change': round(change, 2),
                'changePct': round(change_pct, 2),
                'volume': tick.get('volume', 0),
                'amount': tick.get('amount', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get quote from tick for {code}: {e}")
            return None

    def get_quotes_batch(self, codes: List[str]) -> List[Dict]:
        """Get multiple stock quotes"""
        _ensure_xtdata()

        full_codes = [self._resolve_code(c) for c in codes]

        try:
            data = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'preClose',
                           'volume', 'amount'],
                stock_list=full_codes,
                period='1d',
                count=1
            )

            if data is None:
                return []

            results = []
            for code, full_code in zip(codes, full_codes):
                # Handle both dict and DataFrame return types
                if isinstance(data, dict):
                    if full_code not in data:
                        continue
                    df = data[full_code]
                    # DataFrame case - xtdata returns DataFrame
                    if hasattr(df, 'iloc') and len(df) > 0:
                        row = df.iloc[0]
                        close = float(row.get('close', 0) if hasattr(row, 'get') else row['close'])
                        pre_close = float(row.get('preClose', 0) if hasattr(row, 'get') else row['preClose'])
                        open_price = float(row.get('open', 0) if hasattr(row, 'get') else row['open'])
                        high = float(row.get('high', 0) if hasattr(row, 'get') else row['high'])
                        low = float(row.get('low', 0) if hasattr(row, 'get') else row['low'])
                        volume = int(row.get('volume', 0) if hasattr(row, 'get') else row['volume'])
                        amount = float(row.get('amount', 0) if hasattr(row, 'get') else row['amount'])
                    elif isinstance(df, dict):
                        close = float(df.get('close', 0))
                        pre_close = float(df.get('preClose', 0))
                        open_price = float(df.get('open', 0))
                        high = float(df.get('high', 0))
                        low = float(df.get('low', 0))
                        volume = int(df.get('volume', 0))
                        amount = float(df.get('amount', 0))
                    else:
                        continue
                elif hasattr(data, 'index') and full_code in data.index:
                    row = data.loc[full_code]
                    close = float(row.get('close', 0))
                    pre_close = float(row.get('preClose', 0))
                    open_price = float(row.get('open', 0))
                    high = float(row.get('high', 0))
                    low = float(row.get('low', 0))
                    volume = int(row.get('volume', 0))
                    amount = float(row.get('amount', 0))
                else:
                    continue

                change_pct = (close / pre_close - 1) * 100 if pre_close else 0
                change = close - pre_close if pre_close else 0

                results.append({
                    'code': code,
                    'fullCode': full_code,
                    'name': '',
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'preClose': pre_close,
                    'change': round(change, 2),
                    'changePct': round(change_pct, 2),
                    'volume': volume,
                    'amount': amount
                })

            return results
        except Exception as e:
            logger.error(f"Failed to get batch quotes: {e}")
            return []

    def get_tick(self, code: str) -> Optional[Dict]:
        """Get five-level tick data"""
        _ensure_xtdata()

        full_code = self._resolve_code(code)

        try:
            tick_data = xtdata.get_full_tick([full_code])

            if not tick_data or full_code not in tick_data:
                return None

            tick = tick_data[full_code]

            return {
                'code': code,
                'fullCode': full_code,
                'name': '',
                'lastPrice': tick.get('lastPrice', 0),
                'open': tick.get('open', 0),
                'high': tick.get('high', 0),
                'low': tick.get('low', 0),
                'preClose': tick.get('lastClose', 0),
                'volume': tick.get('volume', 0),
                'amount': tick.get('amount', 0),
                'bidPrice': list(tick.get('bidPrice', [0]*5)),
                'bidVol': list(tick.get('bidVol', [0]*5)),
                'askPrice': list(tick.get('askPrice', [0]*5)),
                'askVol': list(tick.get('askVol', [0]*5)),
                'time': str(tick.get('time', ''))
            }
        except Exception as e:
            logger.error(f"Failed to get tick for {code}: {e}")
            return None

    def get_kline(self, code: str, period: str = '1d',
                  count: int = 100, start: str = None, end: str = None) -> Optional[Dict]:
        """Get Kline data

        优先级：start/end > count
        - 有start/end：按时间范围获取
        - 无start/end：按count获取最近数据
        """
        _ensure_xtdata()

        full_code = self._resolve_code(code)

        # Map period to xtquant format
        period_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '1d': '1d', '1w': '1w', '1mon': '1mon'
        }
        xt_period = period_map.get(period, '1d')

        # 判断是否使用时间范围模式
        use_date_range = start and end

        try:
            # 如果没有指定时间范围，根据count计算
            if not use_date_range:
                end_dt = datetime.now()
                # Estimate days back based on period
                if xt_period in ['1m', '5m', '15m', '30m']:
                    days_back = min(count // 240 + 5, 30)  # ~240 bars per trading day
                elif xt_period == '1h':
                    days_back = min(count // 4 + 5, 90)
                elif xt_period == '1d':
                    days_back = count + 10
                elif xt_period == '1w':
                    days_back = count * 7 + 30
                else:  # 1mon
                    days_back = count * 30 + 60

                start_dt = end_dt - timedelta(days=days_back)
                start = start_dt.strftime('%Y%m%d')
                end = end_dt.strftime('%Y%m%d')

            # Download history data first
            try:
                xtdata.download_history_data(full_code, xt_period, start, end)
            except Exception as e:
                logger.warning(f"Failed to download history data for {code}: {e}")

            # 根据是否使用时间范围选择不同的API调用方式
            if use_date_range:
                # 使用时间范围获取数据
                data = xtdata.get_market_data_ex(
                    field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                    stock_list=[full_code],
                    period=xt_period,
                    start_time=start,
                    end_time=end
                )
            else:
                # 使用count获取最近数据
                data = xtdata.get_market_data_ex(
                    field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                    stock_list=[full_code],
                    period=xt_period,
                    count=count
                )

            if data is None:
                return None

            klines = []

            # Handle dict return type from xtdata (Dict[str, DataFrame])
            if isinstance(data, dict):
                if full_code not in data:
                    return None
                code_data = data[full_code]

                # DataFrame case - xtdata returns DataFrame
                if hasattr(code_data, 'iterrows') and not code_data.empty:
                    for idx, row in code_data.iterrows():
                        klines.append({
                            'date': str(idx).replace('-', '').replace(' ', '').replace(':', '')[:8],
                            'open': float(row.get('open', 0) if hasattr(row, 'get') else row['open']),
                            'high': float(row.get('high', 0) if hasattr(row, 'get') else row['high']),
                            'low': float(row.get('low', 0) if hasattr(row, 'get') else row['low']),
                            'close': float(row.get('close', 0) if hasattr(row, 'get') else row['close']),
                            'volume': int(row.get('volume', 0) if hasattr(row, 'get') else row['volume']),
                            'amount': float(row.get('amount', 0) if hasattr(row, 'get') else row['amount'])
                        })
                elif isinstance(code_data, dict):
                    # Single day data as dict
                    klines.append({
                        'date': datetime.now().strftime('%Y%m%d'),
                        'open': float(code_data.get('open', 0)),
                        'high': float(code_data.get('high', 0)),
                        'low': float(code_data.get('low', 0)),
                        'close': float(code_data.get('close', 0)),
                        'volume': int(code_data.get('volume', 0)),
                        'amount': float(code_data.get('amount', 0))
                    })
            elif hasattr(data, 'index'):
                # DataFrame case
                if full_code not in data.index:
                    return None

                df_data = data.xs(full_code) if hasattr(data, 'xs') else data

                if hasattr(df_data, 'iterrows'):
                    for idx, row in df_data.iterrows():
                        klines.append({
                            'date': str(idx) if not isinstance(idx, tuple) else str(idx[1]),
                            'open': float(row.get('open', 0)),
                            'high': float(row.get('high', 0)),
                            'low': float(row.get('low', 0)),
                            'close': float(row.get('close', 0)),
                            'volume': int(row.get('volume', 0)),
                            'amount': float(row.get('amount', 0))
                        })

            return {
                'code': code,
                'fullCode': full_code,
                'name': '',
                'period': period,
                'count': len(klines),
                'kline': klines
            }
        except Exception as e:
            logger.error(f"Failed to get kline for {code}: {e}")
            return None

    def get_sectors(self) -> List[str]:
        """Get all sector names"""
        _ensure_xtdata()

        try:
            if self._last_sector_sync is None:
                self.download_sector_data()
            return xtdata.get_sector_list()
        except Exception as e:
            logger.error(f"Failed to get sectors: {e}")
            return []

    def get_block_stocks(self, block_name: str) -> List[Dict]:
        """Get stocks in a block/sector"""
        _ensure_xtdata()

        try:
            full_codes = xtdata.get_stock_list_in_sector(block_name)
            return [
                {
                    'code': self._code_from_full(fc),
                    'fullCode': fc,
                    'name': '',
                    'market': fc.split('.')[1],
                    'marketName': self._get_market_name(fc)
                }
                for fc in full_codes
            ]
        except Exception as e:
            logger.error(f"Failed to get block stocks for {block_name}: {e}")
            return []


# Global service instance
_service_instance: Optional[XTQuantService] = None


def get_xtquant_service() -> XTQuantService:
    """Get global XTQuantService instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = XTQuantService()
    return _service_instance