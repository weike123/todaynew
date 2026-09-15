import React, { useState } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  staticFile,
  Easing,
} from "remotion";
import { Backdrop, COLORS, FONT, ProgressBar, sectionColor } from "../components/theme";

const CONTENT_W = 904;    // 1080 - 88*2 页面内边距
const IMG_BOX_MAX_H = 430; // 配图区最大高度（短图动态收紧，长图滚动上限）

/**
 * 从标题提取海报关键词：优先最长的英文/数字词组（如 HydraFusion、Lean 4），
 * 没有则取标题前 8 个字。
 */
const pickKeyword = (title: string): string => {
  const latin = title.match(/[A-Za-z][A-Za-z0-9.+#\-]*(?: [A-Za-z0-9.+#\-]+)*/g);
  if (latin && latin.length) {
    return latin.sort((a, b) => b.length - a.length)[0].trim();
  }
  return title.replace(/[，。：:、！？!?].*$/, "").slice(0, 8);
};

/**
 * 关键词海报卡（无配图时的兜底，替代生硬的「暂无配图」）：
 * 分类色光晕背景 + 装饰圆环/点阵 + 超大关键词 + 分类标签，
 * 观感是有意设计的版式海报，而不是缺图占位。
 */
export const KeywordPoster: React.FC<{
  title: string;
  color: string;
  section?: string;
}> = ({ title, color, section }) => {
  const frame = useCurrentFrame();
  const keyword = pickKeyword(title || "");
  const kwLen = Array.from(keyword).length || 1;
  const kwSize = Math.max(56, Math.min(130, Math.floor(760 / kwLen)));
  const glow = interpolate(frame, [0, 30], [0.25, 0.5], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        marginTop: 36,
        height: IMG_BOX_MAX_H,
        borderRadius: 22,
        overflow: "hidden",
        border: `1px solid ${COLORS.cardBorder}`,
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: `radial-gradient(120% 140% at 20% 0%, ${color}30 0%, ${COLORS.bg2} 55%, #0a0f1e 100%)`,
      }}
    >
      {/* 装饰：大圆环 + 点阵 */}
      <div
        style={{
          position: "absolute",
          right: -110,
          top: -130,
          width: 340,
          height: 340,
          borderRadius: 999,
          border: `2px solid ${color}44`,
        }}
      />
      <div
        style={{
          position: "absolute",
          right: -60,
          top: -80,
          width: 340,
          height: 340,
          borderRadius: 999,
          border: `1px solid ${color}2a`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: -90,
          bottom: -140,
          width: 300,
          height: 300,
          borderRadius: 999,
          background: `radial-gradient(circle, ${color}${Math.round(glow * 100)
            .toString(16)
            .padStart(2, "0")} 0%, transparent 70%)`,
          filter: "blur(6px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `radial-gradient(${color}26 1.5px, transparent 1.5px)`,
          backgroundSize: "34px 34px",
          maskImage:
            "linear-gradient(115deg, rgba(0,0,0,0.9) 0%, transparent 45%)",
          WebkitMaskImage:
            "linear-gradient(115deg, rgba(0,0,0,0.9) 0%, transparent 45%)",
        }}
      />

      {/* 分类标签（左上） */}
      {section ? (
        <div
          style={{
            position: "absolute",
            left: 34,
            top: 30,
            padding: "8px 22px",
            borderRadius: 999,
            background: `${color}1f`,
            border: `1px solid ${color}88`,
            color,
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: 2,
          }}
        >
          {section}
        </div>
      ) : null}

      {/* 中央超大关键词（渐变文字） */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
          transform: "translateY(10px)",
        }}
      >
        <div
          style={{
            fontSize: kwSize,
            fontWeight: 900,
            lineHeight: 1.1,
            letterSpacing: 2,
            background: `linear-gradient(135deg, #ffffff 20%, ${color} 90%)`,
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
            textShadow: "none",
            maxWidth: 820,
            textAlign: "center",
            wordBreak: "break-word",
          }}
        >
          {keyword}
        </div>
        <div
          style={{
            width: 120,
            height: 5,
            borderRadius: 999,
            background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
          }}
        />
      </div>
    </div>
  );
};

/**
 * 配图查看器（动态高度版）：
 * - 已知图片尺寸：容器高度 = min(等比显示高度, IMG_BOX_MAX_H)，短图收紧不留空边
 * - 显示高度 > 上限（长图）：固定为上限高度，场景内先停留 → 匀速竖向滚动到底 → 尾部停留
 * - 尺寸未知 / 加载失败：回落 MAX 高度容器，或关键词海报卡兜底
 */
