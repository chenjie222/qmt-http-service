---
name: qmt-api-client
description: How to call QMT HTTP Server REST APIs for market data, account info, and trading. Use this skill whenever the user mentions QMT, xtquant, stock quotes, K-line data, tick data, market overview, account assets, positions, orders, trades, buy/sell orders, or any trading-related HTTP API calls — even if they don't explicitly ask for "QMT API" or mention the server by name.
---

# QMT HTTP API Client

Call QMT HTTP Server APIs to fetch market data, query accounts, and execute trades.

## Configuration

Edit `config.json` in this skill directory to configure server settings:

```json
{
  "server_url": "http://localhost:8080/api/v1",
  "timeout": {
    "system": 5,
    "quote": 10,
    "kline": 60,
    "stock_list": 120,
    "account": 10,
    "trade": 15
  }
}
```

**Environment variable override** (higher priority than config.json):

```bash
# Override server URL
$env:QMT_SERVER_URL="http://your-server:8080/api/v1"
```

**Priority**: Environment variable > config.json > default

## Base URL

Read from `config.json` or override via `QMT_SERVER_URL` environment variable.

## Response Format

All responses follow this envelope format:

```json
{
  "success": true,
  "timestamp": "2026-05-18T14:38:23",
  "data": { ... },
  "message": "操作成功"
}
```

Error responses:

```json
{
  "success": false,
  "timestamp": "...",
  "error": {
    "code": "QMT_NOT_CONNECTED",
    "message": "QMT 终端未运行或连接失败",
    "details": "..."
  }
}
```

---

## System APIs

### Health Check

```bash
curl http://localhost:8080/api/v1/system/health
```

Response fields: `status`, `xtquantLoaded`, `qmtConnected`, `tradeReady`

### Environment Diagnostics

```bash
curl http://localhost:8080/api/v1/system/doctor
```

Returns detailed environment status including paths, Python version, and QMT connection.

### Server Status

```bash
curl http://localhost:8080/api/v1/system/status
```

---

## Market APIs

### Get Stock Quote (Single)

```bash
curl "http://localhost:8080/api/v1/market/quote/000001"
```

Response fields: `code`, `fullCode`, `name`, `open`, `high`, `low`, `close`, `volume`, `amount`

### Get Stock Quote (Batch)

```bash
curl "http://localhost:8080/api/v1/market/quote?codes=000001,600519,300750"
```

Optional: `?names=true` to include stock names.

### Get K-Line Data

**Priority Rule**: If `start` + `end` provided, use time range mode (count ignored). Otherwise use count mode.

**Time Range Mode (Recommended for historical data)**:

```bash
curl "http://localhost:8080/api/v1/market/kline/000001?period=5m&start=20260301&end=20260501"
```

**Count Mode (For recent data)**:

```bash
curl "http://localhost:8080/api/v1/market/kline/000001?period=1d&count=100"
```

Parameters:
| Param | Values | Default | Notes |
|-------|--------|---------|-------|
| `period` | `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1w`, `1mon` | `1d` | K-line period |
| `start` | YYYYMMDD | - | Start date, higher priority than count |
| `end` | YYYYMMDD | - | End date, higher priority than count |
| `count` | 1-10000 | 100 | Number of bars, optional when start/end provided |

Response fields: `code`, `fullCode`, `period`, `count`, `kline[]` (date, open, high, low, close, volume, amount)

### Get Tick Data (Five-Level Quote)

```bash
# Single stock
curl "http://localhost:8080/api/v1/market/tick/000001"

# Batch
curl "http://localhost:8080/api/v1/market/tick?codes=000001,600519"
```

### Get Stock List

```bash
curl "http://localhost:8080/api/v1/market/stock-list"
```

Returns all stocks with code and name.

### Get Block List

```bash
curl "http://localhost:8080/api/v1/market/blocks"
```

### Get Market Overview (Index)

```bash
curl "http://localhost:8080/api/v1/market/market-overview"
```

Returns major indices: SH000001, SH000300, SZ399001, SZ399006.

---

## Account APIs

**Prerequisite**: Configure `QMT_USERDATA_PATH` and `QMT_ACCOUNT_ID` in `.env`.

### Get Account Asset

```bash
curl "http://localhost:8080/api/v1/account/asset"
```

Response: `total_asset`, `cash`, `market_value`, `account_type`

### Get Positions

```bash
curl "http://localhost:8080/api/v1/account/positions"
```

Response: `stock_code`, `volume`, `can_use_volume`, `market_value`, `cost_price`

### Get Orders

```bash
curl "http://localhost:8080/api/v1/account/orders"
```

### Get Trades

```bash
curl "http://localhost:8080/api/v1/account/trades"
```

