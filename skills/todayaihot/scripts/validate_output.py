"""todayaihot 产出物自动校验脚本。

在 render 前调用，提前暴露问题，节省渲染时间。
0 ERROR 通过；WARN 不阻断但列入报告。

分级原则（2026-10-14 T2）：
- ERROR（硬门，阻断渲染/发布）：缺配图、配图文件缺失或损坏、海报/文字卡兜底、
  TTS 静音占位、failed_clauses、日期/文本指纹不符、坏相对字时标、
  clause start>=end、master.wav 时长不符、口播残句（2026-10-21 新增，
  子句未以完整标点结束 / 由要点截切而成的非边界残句）。
- WARN（排版建议，不一刀切阻断）：clause 超长、无逐字时间戳、images/image_sizes
  数量不一致、链接不可达等。

用法:
    python validate_output.py [--narration work/narration.json] [--timeline work/timeline.json]
                              [--audio work/audio/master.wav] [--images-dir remotion/public/images]
                              [--check-links] [--strict]
    --check-links  检查每条新闻链接可访问性（较慢，默认关）
    --strict       WARN 也视为失败
"""
import argparse
import json
import os
import re
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    AUDIO_DIR, IMAGES_DIR, NARRATION, PUBLIC_AUDIO, TIMELINE,
)
from parse_news import clean_for_tts  # noqa: E402

MAX_SPOKEN_SECONDS = 60      # 口播硬上限
# 语速估算：基准 300 字/分钟，流水线固定以 --speed 1.3（语速 +30%）合成，故按 390 字/分钟折算。
# 2026-09-15 修正：原先用 300 未计入 +30% 语速，导致按 SKILL.md「50-60 秒」目标产出的稿子
# 必被判为超过 60s 上限（430 字实际合成 62s，却估成 86s），使合规成片无法通过校验。
WPM = int(os.environ.get("TTS_WPM_EST", "390"))
MAX_CLAUSE_CHARS = 40        # 单 clause 告警阈值
DURATION_TOLERANCE = 1.0     # 音频时长偏差容忍（秒）
CHAR_TOLERANCE = 0.05        # 字时标允许超出句长的余量（秒）
# 不得作为正式成片配图的来源类型（关键词海报卡兜底）
POSTER_SOURCES = {"poster", "keyword", "text", "textcard"}

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


def _check_image_file(img_rel: str, images_dir: str, scene_id: str):
    """配图文件存在性 + 可解码性 + 来源类型；返回是否通过。"""
    full = os.path.join(images_dir, os.path.basename(img_rel))
    if not os.path.isfile(full):
        err(f"场景 {scene_id} 配图文件不存在: {img_rel} ({full})")
        return False
    try:
        from PIL import Image
        with Image.open(full) as im:
            im.verify()
    except ImportError:
        warn(f"PIL 不可用，跳过配图可解码性检查: {img_rel}")
    except Exception as e:
        err(f"场景 {scene_id} 配图损坏或不可解码: {img_rel} ({type(e).__name__}: {e})")
        return False
    return True


def _clause_text(c) -> str:
    """clause 可能是纯字符串（narration.json）或 dict（timeline）。"""
    if isinstance(c, str):
        return c
    if isinstance(c, dict):
        return c.get("text", "")
    return ""


_CN_SENT_END = "。！？；"


def _marked_norm(s: str) -> str:
    """中文标点保留为边界哨兵 |，其余空白/标点删除（残句比对用）。"""
    s = re.sub(r"[，,。、；;：:！!？?]", "|", s or "")
    s = re.sub(r"[\s\"'“”‘’（）()\[\]【】]", "", s)
    return s


def check_clause_completeness(narr):
    """口播语义完整性硬门（2026-10-21 残句事故加固，ERROR 级）。

    规则：
    1. 每个口播子句必须以句末标点（。！？；）结束；
    2. 由 visual.bullets 派生的子句，若为某要点（清洗后）的严格前缀，
       截点后一个字符必须是中文标点边界（哨兵 |），否则为句中截断残句。
    无法对应到任何来源要点的子句（标题句/被清洗改写的文本）不误判。
    """
    for sc in narr.get("scenes", []):
        v = sc.get("visual", {})
        bullets = v.get("bullets", []) if v.get("type") == "news_item" else []
        for c in sc.get("clauses", []):
            ctext = _clause_text(c).strip()
            if not ctext:
                err(f"场景 {sc.get('id')} 存在空口播子句")
                continue
            if ctext[-1] not in _CN_SENT_END:
                err(f"场景 {sc.get('id')} 口播子句未以完整标点结束"
                    f"（结尾是 {ctext[-1]!r}）: {ctext[:36]}")
            if not bullets:
                continue
            cn = _marked_norm(ctext)
            if cn.endswith("|"):
                cn = cn[:-1]
            if not cn:
                continue
            for b in bullets:
                bm = _marked_norm(clean_for_tts(b))
                if bm.startswith(cn):
                    if len(cn) < len(bm) and bm[len(cn)] != "|":
                        err(f"场景 {sc.get('id')} 口播要点被截成残句"
                            f"（截点后是 {bm[len(cn)]!r}，非中文标点边界）: {ctext[:36]}")
                    break


