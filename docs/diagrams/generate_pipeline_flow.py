# -*- coding: utf-8 -*-
"""生成 README 顶部的横向多排流水线图（SVG）。"""
import os

W, H = 1160, 566
ML = 30
COLS = 4
BW = 249
GAP = 34
ROW_H = 112

X = [ML + i * (BW + GAP) for i in range(COLS)]
ROW_Y = [64, 212, 360]
NOTE_Y = 498
NOTE_H = 46

ACCENT = {
    "collect": "#2563eb",
    "render": "#7c3aed",
    "publish": "#059669",
}

# 每个盒子: (阶段色, 序号, 标题, [正文行], 副标题?)
BOXES = [
    # row 1
    ("collect", "▶", "定时任务", ["每天 16:00 · Automation", "占位符替换即可启用"]),
    ("collect", "①", "AIHOT 采集", ["/api/v1/dailies/latest", "/feed/all.xml 条目池"]),
    ("collect", "②", "筛选 6–7 条", ["核心 · 细节 · 价值", "每条带原文直链"]),
    ("collect", "③", "落盘 news.md", ["AI新闻推送_YYYY-MM-DD", "结构化条目"]),
    # row 2 (右 → 左)
    ("render", "④", "parse 逐字稿", ["narration.json", "分句 + 字数试算"]),
    ("render", "⑤", "fetch 素材", ["原文要点 + 实拍配图", "兜底 Pexels / Pixabay"]),
    ("render", "⑥", "选 BGM", ["assets/bgm 免版权曲库", "闪避混音待用"]),
    ("render", "⑦", "gen_tts 配音", ["edge 云希 + WordBoundary", "master.wav + timeline"]),
    # row 3
    ("publish", "⑧", "validate 质量门", ["配图 · 残句 · 时间戳", "0 ERROR 才放行"]),
    ("publish", "⑨", "render + 抽帧", ["Remotion 1080×1920", "混音 + loudnorm"]),
    ("publish", "⑩", "物料 + 收尾", ["publish · chapters · covers", "run_report + handoff"]),
    ("publish", "⑪", "三平台发布", ["抖音 · B站 · 视频号", "封面重绘 + 回执登记"]),
]

STAGES = ["采集 · 写稿", "素材 · 配音", "成片 · 发布"]

out = []
a = out.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
  f'font-family="PingFang SC, Microsoft YaHei, Noto Sans SC, Helvetica Neue, Arial, sans-serif">')
a('<defs>')
a('<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">'
  '<path d="M 0 0.5 L 10 5 L 0 9.5 z" fill="#6e7781"/></marker>')
a('<filter id="shadow" x="-4%" y="-8%" width="108%" height="124%">'
  '<feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#1f2328" flood-opacity="0.10"/></filter>')
a('</defs>')
a(f'<rect x="0" y="0" width="{W}" height="{H}" rx="14" fill="#ffffff"/>')

# 行标题
for i, s in enumerate(STAGES):
    a(f'<text x="{ML}" y="{ROW_Y[i] - 14}" font-size="13" font-weight="700" fill="#8c959f" '
      f'letter-spacing="1.5">{s}</text>')

def box(col, row, accent, idx, title, lines):
    x = X[col]
    y = ROW_Y[row]
    a('<g>')
    a(f'<rect x="{x}" y="{y}" width="{BW}" height="{ROW_H}" rx="12" fill="#ffffff" stroke="#d0d7de" '
      f'stroke-width="1.2" filter="url(#shadow)"/>')
    a(f'<rect x="{x}" y="{y}" width="5" height="{ROW_H}" rx="2.5" fill="{accent}"/>')
    # 序号徽标
    a(f'<circle cx="{x + 34}" cy="{y + 32}" r="13" fill="{accent}" fill-opacity="0.12"/>')
    a(f'<text x="{x + 34}" y="{y + 37}" font-size="13" font-weight="700" fill="{accent}" '
      f'text-anchor="middle">{idx}</text>')
    a(f'<text x="{x + 56}" y="{y + 38}" font-size="16" font-weight="700" fill="#1f2328">{title}</text>')
    for j, ln in enumerate(lines):
        a(f'<text x="{x + 22}" y="{y + 68 + j * 20}" font-size="12.5" fill="#57606a">{ln}</text>')
    a('</g>')

# row1: 0..3 左→右
for c in range(4):
    box(c, 0, *BOXES[c])
# row2: 4..7 右→左（col 3,2,1,0）
for k in range(4):
    box(3 - k, 1, *BOXES[4 + k])
# row3: 8..11 左→右
for c in range(4):
    box(c, 2, *BOXES[8 + c])

def harrow(x1, x2, y, leftward=False):
    a(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#6e7781" stroke-width="2.1" '
      f'marker-end="url(#arrow)"/>')

def varrow(x, y1, y2):
    a(f'<path d="M {x} {y1} L {x} {y2}" stroke="#6e7781" stroke-width="2.1" fill="none" '
      f'marker-end="url(#arrow)"/>')

# 行内横向箭头
mid1 = ROW_Y[0] + ROW_H / 2
for c in range(3):
    harrow(X[c] + BW + 4, X[c + 1] - 5, mid1)
mid2 = ROW_Y[1] + ROW_H / 2
for c in range(3, 0, -1):
    harrow(X[c] - 5, X[c - 1] + BW + 4, mid2)
mid3 = ROW_Y[2] + ROW_H / 2
for c in range(3):
    harrow(X[c] + BW + 4, X[c + 1] - 5, mid3)

# 行间竖向换行箭头
varrow(X[3] + BW / 2, ROW_Y[0] + ROW_H + 3, ROW_Y[1] - 4)
varrow(X[0] + BW / 2, ROW_Y[1] + ROW_H + 3, ROW_Y[2] - 4)

# 底部硬门提示
a(f'<rect x="{ML}" y="{NOTE_Y}" width="{W - 2 * ML}" height="{NOTE_H}" rx="10" fill="#fff8e1" stroke="#f0d58c"/>')
a(f'<text x="{ML + 18}" y="{NOTE_Y + 21}" font-size="12.5" font-weight="700" fill="#7a5c00">硬门</text>')
a(f'<text x="{ML + 58}" y="{NOTE_Y + 21}" font-size="12.5" fill="#5c4a00">'
  f'缺实拍配图 / 口播残句 / 字幕时间戳异常 → validate_output 判 ERROR 并阻断出片（宁可当天不发）</text>')
a(f'<text x="{ML + 18}" y="{NOTE_Y + 37}" font-size="12.5" fill="#5c4a00">'
  f'<tspan font-weight="700" fill="#7a5c00">封面</tspan>'
  f'<tspan> 发布 JPG 必须由 social-auto-upload 的大字模板重绘，禁止用流水线 PNG 或视频首帧裁切图</tspan></text>')
a('</svg>')

dst = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images", "pipeline-flow.svg"))
with open(dst, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written:", dst, len("\n".join(out)), "bytes")
