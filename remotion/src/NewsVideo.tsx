import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import timeline from "../../work/timeline.json";
import { KTVSubtitle } from "./components/Subtitle";
import { NewsHook } from "./scenes/NewsHook";
import { NewsItem } from "./scenes/NewsItem";
import { NewsOutro } from "./scenes/NewsOutro";
import { TitleCard } from "./scenes/TitleCard";
import { COLORS } from "./components/theme";
import { TAIL_BUFFER_FRAMES, TITLE_CARD_FRAMES, VIDEO_FPS } from "./videoConfig";

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

      {/* 场景序列：用「下一场景起点」收尾，保证无缝衔接不留黑帧。
          末场景必须覆盖整个尾部缓冲（master_duration + TAIL_BUFFER），
          否则缓冲区间是纯背景空尾（2026-10-14 审计 E11，三期成片均有 1.2s+ 空尾）。 */}
      {scenes.map((s, i) => {
          const startFrame = Math.round(starts[i] * VIDEO_FPS);
        const endSec =
          i + 1 < starts.length
            ? starts[i + 1]
            : masterDur + TAIL_BUFFER_FRAMES / VIDEO_FPS;
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

      {/* 配音轨：master.wav 已内置 0.1s 前置静音（TITLE_PAD），必须从第 0 帧起播。
          若再套 Sequence 延迟到第 3 帧，静音会被双计，字幕相对配音整体早 0.1s
          （2026-10-14 审计 E10）。timeline 的 clause.start 含 TITLE_PAD，
          与「wav 位置 = 视频时间」的映射在音频 0 帧起播时严格对齐。 */}
      <Audio src={audioSrc} />
    </AbsoluteFill>
  );
};
