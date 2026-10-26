import { createContext } from "react";

import { videoPlayer } from "./videoPlayer";
import { youtubePlayer } from "./youtubePlayer";

/** The preview's port: every time is in seconds of the live, whatever plays it. */
export interface PlayerLike {
  time(): number;
  seek(liveSeconds: number): void;
  play(): void;
  pause(): void;
  /** Calls ``listener`` as the position changes; returns the unsubscribe. */
  onTime(listener: (liveSeconds: number) => void): () => void;
  destroy(): void;
}

/** Makes the players: the live on YouTube, or the processed video, which starts at
 * ``offsetSeconds`` of the live. */
export interface PlayerFactory {
  youtube(host: HTMLElement, videoId: string, startSeconds: number): PlayerLike;
  video(element: HTMLVideoElement, offsetSeconds: number): PlayerLike;
}

export const browserPlayers: PlayerFactory = { youtube: youtubePlayer, video: videoPlayer };

export const PlayerFactoryContext = createContext<PlayerFactory>(browserPlayers);
