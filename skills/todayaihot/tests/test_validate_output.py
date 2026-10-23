"""T2 正式质量硬门：缺图/静音失败/指纹不符/坏字时标必须 ERROR，排版建议保持 WARN。"""
import copy
import json
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import (make_narration, make_timeline, write_json,  # noqa: E402
                      write_real_png)

import validate_output  # noqa: E402


def _make_master(path, duration=99.0, rate=24000):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * duration))
    return path


def _run_validate(tmp_path, narr=None, tl=None, wav_dur=None,
                  images=None, make_master=True):
    """搭建最小 run 并执行校验，返回 (rc, errors, warnings)。

    wav_dur 只控制 master.wav 时长（timeline 固定记录 99s），
    用于构造「音频指纹不符」场景；None 表示与 timeline 一致。
    """
    d = str(tmp_path)
    narr = narr if narr is not None else make_narration()
    tl = tl if tl is not None else make_timeline(master_duration=99.0)
    # timeline 内嵌 narration（真实数据结构）；调用方已内嵌的（含篡改用例）不覆盖。
    # 必须深拷贝：否则篡改内嵌对象会连带改掉 narration 本体，指纹比对失效。
    tl.setdefault("narration", {"date": narr["date"],
                                "scenes": copy.deepcopy(narr["scenes"])})
    narration_path = write_json(os.path.join(d, "narration.json"), narr)
    timeline_path = write_json(os.path.join(d, "timeline.json"), tl)
    images_dir = os.path.join(d, "images")
    os.makedirs(images_dir, exist_ok=True)
    for rel in (images or []):
        write_real_png(os.path.join(images_dir, os.path.basename(rel)))
    if make_master:
        master = _make_master(os.path.join(d, "master.wav"),
                              wav_dur if wav_dur is not None else 99.0)
    else:
        master = ""

    old = sys.argv
    sys.argv = ["validate_output.py",
                "--narration", narration_path, "--timeline", timeline_path,
                "--audio", master, "--images-dir", images_dir]
    try:
        rc = validate_output.main()
    finally:
        sys.argv = old
    return rc, list(validate_output.errors), list(validate_output.warnings)


def test_missing_image_file_is_error(tmp_path):
    narr = make_narration()
    for sc in narr["scenes"]:
        if sc["visual"]["type"] == "news_item":
            sc["visual"]["images"] = ["images/notexist.jpg"]
    rc, errors, _ = _run_validate(tmp_path, narr=narr)
    assert rc == 1
    assert any("配图文件不存在" in e for e in errors)


def test_corrupt_image_is_error(tmp_path):
    narr = make_narration()
    for sc in narr["scenes"]:
        if sc["visual"]["type"] == "news_item":
            sc["visual"]["images"] = ["images/broken.jpg"]
    d = str(tmp_path)
    os.makedirs(os.path.join(d, "images"), exist_ok=True)
    with open(os.path.join(d, "images", "broken.jpg"), "wb") as f:
        f.write(b"not an image at all")
    rc, errors, _ = _run_validate(tmp_path, narr=narr)
    assert rc == 1
    assert any("损坏" in e for e in errors)


def test_silent_fallback_is_error(tmp_path):
    tl = make_timeline()
    tl["scenes"][1]["clauses"][0]["timing_src"] = "silent_fallback"
    rc, errors, _ = _run_validate(tmp_path, tl=tl)
    assert rc == 1
    assert any("静音占位" in e for e in errors)


def test_failed_clauses_is_error(tmp_path):
    tl = make_timeline()
    tl["failed_clauses"] = ["s1_item#0"]
    rc, errors, _ = _run_validate(tmp_path, tl=tl)
    assert rc == 1
    assert any("TTS 失败" in e for e in errors)


def test_date_mismatch_is_error(tmp_path):
    narr = make_narration(date="2026-10-14")
    tl = make_timeline(date="2026-10-13")
    rc, errors, _ = _run_validate(tmp_path, narr=narr, tl=tl)
    assert rc == 1
    assert any("日期不一致" in e for e in errors)


