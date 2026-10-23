"""todayaihot 公共路径与参数配置（所有脚本共用，避免路径漂移）。"""
import os
import re

# todayaihot/ 的 skill 代码位置：
#   - 项目内副本：<项目根>/skills/todayaihot
#   - 用户级安装：<用户目录>/.workbuddy/skills/todayaihot
# 两者都从 __file__ 推导，不写死任何机器绝对路径。
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_ROOT, "scripts")


def _detect_project_root() -> str:
    """推导项目根目录（remotion/ 与 work/ 的父目录）。

    优先级：
      1. 环境变量 TODAYAIHOT_ROOT（显式覆盖，最高优先级）
      2. 从 skill 位置向上回溯：skill 在 <root>/skills/todayaihot 时，
         root = 上溯两级；skill 直接放在 <root> 下时，root = 上溯一级。
      3. 兜底：skill 目录的父目录（保证不抛异常，路径可能无效但可被环境变量纠正）

    这样任何克隆位置都能工作，不依赖写死的 E:/ 或 C:/ 盘符。
    """
    env = os.environ.get("TODAYAIHOT_ROOT", "").strip()
    if env:
        return os.path.abspath(env)

    # SKILL_ROOT = .../<root>/skills/todayaihot  ->  上溯两级得 <root>
    parent = os.path.dirname(SKILL_ROOT)
    if os.path.basename(parent).lower() == "skills":
        return os.path.abspath(os.path.dirname(parent))
    # SKILL_ROOT = .../<root>  ->  上溯一级得 <root>
    return os.path.abspath(parent)


PROJECT_ROOT = _detect_project_root()


