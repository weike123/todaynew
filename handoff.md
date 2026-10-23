# todaynew 项目交接说明

## 当前任务与状态（2026-10-14）

- 项目目标：AIHOT 每日新闻 → 简报/视频稿 → edge 云希配音与 KTV 字幕 → Remotion 1080×1920/30fps → 抖音、B站、视频号。
- 本次用户要求：重点审阅 `skills/todayaihot/` 与 `skills/定时任务提示词.md`，读取最近产出视频，制定优化方案到 `docs/`。本次已完成该文档任务，未进入代码改造。
- 当前方案：[docs/research/main-AI日报视频优化方案-20261014.md](docs/research/main-AI日报视频优化方案-20261014.md)。目录索引：[docs/README.md](docs/README.md)。首轮建议 T0—T6：文档/配置、实测报告、正式质量门、幂等解析、TTS缓存、时间基准/片尾、混音与并发；第二轮再做显示稿/朗读稿分离、版式选图和发布回执。
- 本次没有生成新视频、发布/补发、修改现有技能/提示词/定时配置、安装依赖、commit或push。修改范围是新方案/证据与本交接。原工作树已有 `.env.example`、Remotion封面组件、技能资源/脚本等未提交改动及旧HTML删除，继续时先看 `git status`，不得覆盖。
- 当前分支审阅时为 main；远端历史登记为 `git@github.com:weike123/todaynew.git`，本次未访问远端。代码/技能/文档的Git状态与实际能力要分开核验。

## 本次复验结果

- 读取最终MP4：10-14=46.61秒；10-13=51.90秒；10-12=52.00秒；均1080×1920/30fps、H.264、AAC 48kHz双声道。详情、SHA256与44张抽帧见 [证据目录](docs/research/evidence/2026-10-14/README.md)。
- 三期尾部抽帧均有至少约1.2秒的纯背景窗口。10-14数字4渐变卡和模型品牌横幅不能计为实拍；部分人像与主题关联弱。旧登记的“7/7实拍”结论已被本次原帧证据修正。
- 原片响度实测10-14=-17.92、10-13=-17.57、10-12=-17.06 LUFS；真峰值分别-1.19/-1.42/-1.39 dBTP。未人工听审，不据此宣称发音/听感已验收。
- 当前FFmpeg支持loudnorm/amix，缺少asplit/aloop/sidechaincompress。历史“缺loudnorm”的说法不能再作为当前完整根因；真实混音链路仍需预检。NumPy备用混音的峰值/RMS不等于综合响度归一化。
- 10-14 `work/narration.json` 与 timeline内嵌narration一致，当前9句、380原始字符、content=44.952秒、master=45.052秒、failed_clauses=[]；旧登记16句不适用于当前快照。逐字相对时间未发现负值/逆序/越界；master已有0.1秒静音而前端再次延后3帧存在静态同步风险，尚未用点击声fixture/听审确认。
- 既有 `validate_output.py` 退出0，0 ERROR/8 WARN；不代表完整成片/配图/听感通过。10-14目录没有run_report.json、publish.md；10-12/13报告把master_duration写成视频时长，未反映最后混音成片。
- `SKILL.md`/`USAGE.md`仍称流水线未恢复，与实际scripts/work/out不符；提示词E/G路径、封面职责与代码存在冲突。本次只提出修订稿，没有改现行执行入口。
- 本次没有核验新闻原文真实性、平台当前发布状态、cookie或正在运行的定时器prompt；原交接发布结果是历史记录。

## 视频登记

### 自动登记（2026-10-23）
<!-- finalize:begin -->
- 日期：2026-10-23
- 主题：每日 AI 头条（7 条精选：Google Cloud 推出 Agen、Open AI 发布 Decisions、Codex 0.164.0 新增十个预设…）
- 简介：2026-10-23 7 条 AI 头条一分钟速览
- 主视频路径：`out\2026-10-23\每日ai热门新闻-2026-10-23.mp4`
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

