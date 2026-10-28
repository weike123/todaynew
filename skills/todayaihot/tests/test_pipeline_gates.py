"""P0-4 流水线互斥锁 + 渲染输入绑定校验 + P1-1 章节标题来源修复。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import make_narration, make_timeline, write_json  # noqa: E402

import common  # noqa: E402
import render  # noqa: E402
import run_all  # noqa: E402


# ---------------------------------------------------------------- P0-4 锁

def test_lock_exclusive(tmp_path, monkeypatch):
    lock = os.path.join(str(tmp_path), "work", ".pipeline.lock")
    monkeypatch.setattr(run_all, "LOCK_PATH", lock)
    assert run_all.acquire_lock() is True
    # 同进程再取：拒绝
    assert run_all.acquire_lock() is False
    run_all.release_lock()
    # 释放后可再取
    assert run_all.acquire_lock() is True
    run_all.release_lock()


def test_lock_takes_over_stale(tmp_path, monkeypatch):
    """残留锁（持有进程已退出）必须可接管，不卡死流水线。"""
    lock = os.path.join(str(tmp_path), "work", ".pipeline.lock")
    monkeypatch.setattr(run_all, "LOCK_PATH", lock)
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    # 找一个几乎不可能存活的 PID
    dead_pid = 4194303 if os.name == "nt" else 4194303
    with open(lock, "w", encoding="utf-8") as f:
        f.write(str(dead_pid))
    assert run_all.acquire_lock() is True, "死进程残留锁必须可接管"
    run_all.release_lock()


def test_lock_alive_pid_refused(tmp_path, monkeypatch):
    lock = os.path.join(str(tmp_path), "work", ".pipeline.lock")
    monkeypatch.setattr(run_all, "LOCK_PATH", lock)
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    with open(lock, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))       # 当前测试进程存活
    assert run_all.acquire_lock() is False


# ---------------------------------------------------------------- P0-4 输入绑定

def _write_master(tmp_path):
    import wave
    import numpy as np
    p = os.path.join(str(tmp_path), "master.wav")
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(np.zeros(24000, dtype=np.int16).tobytes())
    return p


def test_binding_date_mismatch_blocked(tmp_path):
    master = _write_master(tmp_path)
    tl = make_timeline(date="2026-10-28")
    tl["narration"] = {"date": "2026-10-27", "scenes": []}
    problems = render.check_input_binding(tl, master)
    assert any("日期" in p for p in problems)


def test_binding_master_sha_mismatch_blocked(tmp_path):
    master = _write_master(tmp_path)
    tl = make_timeline(date="2026-10-28")
    tl["narration"] = {"date": "2026-10-28", "scenes": []}
    tl["master_sha256"] = "0" * 64          # 与实际 master 不符
    problems = render.check_input_binding(tl, master)
    assert any("master_sha256" in p for p in problems)


def test_binding_ok_when_same_source(tmp_path):
    master = _write_master(tmp_path)
    tl = make_timeline(date="2026-10-28")
    tl["narration"] = {"date": "2026-10-28", "scenes": []}
    tl["master_sha256"] = common.sha256_file(master)
    assert render.check_input_binding(tl, master) == []


def test_binding_legacy_timeline_without_sha_passes(tmp_path):
    master = _write_master(tmp_path)
    tl = make_timeline(date="2026-10-28")
    tl["narration"] = {"date": "2026-10-28", "scenes": []}
    assert render.check_input_binding(tl, master) == []


# ---------------------------------------------------------------- P1-1 章节

def test_chapters_use_narration_titles(tmp_path):
    """timeline.scenes[] 无 visual 时，章节标题必须从内嵌 narration 取得，
    不得全部退化成「第N条」（10-27 事故复现）。"""
    tl = make_timeline(date="2026-10-28")
    tl["narration"] = {
        "date": "2026-10-28",
        "scenes": [
            {"id": "s0_hook", "visual": {"type": "news_hook", "title": "开场"}},
            {"id": "s1_item", "visual": {"type": "news_item",
                                         "title": "Cloudflare 披露跨请求缓存泄露"}},
            {"id": "s2_item", "visual": {"type": "news_item",
                                         "title": "OpenAI 发布 GPT-6.1"}},
        ],
    }
    out_dir = os.path.join(str(tmp_path))
    render.generate_chapters(tl, out_dir)
    chapters = json.load(open(os.path.join(out_dir, "chapters.json"),
                              encoding="utf-8"))["chapters"]
    titles = [c["title"] for c in chapters]
    assert "开场速览" in titles
    assert "Cloudflare 披露跨请求缓存泄露" in titles[:20]
    assert "OpenAI 发布 GPT-6.1" in titles
    assert not all(t.startswith("第") for t in titles), "章节标题不得全部退化成第N条"
