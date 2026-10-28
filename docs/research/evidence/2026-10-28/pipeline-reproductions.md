# 流水线审阅：隔离复现与发布物料证据

> 日期：2026-10-28（Asia/Shanghai）  
> 项目：`E:\workbuddy-workspace\todaynew`  
> 范围：调用当前函数进行隔离复现、读取 2026-10-27 既有物料；未修改产品代码、正式 `work/`、正式 `handoff.md`，未生成或发布视频。

## 1. 结论与证据边界

| 检查 | 实际结果 | 当前依据 |
|---|---|---|
| 质量失败报告传入 READY 判定 | 返回 `('READY', [])` | `skills/todayaihot/scripts/finalize.py:132-157` |
| 两个日期登记，回写较早日期 | 最新日期内容消失，较早日期出现两次 | `skills/todayaihot/scripts/finalize.py:242-254` |
| 空来源名生成置顶评论 | 生成 `[]`，原文 URL 不输出 | `skills/todayaihot/scripts/gen_publish.py:105-116` |
| 已人工改成数组格式的 chapters 输入简介生成 | 章节标题被静默省略 | `skills/todayaihot/scripts/gen_publish.py:87-97` |
| 10-27 既有 publish.md | 不含 HTTP(S) URL；仍有九个“第N条”章节 | `out/2026-10-27/publish.md:23-43` |

第一项是对 `evaluate_status` 的直接函数测试：报告中的元信息是受控 fixture，未伪造真实 MP4 的探测结果。它证明状态判定忽略失败质量字段，不表示最新三期真实 MP4 含 TTS 失败。第二项仅用临时 handoff 复现日期替换范围错误，未改动正式交接。

## 2. 当前源码位置与根因

### 2.1 READY 忽略质量字段

- `finalize.py:113-120` 创建 `quality`，其中 `images_reviewed` 和 `tail_frame_checked` 默认 `False`，另记录 TTS 失败、混音状态和响度。
- `finalize.py:132-157` 仅判断视频路径、哈希、是否有音轨、分辨率、非空帧率、正时长，以及发布物料/封面文件是否存在；没有读取 `quality`。所以质量字段明确失败仍可返回 READY。
- 相关联的生产路径：`render.py:427-438` 在混音失败后选用未处理原片归档，`:460` 失败时不测响度，`:469` 仍返回 0。不能仅因渲染进程返回成功便认为混音通过。
- 测试缺口：`tests/test_finalize.py:65-77` 当前“物料齐即 READY”测试使用空章节与仅 PNG 签名的文件，未验证真实封面、章节内容及质量结论。

### 2.2 handoff 日期范围错误与回执版本问题

- `finalize.py:243-244` 先检查当天自动登记段是否存在。
- `finalize.py:247-249` 随后在**整份 content** 中替换首个 `finalize:begin/end` 区块，`count=1`，没有把替换约束在匹配到的当天段内。
- 当最新一天排在前面、补做较早一天 finalize 时，会覆盖最新一天的 finalize 内容，原较早日期内容仍保留，产生旧日重复。
- 本复现仅把 `_handoff_generation_block` 替换成精简 fixture 格式以排除无关媒体字段；保留当前 `update_handoff` 的日期匹配与正则替换逻辑。
- 邻近风险：`finalize.py:169-170` 原样继承旧 `publish`，没有比较新旧视频哈希；回执应关联已发布的视频版本。`:174-183,204` 生成相对视频路径，与项目要求的绝对路径有冲突。

### 2.3 为什么 10-27 来源显示 `[]`，且没有原文 URL

- 当前 `work/narration.json` 与 `work/timeline.json` 日期均为 2026-10-27；七个新闻场景的 `visual.source` 都是空字符串，而 `link` 和 `original_url` 均存在。本次只读取这些文件，没有重跑 parse/fetch。
- `parse_news.py:193` 将 source 初始化为空。`:280-289` 能从“原文 URL”提取 link，但没有明确来源名称时不会凭空填出名称。提示词要求的 `原文：<直链>` 格式本身不保证来源名非空。
- `gen_publish.py:138-142` 将 `source` 与 `link` 放进 items；`:111` 的 `it.get('source', '未知来源')` 只处理键不存在，不能处理已存在的空字符串；`:113` 把空串包在方括号里，因此输出 `[]`。这不是 source 被转换成 Python 列表。
- `gen_pinned_comment` 从未把 `it['link']` 写到文本中，`gen_description` 也不输出来源 URL。虽已从 narration 取出 link，生成物料时并未使用。
- 实际文件 `out/2026-10-27/publish.md:39-43` 有五个 `[]` 来源条目，全文没有 HTTP(S) URL；后两条新闻也因 `items[:5]` 没进入置顶来源汇总。
- 建议：保留完整原文链接，并以明确来源名或 URL 的域名作可解释兜底；覆盖全部新闻，不能把“来源汇总”生成为无链接的五条截断标题。

### 2.4 为什么 publish.md 仍是“第N条”，而 chapters.json 已有标题