---

## Trade APIs

**Prerequisite**: Same as Account APIs. QMT must enable "极速策略交易" feature.

**Safety**: All trade requests default to preview mode (`confirm: false`). Set `confirm: true` to execute.

### Buy Order

```bash
curl -X POST "http://localhost:8080/api/v1/trade/buy" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "000001",
    "volume": 100,
    "price_type": "FIX",
    "price": 10.55,
    "confirm": false
  }'
```

Price types: `FIX` (fixed price), `LATEST` (latest price), `LIMIT_UP` (limit up), `LIMIT_DOWN` (limit down)

### Sell Order

```bash
curl -X POST "http://localhost:8080/api/v1/trade/sell" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "000001",
    "volume": 100,
    "price_type": "LATEST",
    "confirm": false
  }'
```

### Cancel Order

```bash
curl -X POST "http://localhost:8080/api/v1/trade/cancel" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "12345",
    "confirm": true
  }'
```

---

## Python Client Example

```python
import json
import os
import requests
from pathlib import Path

# Load config.json
config_path = Path(__file__).parent / "config.json"
config = json.loads(config_path.read_text()) if config_path.exists() else {}

# Environment variable override
BASE_URL = os.environ.get("QMT_SERVER_URL", config.get("server_url", "http://localhost:8080/api/v1"))
TIMEOUT = config.get("timeout", {})

def get_quote(code: str) -> dict:
    """Get single stock quote."""
    resp = requests.get(f"{BASE_URL}/market/quote/{code}", timeout=TIMEOUT.get("quote", 10))
    return resp.json()

def get_kline(code: str, period: str = "1d", 
              start: str = None, end: str = None, count: int = None) -> dict:
    """Get K-line data. Use start/end for historical, count for recent."""
    params = {"period": period}
    if start and end:
        params["start"] = start
        params["end"] = end
    else:
        params["count"] = count
    resp = requests.get(f"{BASE_URL}/market/kline/{code}", params=params, timeout=60)
    return resp.json()

def get_asset() -> dict:
    """Get account asset."""
    resp = requests.get(f"{BASE_URL}/account/asset", timeout=10)
    return resp.json()

def buy(code: str, volume: int, price: float, confirm: bool = False) -> dict:
    """Buy order. confirm=True to execute."""
    resp = requests.post(
        f"{BASE_URL}/trade/buy",
        json={
            "code": code,
            "volume": volume,
            "price_type": "FIX",
            "price": price,
            "confirm": confirm
        },
        timeout=15
    )
    return resp.json()

# Usage examples
quote = get_quote("000001")
kline = get_kline("000001", "5m", start="20260301", end="20260501")
asset = get_asset()
result = buy("000001", 100, 10.5, confirm=False)  # Preview
```

---

## Timeout

Configure in `config.json` or use defaults:

| API | Timeout | Reason |
|-----|---------|--------|
| `/system/*` | 5s | Lightweight checks |
| `/market/quote` | 10s | Quick data fetch |
| `/market/kline` | 60s | First call downloads historical data |
| `/market/stock-list` | 120s | Large data download |
| `/account/*` | 10s | Account queries |
| `/trade/*` | 15s | Order execution |

---

## Error Codes

| Code | Meaning | HTTP Status |
|------|---------|-------------|
| `SUCCESS` | Success | 200 |
| `QMT_NOT_CONNECTED` | QMT not running | 503 |
| `XTQUANT_IMPORT_FAILED` | xtquant import failed | 500 |
| `INVALID_CODE` | Invalid stock code | 400 |
| `RATE_LIMITED` | Request rate exceeded | 429 |
| `ACCOUNT_NOT_CONFIGURED` | Account not configured | 503 |
| `ORDER_FAILED` | Order failed | 500 |

---

## Configuration

Server reads configuration from `.env` file in `qmt_server/` directory:

```ini
QMT_XTQUANT_PATH=D:/software/QMT/QMT交易端/bin.x64/Lib/site-packages
QMT_USERDATA_PATH=D:/software/QMT/QMT交易端模拟/userdata_mini
QMT_ACCOUNT_ID=your_account_id
QMT_ACCOUNT_TYPE=STOCK
QMT_SERVER_PORT=8080
QMT_RATE_LIMIT_RPM=60
```

---

## Checklist: Using QMT API

- [ ] Verify server is running: `curl http://localhost:8080/api/v1/system/health`
- [ ] Check QMT connection: `qmtConnected: true` in health response
- [ ] Set appropriate timeout (60s+ for K-line first call)
- [ ] Use `start/end` for historical K-line, `count` for recent
- [ ] Set `confirm: true` only when ready to execute trades
- [ ] Handle error codes appropriately in client code