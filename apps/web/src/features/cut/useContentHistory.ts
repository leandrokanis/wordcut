import { useEffect, useRef, useState } from "react";

import { putCutSegments, type ApiError } from "../../api/client";
import type { Cut } from "../../api/types";
import type { WordRange } from "./sentenceChoice";

/** Saves a change of what the cut plays; resolves to why the API refused it, if it did. */
type Change = () => Promise<string | undefined>;

/** What the session does to the cut's segments. */
export interface ContentHistory {
  /** Saves ``segments`` as what the cut plays. */
  apply: (segments: WordRange[]) => Promise<string | undefined>;
  /** Saves the segments before the last change; undefined when there is none. */
  undo?: Change;
  /** Saves again the segments of the last change undone; undefined when there is none. */
  redo?: Change;
  /** A change is being saved. */
  saving: boolean;
}

interface Stacks {
  undo: WordRange[][];
  redo: WordRange[][];
}

/** The changes of the cut's segments in this session, saved with
 * ``PUT /api/cuts/{id}/segments``; ``onSaved`` takes the cut the API answers and resolves
 * once the page shows it. The screen only ever shows what the API answered and the stacks
 * move only once it did, so a refused change leaves both as they were. */
export function useContentHistory(cut: Cut, onSaved: (cut: Cut) => Promise<void>): ContentHistory {
  const [saving, setSaving] = useState(false);
  const [stacks, setStacks] = useState<Stacks>({ undo: [], redo: [] });
  const current = cut.segments.map(({ from_word, to_word }) => ({ from_word, to_word }));

  async function save(segments: WordRange[], then: Stacks): Promise<string | undefined> {
    setSaving(true);
    try {
      await onSaved(await putCutSegments(cut.id, segments));
      setStacks(then);
      return undefined;
    } catch (refused) {
      return (refused as ApiError).message;
    } finally {
      setSaving(false);
    }
  }

  const { undo, redo } = stacks;
  return {
    apply: (segments) => save(segments, { undo: [...undo, current], redo: [] }),
    undo: undo.length
      ? () => save(undo[undo.length - 1], { undo: undo.slice(0, -1), redo: [...redo, current] })
      : undefined,
    redo: redo.length
      ? () => save(redo[redo.length - 1], { undo: [...undo, current], redo: redo.slice(0, -1) })
      : undefined,
    saving,
  };
}

/** Ctrl+Z (Cmd+Z) runs ``onUndo`` and Ctrl+Shift+Z runs ``onRedo``, anywhere on the page but
 * in a text field, whose own undo the browser keeps (docs/prototype/wordcut.html
 * ``keydown``). An undefined handler leaves its keys alone. */
export function useUndoShortcuts(onUndo?: () => void, onRedo?: () => void) {
  const handlers = useRef({ onUndo, onRedo });
  handlers.current = { onUndo, onRedo };

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "z") {
        return;
      }
      if (inTextField(event.target)) {
        return;
      }
      const run = event.shiftKey ? handlers.current.onRedo : handlers.current.onUndo;
      if (run) {
        event.preventDefault();
        run();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);
}

/** A field that takes typing. A sentence's box is not one, so Ctrl+Z right after ticking it
 * undoes the choice. */
function inTextField(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) {
    return false;
  }
  if (target.closest("textarea, select, [contenteditable='true']")) {
    return true;
  }
  return target instanceof HTMLInputElement && !["checkbox", "radio"].includes(target.type);
}
