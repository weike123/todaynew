import { Composition } from "remotion";
import { MainVideo } from "./NewsVideo";
import { TitleCard } from "./scenes/TitleCard";
import { CoverImage } from "./scenes/CoverImage";
import timeline from "../../work/timeline.json";

const FPS = 30;
const W = 1080;
const H = 1920;
const masterDur = (timeline as any).master_duration as number;
// 尾部留 1.5s 收尾，避免最后一句字幕被硬切
const DURATION_FRAMES = Math.ceil((masterDur + 1.5) * FPS);

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="MainVideo"
        component={MainVideo as any}
        durationInFrames={DURATION_FRAMES}
        fps={FPS}
        width={W}
        height={H}
      />
      <Composition
        id="TitleCard"
        component={TitleCard}
        durationInFrames={1}
        fps={FPS}
        width={W}
        height={H}
      />
      {/* 多比例封面：小红书/抖音竖版 3:4、B站横版 4:3、公众号头图 16:9 */}
      <Composition
        id="Cover3x4"
        component={() => <CoverImage width={1080} height={1440} />}
        durationInFrames={1}
        fps={FPS}
        width={1080}
        height={1440}
      />
      <Composition
        id="Cover4x3"
        component={() => <CoverImage width={1440} height={1080} />}
        durationInFrames={1}
        fps={FPS}
        width={1440}
        height={1080}
      />
      <Composition
        id="Cover16x9"
        component={() => <CoverImage width={1920} height={1080} />}
        durationInFrames={1}
        fps={FPS}
        width={1920}
        height={1080}
      />
    </>
  );
};
