"""Trae CN（国内版 Trae）适配器。

全自动模式：通过 hooks 配置实现会话自动记录。
配置位置：.trae-cn/skills/logrelay/
机制与 Trae 国际版一致，仅配置目录不同。
"""

import json
from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root


def generate_hooks_config() -> dict:
    """生成 Trae CN hooks 配置。"""
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()

    return {
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": python_cmd + ' "' + str(scripts_root) + '/src/hooks/session_start.py" --tool trae-cn',
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
                        "command": python_cmd + ' "' + str(scripts_root) + '/src/hooks/post_tool_use.py" --tool trae-cn',
                    }
                ],
            }
        ],
    }


def install(vault_root: Path) -> None:
    """安装 Trae CN hooks 配置。"""
    skills_dir = vault_root / ".trae-cn" / "skills" / "logrelay"
    skills_dir.mkdir(parents=True, exist_ok=True)

    hooks_config = generate_hooks_config()
    hooks_file = skills_dir / "hooks.json"
    hooks_file.write_text(json.dumps(hooks_config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Trae CN hooks 已写入 {hooks_file}")


def uninstall(vault_root: Path) -> None:
    """卸载 Trae CN hooks 配置。"""
    skills_dir = vault_root / ".trae-cn" / "skills" / "logrelay"
    if skills_dir.exists():
        import shutil
        shutil.rmtree(skills_dir)
        print(f"  ✓ Trae CN hooks 已移除 {skills_dir}")
