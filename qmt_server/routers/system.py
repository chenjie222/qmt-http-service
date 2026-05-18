"""System router"""
import sys
import platform
import logging
import time
from datetime import datetime
from typing import List, Dict
from fastapi import APIRouter, HTTPException

try:
    from qmt_server.models.schemas import (
        APIResponse, DoctorCheckItem
    )
    from qmt_server.services.xtquant_service import get_xtquant_service, is_xtquant_available
    from qmt_server.services.trade_service import get_trade_service, _xtt_available
    from qmt_server.config import get_config
except ImportError:
    from models.schemas import (
        APIResponse, DoctorCheckItem
    )
    from services.xtquant_service import get_xtquant_service, is_xtquant_available
    from services.trade_service import get_trade_service, _xtt_available
    from config import get_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["System"])

# Server startup time
START_TIME = datetime.now()

# Request counters
REQUESTS_TOTAL = 0
REQUESTS_SUCCESS = 0
REQUESTS_FAILED = 0
LAST_ERROR: str = ""


def increment_request(success: bool, error: str = ""):
    """Increment request counters"""
    global REQUESTS_TOTAL, REQUESTS_SUCCESS, REQUESTS_FAILED, LAST_ERROR
    REQUESTS_TOTAL += 1
    if success:
        REQUESTS_SUCCESS += 1
    else:
        REQUESTS_FAILED += 1
        LAST_ERROR = f"{datetime.now().isoformat()} {error}"


@router.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint"""
    try:
        xt_service = get_xtquant_service()
        config = get_config()

        qmt_connected = xt_service.is_ready()
        xtquant_available = is_xtquant_available()
        account_configured = bool(config.account_id and config.userdata_path)

        status = "healthy" if qmt_connected else "degraded"

        return APIResponse(
            success=True,
            data={
                "status": status,
                "qmtConnected": qmt_connected,
                "xtquantAvailable": xtquant_available,
                "accountConfigured": account_configured
            },
            message="System healthy" if status == "healthy" else "System degraded - QMT not connected"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doctor", response_model=APIResponse)
async def doctor():
    """Environment diagnostics"""
    checks: List[Dict] = []
    config = get_config()

    # 1. Platform check
    platform_ok = sys.platform == "win32"
    checks.append({
        "name": "平台检查",
        "ok": platform_ok,
        "detail": f"Windows" if platform_ok else f"{sys.platform} (QMT仅支持Windows)"
    })

    # 2. Python version check
    py_version = platform.python_version()
    version_ok = py_version.startswith("3.10") or py_version.startswith("3.11")
    checks.append({
        "name": "Python版本",
        "ok": version_ok,
        "detail": f"{py_version} {'✓' if version_ok else 'xtquant可能需要3.10/3.11'}"
    })

    # 3. xtquant path check
    path_ok = bool(config.xtquant_path)
    checks.append({
        "name": "xtquant路径配置",
        "ok": path_ok,
        "detail": config.xtquant_path if path_ok else "未配置 (QMT_XTQUANT_PATH)"
    })

    # 4. xtquant import check
    import_ok = is_xtquant_available()
    checks.append({
        "name": "xtquant导入",
        "ok": import_ok,
        "detail": "导入成功" if import_ok else "导入失败"
    })

    # 5. QMT connection check
    conn_ok = False
    conn_detail = "未测试"
    if import_ok:
        try:
            xt_service = get_xtquant_service()
            conn_ok = xt_service.connect()
            conn_detail = "QMT终端连接成功" if conn_ok else "QMT终端未运行"
        except Exception as e:
            conn_detail = str(e)

    checks.append({
        "name": "QMT终端连接",
        "ok": conn_ok,
        "detail": conn_detail
    })

    # 6. Account configuration check
    account_ok = bool(config.account_id and config.userdata_path)
    checks.append({
        "name": "账号配置",
        "ok": account_ok,
        "detail": f"account_id: {config.account_id[:4]}****" if account_ok else "未配置"
    })

    pass_count = sum(1 for c in checks if c["ok"])
    fail_count = len(checks) - pass_count
    overall = "pass" if fail_count == 0 else "fail" if fail_count > 1 else "warning"

    return APIResponse(
        success=True,
        data={
            "checks": checks,
            "pass": pass_count,
            "fail": fail_count,
            "overall": overall
        },
        message=f"Diagnostics complete: {overall}"
    )


@router.get("/status", response_model=APIResponse)
async def status():
    """Server status"""
    uptime = datetime.now() - START_TIME
    days = uptime.days
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds // 60) % 60
    uptime_str = f"{days}d{hours}h{minutes}m"

    return APIResponse(
        success=True,
        data={
            "version": "1.0.0",
            "uptime": uptime_str,
            "startedAt": START_TIME.isoformat(),
            "requestsTotal": REQUESTS_TOTAL,
            "requestsSuccess": REQUESTS_SUCCESS,
            "requestsFailed": REQUESTS_FAILED,
            "lastError": LAST_ERROR if LAST_ERROR else None
        },
        message="Server status"
    )