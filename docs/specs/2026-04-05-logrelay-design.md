---
title: LogRelay - 跨工具工作日志接力系统
date: 2026-04-05
status: approved
---

# LogRelay 设计文档

## 概述

LogRelay 是一个跨 AI 编码工具的工作日志自动记录与接力系统。它支持 Claude Code、Trae、Cursor、Qoder 等工具，自动记录工作会话并实现跨工具的任务接力。配套 Obsidian 插件提供可视化接力链路、跨项目搜索和统计面板。

**核心设计目标**：
1. 跨工具日志共享，一个工具的产出和未完成任务可以被另一个工具无缝接手
2. 跨平台兼容（Windows + macOS），知识库在两个系统间共享，无缝切换

## 项目位置

所有项目代码位于：`my_project/LogRelay/`

## 项目结构

```
my_project/LogRelay/
├── README.md                          # 项目说明
├── src/
│   ├── core/
│   │   ├── config.py                  # 全局配置（工具名映射、路径规则）
│   │   ├── formatter.py               # 标准化日志格式化（frontmatter、摘要）
│   │   ├── status_manager.py           # STATUS.md 读写与状态追踪
│   │   └── utils.py                   # 通用工具函数
│   ├── hooks/
│   │   ├── session_start.py           # 会话开始：创建日志文件 + 读取 STATUS.md
│   │   ├── session_end.py             # 会话结束：生成摘要 + 更新 STATUS.md
│   │   └── post_tool_use.py           # 工具调用后：追加对话片段（可选）
│   ├── commands/
│   │   ├── start_log.py               # CLI 入口：手动启动记录
│   │   └── end_log.py                 # CLI 入口：手动结束记录
│   ├── adapters/
│   │   ├── claude_code.py             # Claude Code 适配器（hooks 配置生成）
│   │   ├── trae.py                    # Trae 适配器
│   │   ├── cursor.py                  # Cursor 适配器（Command 模式）
│   │   └── qoder.py                   # Qoder 适配器（Command 模式）
│   └── obsidian-plugin/               # Obsidian 原生插件
│       ├── main.ts                    # 插件入口
│       ├── settings.ts                # 插件设置页
│       ├── views/
│       │   ├── relay-view.ts          # 接力链路可视化
│       │   ├── search-view.ts         # 跨项目日志搜索
│       │   └── stats-view.ts          # 统计面板
│       ├── services/
│       │   ├── log-parser.ts          # 解析日志 frontmatter
│       │   ├── status-tracker.ts      # STATUS.md 监控
│       │   └── search-engine.ts       # 全文搜索逻辑
│       └── components/
│           ├── relay-graph.ts         # 接力关系图组件
│           ├── search-result.ts       # 搜索结果列表组件
│           └── charts.ts              # 统计图表组件
├── templates/
│   ├── log_template.md                # 日志文件模板
│   └── status_template.md             # STATUS.md 模板
├── install.py                         # 一键安装脚本：为各工具部署 hooks/commands
├── obsidian-plugin/                   # 构建产物（发布到 .obsidian/plugins/logrelay/）
│   ├── main.js
│   ├── manifest.json
│   └── styles.css
└── tests/
    ├── core/
    └── obsidian-plugin/
        └── ...
```

### 模块职责

- `core/`：共享逻辑层，所有适配器都调用它
- `hooks/`：供有 hooks 机制的工具（Claude Code、Trae）自动触发
- `commands/`：供无 hooks 的工具（Cursor、Qoder）手动触发
- `adapters/`：为每个工具生成其所需的配置文件
- `obsidian-plugin/`：Obsidian 原生插件源码（TypeScript）
- `install.py`：一键部署到 vault 中各工具的配置目录

## 核心数据模型

### 日志文件命名规则

```
{YYYY-MM-DD}_{HHMMSS}-{摘要关键词}.md
```

示例：`2026-04-05_143025-数据治理方案.md`

### 日志文件格式（双层架构）

日志文件使用 `%%` 分隔符将内容分为**摘要层**和**对话层**：

- **摘要层**（`%%` 之前）：`session_start.py` 启动时**只加载这一层**，包含 frontmatter + 摘要 + 任务 + 决策 + 产出物 + 上下文传递。紧凑、节省 token。
- **对话层**（`%%` 之后）：完整对话记录，仅在需要回溯细节时手动查看或 AI 按需读取。不自动注入新会话上下文。
- Obsidian 阅读模式下 `%%` 之后的内容自动隐藏。

