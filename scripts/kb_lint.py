"""Semantic linting for the Obsidian knowledge vault: topology, staleness, broken links.

Checks:
- Orphaned formal notes (no incoming or outgoing links)
- Broken wiki links ([[...]] pointing to non-existent files)
- Expired review_date (formal notes past their review date)
- Confirmed conclusions without source references
- Missing derived_from for asset/skill notes

Output format: LEVEL<TAB>CODE<TAB>PATH<TAB>MESSAGE (same as kb_validate.py)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


FORMAL_DIRECTORIES = {
    "10-项目",
    "20-资产",
    "30-资源",
    "40-辅助",
    "50-灵感",
    "60-Skill",
}
SYSTEM_DIRECTORIES = {
    "00-系统",
    "Templates",
    "scripts",
    "docs",
}
EXCLUDE_NAMES = {"Index.md", "index.md", "README.md", "log.md", "AGENTS.md"}
LINK_PATTERN = re.compile(r'\[\[(.*?)(?:\|.*?)?\]\]')


def _parse_value(value: str) -> object:
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
        if key:
            metadata[key] = _parse_value(value)
    return metadata


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def extract_links(text: str) -> list[str]:
    """Extract [[...]] link targets, stripping aliases."""
    return LINK_PATTERN.findall(text)


def _is_formal_note(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    return parts[0] in FORMAL_DIRECTORIES if parts else False


def _is_system_or_special(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return True
    return False


def _find_file_for_link(link_name: str, all_files: dict[str, Path], root: Path) -> Path | None:
    lower_link = link_name.lower()
    # 1. Exact path match: e.g. "01-收件箱/Index" -> "01-收件箱/Index.md"
    for fname, fpath in all_files.items():
        rel_path = f"{_relative_path(fpath, root)}".lower().replace(".md", "")
        if rel_path == lower_link:
            return fpath
    # 2. Stem match anywhere (for bare links like "Index")
    for fname, fpath in all_files.items():
        if fpath.stem.lower() == lower_link:
            return fpath
        if fname.lower() == lower_link + ".md":
            return fpath
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Semantic lint for knowledge vault.")
    parser.add_argument("root", nargs="?", default=".", type=Path, help="vault root directory")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"ERROR\tINVALID_VAULT_ROOT\t.\tvault root does not exist or is not a directory")
        return 1

    # Collect all markdown files (key = relative path for uniqueness)
    all_files: dict[str, Path] = {}  # relative_path -> path
    for path in root.rglob("*.md"):
        rel = _relative_path(path, root)
        # Skip raw/ directory (original sources, read-only)
        if "/raw/" in rel or rel.startswith("raw/"):
            continue
        all_files[rel] = path

    # Parse every file: frontmatter + links
    file_data: dict[str, dict] = {}  # rel_path -> {frontmatter, links, is_formal}
    outgoing: dict[str, set[str]] = defaultdict(set)  # rel_path -> set of linked rel_paths
    incoming: dict[str, set[str]] = defaultdict(set)  # rel_path -> set of linker rel_paths
    broken_links: list[tuple[str, str]] = []  # (from_rel, link_name)

    today = datetime.now(timezone.utc).date()

    for fname, fpath in all_files.items():
        rel = _relative_path(fpath, root)
        if _is_system_or_special(fpath):
            continue

        text = fpath.read_text(encoding="utf-8-sig")
        fm = parse_frontmatter(fpath)
        links = extract_links(text)

        is_formal = _is_formal_note(fpath, root)
        file_data[rel] = {"frontmatter": fm, "links": links, "is_formal": is_formal}

        for link_name in links:
            target = _find_file_for_link(link_name, all_files, root)
            if target is None:
                # Skip template placeholders (files inside Templates/)
                if rel.startswith("Templates/"):
                    continue
                broken_links.append((rel, link_name))
            else:
                target_rel = _relative_path(target, root)
                outgoing[rel].add(target_rel)
                incoming[target_rel].add(rel)

    issues: list[tuple[str, str, str, str]] = []  # (level, code, path, message)

    # 1. Orphaned formal notes (no incoming links, or very few links)
    for rel, data in file_data.items():
        if not data["is_formal"]:
            continue
        # Skip Index files within formal directories
        if Path(rel).name == "Index.md":
            continue
        inc = incoming.get(rel, set())
        out = outgoing.get(rel, set())
        # Total links (in + out) <= 1 is considered orphaned
        total_links = len(inc) + len(out)
        if total_links == 0:
            issues.append(("WARNING", "ORPHANED_NOTE", rel, "no incoming or outgoing links"))
        elif total_links <= 1:
            issues.append(("WARNING", "WEAKLY_LINKED", rel, f"only {total_links} link(s) total (in+out)"))

    # 2. Broken links
    seen_broken = set()
    for from_rel, link_name in broken_links:
        key = (from_rel, link_name)
        if key in seen_broken:
            continue
        seen_broken.add(key)
        issues.append(("WARNING", "BROKEN_LINK", from_rel, f"link target not found: [[{link_name}]]"))

    # 3. Expired review_date
    for rel, data in file_data.items():
        if not data["is_formal"]:
            continue
        fm = data["frontmatter"]
        review_date = fm.get("review_date")
        if review_date and isinstance(review_date, str):
            try:
                rd = datetime.strptime(review_date, "%Y-%m-%d").date()
                if rd < today:
                    days_overdue = (today - rd).days
                    issues.append(("WARNING", "EXPIRED_REVIEW", rel, f"review_date expired by {days_overdue} days ({review_date})"))
            except ValueError:
                issues.append(("ERROR", "INVALID_REVIEW_DATE", rel, f"review_date format invalid: {review_date}"))

    # 4. Confirmed notes without source references
    for rel, data in file_data.items():
        if not data["is_formal"]:
            continue
        fm = data["frontmatter"]
        confidence = fm.get("confidence")
        source_refs = fm.get("source_refs", [])
        if confidence == "confirmed" and (not source_refs or (isinstance(source_refs, list) and len(source_refs) == 0)):
            # Allow if it has derived_from
            derived_from = fm.get("derived_from", [])
            if not derived_from or (isinstance(derived_from, list) and len(derived_from) == 0):
                issues.append(("WARNING", "CONFIRMED_NO_SOURCE", rel, "confidence=confirmed but no source_refs or derived_from"))

    # 5. Asset/Skill notes without derived_from
    for rel, data in file_data.items():
        if not data["is_formal"]:
            continue
        fm = data["frontmatter"]
        note_type = fm.get("type")
        if note_type in ("asset", "skill"):
            derived_from = fm.get("derived_from", [])
            if not derived_from or (isinstance(derived_from, list) and len(derived_from) == 0):
                issues.append(("WARNING", "MISSING_DERIVED_FROM", rel, f"type={note_type} but derived_from is empty"))

    # 6. Missing type frontmatter on formal notes
    for rel, data in file_data.items():
        if not data["is_formal"]:
            continue
        fm = data["frontmatter"]
        if not fm.get("type"):
            issues.append(("ERROR", "MISSING_TYPE", rel, "formal note missing type in frontmatter"))

    # Output sorted
    issues.sort(key=lambda item: (item[2], item[0], item[1], item[3]))
    for level, code, path, message in issues:
        print(f"{level}\t{code}\t{path}\t{message}")

    return 1 if any(level == "ERROR" for level, _, _, _ in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
