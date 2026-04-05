"""Antigravity (Google) 适配器。

半自动模式：通过 .agent/rules/ 注入持久规则 + .agent/workflows/ 提供手动命令。
配置位置：.agent/rules/ + .agent/workflows/
"""

from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root

RULE_CONTENT = """# LogRelay 工作日志接力

## 规则

每次会话开始时：
1. 检查当前项目目录下是否存在 `logs/STATUS.md`
2. 如果存在，读取其中的「未完成任务」列表
3. 向用户报告有未完成的工作可以继续
4. 建议使用 `/start-log` workflow 开始记录本次会话

如果 STATUS.md 不存在：
- 这是新项目，建议使用 `/start-log` 创建日志系统

所有日志文件为 Markdown 格式，存储在 `项目/logs/工具名/` 目录下。
STATUS.md 是跨工具的共享状态文件，记录未完成任务和会话历史。

## 双层日志架构

日志文件用 `%%` 分隔为两层：
- **摘要层**（%% 之前）：frontmatter + 摘要 + 任务 + 决策 + 产出物 + 上下文传递
  - 下次会话启动时只加载这一层，节省上下文空间
- **对话层**（%% 之后）：完整对话记录，仅在需要回溯时查看
- `%%` 必须独占一行，前后各有一个空行
"""

START_LOG_WORKFLOW = """# start-log

启动 LogRelay 工作日志记录。

## 步骤

请执行以下操作：

1. 运行命令：
   `{python_cmd} "{scripts_root}/src/commands/start_log.py" --tool antigravity --cwd "$PWD"`

2. 阅读命令输出中的 STATUS.md 上下文信息

3. 如果有未完成任务，优先继续处理

4. 告诉用户日志已启动，会话结束时请使用 `/end-log`
"""

END_LOG_WORKFLOW = """# end-log

结束 LogRelay 工作日志记录。

## 步骤

请执行以下操作：

1. 回顾本次会话的全部工作内容

2. 生成结构化摘要（JSON 格式）：
   ```json
   {{
     "summary": "一段话总结本次会话（不超过200字）",
     "tasks": [{{"text": "任务描述", "completed": true/false}}],
     "decisions": ["关键决策1"],
     "artifacts": ["创建或修改的文件路径"],
     "related_files": ["相关文件路径"],
     "handoff_to": null,
     "conversation": "完整对话记录（按时间线整理每个 user/assistant 交互的关键操作和技术细节）"
   }}
   ```

   重要：
   - conversation 字段应包含本次会话的完整对话记录，按时间线整理
   - 每个 user 消息写摘要，每个 assistant 响应写关键操作（读了什么、改了什么、运行了什么）
   - 保留关键的技术细节和决策理由
   - 日志采用 %% 双层架构：摘要层自动加载到下次会话；对话层仅在需要回溯时查看

3. 运行命令（将 JSON 作为 --data 参数传入）：
   `{python_cmd} "{scripts_root}/src/commands/end_log.py" --tool antigravity --session-id <会话ID> --data '<JSON数据>'`

   会话 ID 在 /start-log 时输出，查找 `[LogRelay] SESSION_ID=` 行。

4. 告知用户日志已保存。
"""


def install(vault_root: Path) -> None:
    """安装 Antigravity rules 和 workflows。"""
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()

    # Rules（始终生效）
    rules_dir = vault_root / ".agent" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    (rules_dir / "logrelay-rule.md").write_text(RULE_CONTENT, encoding="utf-8")
    print(f"  ✓ Antigravity rules 已写入 {rules_dir}")

    # Workflows（手动触发）
    workflows_dir = vault_root / ".agent" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    (workflows_dir / "start-log.md").write_text(
        START_LOG_WORKFLOW.format(python_cmd=python_cmd, scripts_root=scripts_root),
        encoding="utf-8",
    )
    (workflows_dir / "end-log.md").write_text(
        END_LOG_WORKFLOW.format(python_cmd=python_cmd, scripts_root=scripts_root),
        encoding="utf-8",
    )
    print(f"  ✓ Antigravity workflows 已写入 {workflows_dir}")


def uninstall(vault_root: Path) -> None:
    """卸载 Antigravity 配置。"""
    # Rules
    rule_file = vault_root / ".agent" / "rules" / "logrelay-rule.md"
    if rule_file.exists():
        rule_file.unlink()

    # Workflows
    workflows_dir = vault_root / ".agent" / "workflows"
    for name in ["start-log.md", "end-log.md"]:
        f = workflows_dir / name
        if f.exists():
            f.unlink()

    print("  ✓ Antigravity LogRelay 配置已移除")
