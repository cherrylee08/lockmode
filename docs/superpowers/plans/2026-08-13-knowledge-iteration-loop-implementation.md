# Knowledge Iteration Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有六框架 Obsidian 知识库中实现可持续运行的“输入—消化—业务输出—内容派生—反馈回写”双循环，并保持用户确认和 raw 只读边界。

**Architecture:** Markdown/YAML 继续作为唯一数据源。新增输入生命周期字段、Web Clipper 模板、日清/周复盘辅助模板，以及一个仅使用 Python 标准库的确定性驾驶舱生成器；生成器读取收件箱和六框架元数据，更新受管系统页面，不移动文件、不晋升资产或 Skill。

**Tech Stack:** Obsidian Markdown、受限 YAML frontmatter、Obsidian Web Clipper JSON template schema `0.1.0`、Python 3 标准库、`unittest`、现有 `scripts/kb_validate.py`。

## Global Constraints

- 每天 10 分钟，最多处理 3 条输入。
- 每周 30 分钟，只承诺一个业务关键输出和一个业务派生内容选题。
- 普通 Clipper 输入进入 `01-收件箱`；只有用户配置并认可的可信来源模板才能进入 `30-资源/raw`。
- `30-资源/raw` 只读；任何脚本不得覆盖或改写其中的文件。
- 正式笔记只能有一个 `type`，并明确区分 `confirmed`、`inferred`、`unverified`。
- 移动旧文件、改变唯一主归属、晋升资产、综合页或 Skill 必须由用户确认。
- 不自动发布内容，不执行客户承诺、报价定稿、合同签署或重大业务判断。
- 不引入第三方 Python 依赖，不建设独立后台或向量数据库。
- 保留工作区其他未提交改动；每个提交只暂存本任务明确文件。

---

## File Structure

```text
00-系统/
  知识迭代驾驶舱.md                 # 受管输出：今日 Top 3、本周输出、健康与待确认
  知识库操作手册.md                 # 输入、消化、输出和反馈闭环运行规则
  元数据规范.md                     # 生命周期与指标字段词汇表
  健康报告.md                       # 增加闭环指标和不可计算说明
  知识库首页.md                     # 驾驶舱入口
  index.md                          # 驾驶舱和配置入口
  log.md                            # 只追加实施记录
01-收件箱/
  Index.md                          # Top 3、积压阈值和完成标准
10-项目/
  个人知识库管理系统.md             # 项目进度和下一步
40-辅助/
  Index.md                          # 日清、周复盘和 Clipper 配置入口
  每日Top3消化清单.md               # 每日 10 分钟人工流程
  每周30分钟知识复盘.md             # 每周固定四项产物
  Obsidian Web Clipper配置说明.md   # 导入、Vault 选择、可信模板边界
Templates/
  收件箱输入模板.md                 # captured 输入模板
  每周知识复盘模板.md               # 周复盘记录模板
  Web Clipper-默认收件箱.json       # 官方 Clipper 可导入 JSON
  Web Clipper-可信来源raw示例.json   # 不含具体可信域名的示例，禁止自动触发
scripts/
  kb_dashboard.py                   # 只读采集、指标计算、确定性 Markdown 渲染
  kb_validate.py                    # 生命周期字段的枚举与组合约束
tests/
  test_kb_dashboard.py              # 驾驶舱采集、排序、渲染和写入保护
  test_kb_validate.py               # 新字段验证回归
```

---

### Task 1: 生命周期字段、输入模板与结构校验

**Files:**
- Modify: `00-系统/元数据规范.md`
- Modify: `00-系统/知识库操作手册.md`
- Modify: `01-收件箱/Index.md`
- Create: `Templates/收件箱输入模板.md`
- Create: `Templates/每周知识复盘模板.md`
- Modify: `scripts/kb_validate.py`
- Modify: `tests/test_kb_validate.py`
- Modify: `00-系统/log.md`

**Interfaces:**
- Consumes: existing `parse_frontmatter(path: Path) -> dict[str, object]` and `validate_note(path: Path, root: Path) -> list[Issue]`.
- Produces: `VALID_KNOWLEDGE_STAGES`, conditional lifecycle validation, and templates consumed by Task 2 and Task 3.

- [ ] **Step 1: Add failing lifecycle validation tests**

