"""Pydantic models for QMT Server API"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Base Response Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail structure"""
    code: str
    message: str
    details: Optional[str] = None


class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Optional[Any] = None
    message: str = ""
    error: Optional[ErrorDetail] = None


# ============================================================================
# Market Data Models
# ============================================================================

class QuoteData(BaseModel):
    """Single stock quote"""
    code: str = Field(..., description="6位股票代码")
    full_code: str = Field(..., alias="fullCode", description="完整代码如 000001.SZ")
    name: Optional[str] = Field(None, description="股票名称")
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    pre_close: Optional[float] = Field(None, alias="preClose")
    change: Optional[float] = None
    change_pct: Optional[float] = Field(None, alias="changePct")
    volume: Optional[int] = None
    amount: Optional[float] = None


class QuoteResponse(BaseModel):
    """Quote response wrapper"""
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: Optional[str] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    pre_close: Optional[float] = Field(None, alias="preClose")
    change: Optional[float] = None
    change_pct: Optional[float] = Field(None, alias="changePct")
    volume: Optional[int] = None
    amount: Optional[float] = None


class KlineItem(BaseModel):
    """Single Kline data point"""
    date: str = Field(..., description="日期时间格式 YYYYMMDDHHMMSS")
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


class KlineResponse(BaseModel):
    """Kline response"""
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: Optional[str] = None
    period: str
    count: int
    kline: List[KlineItem]


class TickResponse(BaseModel):
    """Five-level tick data response"""
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: Optional[str] = None
    last_price: float = Field(..., alias="lastPrice")
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = Field(None, alias="preClose")
    volume: Optional[int] = None
    amount: Optional[float] = None
    bid_price: List[float] = Field(..., alias="bidPrice", description="买一~五价")
    bid_vol: List[int] = Field(..., alias="bidVol", description="买一~五量")
    ask_price: List[float] = Field(..., alias="askPrice", description="卖一~五价")
    ask_vol: List[int] = Field(..., alias="askVol", description="卖一~五量")
    time: Optional[str] = None


class StockItem(BaseModel):
    """Stock basic info"""
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: str
    market: str
    market_name: str = Field(..., alias="marketName")


class StockListResponse(BaseModel):
    """Stock list response"""
    total: int
    stocks: List[StockItem]
    synced: bool
    block_count: int = Field(..., alias="blockCount")


class BlockStocksResponse(BaseModel):
    """Block stocks response"""
    block: str
    total: int
    stocks: List[StockItem]


class FinanceTable(BaseModel):
    """Financial data table"""
    report_date: str = Field(..., alias="reportDate")
    # Dynamic fields based on table type
    data: Dict[str, Any]


class FinanceResponse(BaseModel):
    """Finance data response"""
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: Optional[str] = None
    tables: Dict[str, List[Dict[str, Any]]]


class IndexOverview(BaseModel):
    """Market index overview"""
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: str
    close: float
    change: float
    change_pct: float = Field(..., alias="changePct")
    volume: Optional[int] = None
    amount: Optional[float] = None


class MarketOverviewResponse(BaseModel):
    """Market overview response"""
    indexes: List[IndexOverview]


class TradingDatesResponse(BaseModel):
    """Trading dates response"""
    start: str
    end: str
    trading_days: List[str] = Field(..., alias="tradingDays")
    count: int


class InstrumentDetail(BaseModel):
    """Instrument detail"""
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: str
    type: str
    exchange: str
    exchange_name: str = Field(..., alias="exchangeName")
    listed_date: Optional[str] = Field(None, alias="listedDate")
    delisted: bool = False
    float_volume: Optional[float] = Field(None, alias="floatVolume")
    total_volume: Optional[float] = Field(None, alias="totalVolume")


class SubscribeRequest(BaseModel):
    """Subscribe request"""
    codes: List[str]
    seconds: int = Field(default=1, ge=1, le=60)


class SubscribeResponse(BaseModel):
    """Subscribe response"""
    subscribed: List[str]
    duration: int
    tick_count: int = Field(..., alias="tickCount")
    ticks: List[TickResponse]


# ============================================================================
# Account Models
# ============================================================================

class AssetResponse(BaseModel):
    """Asset information"""
    account_id: str = Field(..., alias="accountId")
    account_type: str = Field(..., alias="accountType")
    cash: float
    frozen_cash: float = Field(..., alias="frozenCash")
    market_value: float = Field(..., alias="marketValue")
    total_asset: float = Field(..., alias="totalAsset")


class PositionItem(BaseModel):
    """Single position"""
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: Optional[str] = None
    volume: int
    can_use_volume: int = Field(..., alias="canUseVolume")
    frozen_volume: int = Field(..., alias="frozenVolume")
    yesterday_volume: int = Field(..., alias="yesterdayVolume")
    on_road_volume: int = Field(..., alias="onRoadVolume")
    open_price: float = Field(..., alias="openPrice")
    market_value: float = Field(..., alias="marketValue")


class PositionsResponse(BaseModel):
    """Positions response"""
    positions: List[PositionItem]
    total: int


