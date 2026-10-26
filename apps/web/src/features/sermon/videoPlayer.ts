import type { PlayerLike } from "./Player";

/** The processed video, which starts at ``offsetSeconds`` of the live. */
export function videoPlayer(element: HTMLVideoElement, offsetSeconds: number): PlayerLike {
  return {
    time: () => element.currentTime + offsetSeconds,
    seek(liveSeconds) {
      element.currentTime = Math.max(0, liveSeconds - offsetSeconds);
    },
    play() {
      // A refused play (no user gesture yet) leaves the video paused, as the button shows.
      element.play().catch(() => undefined);
    },
    pause() {
      element.pause();
    },
    onTime(listener) {
      const tell = () => listener(element.currentTime + offsetSeconds);
      element.addEventListener("timeupdate", tell);
      return () => element.removeEventListener("timeupdate", tell);
    },
    destroy() {
      element.pause();
    },
  };
}
