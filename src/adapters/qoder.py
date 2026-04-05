"""Qoder 适配器。

半自动模式：通过 commands + agents 引导用户手动触发。
配置位置：.qoder/commands/ + .qoder/agents/
"""

from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root


START_LOG_CMD = """请执行以下操作来开始工作日志记录：

1. 运行命令：`{python_cmd} "{scripts_root}/src/commands/start_log.py" --tool qoder --cwd "$PWD"`
2. 阅读命令输出的 STATUS.md 上下文信息
3. 如果有未完成任务，优先继续处理
4. 开始工作后，所有操作将被自动记录到日志文件中
"""

END_LOG_CMD = """请执行以下操作来结束工作日志记录：

1. 回顾本次会话的全部工作内容
2. 生成以下结构化摘要并输出为 JSON 格式：
   ```json
   {{
     "summary": "一段话总结本次会话（不超过200字）",
     "tasks": [{{"text": "任务描述", "completed": true/false}}],
     "decisions": ["关键决策1", "关键决策2"],
     "artifacts": ["创建或修改的文件路径"],
     "handoff_to": null
   }}
   ```
3. 运行命令（将 JSON 作为 --data 参数传入）：
   `{python_cmd} "{scripts_root}/src/commands/end_log.py" --tool qoder --session-id <会话ID> --data '<JSON数据>'`

注意：会话ID 在 start-log 时输出，请查找 [LogRelay] SESSION_ID= 行。
"""

AGENT_CONTENT = """# LogRelay 工作日志接力 Agent

你是一个工作日志接力助手。

## 职责
- 检查当前项目目录下是否存在 `logs/STATUS.md`
- 如果存在，读取未完成任务并报告给用户
- 建议使用 `/start-log` 开始记录
- 建议在会话结束时使用 `/end-log` 结束记录

## 注意事项
- 所有日志文件为 Markdown 格式，存储在 `项目/logs/工具名/` 下
- STATUS.md 是跨工具的共享状态文件
"""


def install(vault_root: Path) -> None:
    """安装 Qoder commands 和 agents。"""
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()

    # Commands
    commands_dir = vault_root / ".qoder" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    (commands_dir / "start-log.md").write_text(
        START_LOG_CMD.format(python_cmd=python_cmd, scripts_root=scripts_root),
        encoding="utf-8",
    )
    (commands_dir / "end-log.md").write_text(
        END_LOG_CMD.format(python_cmd=python_cmd, scripts_root=scripts_root),
        encoding="utf-8",
    )

    # Agents
    agents_dir = vault_root / ".qoder" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "logrelay-agent.md").write_text(AGENT_CONTENT, encoding="utf-8")

    print(f"  ✓ Qoder commands 已写入 {commands_dir}")
    print(f"  ✓ Qoder agents 已写入 {agents_dir}")


def uninstall(vault_root: Path) -> None:
    """卸载 Qoder 配置。"""
    commands_dir = vault_root / ".qoder" / "commands"
    for name in ["start-log.md", "end-log.md"]:
        f = commands_dir / name
        if f.exists():
            f.unlink()

    agents_dir = vault_root / ".qoder" / "agents"
    agent_file = agents_dir / "logrelay-agent.md"
    if agent_file.exists():
        agent_file.unlink()

    print("  ✓ Qoder LogRelay 配置已移除")
