import React from "react";
import { CodebaseCover } from "../components/CodebaseCover";
import { useTitleData } from "../useTitleData";

/** 多比例发布封面：3:4、4:3、16:9 共用同一版式。 */
export const CoverImage: React.FC<{ width: number; height: number }> = ({
  width,
  height,
}) => {
  const d = useTitleData();

  return (
    <CodebaseCover
      width={width}
      height={height}
      mainTitle={d.title || "每日 AI 头条"}
      subtitle={`${d.date} ${d.weekday} · ${d.total} 条精选`}
      tag="AI 热点速览"
      pill="AI 头条 · 1 分钟速览"
      author="翻奇兽AI"
    />
  );
};
