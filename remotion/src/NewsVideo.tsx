import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import timeline from "../../work/timeline.json";
import { KTVSubtitle } from "./components/Subtitle";
import { NewsHook } from "./scenes/NewsHook";
import { NewsItem } from "./scenes/NewsItem";
import { NewsOutro } from "./scenes/NewsOutro";
import { TitleCard } from "./scenes/TitleCard";
import { COLORS } from "./components/theme";
import { TITLE_CARD_FRAMES, VIDEO_FPS } from "./videoConfig";

const tl = timeline as any;
const narr = tl.narration || { scenes: [], total: 0 };
const scenes: any[] = (Array.isArray(tl.scenes) ? tl.scenes : []).filter(
  (s: any) => Array.isArray(s?.clauses) && s.clauses.length > 0,
);
const starts = scenes.map((s) => Number(s.clauses[0]?.start || 0));
const masterDur = tl.master_duration as number;

/** 场景路由：visual.type -> 组件 */
const SceneRouter: React.FC<{ scene: any; index: number }> = ({ scene, index }) => {
  const v = scene.visual || {};
  const progress = masterDur > 0 ? starts[index] / masterDur : 0;
  switch (v.type) {
    case "news_hook":
      return <NewsHook v={v} />;
    case "news_item":
      return <NewsItem v={v} progress={progress} total={narr.total} />;
    case "news_outro":
      return <NewsOutro v={v} />;
    default:
      return <AbsoluteFill style={{ background: COLORS.bg0 }} />;
  }
};

export const MainVideo: React.FC = () => {
  const audioSrc = staticFile("audio/master.wav");

  return (
    <AbsoluteFill style={{ background: COLORS.bg0 }}>
      {/* 首帧静音标题卡（供平台抽取封面） */}
      <Sequence from={0} durationInFrames={TITLE_CARD_FRAMES}>
        <TitleCard />
      </Sequence>

      {/* 场景序列：用「下一场景起点」收尾，保证无缝衔接不留黑帧 */}
      {scenes.map((s, i) => {
          const startFrame = Math.round(starts[i] * VIDEO_FPS);
        const endSec =
          i + 1 < starts.length
            ? starts[i + 1]
            : s.clauses[s.clauses.length - 1].end;
          const durationFrames = Math.max(1, Math.round(endSec * VIDEO_FPS) - startFrame);
        const meta = (narr.scenes || []).find((x: any) => x.id === s.id) || {};
        return (
          <Sequence key={s.id} from={startFrame} durationInFrames={durationFrames}>
            <SceneRouter scene={meta} index={i} />
          </Sequence>
        );
      })}

      {/* 全程 KTV 字幕层（置于场景之上） */}
      <KTVSubtitle timeline={tl} />

      {/* 配音轨：标题卡 0.1s 后起播 */}
      <Sequence from={TITLE_CARD_FRAMES}>
        <Audio src={audioSrc} />
      </Sequence>
    </AbsoluteFill>
  );
};
