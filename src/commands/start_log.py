#!/usr/bin/env python3
"""LogRelay 手动启动日志命令。

供 Cursor/Qoder 等无 hooks 的工具手动调用。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 复用 hooks/session_start.py 的逻辑
from hooks.session_start import main as start_main


def main():
    parser = argparse.ArgumentParser(description="LogRelay 手动启动日志")
    parser.add_argument("--tool", required=True, help="工具名称")
    parser.add_argument("--cwd", default=None, help="当前工作目录")
    args = parser.parse_args()

    print(f"[LogRelay] 正在启动日志记录（{args.tool}）...")
    start_main()
    print("[LogRelay] 日志记录已启动。")


if __name__ == "__main__":
    main()
