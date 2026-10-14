"""todayaihot 公共路径与参数配置（所有脚本共用，避免路径漂移）。"""
import os
import re

# todayaihot/（skill 代码位置：C:/Users/<user>/.workbuddy/skills/todayaihot
# 项目里的 E:/workbuddy-workspace/todayaihot/skills/todayaihot 是指向它的 junction）
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_ROOT, "scripts")


def _load_dotenv():
    """轻量 .env 加载（不依赖 python-dotenv）。
    查找顺序：项目根 .env > skill 根 .env。已存在的环境变量不覆盖。"""
    candidates = [
        os.path.join(os.environ.get("TODAYAIHOT_ROOT", r"E:/workbuddy-workspace/todaynew"), ".env"),
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
PROJECT_ROOT = os.environ.get("TODAYAIHOT_ROOT", r"E:/workbuddy-workspace/todaynew")
REMOTION_DIR = os.path.join(PROJECT_ROOT, "remotion")
WORK_DIR = os.path.join(PROJECT_ROOT, "work")            # narration/timeline/音频中间产物
AUDIO_DIR = os.path.join(WORK_DIR, "audio")              # 逐句 wav + master.wav
OUT_DIR = os.path.join(PROJECT_ROOT, "out")              # 最终成片（用户指定归档根）
PUBLIC_AUDIO = os.path.join(REMOTION_DIR, "public", "audio", "master.wav")
IMAGES_DIR = os.path.join(REMOTION_DIR, "public", "images")   # 抓取到的新闻配图（Remotion 用 staticFile 读取）
BGM_DIR = os.path.join(SKILL_ROOT, "assets", "bgm")           # 免版权 BGM 目录（扫描其中的音频文件）

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
CONCURRENCY = 2


_FFMPEG_FULL_CACHE: str | None = None


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


def ffmpeg_path() -> str:
    """优先返回支持 -filter_complex 的完整 ffmpeg，失败才退回 Remotion 自带构建。

    2026-09-15 修正：原实现无条件优先用 Remotion 的 compositor-win32-x64-msvc/ffmpeg.exe，
    该精简构建不认 -filter_complex（报 `Invalid argument`）且缺少 aloop，
    导致 render.py 的 BGM 人声闪避后处理必然失败（静默保留原片，成片无 BGM）。
    """
    global _FFMPEG_FULL_CACHE
    from shutil import which
    if _FFMPEG_FULL_CACHE and os.path.exists(_FFMPEG_FULL_CACHE):
        return _FFMPEG_FULL_CACHE
    for cand in (os.environ.get("TODAYAIHOT_FFMPEG", ""), which("ffmpeg") or ""):
        if cand and os.path.exists(cand) and _supports_filter_complex(cand):
            _FFMPEG_FULL_CACHE = cand
            return cand
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


def ensure_dirs():
    for d in (WORK_DIR, AUDIO_DIR, OUT_DIR, os.path.dirname(PUBLIC_AUDIO), IMAGES_DIR):
        os.makedirs(d, exist_ok=True)


def output_name(date: str) -> str:
    """成片归档相对路径：<date>/每日ai热门新闻-<date>.mp4
    每天的视频放进以日期命名的子文件夹（2026-09-07 用户要求）。"""
    return os.path.join(date, f"每日ai热门新闻-{date}.mp4")
