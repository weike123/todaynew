import { Composition } from "remotion";
import { MainVideo } from "./NewsVideo";
import { TitleCard } from "./scenes/TitleCard";
import { CoverImage } from "./scenes/CoverImage";
import timeline from "../../work/timeline.json";
import {
  durationFramesForMaster,
  VIDEO_FPS,
  VIDEO_HEIGHT,
  VIDEO_WIDTH,
} from "./videoConfig";

const masterDur = (timeline as any).master_duration as number;
const DURATION_FRAMES = durationFramesForMaster(masterDur);

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="MainVideo"
        component={MainVideo as any}
        durationInFrames={DURATION_FRAMES}
        fps={VIDEO_FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
      />
      <Composition
        id="TitleCard"
        component={TitleCard}
        durationInFrames={1}
        fps={VIDEO_FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
      />
      {/* 多比例封面：小红书/抖音竖版 3:4、B站横版 4:3、公众号头图 16:9 */}
      <Composition
        id="Cover3x4"
        component={() => <CoverImage width={1080} height={1440} />}
        durationInFrames={1}
        fps={VIDEO_FPS}
        width={1080}
        height={1440}
      />
      <Composition
        id="Cover4x3"
        component={() => <CoverImage width={1440} height={1080} />}
        durationInFrames={1}
        fps={VIDEO_FPS}
        width={1440}
        height={1080}
      />
      <Composition
        id="Cover16x9"
        component={() => <CoverImage width={1920} height={1080} />}
        durationInFrames={1}
        fps={VIDEO_FPS}
        width={1920}
        height={1080}
      />
    </>
  );
};
