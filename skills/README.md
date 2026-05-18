# QMT HTTP Service Skills

此目录包含 Claude Code 可用的技能文件。

## 安装使用

将技能目录复制到 Claude Code 的 skills 目录：

```bash
# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills\qmt-api-client"
Copy-Item skills/qmt-api-client/SKILL.md "$env:USERPROFILE\.claude\skills\qmt-api-client\SKILL.md"

# macOS/Linux
mkdir -p ~/.claude/skills/qmt-api-client
cp skills/qmt-api-client/SKILL.md ~/.claude/skills/qmt-api-client/SKILL.md
```

安装后的目录结构：

```
~/.claude/skills/
└── qmt-api-client/
    └── SKILL.md    ← 技能文件（必须命名为 SKILL.md，大写）
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
    └── SKILL.md     ← 技能文件（固定命名，大写）
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