class OrderItem(BaseModel):
    """Single order"""
    order_id: int = Field(..., alias="orderId")
    order_sys_id: str = Field(..., alias="orderSysId")
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: Optional[str] = None
    order_type: int = Field(..., alias="orderType")
    order_type_name: str = Field(..., alias="orderTypeName")
    order_volume: int = Field(..., alias="orderVolume")
    traded_volume: int = Field(..., alias="tradedVolume")
    traded_price: Optional[float] = Field(None, alias="tradedPrice")
    price: float
    price_type: int = Field(..., alias="priceType")
    order_status: int = Field(..., alias="orderStatus")
    order_status_name: str = Field(..., alias="orderStatusName")
    order_time: str = Field(..., alias="orderTime")
    strategy_name: str = Field("", alias="strategyName")
    order_remark: str = Field("", alias="orderRemark")
    cancelable: bool


class OrdersResponse(BaseModel):
    """Orders response"""
    orders: List[OrderItem]
    total: int


class TradeItem(BaseModel):
    """Single trade"""
    trade_id: str = Field(..., alias="tradeId")
    order_id: int = Field(..., alias="orderId")
    order_sys_id: str = Field(..., alias="orderSysId")
    code: str
    full_code: str = Field(..., alias="fullCode")
    name: Optional[str] = None
    order_type: int = Field(..., alias="orderType")
    order_type_name: str = Field(..., alias="orderTypeName")
    traded_price: float = Field(..., alias="tradedPrice")
    traded_volume: int = Field(..., alias="tradedVolume")
    traded_amount: float = Field(..., alias="tradedAmount")
    traded_time: str = Field(..., alias="tradedTime")


class TradesResponse(BaseModel):
    """Trades response"""
    trades: List[TradeItem]
    total: int


# ============================================================================
# Trade Request/Response Models
# ============================================================================

PRICE_TYPES = Literal[
    "FIX", "LATEST", "SH_CONVERT_5_CANCEL", "SH_CONVERT_5_LIMIT",
    "PEER_PRICE_FIRST", "MINE_PRICE_FIRST", "SZ_INSTBUSI_RESTCANCEL",
    "SZ_CONVERT_5_CANCEL", "SZ_FULL_OR_CANCEL"
]


class BuyRequest(BaseModel):
    """Buy order request"""
    code: str = Field(..., description="股票代码")
    volume: int = Field(..., description="买入数量，必须是100的整数倍")
    price_type: PRICE_TYPES = Field(..., alias="priceType")
    price: Optional[float] = Field(None, description="指定价格，price_type=FIX时必填")
    strategy_name: str = Field("", alias="strategyName")
    order_remark: str = Field("", alias="orderRemark")
    confirm: bool = Field(False, description="true=真正下单，false=仅预演")

    @field_validator('volume')
    @classmethod
    def validate_volume(cls, v: int) -> int:
        if v % 100 != 0:
            raise ValueError('Volume must be multiple of 100')
        return v

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Optional[float], info) -> Optional[float]:
        if info.data.get('price_type') == 'FIX' and v is None:
            raise ValueError('Price is required when price_type is FIX')
        return v


class SellRequest(BaseModel):
    """Sell order request"""
    code: str = Field(..., description="股票代码")
    volume: int = Field(..., description="卖出数量，必须是100的整数倍")
    price_type: PRICE_TYPES = Field(..., alias="priceType")
    price: Optional[float] = Field(None, description="指定价格，price_type=FIX时必填")
    strategy_name: str = Field("", alias="strategyName")
    order_remark: str = Field("", alias="orderRemark")
    confirm: bool = Field(False, description="true=真正下单，false=仅预演")

    @field_validator('volume')
    @classmethod
    def validate_volume(cls, v: int) -> int:
        if v % 100 != 0:
            raise ValueError('Volume must be multiple of 100')
        return v


class CancelRequest(BaseModel):
    """Cancel order request"""
    order_id: int = Field(..., alias="orderId", description="委托编号")
    confirm: bool = Field(False, description="true=真正撤单")


class TradeResult(BaseModel):
    """Trade execution result"""
    dry_run: bool = Field(..., alias="dryRun")
    action: str
    code: str
    full_code: str = Field(..., alias="fullCode")
    volume: int
    price_type: str = Field(..., alias="priceType")
    price: Optional[float] = None
    order_id: Optional[int] = Field(None, alias="orderId")
    order_time: Optional[str] = Field(None, alias="orderTime")
    estimated_amount: Optional[float] = Field(None, alias="estimatedAmount")
    cancel_result: Optional[int] = Field(None, alias="cancelResult")
    cancel_result_name: Optional[str] = Field(None, alias="cancelResultName")
    note: Optional[str] = None


# ============================================================================
# System Models
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    qmt_connected: bool = Field(..., alias="qmtConnected")
    xtquant_available: bool = Field(..., alias="xtquantAvailable")
    account_configured: bool = Field(..., alias="accountConfigured")


class DoctorCheckItem(BaseModel):
    """Single check item"""
    name: str
    ok: bool
    detail: str


class DoctorResponse(BaseModel):
    """Doctor diagnostics response"""
    checks: List[DoctorCheckItem]
    pass_count: int = Field(..., alias="pass")
    fail_count: int = Field(..., alias="fail")
    overall: str


class StatusResponse(BaseModel):
    """Server status response"""
    version: str
    uptime: str
    started_at: str = Field(..., alias="startedAt")
    requests_total: int = Field(..., alias="requestsTotal")
    requests_success: int = Field(..., alias="requestsSuccess")
    requests_failed: int = Field(..., alias="requestsFailed")
    last_error: Optional[str] = Field(None, alias="lastError")
