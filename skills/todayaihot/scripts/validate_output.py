"""todayaihot 产出物自动校验脚本。

在 render 前调用，提前暴露问题，节省渲染时间。
0 ERROR 通过；WARN 不阻断但列入报告。

用法:
    python validate_output.py [--narration work/narration.json] [--timeline work/timeline.json]
                              [--check-links] [--strict]
    --check-links  检查每条新闻链接可访问性（较慢，默认关）
    --strict       WARN 也视为失败
"""
import argparse
import json
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    AUDIO_DIR, IMAGES_DIR, NARRATION, PUBLIC_AUDIO, TIMELINE,
)

MAX_SPOKEN_SECONDS = 60      # 口播硬上限
# 语速估算：基准 300 字/分钟，流水线固定以 --speed 1.3（语速 +30%）合成，故按 390 字/分钟折算。
# 2026-09-15 修正：原先用 300 未计入 +30% 语速，导致按 SKILL.md「50-60 秒」目标产出的稿子
# 必被判为超过 60s 上限（430 字实际合成 62s，却估成 86s），使合规成片无法通过校验。
WPM = int(os.environ.get("TTS_WPM_EST", "390"))
MAX_CLAUSE_CHARS = 40        # 单 clause 告警阈值
DURATION_TOLERANCE = 1.0     # 音频时长偏差容忍（秒）

errors = []
warnings = []


def err(msg):
    errors.append(msg)
    print(f"  ERROR: {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  WARN:  {msg}")


def load_json(path, label):
    if not os.path.isfile(path):
        err(f"{label} 不存在: {path}")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        err(f"{label} JSON 解析失败: {e}")
        return None


def validate_narration(narr, check_links=False):
    if not narr:
        return
    # 必填字段
    for field in ("date", "scenes", "total"):
        if field not in narr:
            err(f"narration 缺少必填字段: {field}")
    scenes = narr.get("scenes", [])
    if not scenes:
        err("narration.scenes 为空")
        return

    # 口播总字数与预估时长
    total_chars = 0
    item_count = 0
    for sc in scenes:
        v = sc.get("visual", {})
        if v.get("type") == "news_item":
            item_count += 1
            # visual 必填
            for field in ("title",):
                if not v.get(field):
                    err(f"场景 {sc.get('id')} 缺少 visual.{field}")
            # 配图文件存在性（IMAGES_DIR 就是 remotion/public/images，无需再拼路径——
            # 2026-09-17 修：旧写法 dirname(dirname(IMAGES_DIR)) + "remotion/public/images"
            # 会拼成 <root>/remotion/remotion/public/images，导致该检查恒报「文件不存在」）
            for img in v.get("images", []):
                full = os.path.join(IMAGES_DIR, os.path.basename(img))
                if not os.path.isfile(full):
                    warn(f"配图文件不存在: {img} ({full})")
            # image_sizes 与 images 平行
            imgs = v.get("images", [])
            sizes = v.get("image_sizes", [])
            if imgs and len(sizes) != len(imgs):
                warn(f"场景 {sc.get('id')} images({len(imgs)}) 与 image_sizes({len(sizes)}) 数量不一致")
            # 每条新闻必须有配图：无图时渲染端会退化为「关键词文字卡」，
            # 而用户已明令「不允许打字图片」（2026-09-17 事故根因即此，见 SKILL.md §配图）。
            # 判为 ERROR 而非 WARN：本流水线是无人值守自动发布，出片即推三平台，
            # 带着文字卡发布比当日不发更严重 —— 必须在这里硬阻断。
            if not imgs:
                err(f"场景 {sc.get('id')} 无配图（原文全为文字图且图库兜底失败）"
                    f" → 画面会退化为关键词文字卡，用户明令禁止: "
                    f"{(v.get('title') or '')[:26]}；请检查 .env 的 PEXELS_API_KEY / PIXABAY_API_KEY")
        for c in sc.get("clauses", []):
            total_chars += len(c)
            if len(c) > MAX_CLAUSE_CHARS:
                warn(f"场景 {sc.get('id')} clause 超长({len(c)}字): {c[:30]}...")

    est_seconds = total_chars / (WPM / 60)
    print(f"  口播总字数: {total_chars} | 预估时长: {est_seconds:.1f}s | 新闻条目: {item_count}")
    if est_seconds > MAX_SPOKEN_SECONDS:
        err(f"口播预估时长 {est_seconds:.1f}s 超过硬上限 {MAX_SPOKEN_SECONDS}s")
    elif est_seconds > MAX_SPOKEN_SECONDS - 5:
        warn(f"口播预估时长 {est_seconds:.1f}s 接近上限（剩余不足 5s）")

    # 链接可访问性（可选）
    if check_links:
        import requests
        print("  检查链接可访问性...")
        for sc in scenes:
            v = sc.get("visual", {})
            link = v.get("link", "")
            if not link:
                continue
            try:
                r = requests.head(link, timeout=5, allow_redirects=True)
                if r.status_code >= 400:
                    warn(f"链接 HTTP {r.status_code}: {link[:60]}")
            except Exception as e:
                warn(f"链接访问失败: {link[:60]} ({type(e).__name__})")


