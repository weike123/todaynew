# 配图判别反例样本集（P1-2，2026-10-28）

`looks_like_text_image()` 四判据是「高置信度过滤器」而非完备判据：
本目录收录真实事故中的漏网/边界样本，供调阈值与人工审图对照。

| 文件 | 类型 | 说明 |
|---|---|---|
| `counterexample-1026-poster.jpg` | **漏判反例（文字卡/宣传板）** | 10-26 成片第 1 条 7.755s 画面：白底英文宣传文案板通过全部四判据进入成片。抽帧目检必须额外确认「图上是否有成句大字文案」。 |
| `counterexample-1026-workstation-valid.jpg` | **有效实拍（勿误杀参照）** | 10-26 成片第 7 条 48.055s 画面：真实工作站照片，属合格实拍；屏幕中出现界面**不等于**海报。 |

## 人工审图流程（与 `work/image_manifest.json` 配合）

1. fetch 阶段生成逐图溯源清单：`work/image_manifest.json`（file/source/url/query/review=pending）。
2. 成片抽帧目检：逐条确认是照片而非文字卡/海报（对照本目录样本），并核对各条互不重复。
3. 把清单中每条 `review` 改为 `approved` / `rejected`（rejected 需换图重跑 TTS+render）。
4. 全部通过后在 `out/<date>/run_report.json` 置 `quality.images_reviewed=true`，重跑 finalize 升 READY。
