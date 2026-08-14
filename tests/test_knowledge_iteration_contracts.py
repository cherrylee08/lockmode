from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path
import subprocess

from scripts.kb_validate import FORMAL_DIRECTORIES, safe_markdown_paths


REPOSITORY_ROOT = Path(__file__).parents[1]


class KnowledgeIterationContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8-sig")

    def baseline_log(self) -> str:
        result = subprocess.run(
            ["git", "show", "4cbe676:00-系统/log.md"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            encoding="utf-8",
            errors="strict",
            check=True,
        )
        return result.stdout

    def test_weekly_review_storage_contract_is_documented_and_indexed(self) -> None:
        managed_instance = "`00-系统/每周复盘/YYYY-Www.md`"
        for relative_path in (
            "Templates/每周知识复盘模板.md",
            "40-辅助/每周30分钟知识复盘.md",
            "00-系统/知识库操作手册.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertIn(managed_instance, self.read(relative_path))

        weekly_index = REPOSITORY_ROOT / "00-系统/每周复盘/Index.md"
        self.assertTrue(weekly_index.is_file())
        self.assertIn("[[Templates/每周知识复盘模板", weekly_index.read_text(encoding="utf-8-sig"))
        self.assertIn("[[00-系统/每周复盘/Index", self.read("00-系统/index.md"))

    def test_owner_facing_baseline_matches_twelve_formal_notes(self) -> None:
        counts: Counter[str] = Counter()
        for directory, note_type in FORMAL_DIRECTORIES.items():
            for path in safe_markdown_paths(REPOSITORY_ROOT / directory):
                relative = path.relative_to(REPOSITORY_ROOT)
                if path.name == "Index.md" or (directory == "30-资源" and "raw" in relative.parts):
                    continue
                counts[note_type] += 1

        self.assertEqual(Counter({"asset": 8, "helper": 3, "project": 1}), counts)
        self.assertIn(
            "正式六框架笔记：12 篇（项目 1、资产 8、辅助 3；其余框架当前仅有 Index）",
            self.read("00-系统/健康报告.md"),
        )
        self.assertIn(
            "已确认进入六框架的正式内容：共 12 篇（项目 1 篇、资产 8 篇、辅助 3 篇）",
            self.read("10-项目/个人知识库管理系统.md"),
        )

    def test_owner_facing_root_markdown_count_distinguishes_the_first_audit_cohort(self) -> None:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.md"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            check=True,
        )
        root_markdown = [
            path.decode("utf-8")
            for path in result.stdout.split(b"\0")
            if path and b"/" not in path and path != b"AGENTS.md"
        ]

        self.assertEqual(63, len(root_markdown))
        current_count = (
            "Git 已跟踪的根目录 Markdown：63 篇（不含系统 AGENTS.md；首轮 51 篇中已迁移 8 篇、"
            "仍留 43 篇，首轮后新增 20 篇）"
        )
        self.assertIn(current_count, self.read("00-系统/健康报告.md"))
        self.assertIn(current_count, self.read("10-项目/个人知识库管理系统.md"))

    def test_operation_log_keeps_4cbe676_as_exact_prefix(self) -> None:
        self.assertTrue(self.read("00-系统/log.md").startswith(self.baseline_log()))

    def test_operation_log_has_only_task_one_to_four_blocks_after_baseline(self) -> None:
        current = self.read("00-系统/log.md")
        baseline = self.baseline_log()
        self.assertTrue(current.startswith(baseline))
        appended_headers = [
            line
            for line in current[len(baseline):].splitlines()
            if line.startswith("## [")
        ]
        self.assertEqual(
            [
                "## [2026-08-13] system | 知识迭代生命周期建立",
                "## [2026-08-13] dashboard | 知识迭代驾驶舱建立",
                "## [2026-08-13] helper | Clipper 与日周双循环辅助建立",
                "## [2026-08-13] verify | 知识迭代闭环验收",
            ],
            appended_headers,
        )

    def test_inbox_stage_completion_contract_is_documented(self) -> None:
        for relative_path in (
            "00-系统/元数据规范.md",
            "00-系统/知识库操作手册.md",
            "01-收件箱/Index.md",
        ):
            document = self.read(relative_path)
            with self.subTest(relative_path=relative_path):
                self.assertIn("`suggested_type`", document)
                self.assertIn("`related` 或 `review_date`", document)
                self.assertIn("`captured` / `triaged`", document)


if __name__ == "__main__":
    unittest.main()
