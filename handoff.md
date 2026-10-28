# todaynew 项目交接说明

## 当前任务与状态（2026-10-28）

- 项目目标：AIHOT 每日新闻 → 简报与视频稿 → edge 云希配音和 KTV 字幕 → Remotion 1080×1920 / 30fps 竖屏成片，交由外部流程发布到抖音、B站和视频号。
- 本次用户要求：以 `skills/todayaihot/` 为核心，读取最近成片并制定优化方案到 `docs/`。**已完成方案与证据，未实施改造。**当前入口：[2026-10-28 优化方案](docs/research/main-AI日报视频优化方案-20261028.md)；[证据和复现](docs/research/evidence/2026-10-28/README.md)；[文档索引](docs/README.md)。
- 本次仅审阅 10-24、10-26、10-27 本地视频；未生成/重渲染视频、未发布、未修改产品代码或技能、未安装依赖、未 commit/push。任务前 `handoff.md` 已有用户工作树改动，完整原文及历史登记保存在 [本次审阅前交接](docs/research/evidence/2026-10-28/handoff-before-review.md)，更早历史在 [10-14 快照](docs/research/evidence/2026-10-14/handoff-before-review.md)。本文件因原有 33,987 字节超限而压缩，保留近期逐日登记并以快照承载历史。

## 本次发现和验证

- 10-27、10-26、10-24 容器时长分别 51.4、55.8、53.4 秒；最终音轨综合响度/真峰值分别 −14.81/−0.76、−15.05/−0.68、−15.48/−0.79 LUFS/dBTP。三期真峰值均高于项目内部 ≤−1 dBTP 目标；音视频流有 0.067—0.133 秒结束差异。三期末尾抽帧均为结束页，未复现旧报告中的纯背景空尾。
- **纠正 10-26 历史 QA**：第 1 条 7.755 秒的配图区是大面积白底宣传文案，非合格实拍；旧记录的“7 张全实拍、无文字卡”不能沿用。第 7 条是工作站实拍，关联性另议。10-27 的 `M3.1` 跨行拆开，正文有省略；开场“Cohere直接发布”缺对象。
- 10-27/26 的现有报告显示 READY，但 `images_reviewed` 与 `tail_frame_checked` 为 false；隔离 fixture 已证明质量失败仍可 READY。混音失败仍可能归档原片并返回 0。10-27 发布稿为五个空来源 `[]`、没有原文 URL，章节与当前 JSON 不一致。**不要将历史 READY/QA 登记视为新的完整发布验收。**
- 历史平台回执摘要（均未在线重验）：10-26 抖音/B站 `BV1bonQ6mE8L` 成功，视频号当日补发成功；10-22 三平台成功，B站 `BV1sZnm6hE1M`；10-21 抖音/B站 `BV1M2ni6gEro` 成功，视频号当时失败；10-19 三平台成功，B站 `BV1WPnj6TEKD`；10-16 抖音/B站 `BV1wAJ96zEfk` 成功，视频号当时失败。完整细节见审阅前快照。
- `finalize.py` 补写旧日可能覆盖最新日自动块，且继承旧发布回执未核对视频哈希；隔离复现见证据。`fetch_news.py` 清理共享图片，音频和时间轴也有跨次错配风险。正式重跑前须隔离或备份，避免在共享工作目录并行生产。
- 当前实际代码已实现同日解析幂等、preview 隔离、部分 TTS 缓存、混音预检、Audio 第 0 帧起播、尾部场景覆盖、部分媒体实测及 `--only render` 后补发布物料/收尾；后两项与现有技能文档部分描述不一致。10-14 方案不是全部未实施。
- 基线：`python -X utf8 -m pytest skills/todayaihot/tests/ -q` 为 **80 passed**；`remotion/` 的 `npm run typecheck` 通过；当前 `validate_output.py` 为 0 ERROR / 6 WARN。未进行连续观看、人工听审、真机预览、全量新闻事实核查或在线回执核验，不能据此宣称视频通过完整验收。

## 继续时的约束与下一步