Append exact tests to `tests/test_kb_validate.py`:

```python
    def test_invalid_knowledge_stage_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(
                root,
                "10-项目/x.md",
                COMMON_FIELDS + "knowledge_stage: unknown\n",
            )
            issues = validate_vault(root)
        self.assertTrue(any(issue.code == "INVALID_KNOWLEDGE_STAGE" for issue in issues))

    def test_used_stage_requires_used_in_and_feedback_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(
                root,
                "20-资产/x.md",
                COMMON_FIELDS.replace("type: project", "type: asset")
                + "knowledge_stage: used\nused_in: []\nfeedback_status: pending\n",
            )
            issues = validate_vault(root)
        codes = {issue.code for issue in issues}
        self.assertIn("MISSING_USED_IN", codes)

    def test_reviewed_stage_requires_completed_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_note(
                root,
                "20-资产/x.md",
                COMMON_FIELDS.replace("type: project", "type: asset")
                + "knowledge_stage: reviewed\nused_in: [KB-PROJECT-1]\nfeedback_status: pending\n",
            )
            issues = validate_vault(root)
        self.assertTrue(any(issue.code == "INVALID_FEEDBACK_STATUS" for issue in issues))
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest tests.test_kb_validate -v
```

Expected: at least the new lifecycle tests fail because the validator does not inspect `knowledge_stage`, `used_in`, or `feedback_status`.

- [ ] **Step 3: Implement the optional lifecycle contract**

Add to `scripts/kb_validate.py`:

```python
VALID_KNOWLEDGE_STAGES = frozenset(
    {"captured", "triaged", "digested", "connected", "used", "reviewed"}
)
VALID_FEEDBACK_STATUS = frozenset({"not_applicable", "pending", "recorded"})
ITERATION_LIST_FIELDS = ("used_in",)
```

Inside `validate_note`, after the existing list-field loop, add:

```python
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
```

The new fields remain optional for existing formal notes. Once present, their values and combinations are enforced.

- [ ] **Step 4: Create the two Markdown templates**

Create `Templates/收件箱输入模板.md` with incomplete inbox-safe metadata:

```markdown
---
title: {{title}}
captured_at: {{date:YYYY-MM-DD}} {{time:HH:mm}}
capture_channel: manual
knowledge_stage: captured
source_url:
source_title:
source_site:
summary:
confidence: unverified
suggested_type:
related: []
review_date:
---

# {{title}}

## 原始输入

## 一句话结论

## 五个判断

- 是否值得保留：
- 内容性质：事实 / 观点 / 方法 / 想法
- 可信度：unverified
- 建议主归属：
- 下一步：
```

Create `Templates/每周知识复盘模板.md`:

```markdown
---
title: 每周知识复盘 {{date:GGGG-[W]WW}}
week: {{date:GGGG-[W]WW}}
created: {{date:YYYY-MM-DD}}
updated: {{date:YYYY-MM-DD}}
---

# 每周知识复盘 {{date:GGGG-[W]WW}}

## 本周项目变化

## 下周唯一业务输出

- 服务项目：
- 解决问题：
- 验收标准：

## 业务派生内容

- 题目：
- 来源项目：
- 脱敏检查：未完成

## 反馈回写

## 资产 / 综合页 / Skill 候选
```

- [ ] **Step 5: Document the state machine and daily completion rule**

Update `00-系统/元数据规范.md` with exact optional fields:

```yaml
knowledge_stage: [captured, triaged, digested, connected, used, reviewed]
feedback_status: [not_applicable, pending, recorded]
iteration_fields: [captured_at, capture_channel, summary, used_in, feedback_status, last_used, use_count]
```

Update `00-系统/知识库操作手册.md` and `01-收件箱/Index.md` with:

- daily maximum of 3 inputs;
- the five digestion questions;
- minimum completion standard;
- inbox threshold 30;
- stage definitions and archive rule.

- [ ] **Step 6: Run validation tests and live validation**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest tests.test_kb_validate -v
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B scripts/kb_validate.py 'E:\李大谱的小脑瓜'
```

Expected: all validator tests pass; live validator exits `0` with no output.

- [ ] **Step 7: Append log and commit Task 1**

Append to `00-系统/log.md`:

```markdown
## [2026-08-13] system | 知识迭代生命周期建立

