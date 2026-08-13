# 六框架 LLM Wiki 知识库管理系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or execute this plan inline task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不移动现有文档的前提下，把当前 Obsidian 仓库搭建成“项目、资产、资源、辅助、灵感、Skill”六框架知识管理系统，并具备索引、日志、待确认队列、模板、校验和迁移映射能力。

**Architecture:** 以 Markdown/YAML 作为唯一数据源，Obsidian 作为第一阶段界面；`AGENTS.md` 与 `00-系统/知识库操作手册.md` 约束 AI 行为，六框架目录承载正式 Wiki，`30-资源/raw` 保存不可修改的原始来源。Python 标准库脚本只做确定性结构校验和只读迁移分析，不自动移动或晋升任何旧文件。

**Tech Stack:** Obsidian Markdown、YAML frontmatter、Obsidian wikilinks、Git、Python 3 标准库、`unittest`。

## Global Constraints

- 每篇正式笔记只有一个主框架；跨框架关系用 YAML 与 `[[双向链接]]` 表达。
- 原始来源不可由 AI 覆盖修改。
- AI 可新建、补字段、更新索引和链接；移动旧文件、改变主归属、晋升资产或 Skill 必须由用户确认。
- 第一阶段不开发 Web 后台、不引入向量数据库、不批量移动现有文件。
- 保留工作区中所有既有未提交修改；每次只暂存任务明确列出的文件。
- 所有新增 Markdown 使用 UTF-8，文件名和用户可见内容使用中文；机器枚举值使用稳定英文值。
- 不把聊天流水、缓存、依赖、密钥、账号令牌或运行日志导入正式知识层。
- 测试使用工作区依赖中的 Python：`C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`。

## 文件结构与职责

```text
AGENTS.md                                      # Agent 进入仓库时的强制操作边界
00-系统/
  知识库首页.md                                # 用户主入口
  知识库操作手册.md                            # 六类边界与操作流程
  index.md                                     # 全局内容目录
  log.md                                       # 只追加操作记录
  待确认队列.md                                # 移动/归属/晋升审批
  健康报告.md                                  # 最近一次巡检结果
  元数据规范.md                                # 字段与枚举
01-收件箱/Index.md                             # 双入口中的未分类入口
10-项目/Index.md                               # 项目聚合
20-资产/Index.md                               # 资产聚合
30-资源/Index.md                               # 资源聚合
30-资源/raw/README.md                          # 原始来源不可改规则
40-辅助/Index.md                               # 辅助聚合
50-灵感/Index.md                               # 灵感聚合
60-Skill/Index.md                              # Skill 聚合
90-归档/Index.md                               # 归档入口
Templates/项目模板.md                          # 六类专用模板
Templates/资产模板.md
Templates/资源模板.md
Templates/辅助模板.md
Templates/灵感模板.md
Templates/Skill模板.md
scripts/kb_validate.py                         # 确定性结构与 frontmatter 校验
scripts/kb_migration_audit.py                  # 只读扫描并生成归属建议
tests/test_kb_validate.py                      # 校验器单元测试
tests/test_kb_migration_audit.py               # 映射器单元测试
00-系统/现有文档迁移建议-2026-08-13.md          # 首轮迁移映射报告
```

---

### Task 1: 建立系统骨架、治理规则与导航入口

**Files:**
- Create: `AGENTS.md`
- Create: `00-系统/知识库首页.md`
- Create: `00-系统/知识库操作手册.md`
- Create: `00-系统/元数据规范.md`
- Create: `00-系统/index.md`
- Create: `00-系统/log.md`
- Create: `00-系统/待确认队列.md`
- Create: `00-系统/健康报告.md`
- Create: `01-收件箱/Index.md`
- Create: `10-项目/Index.md`
- Create: `20-资产/Index.md`
- Create: `30-资源/Index.md`
- Create: `30-资源/raw/README.md`
- Create: `40-辅助/Index.md`
- Create: `50-灵感/Index.md`
- Create: `60-Skill/Index.md`
- Create: `90-归档/Index.md`

**Interfaces:**
- Consumes: approved design in `docs/superpowers/specs/2026-08-13-llm-wiki-six-frameworks-design.md`.
- Produces: stable directory names, type enums, status enums and navigation links consumed by templates and scripts.

- [ ] **Step 1: Create directories without moving existing files**

Run:

