from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.kb_validate import main, validate_vault


COMMON_FIELDS = """\
id: KB-20260813-000001
title: 测试笔记
type: project
status: active
created: 2026-08-13
updated: 2026-08-13
owner: 李大谱
confidence: confirmed
source_refs: []
related: []
review_date: 2026-08-20
"""


class ValidateVaultTests(unittest.TestCase):
    def write_note(self, root: Path, relative_path: str, frontmatter: str) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{frontmatter}---\n\n# 测试笔记\n", encoding="utf-8")

    def test_valid_formal_note_has_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(root, "10-项目/测试笔记.md", COMMON_FIELDS)

            issues = validate_vault(root)

        self.assertEqual([], [issue for issue in issues if issue.level == "ERROR"])

    def test_missing_required_field_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(
                root,
                "10-项目/测试笔记.md",
                COMMON_FIELDS.replace("owner: 李大谱\n", ""),
            )

            issues = validate_vault(root)

        self.assertTrue(any(issue.code == "MISSING_REQUIRED_FIELD" for issue in issues))

    def test_invalid_type_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(
                root,
                "10-项目/测试笔记.md",
                COMMON_FIELDS.replace("type: project", "type: asset"),
            )

            issues = validate_vault(root)

        self.assertTrue(any(issue.code == "INVALID_TYPE" for issue in issues))

    def test_invalid_confidence_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(
                root,
                "10-项目/测试笔记.md",
                COMMON_FIELDS.replace("confidence: confirmed", "confidence: unknown"),
            )

            issues = validate_vault(root)

        self.assertTrue(any(issue.code == "INVALID_CONFIDENCE" for issue in issues))

    def test_duplicate_id_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(root, "10-项目/a.md", COMMON_FIELDS)
            self.write_note(
                root,
                "20-资产/b.md",
                COMMON_FIELDS.replace("type: project", "type: asset"),
            )

            issues = validate_vault(root)

        duplicate_issues = [issue for issue in issues if issue.code == "DUPLICATE_ID"]
        self.assertEqual(2, len(duplicate_issues))

    def test_inbox_note_may_have_incomplete_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(root, "01-收件箱/待整理.md", "title: 待整理\n")

            issues = validate_vault(root)

        self.assertEqual([], [issue for issue in issues if issue.level == "ERROR"])

    def test_raw_source_is_not_parsed_as_formal_note(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(root, "30-资源/raw/原始资料.md", "not: valid frontmatter\n")

            issues = validate_vault(root)

        self.assertEqual([], [issue for issue in issues if issue.level == "ERROR"])

    def test_framework_indexes_are_not_parsed_as_formal_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for directory in (
                "10-项目",
                "20-资产",
                "30-资源",
                "40-辅助",
                "50-灵感",
                "60-Skill",
            ):
                self.write_note(root, f"{directory}/Index.md", "title: 导航\n")

            issues = validate_vault(root)

        self.assertEqual([], [issue for issue in issues if issue.level == "ERROR"])

    def test_cli_returns_one_and_prints_stable_tsv_for_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(
                root,
                "10-项目/测试笔记.md",
                COMMON_FIELDS.replace("owner: 李大谱\n", ""),
            )
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([str(root)])

        self.assertEqual(1, exit_code)
        self.assertEqual(
            "ERROR\tMISSING_REQUIRED_FIELD\t10-项目/测试笔记.md\tmissing required field: owner\n",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
