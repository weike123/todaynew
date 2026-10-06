# todayaihot 使用说明

## 当前还原状态

当前仓库已恢复 Remotion 前端和优化方案文档，但没有恢复以下流水线层文件：

- `scripts/parse_news.py`、`fetch_news.py`、`gen_tts.py`、`render.py` 等脚本；
- `requirements.txt`、`.env`、`work/timeline.json`、`remotion/public/audio/` 和新闻图片；
- 每日 `out/YYYY-MM-DD/` 运行产物。

因此当前可以继续维护和预览 Remotion 源码，但不能仅凭本目录声称已经完成“抓取 → TTS → 渲染”的端到端任务。先按 [还原检查清单](references/recovery-checklist.md) 补齐缺失层。

## 生成任务的标准顺序

```text
新闻 Markdown
  → narration.json
  → 逐字稿（人工可审阅）
  → narration 回写
  → TTS + word/Whisper 时间轴
  → validate_output
  → Remotion 主视频
  → 首帧/多比例封面
  → publish.md + run_report.json + handoff.md
```

## 关键验收

- 逐字稿句子完整，字幕与 TTS 使用同一文本；
- master 音频时长与 timeline 记录偏差可解释；
- 主视频为 1080×1920、30fps，有音轨；
- 封面包含渐变大标题、白色副标题、黄色胶囊和署名；
- `handoff.md` 记录日期、主题、简介、绝对视频路径、封面、字幕/配音、时长和分辨率。
