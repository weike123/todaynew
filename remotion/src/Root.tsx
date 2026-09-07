import { Composition } from "remotion";
import { MainVideo } from "./NewsVideo";
import { TitleCard } from "./scenes/TitleCard";
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
    </>
  );
};
