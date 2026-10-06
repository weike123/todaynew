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
  "scenes": [
    {
      "id": "s1_item",
      "visual": {"type": "news_item"},
      "clauses": [
        {
          "text": "完整句。",
          "start": 0.1,
          "end": 3.2,
          "chars": [{"char": "完", "t": 0.1}]
        }
      ]
    }
  ]
}
```

不变量：

- `start < end`；相邻句不交叠，除非明确使用了转场层；
- `chars` 的 `t` 为句内相对时间，且不超过句子时长；
- 最终音频时长与 `master_duration` 的偏差必须被报告；
- Remotion 场景从 clause 起点计算，末场景结束后加固定尾部缓冲；
- 缺失 scene、空 clauses 或坏时间轴要在渲染前报错/降级，不能让前端在 `clauses[0]` 处崩溃。

## 文本与字幕

逐字稿是人工可审阅的单一真源。修订后必须重新生成 TTS 和 timeline，不允许只改字幕 JSON 或只改卡片文案。中文分页可以采用项目现有手写逻辑，但不能拆开英文/数字单词。

## handoff

每次视频会话结束时更新根目录 `handoff.md`。同一日期只保留一个自动登记块；主视频路径必须是绝对路径，封面、逐字稿、配音、时间轴、时长和分辨率尽量一并记录。
