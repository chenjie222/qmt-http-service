# QMT HTTP Server

基于 FastAPI 的 QMT 行情交易 HTTP 服务，将 QMT 终端功能封装为 REST API，支持跨平台调用。

---

## 目录

- [环境要求](#环境要求)
- [快速启动](#快速启动)
- [配置说明](#配置说明)
- [运行方式](#运行方式)
- [接口文档](#接口文档)
- [项目结构](#项目结构)
- [常见问题](#常见问题)

---

## 环境要求

| 项目 | 要求 | 说明 |
|------|------|------|
| 操作系统 | **Windows** | QMT 终端仅支持 Windows |
| Python | **3.10 / 3.11** | xtquant .pyd 限制，不支持 3.12+ |
| QMT 终端 | **已安装并运行** | 国金/迅投 QMT 量化交易终端 |
| 网络 | **本地/局域网** | 默认监听 0.0.0.0:8080 |

---

## 快速启动

### 1. 安装依赖

```bash
cd qmt-http-service
pip install -r qmt_server/requirements.txt
```

### 2. 配置环境变量

```powershell
# 必需：xtquant 路径（根据实际安装位置调整）
$env:QMT_XTQUANT_PATH="D:/software/QMT/QMT交易端/bin.x64/Lib/site-packages"

# 可选：交易功能配置（如不使用交易接口，可不配置）
$env:QMT_USERDATA_PATH="D:/software/QMT/QMT交易端模拟/userdata_mini"
$env:QMT_ACCOUNT_ID="your_account_id"

# 可选：服务端口号（默认 8080）
$env:QMT_SERVER_PORT="8080"
```

### 3. 启动服务

```bash
# 使用 uvicorn 启动
python -m uvicorn qmt_server.main:app --host 0.0.0.0 --port 8080 --log-level info

# 或者直接运行
cd qmt_server
python main.py
```

### 4. 验证启动

```bash
# 健康检查
curl http://localhost:8080/api/v1/system/health

# 环境诊断
curl http://localhost:8080/api/v1/system/doctor
```

---

## 配置说明

### 环境变量

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `QMT_XTQUANT_PATH` | ✅ | - | xtquant 库路径，含 `xtquant` 文件夹 |
| `QMT_USERDATA_PATH` | ❌ | - | QMT userdata_mini 路径（交易功能必需）|
| `QMT_ACCOUNT_ID` | ❌ | - | QMT 账号 ID（交易功能必需）|
| `QMT_SERVER_PORT` | ❌ | `8080` | HTTP 服务端口号 |

### 查找 xtquant 路径

在 QMT 终端安装目录中查找：

```
QMT安装目录/
├── bin.x64/
│   └── Lib/
│       └── site-packages/
│           └── xtquant/          ← 这个就是
│               ├── __init__.py
│               ├── xtdata.py
│               └── xttrader.py
```

### 查找 userdata_mini 路径

模拟交易用户数据目录：

```
QMT安装目录/
├── 国金QMT交易端模拟/           ← Mini 模式
│   └── userdata_mini/          ← 使用这个
│       ├── account.dat
│       └── ...
```

---

## 运行方式

### 开发模式（热重载）

```bash
python -m uvicorn qmt_server.main:app --host 0.0.0.0 --port 8080 --reload --log-level debug
```

### 后台运行（Windows）

```powershell
# 使用 PowerShell 后台运行
Start-Process python -ArgumentList "-m uvicorn qmt_server.main:app --host 0.0.0.0 --port 8080" -WindowStyle Hidden
```

---

## 接口文档

### 在线文档（启动后访问）

| 文档类型 | 地址 |
|----------|------|
| Swagger UI | http://localhost:8080/docs |
| ReDoc | http://localhost:8080/redoc |
| OpenAPI JSON | http://localhost:8080/openapi.json |

### 主要接口

#### 系统接口 `/api/v1/system`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/doctor` | 环境诊断 |
| GET | `/status` | 服务器状态 |

#### 行情接口 `/api/v1/market`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/quote/{code}` | 单只行情 |
| GET | `/quote?codes=xxx,yyy` | 批量行情 |
| GET | `/kline/{code}` | K线数据（支持时间范围/count两种模式） |
| GET | `/tick/{code}` | 五档盘口 |
| GET | `/tick?codes=xxx,yyy` | 批量盘口 |
| GET | `/stock-list` | 股票列表 |
| GET | `/blocks` | 板块列表 |
| GET | `/market-overview` | 大盘指数 |

**K线接口参数优先级**:

```
有 start + end → 按时间范围获取，count 可省略
无 start + end → 按 count 获取最近数据，count 默认100
```

**K线调用示例**:

```bash
# 使用时间范围获取历史数据（推荐）
curl "http://localhost:8080/api/v1/market/kline/000001?period=5m&start=20260301&end=20260501"

# 使用count获取最近数据
curl "http://localhost:8080/api/v1/market/kline/000001?period=1d&count=100"
```

#### 账户接口 `/api/v1/account`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/asset` | 账户资产 |
| GET | `/positions` | 持仓查询 |
| GET | `/orders` | 委托查询 |
| GET | `/trades` | 成交查询 |

#### 交易接口 `/api/v1/trade`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/buy` | 买入下单 |
| POST | `/sell` | 卖出下单 |
| POST | `/cancel` | 撤单 |

**重要**：交易接口默认预演模式，需加 `confirm: true` 才真正下单！

---

## 设计文档

详细的 API 设计文档位于 `docs/specs/api-design.md`，包含：
- 完整接口定义
- 请求/响应格式
- 错误码说明
- 超时建议
- 客户端调用示例

---

## 项目结构

```
qmt-http-service/
├── README.md                   # 本文档
├── docs/
│   └── specs/
│       └── api-design.md       # API 设计文档
└── qmt_server/
    ├── __init__.py
    ├── main.py                 # FastAPI 入口
    ├── config.py               # 配置加载
    ├── requirements.txt        # 依赖
    ├── routers/                # 路由
    │   ├── __init__.py
    │   ├── system.py           # 系统接口
    │   ├── market.py           # 行情接口
    │   ├── account.py          # 账户接口
    │   └── trade.py            # 交易接口
    ├── services/               # 服务层
    │   ├── __init__.py
    │   ├── xtquant_service.py  # xtdata 封装
    │   └── trade_service.py    # xttrader 封装
    ├── models/                 # 数据模型
    │   ├── __init__.py
    │   └── schemas.py          # Pydantic 模型
    └── middleware/             # 中间件
        ├── __init__.py
        └── rate_limit.py       # 限流
```

---

## 常见问题

### 1. 启动报错 `ModuleNotFoundError: No module named 'xtquant'`

**解决**：环境变量 `QMT_XTQUANT_PATH` 设置错误，请指向含 `xtquant` 文件夹的目录。

```powershell
# 错误示例
$env:QMT_XTQUANT_PATH="D:/software/QMT/QMT交易端/bin.x64/Lib/site-packages/xtquant"

# 正确示例
$env:QMT_XTQUANT_PATH="D:/software/QMT/QMT交易端/bin.x64/Lib/site-packages"
```

### 2. 健康检查返回 `qmtConnected: false`

**解决**：QMT 终端未运行，请先启动 QMT 终端并登录。

### 3. 交易接口报错 "Trade service not ready"

**解决**：未配置交易账号，需设置 `QMT_USERDATA_PATH` 和 `QMT_ACCOUNT_ID`。

### 4. 端口冲突

**解决**：更换端口：

```powershell
$env:QMT_SERVER_PORT="8081"
python -m uvicorn qmt_server.main:app --host 0.0.0.0 --port 8081
```

### 5. K线接口超时

**解决**：首次获取需下载历史数据，建议客户端设置 60 秒超时。

---

## 许可证

MIT License