def validate_narration(narr, check_links=False, images_dir=IMAGES_DIR):
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
            # 配图文件存在性 + 可解码（IMAGES_DIR 就是 remotion/public/images）
            for img in v.get("images", []):
                _check_image_file(img, images_dir, sc.get("id"))
            # image_sizes 与 images 平行（排版建议，不阻断）
            imgs = v.get("images", [])
            sizes = v.get("image_sizes", [])
            if imgs and len(sizes) != len(imgs):
                warn(f"场景 {sc.get('id')} images({len(imgs)}) 与 image_sizes({len(sizes)}) 数量不一致")
            # 海报/文字卡来源不得进入正式成片（T2 硬门）
            src = (v.get("image_source") or "").lower()
            if src in POSTER_SOURCES:
                err(f"场景 {sc.get('id')} 配图来源为海报/文字卡兜底（{src}），"
                    f"用户明令禁止: {(v.get('title') or '')[:26]}")
            # 每条新闻必须有配图：无图时渲染端会退化为「关键词文字卡」，
            # 用户已明令「不允许打字图片」（2026-09-17 事故根因即此）。
            # 判为 ERROR 而非 WARN：无人值守自动发布，出片即推三平台，
            # 带着文字卡发布比当日不发更严重 —— 必须在这里硬阻断。
            if not imgs:
                err(f"场景 {sc.get('id')} 无配图（原文全为文字图且图库兜底失败）"
                    f" → 画面会退化为关键词文字卡，用户明令禁止: "
                    f"{(v.get('title') or '')[:26]}；请检查 .env 的 PEXELS_API_KEY / PIXABAY_API_KEY")
        for c in sc.get("clauses", []):
            ctext = _clause_text(c)
            # 按非空白字符计数：tts_normalize 会给英文插入助读空格（A M D / C P U /
            # Deep Seek），这些空格不占口播时长。2026-10-21 实测 raw 基数高估约
            # 33%（374 raw 估 57.5s，实际 43.2s），修复残句后更会误报 >60s。
            total_chars += len(re.sub(r"\s", "", ctext))
            if len(ctext) > MAX_CLAUSE_CHARS:
                warn(f"场景 {sc.get('id')} clause 超长({len(ctext)}字): {ctext[:30]}...")

    est_seconds = total_chars / (WPM / 60)
    print(f"  口播总字数: {total_chars} | 预估时长: {est_seconds:.1f}s | 新闻条目: {item_count}")
    if est_seconds > MAX_SPOKEN_SECONDS:
        err(f"口播预估时长 {est_seconds:.1f}s 超过硬上限 {MAX_SPOKEN_SECONDS}s")
    elif est_seconds > MAX_SPOKEN_SECONDS - 5:
        warn(f"口播预估时长 {est_seconds:.1f}s 接近上限（剩余不足 5s）")

    # 口播语义完整性（2026-10-21 残句事故硬门）：子句必须以完整标点结束，
    # 由要点截切而来的子句必须停在中文标点边界上
    check_clause_completeness(narr)

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


def _check_char_timestamps(scene_id: str, clause: dict):
    """逐字相对时间戳：负值 / 逆序 / 超出句长 → ERROR。"""
    chars = clause.get("chars", [])
    if not chars:
        return
    start, end = clause.get("start", 0), clause.get("end", 0)
    dur = end - start
    prev_t = None
    for idx, ch in enumerate(chars):
        t = ch.get("t")
        if t is None:
            continue
        if t < 0:
            err(f"场景 {scene_id} clause#{clause.get('i')} 字时标为负: chars[{idx}].t={t}")
            return
        if prev_t is not None and t < prev_t - 1e-6:
            err(f"场景 {scene_id} clause#{clause.get('i')} 字时标逆序: "
                f"chars[{idx}].t={t} < chars[{idx-1}].t={prev_t}")
            return
        if dur > 0 and t > dur + CHAR_TOLERANCE:
            err(f"场景 {scene_id} clause#{clause.get('i')} 字时标超出句长: "
                f"chars[{idx}].t={t:.3f} > 句长 {dur:.3f}s（应为相对句首时间）")
            return
        prev_t = t


