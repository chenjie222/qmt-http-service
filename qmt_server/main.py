"""QMT HTTP Server main entry point"""
import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Support both standalone and package mode
try:
    # Try package mode first (when running from project root)
    from qmt_server.config import get_config, reload_config
    from qmt_server.routers import market_router, account_router, trade_router, system_router
    from qmt_server.middleware.rate_limit import RateLimitMiddleware
    from qmt_server.services.xtquant_service import get_xtquant_service
    from qmt_server.services.trade_service import get_trade_service
except ImportError:
    # Fall back to standalone mode (when running from qmt_server directory)
    from config import get_config, reload_config
    from routers import market_router, account_router, trade_router, system_router
    from middleware.rate_limit import RateLimitMiddleware
    from services.xtquant_service import get_xtquant_service
    from services.trade_service import get_trade_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("QMT Server starting up...")
    config = get_config()

    # Log configuration
    logger.info(f"Server config: host={config.host}, port={config.port}")
    logger.info(f"QMT config: xtquant_path={config.xtquant_path}, account_id={config.account_id}")

    # Try to connect to xtquant
    try:
        xt_service = get_xtquant_service()
        if xt_service.connect():
            logger.info("Connected to QMT via xtquant")
        else:
            logger.warning("Failed to connect to QMT - check if QMT terminal is running")
    except Exception as e:
        logger.error(f"Failed to initialize xtquant: {e}")

    # Try to connect to xttrader (if configured)
    if config.account_id and config.userdata_path:
        try:
            trade_service = get_trade_service()
            if trade_service.connect():
                logger.info("Connected to xttrader")
            else:
                logger.warning("Failed to connect to xttrader")
        except Exception as e:
            logger.error(f"Failed to initialize xttrader: {e}")

    yield

    # Shutdown
    logger.info("QMT Server shutting down...")
    try:
        trade_service = get_trade_service()
        trade_service.disconnect()
    except:
        pass


# Create FastAPI app
app = FastAPI(
    title="QMT HTTP Server",
    description="HTTP API wrapper for QMT (Quantitative Trading) xtquant library",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limit middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(market_router, prefix="/api/v1")
app.include_router(account_router, prefix="/api/v1")
app.include_router(trade_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return {
        "message": "QMT HTTP Server",
        "docs": "/docs",
        "health": "/api/v1/system/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "timestamp": "",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc)
            }
        }
    )


def main():
    """Main entry point"""
    config = get_config()

    import uvicorn
    uvicorn.run(
        "qmt_server.main:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower()
    )


if __name__ == "__main__":
    main()