```
┌─────────────────────────────────┐
│ 摘要层（%% 之前）                 │ ← session_start.py 只读这一层
│ - frontmatter                   │ ← Obsidian 正常渲染
│ - 摘要 / 任务 / 决策 / 产出物      │
│ - 上下文传递                      │
├─────────────────────────────────┤
│ %%                              │ ← 分隔符（Obsidian 阅读模式隐藏后续）
├─────────────────────────────────┤
│ 对话层（%% 之后）                 │ ← 不自动加载，按需手动查看
│ - 完整对话时间线                  │
│ - 技术细节保留                    │
└─────────────────────────────────┘
```

完整格式如下：

```markdown
---
tool: trae
tool_version: "1.4.0"
session_id: "2026-04-05_143025"
project: 大庆油田
project_path: project/大庆油田
started: 2026-04-05T14:30:25
ended: 2026-04-05T15:45:10
status: paused                      # active | completed | paused | failed
tags: [数据治理, API设计]
handoff_to: null                    # 建议接手工具，null=不限
---

## 摘要
为数据治理模块设计了 API 接口方案，完成了需求分析和接口设计，
数据库表结构设计未完成。

## 任务清单
- [x] 需求分析文档
- [x] API 接口设计
- [ ] 数据库表结构设计
- [ ] 前端页面原型

## 关键决策
- 选择 RESTful 风格而非 GraphQL（团队熟悉度考量）
- 分页采用 cursor-based 方案

## 产出物
- `project/大庆油田/设计文档/API接口方案.md`

## 上下文传递
- 依赖前置会话: logs/claude-code/2026-04-04_100000-需求调研.md
- 相关文件: project/大庆油田/需求/数据治理需求v2.pdf

%%

## 完整对话记录

### [14:30:25] User
帮我设计数据治理模块的 API 接口...

### [14:31:02] Assistant
好的，我先了解一下现有需求文档...

## 上下文传递
- 依赖前置会话: logs/claude-code/2026-04-04_100000-需求调研.md
- 相关文件: project/大庆油田/需求/数据治理需求v2.pdf

%%

## 完整对话记录

### [14:30:25] User
帮我设计数据治理模块的 API 接口...

### [14:31:02] Assistant
好的，我先了解一下现有需求文档...

（完整对话内容，按时间戳逐条记录）
```

### STATUS.md 格式（跨工具接力棒）

```markdown
---
project: 大庆油田
project_path: project/大庆油田
updated: 2026-04-05T15:45:10
active_session: null                # 当前活跃会话ID，null=无
---

# 项目状态：大庆油田

## 当前阶段
数据治理模块 - API 设计阶段

## 未完成任务
- [ ] 数据库表结构设计
  - from: logs/trae/2026-04-05_143025-数据治理方案.md
  - detail: 需要根据 API 接口设计对应的表结构
- [ ] 前端页面原型

## 已完成任务（最近5条）
- [x] 需求分析文档 (trae, 2026-04-05)
- [x] API 接口设计 (trae, 2026-04-05)

## 会话历史
| 日期 | 工具 | 会话 | 主题 |
|------|------|------|------|
| 04-05 | trae | 143025 | 数据治理方案 |
| 04-04 | claude-code | 100000 | 需求调研 |

## 产出物索引
- `project/大庆油田/设计文档/API接口方案.md` (新增)
```

### 日志存储路径

```
{项目目录}/logs/{工具名}/{日志文件名}.md
{项目目录}/logs/STATUS.md
```

示例：
```
project/大庆油田/
├── logs/
│   ├── STATUS.md
│   ├── trae/
│   │   └── 2026-04-05_143025-数据治理方案.md
│   └── claude-code/
│       └── 2026-04-05_160100-审查数据治理.md
└── ...（项目其他文件）
```

## 跨工具接力机制

### 接力流程

```
工具 A（如 Trae）结束会话
  1. 工具 AI 生成结构化摘要（摘要、任务清单、关键决策、产出物）
  2. session_end.py 接收摘要 → 写入日志文件到 项目/logs/trae/
  3. 更新 项目/logs/STATUS.md
          │
          ▼
工具 B（如 Claude Code）启动
  1. session_start.py 检测当前工作目录
  2. 定位所属项目 → 读取 项目/logs/STATUS.md
  3. 将 STATUS.md 内容注入为会话上下文
  4. 创建新日志文件，标记依赖前置会话
          │
          ▼
工具 B 继续工作
  - 感知未完成任务
  - 引用前序产出物
  - 结束时工具 AI 生成摘要，更新 STATUS.md
```

