"""T3 解析重跑幂等：同日重跑不自杀、preview 无副作用、跨日去重仍生效。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parse_news  # noqa: E402

MD_TEMPLATE = """# AI 新闻推送 · {date}

**1. Google 发布 Gemini 4 Argon：1M 上下文前沿模型上线**
核心：Google 发布新模型。
细节：上下文 1M。
价值：开发者可用。
原文：https://example.com/1

**2. Anthropic 自研版本控制系统 Scion**
核心：Anthropic 开源 Scion。
细节：五个月替换 Git。
价值：可借鉴。
原文：https://example.com/2

**3. LangChain 发布 langchain-scaledown**
核心：LangChain 新工具。
细节：自动缩放。
价值：提效。
原文：https://example.com/3
"""


def _write_md(path, date):
    with open(path, "w", encoding="utf-8") as f:
        f.write(MD_TEMPLATE.format(date=date))
    return path


def _setup_workdir(tmp_path, monkeypatch):
    workdir = os.path.join(str(tmp_path), "work")
    os.makedirs(workdir, exist_ok=True)
    monkeypatch.setattr(parse_news, "SEEN_TITLES_PATH",
                        os.path.join(workdir, "seen_titles.json"))
    return workdir


def _run_main(md, out, preview=False):
    argv = ["parse_news.py", md, "--out", out,
            "--workdir", os.path.dirname(os.path.abspath(out))]
    if preview:
        argv.append("--preview")
    old = sys.argv
    sys.argv = argv
    try:
        rc = parse_news.main()
    finally:
        sys.argv = old
    return rc


def test_same_day_rerun_keeps_all_items(tmp_path, monkeypatch):
    """同日同输入连续两次 parse：第二次不得把自己过滤掉（E6 自锁）。"""
    workdir = _setup_workdir(tmp_path, monkeypatch)
    md = _write_md(os.path.join(str(tmp_path), "news.md"), "2026-10-14")

    rc1 = _run_main(md, os.path.join(workdir, "narration.json"))
    assert rc1 == 0
    n1 = json.load(open(os.path.join(workdir, "narration.json"), encoding="utf-8"))
    items1 = [s for s in n1["scenes"] if s["visual"]["type"] == "news_item"]

    rc2 = _run_main(md, os.path.join(workdir, "narration.json"))
    assert rc2 == 0
    n2 = json.load(open(os.path.join(workdir, "narration.json"), encoding="utf-8"))
    items2 = [s for s in n2["scenes"] if s["visual"]["type"] == "news_item"]

    assert len(items1) == len(items2) == 3
    assert [s["visual"]["title"] for s in items1] == [s["visual"]["title"] for s in items2]


def test_cross_day_dedup_still_works(tmp_path, monkeypatch):
    """跨日已出现过的标题仍要去重。"""
    workdir = _setup_workdir(tmp_path, monkeypatch)
    # 昨天已发布过「LangChain 发布 langchain-scaledown」
    seen_path = os.path.join(workdir, "seen_titles.json")
    with open(seen_path, "w", encoding="utf-8") as f:
        json.dump({"2026-10-13": [parse_news._norm_title("LangChain 发布 langchain-scaledown")]}, f)

    md = _write_md(os.path.join(str(tmp_path), "news.md"), "2026-10-14")
    rc = _run_main(md, os.path.join(workdir, "narration.json"))
    assert rc == 0
    n = json.load(open(os.path.join(workdir, "narration.json"), encoding="utf-8"))
    titles = [s["visual"]["title"] for s in n["scenes"] if s["visual"]["type"] == "news_item"]
    assert not any("langchain-scaledown" in t for t in titles), "跨日重复未被过滤"
    assert len(titles) == 2


def test_preview_has_no_side_effects(tmp_path, monkeypatch):
    """preview 不得写 seen_titles，也不得覆盖正式 narration.json。"""
    workdir = _setup_workdir(tmp_path, monkeypatch)
    seen_path = os.path.join(workdir, "seen_titles.json")
    md = _write_md(os.path.join(str(tmp_path), "news.md"), "2026-10-14")

    # 先正式跑一次，建立基线
    assert _run_main(md, os.path.join(workdir, "narration.json")) == 0
    seen_before = open(seen_path, encoding="utf-8").read()
    narr_before = open(os.path.join(workdir, "narration.json"), encoding="utf-8").read()

    # preview 跑同一天
    rc = _run_main(md, os.path.join(workdir, "narration.json"), preview=True)
    assert rc == 0
    assert open(seen_path, encoding="utf-8").read() == seen_before, "preview 改写了 seen_titles"
    assert open(os.path.join(workdir, "narration.json"), encoding="utf-8").read() == narr_before, \
        "preview 覆盖了正式 narration.json"
    assert os.path.isfile(os.path.join(workdir, "narration.preview.json")), \
        "preview 应产出独立的预览稿"


def test_second_failure_keeps_first_state(tmp_path, monkeypatch):
    """第二次运行失败（坏 md）不得损坏第一次成功的 seen 状态。"""
    workdir = _setup_workdir(tmp_path, monkeypatch)
    seen_path = os.path.join(workdir, "seen_titles.json")
    md = _write_md(os.path.join(str(tmp_path), "news.md"), "2026-10-14")

    assert _run_main(md, os.path.join(workdir, "narration.json")) == 0
    seen_before = json.load(open(seen_path, encoding="utf-8"))

    bad_md = os.path.join(str(tmp_path), "bad.md")
    with open(bad_md, "w", encoding="utf-8") as f:
        f.write("# 没有条目\n\n一些没有格式的文本。\n")
    rc = _run_main(bad_md, os.path.join(workdir, "narration.json"))
    assert rc == 1
    assert json.load(open(seen_path, encoding="utf-8")) == seen_before, \
        "失败的第二次运行损坏了 seen 状态"


def test_save_seen_titles_latest_wins(tmp_path, monkeypatch):
    """save_seen_titles 重复保存：后者覆盖同日键，旧日期保留。"""
    workdir = _setup_workdir(tmp_path, monkeypatch)
    seen_path = os.path.join(workdir, "seen_titles.json")
    parse_news.save_seen_titles("2026-10-12", ["旧闻A"])
    parse_news.save_seen_titles("2026-10-14", ["新闻甲", "新闻乙"])
    parse_news.save_seen_titles("2026-10-14", ["新闻甲"])
    data = json.load(open(seen_path, encoding="utf-8"))
    assert data["2026-10-14"] == [parse_news._norm_title("新闻甲")]
    assert data["2026-10-12"] == [parse_news._norm_title("旧闻A")]
