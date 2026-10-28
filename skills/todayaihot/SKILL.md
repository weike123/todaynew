---
name: todayaihot
description: 将每日 AI 新闻 Markdown 生成可审阅的逐字稿、配音字幕、Remotion 竖屏视频和 codebase-style 封面；适用于 todaynew 项目的新闻短视频流水线。
---

# todayaihot

## 目标

把项目根目录的每日 AI 新闻简报转换为 `out/YYYY-MM-DD/` 下的 9:16 成片、字幕时间轴、封面、发布物料和 `handoff.md` 登记。

## 当前能力状态（2026-10-14 核实）

- `scripts/` 流水线（parse → fetch → tts → render → gen_publish → finalize）、`work/` 中间产物、每日 `out/` 产物均真实存在，可端到端运行。
- 项目内 `skills/todayaihot` 是完整副本（实体目录，非 junction）；用户级安装位置为 `%USERPROFILE%/.workbuddy/skills/todayaihot`。两份内容需要手动保持同步。
- 已验证运行环境：Python 3.10+（含 requests/bs4/lxml/PIL/numpy/edge-tts）；Remotion 4.0.520 在 `remotion/`，首次渲染会自动下载 Chrome Headless Shell。
- 若上述文件意外缺失（误删、junction 断裂），按 [还原检查清单](references/recovery-checklist.md) 排查；该清单仅作异常恢复参考，不代表当前状态。

## 无人值守定时任务（任意 agent 可用）

本 skill 自带一份**可移植的定时任务提示词**：[automation-prompt.md](references/automation-prompt.md)。它把「AIHOT 采集 → 写 news.md → 出片 → 三平台发布 → 回写 handoff」写成一条完整任务，路径全部用占位符（`<PROJECT_ROOT>` / `<NEWS_DIR>` / `<SOCIAL_AUTO_UPLOAD_DIR>` / `<PYTHON>`），clone 后不需要改代码。

创建方式：对任意 agent 说「读取 `<PROJECT_ROOT>/skills/todayaihot/references/automation-prompt.md`，替换占位符后创建每天 16:00 的定时任务」，agent 会按其正文建 recurring 任务（WorkBuddy 等价于 `automation_update(mode="create", rrule="FREQ=DAILY;BYHOUR=16;BYMINUTE=0")`）。

执行链路与人工执行完全一致（`run_all.py` 六环节 + 抽帧自检 + 发布），差异只在于三处强制项：图库 Key 前置检查、成片抽帧目检、发布封面必须重绘。不想自动发布时删掉提示词中的「第六步」即可。

## 不可回归的约束

1. **逐字稿先行**：先生成并校验 `work/逐字稿_<date>.md`，再生成配音和字幕。
2. **同一文本源**：卡片正文、逐字稿、TTS 输入、字幕文本必须来自同一份完整句；人工改稿后先回写 narration，再重生成 TTS。
3. **禁止字符硬截断**：超时或过长时重写成更短的完整句，不能截成"研究团队称……"这类残句；每句必须以完整标点结束。具体规则（2026-10-21 残句事故后加固）：
   - 口播要点优先取**第一条完整句**；超长时**只允许在中文标点（，、；：）边界**截切；
   - **绝不在 ASCII 空格处截切**——英文词间空格不是语义边界（`tts_normalize` 插入的助读空格更不是）；
   - 找不到中文标点边界时**整句保留或放弃该口播要点**，不出半句话；
   - 每句结尾必须是 `。！？；`（逗号切分的标题子句统一补句号）；
   - 三层防线：`_spoken_bullet` 构造期不出残句 → `assemble_item_clauses` 组装期审计丢弃 → `validate_output` 渲染前判 ERROR 阻断；回归用例见 `tests/test_spoken_clause.py`，事故记录见 [口播完整性](references/spoken-clause-completeness.md)。
4. **时间轴连续**：每个 clause 满足 `start < end`，字符边界位于句内；音频、字幕和场景使用同一时间基准。
5. **封面分工**：流水线用 Remotion still 生成 `out/<date>/covers/` 下 3:4 / 4:3 / 16:9 PNG（预览与备用）；**发布用 JPG 封面必须由外部 video-upload 的 codebase-style 大字模板重绘**，并在 run_report/manifest 标明实际采用文件。禁止把视频首帧或 PNG 直接裁切当发布封面。
6. **配图硬要求**：每条新闻必须真实实拍照片；文字卡/海报卡/满屏文字截图不得进入正式成片。图库兜底失效（Pexels/Pixabay Key 缺失）时流水线打 CRITICAL 并由 validate_output 判 ERROR 阻断渲染，**不提供海报卡兜底**（海报卡仅允许出现在开发/冒烟 fixture）。
7. **输出可交接**：视频结束前更新项目根 `handoff.md`，同日期更新原条目，不重复追加。

