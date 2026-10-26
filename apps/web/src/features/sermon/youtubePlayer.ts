import type { PlayerLike } from "./Player";

// The live plays from YouTube's own embed, with the privacy-enhanced host (ADR-0023).
const IFRAME_API_URL = "https://www.youtube.com/iframe_api";
const EMBED_HOST = "https://www.youtube-nocookie.com";
// The IFrame API has no time event; the position is read this often.
const POLL_MS = 250;

/** The part of the YouTube IFrame API this adapter uses:
 * https://developers.google.com/youtube/iframe_api_reference */
interface YouTubePlayer {
  getCurrentTime(): number;
  seekTo(seconds: number, allowSeekAhead: boolean): void;
  playVideo(): void;
  pauseVideo(): void;
  destroy(): void;
}

interface YouTubeApi {
  Player: new (
    element: HTMLElement,
    options: {
      host: string;
      videoId: string;
      width: string;
      height: string;
      playerVars: Record<string, number>;
      events: { onReady: () => void };
    },
  ) => YouTubePlayer;
}

declare global {
  interface Window {
    YT?: YouTubeApi;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let loading: Promise<YouTubeApi> | undefined;

/** Loads the IFrame API once, the first time a sermon's preview needs the live. */
function loadApi(): Promise<YouTubeApi> {
  loading ??= new Promise((resolve) => {
    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previous?.();
      if (window.YT) {
        resolve(window.YT);
      }
    };
    const script = document.createElement("script");
    script.src = IFRAME_API_URL;
    document.head.append(script);
  });
  return loading;
}

/** The live on YouTube inside ``host``, starting at ``startSeconds``. */
export function youtubePlayer(host: HTMLElement, videoId: string, startSeconds: number): PlayerLike {
  let time = startSeconds;
  let player: YouTubePlayer | undefined;
  let destroyed = false;
  const listeners = new Set<(liveSeconds: number) => void>();
  // The API replaces this element with its iframe; React keeps owning ``host``.
  const mount = document.createElement("div");
  host.append(mount);

  const timer = setInterval(() => {
    const now = player?.getCurrentTime();
    if (now !== undefined && now !== time) {
      time = now;
      listeners.forEach((listener) => listener(now));
    }
  }, POLL_MS);

  loadApi().then((api) => {
    if (destroyed) {
      return;
    }
    const created = new api.Player(mount, {
      host: EMBED_HOST,
      videoId,
      width: "100%",
      height: "100%",
      playerVars: { start: Math.floor(time), controls: 0, rel: 0, playsinline: 1, disablekb: 1 },
      events: {
        onReady: () => {
          player = created;
          player.seekTo(time, true);
        },
      },
    });
  });

  return {
    time: () => time,
    seek(liveSeconds) {
      time = liveSeconds;
      player?.seekTo(liveSeconds, true);
    },
    play() {
      player?.playVideo();
    },
    pause() {
      player?.pauseVideo();
    },
    onTime(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    destroy() {
      destroyed = true;
      clearInterval(timer);
      player?.destroy();
      mount.remove();
    },
  };
}
