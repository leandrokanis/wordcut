import { useEffect, useRef, useState } from "react";

import { trimSermon, type ApiError } from "../../api/client";
import type { SermonShown } from "../../api/types";
import type { Bounds } from "./bounds";

export type Edge = "start" | "end";

// The core refuses a sermon under a minute (service/sermons.py MIN_SERMON_SECONDS).
export const MIN_SERMON_SECONDS = 60;
// I and O pressed in a row make one change; the drag saves at once, on release.
const MARK_SAVE_DELAY_MS = 500;
const TOO_SHORT: Record<Edge, string> = {
  start: "O início precisa ficar antes do fim, com pelo menos 1 min de pregação.",
  end: "O fim precisa ficar depois do início, com pelo menos 1 min de pregação.",
};

interface ClipEdgesOptions {
  sermonId: number;
  saved: Bounds;
  liveDuration: number;
  onSaved: (sermon: SermonShown) => void;
}

export interface ClipEdges {
  /** The borders on the screen: the ones being moved, or the saved ones. */
  bounds: Bounds;
  /** Whether a border was moved and not saved yet. */
  moving: boolean;
  /** Moves an edge towards ``liveSeconds``; gives where it stopped, a minute from the other. */
  move(edge: Edge, liveSeconds: number): number;
  /** Saves the moved borders, as the dragged edge is released. */
  release(): void;
  /** Brings an edge to the cursor (I and O), saved once the presses stop. */
  mark(edge: Edge, cursor: number): void;
  /** When the API last confirmed a save; 0 before any. */
  savedAt: number;
  /** Why the last change was not saved. */
  error?: string;
}

/** The sermon's borders while the assistant moves them, saved by ``PATCH``. */
export function useClipEdges({
  sermonId,
  saved,
  liveDuration,
  onSaved,
}: ClipEdgesOptions): ClipEdges {
  const [draft, setDraft] = useState<Bounds>();
  const [savedAt, setSavedAt] = useState(0);
  const [error, setError] = useState<string>();
  // The window's pointer handlers outlive a render; they read the borders from here.
  const latest = useRef<Bounds>();
  const pendingSave = useRef<ReturnType<typeof setTimeout>>();
  const bounds = draft ?? saved;

  useEffect(() => () => clearTimeout(pendingSave.current), []);

  function show(next: Bounds | undefined) {
    latest.current = next;
    setDraft(next);
  }

  function move(edge: Edge, liveSeconds: number): number {
    const next = moved(latest.current ?? saved, edge, liveSeconds, liveDuration);
    setError(undefined);
    show(next);
    return next[edge];
  }

  function mark(edge: Edge, cursor: number) {
    const next = { ...(latest.current ?? saved), [edge]: Math.round(cursor) };
    if (next.end - next.start < MIN_SERMON_SECONDS) {
      setError(TOO_SHORT[edge]);
      return;
    }
    setError(undefined);
    show(next);
    clearTimeout(pendingSave.current);
    pendingSave.current = setTimeout(release, MARK_SAVE_DELAY_MS);
  }

  function release() {
    clearTimeout(pendingSave.current);
    const next = latest.current;
    if (!next) {
      return;
    }
    trimSermon(sermonId, next.start, next.end).then(
      (sermon) => {
        show(undefined);
        setSavedAt(Date.now());
        onSaved(sermon);
      },
      (failure: ApiError) => {
        show(undefined);
        setError(failure.message);
      },
    );
  }

  return { bounds, moving: draft !== undefined, move, release, mark, savedAt, error };
}

function moved(bounds: Bounds, edge: Edge, liveSeconds: number, liveDuration: number): Bounds {
  return edge === "start"
    ? { ...bounds, start: Math.max(0, Math.min(liveSeconds, bounds.end - MIN_SERMON_SECONDS)) }
    : {
        ...bounds,
        end: Math.min(liveDuration, Math.max(liveSeconds, bounds.start + MIN_SERMON_SECONDS)),
      };
}
