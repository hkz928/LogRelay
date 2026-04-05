"""Trae CN（国内版 Trae）适配器。

全自动模式：通过 hooks 配置实现会话自动记录。
配置位置：.trae-cn/skills/logrelay/
机制与 Trae 国际版一致，仅配置目录不同。
"""

import json
from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root

RULE_CONTENT = """---
name: logrelay
description: 跨工具工作日志接力系统。会话开始时自动加载未完成任务，会话结束时用户说"保存日志"或"结束日志"触发日志保存，生成双层日志（摘要层+对话层）并更新 STATUS.md。
---

# LogRelay 工作日志接力

## 规则

每次会话开始时：
1. 检查当前项目目录下是否存在 `logs/STATUS.md`
2. 如果存在，读取其中的「未完成任务」列表
3. 向用户报告有未完成的工作可以继续

## 会话结束日志记录

当用户说以下任何一种时，执行会话日志保存：
- "结束日志" / "保存日志" / "end log"
- "记录会话" / "记录一下"

### 执行步骤

1. 回顾本次会话的全部工作内容
2. 从 SessionStart hook 输出中找到 `SESSION_ID` 和 `LOG_PATH`
3. 生成结构化摘要（JSON 格式）：
   ```json
   {{
     "summary": "一段话总结本次会话（不超过200字）",
     "tasks": [{{"text": "任务描述", "completed": true/false}}],
     "decisions": ["关键决策1"],
     "artifacts": ["创建或修改的文件路径"],
     "related_files": ["相关文件路径"],
     "handoff_to": null,
     "conversation": "完整对话记录（按时间线整理每个交互的关键操作和技术细节）"
   }}
   ```
4. 运行命令：
   `{python_cmd} "{scripts_root}/src/hooks/session_end.py" --tool trae-cn --session-id <SESSION_ID> --data '<JSON数据>'`

### 双层日志架构
- 日志文件用 `%%` 分隔为两层
- 摘要层（%% 之前）：下次会话自动加载，包含摘要/任务/决策/产出物
- 对话层（%% 之后）：完整对话记录，仅按需查看
- `%%` 必须独占一行，前后各有一个空行
"""


def generate_hooks_config() -> dict:
    """生成 Trae CN hooks 配置。"""
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()

    return {
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": python_cmd + ' "' + str(scripts_root) + '/src/hooks/session_start.py" --tool trae-cn',
                    }
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit|Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": python_cmd + ' "' + str(scripts_root) + '/src/hooks/post_tool_use.py" --tool trae-cn',
                    }
                ],
            }
        ],
    }


def install(vault_root: Path) -> None:
    """安装 Trae CN hooks 配置和日志规则。"""
    skills_dir = vault_root / ".trae-cn" / "skills" / "logrelay"
    skills_dir.mkdir(parents=True, exist_ok=True)

    hooks_config = generate_hooks_config()
    hooks_file = skills_dir / "hooks.json"
    hooks_file.write_text(json.dumps(hooks_config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Trae CN hooks 已写入 {hooks_file}")

    # 写入 SKILL.md（Trae skill 入口文件，AI 自动加载）
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(
        RULE_CONTENT.format(python_cmd=python_cmd, scripts_root=scripts_root),
        encoding="utf-8",
    )
    print(f"  ✓ Trae CN SKILL.md 已写入 {skill_file}")


def uninstall(vault_root: Path) -> None:
    """卸载 Trae CN hooks 配置。"""
    skills_dir = vault_root / ".trae-cn" / "skills" / "logrelay"
    if skills_dir.exists():
        import shutil
        shutil.rmtree(skills_dir)
        print(f"  ✓ Trae CN hooks 已移除 {skills_dir}")
