import type { PlayerFactory, PlayerLike } from "../features/sermon/Player";

/** A player the test drives: ``moveTo`` moves it to a time, as playing the real one would. */
export interface FakePlayer extends PlayerLike {
  kind: "youtube" | "video";
  /** What the factory got: the YouTube id and start, or the ``<video>`` and its offset. */
  args: unknown[];
  seeks: number[];
  playing: boolean;
  destroyed: boolean;
  /** Moves the player to ``liveSeconds`` and tells the listeners. */
  moveTo(liveSeconds: number): void;
}

export interface FakePlayers extends PlayerFactory {
  created: FakePlayer[];
  /** The player made last, the one on the screen. */
  current(): FakePlayer;
}

/** Doubles of the ``PlayerLike`` port: no YouTube script, iframe or media is loaded. */
export function fakePlayers(): FakePlayers {
  const created: FakePlayer[] = [];
  function make(kind: FakePlayer["kind"], args: unknown[], start: number): FakePlayer {
    let time = start;
    const listeners = new Set<(liveSeconds: number) => void>();
    const player: FakePlayer = {
      kind,
      args,
      seeks: [],
      playing: false,
      destroyed: false,
      time: () => time,
      seek(liveSeconds) {
        player.seeks.push(liveSeconds);
        time = liveSeconds;
      },
      play() {
        player.playing = true;
      },
      pause() {
        player.playing = false;
      },
      onTime(listener) {
        listeners.add(listener);
        return () => listeners.delete(listener);
      },
      destroy() {
        player.destroyed = true;
      },
      moveTo(liveSeconds) {
        time = liveSeconds;
        listeners.forEach((listener) => listener(liveSeconds));
      },
    };
    created.push(player);
    return player;
  }
  return {
    created,
    current: () => created[created.length - 1],
    youtube: (_host, videoId, startSeconds) => make("youtube", [videoId, startSeconds], startSeconds),
    video: (element, offsetSeconds) => make("video", [element, offsetSeconds], offsetSeconds),
  };
}
