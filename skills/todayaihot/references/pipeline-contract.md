# todayaihot 流水线契约

## narration.json

至少保留日期、标题、总条数和 scenes。每个新闻 scene 的 `visual` 保存卡片展示内容；`clauses` 保存实际口播句。卡片 bullets 可以比口播更详细，但口播句不能由卡片文字再做字符截断得到。

## timeline.json

至少包含：

```json
{
  "date": "YYYY-MM-DD",
  "master_duration": 45.5,
  "content_duration": 45.4,
  "tts_backend": "edge",
  "align_mode": "auto",
  "failed_clauses": [],
  "narration": {"date": "YYYY-MM-DD", "scenes": []},
  "scenes": [
    {
      "id": "s1_item",
      "clauses": [
        {
          "i": 0,
          "text": "完整句。",
          "start": 0.1,
          "end": 3.2,
          "duration": 3.1,
          "timing_src": "edge",
          "chars": [{"ch": "完", "t": 0.1}]
        }
      ]
    }
  ]
}
```

说明：`chars` 的字符键实际为 `ch`（与 gen_tts/前端 Subtitle.tsx 一致），历史文档写的 `char` 不再使用；`narration` 为内嵌稿件快照，validate_output 用它做文本指纹校验。narration.json 中 `clauses` 为纯字符串数组，timeline 中为 dict。

不变量：

- `start < end`；相邻句不交叠，除非明确使用了转场层；
- `chars` 的 `t` 为句内相对时间（相对所在 clause 起点），且不超过句子时长；
- `failed_clauses` 为空才算配音成功；静音占位不构成成功；
- 最终音频时长与 `master_duration` 的偏差必须被报告；
- Remotion 场景从 clause 起点计算，末场景结束后加固定尾部缓冲（videoConfig 中 1.5s）；
- 缺失 scene、空 clauses 或坏时间轴要在渲染前报错/降级，不能让前端在 `clauses[0]` 处崩溃。

## 文本与字幕

逐字稿是人工可审阅的单一真源。修订后必须重新生成 TTS 和 timeline，不允许只改字幕 JSON 或只改卡片文案。中文分页可以采用项目现有手写逻辑，但不能拆开英文/数字单词。

## 音频与混音

- master.wav 已含 0.1s 前置静音（TITLE_PAD）；**Remotion 端 Audio 必须从第 0 帧起播**，不得再套延迟 Sequence（否则静音双计，字幕相对配音整体早 0.1s，E10）。前端 `TITLE_CARD_FRAMES` 必须等于 `TITLE_PAD * FPS`。
- timeline 的 clause.start 含 TITLE_PAD；「wav 位置 = 视频时间」映射在 0 帧起播时严格成立，句起点取整误差 ≤ 1 帧。
- **末场景必须覆盖整个尾部缓冲**（master_duration + TAIL_BUFFER），缓冲区不得出现纯背景空尾（E11）。
- BGM 闪避混音与 LUFS 归一状态（成功/失败/所用文件）必须写入 run_report；失败不得伪装成完成。
- 混音前必须用真实微型链路预检 ffmpeg（asplit/aloop/sidechaincompress/amix/loudnorm 组合）；链路不可用时 BGM 模式在渲染前失败，不静默归档未混音成片。
- 成片后用 loudnorm 分析模式实测综合响度与真峰值（integrated_lufs / true_peak_dbtp）写入 run_report；项目内部目标 -14±1 LUFS、TP ≤ -1 dBTP（项目建议目标，非平台统一硬性要求）。
- 混音前后视频流 copy：帧数不变，AV 结束偏差 ≤ 1 帧目标（容器容差 0.15s）。

## 封面

- 流水线产 `out/<date>/covers/` 三比例 PNG（3:4 / 4:3 / 16:9），与首帧 TitleCard 同源（CodebaseCover.tsx）。
- 发布 JPG 由外部 video-upload 大字模板重绘；run_report/manifest 标明实际采用文件与来源（流水线 PNG / 外部重绘）。
- 禁止视频首帧裁切图、ffmpeg 垫底图充当发布封面。

## run_report 与 READY 门（2026-10-28 P0-1 落地）

run_report.json 在现有字段上扩充，语义：

- `status`: `READY`（物料齐全 + 混音/响度实测合格 + 人工审图与片尾检查已记录，可交外部发布）｜`GENERATED`（成片可用但必选质量检查未完成）｜`BLOCKED`（TTS 失败句 / 混音失败 / 成片不可测，不得发布）。
- `READY` 与 `quality.video_sha256` 绑定：人工审阅（images_reviewed / tail_frame_checked / reviewed_by）只对同一哈希有效，重渲染产生新哈希即自动失效；发布器须核对同一 SHA256。
- `video` 记录最终文件实测：path / sha256 / duration_sec / width / height / fps / streams（音视频流级时长与帧数，P0-2）；不用 master_duration 充数。
- `quality` 记录 video_sha256 / tts_failed / images_missing / images_reviewed / reviewed_by / audio_mix_ok / audio_mix_status / integrated_lufs / true_peak_dbtp / tail_frame_checked；0/null/false 为未测状态，绝不写成成功。
- 响度门：-14±1 LUFS、真峰值 ≤ -1 dBTP；未测按未通过处理（不能 READY）。
- 平台回执单独保存在 `publish`，finalize 合入时按视频哈希绑定：哈希一致原样保留；哈希不一致（新版成片）不继承旧回执；历史报告无哈希时继承但登记 `_legacy_without_sha`。

## handoff

每次视频会话结束时更新根目录 `handoff.md`。同一日期只保留一个自动登记块；主视频路径必须是绝对路径（P0-3），封面、逐字稿、配音、时间轴、时长和分辨率尽量一并记录。发布结果（平台/成功或失败/回执）由发布技能回写同一日期块，与生成信息分区展示。补做旧日 finalize 只在该日期块内替换，不得覆盖其他日期。文件超过 24 KiB 时自动把历史日期块归档到 `handoff-archive-<时间戳>.md`（保留当前日期与其后 2 个日期块）。

## 流水线互斥与输入绑定（P0-4）

- run_all 启动时在 `work/.pipeline.lock` 创建独占锁（记录 PID）；已有活锁时拒绝并发/重入，残留死锁自动接管。脚本异常退出后如需强制继续，先确认无实例再删锁文件。
- gen_tts 把 `master_sha256` 与 `master_voice` 写入 timeline；render 校验 timeline 与 master.wav 同源、内嵌 narration 日期一致，错配即阻断（提示重跑 gen_tts）。
