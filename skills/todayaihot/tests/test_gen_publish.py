"""P1-1 发布物料：来源兜底、原文链接全覆盖、章节 schema 不静默吞错。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gen_publish  # noqa: E402


def _item(**kw):
    base = {"title": "测试新闻标题", "source": "测试来源",
            "link": "https://example.com/a"}
    base.update(kw)
    return base


def test_empty_source_uses_domain_fallback():
    """来源名为空：用原文 URL 域名兜底，绝不输出 `[]`（10-27 事故复现）。"""
    items = [_item(source="", link="https://blog.cloudflare.com/kv-cache/")]
    comment = gen_publish.gen_pinned_comment(items)
    assert "[]" not in comment
    assert "blog.cloudflare.com" in comment
    assert "https://blog.cloudflare.com/kv-cache/" in comment, "原文链接必须出现在来源汇总"


def test_missing_source_and_link_label():
    items = [_item(source="", link="")]
    comment = gen_publish.gen_pinned_comment(items)
    assert "[]" not in comment
    assert "来源未标注" in comment


def test_pinned_comment_covers_all_items():
    """置顶评论必须覆盖全部条目，不得截断到前 5 条。"""
    items = [_item(title=f"第{i}条", link=f"https://e.com/{i}") for i in range(7)]
    comment = gen_publish.gen_pinned_comment(items)
    for i in range(7):
        assert f"第{i}条" in comment
        assert f"https://e.com/{i}" in comment


def test_description_contains_all_source_links():
    items = [_item(title=f"新闻{i}", link=f"https://e.com/{i}") for i in range(7)]
    desc = gen_publish.gen_description(items, "2026-10-28")
    for i in range(7):
        assert f"https://e.com/{i}" in desc, "简介必须包含全部原文链接"


def test_chapters_list_format_not_silently_dropped(tmp_path):
    """顶层 list 章节（历史遗留）：可用但告警，标题不得静默消失。"""
    p = os.path.join(str(tmp_path), "chapters.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump([{"time": "00:00", "title": "开场速览"},
                   {"time": "00:05", "title": "Cloudflare 披露缓存泄露"}], f)
    desc = gen_publish.gen_description([], "2026-10-28", p)
    assert "Cloudflare 披露缓存泄露" in desc, "list 章节不得被静默省略"
    assert "开场速览" in desc


def test_chapters_broken_json_reports_explicitly(tmp_path):
    """章节文件损坏：显式报告异常，不得静默吞掉。"""
    p = os.path.join(str(tmp_path), "chapters.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("{broken json")
    desc = gen_publish.gen_description([], "2026-10-28", p)
    assert "章节数据异常" in desc


def test_chapters_missing_file_ok():
    desc = gen_publish.gen_description([], "2026-10-28", "")
    assert "章节导航" not in desc


def test_source_label_prefers_explicit_source():
    assert gen_publish._source_label(_item()) == "测试来源"
