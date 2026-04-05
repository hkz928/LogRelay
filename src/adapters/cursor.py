"""Cursor 适配器。

半自动模式：通过 commands + rules 引导用户手动触发。
配置位置：.cursor/commands/ + .cursor/skills/
"""

from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root


START_LOG_CMD = """请执行以下操作来开始工作日志记录：

1. 运行命令：`{python_cmd} "{scripts_root}/src/commands/start_log.py" --tool cursor --cwd "$PWD"`
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
   `{python_cmd} "{scripts_root}/src/commands/end_log.py" --tool cursor --session-id <会话ID> --data '<JSON数据>'`

注意：会话ID 在 start-log 时输出，请查找 [LogRelay] SESSION_ID= 行。
"""

RULE_CONTENT = """# LogRelay 工作日志接力

每次会话开始时，请检查当前项目目录下是否存在 `logs/STATUS.md` 文件。

如果存在：
1. 读取 `logs/STATUS.md` 中的未完成任务
2. 向用户报告有未完成的工作可以继续
3. 建议使用 `/start-log` 开始记录本次会话

如果不存在：
- 这是新项目，建议使用 `/start-log` 创建日志系统
"""


def install(vault_root: Path) -> None:
    """安装 Cursor commands 和 rules。"""
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()

    # Commands
    commands_dir = vault_root / ".cursor" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    (commands_dir / "start-log.md").write_text(
        START_LOG_CMD.format(python_cmd=python_cmd, scripts_root=scripts_root),
        encoding="utf-8",
    )
    (commands_dir / "end-log.md").write_text(
        END_LOG_CMD.format(python_cmd=python_cmd, scripts_root=scripts_root),
        encoding="utf-8",
    )

    # Rules
    skills_dir = vault_root / ".cursor" / "skills" / "logrelay"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "logrelay-rule.md").write_text(RULE_CONTENT, encoding="utf-8")

    print(f"  ✓ Cursor commands 已写入 {commands_dir}")
    print(f"  ✓ Cursor rules 已写入 {skills_dir}")


def uninstall(vault_root: Path) -> None:
    """卸载 Cursor 配置。"""
    commands_dir = vault_root / ".cursor" / "commands"
    for name in ["start-log.md", "end-log.md"]:
        f = commands_dir / name
        if f.exists():
            f.unlink()

    skills_dir = vault_root / ".cursor" / "skills" / "logrelay"
    if skills_dir.exists():
        import shutil
        shutil.rmtree(skills_dir)

    print("  ✓ Cursor LogRelay 配置已移除")