### 自动登记（2026-10-22）
<!-- finalize:begin -->
- 日期：2026-10-22
- 主题：每日 AI 头条（7 条精选：Open AI A P I 支持 12 、蚂蚁集团与 v L L M 社区开源量化、Wiz 披露 LiteLLM PyPI …）
- 简介：2026-10-22 7 条 AI 头条一分钟速览
- 主视频路径：`out\2026-10-22\每日ai热门新闻-2026-10-22.mp4`
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
- 主视频路径：`out\2026-10-21\每日ai热门新闻-2026-10-21.mp4`
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
- 主视频路径：`out\2026-10-20\每日ai热门新闻-2026-10-20.mp4`
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
- 主视频路径：`out\2026-10-19\每日ai热门新闻-2026-10-19.mp4`
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
- 主视频路径：`out\2026-10-16\每日ai热门新闻-2026-10-16.mp4`
- 状态：READY（1080×1920 @30fps，49.2s，15.0MB，音轨正常，sha256 1b9b6e873766…）
- TTS：edge-tts，align=auto，7 条/16 句
- 封面：`out\2026-10-16\covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）
- 章节：`out\2026-10-16\chapters.json`（9 条）
- 发布物料：`out\2026-10-16\publish.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
<!-- finalize:end -->

### 发布结果（2026-10-16，人工登记）
- 抖音：✓ 发布成功（合集「每日全球AI大事」+ 重绘 3:4 大字封面；「章节要点」弹窗未出现，已知非致命告警）
- B站：✓ 发布成功 `BV1wAJ96zEfk`（tid=231，审核中）
- 视频号：✗ 失败——tencent/tencent1 cookie 失效（code=1），需管理员微信扫码重新登录后补发
- 说明：首跑因视频号 cookie 无效整体中止，改 --platforms douyin,bilibili 完成发布；未重复发布

### 自动登记（2026-10-15）
<!-- finalize:begin -->
- 日期：2026-10-15
- 主题：每日 AI 头条（7 条精选：Visual Studio Copilo、微软 Work IQ 知识编译引擎：不换、Claude Code 空闲压缩机制详解…）
- 简介：2026-10-15 7 条 AI 头条一分钟速览
- 主视频路径：`out\2026-10-15\每日ai热门新闻-2026-10-15.mp4`
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
- 主视频路径：`out/2026-10-14\每日ai热门新闻-2026-10-14.mp4`
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
- 主视频路径：`out/2026-10-13\每日ai热门新闻-2026-10-13.mp4`
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
- 主视频路径：`out/2026-10-12\每日ai热门新闻-2026-10-12.mp4`
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

## 必须保留的执行约束

- TTS固定 `--backend edge`、`zh-CN-YunxiNeural`（云希男声）、语速+30%、音量+50%；不要探测/启动GPT-SoVITS。仅用户当次明确要求克隆音色时另行确认参考音色。
- KTV `chars[].t`必须相对句首；生成后逐条取句中帧看黄白高亮，并进行实际听审，不能仅看时间戳通过。
- 新闻必须相关实拍照片，禁止文字/海报卡。缺失图片、静音失败、图片不合格应阻断正式发布；现有校验器尚未完整实现这些门，见新方案。
- 发布封面按现有外部video-upload大字模板重绘，仅传文字字段、加`--force-regen`，不传`--cover-*`绕过重绘；3:4和16:9均目检。副标题约18—20字符只是旧经验，不替代实际换行/边界检查。
- 当前解析会写`work/seen_titles.json`且同日自去重；fetch会清空共享`remotion/public/images/`。本次未运行parse/fetch/smoke。续接先解决幂等或在隔离备份下操作，不能反复删正式状态凑通过。
- 输入新闻当前E盘路径存在；旧提示词仍含G盘。共享运行时不得贸然搬迁。新装大依赖/缓存放F盘，统一插件配置仍走`F:\Migrated\.codex\pluginandskills.toml`与同步脚本。
- 发布由外部 `<SOCIAL_AUTO_UPLOAD_DIR>` 管理。抖音合集“每日全球AI大事”、B站tid=231、署名“翻奇兽AI”。发布结果未知先核查，不盲重试；已成功平台不跟随补发。已发布版本处置/删除需用户明确授权。
- `--only render`目前不会自动完整生成发布文案/报告；只换图重渲染后要留意报告缺失或过期。最终音频/图片/时间轴须同run，不能默认共享文件仍是对应日期。
- 正式逻辑修改严格先行为Red再Green，五维质量评审；新规格/跨模块改造先确认。未经明确要求不提交、推送、重发或清理线上历史作品。

## 待处理与下一步

1. 本次方案任务无阻塞；实现尚未开始。下一步按方案T0—T6作独立切片，并在涉及新内容契约前确认规格。不要把本报告完成当作改造完成。
2. 10-14视频号历史登记失败，需管理员恢复登录后仅该平台补发；此前抖音/B站已登记成功，本次未重复发布也未在线重验。
3. 09-18首版女声/字幕缺陷视频与修复版历史记录显示在线并存，是否删除首版仍待用户决定；未经授权不得处理。
4. 字幕正文布局、文字卡漏检、跨期重复图库、BGM临时兜底、TTS缓存/失败静音、去重自锁与报告可信度均纳入新方案，不再视为“卡点无”。
5. 继续时读取本交接、方案及当前Git状态；工作目录可能已被次日定时任务覆盖，以证据快照核对本次结论。

