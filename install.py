#!/usr/bin/env python3
"""LogRelay 一键安装脚本。

用法：
    # 安装全部（工具 hooks + Obsidian 插件）
    python3 install.py

    # 仅安装指定工具
    python3 install.py --tools claude-code,trae

    # 仅构建部署 Obsidian 插件
    python3 install.py --plugin-only

    # 跳过 Obsidian 插件构建
    python3 install.py --tools claude-code --skip-plugin

    # 卸载
    python3 install.py --uninstall claude-code
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# 确保 src 可导入
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from src.adapters.claude_code import install as install_claude, uninstall as uninstall_claude
from src.adapters.trae import install as install_trae, uninstall as uninstall_trae
from src.adapters.trae_cn import install as install_trae_cn, uninstall as uninstall_trae_cn
from src.adapters.cursor import install as install_cursor, uninstall as uninstall_cursor
from src.adapters.qoder import install as install_qoder, uninstall as uninstall_qoder
from src.adapters.codex import install as install_codex, uninstall as uninstall_codex
from src.adapters.antigravity import install as install_antigravity, uninstall as uninstall_antigravity
from src.core.config import SUPPORTED_TOOLS, TOOL_CONFIG_DIRS, get_vault_root

ADAPTERS = {
    "claude-code": (install_claude, uninstall_claude),
    "trae": (install_trae, uninstall_trae),
    "trae-cn": (install_trae_cn, uninstall_trae_cn),
    "cursor": (install_cursor, uninstall_cursor),
    "qoder": (install_qoder, uninstall_qoder),
    "codex": (install_codex, uninstall_codex),
    "antigravity": (install_antigravity, uninstall_antigravity),
}

# 路径常量
PROJECT_ROOT = Path(__file__).resolve().parent
PLUGIN_SRC = PROJECT_ROOT / "src" / "obsidian-plugin"
PLUGIN_DIST = PROJECT_ROOT / "obsidian-plugin"
PLUGIN_DEPLOY_DIR_NAME = ".obsidian/plugins/logrelay"


def check_environment():
    """检查运行环境。"""
    print("=== LogRelay 安装 ===\n")

    # Python 版本
    py_version = sys.version_info
    print(f"Python: {py_version.major}.{py_version.minor}.{py_version.micro}")
    if py_version < (3, 8):
        print("  ✗ 需要 Python 3.8+")
        sys.exit(1)
    print("  ✓ Python 版本满足要求")

    # 平台
    plat = platform.system()
    print(f"平台: {plat}")
    print(f"  ✓ {'macOS' if plat == 'Darwin' else 'Windows' if plat == 'Windows' else plat}")

    # Vault 根目录
    try:
        vault_root = get_vault_root()
        print(f"Vault 根目录: {vault_root}")
        print("  ✓ 已定位")
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
        sys.exit(1)

    return vault_root


def check_tool_dirs(vault_root: Path, tools: list[str]) -> dict:
    """检查各工具配置目录是否存在。"""
    from src.core.config import TOOL_CONFIG_DIRS

    status = {}
    print("\n--- 工具配置目录检查 ---")
    for tool in tools:
        config_dir = TOOL_CONFIG_DIRS.get(tool, "")
        dir_path = vault_root / config_dir
        exists = dir_path.exists()
        status[tool] = dir_path
        mark = "✓" if exists else "○"
        note = "" if exists else "（将在安装时创建）"
        print(f"  {mark} {tool}: {dir_path}{note}")

    return status


def install_tools(vault_root: Path, tools: list[str]):
    """安装指定工具的配置。"""
    print(f"\n--- 开始安装 {len(tools)} 个工具 ---\n")

    for tool in tools:
        if tool not in ADAPTERS:
            print(f"  ✗ 未知工具: {tool}，跳过")
            continue

        print(f"[{tool}]")
        install_fn = ADAPTERS[tool][0]
        try:
            install_fn(vault_root)
        except Exception as e:
            print(f"  ✗ 安装失败: {e}")

    print("\n--- 工具安装完成 ---")


def uninstall_tools(vault_root: Path, tools: list[str]):
    """卸载指定工具的配置。"""
    print(f"\n--- 开始卸载 {len(tools)} 个工具 ---\n")

    for tool in tools:
        if tool not in ADAPTERS:
            print(f"  ✗ 未知工具: {tool}，跳过")
            continue

        print(f"[{tool}]")
        uninstall_fn = ADAPTERS[tool][1]
        try:
            uninstall_fn(vault_root)
        except Exception as e:
            print(f"  ✗ 卸载失败: {e}")

    print("\n--- 卸载完成 ---")


# ========== Obsidian 插件 ==========

def check_node():
    """检查 Node.js 是否可用。"""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"Node.js: {version}")
            major = int(version.lstrip("v").split(".")[0])
            if major < 16:
                print("  ✗ 需要 Node.js 16+")
                return False
            print("  ✓ Node.js 版本满足要求")
            return True
    except FileNotFoundError:
        pass

    print("  ✗ 未找到 Node.js，跳过 Obsidian 插件构建")
    print("    安装 Node.js: https://nodejs.org/")
    return False


def build_plugin():
    """构建 Obsidian 插件（npm install + npm run build）。"""
    print("\n--- 构建 Obsidian 插件 ---")

    if not check_node():
        return False

    # 检查 package.json 存在
    if not (PLUGIN_SRC / "package.json").exists():
        print("  ✗ 未找到 src/obsidian-plugin/package.json")
        return False

    # npm install（仅在无 node_modules 时）
    if not (PLUGIN_SRC / "node_modules").exists():
        print("  → npm install...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(PLUGIN_SRC),
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            print(f"  ✗ npm install 失败:\n{result.stderr}")
            return False
        print("  ✓ 依赖安装完成")
    else:
        print("  ✓ 依赖已存在，跳过安装")

    # npm run build
    print("  → npm run build...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(PLUGIN_SRC),
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        print(f"  ✗ 构建失败:\n{result.stderr}")
        return False

    # 验证产物
    main_js = PLUGIN_DIST / "main.js"
    if not main_js.exists():
        print("  ✗ 构建产物 main.js 未生成")
        return False

    size_kb = main_js.stat().st_size / 1024
    print(f"  ✓ 构建完成: main.js ({size_kb:.1f} KB)")
    return True


def deploy_plugin(vault_root: Path):
    """部署 Obsidian 插件到 .obsidian/plugins/logrelay/。"""
    print("\n--- 部署 Obsidian 插件 ---")

    deploy_dir = vault_root / PLUGIN_DEPLOY_DIR_NAME
    deploy_dir.mkdir(parents=True, exist_ok=True)

    # 需要部署的文件
    files_to_copy = [
        PLUGIN_DIST / "main.js",
        PLUGIN_DIST / "styles.css",
        PLUGIN_SRC / "manifest.json",
    ]

    # 检查源文件都存在
    for src in files_to_copy:
        if not src.exists():
            print(f"  ✗ 缺少文件: {src}")
            return False

    # 复制
    for src in files_to_copy:
        dst = deploy_dir / src.name
        shutil.copy2(src, dst)
        size_kb = dst.stat().st_size / 1024
        print(f"  ✓ {src.name} ({size_kb:.1f} KB)")

    # 注册到 community-plugins.json
    register_plugin(vault_root)

    print(f"  ✓ 插件已部署到 {deploy_dir}")
    return True


def register_plugin(vault_root: Path):
    """将 LogRelay 注册到 Obsidian 的 community-plugins.json。"""
    cp_file = vault_root / ".obsidian" / "community-plugins.json"

    plugins = []
    if cp_file.exists():
        try:
            plugins = json.loads(cp_file.read_text(encoding="utf-8"))
            if not isinstance(plugins, list):
                plugins = []
        except (json.JSONDecodeError, OSError):
            plugins = []

    if "logrelay" not in plugins:
        plugins.append("logrelay")
        cp_file.write_text(json.dumps(plugins, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("  ✓ 已注册到 community-plugins.json")
    else:
        print("  ✓ 已在 community-plugins.json 中（无需重复注册）")


def uninstall_plugin(vault_root: Path):
    """卸载 Obsidian 插件。"""
    print("\n--- 卸载 Obsidian 插件 ---")

    deploy_dir = vault_root / PLUGIN_DEPLOY_DIR_NAME

    # 移除部署文件
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
        print(f"  ✓ 已删除 {deploy_dir}")
    else:
        print("  ○ 插件目录不存在，跳过")

    # 从 community-plugins.json 移除
    cp_file = vault_root / ".obsidian" / "community-plugins.json"
    if cp_file.exists():
        try:
            plugins = json.loads(cp_file.read_text(encoding="utf-8"))
            if "logrelay" in plugins:
                plugins.remove("logrelay")
                cp_file.write_text(json.dumps(plugins, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print("  ✓ 已从 community-plugins.json 移除")
        except (json.JSONDecodeError, OSError):
            pass


def install_all(vault_root: Path, tools: list[str], skip_plugin: bool = False):
    """完整安装流程：工具 hooks + Obsidian 插件。"""
    # Step 1: 工具适配器
    if tools:
        check_tool_dirs(vault_root, tools)
        install_tools(vault_root, tools)

    # Step 2: Obsidian 插件
    if not skip_plugin:
        if build_plugin():
            deploy_plugin(vault_root)
        else:
            print("\n  ⚠ Obsidian 插件构建跳过（不影响工具 hooks 功能）")

    print("\n" + "=" * 40)
    print("安装完成！")
    print("=" * 40)
    print("\n后续步骤：")
    if tools:
        print("  1. 工具 hooks 已就绪，直接使用即可")
    if not skip_plugin:
        print("  2. 在 Obsidian 中按 Cmd+Shift+R 重新加载，插件将自动启用")
        print("  3. 在 Obsidian 设置 → LogRelay 中可调整插件参数")
    print("\n提示：切换平台后重新运行 install.py 即可适配。")


def main():
    all_tools_str = ",".join(SUPPORTED_TOOLS)

    parser = argparse.ArgumentParser(
        description="LogRelay 一键安装脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
示例：
  python3 install.py                          # 全部安装（所有工具 + Obsidian 插件）
  python3 install.py --tools claude-code      # 仅安装 Claude Code
  python3 install.py --plugin-only            # 仅构建部署 Obsidian 插件
  python3 install.py --skip-plugin            # 安装所有工具，跳过插件
  python3 install.py --uninstall claude-code  # 卸载 Claude Code

支持的工具: {all_tools_str}
""",
    )
    parser.add_argument(
        "--tools",
        default=None,
        help=f"要安装的工具，逗号分隔（默认: 全部）",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="卸载模式，指定要卸载的工具",
    )
    parser.add_argument(
        "--plugin-only",
        action="store_true",
        help="仅构建部署 Obsidian 插件",
    )
    parser.add_argument(
        "--skip-plugin",
        action="store_true",
        help="跳过 Obsidian 插件构建",
    )
    args = parser.parse_args()

    vault_root = check_environment()

    # 卸载模式
    if args.uninstall:
        tools = [t.strip() for t in args.tools.split(",")] if args.tools else SUPPORTED_TOOLS
        uninstall_tools(vault_root, tools)
        return

    # 仅插件模式
    if args.plugin_only:
        if build_plugin():
            deploy_plugin(vault_root)
        return

    # 正常安装
    tools = [t.strip() for t in args.tools.split(",")] if args.tools else SUPPORTED_TOOLS

    # 验证工具名
    for tool in tools:
        if tool not in SUPPORTED_TOOLS:
            print(f"错误：不支持的工具 '{tool}'")
            print(f"支持的工具: {all_tools_str}")
            sys.exit(1)

    install_all(vault_root, tools, skip_plugin=args.skip_plugin)


if __name__ == "__main__":
    main()