```powershell
$paths = @(
  '00-系统','01-收件箱','10-项目','20-资产','30-资源','30-资源/raw',
  '40-辅助','50-灵感','60-Skill','90-归档','scripts','tests'
)
$paths | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
```

Expected: all paths exist; existing root Markdown files remain in place.

- [ ] **Step 2: Create repository Agent rules**

Create `AGENTS.md` with these enforceable rules:

```markdown
# 知识库 Agent 操作规则

## 先读入口
1. 先读 [[00-系统/知识库首页]] 和 [[00-系统/知识库操作手册]]。
2. 查询先读 `00-系统/index.md`，再读对应框架的 `Index.md`。

## 权限边界
- 可自动：新建笔记、补元数据、更新索引/日志、建立链接、生成建议和健康报告。
- 必须确认：移动旧文件、改变唯一主归属、晋升资产、晋升 Skill。
- 原始来源 `30-资源/raw/` 只读，不覆盖、不改写。

## 内容边界
- 每篇正式笔记只能有一个 `type`。
- `confirmed`、`inferred`、`unverified` 必须明确区分。
- 不保存聊天流水、缓存、依赖、密钥、令牌或未验证敏感信息。
- 变更正式知识后更新相应 Index 和 `00-系统/log.md`。

## 六类枚举
- `project` 项目
- `asset` 资产
- `resource` 资源
- `helper` 辅助
- `inspiration` 灵感
- `skill` Skill
```

- [ ] **Step 3: Create the system manual and metadata contract**

`00-系统/知识库操作手册.md` must contain the exact approved definitions, the common knowledge chain, AI/user permission split, ingest/query/write-back/promote/lint workflows, weekly/monthly cadence, and the seven user commands from the design.

The manual uses the exact operation labels `摄取`、`查询与回写`、`资产候选`、`Skill 候选`、`每周轻巡检` and `每月深巡检`, so later agents and the future backend can locate these contracts deterministically.

`00-系统/元数据规范.md` must define:

```yaml
required_common:
  - id
  - title
  - type
  - status
  - created
  - updated
  - owner
  - confidence
  - source_refs
  - related
  - review_date
types: [project, asset, resource, helper, inspiration, skill]
confidence: [confirmed, inferred, unverified]
project_status: [planning, active, waiting, blocked, completed, paused, archived]
inspiration_status: [captured, validating, in_project, adopted, rejected]
skill_status: [draft, validating, stable, deprecated]
```

The note must explain that YAML is illustrative machine-readable vocabulary, while each Markdown page still uses normal frontmatter.

- [ ] **Step 4: Create homepage, global infrastructure and framework indexes**

`00-系统/知识库首页.md` links to inbox, all six framework Indexes, archive, global index, log, pending approvals, health report, metadata spec and the legacy `[[知识库总索引]]` during migration.

Each framework `Index.md` must include:

```markdown
---
title: <框架名> Index
type: system
status: active
created: 2026-08-13
updated: 2026-08-13
---

# <框架名> Index

## 定义
<approved one-sentence definition>

## 当前内容

## 待处理

---
相关：[[00-系统/知识库首页]]
```

`00-系统/log.md` starts with the parseable entry:

```markdown
## [2026-08-13] system | 六框架 LLM Wiki 骨架建立

- 建立系统、收件箱、六框架和归档入口。
- 未移动任何既有文档。
```

`00-系统/待确认队列.md` contains an empty table with columns: `编号 | 动作 | 当前文件 | 建议目标 | 理由 | 风险/影响 | 用户决定 | 状态`.

`00-系统/健康报告.md` states that the first report will be populated by Task 4 and must not claim the vault is healthy before validation.

`30-资源/raw/README.md` explicitly says the directory is append-only for original sources and that corrections belong in resource notes, not by modifying originals.

- [ ] **Step 5: Verify navigation and untouched legacy files**

Run:

```powershell
$required = @(
  'AGENTS.md','00-系统/知识库首页.md','00-系统/index.md','00-系统/log.md',
  '01-收件箱/Index.md','10-项目/Index.md','20-资产/Index.md','30-资源/Index.md',
  '40-辅助/Index.md','50-灵感/Index.md','60-Skill/Index.md','90-归档/Index.md'
)
$missing = $required | Where-Object { -not (Test-Path -LiteralPath $_) }
if ($missing) { throw "Missing: $($missing -join ', ')" }
git status --short
```

Expected: no missing files; pre-existing modified/untracked files are still present and unchanged.

