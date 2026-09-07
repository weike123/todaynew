import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

export const COLORS = {
  bg0: "#070b16",
  bg1: "#0e1730",
  accent: "#4f8cff",   // 主蓝
  accent2: "#22d3ee",  // 青
  warn: "#ffd60a",     // KTV 黄
  text: "#ffffff",
  dim: "rgba(255,255,255,0.62)",
  faint: "rgba(255,255,255,0.34)",
  card: "rgba(255,255,255,0.055)",
  cardBorder: "rgba(255,255,255,0.12)",
};

export const FONT =
  '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", system-ui, sans-serif';

export const SECTION_COLOR: Record<string, string> = {
  全球大模型: "#4f8cff",
  "AI Coding": "#22d3ee",
  开源项目: "#a78bfa",
};

export function sectionColor(name: string): string {
  return SECTION_COLOR[name] || COLORS.accent;
}

/** 统一的深色背景：径向渐变 + 细网格 + 顶部光晕 */
export const Backdrop: React.FC<{ hue?: string }> = ({ hue }) => {
  const frame = useCurrentFrame();
  const drift = interpolate(frame % 300, [0, 300], [0, 40]);
  const c = hue || COLORS.accent;
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 90% at 50% 0%, ${COLORS.bg1} 0%, ${COLORS.bg0} 62%)`,
      }}
    >
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px)",
          backgroundSize: "90px 90px",
          backgroundPosition: `0px ${drift}px`,
          opacity: 0.55,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(60% 34% at 50% 6%, ${c}2e 0%, transparent 70%)`,
        }}
      />
    </AbsoluteFill>
  );
};

/** 顶部细进度条，反映全局播放进度 */
export const ProgressBar: React.FC<{ progress: number; color?: string }> = ({
  progress,
  color,
}) => (
  <div
    style={{
      position: "absolute",
      left: 0,
      right: 0,
      top: 0,
      height: 6,
      background: "rgba(255,255,255,0.08)",
    }}
  >
    <div
      style={{
        width: `${Math.max(0, Math.min(1, progress)) * 100}%`,
        height: "100%",
        background: `linear-gradient(90deg, ${color || COLORS.accent}, ${COLORS.accent2})`,
        boxShadow: `0 0 18px ${color || COLORS.accent}`,
      }}
    />
  </div>
);
