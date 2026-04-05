"""LogRelay 通用工具函数。"""

from datetime import datetime
from pathlib import Path


def find_vault_root(start_path: Path) -> Path:
    """从 start_path 向上遍历，定位 vault 根目录。

    判定标志：目录下存在 my_project/ 或 .obsidian/。
    """
    current = Path(start_path).resolve()
    for _ in range(20):  # 最多向上 20 层
        if (current / "my_project").is_dir() or (current / ".obsidian").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise FileNotFoundError(f"无法定位 vault 根目录（从 {start_path} 开始）")


def find_project_root(start_path: Path, vault_root: Path) -> tuple[Path, str]:
    """定位项目目录和项目名。

    vault 的直接子目录即为"项目"。如果在 vault 根，项目名="global"。
    返回 (项目目录 Path, 项目名 str)。
    """
    current = Path(start_path).resolve()
    vault_root = vault_root.resolve()

    if current == vault_root:
        return vault_root, "global"

    # vault 的直接子目录
    for child in vault_root.iterdir():
        if not child.is_dir():
            continue
        try:
            current.relative_to(child)
            return child, child.name
        except ValueError:
            continue

    # fallback：不在任何已知项目下，视为 global
    return vault_root, "global"


def ensure_logs_dir(project_path: Path, tool_name: str) -> Path:
    """确保 项目/logs/工具名/ 目录存在，返回该路径。"""
    logs_dir = project_path / "logs" / tool_name
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def generate_filename(summary_keywords: str = "") -> str:
    """生成日志文件名：{YYYY-MM-DD}_{HHMMSS}-{摘要关键词}.md"""
    now = datetime.now()
    base = now.strftime("%Y-%m-%d_%H%M%S")
    if summary_keywords:
        # 清理关键词：移除不安全字符，截断长度
        clean = "".join(c for c in summary_keywords if c.isalnum() or c in "-_. \u4e00-\u9fff")
        clean = clean.strip()[:30]
        if clean:
            return f"{base}-{clean}.md"
    return f"{base}.md"


def get_timestamp() -> str:
    """返回 ISO 8601 格式时间戳。"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def normalize_path(path: Path) -> str:
    """将路径统一为正斜杠字符串。"""
    return str(path).replace("\\", "/")
