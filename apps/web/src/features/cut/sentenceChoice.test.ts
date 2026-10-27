import { toggleSentence, type SentenceBounds, type WordRange } from "./sentenceChoice";

// Five sentences of a cut's range, by word ID, in sermon order.
const SENTENCES: SentenceBounds[] = [
  { id: 1, first_word: 1, last_word: 4, included: "none" },
  { id: 2, first_word: 5, last_word: 6, included: "none" },
  { id: 3, first_word: 7, last_word: 8, included: "none" },
  { id: 4, first_word: 9, last_word: 12, included: "none" },
  { id: 5, first_word: 13, last_word: 14, included: "none" },
];

/** The sentences as the cut playing ``segments`` shows them, ``part`` where given. */
function shown(segments: WordRange[], partly: number[] = []): SentenceBounds[] {
  return SENTENCES.map((sentence) => {
    const played = segments.some(
      (range) => range.from_word <= sentence.first_word && sentence.last_word <= range.to_word,
    );
    const included = partly.includes(sentence.id) ? "part" : played ? "all" : "none";
    return { ...sentence, included };
  });
}

function range(from_word: number, to_word: number): WordRange {
  return { from_word, to_word };
}

function toggled(segments: WordRange[], id: number, partly: number[] = []) {
  return toggleSentence(segments, shown(segments, partly), id);
}

test("leaving out a sentence in the middle of a segment splits it in two", () => {
  expect(toggled([range(1, 8)], 2)).toEqual({
    segments: [range(1, 4), range(7, 8)],
  });
});

test.each([
  ["first", 1, [range(5, 8)]],
  ["last", 3, [range(1, 6)]],
])("leaving out the %s sentence of a segment shortens it", (_end, id, segments) => {
  expect(toggled([range(1, 8)], id)).toEqual({ segments });
});

test("leaving out a sentence that is a whole segment removes the segment", () => {
  expect(toggled([range(1, 4), range(9, 12)], 1)).toEqual({
    segments: [range(9, 12)],
  });
});

test("leaving out a sentence keeps the order of the other segments when they are reordered", () => {
  expect(toggled([range(9, 12), range(1, 8)], 2)).toEqual({
    segments: [range(9, 12), range(1, 4), range(7, 8)],
  });
});

test("refuses to leave out the only sentence of the cut", () => {
  expect(toggled([range(5, 6)], 2)).toEqual({
    error: "O corte precisa de ao menos uma frase; marque outra antes de tirar esta.",
  });
});

test.each([
  ["the segment before it", [range(1, 4)], [range(1, 6)]],
  ["the segment after it", [range(7, 8)], [range(5, 8)]],
  ["both segments it links", [range(1, 4), range(7, 8)], [range(1, 8)]],
])("including a sentence next to a segment joins %s", (_case, segments, joined) => {
  expect(toggled(segments, 2)).toEqual({ segments: joined });
});

test("including a sentence apart from the segments puts it right after the one with the sentence before it", () => {
  expect(toggled([range(1, 4), range(13, 14)], 3)).toEqual({
    segments: [range(1, 4), range(7, 8), range(13, 14)],
  });
});

test("including a sentence apart from the segments with no sentence before it in the cut puts it first", () => {
  expect(toggled([range(13, 14)], 2)).toEqual({
    segments: [range(5, 6), range(13, 14)],
  });
});

test("including a sentence with the segments reordered follows the one with the sentence before it", () => {
  expect(toggled([range(1, 4), range(13, 14)].reverse(), 3)).toEqual({
    segments: [range(13, 14), range(1, 4), range(7, 8)],
  });
});

test.each([
  ["inside a segment of its own", [range(1, 4), range(10, 11)], [range(1, 4), range(9, 12)]],
  ["at the start of a longer segment", [range(10, 14)], [range(9, 14)]],
  ["at the end of a longer segment", [range(1, 10)], [range(1, 12)]],
])("including a sentence the cut plays in part, %s, plays all of it", (_case, segments, whole) => {
  expect(toggled(segments, 4, [4])).toEqual({ segments: whole });
});

test("leaves the segments it is given as they were", () => {
  const segments = [range(1, 8)];

  toggled(segments, 2);
  toggled(segments, 5);

  expect(segments).toEqual([range(1, 8)]);
});
