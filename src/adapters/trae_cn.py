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

### 关键：获取 SESSION_ID

SESSION_ID 由会话启动时的 SessionStart hook 自动生成，格式为 `2026-04-06_HHMMSS`（如 `2026-04-06_143025`）。

**获取方式（按优先级）**：
1. 查看会话开始时的系统输出，找 `[LogRelay] SESSION_ID=` 行，等号后面的值即为 SESSION_ID
2. 如果找不到，运行命令搜索当前项目的活跃日志文件：
   `grep -rl "status: active" 项目目录/logs/trae-cn/ 2>/dev/null || grep -rl "status: active" logs/trae-cn/ 2>/dev/null`
   从找到的文件名中提取 SESSION_ID（文件名格式：`2026-04-06_HHMMSS-xxx.md`，取前 17 个字符）
3. 如果仍找不到，用当前时间生成一个：`2026-04-06_HHMMSS`（年-月-日_时分秒）

### 执行步骤

1. 回顾本次会话的全部工作内容
2. 按上述方式获取 SESSION_ID
3. 生成结构化摘要（JSON 格式）：
   ```json
   {{
     "summary": "一段话总结本次会话（不超过200字）",
     "tasks": [{{"text": "任务描述", "completed": true/false}}],
     "decisions": ["关键决策1"],
     "artifacts": ["创建或修改的文件路径"],
     "related_files": ["相关文件路径"],
     "handoff_to": null,
     "conversation": "完整对话记录（必须按时间线整理，每条包含时间戳、用户说了什么、助手做了什么关键操作）"
   }}
   ```

   **conversation 字段要求**：
   - 必须是按时间线整理的完整对话记录，不能只是一句话概括
   - 格式示例："### [14:30] User: 要求优化PPT演讲词\\n### [14:31] Assistant: 读取了会议纪要文件...\\n### [14:35] User: 语言要平实\\n### [14:36] Assistant: 修改了 Page1-7 的演讲词..."

4. 运行命令：
   `{python_cmd} "{scripts_root}/src/hooks/session_end.py" --tool trae-cn --session-id <SESSION_ID> --data '<JSON数据>'`

5. 如果命令报"未找到活跃日志文件"或 session_id 无法匹配，说明 SessionStart hook 可能未触发。此时改为直接写入日志：
   - 在项目的 `logs/trae-cn/` 目录下创建日志文件（如不存在则创建目录）
   - 文件名格式：`SESSION_ID-摘要关键词.md`
   - 写入包含 frontmatter + 摘要层 + %% + 对话层的完整日志
   - 同时更新 `logs/STATUS.md`

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
