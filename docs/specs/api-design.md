# QMT HTTP Server 设计文档

**版本**: 1.0
**日期**: 2026-05-11
**状态**: Draft

---

## 1. 项目概述

### 1.1 背景

TradingAgents-CN 当前集成 QMT 数据源通过本地 `xtquant` 库直接连接 QMT 终端，这要求 TradingAgents-CN 必须部署在 Windows 上且与 QMT 终端在同一机器。

为实现跨平台部署，将 QMT 连接逻辑抽取为独立的 HTTP Server：
- **Server 端**：部署在 Windows 上，直连 QMT 终端，暴露 HTTP API
- **Client 端**：TradingAgents-CN 通过 HTTP 调用获取数据，可部署在任意平台

### 1.2 架构

```
┌─────────────────────────────────────────────────────────┐
│  TradingAgents-CN (任意平台)                              │
│  ├── app/services/data_sources/qmt_adapter.py           │
│  │   └── HTTP Client → QMT Server                       │
│  └── 配置: QMT_SERVER_URL=http://windows-server:8080    │
└───────────────────────HTTP──────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  QMT Server (Windows)                                    │
│  ├── FastAPI 应用                                        │
│  ├── xtquant 本地连接 QMT 终端                           │
│  ├── qmt_server/                                         │
│  │   ├── main.py              (应用入口)                 │
│  │   ├── config.py            (配置管理)                 │
│  │   ├── routers/                                         │
│  │   │   ├── market.py        (行情接口)                 │
│  │   │   ├── account.py       (账户查询)                 │
│  │   │   ├── trade.py         (交易接口)                 │
│  │   │   └── system.py        (系统/诊断)                │
│  │   ├── services/                                        │
│  │   │   ├── xtquant_service.py (xtquant 封装)          │
│  │   │   └── trade_service.py  (交易封装)               │
│  │   └── models/                                          │
│  │       └── schemas.py       (Pydantic 模型)            │
│  └── scripts/config.json      (QMT 配置)                 │
└─────────────────────────────────────────────────────────┘
```

### 1.3 技术栈

- **Python**: 3.10 / 3.11（xtquant .pyd 限制）
- **Web 框架**: FastAPI
- **数据源**: xtquant (xtdata + xttrader)
- **运行平台**: Windows only（QMT 终端要求）
- **端口**: 8080（可配置）

---

## 2. 接口设计

### 2.1 基础 URL

```
http://{host}:{port}/api/v1/{module}/{action}
```

所有响应统一格式：

```json
{
  "success": true,
  "timestamp": "2026-05-11T15:30:00",
  "data": { ... },
  "message": "操作成功"
}
```

错误响应：

```json
{
  "success": false,
  "timestamp": "2026-05-11T15:30:00",
  "error": {
    "code": "QMT_NOT_CONNECTED",
    "message": "QMT 终端未运行或连接失败",
    "details": "..."
  }
}
```

---

## 3. 行情接口 (Market)

**Base URL**: `/api/v1/market`

### 3.1 实时行情快照 - 单只

**端点**: `GET /api/v1/market/quote/{code}`

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | string | 是 | 6位股票代码或完整代码，如 `000001` 或 `000001.SZ` |

**响应示例**:

```json
{
  "success": true,
  "timestamp": "2026-05-11T15:30:00",
  "data": {
    "code": "000001",
    "fullCode": "000001.SZ",
    "name": "平安银行",
    "open": 10.50,
    "high": 10.68,
    "low": 10.42,
    "close": 10.55,
    "preClose": 10.48,
    "change": 0.07,
    "changePct": 0.67,
    "volume": 125000000,
    "amount": 1318750000.00
  },
  "message": "获取 000001 行情成功"
}
```

---

### 3.2 实时行情快照 - 批量

**端点**: `GET /api/v1/market/quote`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `codes` | string | 是 | 股票代码列表，逗号分隔，如 `000001,600519,300750` |
| `names` | boolean | 否 | 是否返回股票名称，默认 `true` |

---

### 3.3 K线数据

**端点**: `GET /api/v1/market/kline/{code}`

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | string | 是 | 6位股票代码，如 `000001` |

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `period` | string | 否 | `1d` | K线周期：`1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1w`, `1mon` |
| `start` | string | 否 | - | 开始日期 YYYYMMDD，**优先级高于count** |
| `end` | string | 否 | - | 结束日期 YYYYMMDD，**优先级高于count** |
| `count` | integer | 否 | `100` | 返回K线数量（最多 10000），有start/end时可省略 |

**参数优先级规则**:

```
有 start + end → 按时间范围获取数据，count 参数可选（会被忽略）
无 start + end → 按 count 获取最近N条数据，count 默认100
```

**调用示例**:

```bash
# 方式1：使用时间范围获取历史数据（start/end优先级更高）
curl "http://localhost:8080/api/v1/market/kline/000001?period=5m&start=20260301&end=20260501"

# 方式2：使用count获取最近数据
curl "http://localhost:8080/api/v1/market/kline/000001?period=5m&count=20"

# 方式3：获取日线数据
curl "http://localhost:8080/api/v1/market/kline/000001?period=1d&count=100"
```

