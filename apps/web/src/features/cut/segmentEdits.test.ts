import { moveSegment, removeSegment, splitAt, type TimedRange } from "./segmentEdits";
import type { WordRange } from "./sentenceChoice";

// Five sentences of a cut's range, by word ID, starting every 10 s of the sermon.
const SENTENCES = [
  { id: 1, first_word: 1, last_word: 4, start: 0 },
  { id: 2, first_word: 5, last_word: 6, start: 10 },
  { id: 3, first_word: 7, last_word: 8, start: 20 },
  { id: 4, first_word: 9, last_word: 12, start: 30 },
  { id: 5, first_word: 13, last_word: 14, start: 40 },
];

function range(from_word: number, to_word: number): WordRange {
  return { from_word, to_word };
}

/** Words ``from_word`` to ``to_word``, played from ``start`` to ``end`` of the sermon. */
function timed(from_word: number, to_word: number, start: number, end: number): TimedRange {
  return { from_word, to_word, start, end };
}

test("splits a segment at the sentence boundary nearest the cursor", () => {
  expect(splitAt([timed(1, 8, 0, 30)], SENTENCES, 0, 18)).toEqual([range(1, 6), range(7, 8)]);
});

test("splits at the earlier boundary when the cursor is as near the later one", () => {
  expect(splitAt([timed(1, 8, 0, 30)], SENTENCES, 0, 15)).toEqual([range(1, 4), range(5, 8)]);
});

test("reads the cursor in time of the cut, after the segments played before", () => {
  expect(splitAt([timed(13, 14, 40, 50), timed(1, 8, 0, 30)], SENTENCES, 1, 18)).toEqual([
    range(13, 14),
    range(1, 4),
    range(5, 8),
  ]);
});

test.each([
  ["before", -1],
  ["after", 31],
])("refuses to split when the cursor is %s the segment", (_where, cursor) => {
  expect(splitAt([timed(1, 8, 0, 30)], SENTENCES, 0, cursor)).toBeUndefined();
});

test("refuses to split a segment of one sentence", () => {
  expect(splitAt([timed(9, 12, 30, 40)], SENTENCES, 0, 5)).toBeUndefined();
});

test("refuses to split a segment that starts and ends inside one sentence", () => {
  expect(splitAt([timed(10, 11, 32, 38)], SENTENCES, 0, 3)).toBeUndefined();
});

test.each([
  ["left", -1, [range(5, 6), range(1, 4), range(7, 8)]],
  ["right", 1, [range(1, 4), range(7, 8), range(5, 6)]],
] as const)(
  "moves a segment to the %s, swapping it with its neighbour",
  (_side, direction, moved) => {
    expect(moveSegment([range(1, 4), range(5, 6), range(7, 8)], 1, direction)).toEqual(moved);
  },
);

test.each([
  ["first", 0, -1],
  ["last", 2, 1],
] as const)("refuses to move the %s segment out of the cut", (_end, index, direction) => {
  expect(moveSegment([range(1, 4), range(5, 6), range(7, 8)], index, direction)).toBeUndefined();
});

test("removes a segment, keeping the order of the others", () => {
  expect(removeSegment([range(7, 8), range(1, 4), range(5, 6)], 1)).toEqual([
    range(7, 8),
    range(5, 6),
  ]);
});

test("refuses to remove the only segment left", () => {
  expect(removeSegment([range(1, 4)], 0)).toBeUndefined();
});

test("leaves the segments it is given as they were", () => {
  const segments = [timed(1, 8, 0, 30), timed(9, 12, 30, 40)];
  const before = structuredClone(segments);

  splitAt(segments, SENTENCES, 0, 18);
  moveSegment(segments, 0, 1);
  removeSegment(segments, 0);

  expect(segments).toEqual(before);
});
