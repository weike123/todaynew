# 代码还原后的检查清单

## 必查

1. `skills/todayaihot/SKILL.md` 与 `scripts/` 是否真实存在；若只有文档，标记流水线层未恢复。
2. `remotion/src/Root.tsx` 引用的 `work/timeline.json` 是否由上游脚本生成；没有就不要直接运行 render。
3. `remotion/public/audio/master.wav`、`public/images/` 是否存在且与 timeline 同一日期。
4. `package.json` 与 `package-lock.json` 的 Remotion 版本是否一致并锁定。
5. `TitleCard`、`CoverImage` 是否共用 codebase-style 组件。
6. `.env` 是否只存本机密钥，且没有被纳入版本控制。

## 恢复顺序

先恢复 Python 流水线和依赖，再恢复当日新闻/配音/图片中间产物，最后运行校验和 Remotion preview。不要先创建一份假的 timeline 来冒充完整恢复；如果需要前端开发，使用独立 fixture，并明确标注为 fixture。
