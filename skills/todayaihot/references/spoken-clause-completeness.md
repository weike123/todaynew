# 口播语义完整性：2026-10-21 残句事故与修复

> 状态：已修复并加固（2026-10-21）。本文记录根因、修复方案与三层防线，
> 后续修改 `fetch_news.py` / `tts_normalize.py` / `validate_output.py` 前必读。

## 事故现象

2026-10-21 成片（`out/2026-10-21/每日ai热门新闻-2026-10-21.mp4`，已发布抖音/B站）中，
第 1、3 条的口播配音与 KTV 字幕同时呈现**半句话**：

| 条目 | 来源要点（完整） | 成片实际口播（残句） |
| --- | --- | --- |
| DeepSeek 开源 DeepInfer | DeepSeek 将内部生产级推理框架 DeepInfer 全面开源，并同步开源高性能 Token 编解码组件 deepseek-recipe。 | DeepSeek 将内部生产级推理框架。 |
| AMD 与英特尔统一 x86 | AMD 与英特尔宣布在 PyTorch 的 x86 CPU 优化上合作，将各自优化整合进开源库 oneDNN…… | AMD 与英特尔宣布在 PyTorch 的 x86。 |

字幕组件（`remotion/src/components/Subtitle.tsx`）只分页渲染 clause 原文、不截断，
问题全部出在**数据层**：口播 clause 本身就是残句。

## 根因

`fetch_news.py::_spoken_bullet`（浓缩模式：标题归一化 ≤32 字的条目追加一条 ≤22 字要点口播）
的截切逻辑：

```python
cut = b[:MAX_BULLET_SPOKEN + 6]
for sep in ("，", "、", "；", " "):     # ← 空格是杀手
    p = cut.rfind(sep)
    if p >= MAX_BULLET_SPOKEN - 8:
        cut = cut[:p]
        break
```

要点首句超过 22 字、且窗口内没有中文标点时，循环退化到 **ASCII 空格**截切。
`DeepSeek 将内部生产级推理框架 DeepInfer 全面开源，…` 的第一个中文逗号在第 34 字，
超出 28 字窗口，于是切在 "框架" 后的英文词间空格上——主语宾语被切掉，
`ensure_period` 再补一个句号，残句就此生成并流入 narration.json → TTS → 字幕。

同类缺陷还有两处：

1. `tts_normalize.py::split_long_clause` 硬切兜底的标点集合含 ASCII 空格；
2. `build_bullets` 兜底 `sents[0][:BULLET_MAX + 6]` 直接硬切。

三者共同点：**把 ASCII 空格当语义边界**。`tts_normalize` 恰会给英文插入助读空格
（`DeepSeek → Deep Seek`、`x86 CPU → x86 C P U`），使空格截切更容易命中、更隐蔽。

## 修复方案（2026-10-21）

### 1. `_spoken_bullet` 重写（构造期不出残句）

```text
1. 第一条完整句（按 。！？； 切）且 ≤ COMPLETE_SENT_MAX(36) 字 → 整句口播；
2. 超长 → 只在前 36+8 字符内找最后一个中文标点（，、；：）截切；
3. 找不到边界 → 返回 ""（宁可不口播，不出半句话）。
```

- 截切候选标点**移除 ASCII 空格**；截切结果最短 10 字（`MIN_SPOKEN`）。
- 截切前先过 `clean_for_tts`，与标题子句同形态。
- 修复后两条事故条目变为：
  - `Deep Seek 将内部生产级推理框架 DeepInfer 全面开源。`
  - `A M D 与英特尔宣布在 PyTorch 的 x86 C P U 优化上合作。`
  （口播总字数 374→404 raw / 320→341 非空白，预估时长仍在 60s 硬门内。）

### 2. `assemble_item_clauses` 组装期审计（纵深防御）

新增 `audit_spoken_clause(clause, bullets)`：子句（清洗后去尾句号）若是某要点
（清洗后）的**严格前缀**，截点后一个字符必须是中文标点边界（哨兵 `|`），
否则判残句 → **丢弃该子句并打日志**，不中断流水线。
无法对应到来源要点的子句（标题句等）不误判。
fetch 主流程末尾还有一遍**全局审计**，覆盖人工改动 narration 的路径。

### 3. `validate_output.py` 渲染前硬门（ERROR 级）

`check_clause_completeness(narr)`：

1. 每个口播子句必须以 `。！？；` 结束，否则 ERROR；
2. 由 `visual.bullets` 派生的子句若为严格前缀且截点非中文标点边界，ERROR。

render 前自动执行，ERROR 即阻断——本次事故若有此门，成片根本不会渲染出来。

### 4. 关联修复

- `split_long_clause` 硬切兜底：只认中文标点；找不到边界**整句保留**交字幕分页
  （`PAGE_CHARS=32` 分页能正常显示超长 clause），不在空格/单词内部切。
- `build_bullets` 兜底首句超长时同样只做中文标点截切，找不到边界保留整句。
- `parse_news.build_script`：所有口播子句统一 `ensure_period`（逗号切分的标题子句
  此前的结尾标点会被 `clean_for_tts` 清掉，变成无标句子句）。
- `validate_output` 口播时长估算改按**非空白字符**计数：`tts_normalize` 插入的
  助读空格不占口播时长，raw 基数实测高估约 33%（374 raw 估 57.5s，实际 43.2s），
  修复残句后更会误报 >60s。改基数后当前片估 49.2s / 修复后估 52.5s，仍保守。

## 回归与验证

- `tests/test_spoken_clause.py`（19 用例）：真实事故样本复现 + 修复断言 +
  纵深防御（monkeypatch 让 `_spoken_bullet` 回归产出残句，组装层必须丢弃）+
  validate 硬门 + `split_long_clause` 不切空格。
- 全量 `pytest tests/`：70 passed。
- `validate_output.py` 对 2026-10-21 已发布成片的 narration.json 实跑：
  精确报出 2 条残句 ERROR、无雾报。

## 已发布成片的处置

2026-10-21 抖音/B站成片含 2 条残句口播（发布时无此硬门）。按"不静默重发"原则：
- 未重新渲染、未重新发布（用户 2026-10-21 明确不重新生成视频）；
- 已在 `handoff.md` 登记缺陷与修复选项；如需更正版，cookie 恢复后按
  完整流水线重跑（parse→fetch→tts→render）再单平台补发，并先与用户确认
  旧版处置方式。

## 经验（写进 SKILL.md 约束 #3）

1. 字幕/配音呈现的半句话，先查数据层（narration/timeline），渲染组件只是传声筒。
2. 凡"截断"必问：截点是不是语义边界？中文标点才是，ASCII 空格从来不是。
3. 助读变换（英文加空格、缩写拼读）会改变字符索引，截切逻辑必须放在变换之后、
   且只认变换后依然稳定的边界（中文标点）。
4. 安全类缺陷要三层防线：构造期不出 → 组装期审计丢 → 渲染前 ERROR 阻断，
   单点修复迟早被下一次改动绕开。
