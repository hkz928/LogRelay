"""Claude Code 适配器。

全自动模式：通过 hooks 配置实现会话自动记录。
配置位置：.claude/settings.json
日志规则写入 CLAUDE.md（始终生效，无需斜杠命令）。
"""

import json
from pathlib import Path

from ..core.config import get_python_cmd, get_scripts_root


def generate_hooks_config() -> dict:
    """生成 Claude Code hooks 配置。"""
    scripts_root = get_scripts_root()
    python_cmd = get_python_cmd()

    hooks = {
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{python_cmd} \"{scripts_root}/src/hooks/session_start.py\" --tool claude-code",
                    }
                ],
            }
        ],
    }

    return hooks


# CLAUDE.md 中追加的日志记录规则片段
CLAUDE_MD_RULE = """\

---

## LogRelay Session Logging

### 会话结束日志记录规则

当用户说以下任何一种时，执行会话日志保存：
- "结束日志" / "保存日志" / "end log"
- "记录会话" / "记录一下"

#### 执行步骤

1. **回顾本次会话**：梳理全部对话和工作内容
2. **定位会话信息**：从系统提示中提取 `SESSION_ID` 和 `LOG_PATH`（由 SessionStart hook 注入）
3. **生成完整日志**：用 Write 工具直接写入日志文件（路径来自 `LOG_PATH`），格式如下：

```
---
tool: "claude-code"
session_id: "{SESSION_ID}"
project: "{项目名}"
started: "{开始时间}"
ended: "{当前时间}"
status: completed
tags: [{标签}]
---

## 摘要
{一句话总结}

## 任务清单
- [x] 已完成任务
- [ ] 未完成任务

## 关键决策
- 决策及原因

## 产出物
- 文件路径

## 上下文传递
- 依赖前置会话: {路径}
- 相关文件: {路径}

---

## 完整对话记录

{本次会话的全部对话按时间线整理，包括：
- 每个 user 消息的摘要
- 每个 assistant 响应的关键操作（读了什么文件、改了什么代码、运行了什么命令）
- 保留关键的技术细节和决策理由}
```

4. **更新 STATUS.md**：用 Write 工具更新 `logs/STATUS.md`
5. **确认**：告诉用户日志已保存

#### 关键要求
- 日志必须包含**完整对话记录**，不能只有摘要
- 保留技术细节（具体文件路径、命令输出、错误信息等）
- 如果没有 SESSION_ID，从 `logs/claude-code/` 目录找 status 为 active 的日志
"""


def install(vault_root: Path) -> None:
    """安装 Claude Code hooks 配置和日志规则。"""
    settings_file = vault_root / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    # 读取现有配置
    settings = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            settings = {}

    # 合并 hooks
    new_hooks = generate_hooks_config()
    if "hooks" not in settings:
        settings["hooks"] = {}

    for event, configs in new_hooks.items():
        if event not in settings["hooks"]:
            settings["hooks"][event] = configs
        else:
            existing_commands = {
                h["command"]
                for c in settings["hooks"][event]
                for h in c.get("hooks", [])
            }
            for config in configs:
                new_commands = {
                    h["command"] for h in config.get("hooks", [])
                }
                if not new_commands & existing_commands:
                    settings["hooks"][event].append(config)

    settings_file.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Claude Code hooks 已写入 {settings_file}")

    # 确保 CLAUDE.md 中有日志规则
    claude_md = vault_root / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if "LogRelay Session Logging" not in content:
            claude_md.write_text(content + "\n" + CLAUDE_MD_RULE, encoding="utf-8")
            print(f"  ✓ 日志规则已追加到 CLAUDE.md")
        else:
            print(f"  ✓ CLAUDE.md 中已有日志规则（无需重复写入）")
    else:
        claude_md.write_text(CLAUDE_MD_RULE, encoding="utf-8")
        print(f"  ✓ CLAUDE.md 已创建并写入日志规则")


def uninstall(vault_root: Path) -> None:
    """卸载 Claude Code hooks 配置和日志规则。"""
    settings_file = vault_root / ".claude" / "settings.json"
    if not settings_file.exists():
        return

    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    hooks = settings.get("hooks", {})
    scripts_root = get_scripts_root()

    for event in list(hooks.keys()):
        hooks[event] = [
            config
            for config in hooks[event]
            if not any(
                str(scripts_root) in h.get("command", "")
                for h in config.get("hooks", [])
            )
        ]
        if not hooks[event]:
            del hooks[event]

    if not hooks:
        settings.pop("hooks", None)

    settings_file.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Claude Code hooks 已从 {settings_file} 移除")

    # 从 CLAUDE.md 中移除日志规则
    claude_md = vault_root / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if "LogRelay Session Logging" in content:
            marker = "\n---\n\n## LogRelay Session Logging"
            idx = content.find(marker)
            if idx > 0:
                content = content[:idx].rstrip() + "\n"
                claude_md.write_text(content, encoding="utf-8")
                print(f"  ✓ 日志规则已从 CLAUDE.md 移除")
