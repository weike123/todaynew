# todaynew · 每日 AI 头条短视频流水线

把一份「每日 AI 新闻」Markdown，自动化做成可直接投放的 **9:16 竖屏口播短视频**：逐字稿 → 配音 → KTV 逐字字幕 → 实拍配图 → Remotion 渲染 → 发布物料 → 三平台发布。

**面向开发者**：不接任何新闻源的账号体系，不依赖任何付费服务；默认 TTS 用免费的 edge-tts，配图用原文实拍图 + Pexels/Pixabay 兜底。

---

## 目录

- [它解决什么问题](#它解决什么问题)
- [快速开始（5 分钟跑通）](#快速开始5-分钟跑通)
- [环境要求](#环境要求)
- [配置密钥](#配置密钥)
- [完整使用方法](#完整使用方法)
- [目录结构](#目录结构)
- [工作原理](#工作原理)
- [质量门与验收](#质量门与验收)
- [测试](#测试)
- [常见问题排查](#常见问题排查)
- [二次开发](#二次开发)
- [安全与隐私](#安全与隐私)
- [许可证](#许可证)

---

## 它解决什么问题

每天做一条 AI 资讯短视频，重复劳动集中在四处：

| 环节 | 手工做的事 | 本项目的自动化 |
|---|---|---|
| 选题 | 刷几十个源、凑 6–7 条 | 按 Markdown 结构化解析，直接吃现成简报 |
| 配音 | 逐句 TTS、对时间轴 | 逐句合成 + 指纹缓存（改一句只重合成一句） |
| 字幕 | 手动卡点、做 KTV 高亮 | 从 TTS 词边界直接生成逐字时间戳 |
| 画面 | 找图、担心配图变成"满屏文字" | 原文实拍图优先，图库兜底，**文字卡直接阻断出片** |

**核心设计取舍**：宁可阻断出片，也不发一条画面是"标题文字卡"的视频。所以「缺配图」「口播残句」「字幕时间戳异常」都是 **ERROR 级硬门**，直接中止流水线。

---

## 快速开始（5 分钟跑通）

```bash
# 1. 克隆
git clone <this-repo-url> todaynew
cd todaynew

# 2. 安装 Remotion 依赖（Node 18+）
cd remotion && npm install && cd ..

# 3. 安装 Python 依赖
pip install -r skills/todayaihot/requirements.txt

# 4. 配置密钥
cp .env.example .env
# 编辑 .env，填入 PEXELS_API_KEY 与 PIXABAY_API_KEY（见下节）

# 5. 先跑冒烟测试，确认渲染链路通畅（约 1–2 分钟，不需要任何 API Key）
cd skills/todayaihot
python scripts/run_all.py --smoke
```

冒烟测试会生成 6 秒测试视频并渲染到 `out/2026-09-06/每日ai热门新闻-2026-09-06.mp4`，用来验证「Python → ffmpeg → Remotion」整条链路在你的机器上能跑通。

> 冒烟数据自带一张现场生成的 PNG 配图，**不需要配置任何 API Key**，也不访问网络。
> 它会覆盖 `work/narration.json` 与 `work/timeline.json`（中间产物，下次跑流水线会重新生成）。
> 跑完可直接删除 `out/2026-09-06/`。

**跑通后再跑真实内容**：

```bash
python scripts/run_all.py "/绝对路径/AI新闻推送_2026-10-23.md" --backend edge --concurrency 1
```

---

## 环境要求

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | 3.10+ | 需 `requests` `beautifulsoup4` `lxml` `pillow` `numpy` `edge-tts` `websocket-client` |
| Node.js | 18+ | 仅用于 Remotion 渲染；`render.py` 会自动探测 node 位置 |
| ffmpeg | 需支持 `asplit/aloop/sidechaincompress/amix/loudnorm` | **BGM 闪避混音必需**。Remotion 自带的是精简构建，不够用 |
| Chrome Headless Shell | 自动 | 首次渲染时 Remotion 自动下载 |

### 关于 ffmpeg（最容易踩的坑）

BGM 人声闪避混音依赖 `asplit` / `aloop` / `sidechaincompress` / `amix` / `loudnorm` 这一整条滤镜链。
**Remotion 自带的 ffmpeg 是精简构建，缺这些滤镜**，用它混音必然失败。

处理方式（二选一）：

```bash
# 方式 A：设置环境变量指向完整构建（推荐）
set TODAYAIHOT_FFMPEG=D:/path/to/ffmpeg/bin/ffmpeg.exe

# 方式 B：本次禁用 BGM，只做响度归一
python scripts/run_all.py "news.md" --no-bgm
```

启动时 `check_deps.py` 会实测滤镜链能力并明确报告"可用/不可用"，不会让你跑到一半才发现。

---

## 配置密钥

复制 `.env.example` 为 `.env`（`.env` 已在 `.gitignore` 中，**永远不会被提交**）：

```bash
cp .env.example .env
```

| 变量 | 必需 | 说明 |
|---|---|---|
| `PEXELS_API_KEY` | ✅ | 实拍配图兜底。[申请地址](https://www.pexels.com/api/) |
| `PIXABAY_API_KEY` | ✅ | 实拍配图兜底 + BGM 检索。[申请地址](https://pixabay.com/api/docs/) |
| `VOLC_TTS_API_KEY` | ❌ | 火山引擎 seed-tts-2.0。填了才能用 `--backend volc` |
| `TTS_EDGE_VOICE` | ❌ | edge-tts 音色，默认 `zh-CN-YunxiNeural`（云希） |
| `TODAYAIHOT_ROOT` | ❌ | 项目根目录。默认自动从脚本位置推导 |
| `TODAYAIHOT_FFMPEG` | ❌ | 完整 ffmpeg 路径 |
| `TODAYAIHOT_BGM_DIR` | ❌ | BGM 目录，默认 `<项目根>/assets/bgm` |

> ⚠️ **两个图库 Key 必须都填**。只填一个时，另一个源失效仍可能凑巧成功，但一旦原文抓图失败且只有一个源可用，配图兜底会静默失效，画面退化成文字卡——而这正是本项目要杜绝的情况。

---

## 完整使用方法

### 每日新闻简报的格式要求

流水线依赖这个结构（`#` 标题 + 条目 + 三行要点 + 原文直链）：

```markdown
# AI 新闻推送 · 2026-10-23

**1. OpenAI 发布 GPT-6.1 Sol Ultrafast**
核心：推理速度提升 8 倍，API 定价 $12/$60 每百万 token。
细节：Codex steering 即时生效，同步进入 ChatGPT Work。
价值：编码 Agent 的 token 成本可下降约 40%，适合高并发 CI 场景。
原文：https://example.com/some-article
```

要点：
- 每条**必须**有 `原文：<直链>`（不是聚合站链接）——抓图环节靠它定位原文配图
- 每条至少写满 `核心/细节/价值` 三行
- 建议 6–7 条（对应成片 50–60 秒）；少于 6 条时长不达标

### 一键跑完整条流水线

```bash
cd skills/todayaihot
python scripts/run_all.py "/路径/AI新闻推送_2026-10-23.md" --backend edge --concurrency 1
```

依次执行 6 个环节：

| # | 环节 | 脚本 | 产物 |
|---|---|---|---|
| 1 | 解析 | `parse_news.py` | `work/narration.json` |
| 2 | 抓取富化 | `fetch_news.py` | 补全要点 + `remotion/public/images/` 配图 |
| 3 | 配音+时间轴 | `gen_tts.py` | `work/audio/master.wav` + `work/timeline.json` |
| 4 | 渲染 | `render.py` | `out/<date>/每日ai热门新闻-<date>.mp4` + `covers/` + `chapters.json` |
| 5 | 发布物料 | `gen_publish.py` | `out/<date>/publish.md` |
| 6 | 收尾 | `finalize.py` | `out/<date>/run_report.json` + `handoff.md` 登记 |

### 分环节执行

```bash
python scripts/run_all.py "news.md" --only parse    # 只解析
python scripts/run_all.py "news.md" --only fetch    # 只抓图
python scripts/run_all.py "news.md" --only tts      # 只配音
python scripts/run_all.py "news.md" --only render   # 只渲染（仍会自动补跑 gen_publish + finalize）
```

### 常用参数

| 参数 | 说明 |
|---|---|
| `--preview` | **只解析并打印口播字数**，不写 `seen_titles.json`、不覆盖正式 `narration.json`。零副作用，改稿前先跑它 |
| `--backend edge\|volc\|auto\|gptsovits` | TTS 后端。默认 `edge`（免费、稳定） |
| `--force-tts` | 强制全量重合成配音。**正常重跑不需要**——缓存按「文本+后端+语速+音量」指纹复用 |
| `--concurrency 1` | 渲染并发。默认 1（并发 2 曾导致 OOM） |
| `--no-bgm` | 关闭 BGM，只做响度归一 |
| `--skip-render` | 只跑到时间轴，不渲染。改稿阶段用它最快 |
| `--check-links` | 校验时检查新闻链接可访问性（慢） |
| `--smoke` | 冒烟模式，生成 6 秒测试视频 |

### 改稿的正确姿势

1. 改 `news.md` → 跑 `--preview` 确认字数在 325–385 字（≈50–59 秒）
2. 跑 `--skip-render` 验证配音与字幕
3. 满意后跑完整流水线

> 改稿后**不需要** `--force-tts`：配音缓存按内容指纹失效，只重合成真正改动的那几句。

### 换配图（不改稿，只换图）

某些原文的头图是"浅色渐变底 + 居中大字"的标题卡，会被当成合法图片通过过滤器。修法：

1. 从 Pexels 找一张同主题实拍图，存到 `remotion/public/images/`
2. 回写 `work/narration.json` **和** `work/timeline.json` 中 `narration.scenes[sN].visual`：
   ```json
   {
     "images": ["images/你的文件名.jpg"],
     "image_sizes": [[1920, 1080]],
     "image_source": "pexels"
   }
   ```
   ⚠️ 字段必须是 **plural 数组形态**（`images` / `image_sizes`）。写成 singular 的 `image` 字段会被前端忽略，画面仍是旧图。
3. 只重跑渲染（约 2 分钟），无需重跑 parse/fetch/TTS：
   ```bash
   python scripts/render.py
   ```

### 发布到抖音 / B站 / 视频号

发布由外部工具 `social-auto-upload`（独立仓库）负责，本项目只产出物料：

- `out/<date>/publish.md` —— 备选标题、话题标签、简介、置顶评论
- `out/<date>/chapters.json` —— B站章节（3–10 条，首章 00:00，标题 ≤20 字）
- `out/<date>/covers/` —— 3:4 / 4:3 / 16:9 三种比例 PNG

**封面分工（重要）**：本流水线产出的是 Remotion still 生成的 PNG，用于预览与备用。
**正式发布的 JPG 封面必须由外部发布工具的 codebase-style 大字模板重绘**——不要把 PNG 或视频首帧裁切图直接当封面传过去，否则三平台封面会全部不对且无任何告警。

---

## 目录结构

```
todaynew/
├── skills/todayaihot/          # 流水线源码（Python）
│   ├── scripts/
│   │   ├── run_all.py          # 一键入口
│   │   ├── parse_news.py       # md -> narration.json
│   │   ├── fetch_news.py       # 抓取富化 + 配图（含文字卡识别）
│   │   ├── gen_tts.py          # 配音 + KTV 时间轴
│   │   ├── render.py           # Remotion 渲染 + 封面 + 章节
│   │   ├── gen_publish.py      # 发布物料
│   │   ├── finalize.py         # run_report + handoff 登记
│   │   ├── validate_output.py  # 质量门（ERROR 阻断）
│   │   └── common.py           # 路径与参数（唯一配置源）
│   ├── references/             # 契约、规范、踩坑记录
│   ├── tests/                  # pytest 回归测试
│   └── assets/bgm/             # 免版权 BGM（可选）
├── remotion/                   # 渲染工程
│   ├── src/
│   │   ├── Root.tsx            # Composition 定义
│   │   ├── NewsVideo.tsx       # 主视频场景编排
│   │   ├── scenes/             # 开场 / 新闻卡 / 结尾
│   │   ├── components/         # 字幕、主题、封面
│   │   └── types/              # 类型声明
│   └── public/                 # 配音与配图（运行时生成，不入库）
├── assets/bgm/                 # 免版权 BGM
├── docs/                       # 优化方案与审阅证据
├── out/<date>/                 # 成片与发布物料
├── work/                       # 中间产物（不入库）
└── handoff.md                  # 每次生成的视频登记
```

---

## 工作原理

### 数据流

```
news.md ──parse──▶ narration.json ──fetch──▶ 富化narration + 配图
                         │
                         ├──tts──▶ master.wav + timeline.json
                         │              (含逐字时间戳)
                         └──render──▶ Remotion ──▶ out/<date>/*.mp4
                                                    + covers/ + chapters.json
                         └──gen_publish──▶ publish.md
                         └──finalize──▶ run_report.json + handoff.md
```

### 为什么字幕能对上音

`gen_tts.py` 用 edge-tts 的 **WordBoundary 词边界**直接产出逐字相对时间戳，写入每个 clause 的 `chars[].t`。

时间基准是：`master.wav = [0.1s 静音][逐句 PCM]`，且 `clause.start = 0.1 + 游标`。
视频中音频从**第 0 帧**起播（master 已内置那 0.1 秒静音），于是「wav 位置 == 视频时间」严格成立。

> ⚠️ 改 `NewsVideo.tsx` 时注意：**不要**给 `<Audio>` 再套延迟 `<Sequence>`，否则静音被双计、字幕整体偏移 0.1 秒。
> 这条契约由 `tests/test_timing_contract.py` 锁定。

### 配图的硬规则

画面**绝不允许**出现文字卡 / 海报卡 / 满屏文字截图。判定由 `looks_like_text_image()` 四判据执行（颜色唯一度、彩色度、主色占比、前 3 色集中度）。

> 四判据是**高置信度过滤器**而非完备判据。厂商博客那种「浅色柔光渐变底 + 居中大字」的标题卡能通过全部四判据。
> 所以**出片后必须抽帧目检**，不能只看日志。

### 配图来源优先级

1. 原文真实配图
2. Pexels 实拍图
3. Pixabay 实拍图

三者都拿不到 → 校验判 **ERROR** → **阻断出片**（不留文字卡兜底）。

---

## 质量门与验收

`validate_output.py` 在渲染前自动运行，**0 ERROR 才放行**：

| 级别 | 检查项 |
|---|---|
| ERROR | 缺配图 / 配图文件缺失或损坏 / 走了海报文字卡兜底 |
| ERROR | 口播残句（截断成"研究团队称……"这类半句） |
| ERROR | 字幕逐字时间戳为负、逆序、或超出句长 |
| ERROR | clause 时间轴不连续（`start >= end`） |
| WARN | 其它非致命项（如链接不可达） |

`finalize.py` 生成的 `run_report.json` 有三种状态：

| 状态 | 含义 |
|---|---|
| `READY` | 物料齐全且成片实测通过，可交外部发布 |
| `GENERATED` | 文件已生成，但缺物料，未完成发布前验收 |
| `BLOCKED` | 失败原因与恢复方式已记录，**不得发布** |

### 出片后的人工抽帧检查（必做）

```bash
ffmpeg -i out/<date>/每日ai热门新闻-<date>.mp4 -vf "select='eq(n\,90)+eq(n\,240)+eq(n\,390)'" -vsync vfr frames_%02d.jpg
```

逐张确认：
- ✅ 配图是**真实实拍照片**，不是文字卡
- ✅ 各条配图**互不重复**
- ✅ KTV 字幕有**黄白高亮**（已朗读变黄），不是全白

---

## 测试

```bash
cd skills/todayaihot
python -m pytest tests/ -q
```

当前 **80 个用例全通过**，覆盖：

| 测试文件 | 锁定的不变量 |
|---|---|
| `test_timing_contract.py` | 时间基准、Audio 0 帧起播、末场景覆盖尾部缓冲 |
| `test_spoken_clause.py` | 口播残句三层防线 |
| `test_validate_output.py` | 质量门判定逻辑 |
| `test_gen_tts_cache.py` | 配音缓存指纹与失败重试 |
| `test_parse_dedup.py` | 跨天去重 |
| `test_finalize.py` | run_report 状态机、handoff 保留发布回执 |
| `test_mix_chain.py` | ffmpeg 混音链路预检 |
| `test_punct_normalization.py` | 标点归一化 |
| `test_run_all_steps.py` | 环节编排 |

部分用例需要完整 ffmpeg（生成真实视频 fixture）。找不到时该用例会 **skip** 而非失败。

---

## 常见问题排查

### `Cannot find module '../../work/timeline.json'`

`work/` 是中间产物目录，已被 `.gitignore` 排除，新克隆的仓库里不存在它。

- **只跑 `npm run typecheck`**：已由 `remotion/src/types/work-timeline.d.ts` 兜底，不会报错
- **要真正渲染**：必须先生成 `work/timeline.json`，即先跑 `parse` + `tts`（或直接 `--smoke`）

### 渲染报「混音链路预检未通过」

你的 ffmpeg 不支持 BGM 闪避混音。设置 `TODAYAIHOT_FFMPEG` 指向完整构建，或加 `--no-bgm`。

### 渲染报「No available ports found」

Remotion 需要在 `3000-3100` 段找端口，而这段常被 Windows 的「排除端口范围」策略保留（企业安全软件、VPN 客户端会占用）：

```powershell
netsh int ipv4 show excludedportrange protocol=tcp
```

`render.py` 已内置**自动端口探测**：首次渲染失败时会自动改用可用端口重试（依次探测 3000-3100 → 4000-4100 → 18000-18050）。
若仍失败，请关闭占用该端口段的代理/安全软件。

### 画面全是文字卡

图库 Key 没配或失效。检查 `.env` 里 `PEXELS_API_KEY` 和 `PIXABAY_API_KEY` **都**有值，且没过期。

### KTV 字幕全程不变黄

逐字时间戳时间基准错误。检查 `align_whisper.py` 写出的 `chars[].t` 是否是**相对句首**而非绝对全局时间。

### 配音是女声 / 英文发音奇怪

用了非 `edge` 后端。指定 `--backend edge`，默认音色是云希（`zh-CN-YunxiNeural`）。

### 成片时长明显偏短

条目被解析少了。用 `--preview` 检查口播字数与条目数，目标 325–385 字。

### edge-tts 报 429 限流

微软侧瞬时风控。等待几秒重试即可；`gen_tts.py` 已内置 4 次重试，通常能自愈。

### 渲染 OOM

`--concurrency 1`（默认值）。不要调大。

---

## 二次开发

### 配置的唯一来源

所有路径与参数集中在 `skills/todayaihot/scripts/common.py`：

- `PROJECT_ROOT` —— 自动从脚本位置推导（`<root>/skills/todayaihot` → 上溯两级），也可用 `TODAYAIHOT_ROOT` 覆盖
- `BGM_DIR` —— 优先 `<root>/assets/bgm`，其次 skill 内 `assets/bgm`，也可用 `TODAYAIHOT_BGM_DIR` 覆盖
- `WIDTH/HEIGHT/FPS` —— 1080×1920 @ 30fps
- `CONCURRENCY` —— 渲染并发，默认 1

### 新增一个场景类型

1. 在 `remotion/src/scenes/` 加组件
2. 在 `remotion/src/NewsVideo.tsx` 的 `SceneRouter` 里加 `case`
3. 在 `parse_news.py` 里产出对应的 `visual.type`

### 加一个 TTS 后端

在 `skills/todayaihot/scripts/tts_backend.py` 实现 `synth()`，返回 `(wav路径, 词边界列表)`。

---

## 安全与隐私

- **`.env` 永不提交**：已在 `.gitignore`，仓库内只有 `.env.example`（无任何真实值）
- **密钥只从环境变量读取**：代码中无任何明文默认值
- **中间产物不入库**：`work/`、`out/`、`remotion/public/audio|images/`、音频视频文件均已忽略
- **日志与交接文件不写密钥值**
- 历史提交中未发现任何密钥泄露（已对全部 commit 做过 `git grep` 扫描）

> 如果你 fork 后填了自己的 Key 并误提交，请立即到对应平台吊销并重置——Git 历史一旦推送，删除文件也不能抹除历史。

---

## 许可证

本项目代码与文档采用 **MIT 许可证**，见 [LICENSE](LICENSE)。

`assets/bgm/` 下的音乐素材来自 Pixabay 等免版权来源，遵循各自原始授权，**不适用**本仓库的 MIT 许可证。

新闻内容版权归原作者所有，本项目仅作技术演示用途。