export const ImageViewer: React.FC<{
  src?: string;
  dims?: [number, number];
  color: string;
  title: string;
  section?: string;
  durationInFrames: number;
}> = ({ src, dims, color, title, section, durationInFrames }) => {
  const frame = useCurrentFrame();
  const [imgErr, setImgErr] = useState(false);

  const dispH = dims && dims[0] > 0 ? (CONTENT_W * dims[1]) / dims[0] : null;
  const boxH = dispH ? Math.max(180, Math.min(dispH, IMG_BOX_MAX_H)) : IMG_BOX_MAX_H;
  const scrollDist = dispH && dispH > IMG_BOX_MAX_H ? dispH - IMG_BOX_MAX_H : 0;
  // 滚动节奏：前 12 帧停留 → 匀速滚动 → 最后 12 帧停留
  const yOffset = scrollDist
    ? interpolate(frame, [12, Math.max(13, durationInFrames - 12)], [0, scrollDist], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.inOut(Easing.quad),
      })
    : 0;
  // Ken Burns 缓动：非长图时配图缓慢放大 1.0→1.06，避免画面完全静止
  const kenBurns = scrollDist
    ? 1.0
    : interpolate(frame, [0, durationInFrames], [1.0, 1.06], {
        extrapolateRight: "clamp",
        easing: Easing.inOut(Easing.quad),
      });

  const outer: React.CSSProperties = {
    marginTop: 36,
    height: boxH,
    borderRadius: 22,
    overflow: "hidden",
    border: `1px solid ${COLORS.cardBorder}`,
    background: `linear-gradient(135deg, ${color}33, ${COLORS.bg2})`,
    opacity: interpolate(frame, [6, 22], [0, 1], { extrapolateRight: "clamp" }),
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  if (!src || imgErr) {
    return <KeywordPoster title={title} color={color} section={section} />;
  }

  return (
    <div style={outer}>
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          justifyContent: "center",
          alignItems: scrollDist ? "flex-start" : "center",
          overflow: "hidden",
        }}
      >
        <img
          src={staticFile(src)}
          alt=""
          onError={() => setImgErr(true)}
          style={{
            width: "100%",
            height: "auto",
            display: "block",
            transform: `translateY(${-yOffset}px) scale(${kenBurns})`,
            transformOrigin: "center center",
          }}
        />
      </div>
    </div>
  );
};

/** 单条新闻卡片：序号 / 分类 / 标题 / 抓取配图 / 详细要点 / 来源 */
export const NewsItem: React.FC<{
  v: any;
  progress: number;
  total: number;
}> = ({ v, progress, total }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const color = sectionColor(v.section);
  const enter = spring({ frame, fps: 30, config: { damping: 200 } });

  // 入场后缓慢放大，避免画面完全静止
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.03], {
    extrapolateRight: "clamp",
  });

  const title: string = v.title || "";
  const titleSize = title.length > 34 ? 52 : title.length > 22 ? 60 : 70;
  const tags: string[] = (v.tags || []).slice(0, 3);
  const bullets: string[] = (v.bullets || []).slice(0, 3);
  const images: string[] = v.images || [];

  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <Backdrop hue={color} />
      <ProgressBar progress={progress} color={color} />

      <AbsoluteFill
        style={{
          padding: "96px 88px 0",
          transform: `scale(${zoom})`,
        }}
      >
        {/* 顶部：分类 + 序号 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 18,
            opacity: interpolate(frame, [0, 14], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          <div
            style={{
              padding: "10px 26px",
              borderRadius: 999,
              background: `${color}22`,
              border: `1px solid ${color}`,
              color,
              fontSize: 34,
              fontWeight: 800,
            }}
          >
            {v.section}
          </div>
          <div
            style={{
              fontSize: 34,
              fontWeight: 800,
              color: COLORS.faint,
              letterSpacing: 2,
            }}
          >
            {String(v.index).padStart(2, "0")} / {String(total).padStart(2, "0")}
          </div>
        </div>

        {/* 标题 */}
        <div
          style={{
            marginTop: 56,
            fontSize: titleSize,
            fontWeight: 900,
            lineHeight: 1.3,
            color: "#ffffff",
            letterSpacing: 1,
            opacity: enter,
            transform: `translateY(${(1 - enter) * 40}px)`,
            textShadow: "0 6px 30px rgba(0,0,0,0.55)",
          }}
        >
          {title}
        </div>

        {/* 抓取配图：完整展示（contain），长图在场景内匀速竖向滚动；无图时用关键词海报卡兜底 */}
        <ImageViewer
          src={images[0]}
          dims={(v.image_sizes || [])[0]}
          color={color}
          title={title}
          section={v.section}
          durationInFrames={durationInFrames}
        />

        {/* 详细要点（来自原文抓取） */}
        {bullets.length > 0 && (
          <div
            style={{
              marginTop: 32,
              display: "flex",
              flexDirection: "column",
              gap: 14,
              opacity: interpolate(frame, [12, 28], [0, 1], {
                extrapolateRight: "clamp",
              }),
            }}
          >
            {bullets.map((b: string, i: number) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 18,
                  fontSize: 30,
                  lineHeight: 1.4,
                  color: "#eef2ff",
                  fontWeight: 500,
                }}
              >
                <span
                  style={{
                    flex: "0 0 auto",
                    marginTop: 11,
                    width: 13,
                    height: 13,
                    borderRadius: 999,
                    background: color,
                    boxShadow: `0 0 14px ${color}aa`,
                  }}
                />
                <span style={{ flex: 1 }}>{b}</span>
              </div>
            ))}
          </div>
        )}

        {/* 来源 */}
        {v.source ? (
          <div
            style={{
              marginTop: 22,
              paddingTop: 18,
              borderTop: `1px solid ${COLORS.cardBorder}`,
              fontSize: 26,
              color: COLORS.faint,
              fontWeight: 500,
              opacity: interpolate(frame, [16, 30], [0, 1], {
                extrapolateRight: "clamp",
              }),
            }}
          >
            来源：{v.source}
          </div>
        ) : null}
      </AbsoluteFill>

      {/* 左侧分类色条 */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 10,
          background: `linear-gradient(180deg, ${color}, transparent)`,
          opacity: 0.9,
        }}
      />
    </AbsoluteFill>
  );
};
