---
title: macOS Computer Use 权限排查
tags:
  - macOS
  - ChatGPT
  - Computer-Use
  - 权限排查
created: 2026-09-29
updated: 2026-09-29
status: 可复用操作说明
---

# macOS Computer Use 权限排查

## 当前结论

Computer Use 通常是 ChatGPT 内部安装的插件或辅助进程，不一定在“应用程序”文件夹中存在独立 `.app`。普通截图能力可能只要求为 **ChatGPT** 开启屏幕权限；自动点击、输入和控制其他应用时，插件实际启动后通常还会出现 **Codex Computer Use**，并需要屏幕录制和辅助功能两类权限。

## 正确设置顺序

1. 将 ChatGPT Mac 客户端更新到最新版。
2. 打开 ChatGPT，切换到 Work 或 Codex。
3. 进入 `Plugins → Computer Use`。
4. 安装/启用插件，并打开 Computer Use 的 Server 与 Skill 开关。
5. 点击 `Try now`，让辅助进程实际启动一次。
6. 出现 macOS 提示后，从提示进入系统设置。
7. 在以下两处分别启用 `Codex Computer Use`；若当前只有 ChatGPT，也先允许 ChatGPT：
   - `系统设置 → 隐私与安全性 → 屏幕与系统音频录制`
   - `系统设置 → 隐私与安全性 → 辅助功能`
8. 使用 `⌘Q` 完全退出 ChatGPT，再重新打开并测试。

不要先在权限页面点击“+”号去“应用程序”目录寻找 Computer Use。应由插件启动后主动向 macOS 注册权限条目。

## 仍然失败时

- 在 `Plugins → Computer Use` 中关闭后重新启用。
- 完全退出 ChatGPT，再次打开并触发 `Try now`。
- 仍不出现 `Codex Computer Use` 时，重新安装最新版 ChatGPT 客户端，再重新触发权限请求。
- 每次调整权限后都要完全退出并重启应用，不能只关闭窗口。

## 参考

- [Computer Use 官方说明](https://learn.chatgpt.com/docs/computer-use)
- [ChatGPT macOS 截图权限说明](https://help.openai.com/en/articles/9295245-chatgpt-macos-app-screenshot-tool)

---

相关：[[个人AI工作台 Index]] · [[每日核心沉淀 2026-09-29]] · [[知识库总索引]]
