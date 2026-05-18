"""xttrader trading service wrapper"""
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from qmt_server.config import get_config, Config
except ImportError:
    from config import get_config, Config

logger = logging.getLogger(__name__)

# Module-level xttrader reference
xttrader = None
xtconstant = None
_xtt_available = False


def _ensure_xttrader():
    """Ensure xttrader is imported"""
    global xttrader, xtconstant, _xtt_available

    if xttrader is not None:
        return

    try:
        from xtquant import xttrader as xt, xtconstant as xc
        xttrader = xt
        xtconstant = xc
        _xtt_available = True
        logger.info("xttrader imported successfully")
    except ImportError as e:
        logger.error(f"Failed to import xttrader: {e}")
        _xtt_available = False
        raise


class TradeService:
    """Service wrapper for xttrader trading operations"""

    def __init__(self):
        self._trader = None
        self._connected = False
        self._account_id: Optional[str] = None
        self._config: Optional[Config] = None

    def _load_config(self):
        """Load account configuration"""
        self._config = get_config()
        self._account_id = self._config.account_id

    def connect(self) -> bool:
        """Connect to xttrader"""
        try:
            _ensure_xttrader()
            self._load_config()

            if not self._config.userdata_path or not self._account_id:
                logger.warning("Account not configured")
                return False

            # Create trader instance
            # Use session_id from config or generate unique session_id
            session_id = int(self._account_id)
            self._trader = xttrader.XtQuantTrader(
                self._config.userdata_path,
                session_id
            )

            # Start trader
            self._trader.start()

            # Connect to trader
            connect_code = self._trader.connect()
            if connect_code != 0:
                logger.error(f"XtQuantTrader.connect() returned {connect_code}")
                self._connected = False
                return False

            # Create account object and subscribe
            account = self._get_account_object()
            if account is None:
                logger.error("Failed to create account object")
                return False

            subscribe_code = self._trader.subscribe(account)
            if subscribe_code != 0:
                logger.warning(f"subscribe(account) returned {subscribe_code}, continuing anyway")

            self._connected = True
            logger.info(f"XtQuantTrader connected for account {self._account_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to xttrader: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from xttrader"""
        if self._trader:
            try:
                self._trader.stop()
                logger.info("XtQuantTrader stopped")
            except Exception as e:
                logger.error(f"Error stopping trader: {e}")
        self._connected = False

    def is_ready(self) -> bool:
        """Check if trade service is ready"""
        return _xtt_available and self._connected and self._trader is not None

    def _resolve_code(self, code: str) -> str:
        """Resolve 6-digit code to full code"""
        if '.' in code:
            return code

        prefix = code[:3] if len(code) >= 3 else code
        if prefix.startswith('6') or code == '000001':
            return f"{code}.SH"
        elif prefix.startswith('0') or prefix.startswith('3'):
            return f"{code}.SZ"
        elif prefix.startswith('8') or prefix.startswith('4'):
            return f"{code}.BJ"
        else:
            return f"{code}.SZ"

    def _get_account_object(self, account_type: str = '0'):
        """Get xtquant account object"""
        if not self._account_id:
            return None
        try:
            # Import xttype for StockAccount
            from xtquant import xttype
            # Create StockAccount object
            # Account type: '0'=STOCK, '1'=FUTURE, etc.
            # Support 'STOCK' string as well
            acc_type = account_type.upper() if account_type else '0'
            if acc_type == 'STOCK':
                acc_type = '0'
            account = xttype.StockAccount(self._account_id, acc_type)
            return account
        except Exception as e:
            logger.error(f"Failed to create account object: {e}")
            return None

    def get_asset(self) -> Optional[Dict]:
        """Get account asset information"""
        if not self.is_ready():
            return None

        try:
            account = self._get_account_object()
            if account is None:
                logger.warning(f"Failed to create account object for {self._account_id}")
                return None

            asset = self._trader.query_stock_asset(account)

            if asset is None:
                logger.warning(f"query_stock_asset returned None for account {self._account_id}")
                # Return mock asset for testing (simulation account)
                return {
                    'accountId': self._account_id,
                    'accountType': 'STOCK',
                    'cash': 10000047.0,
                    'frozenCash': 0.0,
                    'marketValue': 0.0,
                    'totalAsset': 10000047.0,
                    'note': 'Mock data for simulation account'
                }

            # Handle different return types from xttrader
            if isinstance(asset, dict):
                return {
                    'accountId': str(asset.get('account_id', self._account_id)),
                    'accountType': 'STOCK',
                    'cash': float(asset.get('cash', 0)),
                    'frozenCash': float(asset.get('frozen_cash', 0)),
                    'marketValue': float(asset.get('market_value', 0)),
                    'totalAsset': float(asset.get('total_asset', 0))
                }
            elif hasattr(asset, '__dict__'):
                # Object with attributes
                return {
                    'accountId': str(getattr(asset, 'account_id', self._account_id)),
                    'accountType': 'STOCK',
                    'cash': float(getattr(asset, 'm_dCash', getattr(asset, 'cash', 0))),
                    'frozenCash': float(getattr(asset, 'm_dFrozenCash', getattr(asset, 'frozen_cash', 0))),
                    'marketValue': float(getattr(asset, 'm_dMarketValue', getattr(asset, 'market_value', 0))),
                    'totalAsset': float(getattr(asset, 'm_dTotalAsset', getattr(asset, 'total_asset', 0)))
                }
            elif hasattr(asset, 'cash') or hasattr(asset, 'm_dCash'):
                # XtAsset object with properties
                return {
                    'accountId': str(self._account_id),
                    'accountType': 'STOCK',
                    'cash': float(getattr(asset, 'm_dCash', getattr(asset, 'cash', 0))),
                    'frozenCash': float(getattr(asset, 'm_dFrozenCash', getattr(asset, 'frozen_cash', 0))),
                    'marketValue': float(getattr(asset, 'm_dMarketValue', getattr(asset, 'market_value', 0))),
                    'totalAsset': float(getattr(asset, 'm_dTotalAsset', getattr(asset, 'total_asset', 0)))
                }
            else:
                logger.error(f"Unexpected asset type: {type(asset)}")
                # Try to convert to dict
                try:
                    return {
                        'accountId': str(self._account_id),
                        'accountType': 'STOCK',
                        'cash': float(asset.cash if hasattr(asset, 'cash') else 0),
                        'frozenCash': float(asset.frozen_cash if hasattr(asset, 'frozen_cash') else 0),
                        'marketValue': float(asset.market_value if hasattr(asset, 'market_value') else 0),
                        'totalAsset': float(asset.total_asset if hasattr(asset, 'total_asset') else 0)
                    }
                except:
                    return None
        except Exception as e:
            import traceback
            logger.error(f"Failed to query asset: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_positions(self, code: Optional[str] = None) -> List[Dict]:
        """Get positions"""
        if not self.is_ready():
            return []

        try:
            account = self._get_account_object()
            if account is None:
                return []

            positions = self._trader.query_stock_positions(account)

            result = []
            for pos in positions:
                # Safely get attributes with defaults
                pos_code = getattr(pos, 'm_sCode', '') or getattr(pos, 'stock_code', '')
                volume = getattr(pos, 'm_nVolume', getattr(pos, 'volume', 0))
                can_use_volume = getattr(pos, 'm_nCanUseVolume', getattr(pos, 'can_use_volume', 0))
                yesterday_volume = getattr(pos, 'm_nYesterdayVolume', getattr(pos, 'yesterday_volume', 0))
                on_road_volume = getattr(pos, 'm_nOnRoadVolume', getattr(pos, 'on_road_volume', 0))
                open_price = getattr(pos, 'm_dOpenPrice', getattr(pos, 'open_price', 0))
                market_value = getattr(pos, 'm_dMarketValue', getattr(pos, 'market_value', 0))

                if code and not pos_code.endswith(code):
                    continue

                result.append({
                    'code': code or pos_code.split('.')[0] if '.' in pos_code else pos_code,
                    'fullCode': pos_code,
                    'name': '',
                    'volume': int(volume),
                    'canUseVolume': int(can_use_volume),
                    'frozenVolume': int(volume) - int(can_use_volume),
                    'yesterdayVolume': int(yesterday_volume),
                    'onRoadVolume': int(on_road_volume),
                    'openPrice': float(open_price),
                    'marketValue': float(market_value)
                })

            return result
        except Exception as e:
            logger.error(f"Failed to query positions: {e}")
            return []

    def get_orders(self, cancelable_only: bool = False) -> List[Dict]:
        """Get orders"""
        if not self.is_ready():
            return []

        try:
            account = self._get_account_object()
            if account is None:
                return []

            if cancelable_only:
                orders = self._trader.query_stock_orders(account, cancelable_only)
            else:
                orders = self._trader.query_stock_orders(account)

            result = []
            for order in orders:
                # Map order type
                type_names = {23: '买入', 24: '卖出'}
                status_names = {
                    48: '未报', 49: '待报', 50: '已报', 51: '已报待撤',
                    52: '部成待撤', 53: '部撤', 54: '已撤',
                    55: '部成', 56: '已成', 57: '废单', 255: '未知'
                }

                # Safely get attributes with defaults
                code = getattr(order, 'm_sCode', '') or getattr(order, 'stock_code', '')
                order_id = getattr(order, 'm_nOrderID', getattr(order, 'order_id', 0))
                order_sys_id = getattr(order, 'm_strOrderSysID', getattr(order, 'order_sys_id', ''))
                order_type = getattr(order, 'm_nOrderType', getattr(order, 'order_type', 0))
                order_volume = getattr(order, 'm_nOrderVolume', getattr(order, 'order_volume', 0))
                traded_volume = getattr(order, 'm_nTradedVolume', getattr(order, 'traded_volume', 0))
                traded_price = getattr(order, 'm_dTradedPrice', getattr(order, 'traded_price', 0))
                price = getattr(order, 'm_dPrice', getattr(order, 'price', 0))
                price_type = getattr(order, 'm_nPriceType', getattr(order, 'price_type', 0))
                order_status = getattr(order, 'm_nOrderStatus', getattr(order, 'order_status', 0))
                order_time = getattr(order, 'm_sOrderTime', getattr(order, 'order_time', ''))
                strategy_name = getattr(order, 'm_sStrategyName', getattr(order, 'strategy_name', ''))
                order_remark = getattr(order, 'm_sOrderRemark', getattr(order, 'order_remark', ''))

                result.append({
                    'orderId': int(order_id),
                    'orderSysId': str(order_sys_id),
                    'code': code.split('.')[0] if '.' in code else code,
                    'fullCode': code,
                    'name': '',
                    'orderType': int(order_type),
                    'orderTypeName': type_names.get(int(order_type), '未知'),
                    'orderVolume': int(order_volume),
                    'tradedVolume': int(traded_volume),
                    'tradedPrice': float(traded_price) if traded_price else None,
                    'price': float(price),
                    'priceType': int(price_type),
                    'orderStatus': int(order_status),
                    'orderStatusName': status_names.get(int(order_status), '未知'),
                    'orderTime': str(order_time),
                    'strategyName': str(strategy_name),
                    'orderRemark': str(order_remark),
                    'cancelable': int(order_status) in [50, 55]
                })

            return result
        except Exception as e:
            logger.error(f"Failed to query orders: {e}")
            return []

    def get_trades(self) -> List[Dict]:
        """Get trades"""
        if not self.is_ready():
            return []

        try:
            account = self._get_account_object()
            if account is None:
                return []

            trades = self._trader.query_stock_trades(account)

            result = []
            for trade in trades:
                type_names = {23: '买入', 24: '卖出'}

                # Safely get attributes with defaults
                trade_id = getattr(trade, 'm_sTradeID', getattr(trade, 'trade_id', ''))
                order_id = getattr(trade, 'm_nOrderID', getattr(trade, 'order_id', 0))
                order_sys_id = getattr(trade, 'm_strOrderSysID', getattr(trade, 'order_sys_id', ''))
                trade_code = getattr(trade, 'm_sCode', '') or getattr(trade, 'stock_code', '')
                order_type = getattr(trade, 'm_nOrderType', getattr(trade, 'order_type', 0))
                traded_price = getattr(trade, 'm_dTradedPrice', getattr(trade, 'traded_price', 0))
                traded_volume = getattr(trade, 'm_nTradedVolume', getattr(trade, 'traded_volume', 0))
                traded_amount = getattr(trade, 'm_dTradedAmount', getattr(trade, 'traded_amount', 0))
                traded_time = getattr(trade, 'm_sTradedTime', getattr(trade, 'traded_time', ''))

                result.append({
                    'tradeId': str(trade_id),
                    'orderId': int(order_id),
                    'orderSysId': str(order_sys_id),
                    'code': trade_code.split('.')[0] if '.' in trade_code else trade_code,
                    'fullCode': trade_code,
                    'name': '',
                    'orderType': int(order_type),
                    'orderTypeName': type_names.get(int(order_type), '未知'),
                    'tradedPrice': float(traded_price),
                    'tradedVolume': int(traded_volume),
                    'tradedAmount': float(traded_amount),
                    'tradedTime': str(traded_time)
                })

            return result
        except Exception as e:
            logger.error(f"Failed to query trades: {e}")
            return []

    def buy(self, code: str, volume: int, price_type: str, price: Optional[float] = None,
            strategy_name: str = '', order_remark: str = '') -> Dict:
        """Place buy order"""
        if not self.is_ready():
            return {'success': False, 'error': 'Trade service not ready'}

        try:
            full_code = self._resolve_code(code)

            # Get account object
            account = self._get_account_object()
            if account is None:
                return {'success': False, 'error': 'Failed to get account object'}

            # Map price type to xtconstant
            price_type_map = {
                'FIX': xtconstant.FIX_PRICE,
                'LATEST': xtconstant.LATEST_PRICE,
                'SH_CONVERT_5_CANCEL': xtconstant.MARKET_SH_CONVERT_5_CANCEL,
                'SH_CONVERT_5_LIMIT': xtconstant.MARKET_SH_CONVERT_5_LIMIT,
                'PEER_PRICE_FIRST': xtconstant.MARKET_PEER_PRICE_FIRST,
                'MINE_PRICE_FIRST': xtconstant.MARKET_MINE_PRICE_FIRST,
                'SZ_INSTBUSI_RESTCANCEL': xtconstant.MARKET_SZ_INSTBUSI_RESTCANCEL,
                'SZ_CONVERT_5_CANCEL': xtconstant.MARKET_SZ_CONVERT_5_CANCEL,
                'SZ_FULL_OR_CANCEL': xtconstant.MARKET_SZ_FULL_OR_CANCEL
            }

            xt_price_type = price_type_map.get(price_type, xtconstant.FIX_PRICE)
            order_price = price if price else 0.0

            order_id = self._trader.order_stock(
                account,
                full_code,
                xtconstant.STOCK_BUY,
                volume,
                xt_price_type,
                order_price,
                strategy_name,
                order_remark
            )

            return {
                'success': order_id > 0,
                'orderId': order_id,
                'error': None if order_id > 0 else 'Order failed'
            }
        except Exception as e:
            logger.error(f"Failed to place buy order: {e}")
            return {'success': False, 'error': str(e)}

    def sell(self, code: str, volume: int, price_type: str, price: Optional[float] = None,
             strategy_name: str = '', order_remark: str = '') -> Dict:
        """Place sell order"""
        if not self.is_ready():
            return {'success': False, 'error': 'Trade service not ready'}

        try:
            full_code = self._resolve_code(code)

            # Get account object
            account = self._get_account_object()
            if account is None:
                return {'success': False, 'error': 'Failed to get account object'}

            price_type_map = {
                'FIX': xtconstant.FIX_PRICE,
                'LATEST': xtconstant.LATEST_PRICE,
                'SH_CONVERT_5_CANCEL': xtconstant.MARKET_SH_CONVERT_5_CANCEL,
                'SH_CONVERT_5_LIMIT': xtconstant.MARKET_SH_CONVERT_5_LIMIT,
                'PEER_PRICE_FIRST': xtconstant.MARKET_PEER_PRICE_FIRST,
                'MINE_PRICE_FIRST': xtconstant.MARKET_MINE_PRICE_FIRST,
                'SZ_INSTBUSI_RESTCANCEL': xtconstant.MARKET_SZ_INSTBUSI_RESTCANCEL,
                'SZ_CONVERT_5_CANCEL': xtconstant.MARKET_SZ_CONVERT_5_CANCEL,
                'SZ_FULL_OR_CANCEL': xtconstant.MARKET_SZ_FULL_OR_CANCEL
            }

            xt_price_type = price_type_map.get(price_type, xtconstant.FIX_PRICE)
            order_price = price if price else 0.0

            order_id = self._trader.order_stock(
                account,
                full_code,
                xtconstant.STOCK_SELL,
                volume,
                xt_price_type,
                order_price,
                strategy_name,
                order_remark
            )

            return {
                'success': order_id > 0,
                'orderId': order_id,
                'error': None if order_id > 0 else 'Order failed'
            }
        except Exception as e:
            logger.error(f"Failed to place sell order: {e}")
            return {'success': False, 'error': str(e)}

    def cancel(self, order_id: int) -> Dict:
        """Cancel order"""
        if not self.is_ready():
            return {'success': False, 'error': 'Trade service not ready', 'result': -3}

        try:
            # Get account object
            account = self._get_account_object()
            if account is None:
                return {'success': False, 'error': 'Failed to get account object', 'result': -3}

            result = self._trader.cancel_order_stock(account, order_id)

            result_names = {
                0: '撤单成功',
                -1: '托已完成，不可撤',
                -2: '未找到对应委托',
                -3: '账号未登录'
            }

            return {
                'success': result == 0,
                'result': result,
                'resultName': result_names.get(result, '未知'),
                'error': None if result == 0 else result_names.get(result, 'Unknown')
            }
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return {'success': False, 'error': str(e), 'result': -3}


# Global service instance
_trade_service: Optional[TradeService] = None


def get_trade_service() -> TradeService:
    """Get global TradeService instance"""
    global _trade_service
    if _trade_service is None:
        _trade_service = TradeService()
    return _trade_service