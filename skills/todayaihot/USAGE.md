# todayaihot 使用说明

## 当前状态（2026-10-14 核实）

`scripts/` 流水线、`work/` 中间产物、每日 `out/` 产物均已存在，可端到端运行：

| 环节 | 脚本 | 产物 |
|---|---|---|
| 解析 | `parse_news.py` | `work/narration.json` |
| 抓取富化 | `fetch_news.py` | 富化后的 narration + `remotion/public/images/` 配图 |
| 配音+时间轴 | `gen_tts.py` | `work/audio/master.wav` + `work/timeline.json` |
| 渲染 | `render.py` | `out/<date>/每日ai热门新闻-<date>.mp4` + `covers/` + `chapters.json` |
| 发布物料 | `gen_publish.py` | `out/<date>/publish.md` |
| 收尾 | `finalize.py` | `out/<date>/run_report.json` + `handoff.md` 登记 |

入口 `run_all.py` 依次串起以上全部环节；`--only <环节>` 可单独跑某一步（注意 `--only render` 不补 gen_publish/finalize）。

无人值守：用 [定时任务提示词](references/automation-prompt.md) 在任意 agent 中创建每日任务，无需改动代码。

## 运行环境

- 解释器：Python 3.10+（已验证 `python.exe` 含 requests/bs4/lxml/PIL/numpy/edge-tts；run_all 子进程复用同一解释器）。
- Remotion：`remotion/` 下 4.0.520，node 由 `render.py` 自动定位（WB_NODE → managed → 系统 PATH）。
- 密钥：只从项目根 `.env` 或环境变量读取（PEXELS_API_KEY / PIXABAY_API_KEY / VOLC_TTS_API_KEY），不写入代码、日志、交接文件。
- TTS 默认 `--backend edge`（云希 zh-CN-YunxiNeural，语速 +30%）；auto=火山优先失败降级；不主动拉起 GPT-SoVITS。

## 标准命令

```bash
cd <PROJECT_ROOT>/skills/todayaihot
python scripts/run_all.py "<news.md 绝对路径>" --backend edge --concurrency 1
```

- `--concurrency 1`：本机渲染并发保守值（曾因并发 2 OOM）；后续按实测耗时/内存再调。
- `--force-tts`：仅在人工改稿后需要全量重合成时使用；正常情况下缓存按内容+配置指纹复用。
- 渲染约 1—4 分钟，建议后台执行；完成后用 ffprobe 校验时长与 50—60 秒目标。

## 封面分工（硬要求）

- 流水线产出 `out/<date>/covers/cover_3x4.png`、`cover_4x3.png`、`cover_16x9.png`（codebase-style 大字模板，Remotion still 渲染），用于预览与备用。
- **发布用 JPG 封面由外部 video-upload 的大字模板重绘**，run_report 需标明实际采用文件；严禁传 `--cover-*` 参数绕过重绘，严禁用 ffmpeg 从成片首帧裁切。

## 关键验收

- 逐字稿句子完整，字幕与 TTS 使用同一文本；
- master 音频时长与 timeline 记录偏差可解释；
- 主视频为 1080×1920、30fps，有音轨，实测宽高/时长/哈希写入 run_report；
- 七条配图均为真实实拍照片且互不重复（md5 去重），来源非空；
- KTV 字幕黄白高亮正常，最长术语不超两行；
- `handoff.md` 记录日期、主题、简介、绝对视频路径、封面、字幕/配音、时长和分辨率。
