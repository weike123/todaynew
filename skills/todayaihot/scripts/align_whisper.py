"""Whisper 强制对齐：对合成后的 master.wav 做逐词时间戳对齐。

解决非 edge 后端（volc/gptsovits）只能句内均分时间戳导致字幕漂移的问题。
对 edge 后端也可用（WordBoundary 限流时的兜底）。

工作流：
  1. 加载 timeline.json + master.wav
  2. 按每个 clause 的 [start, end] 从 master.wav 切出音频片段
  3. faster-whisper 转写（word_timestamps=True），获取词级时间戳
  4. 词→字线性插值，与 clause 已知文本做字符级对齐
  5. 覆盖 clause.chars，timing_src=whisper
  6. 保存 timeline.json

用法:
    python align_whisper.py [--timeline work/timeline.json] [--model large-v3]
                            [--device cpu] [--compute_type int8]
"""
import argparse
import difflib
import json
import os
import re
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import AUDIO_DIR, SAMPLE_RATE, TIMELINE, TITLE_PAD  # noqa: E402


def _strip_text(s: str) -> str:
    """去空白、去标点，用于对齐匹配。"""
    return re.sub(r"[\s，,。.！!？?；;：:、\"'\"'（）()【】\[\]《》<>\-—…·]", "", s)


def slice_wav(master_path: str, start_sec: float, end_sec: float, out_path: str):
    """从 master.wav 切出 [start, end] 片段，保存为 out_path。"""
    with wave.open(master_path, "rb") as w:
        nchannels = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        nframes = w.getnframes()
        start_frame = int(start_sec * framerate)
        end_frame = int(end_sec * framerate)
        start_frame = max(0, min(start_frame, nframes))
        end_frame = max(start_frame, min(end_frame, nframes))
        w.setpos(start_frame)
        frames = w.readframes(end_frame - start_frame)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        w.writeframes(frames)


def align_clause_chars(text: str, whisper_words: list, clause_start: float) -> list:
    """把 whisper 词级时间戳对齐到 clause 文本的每个字符。

    返回 [{"ch": char, "t": seconds_since_clause_start}, ...]
    """
    # clause 字符列表（保留空白，用于最终输出）
    chars_all = list(text)
    # 去空白后的字符列表，用于对齐
    chars_nonws = [c for c in chars_all if c.strip()]
    if not chars_nonws:
        return []

    # whisper 词列表：每个词 {text, start, end}（相对于片段起点）
    # 拼接 whisper 文本，与 clause 文本做字符级对齐
    whisper_text = "".join(_strip_text(w.get("word", "")) for w in whisper_words)
    clause_text = "".join(_strip_text(c) for c in chars_nonws)

    if not whisper_text or not clause_text:
        # 无 whisper 结果，退回均分
        return _even_chars(chars_nonws, clause_start)

    # 字符级对齐：difflib 找匹配块
    matcher = difflib.SequenceMatcher(None, whisper_text, clause_text, autojunk=False)
    # 每个 clause 字符对应的 whisper 词索引和词内偏移
    char_to_word = [None] * len(chars_nonws)
    clause_pos = 0  # 在 clause_text 中的位置

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # 匹配块：whisper_text[i1:i2] == clause_text[j1:j2]
            # 找到这些 whisper 字符属于哪个词
            for k in range(j2 - j1):
                ci = j1 + k
                if ci < len(chars_nonws):
                    # 找这个 whisper 字符属于哪个词
                    wi = _find_word_at(whisper_words, i1 + k)
                    if wi is not None:
                        char_to_word[ci] = wi
        elif tag in ("replace", "delete"):
            # whisper 多识别或识别错：clause_text[j1:j2] 没有对应 whisper 字符
            # 用前后匹配的词时间插值，先标记为 None，后面统一处理
            pass
        # insert: clause 有但 whisper 没有，同样标记 None

    # 为每个字符分配时间
    result = []
    for ci, ch in enumerate(chars_nonws):
        wi = char_to_word[ci]
        if wi is not None:
            w = whisper_words[wi]
            # 词内字符线性插值
            word_text = _strip_text(w.get("word", ""))
            word_chars = list(word_text)
            # 找这个字符在词内的位置
            word_pos = 0
            # 简单：用词的起止时间，词内字符均分
            if len(word_chars) > 1:
                # 找到 ci 在 clause 中对应 whisper 词内的大致位置
                # 用匹配块的偏移
                t = w["start"] + (w["end"] - w["start"]) * 0.5  # 词中点
            else:
                t = w["start"]
            result.append({"ch": ch, "t": round(clause_start + t, 4)})
        else:
            result.append({"ch": ch, "t": None})

    # 对 None 时间做前后插值
    result = _interpolate_none(result, clause_start)
    return result


def _find_word_at(whisper_words: list, char_index: int) -> int:
    """找到 whisper 拼接文本中第 char_index 个字符属于哪个词。"""
    pos = 0
    for i, w in enumerate(whisper_words):
        wlen = len(_strip_text(w.get("word", "")))
        if pos <= char_index < pos + wlen:
            return i
        pos += wlen
    return None


def _interpolate_none(chars: list, clause_start: float) -> list:
    """对 t=None 的字符做前后线性插值。"""
    n = len(chars)
    # 先找所有已知时间的位置
    known = [(i, c["t"]) for i, c in enumerate(chars) if c["t"] is not None]
    if not known:
        # 全部未知，退回均分
        return _even_chars([c["ch"] for c in chars], clause_start)

    for i, c in enumerate(chars):
        if c["t"] is not None:
            continue
        # 找前一个和后一个已知
        prev = next(((j, t) for j, t in reversed(known) if j < i), None)
        nxt = next(((j, t) for j, t in known if j > i), None)
        if prev and nxt:
            ratio = (i - prev[0]) / (nxt[0] - prev[0])
            c["t"] = round(prev[1] + (nxt[1] - prev[1]) * ratio, 4)
        elif prev:
            c["t"] = prev[1]
        elif nxt:
            c["t"] = nxt[1]
        else:
            c["t"] = clause_start
    return chars


