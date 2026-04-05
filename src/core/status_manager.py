"""LogRelay STATUS.md 管理模块。"""

from pathlib import Path
from typing import Optional

from .formatter import format_frontmatter, parse_frontmatter
from .utils import get_timestamp


def read_status(project_path: Path) -> Optional[dict]:
    """读取并解析项目下的 STATUS.md。

    返回包含 frontmatter 和 sections 的 dict，不存在则返回 None。
    """
    status_file = project_path / "logs" / "STATUS.md"
    if not status_file.exists():
        return None

    content = status_file.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(content)

    # 解析各 section
    sections = _parse_sections(content)

    return {
        "frontmatter": frontmatter,
        "sections": sections,
        "raw_content": content,
    }


def write_status(project_path: Path, data: dict) -> None:
    """将 data 写入 STATUS.md。"""
    logs_dir = project_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    status_file = logs_dir / "STATUS.md"
    status_file.write_text(_render_status(data), encoding="utf-8")


def create_initial_status(project_path: Path, project_name: str) -> None:
    """创建初始 STATUS.md。"""
    data = {
        "frontmatter": {
            "project": project_name,
            "project_path": str(project_path.name),
            "updated": get_timestamp(),
            "active_session": None,
        },
        "sections": {
            "当前阶段": "",
            "未完成任务": [],
            "已完成任务（最近5条）": [],
            "会话历史": [],
            "产出物索引": [],
        },
    }
    write_status(project_path, data)


def update_status_on_session_end(
    project_path: Path,
    project_name: str,
    session_info: dict,
) -> None:
    """会话结束时更新 STATUS.md。

    session_info 包含：
    - tool: 工具名
    - session_id: 会话 ID
    - summary: 摘要
    - tasks: [{text, completed}, ...]
    - decisions: [str, ...]
    - artifacts: [str, ...]
    - log_path: 日志文件路径
    - handoff_to: 建议接手工具
    """
    status = read_status(project_path)

    if status is None:
        create_initial_status(project_path, project_name)
        status = read_status(project_path)

    fm = status["frontmatter"]
    sections = status["sections"]

    # 更新 frontmatter
    fm["updated"] = get_timestamp()
    fm["active_session"] = None

    # 本次会话任务分类
    completed_task_texts = {t["text"] for t in session_info.get("tasks", []) if t.get("completed")}
    pending_tasks = []
    for t in session_info.get("tasks", []):
        if not t.get("completed"):
            pending_tasks.append({
                "text": t["text"],
                "from": session_info.get("log_path", ""),
                "detail": "",
            })

    # 合并：保留旧的未完成任务（去重 + 移除已完成），加入新的
    existing_pending = sections.get("未完成任务", [])
    # existing_pending 可能包含 dict 或 string（从文件解析回来）
    def _get_task_text(t):
        if isinstance(t, dict):
            return t.get("text", "")
        return str(t).lstrip("- ").strip()

    # 过滤：移除已完成的旧任务
    filtered = [t for t in existing_pending if _get_task_text(t) not in completed_task_texts]
    existing_texts = {_get_task_text(t) for t in filtered}
    for pt in pending_tasks:
        if pt["text"] not in existing_texts:
            filtered.append(pt)
    sections["未完成任务"] = filtered

    # 已完成任务
    completed_tasks = [t for t in session_info.get("tasks", []) if t.get("completed")]
    recent_completed = sections.get("已完成任务（最近5条）", [])
    for ct in completed_tasks:
        recent_completed.insert(0, f"{ct['text']} ({session_info['tool']}, {session_info['session_id'][:10]})")
    sections["已完成任务（最近5条）"] = recent_completed[:5]

    # 会话历史
    history = sections.get("会话历史", [])
    history.insert(0, {
        "日期": session_info["session_id"][:10],
        "工具": session_info["tool"],
        "会话": session_info["session_id"].split("_")[1] if "_" in session_info["session_id"] else "",
        "主题": session_info.get("summary", "")[:20],
    })
    sections["会话历史"] = history

    # 产出物索引
    artifacts_idx = sections.get("产出物索引", [])
    for a in session_info.get("artifacts", []):
        artifacts_idx.append(f"`{a}` (新增)")
    sections["产出物索引"] = artifacts_idx

    # 当前阶段
    if session_info.get("summary"):
        sections["当前阶段"] = session_info["summary"][:50]

    write_status(project_path, {
        "frontmatter": fm,
        "sections": sections,
    })