- [ ] **Step 6: Commit only Task 1 files**

```powershell
git add -- AGENTS.md '00-系统' '01-收件箱' '10-项目' '20-资产' '30-资源' '40-辅助' '50-灵感' '60-Skill' '90-归档'
git commit -m "feat: scaffold six-framework knowledge system"
```

Expected: commit contains only governance, navigation and directory skeleton files.

---

### Task 2: 建立六类模板与晋升标准

**Files:**
- Create: `Templates/项目模板.md`
- Create: `Templates/资产模板.md`
- Create: `Templates/资源模板.md`
- Create: `Templates/辅助模板.md`
- Create: `Templates/灵感模板.md`
- Create: `Templates/Skill模板.md`
- Modify: `00-系统/知识库首页.md`
- Modify: `00-系统/log.md`

**Interfaces:**
- Consumes: common fields and enums defined in Task 1.
- Produces: six deterministic note shapes validated by Task 3.

- [ ] **Step 1: Create the project template**

Use this frontmatter and sections:

```markdown
---
id: KB-{{date:YYYYMMDD}}-{{time:HHmmss}}
title: {{title}}
type: project
status: planning
created: {{date:YYYY-MM-DD}}
updated: {{date:YYYY-MM-DD}}
owner: 李大谱
confidence: confirmed
source_refs: []
related: []
review_date: {{date+7d:YYYY-MM-DD}}
goal: ""
next_action: ""
deadline:
---
# {{title}}
## 一句话目标
## 成功标准
## 当前状态
## 下一步
## 决策记录
## 产出与候选资产
## 方法与候选 Skill
## 来源与关联
```

- [ ] **Step 2: Create asset, resource and helper templates**

Required unique fields and sections:

- Asset: `asset_type`, `version`, `approved_by`, `derived_from`; sections `用途、当前确认版、复用说明、版本记录、来源项目`.
- Resource: `source_type`, `source_url`, `author`, `published`; sections `来源信息、内容摘要、关键事实、可用价值、与现有知识的关系、待核实`.
- Helper: `helper_type`, `applies_to`, `version`; sections `适用场景、使用方法、正文、注意事项、版本记录`.

All three reuse the common fields verbatim and default to `confidence: unverified` only for resource; asset and helper default to `confirmed`.

- [ ] **Step 3: Create inspiration and Skill templates**

Inspiration adds `hypothesis`, `decision`, `project_ref`, defaults to `status: captured`, and contains `快速记录、为什么值得关注、验证方法、决策记录、关联项目`.

Skill adds `skill_status`, `trigger`, `inputs_outputs`, `validation`, defaults to `status: active`, `skill_status: draft`, and contains `何时使用、适用边界、输入、步骤、输出、验收标准、失败处理、验证记录、来源`.

- [ ] **Step 4: Link templates and log the change**

Add a `## 新建笔记` section to `00-系统/知识库首页.md` linking all six templates. Append:

```markdown
## [2026-08-13] system | 六类模板建立

- 建立项目、资产、资源、辅助、灵感和 Skill 模板。
- 模板采用唯一主归属和统一可信度字段。
```

- [ ] **Step 5: Verify template type uniqueness**

Run:

```powershell
$templates = Get-ChildItem -LiteralPath Templates -Filter '*模板.md'
foreach ($file in $templates) {
  $types = Select-String -LiteralPath $file.FullName -Pattern '^type:\s+' | ForEach-Object Line
  if ($types.Count -ne 1) { throw "$($file.Name) has $($types.Count) type fields" }
}
```

Expected: every six-framework template has exactly one `type` field.

- [ ] **Step 6: Commit only template-related files**

```powershell
git add -- 'Templates/项目模板.md' 'Templates/资产模板.md' 'Templates/资源模板.md' 'Templates/辅助模板.md' 'Templates/灵感模板.md' 'Templates/Skill模板.md' '00-系统/知识库首页.md' '00-系统/log.md'
git commit -m "feat: add six-framework note templates"
```

---

### Task 3: 建立确定性校验器与测试

**Files:**
- Create: `scripts/kb_validate.py`
- Create: `tests/test_kb_validate.py`
- Modify: `00-系统/知识库操作手册.md`
- Modify: `00-系统/log.md`

**Interfaces:**
- Consumes: formal directory names, required common fields and enums from Task 1.
- Produces: `validate_vault(root: Path) -> list[Issue]`, CLI exit code `0` when no errors and `1` when errors exist.

