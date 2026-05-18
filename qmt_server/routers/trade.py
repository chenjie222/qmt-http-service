"""Trade router"""
import logging
from fastapi import APIRouter, HTTPException

try:
    from qmt_server.models.schemas import (
        APIResponse, BuyRequest, SellRequest, CancelRequest
    )
    from qmt_server.services.trade_service import get_trade_service
    from qmt_server.services.xtquant_service import get_xtquant_service
except ImportError:
    from models.schemas import (
        APIResponse, BuyRequest, SellRequest, CancelRequest
    )
    from services.trade_service import get_trade_service
    from services.xtquant_service import get_xtquant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trade", tags=["Trade"])


@router.post("/buy", response_model=APIResponse)
async def buy(request: BuyRequest):
    """Place buy order"""
    try:
        service = get_trade_service()
        xt_service = get_xtquant_service()

        full_code = xt_service._resolve_code(request.code) if xt_service.is_ready() else f"{request.code}.SZ"

        # Calculate estimated amount for dry run
        estimated_amount = request.volume * (request.price or 0)

        if not request.confirm:
            # Dry run mode
            return APIResponse(
                success=True,
                data={
                    "dryRun": True,
                    "action": "BUY",
                    "code": request.code,
                    "fullCode": full_code,
                    "volume": request.volume,
                    "priceType": request.price_type,
                    "price": request.price,
                    "estimatedAmount": estimated_amount,
                    "note": "confirm=false, dry run only, order not sent to QMT"
                },
                message="Dry run (order not placed)"
            )

        # Real order
        if not service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Trade service not ready"
            )

        result = service.buy(
            code=request.code,
            volume=request.volume,
            price_type=request.price_type,
            price=request.price,
            strategy_name=request.strategy_name,
            order_remark=request.order_remark
        )

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Order failed'))

        return APIResponse(
            success=True,
            data={
                "dryRun": False,
                "action": "BUY",
                "code": request.code,
                "fullCode": full_code,
                "volume": request.volume,
                "priceType": request.price_type,
                "price": request.price,
                "orderId": result['orderId'],
                "orderTime": None
            },
            message=f"Buy order submitted, orderId={result['orderId']}"
        )
    except Exception as e:
        logger.error(f"Error placing buy order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sell", response_model=APIResponse)
async def sell(request: SellRequest):
    """Place sell order"""
    try:
        service = get_trade_service()
        xt_service = get_xtquant_service()

        full_code = xt_service._resolve_code(request.code) if xt_service.is_ready() else f"{request.code}.SZ"

        estimated_amount = request.volume * (request.price or 0)

        if not request.confirm:
            return APIResponse(
                success=True,
                data={
                    "dryRun": True,
                    "action": "SELL",
                    "code": request.code,
                    "fullCode": full_code,
                    "volume": request.volume,
                    "priceType": request.price_type,
                    "price": request.price,
                    "estimatedAmount": estimated_amount,
                    "note": "confirm=false, dry run only, order not sent to QMT"
                },
                message="Dry run (order not placed)"
            )

        if not service.is_ready():
            raise HTTPException(status_code=503, detail="Trade service not ready")

        result = service.sell(
            code=request.code,
            volume=request.volume,
            price_type=request.price_type,
            price=request.price,
            strategy_name=request.strategy_name,
            order_remark=request.order_remark
        )

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Order failed'))

        return APIResponse(
            success=True,
            data={
                "dryRun": False,
                "action": "SELL",
                "code": request.code,
                "fullCode": full_code,
                "volume": request.volume,
                "priceType": request.price_type,
                "price": request.price,
                "orderId": result['orderId']
            },
            message=f"Sell order submitted, orderId={result['orderId']}"
        )
    except Exception as e:
        logger.error(f"Error placing sell order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel", response_model=APIResponse)
async def cancel(request: CancelRequest):
    """Cancel order"""
    try:
        service = get_trade_service()

        if not request.confirm:
            return APIResponse(
                success=True,
                data={
                    "dryRun": True,
                    "action": "CANCEL",
                    "orderId": request.order_id,
                    "note": "confirm=false, dry run only, order not cancelled"
                },
                message="Dry run (order not cancelled)"
            )

        if not service.is_ready():
            raise HTTPException(status_code=503, detail="Trade service not ready")

        result = service.cancel(request.order_id)

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Cancel failed'))

        return APIResponse(
            success=True,
            data={
                "dryRun": False,
                "action": "CANCEL",
                "orderId": request.order_id,
                "cancelResult": result['result'],
                "cancelResultName": result['resultName']
            },
            message="Cancel order success"
        )
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        raise HTTPException(status_code=500, detail=str(e))