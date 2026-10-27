/** Words ``from_word`` to ``to_word`` of the sermon, by word ID, as ``cut segments`` takes
 * them (docs/cli.md §8.10). */
export interface WordRange {
  from_word: number;
  to_word: number;
}

/** A sentence of the cut's range, as ``range_sentences`` gives it (docs/cli.md §8.2). */
export interface SentenceBounds {
  id: number;
  first_word: number;
  last_word: number;
  included: "all" | "part" | "none";
}

export type Toggled = { segments: WordRange[] } | { error: string };

/** The segments once the sentence ``id`` is left out of the cut, when the cut plays all of
 * it, or played whole otherwise. Word IDs grow in sermon order, as the transcript stores
 * the words. */
export function toggleSentence(
  segments: WordRange[],
  sentences: SentenceBounds[],
  id: number,
): Toggled {
  const index = sentences.findIndex((sentence) => sentence.id === id);
  const rest = withoutSentence(segments, sentences, index);
  if (sentences[index].included !== "all") {
    return { segments: withSentence(rest, sentences, index) };
  }
  if (rest.length === 0) {
    return {
      error: "O corte precisa de ao menos uma frase; marque outra antes de tirar esta.",
    };
  }
  return { segments: rest };
}

/** ``segments``, which play none of the sentence at ``index``, with all of it: joined to the
 * segment that ends just before it and to the one that starts just after it. */
function withSentence(
  segments: WordRange[],
  sentences: SentenceBounds[],
  index: number,
): WordRange[] {
  const { first_word, last_word } = sentences[index];
  const before = segments.findIndex(
    (segment) => segment.to_word === sentences[index - 1]?.last_word,
  );
  const after = segments.findIndex(
    (segment) => segment.from_word === sentences[index + 1]?.first_word,
  );
  if (before < 0 && after < 0) {
    const at = insertionPoint(segments, first_word);
    return [
      ...segments.slice(0, at),
      { from_word: first_word, to_word: last_word },
      ...segments.slice(at),
    ];
  }
  const joined = {
    from_word: before < 0 ? first_word : segments[before].from_word,
    to_word: after < 0 ? last_word : segments[after].to_word,
  };
  const at = before < 0 ? after : before;
  return segments.flatMap((segment, position) => {
    if (position === at) {
      return [joined];
    }
    return position === before || position === after ? [] : [segment];
  });
}

/** ``segments`` without the words of the sentence at ``index``, a segment around it split
 * in two; the sentences tile the range, so the words next to it are their neighbours'. */
function withoutSentence(
  segments: WordRange[],
  sentences: SentenceBounds[],
  index: number,
): WordRange[] {
  const { first_word, last_word } = sentences[index];
  return segments.flatMap((segment) => {
    if (segment.to_word < first_word || last_word < segment.from_word) {
      return [segment];
    }
    const pieces: WordRange[] = [];
    if (segment.from_word < first_word) {
      pieces.push({
        from_word: segment.from_word,
        to_word: sentences[index - 1].last_word,
      });
    }
    if (last_word < segment.to_word) {
      pieces.push({
        from_word: sentences[index + 1].first_word,
        to_word: segment.to_word,
      });
    }
    return pieces;
  });
}

/** Where a segment starting at ``first_word`` goes: right after the segment that plays the
 * latest word before it, or first when no segment plays an earlier word. */
function insertionPoint(segments: WordRange[], first_word: number): number {
  let at = 0;
  let latest = -Infinity;
  segments.forEach((segment, position) => {
    if (segment.to_word < first_word && segment.to_word > latest) {
      latest = segment.to_word;
      at = position + 1;
    }
  });
  return at;
}