## 关键路径与只读复核命令

- 方案：`docs/research/main-AI日报视频优化方案-20261014.md`。
- 原始42KB交接与历史视频/发布记录：`docs/research/evidence/2026-10-14/handoff-before-review.md`。更早视频登记、旧故障细节保存在该快照，不再在24KiB交接中重复堆积。
- 现有旧方案：`docs/todayaihot-优化方案-20260914.md`，仅历史参考；续接先读新方案。
- 当前源码：`skills/todayaihot/scripts/`、`remotion/src/`；提示词：`skills/定时任务提示词.md`；新闻源：`<NEWS_DIR>/AI新闻推送_YYYY-MM-DD.md`。

```powershell
Set-Location '<项目根目录>'
git status --short
python -X utf8 skills/todayaihot/scripts/validate_output.py
(Get-Item -LiteralPath '.\handoff.md').Length
```

完整媒体复核命令见证据README；本次未跑新的渲染、TTS或产品回归测试，不能把只读检查说成实现Green。handoff必须≤24,576字节，长期历史与证据放docs并由本文件引用。

## 2026-10-19 每日AI头条发布结果（fe33e700）
- 成片：out/2026-10-19/每日ai热门新闻-2026-10-19.mp4（47.8s，edge+云希，357 字口播）
- QA：8 帧抽帧通过，配图原文 2 / Pexels 5 / 缺失 0，实拍互不重复，KTV 黄白字幕正常
- 抖音：✅ 发布成功（合集「每日全球AI大事」，重绘 3:4 大字封面；章节要点弹窗未出现，非致命）
- B站：✅ 发布成功 BV1WPnj6TEKD（审核中）
- 视频号：✅ 补发成功（16:14，cookie 恢复后单平台重发；短标题「1019AI头条速览」，3:4 封面成功、4:3 横版失败属已知非致命）


## 2026-10-21 每日AI头条发布结果（fe33e700）
- 成片：out/2026-10-21/每日ai热门新闻-2026-10-21.mp4（44.9s，edge+云希，328 字口播，7 条条目）
- QA：11 帧抽帧通过，全部实拍照片互不重复，KTV 黄白字幕正常；TorchTPU 原文配图为 profiling 截图已替换为 Pexels 实拍；MemCurrent/Voxtral 缺图经 Pexels 修复后缺失 0
- 抖音：✅ 发布成功（合集「每日全球AI大事」，重绘 3:4 大字封面 --force-regen；章节要点弹窗未出现，非致命）
- B站：✅ 发布成功 BV1M2ni6gEro（tid 231，审核中）
- 视频号：❌ 未发布（cookie 已失效需扫码重登，无人值守无法扫码，如实登记阻塞；待 cookie 恢复后单平台补发）
- 封面：主标题「每日AI头条 10.21」副标题「DeepSeek开源推理框架」，门禁通过（AR 0.750，亮像素 18.2%）
- **缺陷登记（2026-10-21 晚修复）**：已发布成片中第 1、3 条口播/字幕为残句（"DeepSeek 将内部生产级推理框架。"、"AMD 与英特尔宣布在 PyTorch 的 x86。"）——`_spoken_bullet` 在 ASCII 空格处截断要点所致。用户明确不重新生成视频，故未重渲染未重发。修复已落入 skill：`_spoken_bullet` 重写（只认中文标点边界）+ `audit_spoken_clause` 组装期审计 + `validate_output` 残句 ERROR 硬门 + `split_long_clause`/`build_bullets` 同源缺陷修复 + 时长估算改非空白字符基数；`tests/test_spoken_clause.py` 19 用例回归，全量 70 passed；对当日 narration.json 实跑校验精确报 2 ERROR 无误报。如需更正版：cookie 恢复后完整流水线重跑并单平台补发，补发前须与用户确认旧版处置方式，详见 `skills/todayaihot/references/spoken-clause-completeness.md`。


