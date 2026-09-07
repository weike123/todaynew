import timeline from "../../work/timeline.json";

/**
 * 标题卡数据源。timeline.json 里已内嵌 narration，
 * 这样 TitleCard 既能单独渲染（still），也能在主视频里复用同一份数据，
 * 不会出现「标题卡文案和正文不是同一天」的情况。
 */
export function useTitleData() {
  const tl = timeline as any;
  const n = tl.narration || {};
  return {
    date: (n.date || tl.date || "") as string,
    weekday: (n.weekday || "") as string,
    total: (n.total || 0) as number,
    sections: (n.sections || []) as string[],
    title: (n.title || "每日 AI 头条") as string,
    subtitle: (n.subtitle || "") as string,
  };
}
