import React from "react";
import { CodebaseCover } from "../components/CodebaseCover";
import { useTitleData } from "../useTitleData";

/**
 * 首帧静音标题卡（Composition: TitleCard）。
 * 主视频首帧和外部发布封面共用 CodebaseCover，保持视觉与交接规范一致。
 */
export const TitleCard: React.FC = () => {
  const d = useTitleData();

  return (
    <CodebaseCover
      width={1080}
      height={1920}
      mainTitle={d.title || "每日 AI 头条"}
      subtitle={`${d.date} ${d.weekday} · ${d.total} 条精选`}
      tag="AI 热点速览"
      pill="AI 头条 · 1 分钟速览"
      author="翻奇兽AI"
    />
  );
};