1. 先阅读 10-28 方案与当前源码；优先讨论质量门、混音失败处理、日期块与回执绑定、章节来源，然后处理运行隔离、实拍审核与样片版式。跨模块状态和显示稿/朗读稿契约在实施前按项目规则确认；严格先写可复现失败测试，再实现与回归。
2. 仍保持每条新闻真实实拍照片、禁止文字卡/海报；图库照片若与事件无直接关系，应标为示意并审相关性。更改为允许官方界面、录屏或图表需要另行确认。固定 edge 云希 `zh-CN-YunxiNeural`、语速 +30%、音量 +50%；不要主动启动 GPT-SoVITS。
3. 发布封面由外部 video-upload 大字模板重绘，按现有流程 `--force-regen`、不传显式封面绕过重绘；抖音合集“每日全球AI大事”、B站 tid=231、署名“翻奇兽AI”。线上状态未知先核验；不同平台及不同视频哈希分别记录，已成功的平台不要跟随补发。
4. 历史未闭事项：10-14、10-21、10-24 视频号曾因 cookie 失败，当前线上状态未重新核验；10-16 亦有视频号失败登记，需以实际回执核验。09-18 首版与修复版曾在线并存，删除/重发须用户明确授权。10-24 本地版是 10-25 修正版，线上当时仍为旧版。
5. 现有 handoff 自动写入日期块有已复现缺陷；在修复前不要用 `finalize.py` 对旧日做正式回写。10-12 曾对本机 edge-tts 安装打补丁，升级包可能覆盖；以归档记录和现状核实，勿盲目重打。新依赖和缓存遵循 F 盘迁移约定，配置插件/MCP 走统一 TOML 真相源。

## 关键路径与命令

- 技能与契约：`skills/todayaihot/SKILL.md`、`skills/todayaihot/USAGE.md`、`skills/todayaihot/references/pipeline-contract.md`、`skills/todayaihot/references/automation-prompt.md`。
- 生产脚本：`skills/todayaihot/scripts/`；前端：`remotion/src/`；现有中间文件：`work/`，可能被后续运行覆盖。
- 只读验证：项目根执行 `python -X utf8 -m pytest skills/todayaihot/tests/ -q` 和 `python -X utf8 skills/todayaihot/scripts/validate_output.py`；进入 `remotion/` 执行 `npm run typecheck`。
- 更新本交接时保持 ≤24,576 字节，同日期更新而非重复；执行前先核对日期和自动块范围。历史回执原文见归档，不得因为归档而删除仍有效事实。

## 视频登记

下列 `READY` 是历史流水线原始状态，不代表 10-28 新增质量标准已通过；平台结果为历史登记，未在线重验。每条视频的主路径使用绝对路径，保留自动登记块以供后续接续。

### 自动登记（2026-10-27）
<!-- finalize:begin -->
- 日期：2026-10-27
- 主题：每日 AI 头条（7 条精选：Open AI 发布 G P T 六.1、Open AI 宣布模型连下三项科学突破、Cloudflare 披露 G L M …）
- 简介：2026-10-27 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-27\每日ai热门新闻-2026-10-27.mp4`
- 状态：READY（1080×1920 @30fps，51.4s，16.7MB，音轨正常，sha256 862fce484d68…）
- TTS：edge-tts，align=auto，7 条/9 句
- 封面：`out\2026-10-27\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-27\chapters.json`（9 条）
- 发布物料：`out\2026-10-27\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
- 发布结果（2026-10-27 10:11 完成）：抖音✓（合集「每日全球AI大事」+ --force-regen 重绘 3:4 大字封面，封面目检通过）/ B站✓ BV1EoxK6UEWV（审核中）/ 视频号✓（3:4 竖版封面成功，4:3 横版失败属已知非致命）
- QA：8 帧初检 + 4 帧复检通过；4 处配图返工（OpenAI Discover 海报 / Cloudflare 插画 / North 2 海报 / MiniMax 宣传图）→ repair_1027.py 换 Pexels 实拍后重建 timeline 重渲染；KTV 黄白字幕正常，配图缺失 0，7 张配图互不重复
<!-- finalize:end -->

### 自动登记（2026-10-26）
<!-- finalize:begin -->
- 日期：2026-10-26
- 主题：每日 AI 头条（7 条精选：南北阁发布 Nanbeige4.3-33、斯坦福与伯克利发布 TokenGate 、HumanLayer 提出 Agent …）
- 简介：2026-10-26 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-26\每日ai热门新闻-2026-10-26.mp4`
- 状态：READY（1080×1920 @30fps，55.8s，21.0MB，音轨正常，sha256 2fab582b558c…）
- TTS：edge-tts，align=auto，7 条/9 句
- 封面：`out\2026-10-26\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-26\chapters.json`（9 条）
- 发布物料：`out\2026-10-26\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->

