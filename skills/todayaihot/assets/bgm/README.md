# BGM 目录

放入免版权背景音乐（.mp3 / .wav / .ogg / .m4a），render.py 会自动扫描并随机选一首做人声闪避混音。

## 推荐来源（免商用授权）

- Pixabay Music: https://pixabay.com/music/
- YouTube Audio Library: https://studio.youtube.com/channel/UC-9-kyTW8ZkZNDHQJ6FgpwQ/music
- Free Music Archive: https://freemusicarchive.org/
- Bensound: https://www.bensound.com/（需署名）

## 选择建议

- 口播类视频选纯音乐（无人声），BPM 90-120
- 音量不要盖过人声，脚本会自动做 sidechaincompress 闪避（人声说话时 BGM 压低 18-20dB）
- 时长建议 1-3 分钟，脚本会自动循环对齐成片时长

## 无 BGM 时

如果此目录为空，render.py 会跳过 BGM 混音，仅做 -14 LUFS 响度归一化，不影响成片。
