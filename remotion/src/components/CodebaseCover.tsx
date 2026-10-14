import React from "react";
import { AbsoluteFill } from "remotion";

type CodebaseCoverProps = {
  width: number;
  height: number;
  mainTitle: string;
  subtitle: string;
  tag?: string;
  pill?: string;
  author?: string;
};

// CJK/全角字符 ≈ 1.0em，其余（ASCII 半角）≈ 0.56em；粗体再加 6% 余量
const estimateTextWidth = (text: string, fontSize: number, letterSpacing: number): number => {
  let units = 0;
  let count = 0;
  for (const ch of text) {
    count += 1;
    units += /[\u2E80-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF\u3000-\u303F]/.test(ch) ? 1.0 : 0.56;
  }
  return units * fontSize * 1.06 + letterSpacing * Math.max(0, count - 1);
};

// 单行放不下则缩字号（下限 floor），配合 wordBreak 兜底换行。
// 2026-10-12 沉淀：whiteSpace: nowrap + 外层 overflow: hidden 会让超宽文案静默裁切。
const fitFontSize = (
  text: string,
  baseSize: number,
  maxWidth: number,
  letterSpacing: number,
  floor: number,
): number => {
  if (!text) return baseSize;
  const w = estimateTextWidth(text, baseSize, letterSpacing);
  if (w <= maxWidth) return baseSize;
  return Math.max(floor, Math.floor(baseSize * (maxWidth / w) * 0.97));
};

/**
 * video-upload skill 的 codebase-style 封面：深蓝径向渐变、细网格、
 * 顶/底光带、蓝黄橙渐变大标题与黄色描边胶囊。
 * 主视频首帧和各比例静态封面共用此组件，避免风格回归。
 */
export const CodebaseCover: React.FC<CodebaseCoverProps> = ({
  width,
  mainTitle,
  subtitle,
  tag = "AI 热点速览",
  pill = "AI 头条 · 1 分钟速览",
  author = "翻奇兽AI",
}) => {
  const scale = width / 1080;
  const contentWidth = width - 2 * Math.max(44, 70 * scale);
  const titleSize = fitFontSize(
    mainTitle,
    Math.max(78, Math.min(210, 128 * scale)),
    contentWidth * 0.88,
    4 * scale,
    64,
  );
  const subtitleSize = fitFontSize(
    subtitle,
    Math.max(34, Math.min(84, 58 * scale)),
    contentWidth * 0.88,
    0,
    34,
  );
  const tagSize = Math.max(28, Math.min(58, 38 * scale));
  const pillSize = fitFontSize(
    pill,
    Math.max(30, Math.min(62, 42 * scale)),
    contentWidth * 0.80 - 2 * 38 * scale,
    0,
    30,
  );
  const authorSize = Math.max(28, Math.min(54, 36 * scale));
  const sidePadding = Math.max(44, 70 * scale);

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        background:
          "radial-gradient(120% 82% at 50% 8%, #182b59 0%, #0b142c 55%, #050913 100%)",
        fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif',
      }}
    >
      <AbsoluteFill
        style={{
          opacity: 0.34,
          backgroundImage:
            "linear-gradient(rgba(126,168,255,0.18) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(126,168,255,0.18) 1px, transparent 1px)",
          backgroundSize: `${60 * scale}px ${60 * scale}px`,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: Math.max(28, 74 * scale),
          left: sidePadding,
          right: sidePadding,
          height: Math.max(4, 8 * scale),
          background:
            "linear-gradient(90deg, #ffd60a 0%, #7ecbff 46%, rgba(126,203,255,0.05) 100%)",
          boxShadow: "0 0 28px rgba(126,203,255,0.45)",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: Math.max(34, 76 * scale),
          left: "25%",
          right: "25%",
          height: Math.max(4, 8 * scale),
          background:
            "linear-gradient(90deg, transparent, rgba(255,214,10,0.95), transparent)",
          boxShadow: "0 0 28px rgba(255,214,10,0.42)",
        }}
      />
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: `${90 * scale}px ${sidePadding}px`,
          transform: "translateY(-2%)",
          textAlign: "center",
        }}
      >
        <div
          style={{
            color: "#8eb7ff",
            fontSize: tagSize,
            fontWeight: 800,
            letterSpacing: 3 * scale,
            marginBottom: 32 * scale,
          }}
        >
          {tag}
        </div>
        <div
          style={{
            maxWidth: "88%",
            color: "transparent",
            fontSize: titleSize,
            fontWeight: 950,
            letterSpacing: 4 * scale,
            lineHeight: 1.08,
            wordBreak: "break-word",
            background: "linear-gradient(100deg, #69bdff 0%, #ffd60a 48%, #ff7043 100%)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            textShadow: "0 10px 42px rgba(40,121,255,0.28)",
          }}
        >
          {mainTitle}
        </div>
        <div
          style={{
            maxWidth: "88%",
            marginTop: 48 * scale,
            color: "#ffffff",
            fontSize: subtitleSize,
            fontWeight: 850,
            lineHeight: 1.25,
            wordBreak: "break-word",
            textShadow: "0 5px 18px rgba(0,0,0,0.55)",
          }}
        >
          {subtitle}
        </div>
        <div
          style={{
            marginTop: 64 * scale,
            padding: `${18 * scale}px ${38 * scale}px`,
            border: `${Math.max(2, 3 * scale)}px solid #ffd60a`,
            borderRadius: 999,
            color: "#ffd60a",
            background: "rgba(255,214,10,0.10)",
            fontSize: pillSize,
            fontWeight: 900,
            wordBreak: "break-word",
            maxWidth: "80%",
            boxShadow: "0 0 26px rgba(255,214,10,0.15)",
          }}
        >
          {pill}
        </div>
        <div
          style={{
            marginTop: 54 * scale,
            color: "#b8d6ff",
            fontSize: authorSize,
            fontWeight: 750,
            letterSpacing: 2 * scale,
          }}
        >
          {author}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
