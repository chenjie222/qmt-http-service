# 证券详情接口扩容设计

**日期**: 2026-05-26
**状态**: Draft
**驱动**: 用户需要流通股本数据计算换手率等指标

---

## 1. 背景

当前 `/api/v1/market/instrument/{code}` 接口仅返回基础信息（code、name、exchange），缺少流通股本（FloatVolume）和总股本（TotalVolume）。xtquant 的 `get_instrument_detail()` 直接提供这两个字段，无需额外下载，调用成本极低。

## 2. 方案

**选型：方案 A — 扩展现有 `/instrument/{code}` 接口**

在现有 InstrumentDetail 响应中添加 `floatVolume` 和 `totalVolume` 两个字段。不改动路由结构，不新增端点。

## 3. 数据流

```
客户端 → GET /api/v1/market/instrument/000001
  → market.py router → service.get_instrument_detail("000001")
    → xtquant_service.py → xtdata.get_instrument_detail("000001.SZ")
      → 返回 dict { FloatVolume, TotalVolume, InstrumentName, ... }
    → 解析为返回 dict { floatVolume, totalVolume, name, type, ... }
  → APIResponse { data: { ... } }
```

失败时 fallback：quote 数据构造基础信息 + floatVolume/totalVolume 设为 null。

## 4. 改动清单

### 4.1 `qmt_server/models/schemas.py`

在 `InstrumentDetail` 类末尾加两个字段：

```python
float_volume: Optional[float] = Field(None, alias="floatVolume")
total_volume: Optional[float] = Field(None, alias="totalVolume")
```

- `Optional[float]` — 指数、基金等无股本数据的证券返回 null
- `alias="floatVolume"` — 保持 JSON camelCase 风格

### 4.2 `qmt_server/services/xtquant_service.py`

新增方法：

```python
def get_instrument_detail(self, code: str) -> Optional[Dict]:
```

实现：
- `_ensure_xtdata()` + `self._resolve_code(code)` 遵循现有模式
- 调用 `xtdata.get_instrument_detail(full_code)`
- 安全读取字段：`FloatVolume`, `TotalVolume`, `InstrumentName`, `InstrumentType`, `ListedDate`, `IsDelisting`, `ExchangeID`
- 全部用 `.get()` 兜底，不会因缺字段崩溃
- 失败返回 None

### 4.3 `qmt_server/routers/market.py`

重写 `get_instrument` 路由：
- 主路径：`service.get_instrument_detail(code)`
- fallback：当返回 None 时，从 quote 构造基础数据 + `floatVolume: null, totalVolume: null`
- 返回 dict key 用 camelCase 匹配 InstrumentDetail schema alias

### 4.4 `docs/specs/api-design.md`

- 在 3.8（大盘指数概览）后新增 **3.9 证券详情** 章节
- 参数表、响应示例、字段说明（含 floatVolume/totalVolume）
- 更新 9.1 超时表、10. curl 示例

## 5. 风险

- **字段名不匹配**：xtdata 返回字段名若有变化，`.get()` 兜底安全
- **同步阻塞**：`get_instrument_detail` 是同步调用（跟其他方法一致），后续如需优化可统一迁入线程池
- **指数无股本**：`FloatVolume` 为 null，JSON 输出 `null`

## 6. 验证

1. `GET /api/v1/market/instrument/000001` → 返回含 floatVolume/totalVolume
2. `GET /api/v1/market/instrument/000001.SH` → 指数返回 floatVolume=null
3. `GET /api/v1/market/instrument/INVALID` → 404
4. 检查 API docs 渲染（/docs 页面 + api-design.md 格式）