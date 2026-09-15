# todaynew 项目交接说明

## 项目背景
每日 AI 热点新闻短视频自动化项目（todaynew）。工作流：抓取每日 AI 新闻 → 生成逐字稿与配音 → Remotion 渲染 9:16 竖屏成片，输出到 `out/YYYY-MM-DD/`。

## 视频登记

### 自动登记（2026-09-03）
- 日期：2026-09-03
- 主题：每日 AI 头条（5 条精选：通义千问发布 Qwen3.8-Max-0、Cursor 推出 Self-Hoste、Git Hub 披露 Copilot 四…）
- 简介：2026-09-03 5 条 AI 头条一分钟速览
- 主视频路径：`out/2026-09-03\每日ai热门新闻-2026-09-03.mp4`
- 状态：渲染完成（1080×1920 @30fps，32.8s，10.4MB，音轨正常）
- TTS：edge-tts，align=auto，5 条/11 句
- 封面：`out/2026-09-03/covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏）
- 章节：`out/2026-09-03/chapters.json`（7 条）
- 发布物料：`out/2026-09-03/publish.md`（标题×3 / 话题标签 / 简介 / 置顶评论）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）

### 封面缺陷排查与修复（2026-09-14 23:00，用户指令「排查并修复，不需要重新发布视频」）
- 现象：当日三平台发布所用封面**不是 video-upload skill 的 codebase-style 大字封面**，而是成片首帧标题卡的裁切图——无副标题、无黄胶囊、无署名、下半幅留白；体积 52~82KB，对照 09-12 大字封面 173~221KB 明显偏小
- 根因（代码级确证）：
  1. `todayaihot` 流水线**不产封面**（已复核其脚本与 SKILL.md），封面本应由 `video-upload/scripts/prepare_covers.py` 在 codebase-style 大字模板上重绘；
  2. 执行时先用 `ffmpeg` 从 `first_frame.png` 裁出 `cover_3x4/4x3/16x9.jpg`，再以 `--cover-3x4 / --cover-4x3 / --cover-16x9 / --cover-douyin` 传入 `publish_all.py`；
  3. `publish_all.py::ensure_covers()` 的 `candidates = {"3x4": args.cover_3x4 or outdir/"cover_3x4.jpg", ...}` —— 传入文件已存在 → `missing=[]`；其 mtime（16:09）晚于 `prepare_covers.py`（09-07）→ `stale=[]` → `need_regen=False`，**自动大字重绘被完全短路**；`resolve_douyin_cover()` 又因 `--cover-douyin` 属第一优先级而直接沿用该图；
  4. 全程**无任何告警**（静默降级），故直到事后人工核对才发现。直接诱因是原自动化指令写着「封面：优先用 out/<日期>/ 下已有封面图；没有则由 video-upload skill 用视频首帧生成或直接使用首帧」，与 SKILL.md 第 4 步「所有平台封面都按大字模板重绘，不直接裁切原图」相互冲突
- 修复（三层，均已完成）：
  1. **本地封面重绘**：用 `prepare_covers.py` 重出 `out/2026-09-14/covers/` 的 `cover_3x4.jpg`（1080×1440）/ `cover_4x3.jpg`（1440×1080）/ `cover_16x9.jpg`（1920×1080）；已 Read 目检确认副标题「编程模型排行·Agent密钥被窃」未被左右裁切。旧首帧裁切图移入 `out/2026-09-14/covers/_firstframe_fallback/` 留档
  2. **skill 加固**（`C:\Users\Administrator\.workbuddy\skills\video-upload\` → 符号链接至 `E:\code\social-auto-upload\skills\video-upload\`，单一真源）：
     - `SKILL.md` 第 4 步新增硬规则——除用户提供现成封面外**严禁传 `--cover-*`**（会短路自动重绘且无告警），改传 `--main-title/--subtitle/--tag/--pill/--author`，并给出发布日志自检口径；新增排障章节「封面静默降级：传了 `--cover-*` 导致大字重绘被跳过」
     - `scripts/publish_all.py::ensure_covers()` 增加静默降级告警：命中「显式 `--cover-*`（含 `--cover-douyin`）且本次未重绘」时打印 `⚠️ 显式封面 [...] 已生效，本次跳过自动大字重绘`，把无声故障变为可见
  3. **自动化指令修正**：`automation-1777523241910`（每日 AI 新闻推送）第六步重写——封面升级为硬要求（必须大字重绘、严禁首帧裁切/FFmpeg 垫底）、补齐完整发布命令模板（以 `--main-title/--subtitle/--tag/--pill/--author` 取代 `--cover-*`）、加入发布日志自检与可选 `--force-regen`、并标注 `todayaihot 不产封面` 以免重复踩坑
- 只读验证证据（`--dry-run`，未发布任何内容）：
  - 正确用法：「只传文字字段」→ `[publish] 抖音封面（重绘 3:4 大字版）: .../covers/cover_3x4.jpg`（无告警）
  - 错误用法复现：「显式 `--cover-douyin` 指向首帧裁切图」→ 新增告警如期打印，随后才是「抖音封面（显式指定）」
- 线上状态：当日已发布的三条（B站 `BV1ffYk6BEuW`、视频号、抖音 21:02 补发稿）**封面仍为旧图**；本次按用户要求**未重新发布**。抖音支持发布后改封面（每作品限 5 次，用 `update_douyin_cover.py`），B站/视频号不支持改封面
- **线上封面修正结果（抖音，2026-09-14 23:48–23:50，用户指令「只改封面，不重新发布视频」）**：✅ **成功**
  - 执行时间：23:47 起（**先做并发检查**：`logs/douyin.log` 末条 23:40:06，距当时 6.8 分钟 > 5 分钟窗口，判定无并发冲突，未推迟）；23:49:41 保存成功，23:49:48 线上核验通过
  - 目标对象：抖音 `douyin1`，作品「0914AI头条：Agent密钥被窃·编程模型实测排行」（21:02:53 发布，合集「每日全球AI大事」），管理页关键词 `0914AI头条`（唯一匹配，第 1 步已 grep 到 21:02:53.095「视频发布成功」记录）
  - 结果：抖音线上封面**已替换为大字模板重绘版 3:4（1080×1440）**——目检确认含「每日AI头条 9.14」三色渐变大字 + 副标题「编程模型排行·Agent密钥被窃」+ tag「每日全球AI大事」+ 黄胶囊「AI日报」+ 署名「翻奇兽AI」；旧的成片首帧标题卡样式（`DAILY AI DIGEST` / `2026-09-14 周一` / 「今日要闻」、下半幅留白）已下线
  - 核验截图：新封面 `out/2026-09-14/verify/cover_fix/online_cover_after.jpg`；旧封面比对 `out/2026-09-14/covers/_firstframe_fallback/cover_3x4.jpg`；流程留档 `dialog_open.png` / `cover_updated.png` / `after_submit.png`
  - 修改次数消耗：**1 次**（首轮脚本固定 5s 等待不足，未命中卡片即退出，**崩溃于「提交修改」之前不消耗配额**；重试一次即走通「编辑作品 → 编辑封面 → 上传 → 完成 → 提交修改」全链路）。**剩余 4 次**
  - 未改动项：标题 / 描述 / 话题 / 合集 / 章节 / 视频本体**均未触碰**，未重新发布；B站 `BV1ffYk6BEuW` 与视频号封面（平台不支持在线改封面）**仍为旧图**，本次按约束未处理
  - 附带修复：`skills/video-upload/scripts/update_douyin_cover.py` 查找「编辑作品」按钮由「固定等待 5s 后一次性查找」改为**轮询重试（最多 8 轮，每轮滚动 1500px）**，并在失败分支补 `fail_no_edit_btn.png` 截图取证（原失败路径直接 return，无任何现场证据）

### 历史登记（2026-09-12）
- 主题：每日 AI 热点新闻（7 条要闻：OpenAI 修复 Codex/GPT-6 Astra 质量问题并重置用量、DeepSeek V4.1 Flash 实测降价与 9/14 强制路由、litelm 开源 2900 行精简模型路由内核、云端 200+ 并发 Agent 三层协作架构、CUDA vLLM 领先 AMD 两天/每美元性能最多差 42 倍、6TB 模型中转站日志泄露 19 家企业凭证、吴恩达 AI 工程能力图谱四项能力）
- 主视频路径：`out/2026-09-12/每日ai热门新闻-2026-09-12.mp4`，1080×1920 @30fps，54.6s，20.2MB
- 发布结果：抖音✓ / B站✓（BV1xCY96EEtc）/ 视频号✓

### 历史登记（2026-09-11）
- 主题：每日 AI 热点新闻（7 条要闻：OpenAI Agents API 公测、Cursor Projects 协调者+数千子智能体、GPT-Live-1 全双工语音 API、Shopify 从 React Native 迁回 Swift/Kotlin、Cognition Devin 完成 RSA-260 因式分解、Stanford/Together AI 提出 Intelligence per Watt、小米开源 CocktailASR-1）
- 主视频路径：`out/2026-09-11/每日ai热门新闻-2026-09-11.mp4`，1080×1920 @30fps，46.7s，22.5MB
- TTS：edge-tts，音色 `zh-CN-YunxiNeural`
- 封面：`out/2026-09-11/covers/`；章节兜底数据：`work/chapters_2026-09-11.json`
- 发布结果：抖音✓（16:34，合集「每日全球AI大事」）/ B站✓（API 核验「开放浏览」，tid 231）/ 视频号✓（16:36，短标题「911AI头条速览」、4:3 封面失败为已知非致命告警）
- 核验记录：抖音管理页截图受「置顶作品」排序影响未命中（`out/2026-09-11/verify/douyin_manage.png`），判定为核验误报
- 发布中断与重发说明：16:13 首次发布因后台任务句柄丢失被中断；核验无重复后于 16:26 前台重发成功

### 历史登记（2026-09-10）
- 主题：每日 AI 热点新闻（7 条要闻：DeepSeek-V4.1-Flash 发布（552B MoE/1M 上下文/Codeforces 3471）、Raschka 解析 GPT-6 Astra 架构、Mistral 用 AI Agent 迁移 4 万行 Fortran 77 到 C++、NSA/FBI/CISA 指控六家中国 AI 公司蒸馏、月之暗面 Kimi 企业合作伙伴计划、Meta A-MLE 自主智能体跑通 ML 迭代、面壁 WhisperTown 全本地多智能体社区）
- 简介：2026-09-10 七条 AI 头条一分钟速览，覆盖开源模型性价比突破、编码 Agent 落地实践、企业级 Agent 生态与行业合规风险
- 主视频路径：`out/2026-09-10/每日ai热门新闻-2026-09-10.mp4`
- 状态：渲染完成（2026-09-10 17:53，1080×1920 @30fps，56.9s，21.8MB，音轨正常 aac 48kHz 双声道）
- TTS：**edge-tts，音色 `zh-CN-YunxiNeural`**（2026-09-10 定版：GPT-SoVITS 英文发音不准，已把 skill 默认后端切回 edge 并换云希音色；`tts_backend.py` EDGE_VOICE 默认值已改，可用 `TTS_EDGE_VOICE` 覆盖）。12 句全部 `timing_src=word`，逐字字幕与配音严格对齐（末字时间 ≈ 0.9×句长）
- 封面：`out/2026-09-10/covers/cover_3x4.jpg`（大字版「每日AI头条 9.10 / DeepSeek开源新模型·Kimi企业伙伴计划 / 每日全球AI大事 / 翻奇兽AI」）、`cover_16x9.jpg`
- 章节兜底数据：`work/chapters_2026-09-10.json`（9 条，00:00 起按句切）
- 发布结果（2026-09-10 17:55 / 18:00）：抖音✓（17:55，合集「每日全球AI大事」、重绘大字封面✓、自主声明「内容由AI生成」✓、章节要点弹窗未出现为已知非致命告警）/ B站✓（17:56，tid 231）/ 视频号✓（18:00，管理员扫码重登后补发成功，3:4 竖版封面✓、短标题「910AI头条速览」✓、4:3 横版封面设置失败为已知非致命告警）
- 新闻源：`G:\Obsidian仓库\AI知识库\每日AI热点资讯\AI新闻推送_2026-09-10.md`
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
- 三平台均已发布完成，无遗留阻塞项。

### 历史登记（2026-09-09）
- 主题：每日 AI 热点新闻（7 条要闻：OpenAI 求解 Navier–Stokes 千禧年难题、蚂蚁百灵 Ling-3.0-flash-VL 开源、Anthropic Claude Platform 降本三方法、ChatGPT Images 2.5、Dwarkesh 数据vs模型贡献实验、Runway Adobe 插件、DeepSeek 科创板 IPO）
- 主视频路径：`out/2026-09-09/每日ai热门新闻-2026-09-09.mp4`，1080×1920 @30fps，48.8s，19.5MB
- 发布结果：抖音✓ / B站✓ / 视频号✓

### 历史登记（2026-09-08）
- 主题：每日 AI 热点新闻（7 条要闻：Spotify Claude Code 架构、阿里 QoderWake 1.0、MiniCPM5 开源、7 模型自主经营实测、Reducto r-1、Mistral 融资、Anthropic 算力协议）
- 主视频路径：`out/2026-09-08/每日ai热门新闻-2026-09-08.mp4`，时长 56.4 秒，1080×1920
- 发布结果：抖音✓（合集「每周Github热门项目盘点」）/ B站✓（tid 231）/ 视频号✓（原创审核中）
- 封面：`out/2026-09-08/covers/cover_3x4.jpg`；章节兜底数据 `out/2026-09-08/chapters.json`

## 当前状态（2026-09-08）
- Git 仓库已初始化，远端：`git@github.com:weike123/todaynew-wk.git`（SSH，账号 weike123）
- 默认分支 `main`，已推送首个提交 `42d43d2`
- 入库内容：`.gitignore` + `remotion/` 源码与配置（共 15 个文件，约 3.9k 行）
- 09-08 成片已产出并通过校验（1080×1920，56.4s，音轨正常）

## 忽略策略（.gitignore）
已排除：
- `AI新闻推送_*.md` —— 每日新闻简报产物
- `out/`、`remotion/out/` —— 渲染输出（mp4 等）
- `remotion/public/audio/`、`remotion/public/images/`、`work/`、`*.wav`、`*.mp4` —— 每日重建的素材与中间产物
- `node_modules/`（751M）、`*.zip`（skills/todayaihot.zip 207M）、`skills/todayaihot` 符号链接
- `.tmp/`、`.workbuddy/`（本地记忆与自动化配置，属私有数据）

## 进度与卡点
- 卡点：无。
- 注意：本环境下 `git fetch` 首次创建 `refs/remotes/origin` 目录时会被静默拦截，导致 `git status` 显示 `[gone]`。已手动创建该目录并写入 ref 修复。若后续再出现，执行：
  `mkdir -p .git/refs/remotes/origin && git fetch origin`

## 下一步计划
- 无既定下一步；如需提交新内容：`git add -A && git commit -m "..." && git push`
