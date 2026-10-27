import { offsetOf } from "./sequence";
import type { WordRange } from "./sentenceChoice";

/** A segment of the cut, by word ID, with where it plays in sermon time. */
export interface TimedRange extends WordRange {
  start: number;
  end: number;
}

/** A sentence of the cut's range, by word ID, with where it starts in sermon time. */
export interface SentenceStart {
  first_word: number;
  last_word: number;
  start: number;
}

/** The segments once segment ``index`` is split in two at the boundary between sentences
 * nearest ``cutSeconds``, the cursor in time of the cut (docs/prototype/wordcut.html
 * ``split``); a tie goes to the earlier boundary. Undefined when the cursor is outside the
 * segment or no boundary lies inside it. */
export function splitAt(
  segments: TimedRange[],
  sentences: SentenceStart[],
  index: number,
  cutSeconds: number,
): WordRange[] | undefined {
  const segment = segments[index];
  const inside = cutSeconds - offsetOf(segments, index);
  if (inside < 0 || segment.end - segment.start < inside) {
    return undefined;
  }
  const at = segment.start + inside;
  let nearest = -1;
  sentences.forEach((sentence, position) => {
    if (sentence.first_word <= segment.from_word || segment.to_word < sentence.first_word) {
      return;
    }
    if (nearest < 0 || Math.abs(sentence.start - at) < Math.abs(sentences[nearest].start - at)) {
      nearest = position;
    }
  });
  if (nearest < 0) {
    return undefined;
  }
  return ranges(segments).flatMap((range, position) =>
    position === index
      ? [
          { from_word: range.from_word, to_word: sentences[nearest - 1].last_word },
          { from_word: sentences[nearest].first_word, to_word: range.to_word },
        ]
      : [range],
  );
}

function ranges(segments: WordRange[]): WordRange[] {
  return segments.map(({ from_word, to_word }) => ({ from_word, to_word }));
}

/** The segments once segment ``index`` swaps places with the one before it (``-1``) or after
 * it (``1``) in the order the cut plays them (docs/prototype/wordcut.html ``mvseg``). Undefined when
 * no segment is there to swap with. */
export function moveSegment(
  segments: WordRange[],
  index: number,
  direction: -1 | 1,
): WordRange[] | undefined {
  const other = index + direction;
  if (other < 0 || other >= segments.length) {
    return undefined;
  }
  const moved = ranges(segments);
  [moved[index], moved[other]] = [moved[other], moved[index]];
  return moved;
}

/** The segments without segment ``index`` (docs/prototype/wordcut.html ``delseg``).
 * Undefined for the only segment left: a cut plays at least one. */
export function removeSegment(segments: WordRange[], index: number): WordRange[] | undefined {
  if (segments.length < 2) {
    return undefined;
  }
  return ranges(segments).filter((_range, position) => position !== index);
}
