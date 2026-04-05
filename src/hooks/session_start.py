#!/usr/bin/env python3
"""LogRelay 会话开始 Hook。

被 Claude Code/Trae 的 SessionStart hook 或 Cursor/Qoder 的 /start-log 命令调用。
功能：
1. 定位当前项目
2. 读取 STATUS.md（如存在），输出未完成任务
3. 加载前次日志摘要层（%% 之前，不含完整对话）
4. 创建新日志文件
"""

import argparse
import sys
from pathlib import Path

# 确保 core 模块可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.utils import (
    find_project_root,
    find_vault_root,
    ensure_logs_dir,
    generate_filename,
    get_timestamp,
    normalize_path,
)
from core.formatter import create_log_content
from core.status_manager import read_status, get_pending_tasks, get_recent_sessions


def _cleanup_stale_active_logs(logs_dir: Path) -> int:
    """清理同工具目录下残留的 active 状态日志。

    将只有 frontmatter 无实质内容的旧 active 日志标记为 abandoned。
    已有摘要等实质内容的保留为 paused 状态（可能用户忘了保存）。

    返回清理的文件数。
    """
    if not logs_dir.exists():
        return 0

    cleaned = 0
    for log_file in logs_dir.glob("*.md"):
        if log_file.name == "STATUS.md":
            continue
        content = log_file.read_text(encoding="utf-8")
        if "status: active" not in content:
            continue

        # 判断是否有实质内容（frontmatter 结束后的正文）
        fm_end = content.find("---", 4)
        if fm_end < 0:
            continue
        body = content[fm_end + 3:].strip()

        if not body:
            # 空壳文件：只有 frontmatter，标记为 abandoned
            new_content = content.replace("status: active", "status: abandoned")
            log_file.write_text(new_content, encoding="utf-8")
            cleaned += 1
        elif "## 摘要" not in body:
            # 有 PostToolUse 追加的操作记录但无正式摘要，标记为 paused
            new_content = content.replace("status: active", "status: paused")
            log_file.write_text(new_content, encoding="utf-8")
            cleaned += 1

    return cleaned


def _get_last_log_summary(project_path: Path, tool: str) -> str | None:
    """读取最近一条已完成日志的摘要层（%% 之前的内容）。

    摘要层包含：frontmatter + 摘要 + 任务清单 + 关键决策 + 产出物 + 上下文传递。
    完整对话记录在 %% 之后，不加载以节省 token。
    """
    logs_dir = project_path / "logs" / tool
    if not logs_dir.exists():
        return None

    candidates = sorted(
        [f for f in logs_dir.glob("*.md") if f.name != "STATUS.md"],
        key=lambda f: f.name,
        reverse=True,
    )

    for log_file in candidates:
        content = log_file.read_text(encoding="utf-8")
        # 只读已完成或暂停的日志
        if "status: completed" not in content and "status: paused" not in content:
            continue

        # 截取 %% 之前的摘要层
        separator = "\n%%\n"
        if separator in content:
            return content.split(separator)[0]
        else:
            # 兼容无 %% 的旧格式日志，截取前 60 行
            return "\n".join(content.split("\n")[:60])

    return None


def main():
    parser = argparse.ArgumentParser(description="LogRelay 会话开始")
    parser.add_argument("--tool", required=True, help="工具名称")
    parser.add_argument("--cwd", default=None, help="当前工作目录（默认 os.getcwd()）")
    args = parser.parse_args()

    tool = args.tool
    cwd = Path(args.cwd) if args.cwd else Path.cwd()

    try:
        vault_root = find_vault_root(cwd)
    except FileNotFoundError:
        print("[LogRelay] 无法定位 vault 根目录，跳过日志记录。")
        return

    project_path, project_name = find_project_root(cwd, vault_root)
    logs_dir = ensure_logs_dir(project_path, tool)
    _cleanup_stale_active_logs(logs_dir)
    session_id = get_timestamp().replace("T", "_").replace(":", "")
    log_filename = generate_filename()
    log_path = logs_dir / log_filename

    # 创建初始日志文件
    frontmatter = {
        "tool": tool,
        "tool_version": "",
        "session_id": session_id,
        "project": project_name,
        "project_path": normalize_path(project_path.relative_to(vault_root)) if project_path != vault_root else ".",
        "started": get_timestamp(),
        "ended": None,
        "status": "active",
        "tags": [],
        "handoff_to": None,
    }

    content = create_log_content(frontmatter)
    log_path.write_text(content, encoding="utf-8")

    # 输出上下文信息
    relative_log = normalize_path(log_path.relative_to(vault_root))
    print(f"[LogRelay] 项目: {project_name}")
    print(f"[LogRelay] 日志文件: {relative_log}")

    # 读取 STATUS.md
    status = read_status(project_path)
    if status is None:
        print("[LogRelay] 新项目，无历史会话。")
    else:
        pending = get_pending_tasks(status)
        recent = get_recent_sessions(status, 3)

        if pending:
            if recent:
                last = recent[0]
                if isinstance(last, dict):
                    tool_info = f"{last.get('工具', '?')}, {last.get('日期', '?')}"
                else:
                    tool_info = str(last)[:60]
                print(f"[LogRelay] 检测到上次会话（{tool_info}）有 {len(pending)} 个未完成任务：")
            else:
                print(f"[LogRelay] 有 {len(pending)} 个未完成任务：")
            for task in pending[:10]:
                if isinstance(task, dict):
                    print(f"[LogRelay]   - {task.get('text', str(task))}")
                else:
                    print(f"[LogRelay]   - {task}")

        status_file = project_path / "logs" / "STATUS.md"
        if status_file.exists():
            print(f"[LogRelay] 状态文件: {normalize_path(status_file.relative_to(vault_root))}")

        # 读取前次日志摘要层（%% 之前的内容，不含完整对话记录）
        last_log_summary = _get_last_log_summary(project_path, tool)
        if last_log_summary:
            print(f"[LogRelay] 前次会话摘要：")
            for line in last_log_summary.split("\n"):
                stripped = line.strip()
                if stripped:
                    print(f"[LogRelay]   {stripped}")

    # 将 session_id 和 log_path 输出供后续使用
    print(f"[LogRelay] SESSION_ID={session_id}")
    print(f"[LogRelay] LOG_PATH={relative_log}")


if __name__ == "__main__":
    main()
