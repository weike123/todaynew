import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring } from "remotion";
import { Backdrop, COLORS, FONT } from "../components/theme";

/** 开场钩子：日期 + 条数 + 分类 */
export const NewsHook: React.FC<{ v: any }> = ({ v }) => {
  const frame = useCurrentFrame();
  const rise = spring({ frame, fps: 30, config: { damping: 200 } });
  const fadeIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
  });

  const chips = (v.sections || []).slice(0, 3);

  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <Backdrop />

      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          opacity: fadeIn,
        }}
      >
        <div
          style={{
            transform: `translateY(${(1 - rise) * 40}px)`,
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 38,
              letterSpacing: 8,
              color: COLORS.accent2,
              fontWeight: 700,
            }}
          >
            DAILY AI DIGEST
          </div>

          <div
            style={{
              marginTop: 28,
              fontSize: 104,
              fontWeight: 900,
              color: "#fff",
              letterSpacing: 4,
              textShadow: "0 6px 32px rgba(79,140,255,0.4)",
            }}
          >
            每日 AI 头条
          </div>

          <div
            style={{
              marginTop: 34,
              fontSize: 56,
              color: COLORS.dim,
              fontWeight: 600,
            }}
          >
            {v.date} {v.weekday}
          </div>
        </div>

        {/* 条数大数字 */}
        <div
          style={{
            marginTop: 80,
            display: "flex",
            alignItems: "baseline",
            gap: 18,
            opacity: interpolate(frame, [8, 26], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          <div
            style={{
              fontSize: 190,
              fontWeight: 900,
              color: COLORS.warn,
              lineHeight: 1,
              textShadow: "0 0 60px rgba(255,214,10,0.35)",
            }}
          >
            {v.total}
          </div>
          <div style={{ fontSize: 54, color: COLORS.dim, fontWeight: 700 }}>
            条精选
          </div>
        </div>

        {/* 分类 chips */}
        <div
          style={{
            marginTop: 54,
            display: "flex",
            gap: 20,
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          {chips.map((s: string, i: number) => (
            <div
              key={s}
              style={{
                padding: "16px 34px",
                borderRadius: 999,
                background: COLORS.card,
                border: `1px solid ${COLORS.cardBorder}`,
                fontSize: 38,
                color: "#fff",
                fontWeight: 700,
                opacity: interpolate(frame, [18 + i * 6, 34 + i * 6], [0, 1], {
                  extrapolateRight: "clamp",
                }),
                transform: `translateY(${interpolate(
                  frame,
                  [18 + i * 6, 34 + i * 6],
                  [24, 0],
                  { extrapolateRight: "clamp" }
                )}px)`,
              }}
            >
              {s}
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
