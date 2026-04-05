"""LogRelay 核心模块单元测试。"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 确保 src 可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.utils import (
    find_vault_root,
    find_project_root,
    ensure_logs_dir,
    generate_filename,
    get_timestamp,
    normalize_path,
)
from core.config import get_vault_root, get_python_cmd, SUPPORTED_TOOLS
from core.formatter import (
    create_log_content,
    parse_frontmatter,
    format_frontmatter,
    update_ended_status,
)
from core.status_manager import (
    read_status,
    write_status,
    create_initial_status,
    update_status_on_session_end,
    get_pending_tasks,
    get_recent_sessions,
)


class TestUtils(unittest.TestCase):
    """工具函数测试。"""

    def test_generate_filename_with_keywords(self):
        name = generate_filename("数据治理方案")
        self.assertTrue(name.endswith(".md"))
        self.assertIn("数据治理方案", name)

    def test_generate_filename_without_keywords(self):
        name = generate_filename()
        self.assertTrue(name.endswith(".md"))
        self.assertRegex(name, r"\d{4}-\d{2}-\d{2}_\d{6}\.md")

    def test_get_timestamp(self):
        ts = get_timestamp()
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_normalize_path(self):
        self.assertEqual(normalize_path(Path("a/b/c")), "a/b/c")
        result = normalize_path(Path("a\\b\\c"))
        self.assertNotIn("\\", result)

    def test_ensure_logs_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            logs_dir = ensure_logs_dir(project, "claude-code")
            self.assertTrue(logs_dir.exists())
            self.assertEqual(logs_dir.name, "claude-code")
            self.assertEqual(logs_dir.parent.name, "logs")

    def test_find_vault_root(self):
        """测试 vault 根目录定位。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            (vault / "my_project").mkdir()
            result = find_vault_root(vault / "my_project" / "sub")
            self.assertEqual(result.resolve(), vault.resolve())

    def test_find_vault_root_no_marker(self):
        """无 vault 标记时应抛出异常。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                find_vault_root(Path(tmpdir))

    def test_find_project_root_at_vault(self):
        """在 vault 根目录时返回 global。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            (vault / "my_project").mkdir()
            path, name = find_project_root(vault, vault)
            self.assertEqual(name, "global")

    def test_find_project_root_in_project(self):
        """在项目子目录时返回项目名。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            project = vault / "大庆油田"
            project.mkdir()
            path, name = find_project_root(project / "子系统", vault)
            self.assertEqual(name, "大庆油田")


class TestFormatter(unittest.TestCase):
    """格式化模块测试。"""

    def test_format_frontmatter(self):
        data = {
            "tool": "claude-code",
            "status": "active",
            "tags": ["a", "b"],
            "ended": None,
        }
        result = format_frontmatter(data)
        self.assertIn("---", result)
        self.assertIn('"claude-code"', result)
        self.assertIn("null", result)

    def test_parse_frontmatter(self):
        content = '---\ntool: "claude-code"\nstatus: active\ntags: [a, b]\nended: null\n---'
        result = parse_frontmatter(content)
        self.assertEqual(result["tool"], "claude-code")
        self.assertEqual(result["status"], "active")
        self.assertIsNone(result["ended"])
        self.assertEqual(result["tags"], ["a", "b"])

    def test_parse_frontmatter_empty(self):
        result = parse_frontmatter("no frontmatter here")
        self.assertEqual(result, {})

    def test_create_log_content(self):
        fm = {"tool": "test", "status": "active"}
        content = create_log_content(
            fm,
            summary="测试摘要",
            tasks=[{"text": "任务1", "completed": True}, {"text": "任务2", "completed": False}],
            decisions=["决策1"],
            artifacts=["file1.py"],
        )
        self.assertIn("## 摘要", content)
        self.assertIn("测试摘要", content)
        self.assertIn("[x] 任务1", content)
        self.assertIn("[ ] 任务2", content)
        self.assertIn("决策1", content)
        self.assertIn("file1.py", content)

    def test_update_ended_status(self):
        content = '---\ntool: "test"\nstatus: active\nended: null\n---\n\n## 摘要'
        result = update_ended_status(content, "2026-04-05T12:00:00", "completed")
        self.assertIn('"2026-04-05T12:00:00"', result)
        self.assertIn("status: completed", result)

    def test_roundtrip_frontmatter(self):
        """序列化后再反序列化应一致。"""
        original = {
            "tool": "trae",
            "session_id": "2026-04-05_test",
            "status": "paused",
        }
        formatted = format_frontmatter(original)
        parsed = parse_frontmatter(formatted)
        self.assertEqual(parsed["tool"], original["tool"])
        self.assertEqual(parsed["status"], original["status"])


class TestStatusManager(unittest.TestCase):
    """STATUS.md 管理测试。"""

    def test_create_and_read_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            create_initial_status(project, "测试项目")
            status = read_status(project)
            self.assertIsNotNone(status)
            self.assertEqual(status["frontmatter"]["project"], "测试项目")

    def test_update_status_on_session_end(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            create_initial_status(project, "测试项目")

            session_info = {
                "tool": "claude-code",
                "session_id": "2026-04-05_143025",
                "summary": "完成了 API 设计",
                "tasks": [
                    {"text": "API 设计", "completed": True},
                    {"text": "数据库设计", "completed": False},
                ],
                "decisions": ["RESTful 风格"],
                "artifacts": ["api_design.md"],
                "log_path": "logs/claude-code/2026-04-05_143025.md",
                "handoff_to": None,
            }
            update_status_on_session_end(project, "测试项目", session_info)

            status = read_status(project)
            self.assertIsNotNone(status)

            # 检查未完成任务
            pending = get_pending_tasks(status)
            self.assertEqual(len(pending), 1)
            self.assertIn("数据库设计", str(pending))

            # 检查已完成任务
            sections = status["sections"]
            completed = sections.get("已完成任务（最近5条）", [])
            self.assertTrue(any("API 设计" in str(c) for c in completed))

            # 检查会话历史
            recent = get_recent_sessions(status, 5)
            self.assertTrue(len(recent) > 0)

    def test_read_status_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            status = read_status(Path(tmpdir))
            self.assertIsNone(status)

    def test_multiple_sessions_accumulate(self):
        """多次会话应累积任务和历史。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            create_initial_status(project, "多会话项目")

            for i in range(3):
                update_status_on_session_end(project, "多会话项目", {
                    "tool": "claude-code",
                    "session_id": f"2026-04-0{i+1}_100000",
                    "summary": f"会话 {i+1}",
                    "tasks": [{"text": f"任务 {i+1}", "completed": i == 0}],
                    "decisions": [],
                    "artifacts": [],
                    "log_path": f"logs/claude-code/2026-04-0{i+1}_100000.md",
                    "handoff_to": None,
                })

            status = read_status(project)
            pending = get_pending_tasks(status)
            self.assertEqual(len(pending), 2)  # 任务2和任务3未完成

            recent = get_recent_sessions(status)
            self.assertTrue(len(recent) >= 3)