- `gen_tts.py:268` 创建 timeline scene 时仅放 `id` 和 `clauses`；`:323-324` 将完整 narration 单独内嵌到 `timeline.narration`。
- `render.py:239-250` 却从 `timeline.scenes[].visual` 读取场景类型和标题；当前这些 scene 没有 visual，因而九个场景全部走“第N条”兜底，连开场和结尾也被编号。
- `gen_publish.py:87-95` 把生成时已有的章节 dict 复制进简介；本期 `publish.md:24-32` 因此保留九个占位标题。
- 当前 `out/2026-10-27/chapters.json` 已是九元素顶层 list，包含开场、七条新闻、结尾；若干标题仍有硬截断英文词。它与 publish.md 的章名不一致。`references/automation-prompt.md:211` 明确要求渲染后人工回写“第N条”，与这种产物分叉相符；本次没有完整执行日志，不能据此确定手工改写的确切时点。
- 更进一步：当前 `gen_description` 预期 dict 并调用 `ch.get('chapters', [])`。若对现有 list 章节重新运行，会触发 `AttributeError`，然后被 `except Exception: pass` 吞掉；章节导航标题可能保留，但所有章节条目被省略。隔离 fixture 已复现 `list_chapters_preserved=False`。
- 建议：按 scene id 从内嵌 narration 取语义短标题；冻结唯一章节 schema；生成简介使用同一份正式章节数据。修复不能只在发布时改一次 JSON。

## 3. 可复跑命令（PowerShell）

运行目录为项目根。所有写操作仅落在 Python `TemporaryDirectory` 中，退出后清理；`gen_pinned_comment` 和 `gen_description` 只构造字符串；最后两项只读正式 publish.md。示例 URL 使用保留的 `.invalid` 域名，不发网络请求。

```powershell
Set-Location 'E:\workbuddy-workspace\todaynew'
$probeCode = @'
import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'skills/todayaihot/scripts')
import finalize as f
import gen_publish as g

with tempfile.TemporaryDirectory(prefix='todayaihot-review-') as root:
    root = Path(root)
    artifact = root / 'artifact'
    artifact.write_text('fixture', encoding='utf-8')
    report = {
        'video': {'path': str(artifact), 'sha256': 'fixture',
                  'has_audio': True, 'width': 1080, 'height': 1920,
                  'fps': 30, 'duration_sec': 55},
        'artifacts': {'publish_md': str(artifact), 'chapters': str(artifact),
                      'covers': [str(artifact)]},
        'quality': {'tts_failed': ['failed'], 'images_reviewed': False,
                    'tail_frame_checked': False,
                    'audio_mix_status': 'bgm_duck:FAILED',
                    'integrated_lufs': None}
    }
    print('quality_failed_status=', f.evaluate_status(report))

    handoff = root / 'handoff.md'
    heading = '### \u81ea\u52a8\u767b\u8bb0\uff08'
    closing = '\uff09'
    def block(date):
        return (heading + date + closing + '\n' + f.FINALIZE_BEGIN
                + '\nDATE=' + date + '\n' + f.FINALIZE_END + '\n')
    handoff.write_text('# fixture\n\n' + block('2026-10-27') + '\n'
                       + block('2026-10-26'), encoding='utf-8')
    f._handoff_generation_block = lambda n, t, v, r: block(n['date'])
    f.update_handoff(str(handoff), {'date': '2026-10-26'}, {}, 'unused', {})
    after = handoff.read_text(encoding='utf-8')
    print('older_day_update_27_count=', after.count('DATE=2026-10-27'),
          '26_count=', after.count('DATE=2026-10-26'))

    comment = g.gen_pinned_comment([{
        'title': 'Fixture title', 'source': '',
        'link': 'https://example.invalid/source'
    }])
    print('empty_source_brackets=', '1. [] Fixture title' in comment)
    print('source_url_in_comment=', 'https://example.invalid/source' in comment)

    chapters = root / 'chapters.json'
    chapters.write_text('[{"time":"00:00","title":"Fixture chapter"}]',
                        encoding='utf-8')
    desc = g.gen_description([], '2026-10-27', str(chapters))
    print('list_chapters_preserved=', 'Fixture chapter' in desc)

publish = Path('out/2026-10-27/publish.md').read_text(encoding='utf-8')
print('actual_1027_publish_contains_url=', 'https://' in publish or 'http://' in publish)
print('actual_1027_publish_placeholder_count=',
      sum(1 for line in publish.splitlines()
          if line.startswith('00:') and '\u7b2c' in line))
'@
python -X utf8 -c $probeCode
```

实际执行退出码：`0`。日志：

```text
quality_failed_status= ('READY', [])
older_day_update_27_count= 0 26_count= 2
empty_source_brackets= True
source_url_in_comment= False
list_chapters_preserved= False
actual_1027_publish_contains_url= False
actual_1027_publish_placeholder_count= 9
```

这些结果是**缺陷复现证据**，不能写成实现修复的 Green。全量 pytest、TypeScript 类型检查与正式数据校验由主审统一记录，本文件不重复执行或冒称其结果。