- 建立 captured 到 reviewed 的输入生命周期与组合校验。
- 新增收件箱输入和每周复盘模板。
- 每天最多消化 3 条，收件箱超过 30 条触发积压提醒。
```

Commit only Task 1 files:

```powershell
git add -- '00-系统/元数据规范.md' '00-系统/知识库操作手册.md' '01-收件箱/Index.md' 'Templates/收件箱输入模板.md' 'Templates/每周知识复盘模板.md' scripts/kb_validate.py tests/test_kb_validate.py '00-系统/log.md'
git commit -m "feat: add knowledge iteration lifecycle"
```

---

### Task 2: 确定性知识迭代驾驶舱

**Files:**
- Create: `scripts/kb_dashboard.py`
- Create: `tests/test_kb_dashboard.py`
- Create: `00-系统/知识迭代驾驶舱.md`
- Modify: `00-系统/知识库首页.md`
- Modify: `00-系统/index.md`
- Modify: `00-系统/健康报告.md`
- Modify: `00-系统/log.md`

**Interfaces:**
- Consumes: `parse_frontmatter(path: Path)` from `scripts.kb_validate`, inbox Markdown, formal project metadata, and `00-系统/待确认队列.md`.
- Produces:

```python
@dataclass(frozen=True)
class DashboardData:
    inbox_count: int
    top_three: tuple[str, ...]
    overdue_reviews: tuple[str, ...]
    active_projects_without_next_action: tuple[str, ...]
    pending_confirmations: int
    weekly_business_output: str | None
    weekly_content_derivative: str | None

def collect_dashboard(root: Path, today: date) -> DashboardData: ...
def render_dashboard(data: DashboardData, generated: str) -> str: ...
def write_dashboard(root: Path, output: Path, generated: str) -> None: ...
def check_dashboard(root: Path, output: Path, generated: str) -> bool: ...
def main(argv: list[str] | None = None) -> int: ...
```

- [ ] **Step 1: Write failing dashboard tests**

Create `tests/test_kb_dashboard.py` with fixtures that assert:

```python
def test_top_three_prioritizes_project_link_then_oldest_capture(): ...
def test_collects_overdue_reviews_and_projects_without_next_action(): ...
def test_counts_only_waiting_pending_queue_rows(): ...
def test_render_marks_unavailable_metrics_instead_of_inventing_values(): ...
def test_write_refuses_raw_formal_and_existing_non_managed_targets(): ...
def test_write_allows_only_exact_managed_dashboard_path(): ...
def test_check_compares_in_memory_without_writing_files(): ...
```

Use a temporary vault containing:

- four inbox notes with `captured_at`, `related`, `summary`, and `knowledge_stage`;
- one active project with an empty `next_action`;
- one note whose `review_date` is before `today`;
- a pending queue with one `待确认` and one `已完成` row.

Expected Top 3: notes linked to an active project first, then remaining notes by oldest `captured_at`; the fourth note is omitted.

- [ ] **Step 2: Run dashboard tests and confirm RED**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest tests.test_kb_dashboard -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.kb_dashboard'`.

- [ ] **Step 3: Implement read-only collection and deterministic rendering**

Implement `scripts/kb_dashboard.py` using only `argparse`, `dataclasses`, `datetime`, and `pathlib` plus `parse_frontmatter`.

Exact selection key for inbox notes:

```python
def inbox_priority(item: InboxItem) -> tuple[int, str, str]:
    return (0 if item.related else 1, item.captured_at or "9999-12-31", item.path)
```

The renderer must include these headings in this order:

```markdown
# 知识迭代驾驶舱

## 今日 Top 3
## 本周唯一业务输出
## 本周业务派生内容
## 待确认
## 活跃项目异常
## 到期复查
## 六项运行指标
## 运行命令
```

For metrics not derivable from current files, render `暂不可计算：缺少本周复盘记录` rather than `0`.

`write_dashboard` must resolve paths before writing. It may overwrite only `root / "00-系统" / "知识迭代驾驶舱.md"`; it must reject any path under `30-资源/raw`, any formal framework directory, any existing non-managed file, and any path outside `root`.

