import React from "react";
import { AbsoluteFill } from "remotion";
import { Backdrop, COLORS, FONT } from "../components/theme";
import { useTitleData } from "../useTitleData";

/**
 * 多比例封面图（Composition: Cover3x4 / Cover4x3 / Cover16x9）
 * 供小红书/抖音竖版封面、B站横版封面、公众号头图使用。
 * 字体大小根据画布宽度自适应。
 */
export const CoverImage: React.FC<{ width: number; height: number }> = ({ width, height }) => {
  const d = useTitleData();
  const scale = width / 1080; // 以 1080 宽为基准缩放

  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <Backdrop />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: 60 * scale,
        }}
      >
        <div
          style={{
            fontSize: 32 * scale,
            letterSpacing: 8 * scale,
            color: COLORS.accent2,
            fontWeight: 700,
            marginBottom: 28 * scale,
          }}
        >
          DAILY AI DIGEST
        </div>

        <div
          style={{
            fontSize: 110 * scale,
            fontWeight: 900,
            color: "#ffffff",
            letterSpacing: 5 * scale,
            lineHeight: 1.15,
            textAlign: "center",
            textShadow: `0 ${6 * scale}px ${32 * scale}px rgba(79,140,255,0.45)`,
          }}
        >
          每日 AI 头条
        </div>

        <div
          style={{
            marginTop: 24 * scale,
            height: 5 * scale,
            width: 180 * scale,
            borderRadius: 3,
            background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.accent2})`,
          }}
        />

        <div
          style={{
            marginTop: 32 * scale,
            fontSize: 44 * scale,
            color: COLORS.dim,
            fontWeight: 600,
            textAlign: "center",
          }}
        >
          {d.date} {d.weekday}
        </div>

        <div
          style={{
            marginTop: 18 * scale,
            fontSize: 38 * scale,
            fontWeight: 800,
            color: COLORS.warn,
          }}
        >
          本期 {d.total} 条精选
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
