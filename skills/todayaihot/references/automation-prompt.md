# 定时任务提示词模板（每日 AI 头条 · 无人值守）

本文件是 `todayaihot` skill 的**可移植定时任务提示词**：clone 仓库后，任何支持定时任务 / 自动化 / cron 的 agent（WorkBuddy、Claude Code、Codex、Cursor 等）都能照着它把「采集 → 写稿 → 出片 → 发布」整条链路跑成每日任务，不依赖本机路径。

---

## 一、怎么用（三种方式，任选其一）

**方式 A · 一句话交给 agent（推荐）**

> 读取 `<PROJECT_ROOT>/skills/todayaihot/references/automation-prompt.md`，按下表把占位符替换成本机路径，然后用「提示词正文」创建每天 16:00 执行的定时任务。

agent 会调用自己的调度能力建任务；WorkBuddy 中等价于：

```
automation_update(mode="create",
  name="每日 AI 新闻推送",
  scheduleType="recurring",
  rrule="FREQ=DAILY;BYHOUR=16;BYMINUTE=0",
  prompt=<提示词正文，占位符已替换>)
```

**方式 B · 手动建任务**：把「提示词正文」整段贴进定时任务输入框，先自行替换占位符。

**方式 C · 只跑一次**：不建定时任务，把正文丢给 agent 手工执行一遍即可。

## 二、创建前必须替换的占位符

| 占位符 | 含义 | 示例 |
|---|---|---|
| `<PROJECT_ROOT>` | 本仓库克隆位置 | `D:/code/todaynew` |
| `<NEWS_DIR>` | 每日新闻 md 的落盘目录（任意可写目录） | `D:/news` |
| `<PYTHON>` | 已装 `requirements.txt` 依赖的解释器绝对路径 | `python` / `C:/Python313/python.exe` |
| `<SOCIAL_AUTO_UPLOAD_DIR>` | `social-auto-upload` 仓库（发布环节，可选） | `D:/code/social-auto-upload` |
| `<GPT_SOVITS_DIR>` | GPT-SoVITS 目录（仅克隆音色时需要，可留空） | `D:/code/GPT-SoVITS` |
| `<AUTOMATION_MEMORY_DIR>` | 执行摘要写入目录（可留空，留空则跳过该步） | `<PROJECT_ROOT>/.workbuddy/memory/automations` |
| `%USERPROFILE%\.workbuddy` | WorkBuddy 数据目录，保持原样，不要写死盘符 | — |

> 约束：**只替换占位符，不要改动提示词正文的判定规则**（时长、配图、封面、发布顺序都是踩坑后固化下来的）。

## 三、创建前的环境前置检查

```bash
cd <PROJECT_ROOT>/skills/todayaihot
<PYTHON> scripts/check_deps.py          # Python 依赖 / ffmpeg 滤镜链 / node 探针
<PYTHON> -m pytest tests/ -q            # 期望 80 passed
```

- `.env` 中 `PEXELS_API_KEY` 与 `PIXABAY_API_KEY` **必须都非空**，否则配图兜底静默失效、画面退化成文字卡。
- BGM 闪避混音需要**完整 ffmpeg**（`asplit/aloop/sidechaincompress/amix/loudnorm`）；用 `TODAYAIHOT_FFMPEG` 指向完整构建，或加 `--no-bgm`。
- 首次渲染会自动下载 Chrome Headless Shell，需要网络。
- 发布环节依赖外部 `social-auto-upload`；不想自动发布就删掉正文第六步。

---

# 提示词正文（以下整段即定时任务 prompt）

每日聚焦 AI 领域与技术开发者强相关的重要动态，重点覆盖以下方向：

1. AI Coding / 开发效率工具：大模型编程助手、代码生成/优化/调试工具、IDE 插件、DevOps 自动化工具的更新与实践
2. AI 智能体（Agent）与大模型应用：开源智能体框架更新、RAG 知识库治理、多模态融合、企业级 AI 平台的落地案例与技术方案
3. 技术栈相关：Java/Python 生态下的 AI 应用实践、本地大模型部署/优化（如 Ollama、开源模型更新）、向量数据库（Milvus/Neo4j）相关进展
4. 行业关键动态：头部厂商技术发布、开源项目更新、对开发者/企业有实际影响的政策或技术趋势

## 环境硬规则（路径可移植，禁止写死本机盘符）

