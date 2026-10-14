# 2026-10-14 成片审阅证据

项目根目录：`E:\workbuddy-workspace\todaynew`。

## 采样与限制

- 三个样本为 `out/2026-10-12`、`out/2026-10-13`、`out/2026-10-14` 中文件名以当天日期结尾的正式 MP4；排除 `_nobgm.mp4` 中间片。
- 每期抽取 0、1、2 秒，以及各章节的中点，再抽尾部 1.2、0.5、0.1 秒附近。章节来自各期 `chapters.json`；10-14 与当前 timeline 核对。
- 原帧是 1080×1920 JPG；联系表只缩小展示，不是重新渲染。10-13 的 51.80 秒抽帧无输出，因此该期14帧，其他两期各15帧，共44帧。失败点没有用旧图补齐。
- 成片画面已按联系表及关键原帧目检。没有人工完整听审、ASR 对照、逐帧全片验收、新闻原文真实性核验或平台留存分析。
- 元数据通过项目 bundled FFmpeg 的 `-i` stderr 提取。该探测命令因未指定输出会返回非零，这是工具用法特征，不代表 MP4 损坏。
- PCM 指标来自成片解码为24kHz单声道，反映该解码口径的样本峰值/RMS；不等于原始TTS的PCM峰值，也不等于LUFS或真峰值。
- LUFS/真峰值来自 `loudnorm` 的 `input_i`/`input_tp`。对应日志内 `output_*` 是测量命令生成并丢弃的临时流，未写回视频。
- `input-snapshot.json` 记录本次现有解释器和依赖版本；本次没有安装/升级依赖。运行环境工具 `load_workspace_dependencies` 返回无效请求后，使用已存在且能运行的 `C:\Python313\python.exe` 提取证据，不将其作为新装位置建议。

## 文件说明

| 文件 | 内容 |
|---|---|
| `media-audit.json` | 视频绝对路径、SHA256、大小、时长、抽帧列表、PCM指标、物料存在性 |
| `loudness-audit.json`、`*-loudness.txt` | 三期原片LUFS/TP/LRA实测与原始日志 |
| `*-probe.txt` | 原始容器与流信息 |
| `*-contact.jpg`、`2026-10-*-<秒数>.jpg` | 三期联系表及原尺寸抽帧 |
| `ffmpeg-capabilities.txt` | 实际滤镜列表，包含loudnorm/amix，缺少asplit/aloop/sidechaincompress；列表能力仍需真实链路预检 |
| `validate-output.txt` | 当日既有校验器输出，退出码0、0 ERROR/8 WARN |
| `code-anchors.json` | 报告引用的源代码位置与原行文本 |
| `input-snapshot.json` | 当前技能、提示词、narration、timeline、public master的SHA256与实际依赖版本 |
| `2026-10-14-narration.json`、`2026-10-14-timeline.json` | 本次只读快照，防止次日work覆盖导致证据丢失 |
| `handoff-before-review.md` | 精简前完整交接，41,892字节；其中旧平台状态未经本次重验 |

## 可复核命令

在项目根目录使用PowerShell。所有命令只读取既有输入；不要为复核运行parse/fetch/smoke，它们目前会改变共享状态。

```powershell
$auditFF = 'E:\workbuddy-workspace\todaynew\remotion\node_modules\@remotion\compositor-win32-x64-msvc\ffmpeg.exe'
$auditVideo = 'E:\workbuddy-workspace\todaynew\out\2026-10-14\每日ai热门新闻-2026-10-14.mp4'
& $auditFF -hide_banner -i $auditVideo
& $auditFF -hide_banner -filters
& $auditFF -hide_banner -nostats -i $auditVideo -vn -af 'loudnorm=I=-14:TP=-1:LRA=11:print_format=json' -c:a pcm_s16le -f wav - > $null
& 'C:\Python313\python.exe' -X utf8 skills/todayaihot/scripts/validate_output.py
Get-FileHash -Algorithm SHA256 -LiteralPath $auditVideo
```

抽帧复核可将一个新的目标路径传给以下命令，避免覆盖本次证据：

```powershell
& $auditFF -hide_banner -ss 6.36 -i $auditVideo -frames:v 1 '<新的抽帧绝对路径>.jpg'
```

最终方案见 [main-AI日报视频优化方案-20261014.md](../../main-AI日报视频优化方案-20261014.md)。