### 自动登记（2026-10-24）
<!-- finalize:begin -->
- 日期：2026-10-24
- 主题：每日 AI 头条（Kimi、Nemotron、Agent 与开源模型等 7 条精选）
- 简介：2026-10-24 的 7 条 AI 新闻一分钟速览。
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-24\每日ai热门新闻-2026-10-24.mp4`
- 状态：本地修正版 1080×1920 / 30fps、53.4 秒，SHA256 `99cfa5f433422574d4077fa16d5b320bd1d4aa0a8053278c50de82765bfddc10`；当前目录无 run_report.json。
- 封面：`E:\workbuddy-workspace\todaynew\out\2026-10-24\covers\`；章节：`E:\workbuddy-workspace\todaynew\out\2026-10-24\chapters.json`。
- 历史发布：抖音、B站成功（`BV1RpHP6bEvj`），视频号因 cookie 失败，是否后续补发未知；当时线上版本早于本地 10-25 版式修正，未在线复核。
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）。
<!-- finalize:end -->

### 自动登记（2026-10-23）
<!-- finalize:begin -->
- 日期：2026-10-23
- 主题：每日 AI 头条（7 条精选：Google Cloud 推出 Agen、Open AI 发布 Decisions、Codex 0.164.0 新增十个预设…）
- 简介：2026-10-23 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-23\每日ai热门新闻-2026-10-23.mp4`
- 状态：READY（1080×1920 @30fps，53.1s，24.1MB，音轨正常，sha256 6f325ca2c870…）
- TTS：edge-tts，align=auto，7 条/9 句
- 封面：`out\2026-10-23\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-23\chapters.json`（9 条）
- 发布物料：`out\2026-10-23\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）

#### 发布结果（2026-10-23 16:40）
- 抖音：✓ 成功（合集「每日全球AI大事」，选「内容由AI生成」；3:4 竖版大字封面已上传，封面门禁通过；「章节要点」弹窗未出现属已知非致命）
- B站：✓ 成功（BV1psnb63Ete，tid 231，状态「审核中」）
- 视频号：✓ 成功（3:4 竖版封面成功，短标题「1023AI头条智能体沙箱」；4:3 横版封面设置失败属已知非致命）
<!-- finalize:end -->

### 自动登记（2026-10-22）
<!-- finalize:begin -->
- 日期：2026-10-22
- 主题：每日 AI 头条（7 条精选：Open AI A P I 支持 12 、蚂蚁集团与 v L L M 社区开源量化、Wiz 披露 LiteLLM PyPI …）
- 简介：2026-10-22 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-22\每日ai热门新闻-2026-10-22.mp4`
- 状态：READY（1080×1920 @30fps，46.1s，16.6MB，音轨正常，sha256 3c165d30ef90…）
- TTS：edge-tts，align=auto，7 条/12 句
- 封面：`out\2026-10-22\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-22\chapters.json`（9 条）
- 发布物料：`out\2026-10-22\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->

### 自动登记（2026-10-21）
<!-- finalize:begin -->
- 日期：2026-10-21
- 主题：每日 AI 头条（7 条精选：Deep Seek 全面开源内部推理框架、Google 与 Meta 推出 Tor、A M D 与英特尔统一 PyTorch…）
- 简介：2026-10-21 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-21\每日ai热门新闻-2026-10-21.mp4`
- 状态：READY（1080×1920 @30fps，44.9s，14.5MB，音轨正常，sha256 6a451b6db58f…）
- TTS：edge-tts，align=auto，7 条/11 句
- 封面：`out\2026-10-21\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-21\chapters.json`（9 条）
- 发布物料：`out\2026-10-21\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->

### 自动登记（2026-10-20）
<!-- finalize:begin -->
- 日期：2026-10-20
- 主题：每日 AI 头条（7 条精选：MiniMax 发布 M3.1 Flas、Open AI 开源 MultiLang、扩散语言模型 Mercury 3 上线 …）
- 简介：2026-10-20 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-20\每日ai热门新闻-2026-10-20.mp4`
- 状态：READY（1080×1920 @30fps，52.0s，15.2MB，音轨正常，sha256 79438039e563…）
- TTS：edge-tts，align=auto，7 条/13 句
- 封面：`out\2026-10-20\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-20\chapters.json`（9 条）
- 发布物料：`out\2026-10-20\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->
- 发布结果（2026-10-20 16:17）：抖音✓（合集「每日全球AI大事」+ 大字封面 --force-regen 重绘，章节弹窗未出现属已知非致命）/ B站✓ `BV1Z2nc6HEvi`（开放浏览，tid=231）/ 视频号✓（3:4 竖版封面设置成功；4:3 横版封面失败属已知非致命）
- 标题「10.20 AI头条：MiniMax降价 端侧35B 提速」/ chapters.json 已回写真实条目标题 / QA 抽帧 8 帧全实拍、KTV 字幕正常、TP -0.69 dBTP

### 自动登记（2026-10-19）
<!-- finalize:begin -->
- 日期：2026-10-19
- 主题：每日 AI 头条（7 条精选：Anthropic 内部研究：初级技术岗、Deep Seek-V4.1-Flash、实测 Google Muse、Grok …）
- 简介：2026-10-19 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-19\每日ai热门新闻-2026-10-19.mp4`
- 状态：READY（1080×1920 @30fps，47.8s，14.8MB，音轨正常，sha256 fd112b381ae9…）
- TTS：edge-tts，align=auto，7 条/12 句
- 封面：`out\2026-10-19\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-19\chapters.json`（9 条）
- 发布物料：`out\2026-10-19\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->

### 自动登记（2026-10-16）
<!-- finalize:begin -->
- 日期：2026-10-16
- 主题：每日 AI 头条（7 条精选：Meta 开源 816B 巨兽 Muse、Anthropic Code Revie、微软 MAI-Base-2：算力效率 4…）
- 简介：2026-10-16 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-16\每日ai热门新闻-2026-10-16.mp4`
- 状态：READY（1080×1920 @30fps，49.2s，15.0MB，音轨正常，sha256 1b9b6e873766…）
- TTS：edge-tts，align=auto，7 条/16 句
- 封面：`out\2026-10-16\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-16\chapters.json`（9 条）
- 发布物料：`out\2026-10-16\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->

### 自动登记（2026-10-15）
<!-- finalize:begin -->
- 日期：2026-10-15
- 主题：每日 AI 头条（7 条精选：Visual Studio Copilo、微软 Work IQ 知识编译引擎：不换、Claude Code 空闲压缩机制详解…）
- 简介：2026-10-15 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-15\每日ai热门新闻-2026-10-15.mp4`
- 状态：READY（1080×1920 @30fps，50.7s，17.0MB，音轨正常，sha256 4316d3b82a3a…）
- TTS：edge-tts，align=auto，7 条/11 句
- 封面：`out\2026-10-15\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-15\chapters.json`（9 条）
- 发布物料：`out\2026-10-15\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->
<!-- publish:begin -->
- 发布结果（2026-10-15 16:21）：抖音✓（合集「每日全球AI大事」+ 重绘 3:4 大字封面，章节弹窗未出现属已知非致命）/ B站✓ `BV1mEJ16xEva`（审核中，tid=231）/ 视频号✓（3:4 竖版封面设置成功；4:3 横版封面失败属已知非致命）
- 发布标题：AI日报1015：Copilot曝漏洞，智能体提速4倍（署名翻奇兽AI）
- QA 记录：11 帧抽帧目检通过，配图原文 3 / Pexels 4 / 缺失 0；首版 s4/s7 图库热图视觉重复，经 work/repair_1015.py 换图（s7→代码屏幕特写）后仅重跑 render 修复
<!-- publish:end -->

下列三期为既有作品。主视频路径补列如下；原登记保留，发布状态未经本次在线复核，测量修正以上节为准。

| 日期 | 主视频路径 | 本次实测时长 |
|---|---|---:|
| 2026-10-14 | `out\2026-10-14\每日ai热门新闻-2026-10-14.mp4` | 46.61s |
| 2026-10-13 | `out\2026-10-13\每日ai热门新闻-2026-10-13.mp4` | 51.90s |
| 2026-10-12 | `out\2026-10-12\每日ai热门新闻-2026-10-12.mp4` | 52.00s |

### 自动登记（2026-10-14）
- 日期：2026-10-14
- 主题：每日 AI 头条（7 条精选：Gemini 4 Argon 1M 上下文、Anthropic 自研 Scion 替代 Git、Argon 无人值守优化 ADK 20 万行、LangChain langchain-scaledown、Liquid AI LFM2.5-24B-A2B、XBOW Chrome 漏洞赏金、RTX Spark 笔记本上市）
- 简介：2026-10-14 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-14\每日ai热门新闻-2026-10-14.mp4`
- 状态：成片已生成，历史发布回执见下；本次实测46.61s、-17.92 LUFS、-1.19 dBTP。存在文字/品牌卡漏检、弱相关配图和空尾，不能沿用历史“7/7实拍合格”的结论。
- TTS：edge-tts（云希），align=auto；当前快照7条/9句、无failed_clauses。历史过程故障：edge 429限流（首跑失败、重试成功）；concurrency=2时Chrome内存不足，降为1成功。
- 封面：`out/2026-10-14/covers/`（3:4 竖版 / 16:9 宽屏，大字模板重绘 --force-regen）
- 章节：`out/2026-10-14/chapters.json`（9 条，真实条目标题已回写）
- 发布结果（2026-10-14 16:15）：抖音✓（合集「每日全球AI大事」+ 重绘 3:4 大字封面，章节弹窗未出现属已知非致命）/ B站✓ `BV1JBpC61EwR`（审核中，tid=231）/ 视频号✗ cookie 失效（tencent/tencent1 code=1，无人值守无法恢复，需管理员扫码后单平台补发）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）

