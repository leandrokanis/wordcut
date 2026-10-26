import type { CutWord } from "../../api/types";
import { churchCaption, shownCut } from "../../test/fixtures";
import { captionBlocks, captionCss, currentWord, timedWords, type TimedWord } from "./captions";

function word(text: string, start: number, end: number, word_id = 1): TimedWord {
  return { word_id, text, original: text, start, end };
}

const texts = (words: TimedWord[]) => words.map(({ text }) => text).join(" ");

test("times the cut's words in time of the cut, segment after segment", () => {
  const words = timedWords(shownCut());

  expect(words.map(({ text, start, end }) => [text, start.toFixed(2), end.toFixed(2)])).toEqual([
    ["Deus", "0.00", "0.40"],
    ["governa.", "0.45", "0.90"],
    ["Irmãos,", "0.90", "1.30"],
    ["graça", "1.40", "1.80"],
    ["paz.", "1.80", "2.35"],
  ]);
});

test("shows the cut's spelling fix instead of the original word", () => {
  const fixed: CutWord[] = shownCut().words.map((each) =>
    each.word_id === 1102 ? { ...each, corrected: "Graça" } : each,
  );

  const words = timedWords(shownCut({ words: fixed }));

  expect(words.find(({ word_id }) => word_id === 1102)).toMatchObject({
    text: "Graça",
    original: "graça",
  });
});

test("never mixes two sentences in one block", () => {
  const blocks = captionBlocks(
    [word("Deus", 0, 0.4), word("governa.", 0.45, 0.9), word("Irmãos,", 0.9, 1.3)],
    60,
  );

  expect(blocks.map(({ words }) => texts(words))).toEqual(["Deus governa.", "Irmãos,"]);
});

test.each([
  ["a pause of 0.59 s keeps", 0.84, ["um dois"]],
  ["a pause of 0.6 s keeps", 0.85, ["um dois"]],
  ["a pause longer than 0.6 s breaks", 0.86, ["um", "dois"]],
])("%s the block, as vertical/captions.py does", (_case, nextStart, expected) => {
  const blocks = captionBlocks([word("um", 0, 0.25), word("dois", nextStart, 1.2)], 60);

  expect(blocks.map(({ words }) => texts(words))).toEqual(expected);
});

test("splits a sentence too long for two lines into blocks of even length", () => {
  const sentence = Array.from({ length: 24 }, (_, index) =>
    word(index === 23 ? "palavra." : "palavra", index * 0.5, index * 0.5 + 0.4),
  );

  const blocks = captionBlocks(sentence, 60);

  expect(blocks.map(({ words }) => words.length)).toEqual([6, 6, 6, 6]);
});

test.each([
  ["follows the next block when it starts within 0.4 s", 1.2, 1.2],
  ["lingers 0.4 s after the last word before a longer gap", 2.0, 1.4],
])("%s", (_case, nextStart, end) => {
  const blocks = captionBlocks([word("Fim.", 0.5, 1.0), word("Outro", nextStart, 2.5)], 60);

  expect(blocks[0].end).toBeCloseTo(end, 9);
});

test.each([
  [0.39, "Deus"],
  [0.4, null],
  [0.45, "governa."],
  [0.9, null],
])("marks only the word under %f s of the cut as the current one", (cutSeconds, expected) => {
  const words = [word("Deus", 0, 0.4), word("governa.", 0.45, 0.9)];

  expect(currentWord(words, cutSeconds)?.text ?? null).toBe(expected);
});

test("converts the style's px of the 1080 frame into the frame's width", () => {
  expect(captionCss(churchCaption({ size: 108, border: 3, offset: 78 }))).toMatchObject({
    "--cap-size": "10cqw",
    "--cap-stroke": "0.5556cqw",
    "--cap-top": "78%",
  });
});

test("gives the caption the style's colours and font", () => {
  expect(
    captionCss(
      churchCaption({ color: "#FFFFFF", border_color: "#00E5FF", font: "Open Sans Bold" }),
    ),
  ).toMatchObject({
    "--cap-color": "#FFFFFF",
    "--cap-stroke-color": "#00E5FF",
    "--cap-font": '"Open Sans"',
    "--cap-weight": "700",
  });
});

test.each([
  ["none", "none"],
  ["soft", "0.2778cqw 0.2778cqw 0 rgba(0, 0, 0, 0.549)"],
  ["strong", "0.463cqw 0.463cqw 0 rgba(0, 0, 0, 0.863)"],
] as const)("draws the %s shadow as the render does", (shadow, css) => {
  expect(captionCss(churchCaption({ shadow }))["--cap-shadow"]).toBe(css);
});
