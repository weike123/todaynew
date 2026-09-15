# todayaihot 技能优化方案

> 制定日期：2026-09-14
> 范围：`skills/todayaihot/`（Python 流水线 + Remotion 前端），不改动上游新闻采集与下游三平台发布
> 原则：**不破坏已验证的口播浓缩、字幕对齐、配图过滤三大核心行为**，只补短板、提工程化、增运营物料

---

## 一、现状诊断

### 1.1 已实现能力（保持不动）

| 模块 | 能力 | 成熟度 |
|---|---|---|
| 解析 | 3 种 md 格式兼容（A/B/C），半角全角归一，英文品牌保护 | 高 |
| 抓取富化 | aihot 页 + 原文直链双模式，文字图三层防线（域名黑名单/URL特征/像素启发式），Pexels 实拍兜底 | 高 |
| TTS | edge/volc/gptsovits/auto 四后端可插拔，edge WordBoundary 真实词边界，响度归一，wav+bounds 缓存 | 高 |
| 字幕 | KTV 逐字高亮，统一 52px 大字号，长句分页（不拆英文单词），尾部压缩变色 | 高 |
| 画面 | 配图完整展示（禁 cover），动态高度，长图竖向滚动，关键词海报卡兜底 | 高 |
| 渲染 | Remotion 1080×1920@30，ffmpeg 校验（分辨率/时长/音轨），日期文件夹归档 | 高 |
| 口播约束 | ≤1 分钟硬上限，标题-only 速览，开场/结尾固定话术 | 高 |
| 健壮性 | 沙箱批量删除防护，抓取失败优雅降级，edge 限流 4 次重试 | 中高 |

### 1.2 问题清单（按模块）

**A. 工程化与可维护性**
- A1 无 `requirements.txt` / 依赖锁定，SKILL 仅写"依赖齐全"
- A2 API Key 明文硬编码：`tts_client.py` 火山 Key、`fetch_news.py` Pexels Key
- A3 无 narration/timeline JSON Schema 文档，Python 与前端靠隐式契约
- A4 无自动化校验脚本（字数/时长/链接/JSON 合法性），全靠运行时
- A5 无 skill 自校验（参考 githubweektop10doc 的 `validate_skill.py`）
- A6 `backup_edge_20260909/` 备份目录混在 skill 代码里，应归档清理
- A7 运行日志只有 print，无结构化 run report（日期/后端/时长/失败项）
- A8 硬编码路径多（`C:/Python313`、`E:/workbuddy-workspace`、音色默认值），虽有环境变量覆盖但默认值写死

**B. TTS 与字幕对齐**
- B1 **非 edge 后端（volc/gptsovits）只能句内均分时间戳，字幕漂移**——这是当前最大的技术短板
- B2 无多音字/英文缩写定读法（GPT-6、CUDA、API、MoE 等读法不统一）
- B3 无单句长度硬校验，超长标题可能导致字幕分页异常
- B4 edge `NoAudioReceived` 限流时，首句连续失败会抛错终止整条流水线（当前靠"原地重跑"人工解决）
- B5 响度归一用 RMS 0.30，非行业标准 LUFS（短视频建议 -14 LUFS / TikTok -11~-14）
- B6 无 BGM/音效（行业标配，静音观看占比高，但有 BGM 提升完播率和质感）

**C. 内容与运营物料**
- C1 开场固定一句话，无钩子库轮换（抖音前 3 秒决定完播率，当前开场"X月X日，N条AI头条，一分钟速览"信息密度低）
- C2 无自动生成 `chapters.json`（timeline 里已有每个场景的 start，天然是 B站章节时间点；B站要求 3-10 条、首章 00:00、标题 2-8 字）
- C3 无封面自动生成（handoff 里 covers 是外部流程产出，不在 skill 内；可复用 Remotion TitleCard still 渲染）
- C4 无发布物料包（备选标题×3、话题标签 5-8 个、简介、置顶评论）——handoff 里发布靠外部流程手工写
- C5 无 AI 生成内容标注自检（平台合规要求：发布页声明、前 5 秒画面标识）
- C6 无跨天/同日新闻去重
- C7 画面每场景静态展示，无"每 2-3 秒微变化"节奏（完播率建议画面切换频率）

