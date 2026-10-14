"""配图链路自检：回归验证文字图判别器 + 抽查图库检索词映射。

用途：改动 `looks_like_text_image()` 阈值或 `STOCK_HINTS` 映射后跑一次，
     确认判别器在标注样本集上仍全部正确。

用法：
    C:/Python313/python.exe scripts/verify_image_filter.py
    C:/Python313/python.exe scripts/verify_image_filter.py --samples <dir>

样本集（随 skill 走）：`references/imgsamples/{text,photo}/`
  - text/  8 张：AI HOT 品牌卡、ithome 标题卡、博客头图卡、OpenAI 渐变标题卡、
                 无内容纯渐变图（都**应**判为文字图）
  - photo/ 9 张：Pexels/Pixabay 实拍图、真实的页面配图（都**不**应判为文字图）
样本全部来自 2026-09-17 事故中真实出现过的 URL，不是人造数据。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_news import looks_like_text_image, stock_queries  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SAMPLES = os.path.join(os.path.dirname(HERE), "references", "imgsamples")

# 检索词映射抽查：标题 → 期望能命中摄影题材（人工核对用，不做断言）
PROBE_TITLES = (
    "VS Code 1.138 发布：智能体可在开发容器内运行",
    "HarnessTax 实测：同一模型换 harness 成功率几乎不变",
    "OpenSpec 发布：轻量 AI 编码规范框架",
    "Mozilla 91 页报告：开放权重模型仅落后前沿约 4 个月",
    "Google Research 的 R4T：检索扇出提速 12 至 20 倍",
)


def main():
    ap = argparse.ArgumentParser(description="配图链路自检")
    ap.add_argument("--samples", default=DEFAULT_SAMPLES, help="标注样本集目录")
    args = ap.parse_args()

    if not os.path.isdir(args.samples):
        print(f"FAIL: 找不到样本集 {args.samples}")
        return 1

    ok = bad = 0
    for kind, expect in (("text", True), ("photo", False)):
        d = os.path.join(args.samples, kind)
        if not os.path.isdir(d):
            print(f"FAIL: 缺少子目录 {d}")
            return 1
        print("-" * 62, kind.upper())
        for fn in sorted(os.listdir(d)):
            got = looks_like_text_image(os.path.join(d, fn))
            hit = got == expect
            ok += hit
            bad += not hit
            print("  %-22s 判为文字图=%-5s 期望=%-5s %s" % (
                fn.rsplit(".", 1)[0], got, expect, "OK" if hit else "<== 不一致"))
    print("=" * 62)
    print("准确率: %d/%d" % (ok, ok + bad))

    print("\n检索词映射抽查（人工核对是否指向摄影题材）：")
    for t in PROBE_TITLES:
        print("  %-40s -> %s" % (t[:40], stock_queries(t)))

    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