def get_pending_tasks(status: dict) -> list:
    """从 STATUS 中提取未完成任务。"""
    if status is None:
        return []
    return status.get("sections", {}).get("未完成任务", [])


def get_recent_sessions(status: dict, n: int = 5) -> list:
    """获取最近 N 条会话记录。

    兼容两种格式：
    - dict 格式：{"日期": "...", "工具": "...", ...}（由 update_status_on_session_end 生成）
    - 字符串格式：markdown 表格行（手动编写的 STATUS.md）
    """
    if status is None:
        return []
    raw = status.get("sections", {}).get("会话历史", [])
    # 过滤掉 markdown 表格头和分隔行，保留 dict 和数据行
    sessions = []
    for item in raw:
        if isinstance(item, dict):
            sessions.append(item)
        elif isinstance(item, str):
            line = item.strip()
            if not line.startswith("|"):
                continue
            if "---" in line or "日期" in line:
                continue
            sessions.append(item)
    return sessions[:n]


def _parse_sections(content: str) -> dict:
    """解析 STATUS.md 正文中的各 section。"""
    sections = {}
    current_section = None
    current_lines = []

    in_frontmatter = False
    fm_count = 0

    for line in content.split("\n"):
        if line.strip() == "---":
            fm_count += 1
            if fm_count >= 2:
                in_frontmatter = False
            else:
                in_frontmatter = True
            continue

        if in_frontmatter:
            continue

        if line.startswith("# ") and not line.startswith("## "):
            continue  # 跳过一级标题

        if line.startswith("## "):
            if current_section is not None:
                sections[current_section] = _parse_section_content(current_lines)
            current_section = line[3:].strip()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    if current_section is not None:
        sections[current_section] = _parse_section_content(current_lines)

    return sections


def _parse_section_content(lines: list) -> list | str:
    """解析 section 内容为列表或字符串。只匹配顶级列表项，忽略缩进子项。"""
    items = []
    text_lines = []

    for line in lines:
        stripped = line.strip()
        # 只匹配顶级行（无缩进或仅有列表前缀）
        is_top_level = not line.startswith(" ") and not line.startswith("\t")

        if is_top_level and stripped.startswith("- ["):
            items.append(stripped)
        elif is_top_level and stripped.startswith("- "):
            items.append(stripped[2:])
        elif is_top_level and stripped.startswith("|") and "|" in stripped[1:]:
            items.append(stripped)
        elif stripped and not stripped.startswith("- "):
            text_lines.append(stripped)

    if items:
        return items
    return "\n".join(text_lines) if text_lines else []


def _render_status(data: dict) -> str:
    """将 status data 渲染为 Markdown 字符串。"""
    fm = data.get("frontmatter", {})
    sections = data.get("sections", {})

    parts = [format_frontmatter(fm)]
    parts.append(f"\n# 项目状态：{fm.get('project', '')}\n")

    for section_name, content in sections.items():
        parts.append(f"\n## {section_name}\n")

        # 会话历史用 markdown 表格渲染
        if section_name == "会话历史" and isinstance(content, list):
            table_items = [item for item in content if isinstance(item, dict)]
            if table_items:
                parts.append("| 日期 | 工具 | 会话 | 主题 |")
                parts.append("|------|------|------|------|")
                for item in table_items:
                    parts.append(f"| {item.get('日期', '')} | {item.get('工具', '')} | {item.get('会话', '')} | {item.get('主题', '')} |")
            # 也有字符串行的旧格式，原样输出
            for item in content:
                if isinstance(item, str) and item.strip().startswith("|"):
                    parts.append(item.strip())
            parts.append("")
            continue

        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    parts.append(f"- {item.get('text', item)}")
                    if item.get("from"):
                        parts.append(f"  - from: {item['from']}")
                    if item.get("detail"):
                        parts.append(f"  - detail: {item['detail']}")
                else:
                    parts.append(f"- {item}")
        elif content:
            parts.append(str(content))
        parts.append("")

    return "\n".join(parts)
