"""Deterministically render the managed knowledge-iteration dashboard."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

if __package__:
    from scripts.kb_validate import is_reparse_point, is_safe_file, is_within, parse_frontmatter, safe_markdown_paths
else:
    from kb_validate import is_reparse_point, is_safe_file, is_within, parse_frontmatter, safe_markdown_paths


FORMAL_DIRECTORIES = (
    "10-项目",
    "20-资产",
    "30-资源",
    "40-辅助",
    "50-灵感",
    "60-Skill",
)
MANAGED_DASHBOARD = Path("00-系统") / "知识迭代驾驶舱.md"
WEEKLY_REVIEW_DIRECTORY = Path("00-系统") / "每周复盘"
UNAVAILABLE_METRIC = "暂不可计算：缺少本周复盘记录"
PENDING_INBOX_STAGES = frozenset({"captured", "triaged"})


@dataclass(frozen=True)
class DashboardData:
    inbox_count: int
    top_three: tuple[str, ...]
    overdue_reviews: tuple[str, ...]
    active_projects_without_next_action: tuple[str, ...]
    pending_confirmations: int
    weekly_business_output: str | None
    weekly_content_derivative: str | None


@dataclass(frozen=True)
class InboxItem:
    path: str
    captured_at: str
    related: bool
    display: str


@dataclass(frozen=True)
class ActiveProjectTargets:
    qualified: frozenset[str]
    unique_basenames: frozenset[str]


def _display_name(path: Path, metadata: dict[str, object], root: Path) -> str:
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return path.relative_to(root).with_suffix("").as_posix()


def inbox_priority(item: InboxItem) -> tuple[int, str, str]:
    return (0 if item.related else 1, item.captured_at or "9999-12-31", item.path)


def _active_project_paths(root: Path) -> ActiveProjectTargets:
    projects = root / "10-项目"
    if not projects.is_dir():
        return ActiveProjectTargets(frozenset(), frozenset())
    active_paths: list[Path] = []
    for path in safe_markdown_paths(projects):
        if path.name == "Index.md" or parse_frontmatter(path).get("status") != "active":
            continue
        active_paths.append(path)

    basename_counts = Counter(path.stem.casefold() for path in safe_markdown_paths(root, skip_hidden=True))
    qualified = frozenset(
        path.relative_to(root).with_suffix("").as_posix().casefold()
        for path in active_paths
    )
    unique_basenames = frozenset(
        path.stem.casefold()
        for path in active_paths
        if basename_counts[path.stem.casefold()] == 1
    )
    return ActiveProjectTargets(qualified, unique_basenames)


def _links_to_active_project(related: object, active_project_paths: ActiveProjectTargets) -> bool:
    if not isinstance(related, list):
        return False
    for value in related:
        if not isinstance(value, str) or not (value.startswith("[[") and value.endswith("]]")):
            continue
        target = value[2:-2].split("|", 1)[0].split("#", 1)[0].strip().replace("\\", "/")
        if target.casefold().endswith(".md"):
            target = target[:-3]
        normalized = target.strip("/").casefold()
        if "/" in normalized and normalized in active_project_paths.qualified:
            return True
        if "/" not in normalized and normalized in active_project_paths.unique_basenames:
            return True
    return False


def _inbox_items(root: Path, active_project_paths: ActiveProjectTargets) -> list[InboxItem]:
    inbox = root / "01-收件箱"
    if not inbox.is_dir():
        return []
    items: list[InboxItem] = []
    for path in safe_markdown_paths(inbox):
        if path.name == "Index.md":
            continue
        metadata = parse_frontmatter(path)
        knowledge_stage = metadata.get("knowledge_stage")
        if knowledge_stage not in (None, "") and knowledge_stage not in PENDING_INBOX_STAGES:
            continue
        captured_at = metadata.get("captured_at")
        related = metadata.get("related")
        summary = metadata.get("summary")
        display = summary.strip() if isinstance(summary, str) and summary.strip() else _display_name(path, metadata, root)
        items.append(
            InboxItem(
                path=path.relative_to(root).as_posix(),
                captured_at=captured_at.strip() if isinstance(captured_at, str) else "",
                related=_links_to_active_project(related, active_project_paths),
                display=display,
            )
        )
    return items


def _formal_note_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in FORMAL_DIRECTORIES:
        directory_path = root / directory
        for path in safe_markdown_paths(directory_path):
            relative = path.relative_to(root)
            if path.name == "Index.md" or (directory == "30-资源" and "raw" in relative.parts):
                continue
            paths.append(path)
    return sorted(paths, key=lambda item: item.relative_to(root).as_posix())


def _overdue_reviews(root: Path, today: date) -> tuple[str, ...]:
    overdue: list[tuple[str, str]] = []
    today_text = today.isoformat()
    for path in _formal_note_paths(root):
        metadata = parse_frontmatter(path)
        review_date = metadata.get("review_date")
        if isinstance(review_date, str) and review_date.strip() and review_date.strip() < today_text:
            overdue.append((_display_name(path, metadata, root), path.relative_to(root).as_posix()))
    return tuple(name for name, _ in sorted(overdue, key=lambda item: (item[0], item[1])))


def _active_projects_without_next_action(root: Path) -> tuple[str, ...]:
    projects = root / "10-项目"
    if not projects.is_dir():
        return ()
    missing: list[tuple[str, str]] = []
    for path in safe_markdown_paths(projects):
        if path.name == "Index.md":
            continue
        metadata = parse_frontmatter(path)
        next_action = metadata.get("next_action")
        if metadata.get("status") == "active" and (not isinstance(next_action, str) or not next_action.strip()):
            missing.append((_display_name(path, metadata, root), path.relative_to(root).as_posix()))
    return tuple(name for name, _ in sorted(missing, key=lambda item: (item[0], item[1])))


def _pending_confirmations(root: Path) -> int:
    queue = root / "00-系统" / "待确认队列.md"
    if not is_safe_file(queue, root):
        return 0
    header: list[str] | None = None
    status_index: int | None = None
    count = 0
    for line in queue.read_text(encoding="utf-8-sig").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            status_index = header.index("状态") if "状态" in header else None
            continue
        if all(cell and set(cell) <= {"-", ":"} for cell in cells):
            continue
        if status_index is not None and status_index < len(cells) and cells[status_index] == "待确认":
            count += 1
    return count


def _current_week(today: date) -> str:
    iso_week = today.isocalendar()
    return f"{iso_week.year}-W{iso_week.week:02d}"


def _review_section(text: str, heading: str) -> tuple[str, ...]:
    lines = text.splitlines()
    start = next((index + 1 for index, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return ()
    end = next((index for index, line in enumerate(lines[start:], start=start) if line.startswith("## ")), len(lines))
    return tuple(lines[start:end])


def _filled_review_value(lines: tuple[str, ...], label: str) -> str | None:
    for line in lines:
        stripped = line.strip()
        for prefix in (f"- {label}：", f"- {label}:"):
            if not stripped.startswith(prefix):
                continue
            value = stripped[len(prefix):].strip()
            if value and value not in {"未填写", "待填写", "无"} and "{{" not in value:
                return value
    return None


def _weekly_review_outputs(root: Path, today: date) -> tuple[str | None, str | None]:
    expected_week = _current_week(today)
    candidates: list[Path] = []
    review_directory = root / WEEKLY_REVIEW_DIRECTORY
    if not review_directory.is_dir():
        return None, None
    for path in safe_markdown_paths(review_directory, recursive=False):
        if path == root / MANAGED_DASHBOARD:
            continue
        if parse_frontmatter(path).get("week") == expected_week:
            candidates.append(path)
    if not candidates:
        return None, None

    review = min(candidates, key=lambda item: item.relative_to(root).as_posix())
    text = review.read_text(encoding="utf-8-sig")
    business_section = _review_section(text, "## 下周唯一业务输出")
    content_section = _review_section(text, "## 业务派生内容")
    service_project = _filled_review_value(business_section, "服务项目")
    problem = _filled_review_value(business_section, "解决问题")
    acceptance = _filled_review_value(business_section, "验收标准")
    title = _filled_review_value(content_section, "题目")
    source_project = _filled_review_value(content_section, "来源项目")
    business = (
        f"服务项目：{service_project}；解决问题：{problem}；验收标准：{acceptance}"
        if service_project and problem and acceptance
        else None
    )
    derivative = f"题目：{title}；来源项目：{source_project}" if title and source_project else None
    return business, derivative


def collect_dashboard(root: Path, today: date) -> DashboardData:
    """Collect deterministic, read-only dashboard data from a vault."""
    root = root.resolve()
    inbox_items = _inbox_items(root, _active_project_paths(root))
    ordered_inbox = sorted(inbox_items, key=inbox_priority)
    weekly_business_output, weekly_content_derivative = _weekly_review_outputs(root, today)
    return DashboardData(
        inbox_count=len(inbox_items),
        top_three=tuple(item.display for item in ordered_inbox[:3]),
        overdue_reviews=_overdue_reviews(root, today),
        active_projects_without_next_action=_active_projects_without_next_action(root),
        pending_confirmations=_pending_confirmations(root),
        weekly_business_output=weekly_business_output,
        weekly_content_derivative=weekly_content_derivative,
    )


def _bullet_list(items: tuple[str, ...], empty_message: str) -> list[str]:
    return [f"- {item}" for item in items] if items else [f"- {empty_message}"]


def render_dashboard(data: DashboardData, generated: str) -> str:
    """Render dashboard data into the single managed system-page format."""
    backlog_status = "正常（不超过 30 条）" if data.inbox_count <= 30 else "积压提醒（超过 30 条）"
    lines = [
        "---",
        "title: 知识迭代驾驶舱",
        "type: system",
        "status: active",
        "created: 2026-08-13",
        f"updated: {generated}",
        "---",
        "",
        "# 知识迭代驾驶舱",
        "",
        f"生成日期：{generated}",
        "",
        "## 今日 Top 3",
        "",
        *_bullet_list(data.top_three, "当前无待消化输入"),
        "",
        "## 本周唯一业务输出",
        "",
        f"- {data.weekly_business_output or '暂无本周复盘记录'}",
        "",
        "## 本周业务派生内容",
        "",
        f"- {data.weekly_content_derivative or '暂无本周复盘记录'}",
        "",
        "## 待确认",
        "",
        f"- 待确认事项：{data.pending_confirmations} 项",
        "",
        "## 活跃项目异常",
        "",
        *_bullet_list(data.active_projects_without_next_action, "无活跃项目缺少下一步"),
        "",
        "## 到期复查",
        "",
        *_bullet_list(data.overdue_reviews, "无到期复查"),
        "",
        "## 六项运行指标",
        "",
        f"1. 输入积压：{data.inbox_count} 条；{backlog_status}",
        f"2. 消化完成率：{UNAVAILABLE_METRIC}",
        f"3. 项目连接率：{UNAVAILABLE_METRIC}",
        f"4. 业务输出兑现：{UNAVAILABLE_METRIC}",
        f"5. 知识复用次数：{UNAVAILABLE_METRIC}",
        f"6. 反馈回写率：{UNAVAILABLE_METRIC}",
        "",
        "## 运行命令",
        "",
        "```powershell",
        "& 'C:\\Users\\lee\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' -B scripts/kb_dashboard.py . --output '00-系统/知识迭代驾驶舱.md' --date 2026-08-13",
        "```",
        "",
    ]
    return "\n".join(lines)


def _managed_output_path(root: Path, output: Path) -> Path | None:
    lexical_root = root.absolute()
    candidate = (lexical_root / output).absolute() if not output.is_absolute() else output.absolute()
    managed = (lexical_root / MANAGED_DASHBOARD).absolute()
    if candidate != managed or not lexical_root.is_dir():
        return None

    managed_parent = managed.parent
    if is_reparse_point(managed_parent) or is_reparse_point(managed):
        return None

    resolved_root = lexical_root.resolve()
    resolved_parent = managed_parent.resolve()
    expected_parent = resolved_root / MANAGED_DASHBOARD.parent
    resolved_managed = managed.resolve()
    if (
        resolved_parent != expected_parent
        or resolved_managed.parent != resolved_parent
        or not is_within(resolved_managed, resolved_root)
    ):
        return None
    return managed


def write_dashboard(root: Path, output: Path, generated: str) -> None:
    """Write only the exact, managed dashboard path; reject every other target."""
    lexical_root = root.absolute()
    managed_output = _managed_output_path(lexical_root, output)
    if managed_output is None:
        raise ValueError("dashboard output must be the managed 00-系统/知识迭代驾驶舱.md page")
    managed_output.parent.mkdir(parents=True, exist_ok=True)
    managed_output.write_text(render_dashboard(collect_dashboard(lexical_root, date.fromisoformat(generated)), generated), encoding="utf-8")


def check_dashboard(root: Path, output: Path, generated: str) -> bool:
    """Compare the expected managed page in memory without modifying the vault."""
    lexical_root = root.absolute()
    managed_output = _managed_output_path(lexical_root, output)
    if managed_output is None or not managed_output.is_file():
        return False
    expected = render_dashboard(collect_dashboard(lexical_root, date.fromisoformat(generated)), generated)
    return managed_output.read_text(encoding="utf-8-sig") == expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or check the managed knowledge iteration dashboard.")
    parser.add_argument("root", nargs="?", default=".", type=Path, help="vault root directory")
    parser.add_argument("--output", default=MANAGED_DASHBOARD, type=Path, help="managed dashboard output path")
    parser.add_argument("--date", dest="generated", default=date.today().isoformat(), help="generation date in YYYY-MM-DD format")
    parser.add_argument("--check", action="store_true", help="compare expected content without writing")
    arguments = parser.parse_args(argv)
    try:
        date.fromisoformat(arguments.generated)
    except ValueError:
        parser.error("--date must use YYYY-MM-DD")

    if arguments.check:
        if check_dashboard(arguments.root, arguments.output, arguments.generated):
            print("dashboard is current")
            return 0
        print("dashboard is stale")
        return 1

    try:
        write_dashboard(arguments.root, arguments.output, arguments.generated)
    except ValueError as error:
        parser.error(str(error))
    print("dashboard updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
