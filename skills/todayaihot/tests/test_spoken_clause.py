"""T7 口播语义完整性（2026-10-21 残句事故回归）。

事故：2026-10-21 成片中 _spoken_bullet 在 ASCII 空格处截断要点，
产出「DeepSeek 将内部生产级推理框架。」「AMD 与英特尔宣布在 PyTorch 的 x86。」
两条残句，配音与 KTV 字幕同时呈现半句话。

本组用例固化：
1. _spoken_bullet 绝不在英文词间空格处截切，只产出完整句或中文标点边界句；
2. audit_spoken_clause 能检出历史残句、放行完整句；
3. assemble_item_clauses 对残句纵深防御（丢弃 + 不中断）；
4. validate_output 把残句判为 ERROR（阻断渲染）；
5. split_long_clause 硬切兜底不再切 ASCII 空格。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch_news  # noqa: E402
import tts_normalize  # noqa: E402
import validate_output  # noqa: E402
from conftest import make_narration, make_timeline, write_json, write_real_png  # noqa: E402

# 2026-10-21 成片真实要点（两条残句的来源文本）
BULLET_DEEPINFER = ("DeepSeek 将内部生产级推理框架 DeepInfer 全面开源，"
                    "并同步开源高性能 Token 编解码组件 deepseek-recipe。")
BULLET_AMD = ("AMD 与英特尔宣布在 PyTorch 的 x86 CPU 优化上合作，"
              "将各自优化整合进开源库 oneDNN，"
              "使其成为 PyTorch 内 x86 加速的默认开源库。")
BULLET_TORCHTPU = ("Google 与 Meta 发布开源项目 TorchTPU，为 TPU 提供原生 "
                   "PyTorch 后端，并据此推出 vLLM、SGLang 的 TPU 原生推理引擎。")

# 当日成片里的两条残句（事故样本，修复后不得再出现）
FRAG_DEEPINFER = "DeepSeek 将内部生产级推理框架。"
FRAG_AMD = "AMD 与英特尔宣布在 PyTorch 的 x86。"

TITLE_DEEPINFER = "Deep Seek 全面开源内部推理框架 DeepInfer"
TITLE_AMD = "A M D 与英特尔统一 PyTorch 的 x86 优化路径"
TITLE_TORCHTPU = "Google 与 Meta 推出 TorchTPU 生态：PyTorch 原生 TPU 后端"  # >32，不加要点


def _norm(t):
    return fetch_news._norm(t)


# ---------------------------------------------------------------- 1. 截切行为

def test_spoken_bullet_never_cuts_at_ascii_space():
    """真实要点不得被切成英文词间空格残句（2026-10-21 事故直接回归）。"""
    for b in (BULLET_DEEPINFER, BULLET_AMD, BULLET_TORCHTPU):
        r = fetch_news._spoken_bullet(b, "")
        assert r != FRAG_DEEPINFER and r != FRAG_AMD
        assert r.endswith(("。", "！", "？", "；")), f"未以完整标点结束: {r!r}"


def test_spoken_bullet_deepinfer_is_complete_sentence():
    """长句在中文逗号边界截切，保留关键实体 DeepInfer。"""
    r = fetch_news._spoken_bullet(BULLET_DEEPINFER, "")
    assert r.endswith("。")
    assert "Deep Infer" in r or "DeepInfer" in r   # 清洗后英文带助读空格
    assert fetch_news.audit_spoken_clause(r, [BULLET_DEEPINFER]) == ""


def test_spoken_bullet_amd_is_complete_sentence():
    r = fetch_news._spoken_bullet(BULLET_AMD, "")
    assert r.endswith("合作。"), f"未停在中文标点边界: {r!r}"
    assert fetch_news.audit_spoken_clause(r, [BULLET_AMD]) == ""


def test_spoken_bullet_short_first_sentence_kept_whole():
    b = "小米发布新模型，支持端侧部署。后续还有别的功能升级。"
    r = fetch_news._spoken_bullet(b, "")
    assert r == "小米发布新模型，支持端侧部署。"


def test_spoken_bullet_no_boundary_returns_empty():
    """无中文标点的超长句：宁可不口播，不出残句。"""
    b = "这是一个没有任何中文标点的超长要点文本一直写到底都没有任何边界可以用来截切它"
    assert len(b) > fetch_news.COMPLETE_SENT_MAX
    assert fetch_news._spoken_bullet(b, "") == ""


def test_spoken_bullet_short_unpunctuated_sentence_kept_whole():
    """无标点但本身是完整短句（≤ 上限）：保留并补句号，不出残句也不丢内容。"""
    b = "这是一条没有标点的完整短句"
    assert fetch_news._spoken_bullet(b, "") == b + "。"


def test_spoken_bullet_title_dedup():
    """与标题归一化后互相包含的要点不口播（避免复读标题）。"""
    b = "Deep Seek 全面开源内部推理框架 DeepInfer，同步开源编解码组件。"
    assert fetch_news._spoken_bullet(b, _norm(TITLE_DEEPINFER)) == ""


# ---------------------------------------------------------------- 2. 残句审计

def test_audit_detects_historical_fragments():
    assert fetch_news.audit_spoken_clause(FRAG_DEEPINFER, [BULLET_DEEPINFER])
    assert fetch_news.audit_spoken_clause(FRAG_AMD, [BULLET_AMD])


def test_audit_accepts_complete_sentences():
    fixed1 = fetch_news._spoken_bullet(BULLET_DEEPINFER, "")
    fixed3 = fetch_news._spoken_bullet(BULLET_AMD, "")
    assert fetch_news.audit_spoken_clause(fixed1, [BULLET_DEEPINFER]) == ""
    assert fetch_news.audit_spoken_clause(fixed3, [BULLET_AMD]) == ""


def test_audit_ignores_unmatched_text():
    """标题句等无法对应到要点的文本不误判。"""
    assert fetch_news.audit_spoken_clause("今天 AI 圈有大事。", [BULLET_DEEPINFER]) == ""


# ---------------------------------------------------------------- 3. 组装防御

def test_assemble_long_title_gets_no_bullet():
    v = {"index": 2, "title": TITLE_TORCHTPU, "bullets": [BULLET_TORCHTPU]}
    clauses = fetch_news.assemble_item_clauses(v, [BULLET_TORCHTPU])
    assert clauses == [TITLE_TORCHTPU + "。"]


def test_assemble_short_title_gets_complete_bullet():
    v = {"index": 1, "title": TITLE_DEEPINFER, "bullets": [BULLET_DEEPINFER]}
    clauses = fetch_news.assemble_item_clauses(v, [BULLET_DEEPINFER])
    assert len(clauses) == 2
    assert clauses[0] == TITLE_DEEPINFER + "。"
    assert clauses[1].endswith("。")
    assert fetch_news.audit_spoken_clause(clauses[1], [BULLET_DEEPINFER]) == ""


def test_assemble_drops_fragment_even_if_producer_regresses(monkeypatch):
    """纵深防御：即使 _spoken_bullet 未来回归产出残句，组装层也必须丢弃。"""
    monkeypatch.setattr(fetch_news, "_spoken_bullet",
                        lambda b, t: FRAG_DEEPINFER)
    v = {"index": 1, "title": TITLE_DEEPINFER, "bullets": [BULLET_DEEPINFER]}
    clauses = fetch_news.assemble_item_clauses(v, [BULLET_DEEPINFER])
    assert clauses == [TITLE_DEEPINFER + "。"]


def test_assemble_every_clause_ends_with_punctuation():
    v = {"index": 3, "title": "甲公司发布新产品，乙公司跟进布局，丙公司宣布适配。",
         "bullets": []}
    clauses = fetch_news.assemble_item_clauses(v, [])
    assert clauses and all(c[-1] in "。！？；" for c in clauses)


# ---------------------------------------------------------------- 4. validate 硬门

def _run_validate(tmp_path, narr):
    d = str(tmp_path)
    images_dir = os.path.join(d, "images")
    os.makedirs(images_dir, exist_ok=True)
    for sc in narr["scenes"]:
        v = sc.get("visual", {})
        if v.get("type") == "news_item":
            v.setdefault("images", [])
            for i, rel in enumerate(v["images"]):
                v["images"][i] = "images/" + os.path.basename(rel)
                write_real_png(os.path.join(images_dir, os.path.basename(rel)))
    tl = make_timeline(date=narr["date"])
    narration_path = write_json(os.path.join(d, "narration.json"), narr)
    timeline_path = write_json(os.path.join(d, "timeline.json"), tl)
    old = sys.argv
    sys.argv = ["validate_output.py", "--narration", narration_path,
                "--timeline", timeline_path, "--images-dir", images_dir]
    try:
        rc = validate_output.main()
    finally:
        sys.argv = old
    return rc, list(validate_output.errors), list(validate_output.warnings)


def _narr_with_clause(clause, bullet):
    narr = make_narration(n_items=1)
    sc = narr["scenes"][1]
    sc["clauses"] = ["第一条标题句。", clause]
    sc["visual"]["bullets"] = [bullet]
    return narr


def test_validate_fragment_is_error(tmp_path):
    narr = _narr_with_clause(FRAG_DEEPINFER, BULLET_DEEPINFER)
    rc, errors, _ = _run_validate(tmp_path, narr)
    assert rc == 1
    assert any("残句" in e for e in errors)


def test_validate_complete_clause_passes(tmp_path):
    fixed = fetch_news._spoken_bullet(BULLET_DEEPINFER, "")
    narr = _narr_with_clause(fixed, BULLET_DEEPINFER)
    rc, errors, _ = _run_validate(tmp_path, narr)
    assert not any("残句" in e for e in errors), errors


def test_validate_clause_without_end_punct_is_error(tmp_path):
    narr = _narr_with_clause("这是一个没有结尾标点的口播子句", BULLET_DEEPINFER)
    rc, errors, _ = _run_validate(tmp_path, narr)
    assert rc == 1
    assert any("未以完整标点结束" in e for e in errors)


# ---------------------------------------------------------------- 5. 长句拆分

def test_split_long_clause_never_cuts_at_ascii_space():
    """超长无标点文本：保留整句交字幕分页，不在空格处切。"""
    text = "这是一个很长的标题没有任何中文标点可以切而且后面还拖着 English words here"
    out = tts_normalize.split_long_clause(text, max_chars=20)
    assert out == [text] or "".join(out) == text
    assert all(not p.endswith(" ") for p in out)


def test_split_long_clause_cuts_at_cn_punct():
    text = "甲公司在发布会上宣布了新产品的详细计划，乙公司随后也表示会跟进这个方向。"
    out = tts_normalize.split_long_clause(text, max_chars=20)
    assert len(out) >= 2
    assert out[0].endswith("，")
    assert "".join(out) == text
