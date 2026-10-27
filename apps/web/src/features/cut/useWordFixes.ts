import { useRef, useState } from "react";

import { fixWord, type ApiError } from "../../api/client";
import type { CutWord } from "../../api/types";

export interface WordFixes {
  /** The cut's words with their spelling fixes as the API last answered them. */
  words: CutWord[];
  /** Saves ``text`` as the word's spelling; the original text removes the fix. Answers the
   * API's refusal, or nothing once saved. */
  fix(wordId: number, text: string): Promise<ApiError | undefined>;
  /** A fix is being saved. */
  saving: boolean;
}

/** The spelling fixes of the cut's words, saved with ``PUT /api/cuts/{id}/words/{word_id}``;
 * new ``initial`` words, of the cut once it plays something else, replace them. */
export function useWordFixes(cutId: number, initial: CutWord[], onSaved: () => void): WordFixes {
  const [words, setWords] = useState(initial);
  const [shown, setShown] = useState(initial);
  if (shown !== initial) {
    setShown(initial);
    setWords(initial);
  }
  const [inFlight, setInFlight] = useState(0);
  const tellSaved = useRef(onSaved);
  tellSaved.current = onSaved;

  async function fix(wordId: number, text: string): Promise<ApiError | undefined> {
    setInFlight((count) => count + 1);
    try {
      const { corrected } = await fixWord(cutId, wordId, text);
      setWords((current) =>
        current.map((word) => (word.word_id === wordId ? { ...word, corrected } : word)),
      );
      tellSaved.current();
      return undefined;
    } catch (error) {
      return error as ApiError;
    } finally {
      setInFlight((count) => count - 1);
    }
  }

  return { words, fix, saving: inFlight > 0 };
}
