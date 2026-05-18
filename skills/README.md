# QMT HTTP Service Skills

此目录包含 Claude Code 可用的技能文件。

## 安装使用

将技能目录复制到 Claude Code 的 skills 目录：

```bash
# Windows (PowerShell)
Copy-Item -Recurse skills/qmt-api-client "$env:USERPROFILE\.claude\skills\qmt-api-client"

# macOS/Linux
cp -r skills/qmt-api-client ~/.claude/skills/qmt-api-client
```

安装后的目录结构：

```
~/.claude/skills/
└── qmt-api-client/
    ├── SKILL.md      ← 技能文件（必须命名为 SKILL.md，大写）
    └── config.json   ← 配置文件（server_url, timeout 等）
```

## 配置

编辑 `~/.claude/skills/qmt-api-client/config.json`：

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

或通过环境变量覆盖：

```bash
$env:QMT_SERVER_URL="http://your-server:8080/api/v1"
```

## 可用技能

### qmt-api-client

QMT HTTP Server REST API 调用指南。

**用途**：
- 获取行情数据（股票报价、K线、盘口）
- 查询账户信息（资产、持仓、委托、成交）
- 执行交易操作（买入、卖出、撤单）

**调用方式**：
- `/qmt-api-client` 命令
- Claude 自动识别涉及 QMT API 的任务

## 添加新技能

1. 在 `skills/` 下创建技能目录：`skills/your-skill-name/`
2. 在目录中创建 `SKILL.md` 文件（必须命名为 `SKILL.md`，大写）
3. 添加 frontmatter 元数据（`name` 和 `description` 必填）
4. 编写技能内容
5. 复制到 `~/.claude/skills/your-skill-name/SKILL.md`

目录结构规范：

```
skills/
├── README.md
└── qmt-api-client/
    ├── SKILL.md     ← 技能文件（固定命名，大写）
    └── config.json  ← 配置文件（可选）
```

## 技能文件格式

技能文件使用以下 frontmatter 格式：

```markdown
---
name: skill-name
description: When to trigger and what it does. Make it "pushy" — include specific scenarios even if user doesn't explicitly name the skill.
---

# Skill Content
...
```