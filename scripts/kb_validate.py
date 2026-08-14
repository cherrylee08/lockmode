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
VALID_SUGGESTED_TYPES = frozenset(FORMAL_DIRECTORIES.values())
DIGESTION_COMPLETE_STAGES = frozenset({"digested", "connected", "used", "reviewed"})
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


def is_reparse_point(path: Path) -> bool:
    """Return whether *path* is a symlink or Windows reparse point without following it."""
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return path.is_symlink() or bool(getattr(metadata, "st_file_attributes", 0) & 0x0400)


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def is_safe_file(path: Path, allowed_directory: Path) -> bool:
    """Accept only a regular file reached without reparse points inside an allowed root."""
    try:
        resolved_allowed = allowed_directory.resolve(strict=True)
        current = path.absolute()
        lexical_allowed = allowed_directory.absolute()
        while current != lexical_allowed:
            if current == current.parent or not is_within(current, lexical_allowed):
                return False
            if is_reparse_point(current):
                return False
            current = current.parent
        if is_reparse_point(lexical_allowed):
            return False
        resolved_path = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    return resolved_path.is_file() and is_within(resolved_path, resolved_allowed)


def safe_markdown_paths(
    directory: Path,
    *,
    recursive: bool = True,
    skip_hidden: bool = False,
) -> list[Path]:
    """Enumerate Markdown without following reparse points or escaping *directory*."""
    lexical_directory = directory.absolute()
    if is_reparse_point(lexical_directory):
        return []
    try:
        resolved_directory = lexical_directory.resolve(strict=True)
    except (OSError, RuntimeError):
        return []
    if not resolved_directory.is_dir():
        return []

    paths: list[Path] = []

    def visit(current: Path) -> None:
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError:
            return
        for child in children:
            if skip_hidden and child.name.startswith("."):
                continue
            if is_reparse_point(child):
                continue
            try:
                resolved_child = child.resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if not is_within(resolved_child, resolved_directory):
                continue
            if resolved_child.is_dir():
                if recursive:
                    visit(child)
                continue
            if resolved_child.is_file() and child.suffix.lower() == ".md":
                paths.append(child)

    visit(lexical_directory)
    return paths


def _expected_type(path: Path, root: Path) -> str | None:
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return None
    if not relative_parts:
        return None
    return FORMAL_DIRECTORIES.get(relative_parts[0])


def _lifecycle_issues(
    metadata: dict[str, object],
    relative_path: str,
    *,
    require_digestion_completion: bool = False,
) -> list[Issue]:
    issues: list[Issue] = []
    knowledge_stage = metadata.get("knowledge_stage")
    if knowledge_stage not in (None, "") and (
        not isinstance(knowledge_stage, str) or knowledge_stage not in VALID_KNOWLEDGE_STAGES
    ):
        issues.append(Issue("ERROR", relative_path, "INVALID_KNOWLEDGE_STAGE", "knowledge_stage is invalid"))

    for field in ITERATION_LIST_FIELDS:
        if field in metadata and not isinstance(metadata[field], list):
            issues.append(Issue("ERROR", relative_path, "INVALID_LIST_FIELD", f"{field} must be a bracket list"))

    if isinstance(knowledge_stage, str) and knowledge_stage in {"used", "reviewed"}:
        used_in = metadata.get("used_in")
        if not isinstance(used_in, list) or not used_in:
            issues.append(Issue("ERROR", relative_path, "MISSING_USED_IN", "used/reviewed knowledge requires used_in"))

    feedback_status = metadata.get("feedback_status")
    if feedback_status not in (None, "") and (
        not isinstance(feedback_status, str) or feedback_status not in VALID_FEEDBACK_STATUS
    ):
        issues.append(Issue("ERROR", relative_path, "INVALID_FEEDBACK_STATUS", "feedback_status is invalid"))
    if knowledge_stage == "reviewed" and feedback_status != "recorded":
        issues.append(Issue("ERROR", relative_path, "INVALID_FEEDBACK_STATUS", "reviewed knowledge requires recorded feedback"))

    if require_digestion_completion and knowledge_stage in DIGESTION_COMPLETE_STAGES:
        summary = metadata.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            issues.append(Issue("ERROR", relative_path, "MISSING_DIGESTION_SUMMARY", "digested knowledge requires a summary"))

        confidence = metadata.get("confidence")
        if confidence in (None, ""):
            issues.append(Issue("ERROR", relative_path, "MISSING_DIGESTION_CONFIDENCE", "digested knowledge requires confidence"))

        suggested_type = metadata.get("suggested_type")
        if not isinstance(suggested_type, str) or suggested_type not in VALID_SUGGESTED_TYPES:
            issues.append(Issue("ERROR", relative_path, "INVALID_SUGGESTED_TYPE", "digested knowledge requires one valid suggested_type"))

        related = metadata.get("related")
        has_related = isinstance(related, list) and any(
            isinstance(value, str) and value.strip() for value in related
        )
        review_date = metadata.get("review_date")
        has_review_date = isinstance(review_date, str) and bool(review_date.strip())
        if not has_related and not has_review_date:
            issues.append(
                Issue(
                    "ERROR",
                    relative_path,
                    "MISSING_DIGESTION_CONNECTION",
                    "digested knowledge requires related or review_date",
                )
            )
    return issues


