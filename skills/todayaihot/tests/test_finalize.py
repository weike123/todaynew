"""T1 最终成片报告：finalize 必须实测最终文件，缺物料不 READY，不覆盖平台回执。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import (make_narration, make_timeline, make_video, read_json,  # noqa: E402
                      sha256_of, write_json)

import finalize  # noqa: E402


def _setup_run(tmp_path, ffmpeg, master_duration=99.0):
    """搭建一套最小 run 产物，返回路径字典。"""
    d = str(tmp_path)
    narration = write_json(os.path.join(d, "narration.json"), make_narration())
    timeline = write_json(os.path.join(d, "timeline.json"), make_timeline(master_duration=master_duration))
    video = make_video(ffmpeg, os.path.join(d, "每日ai热门新闻-2026-10-14.mp4"), duration=3.0)
    return {"dir": d, "narration": narration, "timeline": timeline, "video": video}


def _run_finalize(run, video=None, handoff=None):
    d = run["dir"]
    # 强制显式 handoff/video，防止旧实现回写真实项目 handoff.md / out/
    handoff = handoff or os.path.join(d, "handoff.md")
    video = video or run["video"]
    argv = ["finalize.py", "--narration", os.path.join(d, "narration.json"),
            "--timeline", os.path.join(d, "timeline.json"),
            "--handoff", handoff, "--video", video]
    old = sys.argv
    sys.argv = argv
    try:
        rc = finalize.main()
    finally:
        sys.argv = old
    return rc


def test_report_measures_final_video(tmp_path, ffmpeg):
    """run_report 的视频字段必须来自最终文件实测，不能用 master_duration 冒充。"""
    run = _setup_run(tmp_path, ffmpeg, master_duration=99.0)
    rc = _run_finalize(run)
    assert rc == 0
    report = read_json(os.path.join(run["dir"], "run_report.json"))

    v = report["video"]
    assert v["path"].endswith("每日ai热门新闻-2026-10-14.mp4")
    assert abs(v["duration_sec"] - 3.0) < 0.3, "视频时长必须实测，而非 master_duration=99"
    assert v["width"] == 1080 and v["height"] == 1920
    assert v["fps"] == 30
    assert v["sha256"] == sha256_of(run["video"])
    assert report["pipeline"]["render"]["duration_sec"] == v["duration_sec"]
    assert report["pipeline"]["render"]["fps"] == 30


def test_missing_artifact_not_ready(tmp_path, ffmpeg):
    """缺 publish.md / chapters / covers 时只能是 GENERATED，不能 READY。"""
    run = _setup_run(tmp_path, ffmpeg)
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "GENERATED"
    assert report["status"] != "READY"


def test_ready_when_all_artifacts(tmp_path, ffmpeg):
    """物料齐全 + 审阅记录齐全 + 混音/响度合格 → READY（P0-1 收紧后的就绪路径）。"""
    run = _setup_run(tmp_path, ffmpeg)
    with open(os.path.join(run["dir"], "publish.md"), "w", encoding="utf-8") as f:
        f.write("# 发布物料包\n")
    write_json(os.path.join(run["dir"], "chapters.json"), {"chapters": []})
    os.makedirs(os.path.join(run["dir"], "covers"), exist_ok=True)
    for name in ("cover_3x4.png", "cover_4x3.png", "cover_16x9.png"):
        with open(os.path.join(run["dir"], "covers", name), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
    # render.py 产出的混音/响度实测（P0-1 后 READY 必须有这些记录）
    write_json(os.path.join(run["dir"], "render_state.json"), {
        "audio_mix": {"mode": "bgm_duck", "ok": True, "bgm_file": "a.mp3"},
        "loudness": {"integrated_lufs": -14.2, "true_peak_dbtp": -1.4, "lra": 6},
    })
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "GENERATED", "未人工审阅前只能是 GENERATED"
    # 模拟人工审图 + 片尾检查后重跑 finalize → READY
    report["quality"]["images_reviewed"] = True
    report["quality"]["tail_frame_checked"] = True
    with open(os.path.join(run["dir"], "run_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "READY"


def test_blocked_when_video_missing(tmp_path, ffmpeg):
    """视频缺失：写 BLOCKED 报告并返回非零。"""
    run = _setup_run(tmp_path, ffmpeg)
    os.remove(run["video"])
    rc = _run_finalize(run)
    assert rc != 0
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "BLOCKED"
    assert report.get("blocked_reason")


def test_custom_video_path(tmp_path, ffmpeg):
    """自定义 --out 渲染后，finalize --video 指向同一文件，报告落在成片目录。"""
    run = _setup_run(tmp_path, ffmpeg)
    custom = os.path.join(run["dir"], "custom", "my-video.mp4")
    make_video(ffmpeg, custom, duration=2.0)
    rc = _run_finalize(run, video=custom)
    assert rc == 0
    report = read_json(os.path.join(run["dir"], "custom", "run_report.json"))
    assert report["video"]["path"] == os.path.abspath(custom)
    assert abs(report["video"]["duration_sec"] - 2.0) < 0.3


def test_handoff_preserves_publish_receipts(tmp_path, ffmpeg):
    """handoff 同日块更新不得覆盖发布技能已写入的平台回执。"""
    run = _setup_run(tmp_path, ffmpeg)
    handoff = os.path.join(run["dir"], "handoff.md")
    with open(handoff, "w", encoding="utf-8") as f:
        f.write(
            "# todaynew 项目交接说明\n\n## 视频登记\n\n"
            "### 自动登记（2026-10-14）\n"
            "<!-- finalize:begin -->\n- 日期：2026-10-14\n- 旧生成信息\n<!-- finalize:end -->\n"
            "<!-- publish:begin -->\n- 抖音：已发布（回执 xyz123）\n- B站：已发布（BV1xx）\n<!-- publish:end -->\n"
        )
    _run_finalize(run, handoff=handoff)
    content = open(handoff, encoding="utf-8").read()
    assert "抖音：已发布（回执 xyz123）" in content, "平台回执被覆盖"
    assert "BV1xx" in content
    assert "旧生成信息" not in content, "生成信息应被刷新"


def test_finalize_twice_keeps_publish_block(tmp_path, ffmpeg):
    """连续两次 finalize（返工重渲染场景）：回执仍在，生成信息刷新。"""
    run = _setup_run(tmp_path, ffmpeg)
    handoff = os.path.join(run["dir"], "handoff.md")
    _run_finalize(run, handoff=handoff)
    content = open(handoff, encoding="utf-8").read()
    assert "<!-- publish:begin -->" in content
    assert "<!-- finalize:begin -->" in content
    # 第二次
    _run_finalize(run, handoff=handoff)
    content2 = open(handoff, encoding="utf-8").read()
    assert content2.count("### 自动登记（2026-10-14）") == 1, "同日块不得重复"
    assert "<!-- publish:begin -->" in content2


def test_existing_publish_receipts_survive_report_rewrite(tmp_path, ffmpeg):
    """外部发布写回 run_report 的 publish 字段，finalize 重写时不得清空。"""
    run = _setup_run(tmp_path, ffmpeg)
    report_path = os.path.join(run["dir"], "run_report.json")
    write_json(report_path, {"date": "2026-10-14", "publish": {"douyin": {"status": "success"}}})
    _run_finalize(run)
    report = read_json(report_path)
    assert report["publish"]["douyin"]["status"] == "success"
