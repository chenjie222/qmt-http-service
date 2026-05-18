"""Account router"""
import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

try:
    from qmt_server.models.schemas import APIResponse
    from qmt_server.services.trade_service import get_trade_service
except ImportError:
    from models.schemas import APIResponse
    from services.trade_service import get_trade_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/asset", response_model=APIResponse)
async def get_asset():
    """Get account asset information"""
    try:
        service = get_trade_service()

        if not service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Account not configured or trade service not connected"
            )

        asset = service.get_asset()

        if asset is None:
            raise HTTPException(status_code=404, detail="Asset information not available")

        return APIResponse(
            success=True,
            data=asset,
            message="Asset information"
        )
    except Exception as e:
        logger.error(f"Error getting asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=APIResponse)
async def get_positions(
    code: Optional[str] = Query(None, description="Filter by stock code")
):
    """Get positions"""
    try:
        service = get_trade_service()

        if not service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Account not configured or trade service not connected"
            )

        positions = service.get_positions(code)

        return APIResponse(
            success=True,
            data={"positions": positions, "total": len(positions)},
            message="Positions query"
        )
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", response_model=APIResponse)
async def get_orders(
    cancelable_only: bool = Query(False, alias="cancelable_only")
):
    """Get orders"""
    try:
        service = get_trade_service()

        if not service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Account not configured or trade service not connected"
            )

        orders = service.get_orders(cancelable_only)

        return APIResponse(
            success=True,
            data={"orders": orders, "total": len(orders)},
            message="Today's orders"
        )
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades", response_model=APIResponse)
async def get_trades():
    """Get trades"""
    try:
        service = get_trade_service()

        if not service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Account not configured or trade service not connected"
            )

        trades = service.get_trades()

        return APIResponse(
            success=True,
            data={"trades": trades, "total": len(trades)},
            message="Today's trades"
        )
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))