**D. 渲染与性能**
- D1 Remotion 4.0.380 → 最新 4.0.520，小版本可升（无 breaking），但收益有限
- D2 **AMD RX 6750GRE 不支持 Remotion NVENC 硬件编码**（Remotion Windows 仅支持 NVENC，需 N 卡），保持软件 x264，不折腾硬件编码
- D3 渲染失败无重试/断点续跑
- D4 字幕手写分页逻辑可参考官方 `@remotion/captions`，但中文分页当前手写已完善，**不建议迁移**（官方按英文词设计，中文适配成本高）

**E. 可观测性与交接**
- E1 无自动更新 `handoff.md`（AGENTS.md 强制要求每次视频会话结束登记，目前人工）
- E2 无 run report 落盘（每次运行的元信息）
- E3 smoke_fixture.py 存在但未集成到自动冒烟流程

---

## 二、优化目标

1. **统一字幕对齐**：所有 TTS 后端都能产出逐字时间戳，消除 volc/gptsovits 的字幕漂移
2. **工程化补齐**：依赖锁定、配置外置、Schema 文档、自动校验、skill 自校验
3. **运营物料内聚**：chapters.json、封面、发布物料包在 run_all 内自动产出，减少外部手工环节
4. **完播率提升**：开场钩子轮换、BGM ducking、画面微节奏
5. **流水线健壮性**：单句 TTS 失败不中断整条，自动降级
6. **交接自动化**：run report + handoff.md 自动登记

---

## 三、优化项详细方案

### P0（必做，第一阶段）

#### P0-1 配置外置与密钥安全
**问题**：A2、A8
**方案**：
- 新增 `scripts/config.py`，统一从环境变量 + 可选 `.env` 文件加载所有配置
- 密钥类（`VOLC_TTS_API_KEY`、`PEXELS_API_KEY`）代码中**移除明文默认值**，缺失时打印明确提示并走降级（Pexels 缺失→只用原文图+海报卡；火山缺失→auto 后端直接选 edge）
- 路径类（`PROJECT_ROOT`、`PYTHON`、`GSV_REGISTRY`）保留合理默认但集中管理
- 新增 `.env.example` 模板，`.env` 加入 `.gitignore`
**收益**：密钥不进 git，换机器/换号不改代码
**工作量**：中（改 4 个文件）
**风险**：低，纯重构

#### P0-2 依赖锁定
**问题**：A1
**方案**：
- 新增 `requirements.txt`，锁定当前已验证版本：`requests`、`beautifulsoup4`、`lxml`、`pillow`、`numpy`、`edge-tts`、`websocket-client`
- 新增 `scripts/check_deps.py`，启动时检查依赖，缺失则打印安装命令
**收益**：换环境可一键复现
**工作量**：小

#### P0-3 单句 TTS 失败不中断流水线
**问题**：B4
**方案**：
- `gen_tts.py` 的 `synth_clause` 4 次重试仍失败时，**不再抛错终止**，改为：生成该句时长的静音占位（按字数估算时长），标记 `failed=true`，继续后续句子
- 最终 run report 列出失败句，用户可决定是否 `--force-tts` 重跑该句
- 静音占位保证 timeline 连续、渲染不崩
**收益**：edge 偶发限流不再需要人工"原地重跑"，流水线自愈
**工作量**：小
**风险**：低（失败句静音，成片可听出缺口，但比整条崩好）

#### P0-4 自动校验脚本 `validate_output.py`
**问题**：A4
**方案**（借鉴 githubweektop10doc）：
- 校验项：
  - narration.json / timeline.json JSON 合法性 + 必填字段
  - 口播总字数与预估时长（语速 300 字/分），超过 60s 告警
  - 单 clause 字数 >40 告警（字幕分页压力）
  - 每条 news_item 的 link 可访问性（HEAD 请求，超时 5s，失败列入报告）
  - 配图文件存在性 + 尺寸记录完整
  - master.wav 存在且时长与 timeline.master_duration 一致