`check_dashboard` must render the expected content in memory and compare it with the exact managed dashboard path. CLI `--check` returns `0` for an exact match and `1` for drift; it must not create, overwrite, or delete any file.

- [ ] **Step 4: Generate the live dashboard**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B scripts/kb_dashboard.py 'E:\李大谱的小脑瓜' --output '00-系统/知识迭代驾驶舱.md' --date 2026-08-13
```

Expected: dashboard exists; inbox count is `0`; Top 3 states `当前无待消化输入`; weekly output metrics state that no weekly review exists instead of inventing a result.

- [ ] **Step 5: Link the dashboard and update health reporting**

Add `[[00-系统/知识迭代驾驶舱|知识迭代驾驶舱]]` to `00-系统/知识库首页.md` and `00-系统/index.md` exactly once.

Extend `00-系统/健康报告.md` with a `知识迭代闭环` section containing:

- inbox count and threshold status;
- overdue review count;
- active projects without next action;
- pending confirmation count;
- all six metrics, explicitly using `暂不可计算` where weekly evidence does not exist.

- [ ] **Step 6: Run dashboard and full test suites**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest tests.test_kb_dashboard -v
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest discover -s tests -v
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B scripts/kb_validate.py 'E:\李大谱的小脑瓜'
git diff --check
```

Expected: all tests pass; live validator exits `0`; diff check has no output.

- [ ] **Step 7: Append log and commit Task 2**

Append:

```markdown
## [2026-08-13] dashboard | 知识迭代驾驶舱建立

- 汇总今日 Top 3、本周输出、待确认、项目异常和到期复查。
- 无证据的运行指标明确标记为暂不可计算，不生成虚假数值。
- 驾驶舱生成器只允许更新唯一受管系统页。
```

Commit only Task 2 files with:

```powershell
git add -- scripts/kb_dashboard.py tests/test_kb_dashboard.py '00-系统/知识迭代驾驶舱.md' '00-系统/知识库首页.md' '00-系统/index.md' '00-系统/健康报告.md' '00-系统/log.md'
git commit -m "feat: add knowledge iteration dashboard"
```

---

### Task 3: Web Clipper 配置与日/周执行辅助

**Files:**
- Create: `Templates/Web Clipper-默认收件箱.json`
- Create: `Templates/Web Clipper-可信来源raw示例.json`
- Create: `40-辅助/每日Top3消化清单.md`
- Create: `40-辅助/每周30分钟知识复盘.md`
- Create: `40-辅助/Obsidian Web Clipper配置说明.md`
- Modify: `40-辅助/Index.md`
- Modify: `01-收件箱/Index.md`
- Modify: `00-系统/知识库操作手册.md`
- Modify: `00-系统/log.md`
- Test: PowerShell JSON parse plus live vault validation.

**Interfaces:**
- Consumes: lifecycle vocabulary from Task 1 and dashboard expectations from Task 2.
- Produces: two importable Clipper JSON templates and three formal helper notes.

- [ ] **Step 1: Create the default inbox Clipper JSON**

Create `Templates/Web Clipper-默认收件箱.json` with the official template structure:

```json
{
  "schemaVersion": "0.1.0",
  "name": "李大谱知识库 - 默认收件箱",
  "behavior": "create",
  "noteNameFormat": "{{date|date:\"YYYY-MM-DD\"}} {{title|safe_name}}",
  "path": "01-收件箱",
  "context": "{{content}}",
  "properties": [
    {"name": "captured_at", "value": "{{date|date:\"YYYY-MM-DD\"}} {{time}}", "type": "text"},
    {"name": "capture_channel", "value": "web_clipper", "type": "text"},
    {"name": "knowledge_stage", "value": "captured", "type": "text"},
    {"name": "source_url", "value": "{{url}}", "type": "text"},
    {"name": "source_title", "value": "{{title}}", "type": "text"},
    {"name": "source_site", "value": "{{site}}", "type": "text"},
    {"name": "confidence", "value": "unverified", "type": "text"}
  ],
  "triggers": [],
  "noteContentFormat": "# {{title}}\n\n> 来源：[{{title}}]({{url}}) · 抓取于 {{date|date:\"YYYY-MM-DD\"}}\n\n## 原始内容\n\n{{content}}\n\n## 一句话结论\n\n## 五个判断\n\n- 是否值得保留：\n- 内容性质：事实 / 观点 / 方法 / 想法\n- 可信度：unverified\n- 建议主归属：\n- 下一步："
}
```

