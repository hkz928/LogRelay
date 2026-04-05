"""LogRelay 日志格式化模块。"""

import re
from typing import Optional


def format_frontmatter(data: dict) -> str:
    """将 dict 序列化为 YAML frontmatter 字符串。"""
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f'{key}: "{value}"')
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter(content: str) -> dict:
    """解析 Markdown 文件中的 YAML frontmatter。"""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    result = {}
    for line in match.group(1).strip().split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if value == "null":
            result[key] = None
        elif value == "true":
            result[key] = True
        elif value == "false":
            result[key] = False
        elif value.startswith("[") and value.endswith("]"):
            # 简单列表解析
            inner = value[1:-1]
            result[key] = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
        elif value.startswith('"') and value.endswith('"'):
            result[key] = value[1:-1]
        else:
            result[key] = value

    return result


def create_log_content(
    frontmatter: dict,
    summary: str = "",
    tasks: Optional[list] = None,
    decisions: Optional[list] = None,
    artifacts: Optional[list] = None,
    context: Optional[dict] = None,
    conversation: str = "",
) -> str:
    """组装完整日志 Markdown 文件内容。"""
    parts = [format_frontmatter(frontmatter)]

    if summary:
        parts.append(f"\n## 摘要\n{summary}\n")

    if tasks:
        parts.append("## 任务清单")
        for task in tasks:
            status_mark = "x" if task.get("completed") else " "
            parts.append(f"- [{status_mark}] {task['text']}")
        parts.append("")

    if decisions:
        parts.append("## 关键决策")
        for d in decisions:
            parts.append(f"- {d}")
        parts.append("")

    if artifacts:
        parts.append("## 产出物")
        for a in artifacts:
            parts.append(f"- `{a}`")
        parts.append("")

    if context:
        parts.append("## 上下文传递")
        if context.get("depends_on"):
            parts.append(f"- 依赖前置会话: {context['depends_on']}")
        if context.get("related_files"):
            parts.append(f"- 相关文件: {context['related_files']}")
        parts.append("")

    if conversation:
        parts.append("---\n\n## 完整对话记录\n")
        parts.append(conversation)

    return "\n".join(parts)


def update_ended_status(content: str, ended_time: str, status: str) -> str:
    """更新日志文件中的 ended 和 status 字段。"""
    lines = content.split("\n")
    in_frontmatter = False
    updated = []

    for line in lines:
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                updated.append(line)
                continue
            else:
                in_frontmatter = False
                updated.append(line)
                continue

        if in_frontmatter:
            if line.startswith("ended:"):
                updated.append(f'ended: "{ended_time}"')
                continue
            elif line.startswith("status:"):
                updated.append(f"status: {status}")
                continue

        updated.append(line)

    return "\n".join(updated)