- 0 ERROR 才通过，WARN 列入报告
- `run_all.py` 在 render 前自动调用，ERROR 则中止并提示
**收益**：问题在渲染前暴露，节省渲染时间
**工作量**：中

#### P0-5 清理备份目录
**问题**：A6
**方案**：`backup_edge_20260909/` 移出 skill 目录到 `work/backups/` 或直接删除（已确认是 09-09 的 edge 配置备份，当前代码已稳定）
**工作量**：极小

---

### P1（重要，第二阶段）

#### P1-1 Whisper 强制对齐：统一所有后端的逐字时间戳 ⭐核心改进
**问题**：B1
**方案**：
- 新增 `scripts/align_whisper.py`，对合成后的 master.wav 做 ASR 强制对齐，产出逐字时间戳
- 技术选型：`faster-whisper`（CTranslate2，CPU int8 可跑，large-v3 约 3GB 内存，60s 音频约 10-20s）；用户主力机 AMD 卡无 CUDA，但 faster-whisper CPU 对 60s 短音频完全够用
- 工作流：TTS 合成 → master.wav → faster-whisper `word_timestamps=True` 转写 → 与已知文本（narration clauses）做强制对齐（用 WhisperX 的 wav2vec2 对齐，或 simpler：用 whisper 输出的词时间戳按文本匹配）
- 对齐结果覆盖 timeline 里的 chars 时间轴，`timing_src=whisper`
- 开关：`--align edge|whisper|auto`，默认 `auto`（edge 后端用 WordBoundary 更快，volc/gptsovits 自动用 whisper）
- **注意**：whisper 中文分词是按词不是按字，需做"词→字"的线性插值（同当前 `build_chars_from_bounds` 逻辑）
**收益**：volc/gptsovits 真人声也能精确字幕对齐，不再漂移；降低对 edge WordBoundary 的依赖（edge 限流时更稳）
**工作量**：大（新增依赖 + 对齐逻辑 + 与现有时间轴融合）
**风险**：中（whisper 对专业术语可能识别错，需用已知文本做强制对齐而非自由转写；建议用 `initial_prompt` 注入术语表）
**降级**：whisper 对齐失败时退回现有均分逻辑

#### P1-2 BGM + 人声闪避（ducking）
**问题**：B6、B5
**方案**：
- 新增 `assets/bgm/` 目录，放 2-3 首免版权纯音乐（从 Pixabay/YouTube Audio Library 下载，记录授权）
- `gen_tts.py` 生成 master.wav 后，`render.py` 渲染前用 ffmpeg 做混音：
  ```
  ffmpeg -i master.wav -i bgm.mp3 -filter_complex \
    "[1:a]volume=0.25,aloop=loop=-1:size=2e+09[bgm]; \
     [bgm][0:a]sidechaincompress=threshold=0.02:ratio=10:attack=50:release=500[ducked]; \
     [0:a][ducked]amix=inputs=2:duration=first[out]" \
    -af "loudnorm=I=-14:TP=-1:LRA=11" final.wav
  ```
- 人声说话时 BGM 自动压低 18-20dB（sidechaincompress），句间留白时 BGM 抬起
- 最终响度归一到 -14 LUFS（短视频平台标准），替代当前 RMS 0.30
- 开关：`--bgm` / `--no-bgm`，默认开启（用户可关）
**收益**：成片质感提升，符合行业标配；LUFS 标准化避免平台二次压缩
**工作量**：中
**风险**：低（ffmpeg 纯后处理，不影响 TTS 和渲染）
**注意**：BGM 版权必须合规，免商用授权

#### P1-3 开场钩子库轮换
**问题**：C1
**方案**（借鉴 githubweektop10doc 的 hook-library）：
- 新增 `references/hooks.md`，定义 6-8 种开场钩子模板，按当天新闻特征轮换：
  - H1 数字冲击：「今天 AI 圈有 3 件大事，第 2 件直接降价 70%」
  - H2 悬念提问：「为什么大厂都在偷偷换掉这个模型？」
  - H3 冲突对比：「OpenAI 刚修复，DeepSeek 就降价」
  - H4 结果前置：「60 秒看完今天最值得关注的 N 条 AI 新闻」
  - H5 痛点共鸣：「做 AI 的你，这条必须知道」
  - H6 时间锚点：「9 月 14 日，AI 圈发生了这些」