def validate_timeline(tl, narr=None, audio_path=""):
    if not tl:
        return
    for field in ("date", "scenes", "master_duration"):
        if field not in tl:
            err(f"timeline 缺少必填字段: {field}")
    scenes = tl.get("scenes", [])
    if not scenes:
        err("timeline.scenes 为空")
        return

    # ---- 跨文件一致性：日期与文本指纹 ----
    if narr:
        nd, td = narr.get("date", ""), tl.get("date", "")
        if nd and td and nd != td:
            err(f"narration 与 timeline 日期不一致: {nd} != {td}")
        embedded = tl.get("narration")
        if not isinstance(embedded, dict) or not embedded.get("scenes"):
            err("timeline 缺少内嵌 narration（无法做文本指纹校验）")
        else:
            if embedded.get("date") and nd and embedded["date"] != nd:
                err(f"timeline 内嵌 narration 日期与 narration.json 不一致: "
                    f"{embedded['date']} != {nd}")
            n_scenes = [s for s in narr.get("scenes", [])]
            e_scenes = embedded.get("scenes", [])
            if len(n_scenes) != len(e_scenes):
                err(f"文本指纹不符: narration {len(n_scenes)} 场景 vs 内嵌 {len(e_scenes)} 场景")
            else:
                for ns, es in zip(n_scenes, e_scenes):
                    nv, ev = ns.get("visual", {}), es.get("visual", {})
                    if nv.get("type") == "news_item":
                        nt = (nv.get("title") or "").strip()
                        et = (ev.get("title") or "").strip()
                        if nt != et:
                            err(f"文本指纹不符: 场景 {ns.get('id')} 标题 "
                                f"「{nt[:20]}」 vs 内嵌「{et[:20]}」")
                    n_texts = [_clause_text(c) for c in ns.get("clauses", [])]
                    e_texts = [_clause_text(c) for c in es.get("clauses", [])]
                    if n_texts != e_texts:
                        err(f"文本指纹不符: 场景 {ns.get('id')} 口播句与内嵌 narration 不一致")

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
        # 逐句边界 + 逐字时间戳
        for c in clauses:
            if c.get("start", 0) >= c.get("end", 0):
                err(f"场景 {sc.get('id')} clause#{c.get('i')} start({c.get('start')}) "
                    f">= end({c.get('end')})")
            chars = c.get("chars", [])
            if not chars:
                warn(f"场景 {sc.get('id')} clause#{c.get('i')} 无逐字时间戳")
            else:
                _check_char_timestamps(sc.get("id"), c)
            if c.get("timing_src") == "silent_fallback":
                err(f"场景 {sc.get('id')} clause#{c.get('i')} 为 TTS 失败静音占位"
                    f"（silent_fallback），不得作为正式成片")

    # master.wav 存在且时长一致（音频指纹）
    master = audio_path or os.path.join(AUDIO_DIR, "master.wav")
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

    # TTS 失败句（硬门）
    failed = tl.get("failed_clauses", [])
    if failed:
        err(f"timeline 记录 {len(failed)} 句 TTS 失败（静音占位），不得发布: {failed[:5]}")


def main():
    ap = argparse.ArgumentParser(description="todayaihot 产出物校验")
    ap.add_argument("--narration", default=NARRATION)
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--audio", default="",
                    help="master.wav 路径（默认 work/audio/master.wav，回退 public/audio）")
    ap.add_argument("--images-dir", default=IMAGES_DIR,
                    help="配图目录（默认 remotion/public/images）")
    ap.add_argument("--check-links", action="store_true", help="检查新闻链接可访问性")
    ap.add_argument("--strict", action="store_true", help="WARN 也视为失败")
    args = ap.parse_args()

    # 同一进程重复调用时重置累计结果
    errors.clear()
    warnings.clear()

    print("=" * 60)
    print("todayaihot 产出物校验")
    print("=" * 60)

    print("\n[1/2] narration.json")
    narr = load_json(args.narration, "narration.json")
    validate_narration(narr, check_links=args.check_links, images_dir=args.images_dir)

    print("\n[2/2] timeline.json")
    tl = load_json(args.timeline, "timeline.json")
    validate_timeline(tl, narr=narr, audio_path=args.audio)

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