## 2026-10-22 每日AI头条发布结果（fe33e700）
- 成片：out/2026-10-22/每日ai热门新闻-2026-10-22.mp4（46.1s，edge+云希，365 字口播，7 条条目；1080x1920/30fps，16.6MB）
- 响度：-14.85 LUFS / TP -0.72 dBTP / LRA 3.1；BGM 闪避混音（leberch-ambient-piano）
- QA：7 帧抽帧通过（3/9/15/21/28/35/42s），全部实拍照片互不重复（7 张 md5 全异），KTV 黄白字幕高亮正常，无文字卡
- 配图：原文 2 / Pexels 5 / Pixabay 0 / 缺失 0
- 抖音：✅ 发布成功（合集「每日全球AI大事」，重绘 3:4 大字封面 --force-regen；章节要点弹窗未出现，非致命）
- B站：✅ 发布成功 BV1sZnm6hE1M（tid 231，转码中）
- 视频号：✅ 发布成功（短标题「12小时prompt缓存+Cl」；3:4 竖版封面成功、4:3 横版失败属已知非致命）
- 封面：主标题「每日AI头条 10.22」副标题「12小时prompt缓存与vLLM量化内核」，门禁通过（AR 0.750，亮像素 17.7%）
- 章节：chapters.json 9 条，占位「第N条」已回写为真实条目标题（去助读空格、截 22 字）
- **缺陷修复（2026-10-22）**：发现并修复口播双标点缺陷 —— `merge_clauses` 按逗号切分标题后子句以「，」结尾，`ensure_period` 只识别句末标点却直接追加「。」，产出「xxx 缓存，。」这类双标点（当日 narration.json 实测 2 处）。修复：`ensure_period` 对逗号/顿号结尾做**替换**而非追加（E 盘运行版 + F 盘源同步）；新增 `tests/test_punct_normalization.py` 11 用例回归，全量 80 passed。修复后重跑 parse+fetch+TTS+render，narration.json 双标点计数 0。
- **环境事实登记**：`skills/todayaihot` 已是**实体目录而非 junction**，且与 `<WORKBUDDY_DATA>/skills/todayaihot` 已分叉（E 盘含 10-21 残句修复 audit_spoken_clause，F 盘源为旧版无此函数；E 盘 SKILL.md 5514 字节 vs F 盘 44155 字节）。两处各自维护，修改需同步两份。


## 2026-10-22 每日AI头条发布结果（fe33e700）
- 成片：out/2026-10-22/每日ai热门新闻-2026-10-22.mp4（46.1s，edge+云希，365 字口播，7 条条目；1080x1920/30fps，16.6MB）
- 响度：-14.85 LUFS / TP -0.72 dBTP / LRA 3.1；BGM 闪避混音（leberch-ambient-piano）
- QA：7 帧抽帧通过（3/9/15/21/28/35/42s），全部实拍照片互不重复（7 张 md5 全异），KTV 黄白字幕高亮正常，无文字卡
- 配图：原文 2 / Pexels 5 / Pixabay 0 / 缺失 0
- 抖音：✅ 发布成功（合集「每日全球AI大事」，重绘 3:4 大字封面 --force-regen；章节要点弹窗未出现，非致命）
- B站：✅ 发布成功 BV1sZnm6hE1M（tid 231，转码中）
- 视频号：✅ 发布成功（短标题「12小时prompt缓存+Cl」；3:4 竖版封面成功、4:3 横版失败属已知非致命）
- 封面：主标题「每日AI头条 10.22」副标题「12小时prompt缓存与vLLM量化内核」，门禁通过（AR 0.750，亮像素 17.7%）
- 章节：chapters.json 9 条，占位「第N条」已回写为真实条目标题（去助读空格、截 22 字）
- **缺陷修复（2026-10-22）**：发现并修复口播双标点缺陷 —— `merge_clauses` 按逗号切分标题后子句以「，」结尾，`ensure_period` 只识别句末标点却直接追加「。」，产出「xxx 缓存，。」这类双标点（当日 narration.json 实测 2 处）。修复：`ensure_period` 对逗号/顿号结尾做**替换**而非追加（E 盘运行版 + F 盘源同步）；新增 `tests/test_punct_normalization.py` 11 用例回归，全量 80 passed。修复后重跑 parse+fetch+TTS+render，narration.json 双标点计数 0。
- **环境事实登记**：`skills/todayaihot` 已是**实体目录而非 junction**，且与 `<WORKBUDDY_DATA>/skills/todayaihot` 已分叉（E 盘含 10-21 残句修复 audit_spoken_clause，F 盘源为旧版无此函数；E 盘 SKILL.md 5514 字节 vs F 盘 44155 字节）。两处各自维护，修改需同步两份。
