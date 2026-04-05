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
description: 跨工具工作日志接力系统。会话结束时用户说"保存日志"触发日志保存到 logs/trae-cn/ 目录并更新 logs/STATUS.md。
---

# LogRelay 工作日志接力

当用户说 "结束日志" / "保存日志" / "end log" / "记录会话" / "记录一下" 时，执行以下保存流程。

## 保存流程

### 第一步：确定项目和路径

当前工作目录即为"项目目录"。日志存放路径规则：
- 日志文件：`<项目目录>/logs/trae-cn/<文件名>.md`
- 状态文件：`<项目目录>/logs/STATUS.md`

例如当前工作目录是 `/Users/xxx/vault/project/五厂/`，则：
- 日志存到 `/Users/xxx/vault/project/五厂/logs/trae-cn/2026-04-06_143025-演讲词优化.md`
- STATUS.md 在 `/Users/xxx/vault/project/五厂/logs/STATUS.md`

### 第二步：生成 SESSION_ID

SESSION_ID 格式为 `YYYY-MM-DD_HHMMSS`（如 `2026-04-06_143025`），用当前时间生成即可。

### 第三步：运行保存命令

```bash
mkdir -p <项目目录>/logs/trae-cn && python3 "{scripts_root}/src/hooks/session_end.py" --tool trae-cn --session-id <SESSION_ID> --data '<JSON数据>'
```

其中 JSON 数据格式：
```json
{{
  "summary": "一段话总结本次会话（不超过200字）",
  "tasks": [{{"text": "任务描述", "completed": true/false}}],
  "decisions": ["关键决策1"],
  "artifacts": ["创建或修改的文件路径"],
  "related_files": ["相关文件路径"],
  "handoff_to": null,
  "conversation": "完整对话记录（按时间线整理）"
}}
```

### 第四步：如果命令失败，手动写入日志

用文件写入工具直接创建日志文件 `<项目目录>/logs/trae-cn/<SESSION_ID>-<关键词>.md`，内容格式：

```
---
tool: "trae-cn"
session_id: "<SESSION_ID>"
project: "<项目名>"
started: "<开始时间>"
ended: "<当前时间>"
status: completed
tags: []
---

## 摘要
<一段话总结>

## 任务清单
- [x] 已完成任务
- [ ] 未完成任务

## 关键决策
- 决策及原因

## 产出物
- 文件路径

## 上下文传递
- 相关文件: 路径

%%

## 完整对话记录

### [HH:MM] User: 用户说了什么
### [HH:MM] Assistant: 做了什么关键操作（读了什么、改了什么、运行了什么）
```

同时更新或创建 `<项目目录>/logs/STATUS.md`。

**重要：日志文件必须写到 `logs/trae-cn/` 目录下，不能写到项目其他位置。STATUS.md 必须在 `logs/` 目录下。**
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
