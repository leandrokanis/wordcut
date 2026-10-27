import { useState } from "react";

import type { Cut } from "../../api/types";
import { useMe } from "../../app/Identity";
import type { SegmentTools } from "./CutTransport";
import { moveSegment, removeSegment, splitAt } from "./segmentEdits";
import type { WordRange } from "./sentenceChoice";
import { useUndoShortcuts, type ContentHistory } from "./useContentHistory";

interface Selection {
  /** The selected segment, by its position in the order the cut plays them. */
  selected?: number;
  select: (index: number | undefined) => void;
}

/** The administrator's split, move and remove of the selected segment, at ``cursor`` in
 * seconds of the cut; nothing is available while a change is saved or the sermon processes.
 * After an action, the moved segment stays selected, the first half of a split is selected
 * and a removal, an undo or a redo clears the selection. */
export function useSegmentTools(
  cut: Cut,
  cursor: number,
  { selected, select }: Selection,
  history: ContentHistory,
  processing: boolean,
): SegmentTools {
  const { role } = useMe();
  const admin = role === "admin";
  const [error, setError] = useState<string>();
  const ready = admin && !processing && !history.saving;
  const index =
    ready && selected !== undefined && selected < cut.segments.length ? selected : undefined;

  function run(change: (() => Promise<string | undefined>) | undefined, after?: number) {
    if (!change) {
      return undefined;
    }
    return async () => {
      setError(undefined);
      const refused = await change();
      setError(refused);
      if (!refused) {
        select(after);
      }
    };
  }

  function action(next: WordRange[] | undefined, after: number | undefined) {
    return run(next && (() => history.apply(next)), after);
  }

  const past = {
    admin,
    error,
    onUndo: ready ? run(history.undo) : undefined,
    onRedo: ready ? run(history.redo) : undefined,
  };
  useUndoShortcuts(past.onUndo, past.onRedo);
  if (index === undefined) {
    return past;
  }
  return {
    ...past,
    onSplit: action(splitAt(cut.segments, cut.range_sentences, index, cursor), index),
    onMoveLeft: action(moveSegment(cut.segments, index, -1), index - 1),
    onMoveRight: action(moveSegment(cut.segments, index, 1), index + 1),
    onRemove: action(removeSegment(cut.segments, index), undefined),
  };
}
