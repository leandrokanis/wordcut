import type { SermonShown } from "../../api/types";

/** The sermon's borders, in seconds of the live; without borders, the whole live. */
export interface Bounds {
  start: number;
  end: number;
}

export function savedBounds(sermon: SermonShown, liveDuration: number): Bounds {
  return { start: sermon.live_start ?? 0, end: sermon.live_end ?? liveDuration };
}

export function isTrimmed(sermon: SermonShown): boolean {
  return sermon.live_start != null && sermon.live_end != null;
}
