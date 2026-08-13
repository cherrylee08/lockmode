---
id: KB-ASSET-20260813-004
title: Voice Core M1 发布验收 2026-08-05
type: asset
status: active
created: 2026-08-05
updated: 2026-08-13
owner: 李大谱
confidence: confirmed
source_refs: ["E:\\李大谱的工作台\\docs\\voice-core-acceptance.md"]
related: ["[[个人AI工作台 Index]]"]
review_date: 2026-09-13
asset_type: 发布验收记录
version: M1
approved_by: 李大谱
derived_from: ["Voice Core M1 发布验收-2026-08-05.md"]
tags: [VoiceCore, 个人AI工作台, 发布验收, 桌面应用]
---

# Voice Core M1 发布验收 2026-08-05

## 今日成果

Voice Core M1 形成了发布验收矩阵、release 可执行文件和 NSIS 安装包。

## 自动验证结果

- `npm run verify` 最终退出 0。
- renderer：44/44 通过。
- native：152 pass，1 个官方模型 fixture 测试按设计 ignored。
- Playwright 持久化 E2E 与 8 类恢复：9/9 通过。
- Clippy、源码门禁、生产内容扫描和 release artifact guard 均通过。

## 发布产物

| 产物 | 字节数 | SHA-256 | 签名状态 |
|---|---:|---|---|
| `src-tauri/target/release/voice-core.exe` | 34,225,152 | `76B2FC7CEAE241ACDED98AA966857E6DE4B008466370A2912022F20BF39F18A9` | NotSigned |
| `src-tauri/target/release/bundle/nsis/逗比语音工作台_0.1.0_x64-setup.exe` | 9,060,859 | `D000B545D0C6B374A1C1F41735225BFD73AE03780B2607A9CE97CD4881DE4C05` | NotSigned |

## 今日代码线索

工作台仓库今日有 6 个提交：

- `c5393ba`：连接 workbench discussions 到 Codex CLI。
- `c98fe7a`：避免 voice overlay 阻塞工作台输入。
- `678d94c`：启动时打开可用的工作台 dashboard。
- `32f9e48`：Windows 工作台启动时不显示控制台。
- `08f4a54`：刷新 release artifact hashes。
- `93679a1`：容忍 fallback hotkey 被占用。

## 仍需人工验收

- 代码签名仍为 `NotSigned`，只有签名状态为 Valid 才可视为签名通过。
- 物理唤醒、检测时延、上下文识别、Direct/Confirm 策略、ChatGPT 桌面状态、性能、离线和权限恢复仍需真实设备和人工记录。

## 来源

- `E:\李大谱的工作台\docs\voice-core-acceptance.md`

---

相关：[[个人AI工作台 Index]] · [[桌面语音助手设计]] · [[每日核心沉淀 2026-08-05]]