**响应示例（时间范围模式）**:

```json
{
  "success": true,
  "timestamp": "2026-05-18T14:38:23",
  "data": {
    "code": "000001",
    "fullCode": "000001.SZ",
    "name": "",
    "period": "5m",
    "count": 2064,
    "kline": [
      {
        "date": "20260302",
        "open": 10.85,
        "high": 10.86,
        "low": 10.81,
        "close": 10.82,
        "volume": 69484,
        "amount": 75229910.0
      },
      // ... 更多数据
    ]
  },
  "message": "Get 000001 2064 5m klines"
}
```

**响应示例（count模式）**:

```json
{
  "success": true,
  "timestamp": "2026-05-18T14:39:13",
  "data": {
    "code": "000001",
    "fullCode": "000001.SZ",
    "name": "",
    "period": "5m",
    "count": 10,
    "kline": [
      {
        "date": "20260518",
        "open": 10.88,
        "high": 10.88,
        "low": 10.87,
        "close": 10.87,
        "volume": 10169,
        "amount": 11057364.0
      }
      // ... 10条数据
    ]
  },
  "message": "Get 000001 10 5m klines"
}
```

**K线周期说明**:

| 周期 | 说明 | 每交易日条数 |
|------|------|-------------|
| `1m` | 1分钟 | 240条 |
| `5m` | 5分钟 | 48条 |
| `15m` | 15分钟 | 16条 |
| `30m` | 30分钟 | 8条 |
| `1h` | 1小时 | 4条 |
| `1d` | 日线 | 1条 |
| `1w` | 周线 | - |
| `1mon` | 月线 | - |

**注意事项**:
- 首次获取某股票某周期的历史数据时，需要先下载，可能耗时较长
- 建议客户端设置60秒以上超时
- 周线(1w)、月线(1mon)需要预先在QMT终端订阅或下载历史数据

---

### 3.4 五档盘口

**端点**: `GET /api/v1/market/tick/{code}`

---

### 3.5 股票列表

**端点**: `GET /api/v1/market/stock-list`

---

### 3.6 板块列表

**端点**: `GET /api/v1/market/blocks`

---

### 3.7 板块成分股

**端点**: `GET /api/v1/market/block-stocks`

---

### 3.8 大盘指数概览

**端点**: `GET /api/v1/market/market-overview`

---

## 4. 账户接口 (Account)

**Base URL**: `/api/v1/account`

**前置要求**: 需在 `config.json` 配置 `account_id` 和 `userdata_path`，且 QMT 已开启「极速策略交易」功能。

### 4.1 资产信息

**端点**: `GET /api/v1/account/asset`

### 4.2 持仓查询

**端点**: `GET /api/v1/account/positions`

### 4.3 委托查询

**端点**: `GET /api/v1/account/orders`

### 4.4 成交查询

**端点**: `GET /api/v1/account/trades`

---

## 5. 交易接口 (Trade)

**Base URL**: `/api/v1/trade`

**前置要求**: 同账户接口，且需在请求中带 `confirm=true` 才真正下单。

### 5.1 买入下单

**端点**: `POST /api/v1/trade/buy`

**请求体**:

```json
{
  "code": "000001",
  "volume": 1000,
  "price_type": "FIX",
  "price": 10.55,
  "strategy_name": "",
  "order_remark": "",
  "confirm": false
}
```

### 5.2 卖出下单

**端点**: `POST /api/v1/trade/sell`

### 5.3 撤单

**端点**: `POST /api/v1/trade/cancel`

---

## 6. 系统接口 (System)

**Base URL**: `/api/v1/system`

### 6.1 健康检查

**端点**: `GET /api/v1/system/health`

### 6.2 环境诊断

**端点**: `GET /api/v1/system/doctor`

### 6.3 Server 状态

**端点**: `GET /api/v1/system/status`

---

## 7. 错误码

| 错误码 | 含义 | HTTP 状态码 |
|--------|------|-------------|
| `SUCCESS` | 成功 | 200 |
| `QMT_NOT_CONNECTED` | QMT 终端未运行或连接失败 | 503 |
| `XTQUANT_IMPORT_FAILED` | xtquant 模块导入失败 | 500 |
| `INVALID_CODE` | 无效的股票代码 | 400 |
| `INVALID_PARAMETERS` | 参数错误 | 400 |
| `RATE_LIMITED` | 请求频率超限 | 429 |
| `ACCOUNT_NOT_CONFIGURED` | 账号未配置 | 503 |
| `ORDER_FAILED` | 下单失败 | 500 |
| `CANCEL_FAILED` | 撤单失败 | 500 |
| `INTERNAL_ERROR` | 内部错误 | 500 |

---

## 8. 配置

### 8.1 环境变量

| 变量 | 说明 |
|------|------|
| `QMT_XTQUANT_PATH` | xtquant 路径 |
| `QMT_USERDATA_PATH` | userdata 路径 |
| `QMT_ACCOUNT_ID` | 账号 ID |
| `QMT_SERVER_PORT` | Server 端口 |
| `QMT_LOG_LEVEL` | 日志级别 |