def _load_dotenv():
    """轻量 .env 加载（不依赖 python-dotenv）。
    查找顺序：项目根 .env > skill 根 .env。已存在的环境变量不覆盖。"""
    candidates = [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(SKILL_ROOT, ".env"),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except OSError:
            pass


_load_dotenv()

# ---------------- 密钥（从环境变量加载，代码中不留明文默认值）----------------
# 火山引擎 seed-tts-2.0 API Key（缺失时 auto 后端自动降级 edge）
VOLC_API_KEY = os.environ.get("VOLC_TTS_API_KEY", "")
# 实拍图图库 Key（用户明令禁止文字图，原文抓不到照片时靠图库兜底）
# 缺失时跳过该源；两个源都缺失会退化为「关键词文字卡」，fetch_news 会打 CRITICAL 日志
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
PIXABAY_API_URL = os.environ.get("PIXABAY_API_URL", "https://pixabay.com/api/")

# ---------------- 项目根目录（数据/重资产与代码分离）----------------
# remotion 工程（node_modules 约 200MB+）、work 中间产物、out 成片都在项目目录下，
# 不随 skill 走；可用环境变量 TODAYAIHOT_ROOT 覆盖。
REMOTION_DIR = os.path.join(PROJECT_ROOT, "remotion")
WORK_DIR = os.path.join(PROJECT_ROOT, "work")            # narration/timeline/音频中间产物
AUDIO_DIR = os.path.join(WORK_DIR, "audio")              # 逐句 wav + master.wav
OUT_DIR = os.path.join(PROJECT_ROOT, "out")              # 最终成片（用户指定归档根）
PUBLIC_AUDIO = os.path.join(REMOTION_DIR, "public", "audio", "master.wav")
IMAGES_DIR = os.path.join(REMOTION_DIR, "public", "images")   # 抓取到的新闻配图（Remotion 用 staticFile 读取）


def _resolve_bgm_dir() -> str:
    """定位免版权 BGM 目录。

    优先级：
      1. 环境变量 TODAYAIHOT_BGM_DIR
      2. 项目根 assets/bgm（仓库内的规范位置，随代码一起克隆）
      3. skill 内 assets/bgm（用户级安装时的兜底）

    项目里历史上存在「项目根 assets/bgm」与「skill 内 assets/bgm」两份完全相同的
    副本（各约 492MB）。这里只做读取优先级，不主动删除任何一份——
    避免在用户不知情的情况下破坏其素材库。
    """
    env = os.environ.get("TODAYAIHOT_BGM_DIR", "").strip()
    if env:
        return os.path.abspath(env)
    for cand in (os.path.join(PROJECT_ROOT, "assets", "bgm"),
                 os.path.join(SKILL_ROOT, "assets", "bgm")):
        if os.path.isdir(cand):
            return cand
    return os.path.join(PROJECT_ROOT, "assets", "bgm")


BGM_DIR = _resolve_bgm_dir()                                   # 免版权 BGM 目录（扫描其中的音频文件）

NARRATION = os.path.join(WORK_DIR, "narration.json")
TIMELINE = os.path.join(WORK_DIR, "timeline.json")

# ---------------- 视频参数 ----------------
WIDTH = 1080
HEIGHT = 1920
FPS = 30
TITLE_PAD = 0.1          # 秒：首帧标题卡静音，配音轨 0.1s 后起播
TITLE_FRAMES = 3         # 0.1s * 30fps

# ---------------- TTS 参数（用户偏好：语速 +30% / 音量 +50%）----------------
SPEECH_RATE = 30         # 引擎原生参数，范围 [-50, 100]
LOUDNESS_RATE = 50       # 引擎原生参数，避免 PCM 乘增益导致削波
TARGET_RMS = 0.30        # 合成后再做一次响度归一，保证逐句听感一致
SAMPLE_RATE = 24000

# ---------------- 渲染参数 ----------------
CRF = 23
CONCURRENCY = 1   # 2026-10-14 T6：本机渲染并发默认 1（并发 2 曾 OOM），实测内存充裕后再调


_FFMPEG_FULL_CACHE: str | None = None

# 完整 ffmpeg 候选（按序探测）：环境变量 > PATH > 本机已知的完整构建。
# Remotion 自带的精简构建缺 asplit/aloop/sidechaincompress，只能做转码/响度，
# 不能做 BGM 闪避混音（E9）。
FFMPEG_CANDIDATES = (
    os.environ.get("TODAYAIHOT_FFMPEG", ""),
    "",
    r"D:/download/ffmpeg_v7.1.1_essentials_build_9663.com/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe",
)


def _supports_filter_complex(ff: str) -> bool:
    """探测该 ffmpeg 是否支持 -filter_complex（BGM 闪避混音依赖）。
    Remotion 自带的 compositor 版是精简构建，连 asplit/amix/aloop 都没有。"""
    import subprocess
    try:
        r = subprocess.run(
            [ff, "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "anullsrc", "-t", "0.1",
             "-filter_complex", "[0:a]anull[o]", "-map", "[o]",
             "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# 与 render.post_process_audio 生产链路一致的微型探测图
_MIX_PROBE_GRAPH = (
    "[0:a]asplit=2[voice][sc];"
    "[1:a]aloop=loop=-1:size=1000,volume=0.30[bgm];"
    "[bgm][sc]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=350[bgm_ducked];"
    "[voice][bgm_ducked]amix=inputs=2:duration=first:normalize=0[mix];"
    "[mix]loudnorm=I=-14:TP=-1:LRA=11[out]"
)


def probe_mix_chain(ff: str) -> tuple:
    """用与生产完全一致的滤镜组合做微型探测（T6/E9）。

    返回 (ok, detail)。任何一环缺失（asplit/aloop/sidechaincompress/amix/loudnorm、
    甚至 lavfi sine 源）都会失败——「能找到 exe」不等于「混音可用」。
    """
    import subprocess
    if not ff or not os.path.exists(ff):
        return False, f"ffmpeg 不存在: {ff}"
    try:
        r = subprocess.run(
            [ff, "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=0.2",
             "-f", "lavfi", "-i", "sine=frequency=220:duration=0.2",
             "-filter_complex", _MIX_PROBE_GRAPH, "-map", "[out]",
             "-t", "0.2", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"探测进程异常: {e}"
    if r.returncode == 0:
        return True, "mix chain ok"
    return False, (r.stderr or "").strip()[-200:] or f"returncode={r.returncode}"


def probe_loudnorm(ff: str) -> tuple:
    """探测 loudnorm 单滤镜（--no-bgm 模式所需的最低能力）。"""
    import subprocess
    if not ff or not os.path.exists(ff):
        return False, f"ffmpeg 不存在: {ff}"
    try:
        r = subprocess.run(
            [ff, "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=0.2",
             "-af", "loudnorm=I=-14:TP=-1:LRA=11",
             "-t", "0.2", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"探测进程异常: {e}"
    return (r.returncode == 0,
            "loudnorm ok" if r.returncode == 0 else (r.stderr or "")[-200:])


def ffmpeg_path(require_mix: bool = False) -> str:
    """返回 ffmpeg 路径。

    require_mix=True（BGM 闪避混音）：只返回通过真实链路预检的构建，
    全部候选不支持时抛 FileNotFoundError —— 绝不静默回退精简构建
    （2026-09-15 起旧逻辑回退后混音必然失败却保留原片，E9）。
    require_mix=False：支持 filter_complex 的候选优先，否则回退
    Remotion 自带构建（仅够转码/loudnorm）。
    """
    global _FFMPEG_FULL_CACHE
    from shutil import which
    if _FFMPEG_FULL_CACHE and os.path.exists(_FFMPEG_FULL_CACHE):
        if not require_mix or probe_mix_chain(_FFMPEG_FULL_CACHE)[0]:
            return _FFMPEG_FULL_CACHE
        _FFMPEG_FULL_CACHE = None
    cands = list(FFMPEG_CANDIDATES)
    if "" in cands:
        cands[cands.index("")] = which("ffmpeg") or ""
    for cand in cands:
        if not cand or not os.path.exists(cand):
            continue
        if require_mix:
            ok, _ = probe_mix_chain(cand)
            if not ok:
                continue
        elif not _supports_filter_complex(cand):
            continue
        _FFMPEG_FULL_CACHE = cand
        return cand
    if require_mix:
        raise FileNotFoundError(
            "未找到支持 BGM 闪避混音链路（asplit/aloop/sidechaincompress/amix/loudnorm）"
            "的 ffmpeg。可设置环境变量 TODAYAIHOT_FFMPEG 指向完整构建，"
            "或改用 --no-bgm（仅 loudnorm 归一）。"
        )
    bundled = os.path.join(
        REMOTION_DIR, "node_modules", "@remotion",
        "compositor-win32-x64-msvc", "ffmpeg.exe",
    )
    if os.path.exists(bundled):
        return bundled
    found = which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError(
        f"未找到 ffmpeg（期望 Remotion 自带: {bundled}）。"
        f"可先在 {REMOTION_DIR} 执行 npm install，或安装系统 ffmpeg。"
    )


def measure_loudness(path: str) -> dict | None:
    """用 loudnorm 分析模式实测综合响度/真峰值/LRA（T6）。

    返回 {"integrated_lufs", "true_peak_dbtp", "lra"}；测量失败返回 None。
    引用的是 loudnorm 打印的 input_*（原片指标），不是 output_*。
    """
    import json as _json
    import re as _re
    import subprocess
    try:
        ff = ffmpeg_path()
    except FileNotFoundError:
        return None
    try:
        r = subprocess.run(
            [ff, "-hide_banner", "-nostats", "-i", path,
             "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    m = _re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr or "")
    if not m:
        return None
    try:
        data = _json.loads(m.group(0))
        return {
            "integrated_lufs": round(float(data["input_i"]), 2),
            "true_peak_dbtp": round(float(data["input_tp"]), 2),
            "lra": round(float(data.get("input_lra", 0)), 2),
        }
    except (KeyError, ValueError, _json.JSONDecodeError):
        return None


def ensure_dirs():
    for d in (WORK_DIR, AUDIO_DIR, OUT_DIR, os.path.dirname(PUBLIC_AUDIO), IMAGES_DIR):
        os.makedirs(d, exist_ok=True)


def output_name(date: str) -> str:
    """成片归档相对路径：<date>/每日ai热门新闻-<date>.mp4
    每天的视频放进以日期命名的子文件夹（2026-09-07 用户要求）。"""
    return os.path.join(date, f"每日ai热门新闻-{date}.mp4")


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    """文件 SHA256；不存在返回空串。"""
    import hashlib
    if not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def probe_video(path: str) -> dict:
    """用 ffmpeg 实测视频元信息：duration/width/height/fps/has_audio/pix_fmt。

    解析失败或文件缺失时返回全零/False 字段，由调用方判定，不抛异常。
    """
    import re
    import subprocess
    info = {"duration": 0.0, "width": 0, "height": 0, "fps": 0,
            "has_audio": False, "pix_fmt": "", "exists": os.path.isfile(path)}
    if not info["exists"]:
        return info
    try:
        r = subprocess.run(
            [ffmpeg_path(), "-hide_banner", "-i", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return info
    text = r.stderr or ""
    dur = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", text)
    if dur:
        h, m, s = dur.groups()
        info["duration"] = int(h) * 3600 + int(m) * 60 + float(s)
    for m in re.finditer(r"Stream #\d+:\d+.*?: (Video|Audio): (.*)", text):
        kind, rest = m.group(1), m.group(2)
        if kind == "Video":
            wh = re.search(r", (\d{2,5})x(\d{2,5})", rest)
            if wh:
                info["width"], info["height"] = int(wh.group(1)), int(wh.group(2))
            fps = re.search(r"(\d+(?:\.\d+)?) fps", rest)
            if fps:
                info["fps"] = int(round(float(fps.group(1))))
            pix = re.search(r"(yuv\w+|rgb\w+|gbr\w+|gray\w*)", rest)
            if pix:
                info["pix_fmt"] = pix.group(1)
        else:
            info["has_audio"] = True
    return info
