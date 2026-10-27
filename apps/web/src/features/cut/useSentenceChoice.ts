import { useState } from "react";

import type { Cut } from "../../api/types";
import { useMe } from "../../app/Identity";
import { toggleSentence } from "./sentenceChoice";
import type { SentenceChoice } from "./TextTab";
import type { ContentHistory } from "./useContentHistory";

/** The administrator's choice of the sentences the cut plays, saved through the session's
 * ``history``, so it can be undone. Nothing for anyone else. */
export function useSentenceChoice(
  cut: Cut,
  history: ContentHistory,
  processing: boolean,
): SentenceChoice | undefined {
  const { role } = useMe();
  const [error, setError] = useState<string>();

  async function onToggle(sentenceId: number) {
    const ranges = cut.segments.map(({ from_word, to_word }) => ({ from_word, to_word }));
    const toggled = toggleSentence(ranges, cut.range_sentences, sentenceId);
    if ("error" in toggled) {
      setError(toggled.error);
      return;
    }
    setError(undefined);
    setError(await history.apply(toggled.segments));
  }

  if (role !== "admin") {
    return undefined;
  }
  return { onToggle, disabled: history.saving || processing, error };
}