def validate_timeline(tl):
    if not tl:
        return
    for field in ("date", "scenes", "master_duration"):
        if field not in tl:
            err(f"timeline 缺少必填字段: {field}")
    scenes = tl.get("scenes", [])
    if not scenes:
        err("timeline.scenes 为空")
        return

    # 场景时间连续性
    prev_end = 0
    for sc in scenes:
        clauses = sc.get("clauses", [])
        if not clauses:
            warn(f"场景 {sc.get('id')} 无 clauses")
            continue
        first_start = clauses[0].get("start", 0)
        last_end = clauses[-1].get("end", 0)
        if first_start < prev_end - 0.01:
            err(f"场景 {sc.get('id')} 时间重叠: start={first_start:.2f} < prev_end={prev_end:.2f}")
        prev_end = last_end
        # 逐字时间戳
        for c in clauses:
            chars = c.get("chars", [])
            if not chars:
                warn(f"场景 {sc.get('id')} clause#{c.get('i')} 无逐字时间戳")
            timing = c.get("timing_src", "")
            if timing == "silent_fallback":
                warn(f"场景 {sc.get('id')} clause#{c.get('i')} 为 TTS 失败静音占位")

    # master.wav 存在且时长一致
    master = os.path.join(AUDIO_DIR, "master.wav")
    if not os.path.isfile(master) and os.path.isfile(PUBLIC_AUDIO):
        master = PUBLIC_AUDIO
    if os.path.isfile(master):
        try:
            with wave.open(master, "rb") as w:
                actual = w.getnframes() / w.getframerate()
            expected = tl.get("master_duration", 0)
            diff = abs(actual - expected)
            print(f"  master.wav 实际时长: {actual:.1f}s | timeline 记录: {expected:.1f}s | 偏差: {diff:.2f}s")
            if diff > DURATION_TOLERANCE:
                err(f"master.wav 时长({actual:.1f}s)与 timeline({expected:.1f}s)偏差 {diff:.1f}s > {DURATION_TOLERANCE}s")
        except Exception as e:
            warn(f"master.wav 读取失败: {e}")
    else:
        warn(f"master.wav 不存在: {master}")

    # TTS 失败句
    failed = tl.get("failed_clauses", [])
    if failed:
        warn(f"timeline 记录 {len(failed)} 句 TTS 失败（静音占位），可用 --force-tts 重跑")


def main():
    ap = argparse.ArgumentParser(description="todayaihot 产出物校验")
    ap.add_argument("--narration", default=NARRATION)
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--check-links", action="store_true", help="检查新闻链接可访问性")
    ap.add_argument("--strict", action="store_true", help="WARN 也视为失败")
    args = ap.parse_args()

    print("=" * 60)
    print("todayaihot 产出物校验")
    print("=" * 60)

    print("\n[1/2] narration.json")
    narr = load_json(args.narration, "narration.json")
    validate_narration(narr, check_links=args.check_links)

    print("\n[2/2] timeline.json")
    tl = load_json(args.timeline, "timeline.json")
    validate_timeline(tl)

    print("\n" + "=" * 60)
    print(f"结果: {len(errors)} ERROR, {len(warnings)} WARN")
    if errors:
        print("ERROR 列表:")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print("WARN 列表:")
        for w in warnings:
            print(f"  - {w}")
    print("=" * 60)

    if errors:
        return 1
    if args.strict and warnings:
        return 1
    print("校验通过 ✓" if not errors else "校验失败 ✗")
    return 0


if __name__ == "__main__":
    sys.exit(main())