### 自动登记（2026-10-13）
- 日期：2026-10-13
- 主题：每日 AI 头条（7 条精选：微软发布自研芯片 Maia 300，明年、Epic Games 转向 AI 先行开、Vapi 自研 AI 代码审查机器人，P…）
- 简介：2026-10-13 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-13\每日ai热门新闻-2026-10-13.mp4`
- 状态：成片已生成，历史发布回执见下；本次实测51.90s、-17.57 LUFS、-1.42 dBTP。存在密集正文、关联较弱的素材和纯背景空尾；历史QA不等于本次完整质量通过。
- TTS：edge-tts，align=auto，7 条/16 句
- 封面：`out/2026-10-13/covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏，大字模板重绘）
- 章节：`out/2026-10-13/chapters.json`（9 条）
- 发布物料：`out/2026-10-13/publish.md`（标题×3 / 话题标签 / 简介 / 置顶评论）
- 发布结果（2026-10-13 16:12）：抖音✓（合集「每日全球AI大事」+ 重绘 3:4 大字封面，章节弹窗未出现属已知非致命）/ B站✓ `BV19kWw6REbK`（开放浏览）/ 视频号✓（3:4 竖版封面设置成功，4:3 横版封面失败为已知非致命）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）

### 自动登记（2026-10-12）
- 日期：2026-10-12
- 主题：每日 AI 头条（7 条精选：Open AI 将 G P T 六.1 、Beyond Naive R A G：9、UC San Diego 用心理模型奖励…）
- 简介：2026-10-12 7 条 AI 头条一分钟速览
- 主视频路径：`E:\workbuddy-workspace\todaynew\out\2026-10-12\每日ai热门新闻-2026-10-12.mp4`
- 状态：成片已生成，本次测量最终混音MP4为1080×1920 @30fps、52.00s、17,081,680字节、音轨存在；旧报告50.452s为master时长，不是最终视频时长。
- TTS：edge-tts，align=auto，7 条/14 句
- 封面：`out/2026-10-12/covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏）
- 章节：`out/2026-10-12/chapters.json`（9 条）
- 发布物料：`out/2026-10-12/publish.md`（标题×3 / 话题标签 / 简介 / 置顶评论）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
- 发布结果（2026-10-12 17:00 执行）：B站 ✓ `BV1bip96oEHa`（开放浏览，tid=231）／视频号 ✓（3:4 封面成功、4:3 横版跳过属已知非致命，短标题「每日AI头条1012」）／抖音 ✓（17:14 补发成功，合集「每日全球AI大事」+重绘 3:4 大字封面+AI声明，章节要点弹窗未出现属已知非致命；故障链：cookie 间歇失效→patchright chromium-1208 缺失→重装 20 分钟→login 复用本机会话刷新 cookie→单平台补发一次成功）
- TTS 修复记录：edge 后端 403 硬故障（微软 2026-10 起将合成 WS 端点迁移至 api.msedgeservices.com，旧 host 大面积 403，PR rany2/edge-tts#491 未发版），已本地 patch `site-packages/edge_tts/constants.py`（WSS_URL 换新端点 + token 以 Ocp-Apim-Subscription-Key 参数传递）与 `drm.py`（locale 无关日期解析）；备份 *.bak_1012；升级 edge-tts 时补丁会被覆盖需重打
- 成片修正：BGM 闪避混音流水线失败，已用 `work/audio_fix_1009.py` 兜底，52.0s、峰值 -1.50 dBFS
- QA：原交接曾登记抽帧10帧合格；本次发现三行字幕、正文过密、显示专名被TTS定读污染和空尾，完整质量验收尚未通过。

### 自动登记（2026-09-06）
<!-- finalize:begin -->
- 日期：2026-09-06
- 主题：每日 AI 头条（1 条精选：冒烟测试标题：验证 9:16 竖屏渲染链）
- 简介：2026-09-06 1 条 AI 头条一分钟速览
- 主视频路径：`out\2026-09-06\每日ai热门新闻-2026-09-06.mp4`
- 状态：READY（1080×1920 @30fps，7.6s，1.0MB，音轨正常，sha256 bfe7273f476b…）
- TTS：smoke-tts，align=smoke，1 条/3 句
- 封面：`out\2026-09-06\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-09-06\chapters.json`（3 条）
- 发布物料：`out\2026-09-06\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->