---

## 9. 接口性能与超时建议

### 9.1 超时配置建议

| 接口 | 建议超时 | 说明 |
|------|---------|------|
| `/system/health` | 5 秒 | 轻量级检查 |
| `/system/status` | 5 秒 | 轻量级查询 |
| `/market/quote/{code}` | 10 秒 | 单只行情 |
| `/market/quote` | 15 秒 | 批量行情 |
| `/market/kline/{code}` | 60 秒 | 首次调用需下载历史数据 |
| `/market/tick/{code}` | 10 秒 | 五档盘口 |
| `/market/stock-list` | 120 秒 | 首次调用需下载板块数据 |
| `/account/asset` | 10 秒 | 账户资产 |
| `/trade/buy` | 15 秒 | 买入下单 |

---

## 10. 客户端调用示例

### Python

```python
import requests

BASE_URL = "http://localhost:8080/api/v1"

# 健康检查
resp = requests.get(f"{BASE_URL}/system/health", timeout=5)
print(resp.json())

# 获取单只股票行情
resp = requests.get(f"{BASE_URL}/market/quote/000001", timeout=10)
print(resp.json())

# 获取批量行情
resp = requests.get(f"{BASE_URL}/market/quote?codes=000001,600519", timeout=15)
print(resp.json())

# 获取K线 - 使用时间范围（推荐用于历史数据）
resp = requests.get(
    f"{BASE_URL}/market/kline/000001?period=5m&start=20260301&end=20260501",
    timeout=90
)
data = resp.json()
print(f"获取 {data['data']['count']} 条K线数据")

# 获取K线 - 使用count（推荐用于最近数据）
resp = requests.get(
    f"{BASE_URL}/market/kline/000001?period=1d&count=100",
    timeout=60
)
print(resp.json())

# 获取五档盘口
resp = requests.get(f"{BASE_URL}/market/tick/000001", timeout=10)
print(resp.json())

# 获取大盘指数
resp = requests.get(f"{BASE_URL}/market/market-overview", timeout=10)
print(resp.json())

# 获取账户资产
resp = requests.get(f"{BASE_URL}/account/asset", timeout=10)
print(resp.json())

# 买入预演（confirm=False 不真正下单）
resp = requests.post(
    f"{BASE_URL}/trade/buy",
    json={
        "code": "000001",
        "volume": 100,
        "price_type": "FIX",
        "price": 10.5,
        "confirm": False
    },
    timeout=15
)
print(resp.json())

# 真正下单（confirm=True）
resp = requests.post(
    f"{BASE_URL}/trade/buy",
    json={
        "code": "000001",
        "volume": 100,
        "price_type": "LATEST",
        "confirm": True
    },
    timeout=15
)
print(resp.json())
```

### JavaScript / TypeScript

```javascript
const BASE_URL = "http://localhost:8080/api/v1";

// 获取K线 - 时间范围模式
async function getKlineByDateRange(code, period, start, end) {
  const url = `${BASE_URL}/market/kline/${code}?period=${period}&start=${start}&end=${end}`;
  const response = await fetch(url);
  return response.json();
}

// 获取K线 - count模式
async function getKlineByCount(code, period, count = 100) {
  const url = `${BASE_URL}/market/kline/${code}?period=${period}&count=${count}`;
  const response = await fetch(url);
  return response.json();
}

// 使用示例
const klines = await getKlineByDateRange("000001", "5m", "20260301", "20260501");
console.log(`获取 ${klines.data.count} 条K线`);
```

### curl 命令大全

```bash
# 系统接口
curl http://localhost:8080/api/v1/system/health
curl http://localhost:8080/api/v1/system/doctor
curl http://localhost:8080/api/v1/system/status

# 行情接口
curl "http://localhost:8080/api/v1/market/quote/000001"
curl "http://localhost:8080/api/v1/market/quote?codes=000001,600519,300750"
curl "http://localhost:8080/api/v1/market/kline/000001?period=5m&start=20260301&end=20260501"
curl "http://localhost:8080/api/v1/market/kline/000001?period=1d&count=100"
curl "http://localhost:8080/api/v1/market/tick/000001"
curl "http://localhost:8080/api/v1/market/tick?codes=000001,600519"
curl "http://localhost:8080/api/v1/market/market-overview"
curl "http://localhost:8080/api/v1/market/stock-list"
curl "http://localhost:8080/api/v1/market/blocks"

# 账户接口
curl "http://localhost:8080/api/v1/account/asset"
curl "http://localhost:8080/api/v1/account/positions"
curl "http://localhost:8080/api/v1/account/orders"

# 交易接口（预演）
curl -X POST "http://localhost:8080/api/v1/trade/buy" \
  -H "Content-Type: application/json" \
  -d '{"code":"000001","volume":100,"price_type":"FIX","price":10.5,"confirm":false}'

# 交易接口（真正下单）
curl -X POST "http://localhost:8080/api/v1/trade/buy" \
  -H "Content-Type: application/json" \
  -d '{"code":"000001","volume":100,"price_type":"LATEST","confirm":true}'
```