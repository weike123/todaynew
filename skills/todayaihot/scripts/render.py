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
from common import (  # noqa: E402
    AUDIO_DIR, BGM_DIR, CRF, CONCURRENCY, FPS, HEIGHT, OUT_DIR,
    PUBLIC_AUDIO, REMOTION_DIR, TIMELINE, WIDTH, ffmpeg_path,
    output_name,
)

def _find_node() -> str:
    """定位 node：环境变量 > managed 运行时 > 系统 node。"""
    env = os.environ.get("WB_NODE")
    if env and os.path.exists(env):
        return env
    managed = os.path.join(
        os.path.expanduser("~"), ".workbuddy", "binaries", "node",
        "versions", "22.22.2-2", "node.exe",
    )
    if os.path.exists(managed):
        return managed
    from shutil import which
    found = which("node")
    if found:
        return found
    return managed


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
    """用 ffmpeg 读取视频元信息。"""
    r = subprocess.run(
        [ffmpeg_path(), "-hide_banner", "-i", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    info = r.stderr
    dur = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", info)
    seconds = 0.0
    if dur:
        h, m, s = dur.groups()
        seconds = int(h) * 3600 + int(m) * 60 + float(s)
    video = re.search(r"Stream #\d+:\d+.*Video:.*?, (\d+)x(\d+)", info)
    audio = "Audio:" in info
    return {
        "duration": seconds,
        "width": int(video.group(1)) if video else 0,
        "height": int(video.group(2)) if video else 0,
        "has_audio": audio,
    }


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


def post_process_audio(input_path: str, output_path: str, bgm_path: str = "") -> bool:
    """渲染后音频后处理：BGM 人声闪避 + -14 LUFS 响度归一化。

    bgm_path 为空时只做 loudnorm。视频流 copy 不重编码，仅重编码音频。
    返回 True 成功。
    """
    ff = ffmpeg_path()
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
    返回 chapters.json 路径。
    """
    scenes = timeline.get("scenes", [])
    chapters = []
    for sc in scenes:
        clauses = sc.get("clauses", [])
        if not clauses:
            continue
        start = clauses[0].get("start", 0)
        # 标题：news_hook=开场，news_outro=结尾，news_item=visual.title
        vtype = sc.get("visual", {}).get("type", "")
        if vtype == "news_hook":
            title = "开场速览"
        elif vtype == "news_outro":
            title = "结尾"
        else:
            title = sc.get("visual", {}).get("title", "")
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

    # 渲染（失败自动重试 1 次）
    render_ok = False
    for attempt in range(2):
        if attempt > 0:
            print(f"[render] 第 {attempt + 1} 次重试…")
            try:
                if os.path.exists(tmp_out):
                    os.remove(tmp_out)
            except OSError:
                pass
        r = subprocess.run(cmd, cwd=REMOTION_DIR, encoding="utf-8", errors="replace")
        if r.returncode == 0 and os.path.exists(tmp_out):
            render_ok = True
            break
        print(f"[render] 第 {attempt + 1} 次渲染失败（returncode={r.returncode}）")

    if not render_ok:
        print("FAIL: Remotion 渲染失败（已重试 1 次，见上方输出）")
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
    processed_out = tmp_out.replace(".mp4", "_processed.mp4")
    if post_process_audio(tmp_out, processed_out, bgm_path):
        source_for_archive = processed_out
    else:
        source_for_archive = tmp_out  # 后处理失败时用原片

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

    print(f"DONE -> {final}")
    print(f"      {info['width']}x{info['height']} | {info['duration']:.1f}s | {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
