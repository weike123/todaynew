# todaynew 项目交接说明

## 项目背景
每日 AI 热点新闻短视频自动化项目（todaynew）。工作流：抓取每日 AI 新闻 → 生成逐字稿与配音 → Remotion 渲染 9:16 竖屏成片，输出到 `out/YYYY-MM-DD/`。

## 视频登记

### 自动登记（2026-10-14）
- 日期：2026-10-14
- 主题：每日 AI 头条（7 条精选：Gemini 4 Argon 1M 上下文、Anthropic 自研 Scion 替代 Git、Argon 无人值守优化 ADK 20 万行、LangChain langchain-scaledown、Liquid AI LFM2.5-24B-A2B、XBOW Chrome 漏洞赏金、RTX Spark 笔记本上市）
- 简介：2026-10-14 7 条 AI 头条一分钟速览
- 主视频路径：`out/2026-10-14\每日ai热门新闻-2026-10-14.mp4`
- 状态：已发布（成片经 BGM 闪避混音兜底重混，46.6s，峰值 -1.50 dBFS；QA 抽帧 8 帧目检：7 条配图实拍互不重复（原文 5 / Pexels 2 / 缺失 0）、KTV 黄白字幕正常）
- TTS：edge-tts（云希），align=auto，7 条/16 句；过程故障：edge 429 限流（首跑 gen_tts 失败，重试成功）；渲染 concurrency=2 时 Chrome 内存不足失败，降为 1 成功
- 封面：`out/2026-10-14/covers/`（3:4 竖版 / 16:9 宽屏，大字模板重绘 --force-regen）
- 章节：`out/2026-10-14/chapters.json`（9 条，真实条目标题已回写）
- 发布结果（2026-10-14 16:15）：抖音✓（合集「每日全球AI大事」+ 重绘 3:4 大字封面，章节弹窗未出现属已知非致命）/ B站✓ `BV1JBpC61EwR`（审核中，tid=231）/ 视频号✗ cookie 失效（tencent/tencent1 code=1，无人值守无法恢复，需管理员扫码后单平台补发）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）

### 自动登记（2026-10-13）
- 日期：2026-10-13
- 主题：每日 AI 头条（7 条精选：微软发布自研芯片 Maia 300，明年、Epic Games 转向 AI 先行开、Vapi 自研 AI 代码审查机器人，P…）
- 简介：2026-10-13 7 条 AI 头条一分钟速览
- 主视频路径：`out/2026-10-13\每日ai热门新闻-2026-10-13.mp4`
- 状态：已发布（成片经 BGM 闪避混音兜底重混，51.9s，峰值 -1.50 dBFS；QA 抽帧 9 帧目检：7 条配图实拍互不重复、KTV 黄白字幕正常）
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
- 状态：渲染完成（1080×1920 @30fps，50.5s，17.1MB，音轨正常）
- TTS：edge-tts，align=auto，7 条/14 句
- 封面：`out/2026-10-12/covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏）
- 章节：`out/2026-10-12/chapters.json`（9 条）
- 发布物料：`out/2026-10-12/publish.md`（标题×3 / 话题标签 / 简介 / 置顶评论）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
- 发布结果（2026-10-12 17:00 执行）：B站 ✓ `BV1bip96oEHa`（开放浏览，tid=231）／视频号 ✓（3:4 封面成功、4:3 横版跳过属已知非致命，短标题「每日AI头条1012」）／抖音 ✓（17:14 补发成功，合集「每日全球AI大事」+重绘 3:4 大字封面+AI声明，章节要点弹窗未出现属已知非致命；故障链：cookie 间歇失效→patchright chromium-1208 缺失→重装 20 分钟→login 复用本机会话刷新 cookie→单平台补发一次成功）
- TTS 修复记录：edge 后端 403 硬故障（微软 2026-10 起将合成 WS 端点迁移至 api.msedgeservices.com，旧 host 大面积 403，PR rany2/edge-tts#491 未发版），已本地 patch `site-packages/edge_tts/constants.py`（WSS_URL 换新端点 + token 以 Ocp-Apim-Subscription-Key 参数传递）与 `drm.py`（locale 无关日期解析）；备份 *.bak_1012；升级 edge-tts 时补丁会被覆盖需重打
- 成片修正：BGM 闪避混音流水线失败，已用 `work/audio_fix_1009.py` 兜底，52.0s、峰值 -1.50 dBFS
- QA：抽帧 10 帧目检，7/7 实拍配图互不重复、KTV 黄白分段正常、无文字卡


### 自动登记（2026-10-11）
- 日期：2026-10-11
- 主题：每日 AI 头条（7 条精选：Anthropic 向白宫通报智能体失控、Open AI 智能体逃逸沙箱入侵 Hu、Open AI 失准报告：模型绕过限制并…）
- 简介：2026-10-11 7 条 AI 头条一分钟速览
- 主视频路径：`out/2026-10-11\每日ai热门新闻-2026-10-11.mp4`
- 状态：渲染完成（1080×1920 @30fps，55.5s，17.0MB，音轨正常）
- TTS：edge-tts，align=auto，7 条/15 句
- 封面：`out/2026-10-11/covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏）
- 章节：`out/2026-10-11/chapters.json`（9 条）
- 发布物料：`out/2026-10-11/publish.md`（标题×3 / 话题标签 / 简介 / 置顶评论）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
- 发布结果（2026-10-11 16:12 人工执行）：抖音 ✓（合集「每日全球AI大事」，重绘 3:4 大字封面，章节要点弹窗未出现属已知非致命）／B站 ✓ `BV1TZpE6dEpV`（审核中，tid=231）／视频号 ✗ cookie 失效（tencent/tencent1 code=1，需管理员微信扫码重登后补发）
- 成片修正：流水线 BGM 闪避混音再次失败（精简 ffmpeg 缺 filter_complex），已用 `work/audio_fix_1009.py` 兜底混入 kulakovka-chill-house BGM，成片 57.05s、峰值 -1.50 dBFS
- QA：抽帧 9 帧目检，7/7 实拍配图（md5 互不重复）、KTV 黄白分段正常、无文字卡