- WorkBuddy 数据目录位于 `%USERPROFILE%\.workbuddy`；若它是 junction 指向其他磁盘，**一律通过这一层访问**，不要去猜真实盘符，也不要在别处新建重复目录。
- 运行时实际路径按目录通配查找，不要写死版本号：Node `%USERPROFILE%\.workbuddy\binaries\node\versions\<版本>\node.exe`；Python venv `%USERPROFILE%\.workbuddy\binaries\python\envs\<名称>\Scripts\python.exe`；PortableGit `%USERPROFILE%\.workbuddy\binaries\PortableGit\versions\<版本>`。
- 本仓库根目录记为 `<PROJECT_ROOT>`；新闻落盘目录记为 `<NEWS_DIR>`；发布脚本目录记为 `<SOCIAL_AUTO_UPLOAD_DIR>`。

## 数据源（固定使用 AIHOT，两个入口配合）

**域名**：一律使用 `https://aihot.news`。旧域名 `aihot.virxact.com` 自 2026-10-31 起仅做跳转，不得再写入任何命令或链接。

**入口 A（精选，质量基准）**：`curl -sS "https://aihot.news/api/v1/dailies/latest"`

- 返回 `report.sections`（精选条目，通常 3 条左右）与 `flashes`（补充快讯）。
- 若 latest 返回 404：只查询一次 `curl -sS "https://aihot.news/api/v1/dailies?limit=7"` 取索引，再用实际日期请求 `curl -sS "https://aihot.news/api/v1/dailies/{YYYY-MM-DD}"`；索引为空则停止。**绝不猜测日期**。

**入口 B（全部 AI 动态，条目池）**：`curl -sS -A "Mozilla/5.0" "https://aihot.news/feed/all.xml"`

- RSS 返回最近 7 天全部动态（约 50 条，`pubDate` 倒序），最前面的若干条即今日窗口条目。
- 入口 A 精选只有 3 条左右，**必须用入口 B 补足条数**：入口 A 全部纳入候选，再从入口 B 靠前条目按上述方向筛选补充，合并去重后选出 **6–7 条**。
- 入口 B 的 `description` 有的只有原文链接。信息不足的条目用 WebFetch 请求 `https://aihot.news/items/{id}` 补齐要点；仍不足则放弃该条、换下一候选。
- 只基于接口/RSS 返回内容总结，**不得用训练记忆补充或伪造条目**，也不得切换其他新闻源冒充 AIHOT。

## 筛选要求

从候选中筛选 **6–7 条**高价值信息（与昨日已推送内容差异化；宁多勿少——成片要求 50–60 秒，少于 6 条时长不达标），每条包含：

- 事件核心内容（一句话概括）
- 关键细节/更新点
- 对开发者/企业的价值与影响（技术落地、效率提升、职业发展维度）

语言精简、按优先级排序，优先可直接参考实践的内容，拒绝纯概念与营销资讯；正文末尾可附 2–4 条补充快讯。

## 执行顺序

### 第一步：输出完整新闻摘要作为正文回复（通知卡片展示源）

最终回复直接输出完整推送内容（全部条目与补充快讯），格式清晰、可直接阅读。

⚠️ 关键约束（直接影响卡片展示）：

1. 最终回复必须以 `# AI 新闻推送 · YYYY-MM-DD` 开头，第一句就是新闻内容本身；
2. **严禁**在正文前输出任何过程性文本（"正在检索""已获取素材""开始执行"等进度描述、思考过程、工具调用说明）——这类文本会被拼进推送正文；
3. 正文总长度 1500–3500 字符，不要为凑长度注水；
4. 检索、写文件、present_files、发布视频等过程说明一律不出现；如需收尾，仅允许一句"文件已生成"。

### 第二步：写入文件

用 Write 工具写入 `<NEWS_DIR>\AI新闻推送_YYYY-MM-DD.md`（当天日期）；目录不存在先用 `mkdir -p` 创建。

条目格式（流水线依赖此结构，必须遵守）：

```
# AI 新闻推送 · YYYY-MM-DD

**1. 标题**
核心：…
细节：…
价值：…
原文：<原文直链>
```

- 每条必须有 `原文：<直链>`（非 AIHOT 链接），fetch 环节靠它抓配图。
- 每条至少写满 核心/细节/价值 三行；英文原文条目也须翻译成中文要点。

### 第三步：更新执行记录（可选）

向 `<AUTOMATION_MEMORY_DIR>` 追加本次执行摘要（仅摘要）。该目录留空则跳过本步。

### 第四步：present_files 展示

调用 present_files 展示第二步生成的 markdown（绝对路径）。

