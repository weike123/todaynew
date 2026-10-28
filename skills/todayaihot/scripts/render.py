"""Remotion 渲染 + 成片校验 + 归档命名。

用法:
    python render.py [--out E:/.../每日ai热门新闻-2026-09-06.mp4] [--concurrency 2]

流程:
    1. 校验 timeline.json / master.wav
    2. npx remotion render 1080x1920
    3. ffmpeg 校验（分辨率 / 时长 / 音轨）
    4. 移动为 每日ai热门新闻-yyyy-MM-dd.mp4
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import (  # noqa: E402
    AUDIO_DIR, BGM_DIR, CRF, CONCURRENCY, FPS, HEIGHT, OUT_DIR,
    PUBLIC_AUDIO, REMOTION_DIR, TIMELINE, WIDTH, ffmpeg_path,
    output_name, probe_streams, probe_video,
)

def _find_node() -> str:
    """定位 node：环境变量 > managed 运行时 > 系统 node。

    managed 运行时目录名带构建后缀（如 22.22.2-6），不能写死版本号，
    否则升级后探测路径失效。这里按目录名匹配 node 主版本 >= 18 的最新版本，
    并兼容 `current` 软链。
    """
    env = os.environ.get("WB_NODE")
    if env and os.path.exists(env):
        return env

    managed_root = os.path.join(
        os.path.expanduser("~"), ".workbuddy", "binaries", "node", "versions",
    )
    if os.path.isdir(managed_root):
        best = ""
        best_ver = (-1, -1, -1)
        for name in os.listdir(managed_root):
            exe = os.path.join(managed_root, name, "node.exe")
            if not os.path.exists(exe):
                continue
            # 目录名形如 22.22.2-6 / current / 24.7.0
            m = re.match(r"^(\d+)\.(\d+)\.(\d+)", name)
            if not m:
                continue
            ver = tuple(int(x) for x in m.groups())
            if ver[0] < 18:
                continue
            if ver > best_ver:
                best_ver, best = ver, exe
        if best:
            return best

    from shutil import which
    found = which("node")
    if found:
        return found
    return managed_root


NODE = _find_node()
CLI = os.path.join(REMOTION_DIR, "node_modules", "@remotion", "cli", "remotion-cli.js")


def sh(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(
            f"命令失败 (code={r.returncode}): {' '.join(cmd[:6])}\n"
            f"STDOUT:\n{r.stdout[-2000:]}\nSTDERR:\n{r.stderr[-2000:]}"
        )
    return r


def probe(path):
    """用 ffmpeg 读取视频元信息（兼容旧调用，内部转 common.probe_video）。"""
    return probe_video(path)


def write_render_state(out_dir: str, date: str, final_path: str,
                       bgm_path: str, mix_ok: bool, mix_mode: str,
                       loudness: dict | None = None):
    """把本次渲染的混音状态与最终文件实测写到 out_dir/render_state.json，
    供 finalize 合入 run_report（混音失败不得伪装成完成）。

    P0-2：额外记录音/视频流级时长与帧数（容器 Duration 掩盖流级差异，
    10-27 实测音轨比视频流长 0.133s），及最终文件哈希。
    """
    streams = probe_streams(final_path)
    state = {
        "date": date,
        "final_path": os.path.abspath(final_path),
        "final_sha256": common.sha256_file(final_path),
        "audio_mix": {
            "mode": mix_mode,            # bgm_duck / lufs_only / none
            "ok": bool(mix_ok),
            "bgm_file": os.path.basename(bgm_path) if bgm_path else "",
        },
        "loudness": loudness,            # {"integrated_lufs", "true_peak_dbtp", "lra"}；未测为 None
        "streams": streams,              # {"video_duration","audio_duration","video_frames","audio_frames"}；未测为 None
        "probe": probe_video(final_path),
        "rendered_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    path = os.path.join(out_dir, "render_state.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    lufs = loudness.get("integrated_lufs") if loudness else None
    print(f"[render] 状态存档 -> {path} (mix={mix_mode}, ok={mix_ok}, LUFS={lufs})")
    if streams and streams.get("video_duration") and streams.get("audio_duration"):
        diff = streams["audio_duration"] - streams["video_duration"]
        print(f"[render] 流级时长: 视频 {streams['video_duration']:.3f}s / "
              f"音频 {streams['audio_duration']:.3f}s（差异 {diff:+.3f}s）")
    return path


def find_bgm(seed: str = "") -> str:
    """扫描 BGM_DIR，用 seed 哈希确定性随机返回一个音频文件路径；目录为空返回空串。

    seed 传入成片路径/日期等可复现字符串：同 seed → 同一首 BGM（可重复渲染），
    不同视频自动错开；seed 为空则退化为时间戳随机。
    """
    if not os.path.isdir(BGM_DIR):
        return ""
    exts = (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac")
    files = sorted(f for f in os.listdir(BGM_DIR)
                   if f.lower().endswith(exts) and not f.startswith("README"))
    if not files:
        return ""
    import hashlib, time
    key = seed if seed else f"bgm::{time.time()}"
    idx = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % len(files)
    return os.path.join(BGM_DIR, files[idx])


def _port_available(port: int, hosts=("::1", "127.0.0.1", "::", "0.0.0.0")) -> bool:
    """该端口能否在所有 host 上同时绑定。

    Remotion 的 get-port 逻辑要求端口在 IPv4/IPv6 回环与通配地址上**都**可用，
    任意一个失败就判定该端口不可用。Windows 的「排除端口范围」策略
    （netsh int ipv4 show excludedportrange）常把 3000-3100 整段保留，
    导致 Remotion 报 "No available ports found"。
    """
    import socket
    for host in hosts:
        try:
            fam = socket.AF_INET6 if ":" in host else socket.AF_INET
            s = socket.socket(fam, socket.SOCK_STREAM)
            s.bind((host, port))
            s.close()
        except OSError:
            return False
    return True


def find_usable_port(ranges=((3000, 3101), (4000, 4101), (18000, 18051))) -> int:
    """找一个 Remotion 可用的端口；找不到返回 0（表示不指定 --port）。

    Remotion 默认在 3000-3100 找端口，该段常被系统策略保留。
    这里按优先级探测多段，返回第一个真正可用的端口。
    """
    for start, end in ranges:
        for port in range(start, end):
            if _port_available(port):
                return port
    return 0


def check_mix_preflight(bgm_enabled: bool, ff: str = "") -> tuple:
    """渲染前真实链路预检（T6/E9）。

    bgm_enabled=True 需要完整闪避链路；False 只需 loudnorm。
    返回 (ok, detail)。不通过时调用方必须在渲染前失败，
    不得静默归档未混音成片。
    """
    try:
        if not ff:
            ff = ffmpeg_path(require_mix=bgm_enabled)
    except FileNotFoundError as e:
        return False, str(e)
    if bgm_enabled:
        return common.probe_mix_chain(ff)
    return common.probe_loudnorm(ff)


def post_process_audio(input_path: str, output_path: str, bgm_path: str = "",
                       ff: str = "") -> bool:
    """渲染后音频后处理：BGM 人声闪避 + -14 LUFS 响度归一化。

    bgm_path 为空时只做 loudnorm。视频流 copy 不重编码，仅重编码音频。
    返回 True 成功。
    """
    ff = ff or ffmpeg_path()
    if bgm_path:
        # BGM 循环对齐 → 人声作侧链压低 BGM（闪避）→ 与人声混合 → loudnorm
        # 正确方向：sidechaincompress 主信号 = BGM，侧链信号 = 人声（人声说话时压低 BGM）
        filter_complex = (
            "[0:a]asplit=2[voice][sc];"
            "[1:a]aloop=loop=-1:size=2e+09,volume=0.30[bgm];"
            "[bgm][sc]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=350[bgm_ducked];"
            "[voice][bgm_ducked]amix=inputs=2:duration=first:normalize=0[mix];"
            "[mix]loudnorm=I=-14:TP=-1:LRA=11[out]"
        )
        cmd = [
            ff, "-y", "-hide_banner", "-loglevel", "error",
            "-i", input_path, "-i", bgm_path,
            "-filter_complex", filter_complex,
            "-map", "0:v", "-map", "[out]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
        print(f"[audio] BGM 闪避混音 + LUFS: {os.path.basename(bgm_path)}")
    else:
        # 仅 loudnorm
        cmd = [
            ff, "-y", "-hide_banner", "-loglevel", "error",
            "-i", input_path,
            "-af", "loudnorm=I=-14:TP=-1:LRA=11",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
        print("[audio] LUFS 归一化（无 BGM）")

    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.exists(output_path):
        print(f"[audio] 后处理失败，保留原片: {r.stderr[-300:]}")
        return False
    return True


def generate_chapters(timeline: dict, out_dir: str) -> str:
    """从 timeline 生成 B站章节文件 chapters.json + bilibili_chapters.txt。

    B站规范：3-10 条，首章 00:00，标题 ≤20 字。
    标题来源（P1-1 统一 schema）：timeline.scenes[] 现只含 id/clauses，
    语义标题在内嵌 narration.scenes[] 中，按 scene id 匹配；
    旧版 timeline 的 scenes[].visual 兼容保留。
    返回 chapters.json 路径。
    """
    scenes = timeline.get("scenes", [])
    narr_scenes = {
        s.get("id"): s for s in (timeline.get("narration") or {}).get("scenes", [])
    }

    def scene_title(sc: dict) -> str:
        vtype = sc.get("visual", {}).get("type", "")
        if vtype == "news_hook":
            return "开场速览"
        if vtype == "news_outro":
            return "结尾"
        title = sc.get("visual", {}).get("title", "")
        if not title and sc.get("id") in narr_scenes:
            title = narr_scenes[sc["id"]].get("visual", {}).get("title", "")
        return title

    chapters = []
    for sc in scenes:
        clauses = sc.get("clauses", [])
        if not clauses:
            continue
        start = clauses[0].get("start", 0)
        title = scene_title(sc)
        title = title[:20].strip()
        if not title:
            title = f"第{len(chapters)+1}条"
        mm = int(start) // 60
        ss = int(start) % 60
        chapters.append({
            "time": f"{mm:02d}:{ss:02d}",
            "seconds": round(start, 2),
            "title": title,
        })

    # B站要求 3-10 条，超出截断
    if len(chapters) > 10:
        chapters = chapters[:10]

    chapters_path = os.path.join(out_dir, "chapters.json")
    with open(chapters_path, "w", encoding="utf-8") as f:
        json.dump({"date": timeline.get("date", ""), "chapters": chapters}, f,
                  ensure_ascii=False, indent=2)

    # B站简介格式文本
    txt_path = os.path.join(out_dir, "bilibili_chapters.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for ch in chapters:
            f.write(f"{ch['time']} {ch['title']}\n")

    print(f"[chapters] 生成 {len(chapters)} 条章节 -> {chapters_path}")
    return chapters_path


def generate_covers(out_dir: str) -> list:
    """用 Remotion still 渲染三种比例封面到 out_dir/covers/。

    返回生成的封面路径列表。
    """
    covers_dir = os.path.join(out_dir, "covers")
    os.makedirs(covers_dir, exist_ok=True)

    # still 命令同样需要在可用端口上启动预览服务：Remotion 默认端口段
    # 3000-3100 常被系统「排除端口范围」保留，导致 "No available ports found"。
    port = find_usable_port()
    if port:
        print(f"[cover] 使用端口 {port}")
    else:
        print("[cover] 未找到四 host 通用端口，still 可能失败（可关闭占用 3000-3100 的进程）")

    specs = [
        ("Cover3x4", "cover_3x4.png", "小红书/抖音竖版"),
        ("Cover4x3", "cover_4x3.png", "B站横版"),
        ("Cover16x9", "cover_16x9.png", "公众号头图"),
    ]
    results = []
    for comp_id, filename, label in specs:
        out_path = os.path.join(covers_dir, filename)
        cmd = [
            NODE, CLI, "still", "src/index.tsx", comp_id, out_path,
        ]
        if port:
            cmd += ["--port", str(port)]
        try:
            r = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0 and os.path.exists(out_path):
                results.append(out_path)
                print(f"[cover] {label} {comp_id} -> {filename}")
            else:
                print(f"[cover] {label} 渲染失败: {r.stderr[-200:]}")
        except Exception as e:
            print(f"[cover] {label} 异常: {e}")
    return results


def check_input_binding(tl: dict, master_path: str) -> list:
    """P0-4 输入绑定校验：timeline 与音频/日期必须同源，错配返回问题列表。"""
    problems = []
    date = tl.get("date") or ""
    inner_date = (tl.get("narration") or {}).get("date", "")
    if inner_date and inner_date != date:
        problems.append(f"timeline 日期({date}) 与内嵌 narration 日期({inner_date}) 不一致，"
                        "疑似跨次错配；请重跑 gen_tts.py 重建 timeline")
    master_sha = common.sha256_file(master_path)
    tl_sha = tl.get("master_sha256", "")
    if tl_sha and master_sha and tl_sha != master_sha:
        problems.append("timeline.master_sha256 与当前 master.wav 不一致，"
                        "音频与时间轴非同一次生成；请重跑 gen_tts.py")
    elif not tl_sha:
        print("[render] 警告: timeline 缺少 master_sha256（旧版时间轴），跳过音频同源校验")
    return problems


def main():
    ap = argparse.ArgumentParser(description="Remotion 渲染 9:16 成片")
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--out", default="", help="最终成片路径（默认 out/每日ai热门新闻-<date>.mp4）")
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY)
    ap.add_argument("--crf", type=int, default=CRF)
    ap.add_argument("--bgm", dest="bgm", action="store_true", default=True,
                    help="开启 BGM 人声闪避混音 + LUFS 归一（默认开启）")
    ap.add_argument("--no-bgm", dest="bgm", action="store_false",
                    help="关闭 BGM，仅做 LUFS 归一化")
    args = ap.parse_args()

    if not os.path.exists(args.timeline):
        print(f"FAIL: 找不到 {args.timeline}，请先运行 parse_news.py + gen_tts.py")
        return 1

    with open(args.timeline, "r", encoding="utf-8") as f:
        tl = json.load(f)

    # 配音必须在 public/ 下，否则 Remotion 找不到
    master = os.path.join(AUDIO_DIR, "master.wav")
    if not os.path.exists(PUBLIC_AUDIO) and os.path.exists(master):
        shutil.copy(master, PUBLIC_AUDIO)
    if not os.path.exists(PUBLIC_AUDIO):
        print(f"FAIL: 缺少配音 {PUBLIC_AUDIO}")
        return 1

    date = tl.get("date") or ""
    if not date:
        print("FAIL: timeline.json 缺少 date 字段")
        return 1

    # ---- 输入绑定校验（P0-4）：timeline 与音频必须同源，错配即阻断 ----
    problems = check_input_binding(tl, master)
    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1

    # ---- 混音链路预检（T6/E9）：不支持的组合在渲染前失败，不静默归档未混音成片 ----
    ok, detail = check_mix_preflight(bgm_enabled=args.bgm)
    if not ok:
        print(f"FAIL: 混音链路预检未通过（bgm={args.bgm}）: {detail}")
        print("      处理：设置 TODAYAIHOT_FFMPEG 指向完整构建，或加 --no-bgm 仅做响度归一")
        return 1
    mix_ff = ffmpeg_path(require_mix=args.bgm)
    print(f"[render] 混音预检通过 -> {mix_ff}")

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp_out = os.path.join(REMOTION_DIR, "out", "main.mp4")
    os.makedirs(os.path.dirname(tmp_out), exist_ok=True)

    cmd = [
        NODE, CLI, "render", "src/index.tsx", "MainVideo", tmp_out,
        "--concurrency", str(args.concurrency),
        "--jpeg-quality", "80",
        "--crf", str(args.crf),
        "--pixel-format", "yuv420p",
    ]
    expect = int((tl["master_duration"] + 1.5) * FPS)
    print(f"[render] {WIDTH}x{HEIGHT} @{FPS}fps  预计 {expect} 帧 "
          f"({tl['master_duration']:.1f}s 音频)")
    print("[render] 首次运行会自动下载 Chrome Headless Shell，请耐心等待…")

    # 渲染（失败自动重试；第 2 次改用显式可用端口，规避 Remotion 默认
    # 3000-3100 端口段被系统「排除端口范围」保留导致的
    # "No available ports found" 硬失败）
    render_ok = False
    for attempt in range(2):
        if attempt > 0:
            print(f"[render] 第 {attempt + 1} 次重试…")
            try:
                if os.path.exists(tmp_out):
                    os.remove(tmp_out)
            except OSError:
                pass
            port = find_usable_port()
            if port:
                cmd = cmd + ["--port", str(port)]
                print(f"[render] 显式指定端口 {port}（规避系统保留端口段）")
        r = subprocess.run(cmd, cwd=REMOTION_DIR, encoding="utf-8", errors="replace")
        if r.returncode == 0 and os.path.exists(tmp_out):
            render_ok = True
            break
        print(f"[render] 第 {attempt + 1} 次渲染失败（returncode={r.returncode}）")

    if not render_ok:
        print("FAIL: Remotion 渲染失败（已重试 1 次，见上方输出）")
        print("      常见原因：3000-3100 端口段被系统策略保留。"
              "可关闭占用该段的代理/安全软件，或设置环境变量 REMOTION_PORT 指定其它端口")
        return 1

    # ---- 校验 ----
    info = probe(tmp_out)
    print(f"[check] {info['width']}x{info['height']} | {info['duration']:.1f}s | "
          f"音轨: {'有' if info['has_audio'] else '无'}")

    problems = []
    if (info["width"], info["height"]) != (WIDTH, HEIGHT):
        problems.append(f"分辨率异常: {info['width']}x{info['height']}")
    if not info["has_audio"]:
        problems.append("缺少音轨")
    if abs(info["duration"] - tl["master_duration"]) > 3.0:
        problems.append(
            f"时长偏差过大: 视频 {info['duration']:.1f}s vs 音频 {tl['master_duration']:.1f}s"
        )
    if problems:
        print("FAIL: " + "; ".join(problems))
        return 1

    # ---- 音频后处理：BGM 人声闪避 + -14 LUFS 归一化 ----
    bgm_path = find_bgm(seed=f"{date}|{tl.get('master_duration', '')}") if args.bgm else ""
    mix_mode = "bgm_duck" if bgm_path else "lufs_only"
    processed_out = tmp_out.replace(".mp4", "_processed.mp4")
    mix_ok = post_process_audio(tmp_out, processed_out, bgm_path, ff=mix_ff)
    mix_failed_reason = ""
    if mix_ok:
        source_for_archive = processed_out
        # AV 一致性：视频流 copy 帧数不变；音视频结束偏差 ≤ 1 帧目标（容器容差 0.15s）
        p_src, p_mix = probe_video(tmp_out), probe_video(processed_out)
        av_diff = abs(p_mix["duration"] - p_src["duration"])
        if av_diff > 0.15:
            print(f"[audio] 后处理前后时长偏差 {av_diff:.3f}s 超过 1 帧目标，按失败处理")
            mix_ok = False
            mix_failed_reason = f"后处理前后时长偏差 {av_diff:.3f}s"
            source_for_archive = tmp_out
    else:
        mix_failed_reason = "音频后处理（BGM 闪避/loudnorm）执行失败"
        source_for_archive = tmp_out  # 后处理失败时保留候选原片，但不得伪装成功

    # ---- 归档命名 ----
    # 目标已存在时 shutil.move 会退化为 copy+delete；沙箱的批量删除防护
    # 会拦截这个 delete 并使整个环节报错（成片其实已就位）。
    # 因此改为「先复制、清理失败不报错」。
    final = args.out or os.path.join(OUT_DIR, output_name(date))
    os.makedirs(os.path.dirname(os.path.abspath(final)), exist_ok=True)
    shutil.copy2(source_for_archive, final)
    try:
        os.remove(tmp_out)
    except OSError as e:
        print(f"[render] 中间产物清理被跳过（不影响成片）: {e}")
    size_mb = os.path.getsize(final) / 1024 / 1024

    # ---- 生成 B站章节文件 ----
    generate_chapters(tl, os.path.dirname(os.path.abspath(final)))

    # ---- 生成多比例封面 ----
    generate_covers(os.path.dirname(os.path.abspath(final)))

    # ---- 渲染状态存档（混音状态 + 最终文件实测 + 响度，供 finalize 合入报告）----
    # P0-2：无论混音成败都实测响度（未测≠合格）；混音失败仍归档候选片，
    # 但退出码非 0，finalize 会把该成片标为 BLOCKED，不得进入发布。
    loudness = common.measure_loudness(final)
    if loudness:
        print(f"[render] 成片响度实测: {loudness['integrated_lufs']} LUFS / "
              f"TP {loudness['true_peak_dbtp']} dBTP / LRA {loudness['lra']}")
        if abs(loudness["integrated_lufs"] + 14) > 1.0:
            print(f"[render] 警告: 综合响度 {loudness['integrated_lufs']} LUFS 偏离 -14±1 目标")
        if loudness["true_peak_dbtp"] > -1.0:
            print(f"[render] 警告: 真峰值 {loudness['true_peak_dbtp']} dBTP 超过 -1 目标")
    write_render_state(os.path.dirname(os.path.abspath(final)), date, final,
                       bgm_path, mix_ok, mix_mode, loudness=loudness)

    if not mix_ok:
        print(f"FAIL: 混音未通过（{mix_failed_reason}），候选片已归档但状态记为失败，"
              "不得发布；请检查 ffmpeg 完整构建后重跑 render")
        return 1

    print(f"DONE -> {final}")
    print(f"      {info['width']}x{info['height']} | {info['duration']:.1f}s | {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