### 项目定位规则

脚本通过当前工作目录自动判断所属项目：

- `vault/` → 无项目，日志存 `vault/logs/工具/`
- `vault/project/大庆油田/` → 项目=大庆油田，日志存 `project/大庆油田/logs/工具/`
- `vault/project/大庆油田/子系统/` → 向上查找，仍归属大庆油田
- `vault/知识加油站/` → 项目=知识加油站，日志存 `知识加油站/logs/工具/`

**定位算法**：从当前目录向上遍历到 vault 根，vault 的直接子目录即为"项目"。如果在 vault 根，则视为"全局"项目。

### 上下文注入方式

| 工具 | 注入方式 | 实现 |
|------|----------|------|
| Claude Code | SessionStart hook 输出到 stdout | hook 脚本输出 STATUS.md 内容，自动进入会话上下文 |
| Trae | SessionStart hook 注入 | 同上 |
| Cursor | rules/ 文件 + 手动 `/start-log` | 在 `.cursor/rules/` 中放提示文件引导读取 STATUS.md |
| Qoder | agents/ 配置 + 手动 `/start-log` | 在 agent 指令中引导读取 STATUS.md |

### 摘要生成策略

会话结束时，由工具 AI 自行生成结构化摘要。每个工具的 end-log 命令中包含明确的提示指令：

```markdown
请执行以下操作来结束工作日志记录：

1. 回顾本次会话的全部工作内容
2. 生成以下结构化摘要并输出为 YAML frontmatter：
   - summary: 一段话总结本次会话做了什么（不超过200字）
   - tasks: 任务清单，每项标注 completed/pending
   - decisions: 列出关键决策及原因
   - artifacts: 列出创建或修改的文件路径
   - handoff_to: 建议接手工具（null 表示不限）
3. 调用 end_log.py 保存日志和更新 STATUS.md
```

**实现要点**：
- 提示指令嵌入在各适配器的 end-log 配置中
- AI 输出的摘要直接写入日志文件的对应字段
- `end_log.py` 接收参数（或从 stdin 读取 AI 输出的摘要内容）

## 适配器设计

### Claude Code（全自动）

配置位置：`.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python my_project/LogRelay/src/hooks/session_start.py --tool claude-code"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python my_project/LogRelay/src/hooks/post_tool_use.py --tool claude-code"
          }
        ]
      }
    ]
  }
}
```

无 SessionEnd 事件 → 用 PostToolUse 最后调用 + 专用 `/end-log` 命令兜底。

### Trae（全自动）

配置位置：`.trae/skills/logrelay/`

```
.trae/skills/logrelay/
├── hooks.json
```

hooks.json 中直接调用 Python 脚本，与 Claude Code 共用同一套 `src/hooks/` 脚本，仅 `--tool` 参数不同。

### Cursor（半自动）

配置位置：`.cursor/`

```
.cursor/
├── commands/
│   ├── start-log.md        # /start-log 命令
│   └── end-log.md          # /end-log 命令
└── skills/
    └── logrelay/
        └── logrelay-rule.md  # 持久规则
```

**start-log.md** 内容：执行 `python my_project/LogRelay/src/commands/start_log.py --tool cursor`，然后读取输出的 STATUS.md。

**logrelay-rule.md**：每次会话开始时检查 `logs/STATUS.md` 是否存在，存在则主动读取未完成任务作为上下文。

### Qoder（半自动）

配置位置：`.qoder/`

```
.qoder/
├── commands/
│   ├── start-log.md
│   └── end-log.md
└── agents/
    └── logrelay-agent.md
```

结构与 Cursor 类似。

### 适配器共性

- 共享同一套 `src/core/` 核心逻辑
- 同一个 `--tool` 参数区分来源
- 同一个日志格式和 STATUS.md 格式
- 统一的错误处理（项目定位失败则降级到全局日志）

## Obsidian 插件

### 概述

原生 Obsidian 插件（TypeScript），提供三个核心视图：接力链路可视化、跨项目日志搜索、统计面板。构建产物部署到 `.obsidian/plugins/logrelay/`。

### 接力链路视图（Relay View）

侧边栏展示当前项目的会话接力链路，自动扫描 `项目/logs/*/` 下所有日志的 frontmatter，通过 `上下文传递` 字段构建依赖关系图。

