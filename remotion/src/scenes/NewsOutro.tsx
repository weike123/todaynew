import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
} from "remotion";
import { Backdrop, COLORS, FONT } from "../components/theme";

/** 结尾引导 */
export const NewsOutro: React.FC<{ v: any }> = ({ v }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 200 } });

  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <Backdrop />

      <AbsoluteFill
        style={{ justifyContent: "center", alignItems: "center", padding: 90 }}
      >
        <div
          style={{
            fontSize: 46,
            color: COLORS.accent2,
            fontWeight: 700,
            letterSpacing: 6,
            opacity: interpolate(frame, [0, 12], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          今日盘点
        </div>

        <div
          style={{
            marginTop: 30,
            fontSize: 168,
            fontWeight: 900,
            color: COLORS.warn,
            lineHeight: 1,
            transform: `scale(${0.86 + s * 0.14})`,
            textShadow: "0 0 70px rgba(255,214,10,0.3)",
          }}
        >
          {v.total}
        </div>

        <div
          style={{
            marginTop: 16,
            fontSize: 58,
            color: "#fff",
            fontWeight: 800,
          }}
        >
          条 AI 头条
        </div>

        <div
          style={{
            marginTop: 76,
            padding: "34px 54px",
            borderRadius: 22,
            background: COLORS.card,
            border: `1px solid ${COLORS.cardBorder}`,
            fontSize: 46,
            color: COLORS.dim,
            fontWeight: 700,
            textAlign: "center",
            lineHeight: 1.5,
            opacity: interpolate(frame, [18, 36], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          哪一条你最关注？
          <br />
          <span style={{ color: COLORS.warn }}>评论区聊聊，明天见</span>
        </div>

        <div
          style={{
            marginTop: 60,
            fontSize: 34,
            color: COLORS.faint,
            fontWeight: 600,
            letterSpacing: 3,
          }}
        >
          {v.date} · 每日 AI 头条
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
