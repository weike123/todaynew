"""生成发布物料包 publish.md（备选标题/话题标签/简介/置顶评论/AI声明）。

用法:
    python gen_publish.py [--narration work/narration.json] [--timeline work/timeline.json]
                          [--out out/2026-09-03/publish.md]

不依赖 LLM，纯规则模板 + 关键词提取。

P1-1 约定：
- 来源名缺失时用原文 URL 域名兜底，绝不输出 `[]`；
- 置顶评论/简介必须覆盖全部新闻条目并附原文链接；
- 章节数据唯一 schema：{"date","chapters":[...]}；顶层 list 为历史遗留，
  可读但会显式告警，解析失败必须报告而非静默吞掉。
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NARRATION, OUT_DIR, TIMELINE  # noqa: E402

# 固定话题标签
BASE_TAGS = ["AI", "人工智能", "每日AI头条", "科技"]
# 从标题提取的关键词映射（用于话题标签）
TAG_KEYWORDS = {
    "OpenAI": "OpenAI", "ChatGPT": "ChatGPT", "GPT": "GPT",
    "DeepSeek": "DeepSeek", "Google": "Google", "Gemini": "Gemini",
    "Meta": "Meta", "Llama": "Llama", "NVIDIA": "英伟达", "英伟达": "英伟达",
    "Anthropic": "Anthropic", "Claude": "Claude",
    "Microsoft": "微软", "微软": "微软", "Apple": "苹果", "苹果": "苹果",
    "Amazon": "亚马逊", "Tesla": "特斯拉", "xAI": "xAI", "Grok": "Grok",
    "Mistral": "Mistral", "通义": "通义千问", "Qwen": "通义千问",
    "豆包": "豆包", "文心": "文心一言", "Kimi": "Kimi", "智谱": "智谱AI",
    "Cursor": "Cursor", "Copilot": "Copilot", "GitHub": "GitHub",
    "开源": "开源", "大模型": "大模型", "多模态": "多模态",
    "Agent": "AI智能体", "智能体": "AI智能体", "RAG": "RAG",
}


def extract_tags(items: list) -> list:
    """从新闻标题提取话题标签，固定标签 + 关键词标签，去重后 5-8 个。"""
    tags = list(BASE_TAGS)
    for it in items:
        title = it.get("title", "")
        for kw, tag in TAG_KEYWORDS.items():
            if kw in title and tag not in tags:
                tags.append(tag)
    return tags[:8]


def gen_titles(items: list, date: str, total: int) -> list:
    """生成 3 个备选标题。"""
    titles = []
    # 标题1：日期 + 最重磅新闻
    top = items[0]["title"] if items else ""
    top_short = top[:25] + "…" if len(top) > 25 else top
    titles.append(f"{date} AI头条速览：{top_short}")

    # 标题2：数字冲击
    titles.append(f"{total}条AI新闻一分钟看完，第1条最值得关注")

    # 标题3：公司对比（如果有 2+ 大公司）
    companies = []
    for it in items:
        for c in ("OpenAI", "DeepSeek", "Google", "Meta", "NVIDIA", "Anthropic",
                   "微软", "苹果", "阿里", "腾讯", "字节", "华为"):
            if c in it.get("title", "") and c not in companies:
                companies.append(c)
    if len(companies) >= 2:
        titles.append(f"{companies[0]}和{companies[1]}同时出手，今天AI圈不平静")
    else:
        titles.append(f"今天AI圈发生了这些大事｜{date} 每日AI头条")

    return titles[:3]


def _source_label(it: dict) -> str:
    """来源名：source 缺失/为空时用原文 URL 域名兜底（P1-1，杜绝 `[]`）。"""
    src = (it.get("source") or "").strip()
    if src:
        return src
    link = (it.get("link") or "").strip()
    if link:
        host = urlparse(link).netloc
        if host:
            return host
    return "来源未标注"


def load_chapters(chapters_path: str) -> list:
    """读取章节数据，返回 chapter list（P1-1 统一入口）。

    唯一 schema：{"chapters": [...]}；顶层 list 为历史遗留可读但告警。
    解析失败抛 ValueError（调用方显式报告，不静默吞错）。
    """
    if not chapters_path or not os.path.exists(chapters_path):
        return []
    with open(chapters_path, encoding="utf-8") as f:
        ch = json.load(f)
    if isinstance(ch, dict):
        return ch.get("chapters", [])
    if isinstance(ch, list):
        print("[gen_publish] 警告: chapters.json 为顶层 list（历史遗留格式），"
              "请统一为 {\"chapters\":[…]} schema")
        return ch
    raise ValueError(f"chapters.json 格式无法识别: {type(ch).__name__}")


def gen_description(items: list, date: str, chapters_path: str = "") -> str:
    """生成视频简介（含章节导航与全部原文链接）。"""
    lines = [
        f"📅 {date} 每日 AI 头条",
        f"📊 本期 {len(items)} 条精选，一分钟速览",
        "",
        "📌 本期看点：",
    ]
    for i, it in enumerate(items[:5], 1):
        t = it.get("title", "")[:40]
        lines.append(f"{i}. {t}")
    if len(items) > 5:
        lines.append(f"  …还有 {len(items) - 5} 条")

    # B站章节：解析失败显式告警，绝不静默省略（P1-1）
    try:
        chapters = load_chapters(chapters_path)
        if chapters:
            lines.append("")
            lines.append("⏱ 章节导航：")
            for c in chapters:
                lines.append(f"{c['time']} {c['title']}")
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        lines.append("")
        lines.append(f"⚠️ 章节数据异常，未生成章节导航: {e}")
        print(f"[gen_publish] 章节数据异常: {e}")

    # 来源与原文链接：覆盖全部条目（P1-1）
    links = [(it.get("title", ""), it.get("link", "")) for it in items]
    if any(l for _, l in links):
        lines.append("")
        lines.append("🔗 原文链接：")
        for i, (title, link) in enumerate(links, 1):
            if link:
                lines.append(f"{i}. {title[:36]} {link}")

    lines.append("")
    lines.append("🤖 本视频由 AI 辅助生成，内容仅供参考")
    lines.append("👍 喜欢请点赞关注，每天更新 AI 头条")
    return "\n".join(lines)


def gen_pinned_comment(items: list) -> str:
    """生成置顶评论：覆盖全部条目并附原文链接，来源缺失用域名兜底。"""
    lines = [
        "📝 本期新闻来源汇总：",
    ]
    for i, it in enumerate(items, 1):
        src = _source_label(it)
        title = it.get("title", "")[:30]
        line = f"{i}. [{src}] {title}"
        link = (it.get("link") or "").strip()
        if link:
            line += f" {link}"
        lines.append(line)
    lines.append("")
    lines.append("💬 你最关注哪条？评论区聊聊")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="生成发布物料包 publish.md")
    ap.add_argument("--narration", default=NARRATION)
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--out", default="", help="输出路径（默认 out/<date>/publish.md）")
    args = ap.parse_args()

    if not os.path.isfile(args.narration):
        print(f"FAIL: 找不到 {args.narration}")
        return 1

    with open(args.narration, encoding="utf-8") as f:
        narr = json.load(f)

    date = narr.get("date", "")
    items = []
    for sc in narr.get("scenes", []):
        if sc.get("visual", {}).get("type") == "news_item":
            v = sc["visual"]
            items.append({
                "title": v.get("title", ""),
                "source": v.get("source", ""),
                "link": v.get("link", ""),
            })

    total = len(items)
    # P1-1：缺原文链接/来源的条目显式告警（不阻断，但必须在日志可见）
    n_no_link = sum(1 for it in items if not (it.get("link") or "").strip())
    if n_no_link:
        print(f"[gen_publish] 警告: {n_no_link}/{total} 条新闻缺少原文链接，"
              "发布物料将无法提供来源溯源，请检查 narration.json 的 visual.link")

    out_path = args.out or os.path.join(OUT_DIR, date, "publish.md")
    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    chapters_path = os.path.join(out_dir, "chapters.json")

    titles = gen_titles(items, date, total)
    tags = extract_tags(items)
    desc = gen_description(items, date, chapters_path)
    pinned = gen_pinned_comment(items)

    md = f"""# 发布物料包 - {date}

## 备选标题（×3）
1. {titles[0]}
2. {titles[1]}
3. {titles[2]}

## 话题标签
{' '.join('#' + t for t in tags)}

## 视频简介
{desc}

## 置顶评论
{pinned}

## AI 生成声明
本视频由 AI 辅助生成（口播 TTS + 自动剪辑），新闻内容来自公开来源，
仅供参考，不构成投资/购买建议。如有错误欢迎指正。

## 配套文件
- 成片：每日ai热门新闻-{date}.mp4
- 封面：covers/cover_3x4.png（竖版）、cover_4x3.png（横版）、cover_16x9.png（宽屏）
- 章节：chapters.json / bilibili_chapters.txt
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"DONE 发布物料包 -> {out_path}")
    print(f"  标题×3 / 标签{len(tags)}个 / 简介{len(desc)}字")
    return 0


if __name__ == "__main__":
    sys.exit(main())
