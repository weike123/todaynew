"""生成发布物料包 publish.md（备选标题/话题标签/简介/置顶评论/AI声明）。

用法:
    python gen_publish.py [--narration work/narration.json] [--timeline work/timeline.json]
                          [--out out/2026-09-03/publish.md]

不依赖 LLM，纯规则模板 + 关键词提取。
"""
import argparse
import json
import os
import re
import sys

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


def gen_description(items: list, date: str, chapters_path: str = "") -> str:
    """生成视频简介（含章节，如果有 chapters 文件）。"""
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

    # B站章节
    if chapters_path and os.path.exists(chapters_path):
        try:
            with open(chapters_path, encoding="utf-8") as f:
                ch = json.load(f)
            lines.append("")
            lines.append("⏱ 章节导航：")
            for c in ch.get("chapters", []):
                lines.append(f"{c['time']} {c['title']}")
        except Exception:
            pass

    lines.append("")
    lines.append("🤖 本视频由 AI 辅助生成，内容仅供参考")
    lines.append("👍 喜欢请点赞关注，每天更新 AI 头条")
    return "\n".join(lines)


def gen_pinned_comment(items: list) -> str:
    """生成置顶评论。"""
    lines = [
        "📝 本期新闻来源汇总：",
    ]
    for i, it in enumerate(items[:5], 1):
        src = it.get("source", "未知来源")
        title = it.get("title", "")[:30]
        lines.append(f"{i}. [{src}] {title}")
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
    out_dir = os.path.join(OUT_DIR, date)
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.out or os.path.join(out_dir, "publish.md")
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
