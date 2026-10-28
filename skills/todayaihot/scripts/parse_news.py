"""解析「每日 AI 头条」news.md -> narration.json（口播稿 + 场景数据）

用法:
    python parse_news.py <news.md> [--out narration.json] [--max-sentences 3]

输出 schema 见脚本底部 build_narration()，供 gen_tts.py 与 Remotion 消费。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NARRATION, WORK_DIR  # noqa: E402
from tts_normalize import tts_normalize, split_long_clause  # noqa: E402

SEEN_TITLES_PATH = os.path.join(WORK_DIR, "seen_titles.json")
SEEN_DAYS = 7  # 跨天去重窗口（天）

# ---------------------------------------------------------------- 文本清洗

# 供 TTS 朗读的替换表（先长后短，避免相互覆盖）
TTS_REPLACES = [
    (r"\$(\d[\d.,]*)", r"\1 美元"),          # $0.14 -> 0.14 美元
    (r"≥", "大于等于"),
    (r"≤", "小于等于"),
    (r"~", "约"),
    (r"→", "到"),
    (r"&", "和"),
    (r"([\d万亿])\+", r"\1以上"),            # 15 万+ -> 15 万以上
    (r"\+", " 加 "),
    (r"/", "、"),                            # 斜杠读成停顿，避免 "slash"
    (r"\|", "，"),
]

SECTION_ALIAS = {
    "全球大模型": "全球大模型",
    "大模型": "全球大模型",
    "ai coding": "AI Coding",
    "ai编程": "AI Coding",
    "编程": "AI Coding",
    "开源项目": "开源项目",
    "开源": "开源项目",
}


def clean_for_tts(text: str, assist: bool = True) -> str:
    """把 markdown 正文洗成适合 TTS 朗读的纯中文口语文本。

    顺序很重要：先去 markdown 噪声，再做半角→全角标点归一
    （否则正文里的半角逗号无法作为断句依据）。

    assist=False（P1-5 显示稿模式）：跳过缩写助读与数值口语化替换，
    保留 `GPT-6.1`、`M3.1`、`150GB` 等官方拼写——显示稿与朗读稿
    必须从同一原文派生，但拼写形态分离，助读空格不得进入用户可见文案。
    """
    t = text.strip()
    # --- markdown 噪声 ---
    t = re.sub(r"https?://\S+", " ", t)     # 链接
    t = t.replace("`", "")                   # 代码反引号（保留内容）
    t = re.sub(r"\*\*|__", "", t)            # 粗体
    t = re.sub(r"^\s*#+\s*", "", t)          # 标题井号
    t = re.sub(r"<!--.*?-->", " ", t)        # 注释

    # --- 缩写定读 + 多音字处理（必须在标点归一之前，匹配原始半角缩写）---
    if assist:
        t = tts_normalize(t)

    # --- 数值保护：千分位与时间里的半角标点不能转成全角 ---
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)     # 1,100% -> 1100%
    # 16:00 -> 16点；10:30 -> 10点30分
    t = re.sub(
        r"(\d+):(\d{2})",
        lambda m: f"{m.group(1)}点" + ("" if m.group(2) == "00" else f"{int(m.group(2))}分"),
        t,
    )

    # --- 标点归一：半角 -> 全角 ---
    # 先清掉 "!N" 这类非句末感叹/问号，避免误断句
    t = re.sub(r"[!?](?=[0-9A-Za-z])", "", t)
    t = t.replace(",", "，").replace(";", "；").replace(":", "：")
    t = t.replace("!", "！").replace("?", "？")

    # --- 括号类 -> 空格（保留内容，避免 "GPU(RTX 4090)" 粘成 "GPURTX 4090"）---
    t = re.sub(r"[【】\[\]（）()《》<>]", " ", t)

    # --- 中英文引号：TTS 会读成「引号」，直接去掉（保留被包裹的内容）---
    t = re.sub(r"[“”„‟『』「」’‘]", "", t)
    t = t.replace('"', " ").replace("'", " ")

    # --- 数值/符号口语化（朗读专用；显示稿保留原符号）---
    if assist:
        for pat, rep in TTS_REPLACES:
            t = re.sub(pat, rep, t)

    # --- 收尾清理 ---
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"，{2,}", "，", t)
    t = re.sub(r"、{2,}", "、", t)
    t = re.sub(r"^[,，、.。;；:：\s]+", "", t)
    t = re.sub(r"[,，、\s]+$", "", t)
    return t.strip()


def split_sentences(text: str):
    """按中文句末标点切句，保留标点。"""
    parts = re.split(r"(?<=[。！？!?；;])", text)
    return [p.strip() for p in parts if p and p.strip()]


def merge_clauses(sentences, max_chars=26, min_chars=10):
    """把短句合并成适合做字幕的 clause（每行 <= max_chars）。"""
    clauses = []
    buf = ""
    for s in sentences:
        if not s:
            continue
        # 单句本身超长：按逗号再切（顿号不切，避免「Pro、Enterprise、Premium」
        # 这类英文品牌名列表被拆得支离破碎）
        if len(s) > max_chars:
            if buf:
                clauses.append(buf)
                buf = ""
            sub = re.split(r"(?<=[，,])", s)
            tmp = ""
            for piece in sub:
                if len(tmp) + len(piece) > max_chars and tmp:
                    clauses.append(tmp)
                    tmp = piece
                else:
                    tmp += piece
            if tmp:
                clauses.append(tmp)
            continue
        if len(buf) + len(s) > max_chars and len(buf) >= min_chars:
            clauses.append(buf)
            buf = s
        else:
            buf += s
    if buf:
        clauses.append(buf)
    return [c for c in clauses if clean_for_tts(c)]


# ---------------------------------------------------------------- MD 解析

HEAD_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
HEAD_WEEK = re.compile(r"[（(](周[一二三四五六日天])[）)]")
SEC_RE = re.compile(r"^##\s+(.+?)\s*$")
ITEM_RE = re.compile(r"^###\s+(\d+)[\.、\s]+(.+?)\s*$")          # 格式A: ### 1. 标题
LIST_ITEM_RE = re.compile(r"^(\d+)[\.、]\s+(.+?)\s*$")            # 格式B: 1. 标题
MD_LINK_RE = re.compile(r"^\[(.+?)\]\((.+?)\)\s*(.*)$")
BULLET_RE = re.compile(r"^[-*]\s+(.+?)\s*$")
TAG_RE = re.compile(r"^\**\s*标签\s*[:：]\**\s*(.+?)\s*$")
SRC_RE = re.compile(r"^\**\s*来源\s*[:：]\**\s*(.+?)\s*$")

# 格式C（每日 AI 新闻推送 md）：`**1. 标题**` + `核心：`/`细节：`/`价值：` 行
# 例：**1. OpenAI 官宣达成"自动化研究实习生"里程碑**
#     核心：OpenAI 发布内部研究加速报告...
BOLD_ITEM_RE = re.compile(r"^\*{1,2}\s*(\d+)[\.、]\s*(.+?)\s*\*{1,2}\s*$")
FIELD_RE = re.compile(r"^\**\s*(核心|细节|价值|影响|要点|摘要|看点)\s*[:：]\**\s*(.+?)\s*$")
ANY_URL_RE = re.compile(r"(https?://\S+)")

# 行内噪声（整行跳过）
NOISE_LINE_RE = re.compile(
    r"^(数据来源|时间窗|本期完|---+|\*{2,}).*"
)
# 整行括注噪声：`（今日 AI HOT 日报 flashes 为空，无补充快讯）`
PAREN_NOISE_RE = re.compile(r"^[（(].*(快讯|日报|完|END).*[）)]\s*$", re.I)

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _clean_source(raw: str) -> str:
    """「The Decoder · 北京时间 09-05 15:41」->「The Decoder」（朗读不需要时间戳）。"""
    s = raw.strip()
    s = re.sub(r"[（(]未进入精选[）)]", "", s)
    if "北京时间" in s:
        s = s.split("北京时间")[0]
    return s.strip(" ·，,；;")


def _new_item(index, title_rest, section):
    """兼容两种条目写法：[标题](url)（未进入精选） / 纯文本标题。"""
    title = title_rest
    link = ""
    m = MD_LINK_RE.match(title_rest)
    if m:
        title = m.group(1)
        link = m.group(2)
    title = re.sub(r"[（(]未进入精选[）)]", "", title).strip()
    return {
        "index": int(index),
        # P1-5：显示稿保留官方拼写（GPT-6.1 / M3.1），朗读稿单独派生 title_tts
        "title": clean_for_tts(title, assist=False),
        "title_tts": clean_for_tts(title),
        "section": section or "今日要闻",
        "link": link,
        "tags": [],
        "source": "",
        "body": "",
        "points": [],          # 格式C：核心/细节/价值 等要点（画面卡片展示，不上口播）
    }


def parse_markdown(md_text: str, fallback_date: str = ""):
    """解析 news.md，返回 (meta, items)。

    同时兼容两种每日产出格式：
      A) `### N. 标题` + `**标签：**` + 段落正文 + `**来源：**`
      B) `## 分类` + `N. [标题](url)` + `- 来源：xxx` + `- 正文`
    """
    m = HEAD_DATE.search(md_text)
    date = m.group(0) if m else fallback_date
    wm = HEAD_WEEK.search(md_text)
    weekday = wm.group(1) if wm else ""
    if not weekday and date:
        import datetime
        try:
            dt = datetime.date.fromisoformat(date)
            weekday = WEEKDAY_CN[dt.weekday()]
        except Exception:
            weekday = ""

    current_section = ""
    items = []
    cur = None
    body_lines: list[str] = []

    def flush_body():
        # 关键：body_lines 为空时不要覆写已有 body。
        # 「## 新章节」与「### 新条目」会连续触发两次 flush，
        # 若无此保护，每节最后一条的正文会被第二次空 flush 清空。
        if cur is not None and body_lines:
            cur["body"] = " ".join(x for x in body_lines if x).strip()

    for raw in md_text.splitlines():
        line = raw.rstrip()
        s = line.strip()

        if not s or s == "---" or s.startswith(">"):
            continue
        # 格式C：**1. 标题**（每日 AI 新闻推送 md，无 ## 章节也可识别）
        # 必须排在 NOISE_LINE_RE 之前：噪声规则会吃掉所有 `**` 开头的行
        mbo = BOLD_ITEM_RE.match(s)
        if mbo:
            flush_body()
            body_lines = []
            cur = _new_item(mbo.group(1), mbo.group(2), current_section)
            items.append(cur)
            continue

        if set(s) == {"-"} or NOISE_LINE_RE.match(s) or PAREN_NOISE_RE.match(s):
            continue

        ms = SEC_RE.match(s)
        if ms:
            flush_body()
            body_lines = []
            name = ms.group(1)
            name = re.sub(r"^[一二三四五六七八九十]+[、.\s]*", "", name).strip()
            name = re.sub(r"^\d+[、.\s]*", "", name).strip()
            current_section = SECTION_ALIAS.get(name.lower(), name)
            continue

        # 格式A：### 1. 标题
        mi = ITEM_RE.match(s)
        if mi:
            flush_body()
            body_lines = []
            cur = _new_item(mi.group(1), mi.group(2), current_section)
            items.append(cur)
            continue

        # 格式B：N. [标题](url)（须已在某个章节内，避免误伤正文里的编号）
        ml = LIST_ITEM_RE.match(s)
        if ml and current_section:
            flush_body()
            body_lines = []
            cur = _new_item(ml.group(1), ml.group(2), current_section)
            items.append(cur)
            continue

        if cur is None:
            continue

        # 格式C 的原文链接：行尾「原文：https://...」/「来源：IT之家 https://...」
        if not cur.get("link"):
            mu = ANY_URL_RE.search(s)
            if mu:
                cur["link"] = mu.group(1).rstrip("。，,；;）)")
                # 若链接前写了「来源：xxx」，把来源名留下来
                head = s[:mu.start()]
                ms_h = re.search(r"(?:来源|原文|来自)\s*[:：]\s*(.+?)\s*$", head)
                if ms_h and not cur.get("source"):
                    cur["source"] = _clean_source(ms_h.group(1))

        # 格式C 的要点行：核心：/ 细节：/ 价值：
        mf = FIELD_RE.match(s)
        if mf:
            val = ANY_URL_RE.sub("", mf.group(2))
            # 去掉被剥掉 URL 后残留的标签尾巴：「...。来源：IT之家」「...。原文：」
            val = re.sub(r"[。；;]\s*(?:原文|来源|链接|来自)\s*[:：].*$", "。", val)
            val = re.sub(r"(?:原文|来源|链接|来自)\s*[:：]\s*$", "", val).strip()
            if val:
                cur["points"].append(ensure_period(val))
                body_lines.append(val)
            continue

        # 列表子弹行：- 来源：xxx / - 正文
        mb = BULLET_RE.match(s)
        if mb and line.startswith((" ", "\t", "-")):
            content = mb.group(1)
            if content.startswith(("来源", "**来源")):
                cur["source"] = _clean_source(
                    ANY_URL_RE.sub("", re.sub(r"^\**\s*来源\s*[:：]\**\s*", "", content))
                )
            else:
                body_lines.append(content)
            continue

        mt = TAG_RE.match(s)
        if mt:
            cur["tags"] = [t.strip() for t in re.split(r"[/、,，|]", mt.group(1)) if t.strip()]
            continue

        msr = SRC_RE.match(s)
        if msr:
            cur["source"] = _clean_source(ANY_URL_RE.sub("", msr.group(1)).strip())
            continue

        if s.startswith("**") and s.endswith("**"):
            continue  # 其他粗体元信息行跳过

        body_lines.append(s)

    flush_body()
    return {"date": date, "weekday": weekday}, items


# ---------------------------------------------------------------- 口播稿生成

def pick_within_budget(clauses, max_clauses=5, max_chars=120):
    """摘要首句信息量最大，按顺序取，直到子句数或字数预算耗尽。

    短视频节奏：每条新闻 ~20s，过长会掉完播率。
    """
    picked, total = [], 0
    for c in clauses:
        if len(picked) >= max_clauses:
            break
        if picked and total + len(c) > max_chars:
            break
        picked.append(c)
        total += len(c)
    return picked


# ---------------------------------------------------------------- 开场钩子
HOOK_COMPANIES = (
    "OpenAI", "DeepSeek", "Google", "Meta", "NVIDIA", "Anthropic", "Microsoft",
    "Apple", "Amazon", "Tesla", "xAI", "Mistral", "Cohere", "Stability",
    "阿里", "腾讯", "百度", "字节", "华为", "小米", "美团", "京东",
    "通义", "豆包", "文心", "Kimi", "智谱", "月之暗面",
)
HOOK_ACTIONS = (
    "发布", "推出", "开源", "降价", "涨价", "收购", "投资", "突破",
    "超越", "提升", "上线", "关闭", "裁员", "融资", "上市", "合作",
    "集成", "支持", "修复", "更新",
)


def _extract_company(title: str) -> str:
    for c in HOOK_COMPANIES:
        if c in title:
            return c
    return ""


def _extract_action(title: str) -> str:
    for a in HOOK_ACTIONS:
        if a in title:
            return a
    return ""


def _extract_number(title: str) -> str:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|％|亿美元|亿|万美元|万|倍|GB|TB|参数)", title)
    if m:
        return m.group(0)
    m = re.search(r"[A-Za-z]+\d+(?:\.\d+)*", title)
    if m:
        return m.group(0)
    return ""


def _trim_object(obj: str, limit: int = 12) -> str:
    """按词元边界截断对象短语，绝不把 `GPT-6.1` 拦腰切成 `GPT-6.1 Terr` 残句。

    以空格分词整词累加（保留词间空格），超限即停；
    一个完整词都放不下时返回空串（调用方降级为无对象句式）。
    """
    out = ""
    for w in obj.split():
        cand = (out + " " + w).strip()
        if len(cand) > limit:
            break
        out = cand
    return out


def _hook_triples(items: list) -> list:
    """从同一条新闻标题内提取 (主体, 动作, 对象) 三元组（P1-3）。

    旧实现的致命缺陷：companies/actions 是跨条目各自收集后按下标拼接，
    会产出「Cohere直接发布」这类主体来自 A 条、动作来自 B 条的无对象残句。
    现在主体与动作必须出现在**同一条标题**里，对象取动作后的同句短语，
    并按词元边界截断（P1-3：钩子不得出现被切碎的残句形态）。
    """
    triples = []
    for it in items:
        t = it.get("title", "") or it.get("title_tts", "")
        c = _extract_company(t)
        a = _extract_action(t)
        if not (c and a):
            continue
        obj = ""
        ai = t.find(a)
        rest = t[ai + len(a):].strip(" ，,：:、")
        if rest:
            obj = re.split(r"[，,。；;：]", rest)[0].strip()
            obj = _trim_object(obj)
        triples.append((c, a, obj))
    return triples


def generate_hook(items: list, date: str, weekday: str) -> str:
    """根据当天新闻特征动态生成开场钩子，≤30 字（约 6 秒口播）。

    钩子类型按日期哈希轮换，优先级：H1 数字冲击 > H2 公司对比 > H3 结果前置 > H4 时间锚点。
    P1-3：主体/动作/对象必须同源（同一条新闻），不跨条拼接、不出无对象残句。
    """
    total = len(items)
    date_spoken = spoken_date(date)

    triples = _hook_triples(items)
    companies = [c for c, _, _ in triples]
    numbers = []
    for it in items:
        n = _extract_number(it.get("title", ""))
        if n and n not in numbers:
            numbers.append(n)

    day_hash = sum(ord(c) for c in date) % 4

    # H1 数字冲击：主体+动作+对象必须来自同一条新闻
    if (day_hash == 0 or day_hash == 2) and numbers and triples:
        c, a, obj = triples[0]
        if obj:
            sep_obj = " " if obj[0].isascii() else ""   # 拉丁宾语与动词之间留空格
            sep_c = " " if c[-1].isascii() and not a[0].isascii() else ""
            hook = f"今天 AI 圈有 {total} 件大事，{c}{sep_c}{a}{sep_obj}{obj}。"
            return hook if len(hook) <= 40 else f"今天 AI 圈有 {total} 件大事，先看{c}。"
        return f"今天 AI 圈有 {total} 件大事，{c}{a}了大事。"
    # H2 公司对比：两组主体/动作各自来自同一条新闻
    if (day_hash == 1 or day_hash == 3) and len(triples) >= 2:
        c1, a1, _ = triples[0]
        c2, a2, _ = triples[1]
        if c1 != c2:
            return f"{c1} 刚{a1}，{c2} 就{a2}。"
    # H3 结果前置
    if total >= 3:
        return f"60 秒速览今天最值得关注的 {total} 条 AI 新闻。"
    # H4 时间锚点（兜底）
    return f"{date_spoken}，{total} 条 AI 头条，一分钟速览。"


# ---------------------------------------------------------------- 跨天去重
def _norm_title(title: str) -> str:
    """标题规范化：去标点/空格/大小写，用于跨天去重比较。"""
    return re.sub(r"[\s，,。.！!？?；;：:、\"'\"'（）()【】\[\]《》<>\-—…·#*]", "", title or "").lower()


def load_seen_titles() -> dict:
    """加载最近 SEEN_DAYS 天的标题记录，格式 {date: [norm_titles]}。"""
    if not os.path.exists(SEEN_TITLES_PATH):
        return {}
    try:
        with open(SEEN_TITLES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # 只保留最近 SEEN_DAYS 天
        sorted_dates = sorted(data.keys(), reverse=True)[:SEEN_DAYS]
        return {d: data[d] for d in sorted_dates}
    except Exception:
        return {}


def save_seen_titles(date: str, titles: list):
    """保存当天标题到 seen_titles.json，合并已有记录并只保留最近 SEEN_DAYS 天。

    原子写入（临时文件 + replace）：写失败不会留下半个 JSON 损坏账本；
    内容无变化时跳过落盘。
    """
    data = load_seen_titles()
    normalized = [_norm_title(t) for t in titles]
    if data.get(date) == normalized:
        return  # 无变化，不重复落盘
    data[date] = normalized
    sorted_dates = sorted(data.keys(), reverse=True)[:SEEN_DAYS]
    data = {d: data[d] for d in sorted_dates}
    os.makedirs(os.path.dirname(SEEN_TITLES_PATH), exist_ok=True)
    tmp = SEEN_TITLES_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SEEN_TITLES_PATH)


def filter_duplicates(items: list, exclude_date: str = "") -> list:
    """过滤与最近 SEEN_DAYS 天重复的新闻，返回去重后的列表。

    exclude_date：当天日期。同日已记录标题不参与过滤——否则同一天
    第二次 parse（预览/重跑/返工）会把自己第一次选中的条目全部滤掉，
    造成「去重自锁」（2026-10-14 E6）。跨日已出现标题仍照常去重。
    """
    seen = load_seen_titles()
    all_seen = set()
    for d, titles in seen.items():
        if exclude_date and d == exclude_date:
            continue
        all_seen.update(titles)

    kept = []
    dup_count = 0
    for it in items:
        norm = _norm_title(it.get("title", ""))
        if norm and norm in all_seen:
            print(f"  [dedup] 跳过重复（近{SEEN_DAYS}天已出现）: {it.get('title', '')[:40]}")
            dup_count += 1
            continue
        kept.append(it)
    if dup_count:
        print(f"  [dedup] 共跳过 {dup_count} 条重复，保留 {len(kept)} 条")
    return kept


def build_script(meta, items, max_clauses=5, max_chars=120):
    """把解析结果组织成 Remotion 场景 + 口播 clauses。"""
    date, weekday = meta["date"], meta["weekday"]
    total = len(items)
    sections = []
    for it in items:
        if it["section"] not in sections:
            sections.append(it["section"])

    scenes = []

    # --- 开场（动态钩子：根据当天新闻特征选择，≤6 秒口播） ---
    intro_text = generate_hook(items, date, weekday)
    intro_clauses = [intro_text]
    scenes.append({
        "id": "s0_intro",
        "visual": {
            "type": "news_hook",
            "date": date,
            "weekday": weekday,
            "total": total,
            "sections": sections,
        },
        "clauses": [ensure_period(c) for c in (clean_for_tts(x) for x in intro_clauses) if c],
    })

    # --- 每条新闻（浓缩版：只出标题，fetch 阶段再补一条精简要点；
    #     「第 N 条」「来源」「正文」不上口播，仍展示在画面卡片上） ---
    for n, it in enumerate(items, start=1):
        clauses = []
        # 口播用朗读稿（title_tts，助读拼写）；visual.title 保留显示稿官方拼写
        tts_title = it.get("title_tts") or it["title"]
        if tts_title:
            # 标题可能很长（列表格式常超 40 字），同样按字幕行宽拆句
            clauses.extend(merge_clauses([ensure_period(tts_title)]))

        scenes.append({
            "id": f"s{n}_item",
            "visual": {
                "type": "news_item",
                "index": n,
                "section": it["section"],
                "title": it["title"],
                "link": it.get("link", ""),
                "tags": it["tags"][:3],
                "source": it["source"],
                # md 自带要点（核心/细节/价值）：fetch 成功会被覆盖，
                # 抓取失败时至少画面上还有内容，不会只剩标题
                "bullets": it.get("points", [])[:3],
            },
            # 每个子句都必须以完整标点结束（逗号切分的标题子句补句号，
            # SKILL.md 约束 #3：禁止无标点残句）。
            # clauses 已由 title_tts（朗读稿）派生，不再二次 clean_for_tts，
            # 避免对已助读文本重复归一化产生不可控变换（P1-5）。
            "clauses": [ensure_period(c) for c in clauses if c],
        })

    # --- 结尾（浓缩版：一句收束） ---
    scenes.append({
        "id": f"s{total + 1}_outro",
        "visual": {"type": "news_outro", "date": date, "total": total},
        "clauses": [
            "以上就是今天的 AI 头条，我们明天见。",
        ],
    })

    narration = {
        "date": date,
        "weekday": weekday,
        "title": "每日 AI 头条",
        "subtitle": f"{date} {weekday} · {total} 条精选".strip(),
        "total": total,
        "sections": sections,
        "scenes": scenes,
    }

    # --- 单句硬上限：超长 clause（如无逗号的长标题）在标点处拆分 ---
    for sc in narration["scenes"]:
        expanded = []
        for c in sc["clauses"]:
            expanded.extend(split_long_clause(c, max_chars=40))
        sc["clauses"] = [c for c in expanded if c.strip()]

    return narration


def spoken_date(date: str) -> str:
    """2026-09-06 -> 2026 年 9 月 6 日"""
    try:
        y, m, d = date.split("-")
        return f"{y} 年 {int(m)} 月 {int(d)} 日"
    except Exception:
        return date


def ensure_period(s: str) -> str:
    """确保子句以句末标点收尾。

    逗号结尾的子句（merge_clauses 按逗号切分标题/长句产生）必须把逗号
    **替换**为句号，不能直接追加 —— 否则会产出「xxx缓存，。」这类双标点
    （2026-10-22 成片前发现）。顿号同理。
    """
    s = s.strip()
    if not s:
        return s
    if s[-1] in "。！？!?；;":
        return s
    if s[-1] in "，,、":
        return s[:-1].rstrip() + "。"
    return s + "。"


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description="news.md -> narration.json")
    ap.add_argument("news_md", help="每日 AI 头条 markdown 文件路径")
    ap.add_argument("--out", default="", help="输出 narration.json 路径（默认与 md 同目录工作区）")
    ap.add_argument("--max-clauses", type=int, default=5, help="每条新闻最多取 N 个口播子句（默认 5）")
    ap.add_argument("--max-chars", type=int, default=120, help="每条新闻正文最多 N 字（默认 120）")
    ap.add_argument("--workdir", default="", help="工作目录（默认脚本上一层的 work/）")
    ap.add_argument("--preview", action="store_true",
                    help="预览模式：只解析不去重记账，产物写 narration.preview.json，"
                         "不触碰 seen_titles.json 与正式 narration.json")
    args = ap.parse_args()

    md_path = os.path.abspath(args.news_md)
    if not os.path.isfile(md_path):
        print(f"FAIL: news.md 不存在: {md_path}")
        return 1

    text = open(md_path, encoding="utf-8").read()
    fallback = HEAD_DATE.search(os.path.basename(md_path))
    meta, items = parse_markdown(text, fallback.group(0) if fallback else "")

    if not items:
        print("FAIL: 未解析到任何新闻条目，请检查 md 格式（### N. 标题）")
        return 1

    # 跨天去重：跳过最近 7 天已出现过的标题（排除当天，保证同日重跑幂等）
    items = filter_duplicates(items, exclude_date=meta.get("date", ""))
    if not items:
        print("FAIL: 去重后无剩余新闻条目")
        return 1

    narration = build_script(meta, items, args.max_clauses, args.max_chars)

    if args.preview:
        # 预览模式忽略 --out：始终写独立预览稿，绝不覆盖正式 narration.json
        workdir = args.workdir or os.path.dirname(NARRATION)
        os.makedirs(workdir, exist_ok=True)
        out = os.path.join(workdir, "narration.preview.json")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(narration, f, ensure_ascii=False, indent=2)
        n_clauses = sum(len(s["clauses"]) for s in narration["scenes"])
        total_chars = sum(len(c) for s in narration["scenes"] for c in s["clauses"])
        print(f"OK  [preview] {len(items)} 条新闻 / {len(narration['scenes'])} 个场景 / "
              f"{n_clauses} 句口播 / 口播总字数 {total_chars}")
        print(f"    日期: {narration['date']} {narration['weekday']}  "
              f"（预览模式：未写 seen_titles，未覆盖正式 narration.json）")
        print(f"narration.preview.json -> {out}")
        return 0

    out = args.out
    if not out:
        # 统一走 common.WORK_DIR（项目目录下），避免与 skill 目录里的副本分裂
        workdir = args.workdir or os.path.dirname(NARRATION)
        os.makedirs(workdir, exist_ok=True)
        out = os.path.join(workdir, "narration.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(narration, f, ensure_ascii=False, indent=2)

    n_clauses = sum(len(s["clauses"]) for s in narration["scenes"])
    print(f"OK  解析 {len(items)} 条新闻 / {len(narration['scenes'])} 个场景 / {n_clauses} 句口播")
    print(f"    日期: {narration['date']} {narration['weekday']}  分类: {', '.join(narration['sections'])}")
    print(f"narration.json -> {out}")

    # 记录当天标题供跨天去重（「已选用」记账；「已发布」以平台回执/handoff 为准）
    save_seen_titles(narration["date"], [it.get("title", "") for it in items])
    return 0


if __name__ == "__main__":
    sys.exit(main())