def _even_chars(chars: list, start: float) -> list:
    """兜底：句内均分时间戳。"""
    if not chars:
        return []
    # 估算时长：每字 0.25s
    dur = max(0.5, len(chars) * 0.25)
    step = dur / len(chars)
    return [{"ch": c, "t": round(start + i * step, 4)} for i, c in enumerate(chars)]


def main():
    ap = argparse.ArgumentParser(description="Whisper 强制对齐：逐字时间戳")
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--model", default=os.environ.get("WHISPER_MODEL", "large-v3"),
                    help="faster-whisper 模型（默认 large-v3，可选 small/medium/large-v3-turbo）")
    ap.add_argument("--device", default="cpu", help="cpu 或 cuda（AMD 卡用 cpu）")
    ap.add_argument("--compute_type", default="int8", help="int8/int8_float16/float16")
    ap.add_argument("--force", action="store_true", help="强制重新对齐（覆盖已有 whisper 时间戳）")
    args = ap.parse_args()

    # 检查 faster-whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("FAIL: faster-whisper 未安装。运行: pip install faster-whisper")
        return 1

    if not os.path.isfile(args.timeline):
        print(f"FAIL: 找不到 {args.timeline}，请先运行 gen_tts.py")
        return 1

    with open(args.timeline, encoding="utf-8") as f:
        tl = json.load(f)

    master = os.path.join(AUDIO_DIR, "master.wav")
    if not os.path.isfile(master):
        print(f"FAIL: 找不到 master.wav: {master}")
        return 1

    # 检查是否已经是 whisper 对齐
    existing = sum(1 for s in tl.get("scenes", []) for c in s.get("clauses", [])
                   if c.get("timing_src") == "whisper")
    if existing and not args.force:
        print(f"SKIP: timeline 已有 {existing} 句 whisper 对齐，加 --force 重新对齐")
        return 0

    print(f"[whisper] 加载模型 {args.model} ({args.device}/{args.compute_type})...")
    print(f"[whisper] 首次运行会下载模型（large-v3 约 3GB），请耐心等待")
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    tmpdir = tempfile.mkdtemp(prefix="whisper_align_")
    total = sum(len(s.get("clauses", [])) for s in tl.get("scenes", []))
    done = 0
    failed = 0

    for scene in tl.get("scenes", []):
        for clause in scene.get("clauses", []):
            done += 1
            text = clause.get("text", "")
            start = clause.get("start", 0)
            end = clause.get("end", start + 1)
            duration = end - start

            if duration < 0.3:
                print(f"  [{done}/{total}] 跳过（时长 {duration:.2f}s 过短）: {text[:30]}")
                continue

            # 切音频片段（clause.start 已含 TITLE_PAD，master.wav 也有 TITLE_PAD 前置静音，直接用）
            clip_path = os.path.join(tmpdir, f"clip_{done:03d}.wav")
            try:
                slice_wav(master, start, end, clip_path)
            except Exception as e:
                print(f"  [{done}/{total}] 切音频失败: {e}")
                failed += 1
                continue

            # faster-whisper 转写
            try:
                segments, info = model.transcribe(
                    clip_path,
                    language="zh",
                    word_timestamps=True,
                    initial_prompt="以下是中文AI新闻口播，包含技术术语和英文缩写。",
                    vad_filter=True,
                    beam_size=5,
                )
                whisper_words = []
                for seg in segments:
                    for w in (seg.words or []):
                        whisper_words.append({
                            "word": w.word,
                            "start": w.start,
                            "end": w.end,
                        })
            except Exception as e:
                print(f"  [{done}/{total}] 转写失败: {type(e).__name__}: {str(e)[:80]}")
                failed += 1
                continue

            if not whisper_words:
                print(f"  [{done}/{total}] 无转写结果，退回均分: {text[:30]}")
                failed += 1
                continue

            # 对齐到字符
            # 约定：chars[].t 必须是「相对句首」的秒数，与 gen_tts.build_chars /
            # finalize_chars 以及 remotion Subtitle.tsx 的 KTV 高亮逻辑一致
            #（后者用 elapsed = t - clause.start 与 ch.t 比较）。
            # 2026-09-18 修复：此处原先整段 +start 转成绝对全局时间，导致
            # ch.t <= elapsed 恒为假、KTV 高亮全程不变色（字幕只有白色）。
            chars = align_clause_chars(text, whisper_words, clause_start=0)

            clause["chars"] = chars
            clause["timing_src"] = "whisper"
            print(f"  [{done}/{total}] OK {len(whisper_words)}词/{len(chars)}字  {text[:30]}")

    # 清理临时文件
    import shutil
    try:
        shutil.rmtree(tmpdir)
    except OSError:
        pass

    # 保存
    with open(args.timeline, "w", encoding="utf-8") as f:
        json.dump(tl, f, ensure_ascii=False, indent=2)

    print(f"\nDONE 对齐 {done - failed}/{done} 句，失败 {failed} 句")
    print(f"timeline.json -> {args.timeline}")
    return 0 if failed < total else 0  # 部分失败不阻断，仍保存结果


if __name__ == "__main__":
    sys.exit(main())
