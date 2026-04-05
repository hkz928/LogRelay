"""Trae 适配器。

全自动模式：通过 hooks 配置实现会话自动记录。
配置位置：.trae/skills/logrelay/
"""

import json
from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root

RULE_CONTENT = """---
name: logrelay
description: Cross-tool session logging relay. Saves session log to logs/trae/ and updates logs/STATUS.md when user says "save log" or "end log".
---

# LogRelay Session Logging

When the user says "save log" / "end log" / "保存日志" / "结束日志" / "记录会话", execute the following save flow.

## Save Flow

### Step 1: Determine project and paths

Current working directory is the "project directory". Log path rules:
- Log file: `<project_dir>/logs/trae/<filename>.md`
- Status file: `<project_dir>/logs/STATUS.md`

Example: if CWD is `/Users/xxx/vault/project/myapp/`:
- Log → `/Users/xxx/vault/project/myapp/logs/trae/2026-04-06_143025-API-design.md`
- STATUS.md → `/Users/xxx/vault/project/myapp/logs/STATUS.md`

### Step 2: Generate SESSION_ID

Format: `YYYY-MM-DD_HHMMSS` (e.g. `2026-04-06_143025`). Generate from current time.

### Step 3: Run save command

```bash
mkdir -p <project_dir>/logs/trae && python3 "{scripts_root}/src/hooks/session_end.py" --tool trae --session-id <SESSION_ID> --data '<JSON>'
```

JSON format:
```json
{{
  "summary": "One-sentence summary (max 200 chars)",
  "tasks": [{{"text": "Task", "completed": true/false}}],
  "decisions": ["Key decision"],
  "artifacts": ["File paths"],
  "related_files": ["Related paths"],
  "handoff_to": null,
  "conversation": "Full conversation timeline"
}}
```

### Step 4: If command fails, write log manually

Create file at `<project_dir>/logs/trae/<SESSION_ID>-<keyword>.md`:

```
---
tool: "trae"
session_id: "<SESSION_ID>"
project: "<project name>"
started: "<start time>"
ended: "<current time>"
status: completed
tags: []
---

## Summary
<one-sentence summary>

## Task List
- [x] Completed task
- [ ] Pending task

## Key Decisions
- Decision and reason

## Artifacts
- File path

## Context Relay
- Related files: paths

%%

## Full Conversation Record

### [HH:MM] User: What user said
### [HH:MM] Assistant: Key operations (files read, code changed, commands run)
```

Also create or update `<project_dir>/logs/STATUS.md`.

**IMPORTANT: Log files MUST go to `logs/trae/` directory, NOT anywhere else in the project. STATUS.md MUST be in `logs/` directory.**
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