- [ ] **Step 1: Write failing validator tests**

Create `tests/test_kb_validate.py` using `tempfile.TemporaryDirectory` and `unittest`. Tests must cover:

```python
def test_valid_formal_note_has_no_errors(): ...
def test_missing_required_field_is_error(): ...
def test_invalid_type_is_error(): ...
def test_duplicate_id_is_error(): ...
def test_inbox_note_may_have_incomplete_frontmatter(): ...
def test_raw_source_is_not_parsed_as_formal_note(): ...
```

Fixtures write minimal UTF-8 Markdown files. The valid fixture contains all eleven common fields; the duplicate test writes the same `id` into `10-项目/a.md` and `20-资产/b.md`.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_kb_validate -v
```

Expected: FAIL because `scripts.kb_validate` does not exist.

- [ ] **Step 3: Implement the validator with Python standard library only**

`scripts/kb_validate.py` must define:

```python
@dataclass(frozen=True)
class Issue:
    level: str
    path: str
    code: str
    message: str

def parse_frontmatter(path: Path) -> dict[str, object]: ...
def validate_note(path: Path, root: Path) -> list[Issue]: ...
def validate_vault(root: Path) -> list[Issue]: ...
def main(argv: list[str] | None = None) -> int: ...
```

Implementation rules:

- Parse the limited YAML subset used by templates: scalar strings, blank/null scalars and bracket lists; do not add PyYAML.
- Only validate Markdown under `10-项目`, `20-资产`, `30-资源` excluding `raw`, `40-辅助`, `50-灵感`, and `60-Skill`.
- Exclude each framework `Index.md` because it is system navigation.
- Require the eleven common fields.
- Validate `type` against the directory's expected type.
- Validate `confidence` against `confirmed|inferred|unverified`.
- Detect duplicate non-template IDs across formal notes.
- Emit stable tab-separated CLI lines: `LEVEL<TAB>CODE<TAB>PATH<TAB>MESSAGE`.
- Return exit code 1 only when at least one `ERROR` exists; warnings do not fail.

- [ ] **Step 4: Run tests and the live-vault validator**

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_kb_validate -v
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/kb_validate.py .
```

Expected: all unit tests PASS; live vault returns 0 because newly created framework directories contain only Index pages and templates are outside formal directories.

- [ ] **Step 5: Document validation command and log it**

Add the exact live validation command to `00-系统/知识库操作手册.md`. Append to log:

```markdown
## [2026-08-13] lint | 基础结构校验器建立

- 校验正式笔记的必填字段、主归属、可信度和重复 ID。
- 收件箱、原始来源和框架 Index 不作为正式笔记校验。
```

- [ ] **Step 6: Commit validator task**

```powershell
git add -- scripts/kb_validate.py tests/test_kb_validate.py '00-系统/知识库操作手册.md' '00-系统/log.md'
git commit -m "feat: add knowledge-base structure validator"
```

---

### Task 4: 生成只读迁移映射与首轮健康报告

**Files:**
- Create: `scripts/kb_migration_audit.py`
- Create: `tests/test_kb_migration_audit.py`
- Create: `00-系统/现有文档迁移建议-2026-08-13.md`
- Modify: `00-系统/待确认队列.md`
- Modify: `00-系统/健康报告.md`
- Modify: `00-系统/index.md`
- Modify: `00-系统/log.md`
- Modify: `00-系统/知识库首页.md`

**Interfaces:**
- Consumes: root-level legacy Markdown files and the six destination types.
- Produces: `classify_note(path: Path, text: str) -> Suggestion` and a deterministic Markdown report; never moves or edits scanned legacy files.

- [ ] **Step 1: Write failing migration-audit tests**

Tests must cover these representative classifications:

```python
CASES = {
    "虎客科技技术客服 AI 副驾方案框架.md": "project",
    "企业AI服务体系与参考报价.md": "asset_candidate",
    "视频拆解-RAG向量库实战.md": "resource",
    "系统化提示词-经营驾驶舱.md": "helper",
    "想法库.md": "inspiration",
    "小淀镇企业调研方法论与评分体系.md": "skill_candidate",
}
```

Also test that paths inside new framework directories, `.obsidian`, `.git`, `docs`, `.superpowers`, `Templates`, `scripts` and `tests` are excluded.