### 第五步：生成 9:16 竖屏成片（todayaihot skill，TTS 固定 edge + 云希）

⚠️ **开跑前必做：配图图库 Key**

`<PROJECT_ROOT>/.env` 中 `PEXELS_API_KEY` 与 `PIXABAY_API_KEY` 必须都非空。缺失会让配图兜底静默失效、画面退化成文字卡（2026-09-16/17 事故根因）。Key 值不得写入任何日志或正文。

**TTS 策略（用户定版）**：固定 `--backend edge`、音色 `zh-CN-YunxiNeural`（云希）。

- 原因：GPT-SoVITS 合成英文发音不准；其音色注册表 default 指向**女声**参考音频，误用会让成片变女声且无 KTV 字幕。
- **不要**主动探测或拉起 `127.0.0.1:9880`，**不要**传 `--backend gptsovits`；仅当用户当次明确要求克隆音色才启用，且先确认参考音频性别。

```bash
cd <PROJECT_ROOT>\skills\todayaihot
<PYTHON> scripts/run_all.py "<NEWS_DIR>\AI新闻推送_YYYY-MM-DD.md" --backend edge --concurrency 1
```

要点：

- `--concurrency 1`：并发 2 曾 OOM，不要改回 2。
- 链路：parse（md → narration.json，同日重跑幂等）→ fetch（抓要点 + 配图）→ tts（云希，语速 +30%，生成 master.wav + timeline.json，缓存按「文本+后端+语速+音量」指纹复用，**正常重跑不需要 `--force-tts`**）→ render（Remotion 1080×1920/30fps）→ gen_publish（publish.md）→ finalize（run_report.json + handoff 登记）。
- 成片自动落在 `out/<YYYY-MM-DD>/每日ai热门新闻-YYYY-MM-DD.mp4`，目录不存在会自动创建。
- 渲染约 1–4 分钟，建议后台执行；完成后用 ffprobe 校验时长（目标 50–60 秒，明显短于 35 秒说明条目被解析少了）。
- **口播时长试算（开跑前必做）**：`<PYTHON> scripts/run_all.py "<md>" --preview` 试算口播字数，目标 325–385 字（≈50–59 秒）。预览模式不写 `seen_titles.json`、不覆盖正式 narration，无副作用；**严禁**手动删 seen 当日键（同日重跑已幂等）。
- **标题写法**：①归一化长度须 >32 字，否则会追加一条 22 字要点口播；②标题内不要出现 `/`、`、`、`：`、`，`（`/` 被 TTS 读成停顿，其它标点会把标题切成碎片子句）；③6–7 条标题总字数 330–360 字最稳。

**配图硬要求（用户已三次强调"不允许打字图片"）**：

- 画面绝不允许文字卡/海报卡/满屏文字截图；每条必须是一张**真实实拍照片**（原文真实配图优先，抓不到走 Pexels/Pixabay 兜底）。
- fetch 日志自检：末尾 `配图来源：原文 N / Pexels M / Pixabay K / 缺失 0` 中**缺失必须为 0**；出现 `[CRITICAL] … 关键词文字卡` 或缺失 >0 即配图链路故障（多为 Key 失效或网络），**不得进入发布**，先排查重跑 fetch。
- `validate_output.py` 把「某条无配图」判 **ERROR 并阻断渲染**：流水线在此中止属保护性拦截，不是 bug；修好配图重跑即可。
- **原文 og:image 常是品牌宣传海报**（NVIDIA 标题图、"Build more responsive apps" 这类），文字图识别未必拦得住。出片后必须**抽帧目检**：抽 6–8 帧（`-ss 3 / 9 / 14 / 19 / 26 / 31 / 37 / 46 -frames:v 1`）逐张确认是照片而非文字卡，并确认各条配图**互不重复**（图库相近检索词会返回同一张热图，代码已按 md5 去重）。
- **改配图的正确链路**：`render` 读的是 `work/timeline.json` 内嵌的 narration 快照。只改 `work/narration.json` 后重跑 `--only render` **不生效**；必须「改 narration.json → 重跑 gen_tts.py（重建 timeline，配音按指纹复用）→ 再 render」。字段必须是 plural 数组形态：`visual.images` / `visual.image_sizes`；写 singular `image` 会被前端忽略。
- 个别原文链接抓不到图（x.com 等反爬）会走图库兜底，属预期，不要因此中断。

