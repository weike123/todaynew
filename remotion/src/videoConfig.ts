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

/**
 * 字幕安全区。
 *
 * 字幕块贴底 SUBTITLE_BOTTOM（避开抖音/视频号底部 UI），最多占两行大字号，
 * 因此正文内容必须止于 CONTENT_BOTTOM_LIMIT，否则第 3 条要点会被字幕压住
 * （2026-10-24 成片即出现该重叠）。两个值必须与 Subtitle.tsx / NewsItem.tsx 同源。
 */
export const SUBTITLE_BOTTOM = 360;
export const SUBTITLE_SAFE_HEIGHT = 190;
export const CONTENT_BOTTOM_LIMIT = VIDEO_HEIGHT - SUBTITLE_BOTTOM - SUBTITLE_SAFE_HEIGHT;
export const CONTENT_BOTTOM_GAP = VIDEO_HEIGHT - CONTENT_BOTTOM_LIMIT;

export const durationFramesForMaster = (masterDuration: number): number =>
  Math.max(1, Math.ceil(masterDuration * VIDEO_FPS) + TAIL_BUFFER_FRAMES);