def test_embedded_narration_text_mismatch_is_error(tmp_path):
    narr = make_narration()
    tl = make_timeline()
    # 深拷贝后再篡改：直接引用会连带改掉 narration 本体，指纹比对将失效
    tl["narration"] = {"date": narr["date"], "scenes": copy.deepcopy(narr["scenes"])}
    tl["narration"]["scenes"][1]["visual"]["title"] = "被改过的标题"
    rc, errors, _ = _run_validate(tmp_path, narr=narr, tl=tl)
    assert rc == 1
    assert any("指纹" in e or "不一致" in e for e in errors)


def test_bad_char_timestamps_is_error(tmp_path):
    """负值 / 逆序 / 超出句长的相对字时标都必须失败。"""
    tl = make_timeline()
    clause = tl["scenes"][1]["clauses"][0]
    clause["chars"] = [
        {"ch": "第", "t": 0.0},
        {"ch": "一", "t": 0.5},
        {"ch": "条", "t": 0.2},      # 逆序
        {"ch": "。", "t": 99.0},     # 超出句长
    ]
    rc, errors, _ = _run_validate(tmp_path, tl=tl)
    assert rc == 1
    assert any("字时标" in e for e in errors)


def test_negative_char_time_is_error(tmp_path):
    tl = make_timeline()
    tl["scenes"][1]["clauses"][0]["chars"] = [{"ch": "第", "t": -0.5}]
    rc, errors, _ = _run_validate(tmp_path, tl=tl)
    assert rc == 1
    assert any("字时标" in e for e in errors)


def test_clause_start_ge_end_is_error(tmp_path):
    tl = make_timeline()
    tl["scenes"][1]["clauses"][0]["start"] = 5.0
    tl["scenes"][1]["clauses"][0]["end"] = 5.0
    rc, errors, _ = _run_validate(tmp_path, tl=tl)
    assert rc == 1
    assert any("start" in e and "end" in e for e in errors)


def test_poster_image_source_is_error(tmp_path):
    narr = make_narration()
    for sc in narr["scenes"]:
        if sc["visual"]["type"] == "news_item":
            sc["visual"]["images"] = ["images/ok.jpg"]
            sc["visual"]["image_source"] = "poster"
    rc, errors, _ = _run_validate(tmp_path, narr=narr, images=["images/ok.jpg"])
    assert rc == 1
    assert any("海报" in e or "文字卡" in e for e in errors)


def test_long_clause_stays_warning(tmp_path):
    """排版类问题（clause 超长）只 WARN 不阻断，不一刀切。"""
    # 注意：文本必须以句末标点结束 —— 2026-10-21 起「无标点残句」是 ERROR，
    # 与「超长是 WARN」是两个维度，这里只验证超长不升级为 ERROR。
    long_text = "这是一句特别长的口播句子用来触发超长告警但不应阻断渲染流程。" * 2
    narr = make_narration()
    for sc in narr["scenes"]:
        if sc["visual"]["type"] == "news_item":
            sc["visual"]["images"] = ["images/ok.jpg"]
        sc["clauses"] = [long_text]
    tl = make_timeline()
    rc, errors, warnings = _run_validate(tmp_path, narr=narr, tl=tl,
                                         images=["images/ok.jpg"])
    assert rc == 0
    assert errors == []
    assert any("超长" in w for w in warnings)


def test_clean_fixture_passes(tmp_path):
    narr = make_narration()
    for sc in narr["scenes"]:
        if sc["visual"]["type"] == "news_item":
            sc["visual"]["images"] = ["images/ok.jpg"]
            sc["visual"]["image_source"] = "pexels"
    tl = make_timeline()
    rc, errors, warnings = _run_validate(tmp_path, narr=narr, tl=tl,
                                         images=["images/ok.jpg"])
    assert rc == 0, f"errors={errors}"
    assert errors == []


def test_master_duration_mismatch_is_error(tmp_path):
    """音频指纹：master.wav 时长与 timeline 记录不符必须失败。"""
    narr = make_narration()
    for sc in narr["scenes"]:
        if sc["visual"]["type"] == "news_item":
            sc["visual"]["images"] = ["images/ok.jpg"]
    rc, errors, _ = _run_validate(tmp_path, narr=narr, wav_dur=30.0,
                                  images=["images/ok.jpg"])
    assert rc == 1
    assert any("master.wav 时长" in e for e in errors)
