import { useState } from "react";

import { putCutSegments, type ApiError } from "../../api/client";
import type { Cut } from "../../api/types";
import { useMe } from "../../app/Identity";
import { toggleSentence } from "./sentenceChoice";
import type { SentenceChoice } from "./TextTab";

/** The administrator's choice of the sentences the cut plays, saved with
 * ``PUT /api/cuts/{id}/segments``; ``onSaved`` takes the cut the API answers and resolves
 * once the page shows it. Nothing for anyone else. */
export function useSentenceChoice(
  cut: Cut,
  onSaved: (cut: Cut) => Promise<void>,
  processing: boolean,
): SentenceChoice | undefined {
  const { role } = useMe();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  async function onToggle(sentenceId: number) {
    const ranges = cut.segments.map(({ from_word, to_word }) => ({ from_word, to_word }));
    const toggled = toggleSentence(ranges, cut.range_sentences, sentenceId);
    if ("error" in toggled) {
      setError(toggled.error);
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      await onSaved(await putCutSegments(cut.id, toggled.segments));
    } catch (refused) {
      setError((refused as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  if (role !== "admin") {
    return undefined;
  }
  return { onToggle, disabled: saving || processing, error };
}
