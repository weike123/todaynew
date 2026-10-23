"""T1 run_all 编排：--only render 后也必须完整收尾（E14）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run_all  # noqa: E402


def test_full_flow_order():
    steps = run_all.plan_steps(only="", no_fetch=False, skip_render=False)
    assert steps == ["parse", "fetch", "tts", "render", "gen_publish", "finalize"]


def test_only_render_includes_finalize():
    """返工重渲染后必须重新收尾，不能沿用旧报告（E14）。"""
    steps = run_all.plan_steps(only="render", no_fetch=False, skip_render=False)
    assert steps == ["render", "gen_publish", "finalize"]


def test_only_parse_is_exclusive():
    assert run_all.plan_steps(only="parse", no_fetch=False, skip_render=False) == ["parse"]


def test_only_fetch_exclusive():
    assert run_all.plan_steps(only="fetch", no_fetch=False, skip_render=False) == ["fetch"]


def test_only_tts_exclusive():
    assert run_all.plan_steps(only="tts", no_fetch=False, skip_render=False) == ["tts"]


def test_no_fetch_skips_fetch():
    steps = run_all.plan_steps(only="", no_fetch=True, skip_render=False)
    assert "fetch" not in steps
    assert steps == ["parse", "tts", "render", "gen_publish", "finalize"]


def test_skip_render_stops_at_tts():
    steps = run_all.plan_steps(only="", no_fetch=False, skip_render=True)
    assert steps == ["parse", "fetch", "tts"]