class TestEndToEnd(unittest.TestCase):
    """端到端测试：模拟完整会话生命周期。"""

    def test_full_session_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            project = vault / "大庆油田"
            project.mkdir()
            (vault / "my_project").mkdir()

            # 模拟会话1：Trae
            logs_dir = ensure_logs_dir(project, "trae")
            session_id_1 = "2026-04-05_143025"
            log_file = logs_dir / f"{session_id_1}-数据治理方案.md"

            fm = {
                "tool": "trae",
                "session_id": session_id_1,
                "project": "大庆油田",
                "project_path": "project/大庆油田",
                "started": "2026-04-05T14:30:25",
                "status": "active",
            }
            content = create_log_content(fm, summary="API 设计")
            log_file.write_text(content, encoding="utf-8")

            # 结束会话1
            ended_content = update_ended_status(content, "2026-04-05T15:45:10", "paused")
            log_file.write_text(ended_content, encoding="utf-8")

            update_status_on_session_end(project, "大庆油田", {
                "tool": "trae",
                "session_id": session_id_1,
                "summary": "完成了 API 设计",
                "tasks": [
                    {"text": "API 设计", "completed": True},
                    {"text": "数据库表结构", "completed": False},
                ],
                "decisions": ["RESTful"],
                "artifacts": ["api.md"],
                "log_path": "project/大庆油田/logs/trae/2026-04-05_143025.md",
            })

            # 模拟会话2：Claude Code 接手
            status = read_status(project)
            self.assertIsNotNone(status)

            pending = get_pending_tasks(status)
            self.assertEqual(len(pending), 1)
            self.assertIn("数据库表结构", str(pending))

            # 验证 STATUS.md 文件存在且内容正确
            status_file = project / "logs" / "STATUS.md"
            self.assertTrue(status_file.exists())
            status_content = status_file.read_text(encoding="utf-8")
            self.assertIn("大庆油田", status_content)
            self.assertIn("数据库表结构", status_content)


if __name__ == "__main__":
    unittest.main()
