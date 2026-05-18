"""Market data router"""
import logging
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException

try:
    from qmt_server.models.schemas import (
        APIResponse, SubscribeRequest
    )
    from qmt_server.services.xtquant_service import get_xtquant_service
except ImportError:
    from models.schemas import (
        APIResponse, SubscribeRequest
    )
    from services.xtquant_service import get_xtquant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/quote/{code}", response_model=APIResponse)
async def get_quote_single(code: str):
    """Get single stock quote"""
    try:
        service = get_xtquant_service()
        data = service.get_quote(code)

        if data is None:
            raise HTTPException(status_code=404, detail=f"Quote not found for {code}")

        return APIResponse(
            success=True,
            data=data,
            message=f"Get quote for {code}"
        )
    except Exception as e:
        logger.error(f"Error getting quote for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote", response_model=APIResponse)
async def get_quote_batch(
    codes: str = Query(..., description="Comma-separated stock codes"),
    names: bool = Query(True, description="Include stock names")
):
    """Get batch stock quotes"""
    try:
        service = get_xtquant_service()
        code_list = [c.strip() for c in codes.split(',')]
        quotes = service.get_quotes_batch(code_list)

        return APIResponse(
            success=True,
            data={"total": len(quotes), "quotes": quotes},
            message=f"Get {len(quotes)} stock quotes"
        )
    except Exception as e:
        logger.error(f"Error getting batch quotes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kline/{code}", response_model=APIResponse)
async def get_kline(
    code: str,
    period: str = Query('1d', description="Period: 1m,5m,15m,30m,1h,1d,1w,1mon"),
    start: Optional[str] = Query(None, description="Start date YYYYMMDD (优先级高于count)"),
    end: Optional[str] = Query(None, description="End date YYYYMMDD (优先级高于count)"),
    count: Optional[int] = Query(None, ge=1, le=10000, description="返回条数，有start/end时可省略"),
    download: bool = Query(True, description="Download history data first")
):
    """Get Kline data

    优先级：start/end > count
    - 有start/end：按时间范围获取，count可不填
    - 无start/end：按count获取最近数据，count默认100
    """
    try:
        service = get_xtquant_service()

        # 有start/end时优先使用时间范围，无start/end时使用count
        effective_count = count if count is not None else 100

        data = service.get_kline(code, period, effective_count, start, end)

        if data is None:
            raise HTTPException(status_code=404, detail=f"Kline not found for {code}")

        actual_count = data.get('count', 0)
        return APIResponse(
            success=True,
            data=data,
            message=f"Get {code} {actual_count} {period} klines"
        )
    except Exception as e:
        logger.error(f"Error getting kline for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tick/{code}", response_model=APIResponse)
async def get_tick_single(code: str):
    """Get five-level tick data"""
    try:
        service = get_xtquant_service()
        data = service.get_tick(code)

        if data is None:
            raise HTTPException(status_code=404, detail=f"Tick not found for {code}")

        return APIResponse(
            success=True,
            data=data,
            message=f"Get {code} tick"
        )
    except Exception as e:
        logger.error(f"Error getting tick for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tick", response_model=APIResponse)
async def get_tick_batch(codes: str = Query(..., description="Comma-separated codes")):
    """Get batch tick data"""
    try:
        service = get_xtquant_service()
        code_list = [c.strip() for c in codes.split(',')]
        ticks = [service.get_tick(c) for c in code_list]
        ticks = [t for t in ticks if t is not None]

        return APIResponse(
            success=True,
            data={"total": len(ticks), "ticks": ticks},
            message=f"Get {len(ticks)} tick data"
        )
    except Exception as e:
        logger.error(f"Error getting batch ticks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-list", response_model=APIResponse)
async def get_stock_list(
    sync: bool = Query(True, description="Sync sector data first"),
    market: str = Query('all', description="Filter by market: sh,sz,bj,all")
):
    """Get all stock list"""
    try:
        service = get_xtquant_service()
        stocks = service.get_stock_list(sync)

        # Filter by market if specified
        if market != 'all':
            stocks = [s for s in stocks if s['market'].lower() == market.lower()]

        return APIResponse(
            success=True,
            data={
                "total": len(stocks),
                "stocks": stocks[:100],  # Limit response size
                "synced": sync,
                "blockCount": len(service.get_sectors())
            },
            message=f"Get {len(stocks)} stocks"
        )
    except Exception as e:
        logger.error(f"Error getting stock list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blocks", response_model=APIResponse)
