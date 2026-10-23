"""T8 口播标点规范化（2026-10-22 双标点缺陷回归）。

缺陷：merge_clauses 按逗号切分标题后，子句以「，」结尾；ensure_period
只识别句末标点「。！？!?；;」，于是直接追加「。」，产出「xxx 缓存，。」
这类双标点。2026-10-22 成片前在 narration.json 中实测到 2 处。

本组用例固化：
1. ensure_period 对逗号/顿号结尾的子句做**替换**而非追加；
2. ensure_period 对已有句末标点的子句保持幂等；
3. assemble_item_clauses 产出的每个子句都不含「，。」/「、。」双标点；
4. merge_clauses 切分出的标题子句经组装后无双标点。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch_news  # noqa: E402
import parse_news  # noqa: E402

# 2026-10-22 实测的两条双标点子句
DUP_COMMA = "Open AI A P I 支持 12 小时 prompt 缓存，。"
DUP_COMMA_2 = "Wiz 披露 LiteLLM PyPI 包供应链攻击，。"


# ---------------------------------------------------------------- 1. ensure_period

def test_ensure_period_replaces_trailing_comma():
    assert parse_news.ensure_period("Open AI 支持 12 小时缓存，") == "Open AI 支持 12 小时缓存。"


def test_ensure_period_replaces_trailing_dunhao():
    assert parse_news.ensure_period("甲、乙、丙") == "甲、乙、丙。"


def test_ensure_period_replaces_ascii_comma():
    """ASCII 逗号结尾同样替换为中文句号（口播统一中文标点）。"""
    assert parse_news.ensure_period("hello, world,") == "hello, world。"


def test_ensure_period_is_idempotent_for_sentence_end():
    for s in ("已结束。", "真的吗？", "太好了！", "分号；"):
        assert parse_news.ensure_period(s) == s


def test_ensure_period_appends_when_no_punct():
    assert parse_news.ensure_period("没有结尾标点") == "没有结尾标点。"


def test_ensure_period_never_produces_double_punct():
    for s in ("逗号结尾，", "顿号结尾、", "英文逗号,"):
        out = parse_news.ensure_period(s)
        assert "，。" not in out and "、。" not in out and ",." not in out, out
        assert out.endswith("。")


# ---------------------------------------------------------------- 2. 组装层

def test_assemble_item_clauses_no_double_punct():
    """长标题（按逗号切分）组装后不得出现双标点。"""
    v = {
        "index": 1,
        "title": "OpenAI API 支持 12 小时 prompt 缓存，Codex 与 Work 用户缓存永久保留",
        "bullets": [],
    }
    clauses = fetch_news.assemble_item_clauses(v, [])
    assert clauses
    for c in clauses:
        assert "，。" not in c and "、。" not in c and ",." not in c, c
        assert c[-1] in "。！？；", c


def test_assemble_item_clauses_with_bullet_no_double_punct():
    v = {
        "index": 3,
        "title": "Wiz 披露 LiteLLM PyPI 包供应链攻击，恶意版本窃取凭据",
        "bullets": ["恶意版本 LiteLLM 1.107.0 被上传至 PyPI，随后被隔离。"],
    }
    clauses = fetch_news.assemble_item_clauses(v, v["bullets"])
    for c in clauses:
        assert "，。" not in c and "、。" not in c and ",." not in c, c


def test_historical_double_punct_samples_fixed():
    """历史事故样本不得原样复现：补句号后必须消掉逗号。"""
    assert DUP_COMMA.endswith("，。")          # 事故样本确实是坏的
    fixed = parse_news.ensure_period("Open AI A P I 支持 12 小时 prompt 缓存，")
    assert fixed == "Open AI A P I 支持 12 小时 prompt 缓存。"
    assert "，。" not in fixed

    fixed2 = parse_news.ensure_period("Wiz 披露 LiteLLM PyPI 包供应链攻击，")
    assert fixed2 == "Wiz 披露 LiteLLM PyPI 包供应链攻击。"
    assert "，。" not in fixed2


def test_merge_clauses_output_then_ensure_period_is_clean():
    """merge_clauses 切出的逗号结尾子句，补句号后不得双标点。"""
    raw = parse_news.merge_clauses([parse_news.ensure_period(
        "甲公司发布新产品，乙公司跟进布局，丙公司宣布适配。")])
    for c in raw:
        fixed = parse_news.ensure_period(c)
        assert "，。" not in fixed and "、。" not in fixed, fixed