- 钩子从当天头条标题中提取关键词填充，保证不脱离内容
- 开场口播仍控制在 ≤8 秒，不突破 1 分钟总时长
- 原固定话术作为兜底（H6）
**收益**：前 3 秒信息密度提升，完播率改善
**工作量**：中（钩子模板 + 关键词提取 + 选择逻辑）
**风险**：低（钩子仍基于真实新闻，不编造）

#### P1-4 自动生成 chapters.json
**问题**：C2
**方案**：
- `gen_tts.py` 生成 timeline 后，直接从 `scenes[].clauses[0].start` 提取每个场景的起始时间
- 章节标题取 `visual.title` 截断到 8 字，或 `section` 分类名
- B站规范：首章 00:00、总数 3-10 条、时间戳向下取整到秒、标题 2-8 字
- 输出 `out/<date>/chapters.json` + 同时生成可直接粘贴的 B站简介格式文本（`00:00 标题\n00:15 标题`）
- 当前 7 条新闻 + 开场 + 结尾 = 9 个场景，正好在 B站 3-10 条范围内
**收益**：handoff 里 chapters 不再靠外部流程，timeline 数据直接复用
**工作量**：小

#### P1-5 封面自动生成（Remotion still）
**问题**：C3
**方案**：
- 复用现有 `TitleCard` 组件，`render.py` 渲染完成后调用 `npx remotion still src/index.tsx TitleCard cover.png`
- 新增 3 种比例封面：3:4（抖音/视频号竖版）、4:3（视频号横版）、16:9（B站），通过 Composition  props 控制
- 封面大字从当天头条提取（如"DeepSeek降价·OpenAI修复"），署名"翻奇兽AI"
- 输出到 `out/<date>/covers/`
- 不重新发明轮子，用 Remotion 已有渲染能力
**收益**：封面不再靠外部流程，风格与成片统一
**工作量**：中（需新增 3 个封面 Composition 或 props 化）
**风险**：低

#### P1-6 发布物料包自动生成
**问题**：C4
**方案**：
- `run_all.py` 完成后，基于 narration 内容生成 `out/<date>/publish.md`：
  - 备选标题 ×3（含核心关键词，前 10 字嵌入热点词）
  - 话题标签 5-8 个（#AI #大模型 #每日AI头条 + 当天具体话题如 #DeepSeek #OpenAI）
  - 视频简介（含 chapters 时间轴）
  - 置顶评论文案
  - AI 生成内容声明（平台合规）
- 生成方式：规则模板 + 当天新闻关键词提取，不依赖 LLM API（保持离线可用）
**收益**：发布时直接复制粘贴，减少手工
**工作量**：中

#### P1-7 TTS 文本增强：缩写定读法 + 多音字
**问题**：B2、B3
**方案**：
- 新增 `scripts/tts_normalize.py`（或扩展 `parse_news.clean_for_tts`）：
  - 英文缩写定读表：`GPT-6`→`G P T 六`、`CUDA`→`库达`、`API`→`A P I`、`MoE`→`M O E`、`RAG`→`R A G`、`Agent`保留原词、`CLI`→`C L I`
  - 常见多音字：`重`(zhòng/chóng)、`行`(xíng/háng)、`降`(jiàng/xiáng)——按上下文规则或注音标注
  - 单句硬上限 40 字，超过自动在标点处拆分
- 定读表可配置，用户可扩展
**收益**：专业术语发音准确，不再"GPT六"读成"GPT减六"之类
**工作量**：中
**风险**：低（纯文本预处理，不影响 TTS 后端）

---

### P2（可选，第三阶段，有余力再做）