def validate_inbox_note(path: Path, root: Path) -> list[Issue]:
    """Validate only the stage-aware contract for one inbox input."""
    metadata = parse_frontmatter(path)
    relative_path = _relative_path(path, root)
    issues: list[Issue] = []

    duplicate_keys = metadata.get("__duplicate_keys__", [])
    if isinstance(duplicate_keys, list):
        for key in duplicate_keys:
            issues.append(Issue("ERROR", relative_path, "DUPLICATE_FRONTMATTER_KEY", f"duplicate frontmatter key: {key}"))

    confidence = metadata.get("confidence")
    if confidence not in (None, "") and (
        not isinstance(confidence, str) or confidence not in VALID_CONFIDENCE
    ):
        issues.append(
            Issue(
                "ERROR",
                relative_path,
                "INVALID_CONFIDENCE",
                "confidence must be confirmed, inferred, or unverified",
            )
        )
    if "related" in metadata and not isinstance(metadata["related"], list):
        issues.append(Issue("ERROR", relative_path, "INVALID_LIST_FIELD", "related must be a bracket list"))
    issues.extend(_lifecycle_issues(metadata, relative_path, require_digestion_completion=True))
    return issues


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
    if confidence not in (None, "") and (
        not isinstance(confidence, str) or confidence not in VALID_CONFIDENCE
    ):
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

    issues.extend(_lifecycle_issues(metadata, relative_path))
    return issues


def _formal_note_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in FORMAL_DIRECTORIES:
        directory_path = root / directory
        for path in safe_markdown_paths(directory_path):
            relative_parts = path.relative_to(root).parts
            if path.name == "Index.md" or (directory == "30-资源" and "raw" in relative_parts):
                continue
            paths.append(path)
    return sorted(paths, key=lambda item: _relative_path(item, root))


def _inbox_note_paths(root: Path) -> list[Path]:
    inbox = root / "01-收件箱"
    return sorted(
        (path for path in safe_markdown_paths(inbox) if path.name != "Index.md"),
        key=lambda item: _relative_path(item, root),
    )


def validate_vault(root: Path) -> list[Issue]:
    """Validate all formal notes in a vault and return deterministically ordered issues."""
    root = root.resolve()
    formal_paths = _formal_note_paths(root)
    issues = [issue for path in formal_paths for issue in validate_note(path, root)]
    issues.extend(issue for path in _inbox_note_paths(root) for issue in validate_inbox_note(path, root))

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