```
┌─ 接力链路 ─────────────────────┐
│ 项目：大庆油田                   │
│                                 │
│ [04-04] claude-code ──┐        │
│   需求调研             │        │
│                       ▼        │
│ [04-05] trae ────────┬─┘       │
│   API设计 (2/4完成)   │         │
│                       ▼        │
│ [04-06] claude-code ◄─┘        │
│   表结构设计 (进行中)  │        │
│                       ▼        │
│ [04-07] cursor ◄─────┘        │
│   前端原型 (未开始)             │
│                                 │
│ 点击节点可跳转到对应日志文件     │
└─────────────────────────────────┘
```

- 节点颜色编码：完成=绿、进行中=蓝、暂停=黄、失败=红
- 节点可点击跳转到对应 Markdown 文件
- 最大显示深度可配置（默认 10 层）

### 跨项目日志搜索（Search View）

```
┌─ 日志搜索 ──────────────────────┐
│ 🔍 [搜索框___________________]  │
│                                 │
│ 筛选：                          │
│ 工具: [全部▼] 项目: [全部▼]     │
│ 状态: [全部▼] 日期: [近7天▼]    │
│                                 │
│ 结果 (12条)：                    │
│ ─────────────────────────────── │
│ 📄 数据治理方案                  │
│   trae | 大庆油田 | 04-05       │
│   #数据治理 #API设计             │
│ ─────────────────────────────── │
│ ...                             │
└─────────────────────────────────┘
```

- 全文搜索：搜索日志内容和 frontmatter
- 筛选维度：工具、项目、状态、日期范围、标签
- 结果列表点击跳转到对应文件
- 使用 Obsidian 的 MetadataCache 加速 frontmatter 查询
- 搜索索引定时刷新（间隔可配置，默认 5 分钟）

### 统计面板（Stats View）

```
┌─ LogRelay 统计 ─────────────────┐
│                                 │
│ 📊 工具使用频率                  │
│ ┌───────────────────────────┐  │
│ │ claude-code ████████ 45%  │  │
│ │ trae       ██████   30%   │  │
│ │ cursor     ███      15%   │  │
│ │ qoder      █        10%   │  │
│ └───────────────────────────┘  │
│                                 │
│ ✅ 任务完成率                    │
│ ┌───────────────────────────┐  │
│ │ 总任务: 156                │  │
│ │ 已完成: 128 (82%)          │  │
│ │ 进行中: 18                 │  │
│ │ 待开始: 10                 │  │
│ └───────────────────────────┘  │
│                                 │
│ 📅 近30天活跃度                 │
│ ┌───────────────────────────┐  │
│ │ [日历热力图 - GitHub风格]   │  │
│ └───────────────────────────┘  │
│                                 │
│ 🏆 项目活跃度 TOP 5             │
│ 1. 大庆油田 (42 会话)           │
│ 2. 页岩油 (28 会话)             │
│ 3. ...                         │
└─────────────────────────────────┘
```

- 工具使用频率：条形图，按会话数统计
- 任务完成率：汇总所有日志中的任务清单
- 活跃度热力图：近 30 天的会话数量分布（GitHub 风格）
- 项目活跃度排名：按会话数排序
- 统计周期可配置（默认 30 天）
- 图表使用 Obsidian 原生 API + CSS 实现，不引入第三方图表库

### 插件设置页

```
LogRelay 设置
├── 日志目录名: [logs]          # 默认 logs，可自定义
├── 状态文件名: [STATUS.md]     # 默认 STATUS.md
├── 接力链路：显示深度 [10]      # 最多显示几层接力
├── 搜索：索引间隔 [5分钟]      # 搜索索引刷新频率
└── 统计：统计周期 [30天]       # 统计面板默认时间范围
```

### 插件技术实现

- **语言**：TypeScript，使用 Obsidian Plugin API
- **构建**：esbuild 打包为单个 main.js
- **数据源**：直接读取 vault 中的日志 Markdown 文件，解析 frontmatter
- **UI**：Obsidian WorkspaceLeaf + ItemView API，纯 CSS 样式
- **部署**：构建产物复制到 `.obsidian/plugins/logrelay/`，通过 Obsidian 设置启用

## 跨平台兼容设计

### 约束

知识库（vault）在 Windows 和 macOS 之间共享（同一文件系统或同步），用户会在两个平台间频繁切换。所有功能必须在两个平台上表现一致。

### 路径处理

- Python 代码全部使用 `pathlib.Path`，不使用字符串拼接或 `os.path`
- 日志文件中的路径统一使用正斜杠（`project/大庆油田/logs/`）
- `config.py` 中通过 `platform.system()` 检测当前平台