async def get_blocks(
    keyword: Optional[str] = Query(None, description="Filter keyword"),
    type: str = Query('all', description="Block type: industry,concept,index,all"),
    sync: bool = Query(False, description="Force re-sync"),
    limit: int = Query(200, ge=1, le=1000)
):
    """Get block/sector list"""
    try:
        service = get_xtquant_service()

        if sync:
            service.download_sector_data()

        blocks = service.get_sectors()

        if keyword:
            blocks = [b for b in blocks if keyword in b]

        return APIResponse(
            success=True,
            data={
                "total": len(blocks),
                "returned": min(limit, len(blocks)),
                "blocks": blocks[:limit]
            },
            message=f"Get {len(blocks)} blocks"
        )
    except Exception as e:
        logger.error(f"Error getting blocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/block-stocks", response_model=APIResponse)
async def get_block_stocks(
    block: str = Query(..., description="Block name"),
    limit: int = Query(50, ge=1, le=500)
):
    """Get stocks in a block"""
    try:
        service = get_xtquant_service()
        stocks = service.get_block_stocks(block)

        return APIResponse(
            success=True,
            data={
                "block": block,
                "total": len(stocks),
                "stocks": stocks[:limit]
            },
            message=f"Get {len(stocks)} stocks from {block}"
        )
    except Exception as e:
        logger.error(f"Error getting block stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/finance/{code}", response_model=APIResponse)
async def get_finance(
    code: str,
    tables: str = Query('all', description="Tables: Income,Balance,CashFlow,Capital,PershareIndex,all"),
    limit: int = Query(4, ge=1, le=20)
):
    """Get financial data (placeholder)"""
    # TODO: Implement with xtdata.download_financial_data
    return APIResponse(
        success=True,
        data={"code": code, "tables": {}, "note": "Not yet implemented"},
        message="Financial data endpoint (placeholder)"
    )


@router.get("/market-overview", response_model=APIResponse)
async def get_market_overview():
    """Get market overview"""
    try:
        service = get_xtquant_service()
        # Get major index quotes
        indices = ['000001.SH', '399001.SZ', '399006.SZ']
        quotes = []

        for idx in indices:
            code = idx.split('.')[0]
            q = service.get_quote(code)
            if q:
                quotes.append(q)

        return APIResponse(
            success=True,
            data={"indexes": quotes},
            message="Market overview"
        )
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading-dates", response_model=APIResponse)
async def get_trading_dates(
    start: str = Query(..., description="Start date YYYYMMDD"),
    end: str = Query(..., description="End date YYYYMMDD")
):
    """Get trading dates (placeholder)"""
    # TODO: Implement with xtdata.get_trading_dates
    return APIResponse(
        success=True,
        data={"start": start, "end": end, "tradingDays": [], "count": 0},
        message="Trading dates endpoint (placeholder)"
    )


@router.get("/instrument/{code}", response_model=APIResponse)
async def get_instrument(code: str):
    """Get instrument detail"""
    try:
        service = get_xtquant_service()
        quote = service.get_quote(code)

        if quote is None:
            raise HTTPException(status_code=404, detail=f"Instrument not found: {code}")

        # Build instrument detail from quote
        instrument = {
            "code": code,
            "fullCode": quote['fullCode'],
            "name": quote.get('name', ''),
            "type": "股票",
            "exchange": quote['fullCode'].split('.')[1],
            "exchangeName": service._get_market_name(quote['fullCode']),
            "listedDate": None,
            "delisted": False
        }

        return APIResponse(
            success=True,
            data=instrument,
            message=f"Get instrument {code}"
        )
    except Exception as e:
        logger.error(f"Error getting instrument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscribe", response_model=APIResponse)
async def subscribe(request: SubscribeRequest):
    """Subscribe to tick data (blocking mode)"""
    try:
        service = get_xtquant_service()
        start_time = asyncio.get_event_loop().time()
        ticks = []

        # Blocking wait for specified seconds
        while asyncio.get_event_loop().time() - start_time < request.seconds:
            for code in request.codes:
                tick = service.get_tick(code)
                if tick:
                    ticks.append(tick)
            await asyncio.sleep(0.5)

        duration = int(asyncio.get_event_loop().time() - start_time)

        return APIResponse(
            success=True,
            data={
                "subscribed": request.codes,
                "duration": duration,
                "tickCount": len(ticks),
                "ticks": ticks
            },
            message=f"Subscribe {len(request.codes)} stocks for {duration}s, got {len(ticks)} ticks"
        )
    except Exception as e:
        logger.error(f"Error in subscribe: {e}")
        raise HTTPException(status_code=500, detail=str(e))