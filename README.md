# LogRelay

[中文](#中文) | [English](#english)

---

<a id="english"></a>

## LogRelay — Cross-Tool Session Logging & Relay System

Seamless session continuity across AI coding tools. Design APIs in Trae, continue in Claude Code — LogRelay automatically carries forward unfinished tasks and key decisions, zero manual context-switching required.

### Supported Tools

| Tool | Mode | Auto-trigger | Config Location |
|------|------|-------------|-----------------|
| **Claude Code** | Fully automatic | SessionStart hook + CLAUDE.md rules | `.claude/settings.json` |
| **Trae / Trae CN** | Fully automatic | SessionStart hook | `.trae/skills/logrelay/` |
| **Codex** | Fully automatic | SessionStart hook | `.codex/hooks.json` |
| **Cursor** | Semi-automatic | `/start-log` `/end-log` commands | `.cursor/commands/` |
| **Qoder** | Semi-automatic | `/start-log` `/end-log` commands | `.qoder/commands/` |
| **Antigravity** | Semi-automatic | `/start-log` `/end-log` workflows | `.agent/workflows/` |

### Key Features

- **Dual-layer session logs** — Compact summary for automatic context injection; full conversation transcript available on demand, separated by `%%`
- **Cross-tool relay** — `STATUS.md` shares unfinished tasks across tools; next tool auto-detects and picks up where the previous one left off
- **Cross-project support** — Logs follow projects; `projectA/` and `projectB/` are independent
- **Cross-platform** — Windows + macOS; re-run `install.py` after switching platforms
- **Obsidian plugin** — Relay chain visualization, cross-project search, statistics dashboard

### Quick Start

**Prerequisites:** Python 3.8+, Node.js 16+ (optional, for Obsidian plugin)

```bash
# Install everything (all tools + Obsidian plugin)
python3 install.py

# Install specific tools only
python3 install.py --tools claude-code,trae

# Build and deploy Obsidian plugin only
python3 install.py --plugin-only

# Install tools, skip plugin
python3 install.py --skip-plugin
```

### Usage

**Fully automatic (Claude Code / Trae / Codex):**

1. Start the tool in a project directory
2. SessionStart hook fires automatically: locates project, reads `STATUS.md`, creates log file
3. Work normally
4. Say "end log" / "save log" / "结束日志" to trigger log saving

**Semi-automatic (Cursor / Qoder / Antigravity):**

```
/start-log    → Read STATUS.md and inject context
/end-log      → Generate summary and save log
```

### Dual-Layer Log Architecture

Each session log is split into two layers by `%%`:

```
┌──────────────────────────────┐
│ Summary Layer (above %%)     │ ← Auto-loaded at session start
│ - frontmatter + summary      │   (compact, saves tokens)
│ - tasks / decisions          │
│ - artifacts / context        │
├──────────────────────────────┤
│ %%                           │ ← Obsidian hides content below
├──────────────────────────────┤
│ Conversation Layer (below %%)│ ← On-demand access only
│ - Full dialogue timeline     │   (not injected into context)
│ - Technical details preserved│
└──────────────────────────────┘
```

**Incremental saving**: Say "save log" multiple times — summary layer updates to latest state each time, conversation layer only appends new dialogue, never overwrites.

**Stale log cleanup**: SessionStart auto-cleans leftover `active` logs from previous sessions — empty shells get marked `abandoned`, partial logs get marked `paused`.

### Log Format

```markdown
---
tool: "claude-code"
session_id: "2026-04-06_143025"
project: "MyProject"
status: completed
tags: [API, database]
---

## Summary
Designed REST API interfaces for the data governance module.

## Task List
- [x] Requirements analysis
- [x] API interface design
- [ ] Database schema design

## Key Decisions
- RESTful over GraphQL (team familiarity)

## Artifacts
- `project/schema.sql`

## Context Relay
- Depends on: logs/trae/2026-04-05_requirements.md

%%

## Full Conversation Transcript
### [14:30] User: Design the API...
### [14:31] Assistant: Reading requirements doc...
(detailed conversation timeline)
```

### Cross-Tool Relay Flow

```
Day 1: Trae works on projectA/
  → /end-log → STATUS.md records "DB schema design: incomplete"

Day 2: Claude Code starts in projectA/
  → SessionStart hook reads STATUS.md
  → Auto-outputs: "Previous session (trae, 04-05) has 1 unfinished task:
     - Database schema design"
  → Continues work seamlessly

Day 3: Obsidian relay view shows trae → claude-code chain
```

### Project Structure

```
LogRelay/
├── install.py                    # One-click installer
├── src/
│   ├── core/                     # Shared core (config, formatter, status)
│   ├── hooks/                    # Hook scripts (auto tools)
│   ├── commands/                 # CLI commands (semi-auto tools)
│   ├── adapters/                 # Tool-specific config generators
│   └── obsidian-plugin/          # Obsidian plugin (TypeScript)
├── obsidian-plugin/              # Built plugin artifacts
├── templates/                    # Log & status templates
├── tests/                        # 23 tests, all passing
└── docs/                         # Design specs & plans
```

### Testing

```bash
python3 -m pytest tests/ -v    # 23 tests
```

### Uninstall

```bash
python3 install.py --tools claude-code --uninstall
python3 install.py --uninstall  # Remove everything
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Python backend | Python 3.8+, stdlib only |
| Obsidian plugin | TypeScript + Obsidian API + esbuild |
| Charts | Pure CSS (no third-party chart libs) |
| Paths | `pathlib.Path`, forward slashes in logs |
| Cross-platform | `install.py` auto-detects platform |

### FAQ

**Q: Hooks not firing after install?**
- Claude Code: check `.claude/settings.json` for LogRelay hooks
- Codex: ensure `~/.codex/config.toml` has `[features] codex_hooks = true`
- Trae: check `.trae/skills/logrelay/hooks.json` exists

**Q: Not working after switching Windows/macOS?**
Re-run `install.py` — it regenerates platform-specific configs.

**Q: Where are logs stored?**
`{project}/logs/{tool}/`. At vault root: `vault/logs/{tool}/`.

### License

[MIT](LICENSE)

---

<a id="中文"></a>

## LogRelay — 跨工具工作日志接力系统

在一个项目里用 Trae 做了 API 设计、切到 Claude Code 继续写数据库——LogRelay 让后面的工具自动感知前面留下的未完成任务和关键决策，无需手动交代上下文。

### 支持的工具

| 工具 | 模式 | 自动触发 | 配置位置 |
|------|------|----------|----------|
| **Claude Code** | 全自动 | SessionStart hook + CLAUDE.md 规则 | `.claude/settings.json` |
| **Trae / Trae CN** | 全自动 | SessionStart hook | `.trae/skills/logrelay/` |
| **Codex** | 全自动 | SessionStart hook | `.codex/hooks.json` |
| **Cursor** | 半自动 | `/start-log` `/end-log` 命令 | `.cursor/commands/` |
| **Qoder** | 半自动 | `/start-log` `/end-log` 命令 | `.qoder/commands/` |
| **Antigravity** | 半自动 | `/start-log` `/end-log` 工作流 | `.agent/workflows/` |

### 核心特性

- **双层日志架构** — 紧凑摘要层用于自动上下文注入，完整对话层按需查看，用 `%%` 分隔
- **跨工具接力** — `STATUS.md` 共享未完成任务，新工具启动时自动感知并接手
- **跨项目支持** — 日志跟随项目走，各项目独立
- **跨平台兼容** — Windows + macOS，切换系统后重跑 `install.py` 即可
- **Obsidian 插件** — 接力链路可视化、跨项目搜索、统计面板

### 快速开始

**前提条件：** Python 3.8+，Node.js 16+（可选，用于构建 Obsidian 插件）

```bash
# 一键安装全部（所有工具 + Obsidian 插件）
python3 install.py

# 仅安装指定工具
python3 install.py --tools claude-code,trae

# 仅构建部署 Obsidian 插件
python3 install.py --plugin-only

# 安装工具，跳过插件
python3 install.py --skip-plugin
```

### 使用方法

**全自动模式（Claude Code / Trae / Codex）：**

1. 在项目目录下启动工具
2. SessionStart hook 自动触发：定位项目、读取 `STATUS.md`、创建日志文件
3. 正常工作
4. 说 "结束日志" / "保存日志" 触发日志保存

**半自动模式（Cursor / Qoder / Antigravity）：**

```
/start-log    → 读取 STATUS.md 并注入上下文
/end-log      → 生成摘要并保存日志
```

### 双层日志架构

每条日志用 `%%` 分隔为两层：

```
┌──────────────────────────────┐
│ 摘要层（%% 之前）              │ ← 会话启动时自动加载（紧凑，节省 token）
│ - frontmatter + 摘要          │
│ - 任务清单 / 关键决策          │
│ - 产出物 / 上下文传递          │
├──────────────────────────────┤
│ %%                           │ ← Obsidian 阅读模式自动隐藏后续内容
├──────────────────────────────┤
│ 对话层（%% 之后）              │ ← 仅按需读取（不注入上下文）
│ - 完整对话时间线               │
│ - 技术细节完整保留             │
└──────────────────────────────┘
```

**增量保存**：可多次说 "保存日志"——摘要层每次更新为最新状态，对话层只追加新对话记录，不覆盖已有内容。

**空日志自动清理**：SessionStart 每次启动时自动清理上次遗留的空壳日志——空文件标记为 `abandoned`，有操作记录但未保存的标记为 `paused`。

### 日志格式

```markdown
---
tool: "claude-code"
session_id: "2026-04-06_143025"
project: "项目A"
status: completed
tags: [API, 数据库]
---

## 摘要
为数据治理模块设计了 API 接口方案。

## 任务清单
- [x] 需求分析
- [x] API 接口设计
- [ ] 数据库表结构设计

## 关键决策
- 选择 RESTful 而非 GraphQL（团队熟悉度）

## 产出物
- `project/项目A/schema.sql`

## 上下文传递
- 依赖前置会话: logs/trae/2026-04-05_需求调研.md

%%

## 完整对话记录
### [14:30] User: 设计 API 接口...
### [14:31] Assistant: 读取需求文档...
（完整对话时间线）
```

### 跨工具接力流程

```
Day 1: Trae 在 project/项目A/ 工作
  → /end-log → STATUS.md 记录 "数据库表结构设计 未完成"

Day 2: Claude Code 在 project/项目A/ 启动
  → SessionStart hook 读取 STATUS.md
  → 自动输出: "检测到上次会话（trae, 04-05）有 1 个未完成任务：
     - 数据库表结构设计"
  → 无缝继续工作

Day 3: Obsidian 接力链路视图展示 trae → claude-code 接力关系
```

### 项目结构

```
LogRelay/
├── install.py                    # 一键安装脚本
├── src/
│   ├── core/                     # 核心模块（config, formatter, status）
│   ├── hooks/                    # Hook 脚本（全自动工具）
│   ├── commands/                 # CLI 命令（半自动工具）
│   ├── adapters/                 # 工具适配器（生成各工具配置）
│   └── obsidian-plugin/          # Obsidian 插件（TypeScript）
├── obsidian-plugin/              # 插件构建产物
├── templates/                    # 日志和状态模板
├── tests/                        # 23 个测试，全部通过
└── docs/                         # 设计文档和实现计划
```

### 测试

```bash
python3 -m pytest tests/ -v    # 23 个测试
```

### 卸载

```bash
python3 install.py --tools claude-code --uninstall
python3 install.py --uninstall  # 卸载全部
```

### 技术栈

| 组件 | 技术 |
|------|------|
| Python 后端 | Python 3.8+，纯标准库 |
| Obsidian 插件 | TypeScript + Obsidian API + esbuild |
| 图表 | 纯 CSS（不引入第三方库） |
| 路径处理 | `pathlib.Path`，日志中统一正斜杠 |
| 跨平台 | `install.py` 自动检测平台 |

### 常见问题

**Q: 安装后 hooks 没有触发？**
- Claude Code：检查 `.claude/settings.json` 中是否有 LogRelay 的 hooks
- Codex：确保 `~/.codex/config.toml` 中有 `[features] codex_hooks = true`
- Trae：检查 `.trae/skills/logrelay/hooks.json` 是否存在

**Q: 切换 Windows/macOS 后不工作了？**
重新运行 `install.py` 即可，它会根据当前平台重新生成配置。

**Q: 日志存在哪里？**
`{项目目录}/logs/{工具名}/`。在 vault 根目录工作则存 `vault/logs/{工具名}/`。

### 许可证

[MIT](LICENSE)
