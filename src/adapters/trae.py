"""Trae 适配器。

全自动模式：通过 hooks 配置实现会话自动记录。
配置位置：.trae/skills/logrelay/
"""

import json
from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root

RULE_CONTENT = """---
name: logrelay
description: Cross-tool session logging relay. Auto-loads unfinished tasks at session start. Triggers log saving when user says "save log" or "end log", generates dual-layer logs (summary + conversation) and updates STATUS.md.
---

# LogRelay Session Logging Relay

## Rules

At session start:
1. Check if `logs/STATUS.md` exists in the current project directory
2. If it exists, read the unfinished tasks list
3. Report unfinished work to the user

## Session End Log Saving

When the user says any of the following, save the session log:
- "结束日志" / "保存日志" / "end log" / "save log"
- "记录会话" / "记录一下"

### Steps

1. Review all work done in this session
2. Find `SESSION_ID` and `LOG_PATH` from the SessionStart hook output
3. Generate structured summary (JSON format):
   ```json
   {{
     "summary": "One-sentence summary of this session (max 200 chars)",
     "tasks": [{{"text": "Task description", "completed": true/false}}],
     "decisions": ["Key decision 1"],
     "artifacts": ["Created or modified file paths"],
     "related_files": ["Related file paths"],
     "handoff_to": null,
     "conversation": "Full conversation record (timeline of key operations and technical details)"
   }}
   ```
4. Run command:
   `{python_cmd} "{scripts_root}/src/hooks/session_end.py" --tool trae --session-id <SESSION_ID> --data '<JSON data>'

### Dual-Layer Log Architecture
- Log files are split into two layers by `%%`
- Summary layer (before %%): Auto-loaded next session, includes summary/tasks/decisions/artifacts
- Conversation layer (after %%): Full conversation record, on-demand only
- `%%` must be on its own line with blank lines before and after
"""


def generate_hooks_config() -> dict:
    """生成 Trae hooks 配置。"""
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()

    return {
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{python_cmd} \"{scripts_root}/src/hooks/session_start.py\" --tool trae",
                    }
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit|Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{python_cmd} \"{scripts_root}/src/hooks/post_tool_use.py\" --tool trae",
                    }
                ],
            }
        ],
    }


def install(vault_root: Path) -> None:
    """安装 Trae hooks 配置和日志规则。"""
    skills_dir = vault_root / ".trae" / "skills" / "logrelay"
    skills_dir.mkdir(parents=True, exist_ok=True)

    hooks_config = generate_hooks_config()
    hooks_file = skills_dir / "hooks.json"
    hooks_file.write_text(json.dumps(hooks_config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Trae hooks 已写入 {hooks_file}")

    # 写入 SKILL.md（Trae skill 入口文件，AI 自动加载）
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(
        RULE_CONTENT.format(python_cmd=python_cmd, scripts_root=scripts_root),
        encoding="utf-8",
    )
    print(f"  ✓ Trae SKILL.md 已写入 {skill_file}")


def uninstall(vault_root: Path) -> None:
    """卸载 Trae hooks 配置。"""
    skills_dir = vault_root / ".trae" / "skills" / "logrelay"
    if skills_dir.exists():
        import shutil
        shutil.rmtree(skills_dir)
        print(f"  ✓ Trae hooks 已移除 {skills_dir}")