`triggers` is empty so this template is manually chosen and cannot silently capture every site.

- [ ] **Step 2: Create the trusted-source raw example JSON**

Create `Templates/Web Clipper-可信来源raw示例.json` with:

- `schemaVersion: 0.1.0`;
- `behavior: create`;
- `path: 30-资源/raw`;
- title, URL, site, published date, captured date and unmodified `{{content}}`;
- `triggers: []` with a visible `_setup_warning` property: `导入后必须由用户填写可信域名触发器；未填写前只可手动选择`.

Do not invent or pre-approve any trusted domain. The configuration guide must say that adding each domain is a user approval action.

- [ ] **Step 3: Validate both JSON files**

Run:

```powershell
Get-Content -Raw -LiteralPath 'Templates/Web Clipper-默认收件箱.json' | ConvertFrom-Json | Out-Null
Get-Content -Raw -LiteralPath 'Templates/Web Clipper-可信来源raw示例.json' | ConvertFrom-Json | Out-Null
```

Expected: both commands exit `0` with no output.

- [ ] **Step 4: Create three formal helper notes**

Each helper note must use a unique `KB-HELPER-20260813-NNN` ID, `type: helper`, `status: active`, `confidence: confirmed`, bracket lists for `source_refs` and `related`, and `review_date: 2026-09-13`.

`40-辅助/每日Top3消化清单.md` must contain a timed checklist:

```markdown
## 0-2 分钟：选择 Top 3
## 2-8 分钟：逐条完成五个判断
## 8-10 分钟：建立连接并更新状态
## 完成标准
```

`40-辅助/每周30分钟知识复盘.md` must contain:

```markdown
## 0-8 分钟：项目变化
## 8-15 分钟：唯一业务输出与验收
## 15-22 分钟：业务派生内容与脱敏
## 22-27 分钟：反馈回写
## 27-30 分钟：候选与系统健康
```

`40-辅助/Obsidian Web Clipper配置说明.md` must document:

1. import the two JSON files through Web Clipper Templates;
2. select the local vault `E:\李大谱的小脑瓜`;
3. keep default captures in `01-收件箱`;
4. require user approval before adding a trusted-domain trigger;
5. never edit or overwrite raw captures;
6. test each template on one non-sensitive public page;
7. verify the created Markdown path and frontmatter before normal use.

- [ ] **Step 5: Link helper notes and document commands**

Add the three helper links to `40-辅助/Index.md`. Add the default Clipper template link to `01-收件箱/Index.md`. Add exact user commands to `00-系统/知识库操作手册.md`:

1. `执行今日 Top 3 消化。`
2. `记录本周唯一业务输出：……，验收标准：……。`
3. `从本周业务过程派生一个内容选题。`
4. `将这次使用结果回写到项目和相关知识。`
5. `刷新知识迭代驾驶舱。`

- [ ] **Step 6: Validate helpers and whole vault**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B scripts/kb_validate.py 'E:\李大谱的小脑瓜'
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest discover -s tests -v
git diff --check
```

Expected: validator exits `0`; all tests pass; diff check has no output.

- [ ] **Step 7: Append log and commit Task 3**

Append:

```markdown
## [2026-08-13] helper | Clipper 与日周双循环辅助建立

- 新增默认收件箱和可信来源 raw 示例模板，未预设任何可信域名。
- 新增每日 Top 3 和每周 30 分钟复盘辅助页。
- raw 抓取保持只读，可信来源触发器仍需用户逐项批准。
```

Commit only Task 3 files:

```powershell
git add -- 'Templates/Web Clipper-默认收件箱.json' 'Templates/Web Clipper-可信来源raw示例.json' '40-辅助/每日Top3消化清单.md' '40-辅助/每周30分钟知识复盘.md' '40-辅助/Obsidian Web Clipper配置说明.md' '40-辅助/Index.md' '01-收件箱/Index.md' '00-系统/知识库操作手册.md' '00-系统/log.md'
git commit -m "feat: add clipper and iteration playbooks"
```

---

### Task 4: 整库集成、指标基线与验收

**Files:**
- Modify: `00-系统/知识迭代驾驶舱.md`
- Modify: `00-系统/健康报告.md`
- Modify: `10-项目/个人知识库管理系统.md`
- Modify: `00-系统/log.md`
- Create: `docs/superpowers/specs/2026-08-13-knowledge-iteration-loop-acceptance.md`

**Interfaces:**
- Consumes: all Task 1-3 templates, validators and generator commands.
- Produces: a reproducible live baseline and handoff-ready acceptance record.

- [ ] **Step 1: Run the complete automated suite**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest discover -s tests -v
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B scripts/kb_validate.py 'E:\李大谱的小脑瓜'
```

