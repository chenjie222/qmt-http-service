"""Rate limiting middleware"""
import time
import logging
from typing import Dict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from qmt_server.config import get_config
except ImportError:
    from config import get_config

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}

    async def dispatch(self, request: Request, call_next):
        config = get_config()

        if not config.rate_limit_enabled:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                t for t in self.requests[client_ip]
                if now - t < 60
            ]
        else:
            self.requests[client_ip] = []

        # Check rate limit
        if len(self.requests.get(client_ip, [])) >= config.rate_limit_rpm:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Record request
        self.requests.setdefault(client_ip, []).append(now)

        return await call_next(request)