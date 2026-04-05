"""LogRelay 全局配置。"""

import platform
from pathlib import Path

# 支持的工具列表
SUPPORTED_TOOLS = ["claude-code", "trae", "trae-cn", "cursor", "qoder", "codex", "antigravity"]

# 目录和文件名约定
LOGS_DIR_NAME = "logs"
STATUS_FILENAME = "STATUS.md"

# 适配器配置目录映射（相对于 vault 根）
TOOL_CONFIG_DIRS = {
    "claude-code": ".claude",
    "trae": ".trae",
    "trae-cn": ".trae-cn",
    "cursor": ".cursor",
    "qoder": ".qoder",
    "codex": ".codex",
    "antigravity": ".agent",
}

# 工具模式：auto = hooks 自动触发，semi = 手动 commands
TOOL_MODES = {
    "claude-code": "auto",
    "trae": "auto",
    "trae-cn": "auto",
    "cursor": "semi",
    "qoder": "semi",
    "codex": "auto",
    "antigravity": "semi",
}


def get_vault_root() -> Path:
    """基于当前文件位置定位 vault 根目录。

    文件位置：vault/my_project/LogRelay/src/core/config.py
    vault 根 = 向上 4 级。
    """
    return Path(__file__).resolve().parents[4]


def get_python_cmd() -> str:
    """根据平台返回 Python 命令。"""
    return "python3" if platform.system() == "Darwin" else "python"


def get_scripts_root() -> Path:
    """返回 LogRelay 项目根目录（install.py 所在目录）。"""
    return Path(__file__).resolve().parents[2]


def get_tool_config(tool_name: str) -> dict:
    """返回工具特定配置。"""
    if tool_name not in SUPPORTED_TOOLS:
        raise ValueError(f"不支持的工具: {tool_name}，支持: {SUPPORTED_TOOLS}")
    return {
        "name": tool_name,
        "mode": TOOL_MODES[tool_name],
        "config_dir": TOOL_CONFIG_DIRS[tool_name],
    }