#### P2-1 run report + handoff.md 自动登记
**问题**：E1、E2、A7
**方案**：
- `run_all.py` 结束后生成 `out/<date>/run_report.json`：日期、主题、时长、分辨率、TTS 后端、配图数、抓取失败项、TTS 失败项、校验结果
- 自动更新项目根 `handoff.md`，按 AGENTS.md 要求的字段登记（日期/主题/简介/主视频路径/封面/时长/分辨率/目标平台），同日期则更新而非追加
**收益**：交接零手工，符合 AGENTS.md 强制要求
**工作量**：中

#### P2-2 跨天新闻去重
**问题**：C6
**方案**：
- 维护 `work/seen_titles.json`（标题归一化 hash + 日期），parse 阶段对相似度 >0.8 的标题标记"重复"并跳过或换角度
- 标题归一化：去标点、去英文大小写、提取核心名词
**收益**：避免连续几天讲同一件事
**工作量**：中

#### P2-3 画面微节奏
**问题**：C7
**方案**：
- `NewsItem.tsx` 在场景时长 >8s 时，添加配图轻微 Ken Burns 缓动（缓慢放大/平移），或要点逐条渐入
- 不改变信息布局，只增加动态感
**收益**：画面不呆板，完播率微升
**工作量**：小
**风险**：低

#### P2-4 Remotion 版本升级
**问题**：D1
**方案**：4.0.380 → 4.0.520，小版本无 breaking，`npm install remotion@latest @remotion/cli@latest`
- 升级后跑一次冒烟验证
- **不引入**硬件编码（AMD 不支持）
**收益**：bug 修复、性能微调
**工作量**：小
**风险**：低（小版本）

#### P2-5 渲染失败重试
**问题**：D3
**方案**：`render.py` Remotion 渲染失败时自动重试 1 次（Chrome Headless 偶发崩溃），仍失败才报错
**工作量**：小

#### P2-6 冒烟测试集成
**问题**：E3
**方案**：`smoke_fixture.py` 生成固定 narration → 跳过 fetch/tts → 直接渲染，验证前端组件不崩。加入 `run_all.py --smoke` 模式
**工作量**：小

---

## 四、不做什么（明确边界）

| 项 | 原因 |
|---|---|
| 不迁移到 `@remotion/captions` | 官方按英文词分页，中文适配成本高；当前手写分页已完善且贴合需求 |
| 不搞硬件编码 | Remotion Windows 仅支持 NVENC，用户主力机 AMD RX 6750GRE 不支持；软件 x264 质量更好 |
| 不内置上游新闻采集 | 上游定时任务已稳定产出 md，skill 保持"md→视频"单一职责，避免范围蔓延 |
| 不接入 LLM 生成口播稿 | 当前口播是标题速览，LLM 改写有幻觉风险且突破 1 分钟约束；保持规则驱动 |
| 不做三平台自动发布 | 发布是独立流程（social-auto-upload），skill 只产出物料包 |
| 不换 TTS 后端默认 | edge-tts 免费稳定且 WordBoundary 对齐最好，保持默认；volc/gptsovits 作为可选 |
| 不升级到 Remotion 5.0 | 5.0 宣称的 17x 提速来自 CSDN 博客，可信度待验证，且可能有 breaking change；保守用 4.x 最新 |

---

## 五、分阶段实施路线图

### Phase 1（P0，预计 1-2 小时）—— 工程化打底
1. P0-5 清理备份目录
2. P0-1 配置外置 + 密钥安全
3. P0-2 依赖锁定 + check_deps
4. P0-3 单句 TTS 失败不中断
5. P0-4 validate_output.py
6. 跑一次完整流水线验证无回归

### Phase 2（P1，预计 3-5 小时）—— 核心能力提升
1. P1-7 TTS 文本增强（缩写定读 + 多音字 + 单句上限）—— 先做，因为影响口播文本
2. P1-1 Whisper 强制对齐 ⭐—— 最大技术改进，独立验证
3. P1-2 BGM + LUFS 归一
4. P1-3 开场钩子库
5. P1-4 chapters.json 自动生成
6. P1-5 封面自动生成
7. P1-6 发布物料包
8. 端到端验证 + 对比成片效果

