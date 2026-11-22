// Encode rates derived from the reel length so the MP4 stays under the 10 MB Paperclip attachment cap.
export const BUDGET_BYTES = 8.5e6;
export const AUDIO_BPS = 96000;
const MIN_VIDEO_BPS = 400000;
const MAX_VIDEO_BPS = 8000000;

export function encodeRates(seconds) {
  const total = (BUDGET_BYTES * 8) / Math.max(seconds, 1);
  const video = Math.min(MAX_VIDEO_BPS, Math.max(MIN_VIDEO_BPS, Math.floor((total - AUDIO_BPS) / 1000) * 1000));
  return { videoBitrate: `${video / 1000}k`, audioBitrate: `${AUDIO_BPS / 1000}k` };
}
