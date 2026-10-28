# 2026-10-28 成片审阅证据

本目录是一次只读审阅的结果；原视频、工作稿及线上状态没有被修改。结论和实施建议见[优化方案](../../main-AI日报视频优化方案-20261028.md)。

- [媒体摘要](media-summary.json)：三个 MP4 路径、SHA256、大小、容器与视频流时长、帧率、编码、采样率、报告哈希比对及抽帧时间。
- [音频摘要](audio-summary.json)：对最终成片使用 `ffmpeg -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -` 分析，记录 `input_i`、`input_tp` 和 `input_lra`，没有改写音轨。各日期目录保留 `loudnorm.log` 和 `ffprobe.json`。
- 联系表及原尺寸 JPG：[10-27](2026-10-27/contact-sheet.jpg)、[10-26](2026-10-26/contact-sheet.jpg)、[10-24](2026-10-24/contact-sheet.jpg)。每期 15 个时间点：起始 0、2/30、4/30、2 秒，七条新闻中点，片尾四点；10-27 中点来自当日 timeline，另外两期来自章节起始时间。最后一点按视频流终点计算，而非音频较长的容器终点。
- [narration.json](narration.json) / [timeline.json](timeline.json)：审阅时 `work/` 的 10-27 快照，不能假设它们仍是当前运行状态。各日期目录保存审阅时存在的报告、章节及发布物料；10-24 原目录无 run_report。
- [流水线隔离复现](pipeline-reproductions.md)：状态门、按日期写交接、来源 URL 和章节格式的临时 fixture 与日志，不修改正式文件。
- [pytest.log](pytest.log)、[typecheck.log](typecheck.log)、[validate-output.log](validate-output.log)：分别为 80 passed、类型检查通过、0 ERROR / 6 WARN。
- [source-hashes.json](source-hashes.json)：审阅时 30 个相关源码文件的内容哈希；[审阅前完整交接快照](handoff-before-review.md)保存压缩前的历史登记，另有 [10-14 审阅时快照](../2026-10-14/handoff-before-review.md)。

可在项目根目录复测（只读）：

```powershell
python -X utf8 -m pytest skills/todayaihot/tests/ -q
python -X utf8 skills/todayaihot/scripts/validate_output.py
Set-Location remotion
npm run typecheck
```

帧图只覆盖采样时刻，响度值只覆盖客观音频指标；没有对视频进行完整人工听审、真机 UI 检查或全量新闻核实。采样中间过程中曾以容器终点抽取末帧失败，原因是音频流长于视频流；最终联系表已按实际视频流长度取末帧。
