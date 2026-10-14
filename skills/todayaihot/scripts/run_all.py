"""todayaihot 一键流水线：news.md -> 9:16 竖屏成片

    python run_all.py <news.md> [--backend edge] [--max-clauses 5] [--max-chars 120]

默认 TTS 后端 = edge-tts（免费、无需 Key、稳定）。
需要火山豆包真人声时用 --backend volc（或 auto：火山优先、失败自动降级 edge）。

环节：
    1. parse_news.py  解析 news.md      -> work/narration.json
    2. fetch_news.py  点击条目链接，抓取详细要点 + 配图，富化 narration.json
    3. gen_tts.py    逐句配音 + 时间轴 -> work/audio/master.wav + work/timeline.json
    4. render.py     Remotion 渲染     -> E:/WorkbuddyWorkspace/ainewstoday/out/每日ai热门新闻-yyyy-MM-dd.mp4

可用 --only parse|fetch|tts|render 单独跑某一环节，--skip-render 只做前两步（快速验证配音/字幕）。
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

sys.path.insert(0, HERE)
from common import NARRATION, OUT_DIR, TIMELINE, output_name  # noqa: E402


def run(script, extra):
    cmd = [PY, os.path.join(HERE, script)] + extra
    print(f"\n$ {os.path.basename(script)} {' '.join(extra)}")
    r = subprocess.run(cmd, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"\n[run_all] 环节失败: {script} (code={r.returncode})")
    return r


def check_deps():
    """启动时检查依赖，缺失则打印安装命令并退出。"""
    r = subprocess.run([PY, os.path.join(HERE, "check_deps.py")],
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("\n[run_all] 依赖检查失败，请先安装缺失依赖")


def validate(extra=None):
    """render 前校验 narration/timeline，ERROR 则中止。"""
    cmd = [PY, os.path.join(HERE, "validate_output.py")] + (extra or [])
    r = subprocess.run(cmd, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("\n[run_all] 产出物校验失败，请修复上述 ERROR 后重试")


def main():
    ap = argparse.ArgumentParser(description="news.md -> 9:16 竖屏视频")
    ap.add_argument("news_md", nargs="?", help="每日 AI 头条 markdown 路径（--smoke 模式下可省略）")
    ap.add_argument("--smoke", action="store_true", help="冒烟模式：用 smoke_fixture 生成 6s 测试数据，只验证渲染链路")
    ap.add_argument("--backend", default="edge", choices=["auto", "volc", "edge", "gptsovits"],
                    help="默认 edge；volc=火山豆包真人声；auto=火山优先失败降级；gptsovits=本地 GPT-SoVITS 克隆音色（需 9880 服务在线）")
    ap.add_argument("--align", default="auto", choices=["auto", "edge", "whisper"],
                    help="字幕对齐：auto=edge用词边界/其他用Whisper；edge=强制词边界；whisper=强制Whisper逐词对齐")
    ap.add_argument("--max-clauses", type=int, default=5)
    ap.add_argument("--max-chars", type=int, default=120)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--force-tts", action="store_true", help="强制重新合成配音")
    ap.add_argument("--skip-render", action="store_true", help="只跑到时间轴，不渲染")
    ap.add_argument("--only", default="", choices=["", "parse", "fetch", "tts", "render"])
    ap.add_argument("--no-fetch", action="store_true", help="跳过链接抓取富化（使用 md 自带摘要）")
    ap.add_argument("--out", default="", help="指定成片路径")
    ap.add_argument("--skip-check", action="store_true", help="跳过启动依赖检查")
    ap.add_argument("--skip-validate", action="store_true", help="跳过 render 前产出物校验")
    ap.add_argument("--check-links", action="store_true", help="校验时检查新闻链接可访问性（较慢）")
    ap.add_argument("--bgm", dest="bgm", action="store_true", default=True, help="开启 BGM 人声闪避混音（默认开启）")
    ap.add_argument("--no-bgm", dest="bgm", action="store_false", help="关闭 BGM 混音")
    args = ap.parse_args()

    if not args.skip_check:
        check_deps()

    only = args.only

    # ---------- 冒烟模式：生成 6s 测试数据，跳过 parse/fetch/tts ----------
    if args.smoke:
        print("\n=== 冒烟模式（smoke）===")
        run("smoke_fixture.py", [])
        only = "render"  # 直接跳到渲染

    # ---------- 1. 解析 ----------
    if only in ("", "parse"):
        if not args.news_md:
            print("FAIL: 冒烟模式外必须指定 news.md 路径")
            return 1
        md = os.path.abspath(args.news_md)
        if not os.path.isfile(md):
            print(f"FAIL: 找不到 news.md: {md}")
            return 1
        extra = [md, "--out", NARRATION,
                 "--max-clauses", str(args.max_clauses),
                 "--max-chars", str(args.max_chars)]
        run("parse_news.py", extra)
    if only == "parse":
        return 0

    # ---------- 2. 抓取富化（点击链接，补充详细要点 + 配图）----------
    if only in ("", "fetch") and not args.no_fetch:
        run("fetch_news.py", ["--narration", NARRATION])
    if only == "fetch":
        return 0

    # ---------- 3. 配音 + 时间轴 ----------
    if only in ("", "tts"):
        extra = ["--narration", NARRATION, "--timeline", TIMELINE,
                 "--backend", args.backend, "--align", args.align]
        if args.force_tts:
            extra.append("--force")
        run("gen_tts.py", extra)
    if only == "tts" or args.skip_render:
        return 0

    # ---------- 4. 渲染 ----------
    if not args.skip_validate:
        val_extra = []
        if args.check_links:
            val_extra.append("--check-links")
        validate(val_extra)

    extra = ["--timeline", TIMELINE, "--concurrency", str(args.concurrency)]
    if args.out:
        extra += ["--out", args.out]
    if not args.bgm:
        extra.append("--no-bgm")
    run("render.py", extra)

    # ---------- 5. 发布物料包 ----------
    if only in ("",):
        run("gen_publish.py", ["--narration", NARRATION, "--timeline", TIMELINE])

    # ---------- 6. 收尾：run_report + handoff 登记 ----------
    if only in ("",):
        run("finalize.py", ["--narration", NARRATION, "--timeline", TIMELINE])

    with open(TIMELINE, "r", encoding="utf-8") as f:
        date = json.load(f).get("date", "")
    final = args.out or os.path.join(OUT_DIR, output_name(date))
    print(f"\n✅ 成片: {final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