### Phase 3（P2，预计 1-2 小时）—— 收尾优化
1. P2-1 run report + handoff 自动登记
2. P2-4 Remotion 小版本升级
3. P2-5 渲染重试 + P2-6 冒烟集成
4. P2-2 跨天去重 + P2-3 画面微节奏（可选）

---

## 六、验收标准

### Phase 1 验收
- [ ] 代码中无明文 API Key
- [ ] `requirements.txt` 存在且 `pip install -r` 可复现
- [ ] 故意让某句 TTS 失败，流水线不中断，成片有静音占位且报告列出失败句
- [ ] `validate_output.py` 对正常输入 0 ERROR，对故意损坏的输入能检出
- [ ] 完整跑一次当天 md，成片时长 50-60s、字幕对齐、配图正常

### Phase 2 验收
- [ ] `--backend volc --align whisper` 产出的字幕逐字对齐，无漂移（`timing_src=whisper`）
- [ ] 成片含 BGM，人声说话时 BGM 自动压低，句间抬起；整体响度 -14 LUFS
- [ ] 开场钩子连续 3 天不重复，且基于当天新闻
- [ ] `out/<date>/chapters.json` 存在，符合 B站规范（3-10 条、首章 00:00）
- [ ] `out/<date>/covers/` 含 3:4、4:3、16:9 三张封面
- [ ] `out/<date>/publish.md` 含标题×3、标签、简介、置顶评论
- [ ] GPT-6、CUDA、API 等缩写发音正确

### Phase 3 验收
- [ ] `out/<date>/run_report.json` 存在且字段完整
- [ ] `handoff.md` 自动更新当天条目，不重复追加
- [ ] Remotion 升级后冒烟通过
- [ ] `--smoke` 模式可在无 TTS/无网络下验证渲染

---

## 七、风险与回滚

| 风险 | 影响 | 回滚方案 |
|---|---|---|
| Whisper 对齐识别错误导致字幕乱 | 字幕与文本不匹配 | `--align edge` 退回 WordBoundary；whisper 失败自动降级均分 |
| BGM 版权问题 | 平台下架 | 仅用免商用授权音乐，记录来源；`--no-bgm` 可关 |
| 钩子模板生成不当开场 | 前 3 秒体验下降 | 保留原固定话术作为兜底，钩子可配置关闭 |
| 配置外置后环境变量缺失 | 流水线启动失败 | check_deps 提前检查并打印明确提示 |
| Remotion 小版本升级引入 regression | 渲染失败 | 锁定 package.json version，升级前备份 node_modules |

---

## 八、调研依据（外部最佳实践）

1. **Remotion 4.0.520**：官方 `@remotion/captions`（createTikTokStyleCaptions）、`@remotion/install-whisper-cpp`、硬件编码（仅 NVENC/VideoToolbox）——来源：remotion.dev 官方文档（2026-09 更新）
2. **TTS 2026 版图**：edge-tts 仍是免部署中文最强之一；新选项 Qwen3-TTS、CosyVoice3、IndexTTS-2、F5-TTS、Fish Audio——但用户 AMD 卡本地部署困难，云端 edge/火山最现实
3. **faster-whisper**：`word_timestamps=True` 逐词时间戳，CPU int8 可跑，60s 音频约 10-20s——来源：faster-whisper 文档与多篇实战指南
4. **ffmpeg 音频后期**：`loudnorm=I=-14:TP=-1:LRA=11`（短视频 LUFS 标准）、`sidechaincompress` 人声闪避——来源：ffmpeg-cookbook、EBU R128
5. **平台运营**：抖音完播率权重最高，前 3 秒 hook、画面每 2-3s 切换、信息密度、BGM 节奏匹配；B站章节 3-10 条、首章 00:00、标题 2-8 字——来源：多篇 2026 运营指南
6. **同类技能借鉴**：zhuzigaodoc（TTS 友好化、双轨时长、字数回算、发布物料包、AI 标注自检）、githubweektop10doc（钩子库轮换、validate_output、快照锁定、skill 自校验）
