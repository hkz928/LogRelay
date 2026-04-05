"""LogRelay Hook 集成测试。"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "src"


class TestSessionStartHook(unittest.TestCase):
    """session_start.py 集成测试。"""

    def test_session_start_creates_log(self):
        """会话开始应创建日志文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            (vault / "my_project").mkdir()
            project = vault / "大庆油田"
            project.mkdir()

            result = subprocess.run(
                [sys.executable, str(SCRIPTS_ROOT / "hooks" / "session_start.py"),
                 "--tool", "claude-code", "--cwd", str(project)],
                capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("[LogRelay] 项目:", result.stdout)

            # 检查日志文件创建
            logs_dir = project / "logs" / "claude-code"
            log_files = list(logs_dir.glob("*.md"))
            self.assertEqual(len(log_files), 1)

            # 检查日志内容
            content = log_files[0].read_text(encoding="utf-8")
            self.assertIn("claude-code", content)
            self.assertIn("active", content)

    def test_session_start_reads_status(self):
        """会话开始应读取并输出 STATUS.md 内容。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            (vault / "my_project").mkdir()
            project = vault / "大庆油田"
            project.mkdir()

            # 预创建 STATUS.md
            logs_dir = project / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            status_content = """---
project: "大庆油田"
project_path: "大庆油田"
updated: "2026-04-05T15:45:10"
active_session: null
---

# 项目状态：大庆油田

## 未完成任务

- 数据库表结构设计

## 已完成任务（最近5条）


## 会话历史

"""
            (logs_dir / "STATUS.md").write_text(status_content, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPTS_ROOT / "hooks" / "session_start.py"),
                 "--tool", "claude-code", "--cwd", str(project)],
                capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("未完成任务", result.stdout)


class TestSessionEndHook(unittest.TestCase):
    """session_end.py 集成测试。"""

    def _create_session(self, project_dir: Path) -> str:
        """创建一个活跃会话，返回 session_id。"""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_ROOT / "hooks" / "session_start.py"),
             "--tool", "claude-code", "--cwd", str(project_dir)],
            capture_output=True, text=True,
        )
        for line in result.stdout.split("\n"):
            if line.startswith("[LogRelay] SESSION_ID="):
                return line.split("=", 1)[1].strip()
        raise ValueError(f"未找到 SESSION_ID，输出: {result.stdout}")

    def test_session_end_updates_log(self):
        """会话结束应更新日志文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            (vault / "my_project").mkdir()
            project = vault / "大庆油田"
            project.mkdir()

            session_id = self._create_session(project)

            data = json.dumps({
                "summary": "完成了数据库设计",
                "tasks": [{"text": "设计表结构", "completed": True}],
                "decisions": ["选择 PostgreSQL"],
                "artifacts": ["schema.sql"],
            })

            result = subprocess.run(
                [sys.executable, str(SCRIPTS_ROOT / "hooks" / "session_end.py"),
                 "--tool", "claude-code", "--session-id", session_id,
                 "--cwd", str(project), "--data", data],
                capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("会话已结束", result.stdout)

            # 验证日志文件已更新
            logs_dir = project / "logs" / "claude-code"
            log_files = list(logs_dir.glob("*.md"))
            self.assertEqual(len(log_files), 1)

            content = log_files[0].read_text(encoding="utf-8")
            self.assertIn("completed", content)
            self.assertIn("数据库设计", content)

            # 验证 STATUS.md 已生成
            status_file = project / "logs" / "STATUS.md"
            self.assertTrue(status_file.exists())
            status_content = status_file.read_text(encoding="utf-8")
            self.assertIn("大庆油田", status_content)


if __name__ == "__main__":
    unittest.main()
