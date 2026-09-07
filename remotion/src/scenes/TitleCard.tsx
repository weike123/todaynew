import React from "react";
import { AbsoluteFill } from "remotion";
import { Backdrop, COLORS, FONT } from "../components/theme";
import { useTitleData } from "../useTitleData";

/**
 * 首帧静音标题卡（Composition: TitleCard）
 * 供抖音/视频号抽取封面标题；主视频开头 3 帧也复用它。
 */
export const TitleCard: React.FC = () => {
  const d = useTitleData();
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <Backdrop />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: 90,
        }}
      >
        <div
          style={{
            fontSize: 40,
            letterSpacing: 10,
            color: COLORS.accent2,
            fontWeight: 700,
            marginBottom: 34,
          }}
        >
          DAILY AI DIGEST
        </div>

        <div
          style={{
            fontSize: 132,
            fontWeight: 900,
            color: "#ffffff",
            letterSpacing: 6,
            lineHeight: 1.15,
            textAlign: "center",
            textShadow: "0 8px 40px rgba(79,140,255,0.45)",
          }}
        >
          每日 AI 头条
        </div>

        <div
          style={{
            marginTop: 30,
            height: 6,
            width: 220,
            borderRadius: 3,
            background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.accent2})`,
          }}
        />

        <div
          style={{
            marginTop: 40,
            fontSize: 52,
            color: COLORS.dim,
            fontWeight: 600,
            textAlign: "center",
          }}
        >
          {d.date} {d.weekday}
        </div>

        <div
          style={{
            marginTop: 26,
            display: "flex",
            gap: 18,
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {(d.sections.length ? d.sections : ["全球大模型", "AI Coding", "开源项目"]).map(
            (s: string) => (
              <div
                key={s}
                style={{
                  padding: "14px 30px",
                  borderRadius: 999,
                  background: COLORS.card,
                  border: `1px solid ${COLORS.cardBorder}`,
                  fontSize: 36,
                  color: COLORS.dim,
                  fontWeight: 600,
                }}
              >
                {s}
              </div>
            )
          )}
        </div>

        <div
          style={{
            position: "absolute",
            bottom: 190,
            fontSize: 44,
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
