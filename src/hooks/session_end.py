#!/usr/bin/env python3
"""LogRelay 会话结束 Hook。

被 /end-log 命令或 SessionEnd hook 调用。
功能：
1. 接收 AI 生成的摘要（stdin 或参数）
2. 更新日志文件
3. 更新 STATUS.md
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import get_vault_root
from core.utils import (
    find_project_root,
    find_vault_root,
    get_timestamp,
    normalize_path,
)
from core.formatter import update_ended_status
from core.status_manager import read_status, update_status_on_session_end


def main():
    parser = argparse.ArgumentParser(description="LogRelay 会话结束")
    parser.add_argument("--tool", required=True, help="工具名称")
    parser.add_argument("--session-id", required=True, help="会话 ID")
    parser.add_argument("--summary", default=None, help="摘要文本")
    parser.add_argument("--cwd", default=None, help="当前工作目录")
    parser.add_argument("--data", default=None, help="JSON 格式完整会话数据")
    args = parser.parse_args()

    tool = args.tool
    session_id = args.session_id
    cwd = Path(args.cwd) if args.cwd else Path.cwd()

    # 解析会话数据
    session_data = {}
    if args.data:
        try:
            session_data = json.loads(args.data)
        except json.JSONDecodeError:
            pass

    # 摘要来源优先级：--data JSON > --summary 参数 > stdin
    summary = session_data.get("summary", args.summary)
    if summary is None:
        if not sys.stdin.isatty():
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                # 尝试解析 JSON
                try:
                    parsed = json.loads(stdin_content)
                    summary = parsed.get("summary", stdin_content[:200])
                    session_data.update({k: v for k, v in parsed.items() if k != "summary"})
                except json.JSONDecodeError:
                    summary = stdin_content[:200]

    if not summary:
        summary = f"会话 {session_id}（{tool}）已结束。"

    # 定位项目和日志文件
    try:
        vault_root = find_vault_root(cwd)
    except FileNotFoundError:
        print("[LogRelay] 无法定位 vault 根目录。", file=sys.stderr)
        sys.exit(1)

    project_path, project_name = find_project_root(cwd, vault_root)

    # 查找当前活跃日志文件
    logs_dir = project_path / "logs" / tool
    log_file = _find_active_log(logs_dir, session_id)

    if log_file is None:
        print(f"[LogRelay] 未找到会话 {session_id} 的活跃日志文件。", file=sys.stderr)
        sys.exit(1)

    # 更新日志文件
    content = log_file.read_text(encoding="utf-8")
    ended_time = get_timestamp()
    content = update_ended_status(content, ended_time, session_data.get("status", "completed"))

    # 在日志中写入摘要等
    sections = _build_sections(summary, session_data)
    content = _insert_sections(content, sections)
    log_file.write_text(content, encoding="utf-8")

    # 更新 STATUS.md
    session_info = {
        "tool": tool,
        "session_id": session_id,
        "summary": summary,
        "tasks": session_data.get("tasks", []),
        "decisions": session_data.get("decisions", []),
        "artifacts": session_data.get("artifacts", []),
        "log_path": normalize_path(log_file.relative_to(vault_root)),
        "handoff_to": session_data.get("handoff_to"),
    }
    update_status_on_session_end(project_path, project_name, session_info)

    print(f"[LogRelay] 会话已结束，日志已保存: {normalize_path(log_file.relative_to(vault_root))}")


def _find_active_log(logs_dir: Path, session_id: str) -> Path | None:
    """查找匹配 session_id 的活跃日志文件。"""
    if not logs_dir.exists():
        return None

    for f in logs_dir.iterdir():
        if not f.is_file() or not f.suffix == ".md":
            continue
        content = f.read_text(encoding="utf-8")
        if session_id in content and "status: active" in content:
            return f

    # fallback：按文件名前缀匹配（session_id = YYYY-MM-DD_HHMMSS）
    prefix = session_id.replace(":", "")
    for f in logs_dir.iterdir():
        if f.name.startswith(prefix):
            return f

    return None


def _build_sections(summary: str, data: dict) -> str:
    """构建摘要相关的 section 内容。"""
    parts = [f"\n## 摘要\n{summary}\n"]

    tasks = data.get("tasks", [])
    if tasks:
        parts.append("## 任务清单")
        for t in tasks:
            mark = "x" if t.get("completed") else " "
            parts.append(f"- [{mark}] {t['text']}")
        parts.append("")

    decisions = data.get("decisions", [])
    if decisions:
        parts.append("## 关键决策")
        for d in decisions:
            parts.append(f"- {d}")
        parts.append("")

    artifacts = data.get("artifacts", [])
    if artifacts:
        parts.append("## 产出物")
        for a in artifacts:
            parts.append(f"- `{a}`")
        parts.append("")

    return "\n".join(parts)


def _insert_sections(content: str, sections: str) -> str:
    """在日志文件的摘要位置插入 sections 内容。

    如果已有 ## 摘要 则替换，否则在 frontmatter 后插入。
    """
    if "## 摘要" in content:
        # 替换现有摘要及后续 section 直到 ---
        idx = content.index("## 摘要")
        end_marker = content.find("\n---\n", idx)
        if end_marker > 0:
            return content[:idx] + sections + content[end_marker:]
        else:
            return content[:idx] + sections

    # 在 frontmatter 后插入
    fm_end = content.find("---", 4)
    if fm_end > 0:
        return content[: fm_end + 3] + "\n" + sections + content[fm_end + 3 :]

    return content


if __name__ == "__main__":
    main()