### 自动登记（2026-10-10）
- 日期：2026-10-10
- 主题：每日 AI 头条（7 条精选：Claude 管理智能体上线动态工作流，、阿里 Qoder 上线 Fast 模式：、Prime Agent 用 Rust 重…）
- 简介：2026-10-10 7 条 AI 头条一分钟速览
- 主视频路径：`out/2026-10-10\每日ai热门新闻-2026-10-10.mp4`
- 状态：渲染完成（1080×1920 @30fps，51.4s，16.7MB，音轨正常）
- TTS：edge-tts，align=auto，7 条/15 句
- 封面：`out/2026-10-10/covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏）
- 章节：`out/2026-10-10/chapters.json`（9 条）
- 发布物料：`out/2026-10-10/publish.md`（标题×3 / 话题标签 / 简介 / 置顶评论）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
- **发布结果（2026-10-10 16:25–16:27，前台一次成功、无重发无重试）**：**抖音✓**（合集「每日全球AI大事」、自主声明「内容由AI生成」✓、重绘 3:4 大字封面✓（`--force-regen`，日志命中「重新派生封面」「抖音封面（重绘 3:4 大字版）」）；章节要点弹窗未出现＝已知非致命）/ **B站✓**（`BV1yupv6YEY6`，tid 231，API 核验「开放浏览」）/ **视频号✓**（3:4 竖版封面✓、短标题 13 字；4:3 横版封面设置失败＝已知非致命告警）
- 标题：`每日AI头条10.10：Claude千级并行、Qoder提速`；封面副标题「Claude 千级智能体并行编排落地」（18 字符）
- **执行坑位记录（10-10）**：
  1. 试跑 parse 两次触发 seen_titles 去重自锁（未改动标题的条目被跨 run 去重掉，仅剩 5 条）→ 复跑前删除 `seen_titles.json` 的 `2026-10-10` 键；口播试算 278 字（parse 阶段），fetch 补要点后成片 51.4s 达标
  2. 配图返工 `work/repair_1010.py`：s4（marktechpost 原文图＝tinyfish「Ambassador Program」推广卡）、s5（NVIDIA 文章头图满屏大字）→ 换 Pexels 实拍（chess strategy / programmer coding），只重跑 render.py（约 4 分钟）
  3. 音频后处理第三次静默失败（同因：精简 ffmpeg 缺 sidechaincompress/loudnorm）→ 复用 `work/audio_fix_1009.py`，成片峰值 -1.50 dBFS / RMS -21.26 / 51.39s
  4. 配图 QA：7/7 实拍（原文 2→返工后 Pexels 7 / 缺失 0），md5 互不重复；抽帧 f3/8/13/19/26/33/40/46 + r22/28/31/37 目检，KTV 黄白分段正常
- 新闻源：`<NEWS_DIR>\AI新闻推送_2026-10-10.md`


### 自动登记（2026-10-09）
- 日期：2026-10-09
- 主题：每日 AI 头条（7 条要闻：OpenAI 上线 GPT-6.1 Sol Ultrafast（API/Codex/ChatGPT Work，最高 8 倍速，$12/$60 每百万 token，Codex steering 即时生效）、JetBrains 开源编程模型 Mellum2.1（12B MoE/2.5B 活跃，Apache 2.0，高负载吞吐近 Qwen3.5-9B 两倍，后续出 GGUF 与 vLLM MTP）、LLM 把 TypeScript 编译器/检查器/LSP 移植到 Rust（ts-rust，Opus 5.5 两周约 2.4 万美元完成、100% 兼容）、Anthropic 推出 OSS Scanner（最强模型免费为开源项目扫漏洞，报告无人工复核）、Unsloth 联手 Windows 集成 mxc 操作系统级沙箱（MIT，开销约 84ms，Win11 24H2+ 预装）、Google 开源 AQuA 环境质量智能体（五阶段流水线诊断生产 Agent 静默失败）、Zenity 披露 AgentCorruption（一条提示词劫持 AWS 账户内全部 AgentCore 智能体））
- 简介：2026-10-09 七条 AI 头条一分钟速览，聚焦旗舰模型提速、开源编码模型自托管、LLM 移植大型工具链、开源安全审计、Agent 代码执行隔离、Agent 生产质量工程与云端 Agent 默认权限攻击面
- 主视频路径：`out/2026-10-09/每日ai热门新闻-2026-10-09.mp4`（1080×1920 @30fps，**49.2s**，17.4MB；TTS 内容 49.1s / master 47.62s，12 句无 failed_clauses）
- 新闻源：`<NEWS_DIR>\AI新闻推送_2026-10-09.md`
- **执行坑位记录**：
  1. 首轮 run_all 校验 ERROR「口播预估 60.6s 超 60s 硬上限」→ 7 条标题压缩（去「API 与/高负载/用最强模型/操作系统级/账户内」等）后 360 字 ≈ 55.4s，复跑通过；试跑 parse 会写 seen_titles.json 造成去重自锁，复跑前已备份并清除 2026-10-09 键（`work/seen_titles.bak_1009_preparse.json`）
  2. 依赖环境：Python 3.13 的 `bs4`、`websocket-client` 缺失（check_deps 拦截），pip install 后恢复
  3. **音频后处理再次静默失败**（Remotion 精简 ffmpeg 缺 sidechaincompress/loudnorm，与 10-08 同因）→ `work/audio_fix_1009.py`（numpy RMS 闪避 + 峰值 -1.5dBFS + RMS 兜底，wav 头写真实采样率 24k 防 2 倍速，尾部补静音对齐原片 49.195s）；**包络对齐验证：×1.0 相关 0.9935、×2.0 相关 0.0010，无变速**；成片峰值 -1.50 dBFS
  4. **配图返工（repair_1009.py，只重跑 render 1m20s）**：s1 抓到 x.com 来源的 TestingCatalog 卡通吉祥物插画、s4 命中「CYBER SECURITY」字母拼贴照（满屏文字）、s6 抓到 Google 博客「Open Source Announcement」宣传图 → 按语义指定检索词换 Pexels 实拍（data center server racks corridor / padlock security protection keyboard / control room monitoring screens operator）
- 配图：**原文 1 / Pexels 6 / Pixabay 0 / 缺失 0**，7 张 md5 两两不同；抽帧 f2/6/10/14/18/22/26/30/34/38/42/46 目检：7 条正文卡片全部为实拍照片、无文字卡、KTV 字幕黄白分段正常
- 章节：`out/2026-10-09/chapters.json`（9 条，已回写真实简化标题：开场速览/GPT-6.1 Ultrafast 提速8倍/JetBrains 开源 Mellum2.1/LLM 移植 TS 编译器到 Rust/OSS Scanner 免费扫漏洞/mxc 沙箱隔离 Agent 代码/Google 开源 AQuA/AWS AgentCore 漏洞链/结尾互动），`bilibili_chapters.txt` 同步
- 封面：`out/2026-10-09/covers/`（prepare_covers.py 大字重绘 3:4/4:3/16:9，主标题「每日AI头条 10.9」副标题「GPT-6.1提速8倍·Agent安全」19 字符，已 Read 目检 3x4 与 16x9 均未裁切；抖音取重绘大字版别名 cover_douyin_4x3.jpg）；发布前封面门禁「AR 与主标题均通过门禁 · 主标题可见」✓
- 标题：`AI头条10.9：GPT-6.1提速8倍、Agent安全告警`（30 字符，抖音 ≤30 达标）；视频号短标题「AI头条109速览」9 字
- **发布结果（16:27–16:29，前台一次成功、cookie 三平台均 valid、无重试）**：**抖音✓**（16:27:44「视频发布成功」、合集「每日全球AI大事」、AI 声明✓、竖版封面✓；章节要点弹窗未出现＝已知非致命）/ **B站✓**（`BV1eEp46sEwq`，tid 231，API 核验「开放浏览」）/ **视频号✓**（16:28:52「视频发布成功」、3:4 封面✓、短标题 9 字；4:3 封面失败＝已知非致命）
- 阻塞项：无


### 自动登记（2026-10-08，手动补跑）
- 日期：2026-10-08
- 主题：每日 AI 头条（7 条要闻：OpenAI 把 GPT-6 推给 12 亿 ChatGPT 用户并上线 Intelligent UI、Anthropic 发布 Claude Haiku 5.5（每百万 token 输入 0.10 美元 / 输出 0.50 美元）、微软亚研院开源 Agent Lightning v1.0（3500 行 Harnessed Agentic RL）、微软演示 DeepSeek V4 Flash 量化到 1.6 比特 60GB 本地运行、vLLM 详解 DeepSeek V4.1 Flash 优化（Agent 吞吐 5 倍）、Anthropic 为 Claude Max/Team 套餐新增月度 API 额度、OpenAI 开源 math 仓库（722 份数学手稿 + 372 个成果组））
- 简介：2026-10-08 七条 AI 头条速览，聚焦旗舰模型全量开放与智能 UI、小模型分层定价再打 9 折、智能体 RL 训练框架开源、1.6bit 量化让 284B 模型进消费级 PC、vLLM Agent 负载优化、订阅制自带 API 额度、前沿模型数学成果公开
- 主视频路径：`out/2026-10-08/每日ai热门新闻-2026-10-08.mp4`
- 状态：渲染完成（1080×1920 @30fps，**43.97s**，16MB，音轨正常；TTS master 43.88s，14 句无 failed_clauses）
- **本次为手动补跑**：16:00 定时任务已完成第一、二步（抓取 + 写 md + 更新执行记录），第三～六步（render/配图自检/发布）未执行，本次补齐
- TTS：`--backend edge` + `zh-CN-YunxiNeural`（云希），上午 09:40 已生成，本���沿用未重跑
- 配图：**原文 3 / Pexels 4 / Pixabay 0 / 缺失 0**，7 张 md5 两两不同
- 配图返工记录（**新类型：题材完全抓错，四判据全部放行**）：首轮 4 张 `original` 来源配图内容与新闻完全无关——s1 是烤羊腿美食照（GPT-6 新闻）、s3 是亚洲男性证件照（Agent Lightning）、s4 是苹果发布会现场（DeepSeek 量化）、s6 是欧美人证件照（Claude API 额度）。四判据（颜色唯一度/彩色度/主色占比/前3色）只拦文字卡，拦不住「真实照片但题材错」。修复分两步：`work/repair_1008.py`（4 张换 Pexels 实拍）→ `work/requery_1008.py`（s4/s6 因 5/7 张都是机器人观感重复，按语义指定差异化检索词「data center server room hardware」「credit card online payment laptop」重换），均只回写 `narration.scenes[].visual`（**plural `images` 数组 + `image_sizes` 嵌套数组 + `image_source`**）与 `timeline.narration.scenes[].visual`，**只重跑 `render.py`（2m57s）**
- 抽帧目检（f3/8/13/19/24/30/33.5/36/41/43）：7 条正文卡片全部为实拍照片、无文字卡、KTV 字幕黄白分段正常；f36 为 s7→s8 转场空档（标题渐隐），非缺图
- **音频后处理兜底（重要环境问题）**：渲染日志报 `[audio] 后处理失败` —— `render.py` 的 BGM 闪避 + LUFS 链路依赖 `sidechaincompress`/`loudnorm`，而 `common.ffmpeg_path()` 探测只验证 `-filter_complex` 通用能力，Remotion 自带的**精简版 ffmpeg**（`remotion/node_modules/@remotion/compositor-win32-x64-msvc/ffmpeg.exe`）通过了探测却缺这两个滤镜，静默失败并保留原片，导致母版峰值 **-0.21 dBFS**（超用户 ≤-1dB 硬要求）且无 BGM。环境内无完整 ffmpeg 且 pip 装不上（沙箱网络拦截），故用 `work/audio_fix_1008.py` 以 numpy 实现等效链路（RMS 包络闪避 + 峰值限制 + RMS 兜底），并以精简 ffmpeg 支持的 wav 落盘方式解码 BGM（该构建连 `f32le`/`s16le` 的 pipe 复用器都被裁掉）。结果：峰值 **-1.50 dBFS**、BGM 闪避生效、时长 43.97s。原片备份为 `每日ai热门新闻-2026-10-08-noaudiofix.bak.mp4`
- 章节：`out/2026-10-08/chapters.json`（9 条，语义完整短标题）、`bilibili_chapters.txt` 同步；注意标题在 `visual.title`（**不是** scene 顶层字段），scene 顶层只有 `id`/`visual`/`clauses`
- 发布物料：`out/2026-10-08/covers/`（prepare_covers.py 大字重绘 3x4/4x3/16x9，主标题「每日AI头条 10.8」副标题「GPT-6全量开放·Haiku降价九成」19 字符，已 Read 目检 3x4 与 16x9 均未裁切）、`chapters.json`、`bilibili_chapters.txt`
- 标题：`AI头条10.8：GPT-6全量开放、Haiku降价九成`（30 字符，满足抖音 ≤30）
- **发布结果（音频修复后重发版，22:14 三平台完成）**：**B站✓**（`BV1pqHX65EMj`，tid 231，审核中）/ **抖音✓**（22:12:00，合集「每日全球AI大事」、AI 声明✓、竖版封面✓）/ **视频号✓**（22:14:21，3:4 封面✓、短标题 12 字；4:3 封面失败＝已知非致命）
- ⚠️ **旧版本（坏音频）仍在线，待用户手动删除**：B站 `BV1fkHD6wEuG`、抖音（19:59 发布的同名视频）、视频号（20:02 发布的同名视频）——三平台第一版音频均为 2 倍速变调（根因见下），用户选择自行在后台删除旧版，本次直接重发未做平台内删除
- **音频事故复盘（本次发布翻车根因，最重要教训）**：首发的视频音频是 **2 倍速变调 + 后半段 19s 静音**。根因是 `work/audio_fix_1008.py` 把 24kHz 的 master.wav 混音样本按 **48kHz 头**写出（wave.setframerate(48000)），人声与 BGM 全部 2 倍速、音调高八度。用能量包络对齐法定位：发布版音轨与母版在 ×2.0 速率下相关 0.714、×1.0 仅 0.13；修复版 ×1.0 相关 **0.995**、全程 8 段 RMS 均匀 -20~-23dB、无静音段。**教训：对 24k 母版做任何重混，输出 wav 头必须写真实采样率（24000），重采样交给 ffmpeg `-ar 48000`；改完音频必须用「包络对齐相关系数」验证速度，不能只看总时长与峰值**（总时长被 -t 参数掩盖、峰值正常，两者都查不出 2 倍速）

- 新闻源：`<NEWS_DIR>\AI新闻推送_2026-10-08.md`

### 历史登记（2026-09-23）
- 日期：2026-09-23
- 主题：每日 AI 头条（7 条要闻：Anthropic 发布 Claude Opus 5.5（成本较 Opus 5 降 40% / AA 智能指数 58 登顶 / 1M 上下文 / Claude Code v2.1.280 设为默认 Opus 模型）、OpenAI 发布 GPT-6 Sol 与 Luna（API 价格砍半，Sol $2/$10、Luna $0.10/$0.50，并升级提示词缓存最高 90% 折扣）、Hugging Face transformers 支持直接加载 GGUF 量化模型、OpenRouter 推出 Batch API 批量推理半价（70+ 模型）、Nokia 开源 AnyJev 免训练决策库、Epoch AI 测算同等性能 AI 成本每季度降约 47%、Rogo 创始人指智能体持久记忆卡在 compaction）
- 简介：2026-09-23 七条 AI 头条一分钟速览，聚焦两大旗舰模型同日发布与降价、本地推理（GGUF）与批量推理降本、免训练决策模型替代 prompt 分类、每美元智能的季度级下降曲线与企业级 Agent 记忆治理
- 主视频路径：`out/2026-09-23/每日ai热门新闻-2026-09-23.mp4`
- 状态：渲染完成（1080×1920 @30fps，52.5s，21.6MB，音轨正常；TTS 内容 50.9s，14 句全部成功、无 failed_clauses）
- TTS：`--backend edge` + `zh-CN-YunxiNeural`（云希，男声），`--force-tts`，未探测 gptsovits
- 封面：`out/2026-09-23/covers/cover_3x4.jpg`（大字重绘版，主标题「每日AI头条 9.23」副标题「Opus5.5降价·GPT-6砍半」17 字符，已 Read 目检 3x4 与 16x9 均未裁切）；发布日志命中 `[publish] 重新派生封面 →` 与 `[publish] 抖音封面（重绘 3:4 大字版）`，无静默降级
- 章节：`out/2026-09-23/chapters.json`（9 条，已回写真实简化标题替换「第N条」占位）、`bilibili_chapters.txt` 同步回写
- 配图（含返工）：**原文 1 / Pexels 6 / Pixabay 0 / 缺失 0**，7 张 md5 两两不同；抽帧 f3/8/13/19/26/33/40/47/51 目检确认全部为实拍照片（或人物/设备实拍）、KTV 字幕黄白分段正常
- 配图返工记录：首轮 fetch 采用了 3 张原文「文字/插画卡」（s1 Anthropic 官宣大字卡、s3 HF 博客英文插画、s5 MarkTechPost 博客图表头图），四判据未拦截 → 已用 `work/repair_0923.py` 调 `fetch_news.stock_fallback` 换 Pexels 实拍图（software development team ×2、artificial intelligence technology），回写 narration.json + timeline.json 的 `narration.scenes[].visual`，**只重跑 `render.py`（2m19s）**，未重跑 parse/fetch/TTS
- 发布物料：`out/2026-09-23/publish.md`；运行报告 `out/2026-09-23/run_report.json`
- 发布结果（16:26–16:29，前台一次成功、无重发无重试）：**抖音✓**（16:27:11「视频发布成功」、合集「每日全球AI大事」、自主声明「内容由AI生成」✓、重绘 3:4 大字封面✓、竖版封面上传✓；章节要点弹窗未出现＝已知非致命告警）/ **B站✓**（`BV1zdht64ESy`，tid 231，API 核验「开放浏览」）/ **视频号✓**（16:29:17「视频发布成功」、3:4 竖版封面✓、短标题「AI头条923Opus5」12 字；4:3 横版封面设置失败＝已知非致命告警）
- 标题：`AI头条9.23：Opus5.5降价、GPT-6砍半`（26 字符，满足抖音 ≤30）
- 阻塞项：无。三平台 cookie 本次均 valid（`douyin1` / `bili1` / `tencent1`），无需扫码
- 待确认：无
- 新闻源：`<NEWS_DIR>\AI新闻推送_2026-09-23.md`

#### 执行备注（2026-09-23 新经验）
1. **原文配图是「文字卡/插画卡」的重灾区**：今日 4 条原文图里 3 条是官宣大字卡与博客图表/插画头图（Anthropic、HF、MarkTechPost），全部未被 `looks_like_text_image()` 四判据拦住 —— 再次印证四判据只是高置信过滤器，**出片后抽帧目检必须逐张确认「是不是实拍照片」**，不能只看日志的「缺失 0」。
2. **最小化返工链路已沉淀为脚本** `work/repair_0923.py`：登记保留图指纹 → 仅对被替换条目调 `fetch_news.stock_fallback(item_id, title, sess, images, sizes)` → 回写 `narration.json` 与 `timeline.json` 的 **`narration.scenes[].visual`**（注意：timeline 顶层的 `scenes[]` 只有 id/clauses，`visual` 在 `timeline.narration.scenes[]` 内，Remotion 通过 `import timeline from "../../work/timeline.json"` + `tl.narration` 取值）→ 只重跑 `render.py`，约 2 分 20 秒完成。
3. **G 盘 md 被外部同步回写**：本次 6 处标题 Edit 仅保留 2 处（09-22 已出现同款问题）。改稿后必须回读校验；若反复被回写，以「运行时刻文件内容」为准并确保字数落在 325~390 区间。
4. 口播字数控制：写稿先按标题原始字符数估算，本次 7 条标题合计 363 字（含开场钩子与结尾）→ 实测 TTS 50.9s、成片 52.5s，落在 50–60s 目标区间。

### 历史登记（2026-09-22）
- 日期：2026-09-22
- 主题：每日 AI 头条（7 条要闻：小米开源 MiMo-V2.6 全模态系列（Pro 登顶开放权重智能指数 46 / Code Arena WebDev 约第 10、开源第 3 / MIT 许可）、xAI 发布 Grok 4.7（智能体编码升至全球第三 / AA Intelligence Index 46 / 每百万 token 输入 2 美元输出 6 美元）、NVIDIA 等发布 SoL-Pi（把开源 Pi 编码 Agent 的 token 流量降低 44.7%~49.0% / API 成本降约 33%）、xAI 工程师 Lauren Tan 复盘单月合入 2500 个 PR 的智能体工程方法并开源插件 pstack、Linear 重构 CI 应对 AI 编码验证瓶颈（PR 等待 6 分钟降至 5 分钟出头）、Jev 与 SemIf 等专用决策器接管 if-then 判断（分类成本降 76~209 倍）、Kimi 发布 Kimi Code Desktop 1.0 官方桌面客户端）
- 主视频路径：`out/2026-09-22/每日ai热门新闻-2026-09-22.mp4`（1080×1920 @30fps，54.3s，24.1MB）
- 发布结果：**抖音✓** / **B站✓**（`BV16Rhj6bE7E`，tid 231）/ **视频号✓**（16:32:41 成功、3:4 封面✓；4:3 封面失败＝已知非致命）
- 标题：`AI头条9.22：MiMo开源、编码Agent省token`（29 字符）
- 备注：7 条配图全部走 Pexels 兜底（原文图全判文字图），其中 4 条命中同一检索词「developer coding laptop」，画面同质化

### 历史登记（2026-09-21）
- 日期：2026-09-21
- 主题：每日 AI 头条（7 条要闻：亚马逊 AWS Bedrock 接入 Kimi K3（2.8 万亿参数开源模型 / 100 万 Token 上下文 / Bedrock 首个支持显式提示缓存的开放权重模型）、阿里云开源 Qwen-Image-2.1（7B 统一文生图与图像编辑、原生透明图、支持 ComfyUI）、开发者反思 MCP 协议应逐步淘汰并转向标准 HTTP 接口、ECDYSIS 按跨任务失败模式训练智能体运行时（arXiv:2609.11677）、企业 AI 可见性危机（Cisco 指数 60% 组织不知员工向 GenAI 发了什么）、阿里云 QwenWork 定时比价智能体自动生成带截图报告、中国 AI 实验室否认「开源将死」称靠推理服务收入分成变现）
- 简介：2026-09-21 七条 AI 头条一分钟速览，聚焦开源模型与云托管接入、图像生成编辑统一模型、Agent 工具链协议选型、Agent 运行时训练方法论、企业 Shadow AI 治理、智能体定时任务范式与开源商业模式之争
- 主视频路径：`out/2026-09-21/每日ai热门新闻-2026-09-21.mp4`
- 状态：渲染完成（1080×1920 @30fps，58.2s，25.0MB，音轨正常；TTS 内容 56.62s，14 句全部成功、无 failed_clauses）
- 封面：`out/2026-09-21/covers/cover_3x4.jpg`（大字重绘版，副标题「Kimi上Bedrock·MCP该淘汰」20 字符）
- 发布结果（16:15–16:18，前台一次成功）：**抖音✓** / **B站✓**（`BV1uMhi6aEZG`，tid 231）/ **视频号✓**（16:17:41 成功、3:4 封面✓；4:3 封面失败＝已知非致命）
- 标题：`AI头条9.21：Kimi上Bedrock、MCP该淘汰`（28 字符）
- 配图返工记录：首轮第 1 条命中 ithome 站内 AWS 博客渐变标题卡（属用户禁止的「文字/海报卡」但未触发像素判据）；已手工换 Pexels「data center server room」实拍图并仅重跑 `render.py` 修复
- 阻塞项：无

### 历史登记（2026-09-20）
- 日期：2026-09-20
- 主题：每日 AI 头条（7 条要闻：阶跃星辰 Step 5 Preview 600B总参/27B激活/1M上下文、Noam Brown 访谈披露 1200 个 Agent 沙箱内串通作弊与 CoT 监控失效、面壁 MiniCPM5-2B 无独显老电脑本地跑 AI 新闻摘要、Alexandr Wang 推荐 Opencode+Muse Spark 1.3、阿里 Qwen3.8-LiveTranslate 实时同传 2.3 秒、Claude 协作分解 896 位 RSA、Databricks CEO 称企业 AI 瓶颈在上下文）
- 主视频路径：`out/2026-09-20/每日ai热门新闻-2026-09-20.mp4`（1080×1920 @30fps，55.4s，23.4MB）
- 发布结果：**抖音✓** / **B站✓**（`BV1HXeq6wEAZ`，tid 231）/ **视频号✗ 未发布**（`tencent/tencent1` cookie invalid，`publish_all.py` 前置校验即中止；后改用 `--platforms douyin,bilibili` 前台一次成功）
- 标题：`AI头条9.20：Step5开源、Agent串通作弊`（26 字符）
- 说明：该视频号失效已于 2026-09-21 自行恢复，后续两日均 valid

### 历史登记（2026-09-18）
- 日期：2026-09-18
- 主题：每日 AI 头条（7 条要闻：GitHub 用 Copilot 智能体把运行时从 TypeScript 全量重写为 83 万行 Rust、Claude Code 重构 Projects 为多线程并行项目、Unsloth 发布 Docker 镜像与桌面版本地零配置跑 500+ 模型、PrismML 三值量化 Bonsai 2 27B、Qwen3.8-Omni-Flash 原生全模态开源音视频降价 98%、Anthropic 用 Claude 四周优化 30 多个开源生物分子模型提速 4 倍、Hacktron 3 人团队不到 3000 美元 token 成本攻破 OpenAI 论坛）
- 主视频路径：`out/2026-09-18/每日ai热门新闻-2026-09-18.mp4`（**修复版，已覆盖首版**）
- 发布结果（修复版重发）：**抖音✓** / **B站✓**（`BV1aKe16vEUC`，tid 231）/ **视频号✓**。
- 首版发布记录（含缺陷，**线上仍并存未被删除**）：抖音✓ / B站 `BV1joey66ELG` / 视频号✓
- 待决策：首版（女声无 KTV）与修复版在三平台并存。视频号可用 `tencent-video-delete` skill 删除首版（不可逆，需白名单确认）；抖音/B站无自动删除脚本。**未经用户确认不得执行删除**。
- 缺陷修复详情见下方「2026-09-18 缺陷修复」段

### 历史登记（2026-09-17）
- 日期：2026-09-17
- 主题：每日 AI 头条（7 条要闻：VS Code 1.138 支持在开发容器内跑智能体并扩展 Codex harness、UC Berkeley HarnessTax 实测换 harness 成功率几乎不变而成本最高差 5 倍、Z.ai 复盘 GLM-5.3 驱动 Infra Agent 两周把推理吞吐提升 3.2 倍、OpenSpec 轻量 AI 编码规范框架兼容 39 个工具、OpenAI 发布模型错位披露框架并公开 6 份 RL 事故报告、Mozilla 91 页报告称开放权重仅落后前沿约 4 个月、Google Research R4T 扩散检索器让查询扇出提速 12 至 20 倍）
- 主视频路径：`out/2026-09-17/每日ai热门新闻-2026-09-17.mp4`（1080×1920 @30fps，51.2s，22.1MB）
- 发布结果：**抖音✓** / **B站✓**（`BV1wfeu6WE9Q`）/ **视频号✓**
- 配图文字卡故障修复（2026-09-17 18:00，用户第三次反馈，明确不重出视频）：根因是 `.env` 缺 `PEXELS_API_KEY` + 原文无可用实拍图 + 旧判别器抓不住「柔和渐变底+大字」；已补 Key、改多源兜底、新增颜色唯一度判据、无配图升为 ERROR 阻断、新增判别器自检脚本（17/17）。**⚠️ 09-17 成片未重出**：中断的 fetch 已清空 `remotion/public/images/`，`work/narration.json` 中 4 条配图引用失效，若要重出必须先重跑 `fetch_news.py`

### 历史登记（2026-09-16）
- 主题：每日 AI 头条（7 条要闻：Gergely Orosz 探访 OpenAI 看 Codex 接管内部研发、Perplexity 自研 CobbleDB 替代 DynamoDB 每年省 1 亿美元、Trail of Bits 拆穿 1Password AI 补丁基准、Salesforce 企业智能体模型 Koa、Arena 图像转网站榜单更新、Astera Labs Leo X 卸载 KV Cache、xAI Grok Build v1.0.33）
- 主视频路径：`out/2026-09-16/每日ai热门新闻-2026-09-16.mp4`，1080×1920 @30fps，59.9s，22.7MB
- 发布结果：抖音✓ / B站✓ / 视频号✓

### 历史登记（2026-09-15）
- 主题：每日 AI 头条（7 条要闻：Anthropic 实测智能体编码把 CI 压垮 25 倍、Luna vs Astra 代码评审成本-精度实测、英伟达等大客户限制前沿模型转自研、Agent-net 开源 Webagent、硅基流动 Hy4 preview、单张 RTX 3090 本地跑 Qwen3.8-27B、飞书×豆包团队共享工作伙伴）
- 主视频路径：`out/2026-09-15/每日ai热门新闻-2026-09-15.mp4`，1080×1920 @30fps，55.4s，25.5MB
- 发布结果：抖音✓ / B站✓（`BV1DCen6AEav`）/ **视频号✗ 未发布**（cookie invalid，需扫码后单平台补发）

### 历史登记（2026-09-14）
- 主题：每日 AI 热点新闻（7 条要闻：karminski 后端 Agentic Coding 排行榜实测、Agent 长任务上下文工程四机制、METR API key 被窃用三周耗 60 万美元、MIT HardFlow 硬约束采样、面壁 CPM for Legal 18 个法律智能体、OpenClaw 热度回落反思、OpenAI/Anthropic/Google 商讨共享前沿 AI 安全标准）
- 主视频路径：`out/2026-09-14/每日ai热门新闻-2026-09-14.mp4`，1080×1920 @30fps，61.7s，29.8MB
- 发布结果：B站✓（`BV1ffYk6BEuW`）/ 视频号✓ / 抖音✓（21:02 单平台补发成功；线上封面已于 23:49 用 `update_douyin_cover.py` 修正为大字重绘版，修改次数消耗 1 次，剩余 4 次）

## TTS 音色规范（硬要求，自 2026-09-10 定版，2026-09-18 复核）
- todayaihot **固定 `--backend edge` + `zh-CN-YunxiNeural`（云希，男声）**，语速 +30%、音量 +50%。
- **不要**默认启用 GPT-SoVITS：其音色注册表 `<GPT_SOVITS_DIR>\voice\cloned_voices.json` 的 `default` 为女声 `zh_female_sophie_uranus_bigtts`（表内三个音色全为 female），且英文术语发音易失真（2026-09-10 用户反馈）。
- 仅当用户当次明确要求克隆音色时才启用 gptsovits，且须先与用户确认参考音频音色/性别。

## 字幕规范（硬要求）
- KTV 逐字字幕依赖 `timeline.json` 的 `clause.chars[].t`，该值必须**相对句首**（与 `Subtitle.tsx` 的 `elapsed = t - c.start` 一致）。
- 自检：句内 `max(chars[].t) ≤ clause.duration`；出片后必须抽「句中时刻」帧目检字幕存在**黄色高亮**（全白即为基准错误）。
- 已知观感问题（未修，待决策）：KTV 字幕 bottom=360 与卡片正文底部存在重叠。

## 封面规范（硬要求，自 2026-09-14 起）
- 必须由 `video-upload/scripts/prepare_covers.py` 的 codebase-style 大字模板重绘，**严禁传 `--cover-*` 参数**（会短路自动重绘且无告警），**严禁用成片首帧裁切或 ffmpeg 垫底**。
- 只传文字字段：`--main-title "每日AI头条 M.DD"` + `--subtitle "≤18~20 字符关键词"` + `--tag "每日全球AI大事"` + `--pill "AI日报"` + `--author "翻奇兽AI"`，并加 `--force-regen` 确保每次重绘。
- 发布日志必须出现 `[publish] 重新派生封面` 或 `[publish] 抖音封面（重绘 3:4 大字版）`；若出现「显式指定」或「视频首帧兜底」即为链路被绕开，需停下修正。
- 副标题固定 64px 不缩放，超过 20 字符会左右被裁，生成后必须 Read 目检。

## 口播时长控制（硬要求）
- `validate_output.py` 用**原始字符数**（含空格、标点）/390wpm 估算时长，硬上限 60s。目标区间：原始字数 325~390（约 50~60s）。
- 每条标题 `_norm` 归一化长度必须 >32，否则会额外追加 22 字要点口播导致超时。
- 试跑 `parse_news.py` 会把当日标题写入 `work/seen_titles.json`，**正式 run_all 前必须清除当日键**，否则触发「去重后无剩余新闻条目」自锁（每次已备份 `work/seen_titles.bak_MMDD.json`）。

### 自动登记（2026-09-24）
- 日期：2026-09-24
- 主题：每日 AI 头条（7 条要闻：Cursor 上线 Rollouts 与 Security Reviewer 两款开发机器人、Anthropic 上线 Claude Marketplace 把插件/智能体/服务伙伴聚合到统一入口、Fireworks Research 发布 Ember-1 比 Kimi K3 少四成 token、Anthropic 公开 Claude 把 claude.ai 提速约 3 倍的冲刺复盘、Google Antigravity SDK 接入本地模型 Gemma 4 26B 26B 完全离线跑智能体、Contrastive-LM 开源 CLM-8B 智能体动作评分比 Jev 快最多 9 倍、OpenAI 把 Daybreak 网络防御计划扩展至乌克兰政府）
- 简介：2026-09-24 七条 AI 头条一分钟速览，聚焦 IDE 内常驻智能体机器人（Cursor）、模型生态商店（Claude Marketplace）、编码 Agent token 降本（Ember-1）、AI 驱动代码现代化标准样本（claude.ai 3 倍提速冲刺）、本地化 Agent 离线推理（Antigravity SDK + Gemma 4）、对比式决策模型（CLM-8B 挑战 Jev/AnyJev）、AI 安全工具纳入外交级援助（Daybreak 扩乌克兰）
- 主视频路径：`out/2026-09-24/每日ai热门新闻-2026-09-24.mp4`
- 状态：渲染完成（1080×1920 @30fps，44.5s，13.8MB，音轨正常；TTS 内容 42.9s，14 句全部成功、无 failed_clauses；流水线耗时 23m17s）
- TTS：`--backend edge` + `zh-CN-YunxiNeural`（云希，男声），`--force-tts`，未探测 gptsovits
- 封面：`out/2026-09-24/covers/cover_3x4.jpg`（大字重绘版，主标题「每日AI头条 9.24」副标题「Cursor开发机器人·Ember-1降本」15 字符，已 Read 目检 3x4 与 16x9 均未裁切）；发布日志命中 `[publish] 重新派生封面 →` 与 `[publish] 抖音封面（重绘 3:4 大字版）`，无静默降级
- 章节：`out/2026-09-24/chapters.json`（9 条，已回写真实简化标题替换「第N条」占位）、`bilibili_chapters.txt` 同步回写
- 配图：**原文 2 / Pexels 5 / Pixabay 0 / 缺失 0**，7 张 md5 两两不同；抽帧 f4/10/17/24/31/38/41 目检确认实拍照片，KTV 字幕黄白分段正常
- 配图返工记录：首轮 s7（OpenAI Daybreak）命中了原文博客 hero 图（黄蓝渐变底 + 居中白字英文「OpenAI extends cyber access to Ukraine for civilian defense」），四判据未拦截（属典型"柔和渐变底+大字"漏判，与 09-21 ithome AWS 博客同模式）→ 已用 Pexels「security-protection-anti-virus-software」实拍图（md5 dc54c29078）替换，回写 narration.json + timeline.json 的 `narration.scenes[].visual.images`/`image_sizes`（**注意：必须用 plural `images: [path]` 数组与 `image_sizes: [[w,h]]` 嵌套数组形态**，singular 字段会被 NewsItem.tsx 忽略）→ **只重跑 `render.py`（4m36s）**，未重跑 parse/fetch/TTS
- 发布物料：`out/2026-09-24/publish.md`；运行报告 `out/2026-09-24/run_report.json`
- 发布结果（17:00–17:01，前台一次成功、无重发无重试）：**抖音✓**（17:01:24「视频发布成功」、合集「每日全球AI大事」、自主声明「内容由AI生成」✓、重绘 3:4 大字封面✓、竖版封面上传✓；章节要点弹窗未出现＝已知非致命告警）/ **B站✓**（`BV18EaA6zE3S`，tid 231，API 核验「审核中」）/ **视频号✗ 未发布**（`tencent/tencent1` cookie invalid，须管理员微信扫码重新登录后再单平台补发：`--platforms tencent`）
- 标题：`AI头条9.24：Cursor开发机器人、Ember-1降本`（30 字符）
- 阻塞项：视频号 cookie 失效，待扫码
- 待确认：无
- 新闻源：`<NEWS_DIR>\AI新闻推送_2026-09-24.md`

## 当前状态（2026-09-24 17:02）
- 2026-09-24 成片已完成抖音 + B站 双平台发布（视频号 cookie invalid 待处理）
- 抖音 / B站 cookie 均 valid；视频号 cookie invalid，需扫码后单平台补发
- 自动化任务 `automation-1777523241910`（每日 16:00）按当前提示词执行正常
- Git 仓库已初始化，远端：`git@github.com:weike123/todaynew.git`（SSH，账号 weike123）；默认分支 `main`
- 注意：`validate_output.py` 对「TTS 静音占位」只报 WARN 不阻断，出片前需人工确认日志中无 `TTS失败→静音`
- 可复用脚本：`work/repair_0923.py`（配图返工：仅换图 + 只重跑 render）
- 2026-09-23 成片已完成三平台发布（抖音/B站/视频号全成功，前台一次通过，无重发无重试）
- 三平台 cookie 均 valid（`douyin1` / `bili1` / `tencent1`）
- 自动化任务 `automation-1777523241910`（每日 16:00）按当前提示词执行正常
- Git 仓库已初始化，远端：`git@github.com:weike123/todaynew.git`（SSH，账号 weike123）；默认分支 `main`
- 注意：`validate_output.py` 对「TTS 静音占位」只报 WARN 不阻断，出片前需人工确认日志中无 `TTS失败→静音`
- 可复用脚本：`work/repair_0923.py`（配图返工：仅换图 + 只重跑 render）

## 忽略策略（.gitignore）
已排除：`AI新闻推送_*.md`、`out/`、`remotion/out/`、`remotion/public/audio/`、`remotion/public/images/`、`work/`、`*.wav`、`*.mp4`、`node_modules/`、`*.zip`、`skills/todayaihot` 符号链接、`.tmp/`、`.workbuddy/`。

## 进度与卡点
- 卡点：无。
- 注意：本环境下 `git fetch` 首次创建 `refs/remotes/origin` 目录时会被静默拦截，导致 `git status` 显示 `[gone]`。若出现，执行：
  `mkdir -p .git/refs/remotes/origin && git fetch origin`

## 下一步计划
- 待用户决策：① 2026-09-18 首版（女声无 KTV）视频是否从视频号/抖音/B站删除；② 是否调整 Remotion 字幕纵向位置以消除与卡片正文的重叠。
- 观察项（非阻塞）：抖音「章节要点」弹窗未出现属已知非致命告警；视频号 4:3 横版封面偶发设置失败属已知非致命告警。
- **配图检索词优化建议（2026-09-22 发现）**：`fetch_news.py` 的 Pexels 兜底检索词按内容分类生成，今日 7 条里有 4 条命中同一检索词「developer coding laptop」，画面同质化。建议按条目标题关键词定制（如 SoL-Pi→"server rack"、Linear CI→"team collaboration office"）或对同一检索词结果做「画面相似度」二阶去重。
- **配图判据改进建议（2026-09-21 发现）**：ithome 站内 AWS/厂商博客「柔和渐变底 + 大字」标题卡仍能通过 `looks_like_text_image()` 四判据。建议为 `references/imgsamples/text/` 补充此类样本并考虑提高颜色唯一度阈值 / 增加「大面积浅色底 + 居中大字」判据。
- 如需提交新内容：`git add -A && git commit -m "..." && git push`
