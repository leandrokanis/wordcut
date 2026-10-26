import { cutTimeOf, next, pointAt, type Span } from "./sequence";

// docs/cli.md §8.3: the cut plays 2.5–3.4, then 0.3–1.2, then 1.35–1.9, in sermon time.
const OUT_OF_ORDER: Span[] = [
  { start: 2.5, end: 3.4 },
  { start: 0.3, end: 1.2 },
  { start: 1.35, end: 1.9 },
];

test.each([
  ["inside the first segment", 0, 3.0, { kind: "stay" }],
  ["at the end of the first", 0, 3.4, { kind: "seek", index: 1, to: 0.3 }],
  ["past the end of the second", 1, 1.25, { kind: "seek", index: 2, to: 1.35 }],
  ["at the end of the last", 2, 1.9, { kind: "end" }],
  ["inside the third, before where the first starts", 2, 1.5, { kind: "stay" }],
] as const)("goes on %s in the cut's order", (_case, index, t, action) => {
  expect(next(OUT_OF_ORDER, index, t)).toEqual(action);
});

test("ends the third segment, out of order, instead of going back into the first", () => {
  expect(next(OUT_OF_ORDER, 2, 2.6)).toEqual({ kind: "end" });
});

test("stays in the second segment while its time lies inside the first's", () => {
  const overlapping: Span[] = [
    { start: 10, end: 20 },
    { start: 12, end: 18 },
  ];

  expect(next(overlapping, 1, 15)).toEqual({ kind: "stay" });
});

test("ends a single segment at its end", () => {
  expect(next([{ start: 5, end: 9 }], 0, 9)).toEqual({ kind: "end" });
});

test.each([
  [0, 2.5, 0],
  [0, 3.0, 0.5],
  [1, 0.3, 0.9],
  [1, 1.2, 1.8],
  [2, 1.6, 2.05],
])("turns segment %i at %f s of the sermon into cut time", (index, t, cutSeconds) => {
  expect(cutTimeOf(OUT_OF_ORDER, index, t)).toBeCloseTo(cutSeconds, 9);
});

test.each([
  [0, { index: 0, t: 2.5 }],
  [0.5, { index: 0, t: 3.0 }],
  [1.0, { index: 1, t: 0.4 }],
  [2.05, { index: 2, t: 1.6 }],
  [2.35, { index: 2, t: 1.9 }],
])("finds the segment and sermon time of %f s of the cut", (cutSeconds, point) => {
  const found = pointAt(OUT_OF_ORDER, cutSeconds);

  expect(found.index).toBe(point.index);
  expect(found.t).toBeCloseTo(point.t, 9);
});
