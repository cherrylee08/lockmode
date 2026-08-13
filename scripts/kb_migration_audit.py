"""Read-only migration suggestions for legacy Markdown knowledge notes.

This module deliberately classifies from visible keywords only.  It never
renames, copies, moves, or edits a source note; the command-line entry point
only writes the separately requested suggestion report.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys


EXCLUDED_TOP_LEVEL = frozenset(
    {
        "01-收件箱",
        "10-项目",
        "20-资产",
        "30-资源",
        "40-辅助",
        "50-灵感",
        "60-Skill",
        "90-归档",
        ".obsidian",
        ".git",
        "docs",
        ".superpowers",
        "Templates",
        "scripts",
        "tests",
    }
)

TARGET_DIRECTORIES = {
    "project": "10-项目/",
    "asset_candidate": "20-资产/",
    "resource": "30-资源/",
    "helper": "40-辅助/",
    "inspiration": "50-灵感/",
    "skill_candidate": "60-Skill/",
    "review_required": "01-收件箱/",
}

DISPLAY_TYPES = {
    "project": "项目",
    "asset_candidate": "资产候选",
    "resource": "资源",
    "helper": "辅助",
    "inspiration": "灵感",
    "skill_candidate": "Skill 候选",
    "review_required": "需人工复核",
}


@dataclass(frozen=True)
class Suggestion:
    source: str
    suggested_type: str
    target_dir: str
    confidence: str
    reason: str
    requires_confirmation: bool = True


def is_excluded_path(path: Path) -> bool:
    """Return whether a relative path belongs to a non-legacy scan area."""
    return bool(path.parts) and path.parts[0] in EXCLUDED_TOP_LEVEL


def _score(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _suggest(source: str, kind: str, confidence: str, reason: str) -> Suggestion:
    return Suggestion(
        source=source,
        suggested_type=kind,
        target_dir=TARGET_DIRECTORIES[kind],
        confidence=confidence,
        reason=reason,
    )


def classify_note(path: Path, text: str) -> Suggestion:
    """Classify one legacy note through deterministic filename/content scoring."""
    source = path.as_posix()
    name = path.stem
    corpus = f"{name}\n{text}".lower()

    if "index" in name.lower() or "每日核心沉淀" in name or "日结" in corpus or "知识库总索引" in name:
        return _suggest(source, "review_required", "low", "Index 或日结类页面可能应保留为系统入口，需人工复核")

    active_project_score = _score(name.lower(), ("虎客科技", "玉泉木业", "玉山木业", "客户项目", "项目推进", "进度", "下一步", "待办"))
    if active_project_score >= 2:
        return _suggest(source, "project", "high", "活跃客户/项目与进度或下一步信号明确")

    # Strong filename signals are explicit user-facing labels and take priority
    # over incidental keywords in a note body.
    if any(keyword in name for keyword in ("想法", "机会", "思路")):
        return _suggest(source, "inspiration", "high", "文件名明确标注想法、机会或思路，优先保留为待验证灵感")
    if any(keyword in name for keyword in ("方法论", "评分体系", "工作流", "标准化流程")):
        return _suggest(source, "skill_candidate", "high", "文件名明确标注方法论、评分体系或工作流，作为 Skill 候选")
    if any(keyword in name for keyword in ("终稿", "确认版", "参考报价", "报价", "档案", "发布验收", "交付说明")):
        return _suggest(source, "asset_candidate", "high", "文件名明确标注终稿、确认、报价或交付，作为资产候选")

    scores = {
        "project": _score(corpus, ("虎客科技", "玉泉木业", "玉山木业", "项目", "方案框架", "进度", "下一步", "待办")),
        "asset_candidate": _score(corpus, ("终稿", "确认版", "参考报价", "报价", "交付", "档案", "发布验收")),
        "resource": _score(corpus, ("视频拆解", "报告", "速查", "案例", "数据", "横评", "现状")),
        "helper": _score(corpus, ("提示词", "模板", "清单", "sop", "教程", "说明", "手册", "规则")),
        "inspiration": _score(corpus, ("想法", "机会", "思路")),
        "skill_candidate": _score(corpus, ("方法论", "评分体系", "工作流", "标准化流程")),
    }

    # Priority order turns a tie into a review instead of silently choosing.
    top_score = max(scores.values())
    winners = [kind for kind, score in scores.items() if score == top_score and score > 0]
    if top_score == 0 or len(winners) != 1:
        return _suggest(source, "review_required", "low", "关键词得分不足或并列，避免自动归属")

    kind = winners[0]
    confidence = "high" if top_score >= 2 else "medium"
    labels = {
        "project": "客户/项目、方案或进度关键词得分最高",
        "asset_candidate": "终稿、确认、报价或交付关键词得分最高",
        "resource": "来源型拆解、报告、案例或数据关键词得分最高",
        "helper": "提示词、模板、清单、SOP、教程或说明关键词得分最高",
        "inspiration": "想法、机会或思路关键词得分最高",
        "skill_candidate": "方法论、评分体系或工作流关键词得分最高",
    }
    return _suggest(source, kind, confidence, labels[kind])


def scan_legacy_notes(root: Path) -> list[Suggestion]:
    """Read root-level legacy Markdown files and return sorted suggestions."""
    root = root.resolve()
    suggestions: list[Suggestion] = []
    for path in sorted(root.glob("*.md"), key=lambda item: item.name):
        if path.name == "AGENTS.md":
            continue
        if is_excluded_path(path.relative_to(root)):
            continue
        suggestions.append(classify_note(path.relative_to(root), path.read_text(encoding="utf-8-sig")))
    return suggestions


def _legacy_source_paths(root: Path) -> set[Path]:
    """Return resolved root-level Markdown sources that this audit may read."""
    root = root.resolve()
    return {
        path.resolve()
        for path in root.glob("*.md")
        if path.name != "AGENTS.md" and not is_excluded_path(path.relative_to(root))
    }


def _managed_report_path(root: Path, generated: str) -> Path:
    return (root / "00-系统" / f"现有文档迁移建议-{generated}.md").resolve()


def _is_protected_output(root: Path, output: Path) -> bool:
    try:
        relative = output.relative_to(root)
    except ValueError:
        return False
    return is_excluded_path(relative) or (relative.parts and relative.parts[0] == "00-系统")


def render_report(items: list[Suggestion], generated: str) -> str:
    """Render a deterministic, human-reviewable Markdown migration report."""
    lines = [
        "---",
        "title: 现有文档迁移建议",
        "type: system",
        "status: review_required",
        f"created: {generated}",
        f"updated: {generated}",
        "---",
        "",
        "# 现有文档迁移建议",
        "",
        "> 本报告仅对既有 Markdown 做只读扫描；未移动、重命名、复制或修改任何既有文档。所有建议都须由用户确认后才可执行。",
        "",
        "分类依据为可见的文件名与正文关键词计分：低分或并列结果统一标为“需人工复核”。",
        "",
        "| 当前文件 | 建议主归属 | 建议目标 | 置信度 | 理由 | 是否需确认 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in sorted(items, key=lambda suggestion: suggestion.source):
        confirmation = "是" if item.requires_confirmation else "否"
        lines.append(
            f"| {item.source} | {DISPLAY_TYPES[item.suggested_type]} | {item.target_dir} | "
            f"{item.confidence} | {item.reason} | {confirmation} |"
        )
    lines.extend(
        [
            "",
            "## 统计",
            "",
            f"- 扫描文档数：{len(items)}",
        ]
    )
    for kind in TARGET_DIRECTORIES:
        count = sum(item.suggested_type == kind for item in items)
        if count:
            lines.append(f"- {DISPLAY_TYPES[kind]}：{count}")
    lines.append("")
    return "\n".join(lines)


def suggestion_counts(items: list[Suggestion]) -> Counter[str]:
    """Return suggestion counts for reports without altering source documents."""
    return Counter(item.suggested_type for item in items)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate read-only legacy Markdown migration suggestions.")
    parser.add_argument("root", nargs="?", default=".", type=Path, help="vault root directory")
    parser.add_argument("--output", required=True, type=Path, help="suggestion report path")
    parser.add_argument("--date", required=True, help="report date in YYYY-MM-DD format")
    arguments = parser.parse_args(argv)

    root = arguments.root.resolve()
    output = arguments.output
    if not output.is_absolute():
        output = root / output
    output = output.resolve()
    managed_report = _managed_report_path(root, arguments.date)
    protected = _is_protected_output(root, output)
    allowed_managed_update = output == managed_report
    if output in _legacy_source_paths(root) or (protected and not allowed_managed_update) or (output.exists() and not allowed_managed_update):
        print(
            f"Refusing to overwrite scanned legacy Markdown source: {output}",
            file=sys.stderr,
        )
        return 2

    items = scan_legacy_notes(root)
    output.write_text(render_report(items, arguments.date), encoding="utf-8")
    print(f"Generated {output} with {len(items)} read-only suggestions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
