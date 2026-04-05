#!/usr/bin/env python3
"""LogRelay 手动结束日志命令。

供 Cursor/Qoder 等无 hooks 的工具手动调用。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hooks.session_end import main as end_main


def main():
    parser = argparse.ArgumentParser(description="LogRelay 手动结束日志")
    parser.add_argument("--tool", required=True, help="工具名称")
    parser.add_argument("--session-id", required=True, help="会话 ID")
    parser.add_argument("--summary", default=None, help="摘要文本")
    parser.add_argument("--cwd", default=None, help="当前工作目录")
    parser.add_argument("--data", default=None, help="JSON 格式会话数据")
    args = parser.parse_args()

    print(f"[LogRelay] 正在结束日志记录（{args.tool}）...")
    end_main()
    print("[LogRelay] 日志记录已结束。")


if __name__ == "__main__":
    main()
