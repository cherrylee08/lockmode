from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from scripts.kb_migration_audit import (
    classify_note,
    is_excluded_path,
    render_report,
    scan_legacy_notes,
    main,
)


class MigrationAuditTests(unittest.TestCase):
    CASES = {
        "虎客科技技术客服 AI 副驾方案框架.md": "project",
        "企业AI服务体系与参考报价.md": "asset_candidate",
        "视频拆解-RAG向量库实战.md": "resource",
        "系统化提示词-经营驾驶舱.md": "helper",
        "想法库.md": "inspiration",
        "小淀镇企业调研方法论与评分体系.md": "skill_candidate",
    }

    def test_representative_legacy_notes_receive_expected_suggestions(self) -> None:
        for filename, expected_type in self.CASES.items():
            with self.subTest(filename=filename):
                suggestion = classify_note(Path(filename), "")
                self.assertEqual(expected_type, suggestion.suggested_type)
                self.assertTrue(suggestion.requires_confirmation)

    def test_filename_priority_preserves_idea_and_quote_classification(self) -> None:
        idea = classify_note(Path("想法库.md"), "包含系统化提示词与模板的摘录")
        quote = classify_note(Path("企业AI服务体系与参考报价.md"), "有一份方法论和提示词")

        self.assertEqual("inspiration", idea.suggested_type)
        self.assertEqual("asset_candidate", quote.suggested_type)

    def test_excluded_directories_are_not_scanned(self) -> None:
        excluded = (
            "10-项目/example.md",
            "20-资产/example.md",
            "30-资源/example.md",
            "40-辅助/example.md",
            "50-灵感/example.md",
            "60-Skill/example.md",
            ".obsidian/example.md",
            ".git/example.md",
            "docs/example.md",
            ".superpowers/example.md",
            "Templates/example.md",
            "scripts/example.md",
            "tests/example.md",
        )
        for relative_path in excluded:
            with self.subTest(relative_path=relative_path):
                self.assertTrue(is_excluded_path(Path(relative_path)))

    def test_scan_returns_only_root_legacy_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "企业AI服务体系与参考报价.md").write_text("最终确认版", encoding="utf-8")
            (root / "AGENTS.md").write_text("系统规则", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "视频拆解-RAG向量库实战.md").write_text("", encoding="utf-8")
            (root / "10-项目").mkdir()
            (root / "10-项目" / "虎客科技技术客服 AI 副驾方案框架.md").write_text("", encoding="utf-8")

            suggestions = scan_legacy_notes(root)

        self.assertEqual(["企业AI服务体系与参考报价.md"], [item.source for item in suggestions])
        self.assertEqual("asset_candidate", suggestions[0].suggested_type)

    def test_report_states_no_files_were_moved_and_has_required_columns(self) -> None:
        item = classify_note(Path("企业AI服务体系与参考报价.md"), "最终确认版")

        report = render_report([item], "2026-08-13")

        self.assertIn("未移动、重命名、复制或修改任何既有文档", report)
        self.assertIn("当前文件 | 建议主归属 | 建议目标 | 置信度 | 理由 | 是否需确认", report)
        self.assertIn("企业AI服务体系与参考报价.md", report)

    def test_weak_score_requires_human_review(self) -> None:
        suggestion = classify_note(Path("待整理材料.md"), "一段普通记录")

        self.assertEqual("review_required", suggestion.suggested_type)
        self.assertEqual("low", suggestion.confidence)
        self.assertTrue(suggestion.requires_confirmation)

    def test_tied_top_score_requires_human_review(self) -> None:
        suggestion = classify_note(Path("混合笔记.md"), "报告 提示词")

        self.assertEqual("review_required", suggestion.suggested_type)
        self.assertEqual("low", suggestion.confidence)
        self.assertTrue(suggestion.requires_confirmation)

    def test_cli_refuses_to_overwrite_scanned_legacy_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "想法库.md"
            original = "用户原始内容\n".encode("utf-8")
            source.write_bytes(original)
            stderr = StringIO()

            with redirect_stderr(stderr):
                exit_code = main([str(root), "--output", "想法库.md", "--date", "2026-08-13"])

            self.assertNotEqual(0, exit_code)
            self.assertIn("Refusing to overwrite", stderr.getvalue())
            self.assertEqual(original, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