**KTV 字幕自检（与配图自检同等强制）**：抽帧时必须看到字幕有**黄色高亮**（已朗读变黄、未朗读白色）。整屏全白即 `chars[].t` 时间基准错误，须检查 `align_whisper.py`（只允许写相对句首时间戳），修复后重跑 TTS + render。同时确认第 3 条要点未被字幕压住（正文区止于字幕安全区 `CONTENT_BOTTOM_LIMIT`）。

### 第六步：成片自动发布（social-auto-upload）

成片产出且校验通过后，用 `video-upload`（`social-auto-upload` 仓库内的 skill）把当天成片发布到抖音、B 站、视频号三平台。

- 视频：`<PROJECT_ROOT>/out/<YYYY-MM-DD>/每日ai热门新闻-<YYYY-MM-DD>.mp4`
- 标题：当天日期 + 3 条最重磅要闻关键词，抖音 ≤30 字，署名「翻奇兽AI」。
- 同一期因缺陷修复需重发时，先确认旧内容处置方式（视频号可用 `tencent-video-delete` 删除，抖音/B 站无自动删除），并在回复中说明新旧版本并存，不得静默重复发布。

**封面（硬要求：必须由 video-upload 的 codebase-style 大字模板重绘，严禁任何形式的视频首帧裁切）**：

- 环境：`$PYTHON = <SOCIAL_AUTO_UPLOAD_DIR>/.venv/Scripts/python.exe`，在 `<SOCIAL_AUTO_UPLOAD_DIR>` 下执行；路径参数用 Windows 盘符写法（`D:/…`），不用 `/d/…`。
- **只传封面文字字段**：`--main-title "每日AI头条 M.DD"` + `--subtitle "<当天最重磅关键词，18~20 字符内，超长会左右被裁>"` + `--tag "每日全球AI大事"` + `--pill "AI日报"` + `--author "翻奇兽AI"`。
- ⚠️ **严禁传 `--cover-3x4 / --cover-4x3 / --cover-16x9 / --cover-douyin`，也不要 ffmpeg 裁首帧当封面**：显式传封面会短路 `publish_all.py` 的自动重绘（文件"未过期"→`need_regen=False`），三平台直接用错图且**无任何告警**。
- 日志自检：必须出现 `[publish] 重新派生封面 → …` 或 `[publish] 抖音封面（重绘 3:4 大字版）:`；出现 `（显式指定）`/`（视频首帧兜底）` 说明封面链路被绕开，停下来修参数。**每次都加 `--force-regen`**。

```bash
export PATH="$HOME/.workbuddy/binaries/PortableGit/versions/<版本>/usr/bin:$HOME/.workbuddy/binaries/PortableGit/versions/<版本>/bin:/c/Windows/System32:/c/Windows:$PATH"
cd <SOCIAL_AUTO_UPLOAD_DIR>
PYTHON="<SOCIAL_AUTO_UPLOAD_DIR>/.venv/Scripts/python.exe"
D="<PROJECT_ROOT>/out/<YYYY-MM-DD>"
PROCESSOR_ARCHITECTURE=AMD64 "$PYTHON" skills/video-upload/scripts/publish_all.py \
  --video "$D/每日ai热门新闻-<YYYY-MM-DD>.mp4" \
  --title "<≤30 字标题>" \
  --desc "每日 AI 头条 · <YYYY-MM-DD>｜本期 N 条：<关键词串>" \
  --tags "AI,大模型,Agent,AI编程,开源" \
  --main-title "每日AI头条 M.DD" \
  --subtitle "<18~20 字关键词>" \
  --tag "每日全球AI大事" \
  --pill "AI日报" \
  --author "翻奇兽AI" \
  --chapters "$D/chapters.json" \
  --douyin-collection "每日全球AI大事" \
  --bili-tid 231 \
  --platforms douyin,bilibili,tencent \
  --force-regen
```

- 发布命令**前台执行**（`timeout` 595000）：后台模式会丢句柄并杀掉浏览器。
- 章节数据：由 `work/timeline.json` 场景起始秒生成 `$D/chapters.json`（8–9 条，`[{"time":"MM:SS","title":"…"}]`），渲染后用 narration.json 的真实标题回写「第N条」占位。
- 抖音合集固定「每日全球AI大事」。
- 发布后核验各平台结果（B 站可用 `check_bili_status.py` 取 BV 号），并把发布结果写回 `<PROJECT_ROOT>/handoff.md`（覆盖当日条目，写明各平台成功/失败）。
- 抖音单条失败重试上限 2 次，超过冷却 ≥3 小时补发，禁止短时间反复重试。cookie 过期需扫码时如实登记失败原因，不得重复发布同一条视频。