Expected: all tests pass; validator exits `0` without issues.

- [ ] **Step 2: Check the managed dashboard without writing a temporary file**

Run the read-only in-memory comparison:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B scripts/kb_dashboard.py 'E:\李大谱的小脑瓜' --check --date 2026-08-13
```

Expected: exit `0` with `dashboard is current`; no file is created, overwritten, or deleted. If content has drifted, exit `1` with `dashboard is stale`.

- [ ] **Step 3: Verify safety and scope**

Run:

```powershell
git diff --check
git status --short
git diff --name-status HEAD
```

Expected:

- no file under `30-资源/raw` is modified, deleted or renamed;
- no existing formal note changes `type`;
- no asset, synthesis, or Skill promotion occurs;
- only Task 4 files plus pre-existing unrelated work are uncommitted.

- [ ] **Step 4: Write the acceptance record**

Create `docs/superpowers/specs/2026-08-13-knowledge-iteration-loop-acceptance.md` with this exact evidence table:

```markdown
| 验收项 | 证据 | 结果 |
| --- | --- | --- |
| 普通 Clipper 默认进入收件箱 | JSON path 与导入验证 | 通过/不通过 |
| 可信 raw 示例无预设域名 | triggers 为空 | 通过/不通过 |
| raw 不被生成器覆盖 | 写入保护测试 | 通过/不通过 |
| 已消化输入最低标准 | 模板与字段校验 | 通过/不通过 |
| 驾驶舱可确定性重现 | `--check` 内存比较 | 通过/不通过 |
| 无证据指标不造数 | 驾驶舱文本 | 通过/不通过 |
| 用户确认边界有效 | 代码、手册与待确认队列 | 通过/不通过 |
```

Record actual test counts, validator exit code, dashboard comparison result, and current known limitations.

- [ ] **Step 5: Update the project and operational record**

Update `10-项目/个人知识库管理系统.md`:

- mark the dual-loop system implementation complete;
- set `next_action` to `导入并测试默认 Web Clipper 收件箱模板，完成首个真实输入闭环`;
- add the dashboard, daily checklist, weekly review and Clipper guide under outputs;
- retain open work for legacy migration and asset provenance.

Update the dashboard and health report with the verified baseline. Append:

```markdown
## [2026-08-13] verify | 知识迭代闭环验收

- 完成输入、消化、业务输出、内容派生和反馈回写的双循环验收。
- 驾驶舱可由当前知识库确定性重现，未知指标未生成虚假数值。
- 下一步是导入默认 Clipper 模板并完成第一个真实输入闭环。
```

- [ ] **Step 6: Final verification and commit Task 4**

Run the full test suite, live validator and `git diff --check` again. Commit only:

```powershell
git add -- '00-系统/知识迭代驾驶舱.md' '00-系统/健康报告.md' '10-项目/个人知识库管理系统.md' '00-系统/log.md' 'docs/superpowers/specs/2026-08-13-knowledge-iteration-loop-acceptance.md'
git commit -m "docs: verify knowledge iteration loop"
```

---

## Final Delivery Checks

- [ ] All unit tests pass under Python `-B` with no `__pycache__` residue.
- [ ] Live `kb_validate.py` exits `0`.
- [ ] Both Web Clipper templates parse as JSON.
- [ ] The managed dashboard exactly matches a fresh deterministic render.
- [ ] No raw source was changed.
- [ ] No unapproved move, type change, asset/synthesis promotion, or Skill promotion occurred.
- [ ] Other user worktree changes remain untouched and unstaged.
- [ ] Every changed formal knowledge page is linked from an Index and recorded in `00-系统/log.md`.
