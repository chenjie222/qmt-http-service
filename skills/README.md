# QMT HTTP Service Skills

此目录包含 Claude Code 可用的技能文件。

## 安装使用

将技能文件复制到 Claude Code 的 skills 目录即可使用：

```bash
# Windows (PowerShell)
Copy-Item skills/qmt-api-client.md $env:USERPROFILE\.claude\skills\qmt-api-client.md

# macOS/Linux
cp skills/qmt-api-client.md ~/.claude/skills/qmt-api-client.md
```

或者复制整个目录：

```bash
# Windows
Copy-Item -Recurse skills $env:USERPROFILE\.claude\skills\qmt-api-client

# macOS/Linux
cp -r skills ~/.claude/skills/qmt-api-client
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

## 技能文件格式

技能文件使用以下 frontmatter 格式：

```markdown
---
name: skill-name
description: Brief description
version: 1.0.0
tags: [tag1, tag2]
---

# Skill Content
...
```

## 添加新技能

1. 创建新的 `.md` 文件
2. 添加 frontmatter 元数据
3. 编写技能内容
4. 复制到 `~/.claude/skills/` 目录