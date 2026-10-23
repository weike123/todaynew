# 流水线文件缺失时的排查清单（异常恢复参考）

> 本清单仅在 `scripts/`、`work/`、`out/` 意外缺失（误删、junction 断裂、换机）时使用。
> 当前仓库流水线完整（2026-10-14 核实），正常运行不要按本清单操作。

## 必查

1. `skills/todayaihot/SKILL.md` 与 `scripts/` 是否真实存在；项目内该目录是指向用户级 skill 目录的 junction，检查链接是否断裂。
2. `remotion/src/Root.tsx` 引用的 `work/timeline.json` 是否由上游脚本生成；没有就不要直接运行 render。
3. `remotion/public/audio/master.wav`、`public/images/` 是否存在且与 timeline 同一日期。
4. `package.json` 与 `package-lock.json` 的 Remotion 版本是否一致并锁定。
5. `TitleCard`、`CoverImage` 是否共用 codebase-style 组件。
6. `.env` 是否只存本机密钥，且没有被纳入版本控制。

## 恢复顺序

先恢复 Python 流水线和依赖，再恢复当日新闻/配音/图片中间产物，最后运行校验和 Remotion preview。不要先创建一份假的 timeline 来冒充完整恢复；如果需要前端开发，使用独立 fixture，并明确标注为 fixture。
