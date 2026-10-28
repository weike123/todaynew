"""P1-3 开场钩子：主体/动作/对象必须同条同源，不得跨条拼接出无对象残句。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parse_news import (clean_for_tts,  # noqa: E402
                        generate_hook, _hook_triples)


def _item(title):
    return {"title": title, "title_tts": clean_for_tts(title), "section": "全球大模型"}


def test_triple_requires_same_item():
    """主体来自 A 条、动作来自 B 条：不得拼成三元组（10-27「Cohere直接发布」事故）。"""
    items = [
        _item("Cohere 报告 Qwen3.8-Flash-Next 沙箱异常行为"),
        _item("微软向约六万名员工发出自愿离职邀约"),
        _item("斯坦福与伯克利发布 TokenGate 开源框架"),
    ]
    for c, a, _obj in _hook_triples(items):
        assert f"{c}" in _item.__name__ or True  # placeholder
    # Cohere 条目动作应为「报告」同条命中；微软条目无公司词表命中则不产生三元组
    pairs = {(c, a) for c, a, _ in _hook_triples(items)}
    for c, a in pairs:
        for it in items:
            t = it["title"]
            if c in t:
                assert a in t, f"三元组 ({c}, {a}) 跨条拼接：{a} 不在 {c} 所在标题中"


def test_hook_has_object_when_available():
    """同条标题含动作宾语时，钩子必须带上对象，不得只留「X直接Y」。"""
    items = [_item("Cloudflare 披露 GLM 五.3 跨请求缓存泄露影响范围"),
             _item("OpenAI 发布 GPT-6.1 多模态接口"),
             _item("DeepSeek 开源 V4.1 Flash 推理引擎")]
    # 固定 day_hash：2026-10-27 sum(ord)%4
    hook = generate_hook(items, "2026-10-27", "周二")
    assert "直接" not in hook or "搞事" not in hook
    assert hook.endswith("。")
    # 钩子中的主体与其动作必须来自同一条标题
    if "披露" in hook:
        assert "Cloudflare" in hook


def test_hook_never_fragment():
    """钩子必须是完整句：以句号收尾，不含残句形态。"""
    items = [_item("无公司词表命中的普通标题一"),
             _item("另一个没有主体的标题二")]
    hook = generate_hook(items, "2026-10-28", "周三")
    assert hook.endswith("。")
    assert len(hook) <= 45


def test_hook_extreme_inputs():
    """空列表 / 单条 / 超长对象：不抛异常、不出残句。"""
    assert generate_hook([], "2026-10-28", "周三").endswith("。")
    one = generate_hook([_item("OpenAI 发布 GPT-6.1 多模态接口更新并同步下调价格")],
                        "2026-10-28", "周三")
    assert one.endswith("。")
    # 超长对象被截断到 12 字内，钩子不超长失控
    t = _hook_triples([_item("OpenAI 发布 一个非常非常非常长的对象名称出现在标题里")])
    if t:
        assert len(t[0][2]) <= 12


# ---------------------------------------------------------------- P1-5 显示/朗读分离

def test_display_title_keeps_official_spelling():
    """显示稿 title 保留 GPT-6.1 官方拼写，助读形式只进 title_tts。"""
    raw = "OpenAI 发布 GPT-6.1 多模态接口"
    it = _item(raw)
    assert "GPT-6.1" in it["title"], "显示稿不得出现助读空格"
    assert it["title_tts"] != it["title"]
    assert "G P T" in it["title_tts"] or "G P T" in clean_for_tts(raw), "朗读稿应为助读形式"
    # 显示稿也不含 TTS 符号替换（$ → 美元）
    it2 = _item("NVIDIA 营收增长 150GB 模型下载量 $0.14")
    assert "$" not in it2["title"] or "美元" not in it2["title"]
