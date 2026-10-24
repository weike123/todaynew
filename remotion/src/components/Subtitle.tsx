import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { SUBTITLE_BOTTOM } from "../videoConfig";

/**
 * KTV 卡拉OK 字幕（大字幕分页版）
 * - 全片统一大字号（52px），不按句缩放
 * - 长句自动分页：每页约 32 个非空白字符，页内均衡拆成最多 2 行
 * - 分页边界不会拆开英文/数字单词（如 HydraFusion、GPT-6）
 * - 高亮跟随全局逐字时间轴，跨页连续；尾部字符提前压缩变色（见 gen_tts.py）
 */

const FONT_SIZE = 52;
const PAGE_CHARS = 32;          // 每页非空白字符数（2 行 × 16 字）
const HIGHLIGHT_LEAD = 0.08;    // 高亮提前量（秒），抵消渲染取帧误差

const isWordChar = (ch: string) => /[A-Za-z0-9]/.test(ch);
const isBreakChar = (ch: string) => /[,。！？；、：,.!?;: ]/.test(ch);

/** 文本每个位置之前的非空白字符数（前缀和） */
const nonwsPrefix = (text: string): number[] => {
  const pre = [0];
  for (let i = 0; i < text.length; i++) {
    pre[i + 1] = pre[i] + (text[i].trim() ? 1 : 0);
  }
  return pre;
};

/** 在 [lo, hi] 范围内找最佳断行位置（返回 text 切分下标） */
const findBreak = (text: string, lo: number, hi: number): number => {
  const a = Math.max(1, lo);
  const b = Math.min(text.length - 1, hi);
  // 优先级：标点/空格之后 > 单词边界 > 位置本身
  for (let off = 0; off <= b - a + 4; off++) {
    const p = a + off;
    if (p <= b && isBreakChar(text[p - 1]) && !(isWordChar(text[p - 1]) && isWordChar(text[p]))) return p;
    const q = b - off;
    if (q >= a && isBreakChar(text[q - 1]) && !(isWordChar(text[q - 1]) && isWordChar(text[q]))) return q;
  }
  // 兜底：不在单词内部断
  for (let p = a; p <= b; p++) {
    if (!(isWordChar(text[p - 1]) && isWordChar(text[p]))) return p;
  }
  return Math.min(Math.max(1, lo), text.length - 1);
};

/** 把整句切成若干页，返回 [{start, end}]（text 下标区间） */
const paginate = (text: string, prefix: number[]): { start: number; end: number }[] => {
  const total = prefix[text.length];
  if (total <= PAGE_CHARS) return [{ start: 0, end: text.length }];
  const pages: { start: number; end: number }[] = [];
  let start = 0;
  let startCi = 0;
  while (prefix[text.length] - startCi > PAGE_CHARS) {
    const targetCi = startCi + PAGE_CHARS;
    // 找到非空白序号 ≈ targetCi 的 text 下标
    let idx = start;
    for (let i = start; i < text.length; i++) {
      if (prefix[i + 1] > targetCi) { idx = i + 1; break; }
    }
    const brk = findBreak(text, idx - 6, idx + 6);
    pages.push({ start, end: brk });
    start = brk;
    startCi = prefix[brk];
  }
  pages.push({ start, end: text.length });
  return pages;
};

export const KTVSubtitle: React.FC<{ timeline: any }> = ({ timeline }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  let cur: any = null;
  outer: for (const s of Array.isArray(timeline?.scenes) ? timeline.scenes : []) {
    for (const c of Array.isArray(s?.clauses) ? s.clauses : []) {
      if (t >= c.start && t < c.end) {
        cur = c;
        break outer;
      }
    }
  }
  if (!cur) return null;

  const chars: any[] = Array.isArray(cur.chars) ? cur.chars : [];
  const elapsed = t - cur.start;
  const text: string = cur.text;
  const prefix = nonwsPrefix(text);

  // 已朗读的非空白字符数（含提前量）
  let spoken = 0;
  for (const ch of chars) if (ch.t <= elapsed + HIGHLIGHT_LEAD) spoken++;
  // 当前朗读位置决定所在页；句首spoken=0 时取第 0 页
  const pages = paginate(text, prefix);

  // 朗读位置落在哪一页：取最后一个「页起点 < spoken」的页
  let pageIdx = 0;
  for (let i = 0; i < pages.length; i++) {
    if (spoken > prefix[pages[i].start]) pageIdx = i;
  }
  const page = pages[pageIdx];
  const pageText = text.slice(page.start, page.end);
  const pageCiStart = prefix[page.start];
  const pageCiCount = prefix[page.end] - pageCiStart;

  // 页内拆行：>16 字时在中点附近断行（不拆英文单词）
  const lines: { text: string; ciStart: number }[] = [];
  const pageLen = pageText.length;
  if (prefix[pageLen + page.start] - pageCiStart <= PAGE_CHARS / 2) {
    lines.push({ text: pageText, ciStart: pageCiStart });
  } else {
    const mid = Math.floor(pageLen / 2);
    const brk = findBreak(pageText, mid - 6, mid + 6);
    const l1 = pageText.slice(0, brk);
    const l2 = pageText.slice(brk);
    lines.push({ text: l1, ciStart: pageCiStart });
    if (l2.trim()) lines.push({ text: l2, ciStart: pageCiStart + prefix[page.start + brk] - pageCiStart });
  }

  const wrap: React.CSSProperties = {
    position: "absolute",
    left: 70,
    right: 70,
    bottom: SUBTITLE_BOTTOM,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 12,
    fontFamily: '"PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
    fontWeight: 800,
    fontSize: FONT_SIZE,
    lineHeight: 1.35,
    letterSpacing: 1,
    textAlign: "center",
    color: "#ffffff",
    textShadow: "0 2px 10px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.65)",
    pointerEvents: "none",
  };

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={wrap}>
        {lines.map((ln, li) => {
          // 该行起始字符在全局非空白序 = ln.ciStart
          const globalStart = ln.ciStart;
          const lineNonws = Array.from(ln.text).filter((c) => c.trim()).length;
          const hi = Math.max(0, Math.min(lineNonws, spoken - globalStart));
          const done = hi >= lineNonws;
          return (
            <div key={li} style={{ whiteSpace: "pre-wrap" }}>
              {Array.from(ln.text).map((ch, i) => {
                const idx = Array.from(ln.text).slice(0, i).filter((c) => c.trim()).length;
                const on = done || idx < hi;
                return (
                  <span
                    key={i}
                    style={{
                      color: on ? "#ffd60a" : "#ffffff",
                      WebkitTextStroke: "1px rgba(0,0,0,0.35)",
                    }}
                  >
                    {ch}
                  </span>
                );
              })}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
