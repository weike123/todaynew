---
name: todayaihot
description: 将每日 AI 新闻 Markdown 生成可审阅的逐字稿、配音字幕、Remotion 竖屏视频和 codebase-style 封面；适用于 todaynew 项目的新闻短视频流水线。
---

# todayaihot

## 目标

把项目根目录的每日 AI 新闻简报转换为 `out/YYYY-MM-DD/` 下的 9:16 成片、字幕时间轴、封面、发布物料和 `handoff.md` 登记。

当前还原包只恢复了 Remotion 前端；`scripts/` 流水线、`work/` 中间产物和每日 `out/` 产物尚未恢复。发现这些文件缺失时，必须明确报告“流水线层未恢复”，不能假装已经完成抓取、TTS 或渲染。

## 不可回归的约束

1. **逐字稿先行**：先生成并校验 `work/逐字稿_<date>.md`，再生成配音和字幕。
2. **同一文本源**：卡片正文、逐字稿、TTS 输入、字幕文本必须来自同一份完整句；人工改稿后先回写 narration，再重生成 TTS。
3. **禁止字符硬截断**：超时或过长时重写成更短的完整句，不能截成“研究团队称……”这类残句；每句必须以完整标点结束。
4. **时间轴连续**：每个 clause 满足 `start < end`，字符边界位于句内；音频、字幕和场景使用同一时间基准。
5. **封面独立生成**：首帧静音封面和 3:4 / 4:3 / 16:9 封面使用 codebase-style 大字模板，不能把视频首帧直接裁切当作发布封面。
6. **输出可交接**：视频结束前更新项目根 `handoff.md`，同日期更新原条目，不重复追加。

## 推荐流程

在流水线脚本恢复后，按以下顺序执行：

1. 检查 `.env`、依赖、Remotion 版本和 `work/timeline.json` 生成能力。
2. 解析新闻并抓取要点/配图；Pexels 等密钥只能来自环境变量或 `.env`。
3. 导出逐字稿并做句末标点、总时长和单句长度校验。
4. 如需润色，编辑逐字稿并回写 narration，再强制重新生成配音和字幕。
5. 校验音频与时间轴后渲染主视频。
6. 用 Remotion still 生成 `cover_first_frame.png` 及三种比例封面。
7. 生成章节、发布物料、结构化 run report，并更新 `handoff.md`。

## Remotion 前端约定

- 画布：1080×1920，30fps；时间常量统一放在 `remotion/src/videoConfig.ts`。
- 首帧：3 帧静音 `TitleCard`；音频末尾默认保留 1.5 秒缓冲。
- `TitleCard` 与 `CoverImage` 共用 `components/CodebaseCover.tsx`。
- 配图使用 `staticFile()`，不使用 `objectFit: cover` 裁切新闻主体；无图时使用关键词海报卡兜底。
- 字幕分页不拆英文/数字单词，帧率从 `useVideoConfig()` 获取，不在组件内重复硬编码。
- 渲染前运行 `npm run typecheck`；新增颜色 token、时间常量或组件 props 时必须同步类型，不能依赖 `any` 掩盖输入错误。

## 相关参考

- [流水线契约](references/pipeline-contract.md)：narration、timeline、音频、封面和 handoff 的数据不变量。
- [封面规范](references/cover-style.md)：codebase-style 首帧和多比例封面要求。
- [还原检查清单](references/recovery-checklist.md)：代码还原后先确认哪些能力真实存在。
- [历史优化方案](../../docs/todayaihot-优化方案-20260914.md)：完整的优先级 backlog 与验收标准。
