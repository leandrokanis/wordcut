import { useEffect, useRef, useState } from "react";

import type { ApiError } from "../../api/client";
import type { Preset, PresetChange } from "../../api/types";

// Requisitos gerais de interface: a change saves by itself, once the user pauses on it; the
// same wait as useCaptionStyle (L7).
export const AUTOSAVE_MS = 400;

export interface PresetDrafts {
  /** What the user set on ``key`` of preset ``id`` and is not saved yet. */
  draft<T>(id: number, key: string): T | undefined;
  /** Why the API refused the last change of ``key`` of preset ``id``. */
  error(id: number, key: string): string | undefined;
  /** Shows ``value`` on ``key`` and saves ``change`` on preset ``id``: at once with
   * ``waitMs`` 0, otherwise ``waitMs`` after the last change of that key. Without ``change``
   * (a value the API cannot take yet, as a half-typed number), it is only shown. */
  change(id: number, key: string, value: unknown, change?: PresetChange, waitMs?: number): void;
  /** Saves every waiting change now, each on the preset it was made on. */
  flush(): Promise<void>;
}

interface Waiting {
  timer: ReturnType<typeof setTimeout>;
  save: () => Promise<void>;
}

/** The changes of the presets, saved one key at a time with ``save``; the drafts and errors are
 * kept by preset, so switching presets neither loses nor misplaces them. */
export function usePresetDrafts(
  save: (id: number, change: PresetChange) => Promise<Preset>,
): PresetDrafts {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const waiting = useRef(new Map<string, Waiting>());
  const latestSave = useRef(save);
  latestSave.current = save;

  function send(slot: string, id: number, value: unknown, change: PresetChange, revert: boolean) {
    return latestSave.current(id, change).then(
      () => setDrafts((current) => (current[slot] === value ? without(current, slot) : current)),
      (refusal: ApiError) => {
        setErrors((current) => ({ ...current, [slot]: refusal.message }));
        if (revert) {
          setDrafts((current) => (current[slot] === value ? without(current, slot) : current));
        }
      },
    );
  }

  function flush(): Promise<void> {
    const due = [...waiting.current.values()];
    waiting.current.clear();
    due.forEach((entry) => clearTimeout(entry.timer));
    return Promise.all(due.map((entry) => entry.save())).then(() => undefined);
  }

  const latestFlush = useRef(flush);
  latestFlush.current = flush;
  useEffect(() => () => void latestFlush.current(), []);

  function change(id: number, key: string, value: unknown, change?: PresetChange, waitMs = 0) {
    const slot = slotOf(id, key);
    setDrafts((current) => ({ ...current, [slot]: value }));
    setErrors((current) => without(current, slot));
    clearTimeout(waiting.current.get(slot)?.timer);
    waiting.current.delete(slot);
    if (!change) {
      return;
    }
    if (waitMs === 0) {
      // A picked option the API refuses goes back to the saved one.
      void send(slot, id, value, change, true);
      return;
    }
    const entry: Waiting = {
      save: () => {
        waiting.current.delete(slot);
        return send(slot, id, value, change, false);
      },
      timer: setTimeout(() => void entry.save(), waitMs),
    };
    waiting.current.set(slot, entry);
  }

  return {
    draft: <T>(id: number, key: string) => drafts[slotOf(id, key)] as T | undefined,
    error: (id, key) => errors[slotOf(id, key)],
    change,
    flush,
  };
}

function slotOf(id: number, key: string): string {
  return `${id}:${key}`;
}

function without<T>(record: Record<string, T>, key: string): Record<string, T> {
  return Object.fromEntries(Object.entries(record).filter(([name]) => name !== key));
}
