/**
 * Remotion 与 todayaihot 流水线共享的时间/画布常量。
 *
 * Root、场景路由、音频起播和字幕必须使用同一套值，避免首帧、字幕、
 * 配音和最终视频时长彼此漂移。
 */
export const VIDEO_FPS = 30;
export const VIDEO_WIDTH = 1080;
export const VIDEO_HEIGHT = 1920;

/** 首帧静音标题卡，给平台抽帧留出稳定画面。 */
export const TITLE_CARD_FRAMES = 3;

/** 音频末尾保留的收尾缓冲，避免最后一个字被硬切。 */
export const TAIL_BUFFER_FRAMES = Math.round(1.5 * VIDEO_FPS);

export const durationFramesForMaster = (masterDuration: number): number =>
  Math.max(1, Math.ceil(masterDuration * VIDEO_FPS) + TAIL_BUFFER_FRAMES);