- [ ] **Step 2: Run tests and confirm failure**

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_kb_migration_audit -v
```

Expected: FAIL because the migration audit module does not exist.

- [ ] **Step 3: Implement read-only classification**

`scripts/kb_migration_audit.py` defines:

```python
@dataclass(frozen=True)
class Suggestion:
    source: str
    suggested_type: str
    target_dir: str
    confidence: str
    reason: str
    requires_confirmation: bool = True

def classify_note(path: Path, text: str) -> Suggestion: ...
def scan_legacy_notes(root: Path) -> list[Suggestion]: ...
def render_report(items: list[Suggestion], generated: str) -> str: ...
def main(argv: list[str] | None = None) -> int: ...
```

Classification is transparent filename/content keyword scoring, not an opaque claim of correctness. Priority rules:

1. `Index` and daily settlement notes stay `review_required` because they may become system indexes rather than business pages.
2. Active customer/project names plus progress/next-step terms → `project`.
3. `终稿|确认版|报价|档案|交付` → `asset_candidate`.
4. `视频拆解|报告|速查|案例|数据` with source-oriented language → `resource`.
5. `提示词|模板|清单|SOP|教程|说明` → `helper`.
6. `想法|机会|思路` without active-project signals → `inspiration`.
7. `方法论|评分体系|工作流` → `skill_candidate`.
8. Ties and weak scores → `review_required`.

The report columns are: `当前文件 | 建议主归属 | 建议目标 | 置信度 | 理由 | 是否需确认`. It must state at the top that no files were moved.

- [ ] **Step 4: Run tests and generate the real report**

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_kb_migration_audit -v
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/kb_migration_audit.py . --output '00-系统/现有文档迁移建议-2026-08-13.md' --date 2026-08-13
```

Expected: tests PASS; report exists; `git status --short` shows no legacy file deletion or rename.

- [ ] **Step 5: Populate pending approvals and health report**

Add only high-confidence asset/Skill candidates to `00-系统/待确认队列.md`; use status `待确认`, leave user decision blank, and do not move them.

`00-系统/健康报告.md` records counts for:

- root-level legacy Markdown files;
- inbox notes;
- formal framework notes;
- migration suggestions by type;
- high-confidence asset candidates;
- high-confidence Skill candidates;
- validator errors and warnings;
- known migration risks: existing uncommitted edits, root-level mixed classifications, old Index links.

- [ ] **Step 6: Update index, homepage and log**

Link the migration report and health report from `00-系统/index.md` and homepage. Append:

```markdown
## [2026-08-13] lint | 首轮现有文档映射

- 只读扫描现有 Markdown，生成主归属建议和资产/Skill 候选。
- 未移动、重命名或复制任何既有文档。
- 高置信度晋升候选已进入待确认队列。
```

- [ ] **Step 7: Full verification**

Run:

```powershell
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -v
& 'C:\Users\lee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/kb_validate.py .
git diff --check
git status --short
```

Expected:

- all tests PASS;
- validator has no `ERROR`;
- `git diff --check` has no output;
- no legacy path is deleted or renamed;
- only Task 4 files plus pre-existing unrelated work are uncommitted.

- [ ] **Step 8: Commit Task 4 only**

```powershell
git add -- scripts/kb_migration_audit.py tests/test_kb_migration_audit.py '00-系统/现有文档迁移建议-2026-08-13.md' '00-系统/待确认队列.md' '00-系统/健康报告.md' '00-系统/index.md' '00-系统/log.md' '00-系统/知识库首页.md'
git commit -m "feat: add migration audit and health report"
```

---

## 最终交付检查

- [ ] `00-系统/知识库首页.md` 可进入收件箱、六框架、归档、系统页和原有总索引。
- [ ] 六个模板各有且仅有一个 `type`。
- [ ] `log.md` 使用可解析日期与操作前缀。
- [ ] 待确认队列包含建议但没有未经批准的已执行动作。
- [ ] 原始来源目录有明确不可改规则。
- [ ] 单元测试全部通过。
- [ ] 正式笔记结构校验无错误。
- [ ] 迁移报告明确声明未移动文件。
- [ ] Git 历史按四个独立任务提交。
- [ ] 现有未提交业务工作没有被覆盖或误提交。
- [ ] 第一阶段只交付 Obsidian/Markdown 管理系统；第二阶段可视化后台仍为预留范围，没有提前引入应用代码或新数据源。
