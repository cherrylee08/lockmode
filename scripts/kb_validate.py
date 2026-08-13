"""Deterministic structural validation for formal six-framework knowledge notes."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COMMON_FIELDS = (
    "id",
    "title",
    "type",
    "status",
    "created",
    "updated",
    "owner",
    "confidence",
    "source_refs",
    "related",
    "review_date",
)
VALID_CONFIDENCE = frozenset({"confirmed", "inferred", "unverified"})
VALID_KNOWLEDGE_STAGES = frozenset(
    {"captured", "triaged", "digested", "connected", "used", "reviewed"}
)
VALID_FEEDBACK_STATUS = frozenset({"not_applicable", "pending", "recorded"})
FORMAL_DIRECTORIES = {
    "10-项目": "project",
    "20-资产": "asset",
    "30-资源": "resource",
    "40-辅助": "helper",
    "50-灵感": "inspiration",
    "60-Skill": "skill",
}
LIST_FIELDS = ("source_refs", "related")
ITERATION_LIST_FIELDS = ("used_in",)


@dataclass(frozen=True)
class Issue:
    level: str
    path: str
    code: str
    message: str


def _parse_value(value: str) -> object:
    """Parse the deliberately small frontmatter value subset used by templates."""
    value = value.strip()
    if not value or value in {"null", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        contents = value[1:-1].strip()
        if not contents:
            return []
        return next(csv.reader([contents], skipinitialspace=True))
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> dict[str, object]:
    """Return frontmatter from *path*, or an empty mapping when it is absent."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        return {}

    metadata: dict[str, object] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key and key in metadata:
            duplicates = metadata.setdefault("__duplicate_keys__", [])
            if isinstance(duplicates, list):
                duplicates.append(key)
        if key:
            metadata[key] = _parse_value(value)
    return metadata


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _expected_type(path: Path, root: Path) -> str | None:
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return None
    if not relative_parts:
        return None
    return FORMAL_DIRECTORIES.get(relative_parts[0])


def validate_note(path: Path, root: Path) -> list[Issue]:
    """Validate one formal note; callers are responsible for directory exclusion."""
    metadata = parse_frontmatter(path)
    relative_path = _relative_path(path, root)
    issues: list[Issue] = []

    duplicate_keys = metadata.get("__duplicate_keys__", [])
    if isinstance(duplicate_keys, list):
        for key in duplicate_keys:
            issues.append(Issue("ERROR", relative_path, "DUPLICATE_FRONTMATTER_KEY", f"duplicate frontmatter key: {key}"))

    for field in REQUIRED_COMMON_FIELDS:
        if field not in metadata or metadata[field] is None or metadata[field] == "":
            issues.append(
                Issue("ERROR", relative_path, "MISSING_REQUIRED_FIELD", f"missing required field: {field}")
            )

    expected_type = _expected_type(path, root)
    note_type = metadata.get("type")
    if expected_type and note_type != expected_type:
        issues.append(
            Issue(
                "ERROR",
                relative_path,
                "INVALID_TYPE",
                f"type must be {expected_type} for this directory",
            )
        )

    confidence = metadata.get("confidence")
    if confidence is not None and confidence != "" and confidence not in VALID_CONFIDENCE:
        issues.append(
            Issue(
                "ERROR",
                relative_path,
                "INVALID_CONFIDENCE",
                "confidence must be confirmed, inferred, or unverified",
            )
        )
    for field in LIST_FIELDS:
        if field in metadata and not isinstance(metadata[field], list):
            issues.append(Issue("ERROR", relative_path, "INVALID_LIST_FIELD", f"{field} must be a bracket list"))

    knowledge_stage = metadata.get("knowledge_stage")
    if knowledge_stage not in (None, "") and knowledge_stage not in VALID_KNOWLEDGE_STAGES:
        issues.append(Issue("ERROR", relative_path, "INVALID_KNOWLEDGE_STAGE", "knowledge_stage is invalid"))

    for field in ITERATION_LIST_FIELDS:
        if field in metadata and not isinstance(metadata[field], list):
            issues.append(Issue("ERROR", relative_path, "INVALID_LIST_FIELD", f"{field} must be a bracket list"))

    if knowledge_stage in {"used", "reviewed"}:
        used_in = metadata.get("used_in")
        if not isinstance(used_in, list) or not used_in:
            issues.append(Issue("ERROR", relative_path, "MISSING_USED_IN", "used/reviewed knowledge requires used_in"))

    feedback_status = metadata.get("feedback_status")
    if feedback_status not in (None, "") and feedback_status not in VALID_FEEDBACK_STATUS:
        issues.append(Issue("ERROR", relative_path, "INVALID_FEEDBACK_STATUS", "feedback_status is invalid"))
    if knowledge_stage == "reviewed" and feedback_status != "recorded":
        issues.append(Issue("ERROR", relative_path, "INVALID_FEEDBACK_STATUS", "reviewed knowledge requires recorded feedback"))
    return issues


def _formal_note_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in FORMAL_DIRECTORIES:
        directory_path = root / directory
        if not directory_path.is_dir():
            continue
        for path in directory_path.rglob("*.md"):
            relative_parts = path.relative_to(root).parts
            if path.name == "Index.md" or (directory == "30-资源" and "raw" in relative_parts):
                continue
            paths.append(path)
    return sorted(paths, key=lambda item: _relative_path(item, root))


def validate_vault(root: Path) -> list[Issue]:
    """Validate all formal notes in a vault and return deterministically ordered issues."""
    root = root.resolve()
    formal_paths = _formal_note_paths(root)
    issues = [issue for path in formal_paths for issue in validate_note(path, root)]

    id_paths: dict[str, list[Path]] = defaultdict(list)
    for path in formal_paths:
        note_id = parse_frontmatter(path).get("id")
        if isinstance(note_id, str) and note_id:
            id_paths[note_id].append(path)

    for note_id in sorted(id_paths):
        paths = id_paths[note_id]
        if len(paths) < 2:
            continue
        for path in paths:
            issues.append(
                Issue(
                    "ERROR",
                    _relative_path(path, root),
                    "DUPLICATE_ID",
                    f"duplicate id: {note_id}",
                )
            )
    return sorted(issues, key=lambda issue: (issue.path, issue.level, issue.code, issue.message))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate formal six-framework knowledge notes.")
    parser.add_argument("root", nargs="?", default=".", type=Path, help="vault root directory")
    arguments = parser.parse_args(argv)

    root = arguments.root.resolve()
    issues: list[Issue] = []
    if not root.is_dir():
        issues.append(Issue("ERROR", ".", "INVALID_VAULT_ROOT", "vault root does not exist or is not a directory"))
    else:
        for directory in FORMAL_DIRECTORIES:
            if not (root / directory).is_dir():
                issues.append(Issue("ERROR", directory, "MISSING_FRAMEWORK_DIRECTORY", f"missing framework directory: {directory}"))
        issues.extend(validate_vault(root))
    issues = sorted(issues, key=lambda issue: (issue.path, issue.level, issue.code, issue.message))
    for issue in issues:
        print(f"{issue.level}\t{issue.code}\t{issue.path}\t{issue.message}")
    return 1 if any(issue.level == "ERROR" for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
