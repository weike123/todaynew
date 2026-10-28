"""P0-1/P0-3 质量门与发布回执哈希绑定（2026-10-28 方案首批切片）。

状态语义：
- BLOCKED：TTS 失败句 / 混音失败 / 成片不可测；
- GENERATED：成片可用但必选质量检查未完成（未审图、未查片尾、响度未测或超标）；
- READY：物料齐全 + 全部质量检查有合格记录，且审阅绑定同一视频 SHA256。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import (make_narration, make_timeline, make_video, read_json,  # noqa: E402
                      sha256_of, write_json)

import finalize  # noqa: E402


def _setup_run(tmp_path, ffmpeg, master_duration=99.0):
    d = str(tmp_path)
    narration = write_json(os.path.join(d, "narration.json"), make_narration())
    timeline = write_json(os.path.join(d, "timeline.json"),
                          make_timeline(master_duration=master_duration))
    video = make_video(ffmpeg, os.path.join(d, "每日ai热门新闻-2026-10-28.mp4"), duration=3.0)
    return {"dir": d, "narration": narration, "timeline": timeline, "video": video}


def _full_artifacts(run):
    d = run["dir"]
    with open(os.path.join(d, "publish.md"), "w", encoding="utf-8") as f:
        f.write("# 发布物料包\n")
    write_json(os.path.join(d, "chapters.json"), {"chapters": [
        {"time": "00:00", "title": "开场"}]})
    os.makedirs(os.path.join(d, "covers"), exist_ok=True)
    for name in ("cover_3x4.png", "cover_4x3.png", "cover_16x9.png"):
        with open(os.path.join(d, "covers", name), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")


def _write_render_state(run, mix_ok=True, lufs=-14.0, tp=-1.5):
    write_json(os.path.join(run["dir"], "render_state.json"), {
        "date": "2026-10-28",
        "final_path": run["video"],
        "audio_mix": {"mode": "bgm_duck", "ok": mix_ok, "bgm_file": "a.mp3"},
        "loudness": {"integrated_lufs": lufs, "true_peak_dbtp": tp, "lra": 6},
        "streams": {"video_duration": 3.0, "audio_duration": 3.0,
                    "video_frames": 90, "audio_frames": None},
    })


def _set_review(run, reviewed=True, tail=True, by="pytest"):
    """模拟人工审阅：直接改 run_report.json 的 quality 字段（与生产流程一致）。"""
    p = os.path.join(run["dir"], "run_report.json")
    report = read_json(p)
    report["quality"]["images_reviewed"] = reviewed
    report["quality"]["tail_frame_checked"] = tail
    report["quality"]["reviewed_by"] = by
    with open(p, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def _run_finalize(run, handoff=None):
    d = run["dir"]
    handoff = handoff or os.path.join(d, "handoff.md")
    argv = ["finalize.py", "--narration", os.path.join(d, "narration.json"),
            "--timeline", os.path.join(d, "timeline.json"),
            "--handoff", handoff, "--video", run["video"]]
    old = sys.argv
    sys.argv = argv
    try:
        return finalize.main()
    finally:
        sys.argv = old


def test_unreviewed_images_not_ready(tmp_path, ffmpeg):
    """物料齐全但未人工审图：只能 GENERATED，不能 READY（10-27 事故复现路径）。"""
    run = _setup_run(tmp_path, ffmpeg)
    _full_artifacts(run)
    _write_render_state(run)
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "GENERATED"
    assert any("配图未人工审阅" in r for r in report["blocked_reason"])


def test_mix_failed_blocked(tmp_path, ffmpeg):
    """混音失败（render_state audio_mix.ok=false）：BLOCKED，不得发布。"""
    run = _setup_run(tmp_path, ffmpeg)
    _full_artifacts(run)
    _write_render_state(run, mix_ok=False)
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "BLOCKED"
    assert any("混音失败" in r for r in report["blocked_reason"])


def test_tts_failed_blocked(tmp_path, ffmpeg):
    """TTS 存在失败句：BLOCKED。"""
    run = _setup_run(tmp_path, ffmpeg)
    tl = make_timeline()
    tl["failed_clauses"] = [{"scene": "s1_item", "index": 0,
                             "text": "x", "error": "boom"}]
    write_json(run["timeline"], tl)
    _full_artifacts(run)
    _write_render_state(run)
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "BLOCKED"


def test_loudness_out_of_range_not_ready(tmp_path, ffmpeg):
    """响度未测或真峰值超标：不能 READY。"""
    run = _setup_run(tmp_path, ffmpeg)
    _full_artifacts(run)
    _write_render_state(run, tp=-0.5)          # 真峰值超过 -1 目标
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "GENERATED"
    assert any("真峰值" in r for r in report["blocked_reason"])

    run2 = _setup_run(tmp_path, ffmpeg)
    # 清理 run1 留下的 render_state / run_report，隔离出「响度未测」场景
    for stale in ("render_state.json", "run_report.json"):
        p = os.path.join(run2["dir"], stale)
        if os.path.exists(p):
            os.remove(p)
    _full_artifacts(run2)                       # 无 render_state → 响度未测
    _run_finalize(run2)
    report2 = read_json(os.path.join(run2["dir"], "run_report.json"))
    assert report2["status"] == "GENERATED"
    assert any("响度未实测" in r for r in report2["blocked_reason"])


def test_ready_after_review_bound_to_sha(tmp_path, ffmpeg):
    """完整审阅记录 → READY；成片哈希变化后审阅失效，回到 GENERATED。"""
    run = _setup_run(tmp_path, ffmpeg)
    _full_artifacts(run)
    _write_render_state(run)
    _run_finalize(run)
    _set_review(run)
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "READY"
    assert report["quality"]["video_sha256"] == sha256_of(run["video"])

    # 重渲染产生新哈希 → 旧审阅作废
    with open(run["video"], "ab") as f:
        f.write(b"new-version-bytes")
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["status"] == "GENERATED"
    assert report["quality"]["images_reviewed"] is False, "哈希变化后旧审阅必须失效"


def test_publish_receipts_bound_to_video_sha(tmp_path, ffmpeg):
    """平台回执只属于发布时的那个视频版本：新版本不得继承旧版成功状态。"""
    run = _setup_run(tmp_path, ffmpeg)
    _full_artifacts(run)
    _write_render_state(run)
    _run_finalize(run)
    _set_review(run)
    # 外部发布技能回写回执
    p = os.path.join(run["dir"], "run_report.json")
    report = read_json(p)
    report["publish"] = {"douyin": {"status": "success", "id": "xyz"}}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    # 同一哈希重跑 finalize：回执保留
    _run_finalize(run)
    report = read_json(p)
    assert report["publish"]["douyin"]["status"] == "success"

    # 新版本（哈希变化）重跑：回执不继承
    with open(run["video"], "ab") as f:
        f.write(b"re-rendered")
    _run_finalize(run)
    report = read_json(p)
    assert "douyin" not in report.get("publish", {}), \
        "新版成片不得继承旧版发布回执"


def test_report_carries_stream_measurement(tmp_path, ffmpeg):
    """render_state 的流级实测进入 run_report.video.streams（P0-2）。"""
    run = _setup_run(tmp_path, ffmpeg)
    _write_render_state(run)
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    assert report["video"]["streams"]["video_duration"] == 3.0
    assert report["quality"]["audio_mix_ok"] is True


def test_handoff_older_date_update_is_scoped(tmp_path, ffmpeg):
    """补做旧日登记只替换该日期块，不得覆盖文件中更早出现的最新日期（P0-3）。"""
    run = _setup_run(tmp_path, ffmpeg)
    _write_render_state(run)
    handoff = os.path.join(run["dir"], "handoff.md")
    with open(handoff, "w", encoding="utf-8") as f:
        f.write(
            "# todaynew 项目交接说明\n\n## 视频登记\n\n"
            "### 自动登记（2026-10-27）\n"
            "<!-- finalize:begin -->\n- 日期：2026-10-27\n- 最新日内容\n<!-- finalize:end -->\n\n"
            "### 自动登记（2026-10-26）\n"
            "<!-- finalize:begin -->\n- 日期：2026-10-26\n- 旧日内容\n<!-- finalize:end -->\n"
        )
    # narration 日期改为 2026-10-26，模拟补做旧日 finalize
    narr = make_narration(date="2026-10-26")
    write_json(run["narration"], narr)
    rc = _run_finalize(run, handoff=handoff)
    assert rc == 0
    content = open(handoff, encoding="utf-8").read()
    assert "最新日内容" in content, "补做旧日登记不得覆盖最新日期块"
    assert content.count("### 自动登记（2026-10-27）") == 1
    assert content.count("### 自动登记（2026-10-26）") == 1
    assert "旧日内容" not in content, "旧日生成信息应被刷新"


def test_handoff_archive_on_oversize(tmp_path, ffmpeg):
    """handoff 超 24KiB 时历史日期块归档，当前日期块保留在正文。"""
    run = _setup_run(tmp_path, ffmpeg)
    narr = make_narration(date="2026-10-28")
    write_json(run["narration"], narr)
    _write_render_state(run)
    handoff = os.path.join(run["dir"], "handoff.md")
    filler = "历史内容" * 400          # 单块约 1.6KB，凑 20 块远超 24KiB
    blocks = "\n\n".join(
        f"### 自动登记（2026-09-{d:02d}）\n<!-- finalize:begin -->\n{filler}\n<!-- finalize:end -->"
        for d in range(1, 21)
    )
    with open(handoff, "w", encoding="utf-8") as f:
        f.write("# todaynew 项目交接说明\n\n## 视频登记\n\n" + blocks + "\n")
    _run_finalize(run, handoff=handoff)
    content = open(handoff, encoding="utf-8").read()
    assert "### 自动登记（2026-10-28）" in content, "当前日期块必须保留"
    assert "2026-09-05" not in content, "多数历史块应被归档移出正文"
    archives = [f for f in os.listdir(run["dir"]) if f.startswith("handoff-archive-")]
    assert archives, "超限必须产生归档文件"
    archived = open(os.path.join(run["dir"], archives[0]), encoding="utf-8").read()
    assert "2026-09-05" in archived, "被移出的历史块必须进入归档文件"


def test_report_streams_recorded_in_video(tmp_path, ffmpeg):
    """P0-2：render_state 的音视频流时长进入报告，便于暴露容器时长掩盖的差异。"""
    run = _setup_run(tmp_path, ffmpeg)
    _write_render_state(run)
    _run_finalize(run)
    report = read_json(os.path.join(run["dir"], "run_report.json"))
    streams = report["video"]["streams"]
    assert streams["video_duration"] == 3.0
    assert streams["audio_duration"] == 3.0
