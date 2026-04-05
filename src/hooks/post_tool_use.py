#!/usr/bin/env python3
"""LogRelay 工具调用后 Hook（可选）。

在 Write/Edit/Bash 等操作后追加简要记录到当前活跃日志。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.utils import find_vault_root, find_project_root, get_timestamp


def main():
    parser = argparse.ArgumentParser(description="LogRelay PostToolUse")
    parser.add_argument("--tool", required=True, help="工具名称")
    parser.add_argument("--cwd", default=None, help="当前工作目录")
    args = parser.parse_args()

    cwd = Path(args.cwd) if args.cwd else Path.cwd()

    try:
        vault_root = find_vault_root(cwd)
    except FileNotFoundError:
        return

    project_path, _ = find_project_root(cwd, vault_root)
    logs_dir = project_path / "logs" / args.tool

    if not logs_dir.exists():
        return

    # 找到最新的活跃日志
    active_log = None
    for f in sorted(logs_dir.glob("*.md"), reverse=True):
        content = f.read_text(encoding="utf-8")
        if "status: active" in content:
            active_log = f
            break

    if active_log is None:
        return

    # 追加简要记录
    timestamp = get_timestamp()
    append_line = f"\n### [{timestamp}] 操作记录\n工具调用自动记录。\n"

    with open(active_log, "a", encoding="utf-8") as f:
        f.write(append_line)


if __name__ == "__main__":
    main()
