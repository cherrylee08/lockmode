---
id: KB-HELPER-20260813-003
title: Obsidian Web Clipper 配置说明
type: helper
status: active
created: 2026-08-13
updated: 2026-08-13
owner: 李大谱
confidence: confirmed
source_refs: ["[[00-系统/知识库操作手册]]", "[[00-系统/元数据规范]]"]
related: ["[[01-收件箱/Index]]", "[[40-辅助/每日Top3消化清单]]"]
review_date: 2026-09-13
helper_type: setup_guide
applies_to: ["Templates/Web Clipper-默认收件箱.json", "Templates/Web Clipper-可信来源raw示例.json"]
version: "v1.0"
---

# Obsidian Web Clipper 配置说明

## 适用场景

为本地知识库配置两个手动选择的 Obsidian Web Clipper 模板：普通网页进入收件箱；经用户逐项认可的来源才可使用 raw 示例模板保存证据。

## 配置步骤

1. 打开 Obsidian Web Clipper 的 **Templates**，分别导入 [[Templates/Web Clipper-默认收件箱.json|默认收件箱模板]] 与 [[Templates/Web Clipper-可信来源raw示例.json|可信来源 raw 示例模板]]。
2. 在 Clipper 中选择本地 Vault：`E:\李大谱的小脑瓜`。
3. 保持默认模板的路径为 `01-收件箱`；普通网页、临时材料和无法确定主归属的内容都先进入收件箱。
4. 可信来源 raw 示例默认没有触发器。每新增一个可信域名触发器，都必须先由用户明确批准；未获批准前只可手动选择该模板。不得预设、虚构或默认认可任何域名。
5. `30-资源/raw` 是只读证据层。不要编辑、覆盖、移动或用后续消化结果替换 raw 抓取；消化时另建资源或其他正式笔记。
6. 分别使用一张不含敏感信息的公开页面测试两个模板；测试时避免保存账号秘密、令牌、个人隐私或未经授权的业务信息。
7. 在正常使用前，确认生成的 Markdown 位于预期路径，并核对 frontmatter 中的标题、URL、站点、抓取日期、可信度与输入生命周期字段。

## 模板边界

- 默认收件箱模板的 `triggers` 为空，必须人工选择，不能静默抓取所有网站。
- raw 示例模板的 `triggers` 同样为空，且包含安装警告；它不是任何网站的预先授权。
- raw 模板保留原样 `{{content}}`；原始内容只作证据保存，不能直接当作 confirmed 结论。

## 使用后的下一步

使用 [[40-辅助/每日Top3消化清单]] 处理收件箱输入；对于 raw 抓取，在正式资源笔记中注明来源关系，并保留原始页面不变。

## 版本记录

- v1.0（2026-08-13）：建立默认收件箱与用户审批的 raw 配置边界。
