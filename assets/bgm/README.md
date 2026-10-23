# BGM 目录

放入免版权背景音乐（.mp3 / .wav / .ogg / .m4a），render.py 会自动扫描并随机选一首做人声闪避混音。

## 仓库已内置 20 首

本目录随仓库入库 **20 首精选免版权 BGM（约 92MB）**，覆盖 4 种调性，
clone 后无需额外准备即可直接渲染：

| 调性 | 首数 | 适合场景 |
|---|---|---|
| ambient（氛围） | 5 | 科技资讯、缓慢叙述 |
| chill（舒缓） | 5 | 日常速览、访谈类 |
| lofi（律动） | 5 | 节奏感强的条目播报 |
| upbeat（明快） | 5 | 快讯、结论段落 |

> 选曲逻辑：`render.py` 的 `find_bgm()` 用「日期 + 音频时长」做哈希种子确定性选曲，
> 同一天重复渲染选到同一首（可复现），不同日期自动错开，避免连续多条视频撞曲。

## 追加自己的 BGM

把免版权音乐放进本目录即可，**无需改任何代码**——`find_bgm()` 会自动扫描。

注意：本仓库的 `.gitignore` 只对上面那 20 首做了白名单放行，
你自己新增的音频默认**不会**被提交（避免仓库体积失控）。若确实想入库，
需在 `.gitignore` 中为该文件加一行 `!assets/bgm/<filename>.mp3`。

## 推荐来源（免商用授权）

- Pixabay Music: https://pixabay.com/music/
- YouTube Audio Library: https://studio.youtube.com/channel/UC-9-kyTW8ZkZNDHQJ6FgpwQ/music
- Free Music Archive: https://freemusicarchive.org/
- Bensound: https://www.bensounds.com/（需署名）

## 选择建议

- 口播类视频选纯音乐（无人声），BPM 90-120
- 音量不要盖过人声，脚本会自动做 sidechaincompress 闪避（人声说话时 BGM 压低 18-20dB）
- 时长建议 1-3 分钟，脚本会自动循环对齐成片时长

## 无 BGM 时

如果此目录为空，`render.py` 会跳过 BGM 混音，仅做 -14 LUFS 响度归一化，不影响成片。
也可以显式加 `--no-bgm` 关闭。

## 授权说明

内置曲目来自 Pixabay 等免版权来源，遵循各自原始授权条款，
**不适用**本仓库的 MIT 许可证（见根目录 LICENSE）。