## 推荐流程

一键流程（run_all.py 依次执行 parse → fetch → tts → render → gen_publish → finalize）：

```bash
cd <PROJECT_ROOT>/skills/todayaihot
python scripts/run_all.py "<news.md 绝对路径>" --backend edge --concurrency 1
```

分环节执行用 `--only parse|fetch|tts|render`（2026-10-28 起 `--only render` 同样补跑 gen_publish/finalize，E14）；render 前会自动跑 validate_output，ERROR 即中止。

### 发布就绪状态门（2026-10-28 P0-1 收紧）

`finalize.py` 的状态语义：`BLOCKED`（TTS 失败句 / 混音失败 / 成片不可测，不得发布）＞`GENERATED`（成片可用但必选质量检查未完成）＞`READY`（物料齐全 + 混音/响度实测合格 + 人工审图与片尾检查已有记录）。规则：

- `run_report.json` 的 `quality.images_reviewed` / `tail_frame_checked` 默认 false；人工抽帧审图并确认末帧后**直接改该文件对应字段为 true（可填 reviewed_by）**，再重跑 `finalize.py` 即升级 READY。
- 审阅记录与 `quality.video_sha256` 绑定：重渲染产生新哈希 → 旧审阅自动失效，必须重审。
- 平台发布回执同样绑定视频哈希：新版成片不继承旧版回执。
- 响度门：-14±1 LUFS、真峰值 ≤ -1 dBTP；未测按未通过处理。
- 启动时 run_all 获取流水线互斥锁（work/.pipeline.lock），并发/重入直接拒绝；render 校验 timeline 与 master.wav 的 SHA256 同源。

### 显示稿与朗读稿（2026-10-28 P1-5）

- narration 条目 `visual.title` 为**显示稿**（官方拼写 `GPT-6.1`/`M3.1`/`150GB` 原样）；`title_tts` 为**朗读稿**（助读拼写）。口播/字幕消费朗读稿，画面标题/章节/发布物料消费显示稿；助读空格不得进入用户可见文案。
- NewsItem 标题与正文把型号/数值渲染为 nowrap 词元，`M3.1` 等不再拆行；正文 40px、配图区上限 300px（排版预算见 pipeline-contract.md）。
- 开场钩子主体/动作/对象必须同条同源（`_hook_triples`），对象按词元边界截断，禁止「X直接Y」无对象残句。
- fetch 生成配图溯源清单 `work/image_manifest.json`（review=pending），审图后逐条回填；反例样本在 `assets/imgsamples/`。

## Remotion 前端约定

- 画布：1080×1920，30fps；时间常量统一放在 `remotion/src/videoConfig.ts`。
- 首帧：3 帧静音 `TitleCard`；音频末尾默认保留 1.5 秒缓冲。
- `TitleCard` 与 `CoverImage` 共用 `components/CodebaseCover.tsx`。
- 配图使用 `staticFile()`，不使用 `objectFit: cover` 裁切新闻主体；无图阻断正式成片（见约束 6）。
- 字幕分页不拆英文/数字单词，帧率从 `useVideoConfig()` 获取，不在组件内重复硬编码。
- 渲染前运行 `npm run typecheck`；新增颜色 token、时间常量或组件 props 时必须同步类型，不能依赖 `any` 掩盖输入错误。

## 相关参考

- [定时任务提示词](references/automation-prompt.md)：可直接投喂任意 agent 的无人值守任务模板。
- [流水线契约](references/pipeline-contract.md)：narration、timeline、音频、封面和 handoff 的数据不变量。
- [封面规范](references/cover-style.md)：codebase-style 首帧和多比例封面要求。
- [开场钩子库](references/hooks.md)：口播开场动态钩子类型与选择规则。
- [口播完整性](references/spoken-clause-completeness.md)：2026-10-21 残句事故的根因、修复与三层防线。
- [还原检查清单](references/recovery-checklist.md)：仅当流水线文件意外缺失时的排查清单。
- [历史优化方案](../../docs/todayaihot-优化方案-20260914.md)：2026-09-14 的优先级 backlog，部分结论已被 2026-10-14 审阅修正。
- [当前优化方案](../../docs/research/main-AI日报视频优化方案-20261014.md)：2026-10-14 审阅报告与 T0—T10 实施计划。
