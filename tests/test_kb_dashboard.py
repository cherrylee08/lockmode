from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.kb_dashboard import (
    DashboardData,
    check_dashboard,
    collect_dashboard,
    render_dashboard,
    write_dashboard,
)


class DashboardTests(unittest.TestCase):
    today = date(2026, 8, 13)

    def write_note(self, root: Path, relative_path: str, frontmatter: str) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{frontmatter}---\n\n# 测试笔记\n", encoding="utf-8")

    def create_vault(self, root: Path) -> None:
        (root / "00-系统").mkdir(parents=True)
        self.write_note(
            root,
            "01-收件箱/最早未关联.md",
            "title: 最早未关联\ncaptured_at: 2026-08-01\nrelated: []\nsummary: 最早未关联摘要\nknowledge_stage: captured\n",
        )
        self.write_note(
            root,
            "01-收件箱/关联项目较晚.md",
            "title: 关联项目较晚\ncaptured_at: 2026-08-04\nrelated: [\"[[10-项目/项目A]]\"]\nsummary: 关联项目较晚摘要\nknowledge_stage: captured\n",
        )
        self.write_note(
            root,
            "01-收件箱/关联项目较早.md",
            "title: 关联项目较早\ncaptured_at: 2026-08-02\nrelated: [\"[[10-项目/项目A]]\"]\nsummary: 关联项目较早摘要\nknowledge_stage: captured\n",
        )
        self.write_note(
            root,
            "01-收件箱/最新未关联.md",
            "title: 最新未关联\ncaptured_at: 2026-08-05\nrelated: []\nsummary: 最新未关联摘要\nknowledge_stage: captured\n",
        )
        self.write_note(
            root,
            "10-项目/项目A.md",
            "title: 项目A\nstatus: active\nnext_action: \nreview_date: 2026-08-20\n",
        )
        self.write_note(
            root,
            "20-资产/到期笔记.md",
            "title: 到期笔记\nreview_date: 2026-08-12\n",
        )
        (root / "00-系统/待确认队列.md").write_text(
            "| 编号 | 状态 |\n| --- | --- |\n| Q-001 | 待确认 |\n| Q-002 | 已完成 |\n",
            encoding="utf-8",
        )

    def test_top_three_prioritizes_project_link_then_oldest_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)

            data = collect_dashboard(root, self.today)

        self.assertEqual(
            ("关联项目较早摘要", "关联项目较晚摘要", "最早未关联摘要"),
            data.top_three,
        )
        self.assertEqual(4, data.inbox_count)

    def test_top_three_only_prioritizes_existing_active_project_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)
            self.write_note(root, "20-资产/资产A.md", "title: 资产A\n")
            self.write_note(root, "10-项目/停滞项目.md", "title: 停滞项目\nstatus: paused\n")
            self.write_note(
                root,
                "01-收件箱/资产关联.md",
                "captured_at: 2026-07-01\nrelated: [\"[[20-资产/资产A]]\"]\nsummary: 资产关联\n",
            )
            self.write_note(
                root,
                "01-收件箱/停滞项目关联.md",
                "captured_at: 2026-07-02\nrelated: [\"[[10-项目/停滞项目]]\"]\nsummary: 停滞项目关联\n",
            )
            self.write_note(
                root,
                "01-收件箱/失效项目关联.md",
                "captured_at: 2026-07-03\nrelated: [\"[[10-项目/不存在]]\"]\nsummary: 失效项目关联\n",
            )

            data = collect_dashboard(root, self.today)

        self.assertEqual(
            ("关联项目较早摘要", "关联项目较晚摘要", "资产关联"),
            data.top_three,
        )

    def test_collects_current_week_review_and_uses_stable_path_tiebreaker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)
            review = """---
title: 本周复盘
week: 2026-W33
---

## 下周唯一业务输出

- 服务项目：项目A
- 解决问题：确定 Top 3 的客户优先级
- 验收标准：完成并确认驾驶舱

## 业务派生内容

- 题目：老板如何处理知识积压
- 来源项目：项目A
- 脱敏检查：已完成
"""
            later_review = review.replace("项目A", "项目Z").replace("老板如何处理知识积压", "不应被选择")
            (root / "00-系统/A-周复盘.md").write_text(review, encoding="utf-8")
            (root / "00-系统/Z-周复盘.md").write_text(later_review, encoding="utf-8")
            (root / "00-系统/旧周复盘.md").write_text(review.replace("2026-W33", "2026-W32"), encoding="utf-8")

            data = collect_dashboard(root, self.today)

        self.assertEqual(
            "服务项目：项目A；解决问题：确定 Top 3 的客户优先级；验收标准：完成并确认驾驶舱",
            data.weekly_business_output,
        )
        self.assertEqual("题目：老板如何处理知识积压；来源项目：项目A", data.weekly_content_derivative)

    def test_current_week_review_requires_effectively_filled_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)
            (root / "00-系统/周复盘.md").write_text(
                """---
week: 2026-W33
---

## 下周唯一业务输出

- 服务项目：
- 解决问题：
- 验收标准：

## 业务派生内容

- 题目：
- 来源项目：
""",
                encoding="utf-8",
            )

            data = collect_dashboard(root, self.today)

        self.assertIsNone(data.weekly_business_output)
        self.assertIsNone(data.weekly_content_derivative)

    def test_collects_overdue_reviews_and_projects_without_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)

            data = collect_dashboard(root, self.today)

        self.assertEqual(("到期笔记",), data.overdue_reviews)
        self.assertEqual(("项目A",), data.active_projects_without_next_action)

    def test_counts_only_waiting_pending_queue_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)

            data = collect_dashboard(root, self.today)

        self.assertEqual(1, data.pending_confirmations)

    def test_render_marks_unavailable_metrics_instead_of_inventing_values(self) -> None:
        rendered = render_dashboard(
            DashboardData(0, (), (), (), 0, None, None),
            "2026-08-13",
        )

        headings = [
            "# 知识迭代驾驶舱",
            "## 今日 Top 3",
            "## 本周唯一业务输出",
            "## 本周业务派生内容",
            "## 待确认",
            "## 活跃项目异常",
            "## 到期复查",
            "## 六项运行指标",
            "## 运行命令",
        ]
        self.assertEqual(sorted(headings, key=rendered.index), headings)
        self.assertIn("当前无待消化输入", rendered)
        self.assertIn("暂不可计算：缺少本周复盘记录", rendered)
        self.assertNotIn("消化完成率：0", rendered)

    def test_write_refuses_raw_formal_and_existing_non_managed_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)
            generated = "2026-08-13"
            existing = root / "00-系统/非受管页面.md"
            existing.write_text("保留", encoding="utf-8")
            targets = (
                root / "30-资源/raw/原始资料.md",
                root / "10-项目/项目A.md",
                existing,
                root.parent / "仓库外.md",
            )

            for target in targets:
                with self.subTest(target=target):
                    with self.assertRaises(ValueError):
                        write_dashboard(root, target, generated)

            self.assertEqual("保留", existing.read_text(encoding="utf-8"))

    @unittest.skipUnless(sys.platform == "win32", "directory junctions are a Windows reparse-point behavior")
    def test_write_refuses_managed_parent_directory_junction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            root = temporary_root / "vault"
            root.mkdir()
            outside = temporary_root / "outside"
            outside.mkdir()
            junction = root / "00-系统"
            created = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, created.returncode, created.stderr)

            with self.assertRaises(ValueError):
                write_dashboard(root, junction / "知识迭代驾驶舱.md", "2026-08-13")

            self.assertFalse((outside / "知识迭代驾驶舱.md").exists())

    def test_write_allows_only_exact_managed_dashboard_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)
            output = root / "00-系统/知识迭代驾驶舱.md"

            write_dashboard(root, output, "2026-08-13")

            self.assertTrue(output.is_file())
            self.assertEqual(
                render_dashboard(collect_dashboard(root, self.today), "2026-08-13"),
                output.read_text(encoding="utf-8"),
            )

    def test_check_compares_in_memory_without_writing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)
            output = root / "00-系统/知识迭代驾驶舱.md"
            self.assertFalse(check_dashboard(root, output, "2026-08-13"))
            self.assertFalse(output.exists())

            write_dashboard(root, output, "2026-08-13")
            before = output.read_text(encoding="utf-8")
            self.assertTrue(check_dashboard(root, output, "2026-08-13"))
            self.assertEqual(before, output.read_text(encoding="utf-8"))

    def test_direct_script_cli_generates_managed_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_vault(root)
            script = Path(__file__).parents[1] / "scripts" / "kb_dashboard.py"

            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(script),
                    str(root),
                    "--output",
                    "00-系统/知识迭代驾驶舱.md",
                    "--date",
                    "2026-08-13",
                ],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((root / "00-系统/知识迭代驾驶舱.md").is_file())


if __name__ == "__main__":
    unittest.main()