### Hook 脚本

- 统一使用 Python 脚本（`.py`），不使用 `.sh` / `.bat`
- Windows 下 Claude Code hooks 通过 Git Bash 执行 `python xxx.py`，macOS 通过原生 shell 执行
- `install.py` 根据当前平台生成对应的 hooks 配置

### install.py 平台适配

```
install.py 检测平台 → 生成平台适配的配置：

Windows:
  hooks command: "python E:/华为家庭存储/知识库/vault/my_project/LogRelay/src/hooks/session_start.py --tool claude-code"

macOS:
  hooks command: "python3 /Users/xxx/vault/my_project/LogRelay/src/hooks/session_start.py --tool claude-code"
```

- 使用绝对路径避免跨平台相对路径问题
- `install.py` 在每次执行时根据当前平台重新生成配置（切换平台后重新运行即可）
- vault 根目录通过 `__file__` 相对定位，不硬编码

### Obsidian 插件

- Obsidian 插件本身跨平台（TypeScript → JS 在 Obsidian 内运行）
- 插件中的路径处理使用 `app.vault.adapter.getBasePath()` 获取 vault 根路径
- 不依赖平台特定的系统调用

## 安装部署

### 一键安装

```bash
python my_project/LogRelay/install.py --tools claude-code,trae,cursor,qoder
```

**install.py 执行流程**：

1. 检查环境（Python 版本、各工具配置目录是否存在）
2. 为每个指定工具：
   - 生成 hooks 配置 → 写入 `.claude/settings.json` / `.trae/skills/logrelay/`
   - 生成 commands → 写入 `.cursor/commands/` / `.qoder/commands/`
   - 生成 rules → 写入 `.cursor/skills/` / `.qoder/agents/`
3. 构建 Obsidian 插件（如已安装 Node.js）
4. 部署插件到 `.obsidian/plugins/logrelay/`
5. 验证部署结果
6. 输出各工具的状态报告

支持单工具安装（`--tools claude-code`）和卸载（`--uninstall claude-code`）。

### 日常使用流程

**自动模式（Claude Code / Trae）**：

1. 用户在 `vault/project/大庆油田/` 下启动工具
2. 工具自动触发 `session_start.py`
3. 检测到项目=大庆油田
4. 读取 `project/大庆油田/logs/STATUS.md`（如存在）
5. 将未完成任务注入上下文
6. 创建 `project/大庆庆油田/logs/claude-code/2026-04-05_160100-xxx.md`
7. 用户正常工作
8. 会话结束，执行 `/end-log`
9. 工具 AI 生成结构化摘要，end_log.py 保存并更新 STATUS.md

**半自动模式（Cursor / Qoder）**：

1. 用户在项目中启动工具
2. 手动执行 `/start-log`
3. 效果同自动模式步骤 3-6
4. 用户正常工作
5. 手动执行 `/end-log`
6. 工具 AI 生成摘要，end_log.py 保存并更新 STATUS.md

### 跨工具接力示例

```
Day 1: Trae 在 project/大庆油田/ 工作
       → /end-log: AI 生成摘要，STATUS.md 记录 "数据库表结构设计 未完成"

Day 2: Claude Code 在 project/大庆油田/ 启动
       → SessionStart hook 读取 STATUS.md
       → 自动输出:
         "检测到上次会话（trae, 04-05）有未完成任务：
          - 数据库表结构设计
          相关日志: project/大庆油田/logs/trae/2026-04-05_143025-数据治理方案.md"
       → 用户确认后继续工作

Day 3: 在 Obsidian 中打开接力链路视图
       → 可视化展示 trae → claude-code 的接力关系
       → 搜索 "数据治理" 可跨项目找到相关会话
       → 统计面板显示各工具使用占比
```

## 依赖与约束

- **Python 后端**：Python 3.8+，无第三方库（纯标准库实现）
- **Obsidian 插件**：Node.js 16+（仅构建时），TypeScript，Obsidian API
- **平台**：Windows + macOS 双平台支持，知识库跨平台共享
  - Windows：Python 在 PATH 中，Git Bash 可用
  - macOS：Python3 在 PATH 中
  - 切换平台后重新运行 `install.py` 即可适配
- **存储开销**：每个会话约 10-100KB Markdown 文件
- **Obsidian 兼容**：所有文件为标准 Markdown，frontmatter 可被 Obsidian 识别为属性
- **跨平台路径**：所有 Python 代码使用 `pathlib.Path`，日志中路径统一用正斜杠
