"""Codex (OpenAI Codex CLI) 适配器。

全自动模式：通过 .codex/hooks.json 实现 SessionStart + PostToolUse hooks。
配置位置：项目级 .codex/hooks.json
注意：需在 config.toml 中启用 [features] codex_hooks = true
"""

import json
from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root


def generate_hooks_config() -> dict:
    """生成 Codex hooks.json 配置。"""
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()

    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'{python_cmd} "{scripts_root}/src/hooks/session_start.py" --tool codex',
                            "statusMessage": "LogRelay: 加载会话上下文",
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'{python_cmd} "{scripts_root}/src/hooks/post_tool_use.py" --tool codex',
                        }
                    ],
                }
            ],
        }
    }


def install(vault_root: Path) -> None:
    """安装 Codex hooks 配置到项目级。"""
    codex_dir = vault_root / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)

    hooks_config = generate_hooks_config()
    hooks_file = codex_dir / "hooks.json"

    # 合并已有配置
    existing = {}
    if hooks_file.exists():
        try:
            existing = json.loads(hooks_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    # 深度合并 hooks
    if "hooks" not in existing:
        existing["hooks"] = {}

    new_hooks = hooks_config["hooks"]
    for event, configs in new_hooks.items():
        if event not in existing["hooks"]:
            existing["hooks"][event] = configs
        else:
            existing_commands = {
                h.get("command", "")
                for c in existing["hooks"][event]
                for h in c.get("hooks", [])
            }
            for config in configs:
                new_commands = {h.get("command", "") for h in config.get("hooks", [])}
                if not new_commands & existing_commands:
                    existing["hooks"][event].append(config)

    hooks_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Codex hooks 已写入 {hooks_file}")
    print("  ⚠ 请确保 .codex/config.toml 中 [features] codex_hooks = true")


def uninstall(vault_root: Path) -> None:
    """卸载 Codex hooks 配置。"""
    hooks_file = vault_root / ".codex" / "hooks.json"
    if not hooks_file.exists():
        return

    try:
        existing = json.loads(hooks_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    hooks = existing.get("hooks", {})
    scripts_root = str(get_scripts_root())

    for event in list(hooks.keys()):
        hooks[event] = [
            config
            for config in hooks[event]
            if not any(
                scripts_root in h.get("command", "")
                for h in config.get("hooks", [])
            )
        ]
        if not hooks[event]:
            del hooks[event]

    if not hooks:
        existing.pop("hooks", None)

    hooks_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Codex hooks 已从 {hooks_file} 移除")
