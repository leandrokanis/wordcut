import type { CaptionShadow, CaptionStyle, Cut, CutSegment, CutWord } from "../../api/types";
import { offsetOf } from "./sequence";

/** A word of the caption in time of the cut: ``text`` is what the caption shows, the cut's
 * spelling fix or else the ``original``. */
export interface TimedWord {
  word_id: number;
  text: string;
  original: string;
  start: number;
  end: number;
}

/** A block of the caption, shown from ``start`` to ``end`` of the cut. */
export interface CaptionBlock {
  start: number;
  end: number;
  words: TimedWord[];
}

// The grouping of packages/core vertical/captions.py, the render the preview approximates.
const SENTENCE_END = [".", "?", "!"];
const PAUSE_BREAK_S = 0.6;
const LINGER_S = 0.4;
const MAX_LINE_WIDTH_PX = 960;
const MAX_LINES = 2;
// Without the font's metrics in the browser, a glyph of Open Sans Bold is taken as this share
// of the font size: the blocks approximate the render's, which measures each line.
const GLYPH_WIDTH_EM = 0.6;

/** The cut's words, segment after segment, moved from sermon time into time of the cut. */
export function timedWords(cut: Pick<Cut, "segments" | "words">): TimedWord[] {
  return cut.segments.flatMap((segment, index) => {
    const offset = offsetOf(cut.segments, index);
    return wordsOf(cut.words, segment).map((word) => ({
      word_id: word.word_id,
      text: word.corrected ?? word.text,
      original: word.text,
      start: offset + word.start - segment.start,
      end: offset + word.end - segment.start,
    }));
  });
}

/** The cut's words that ``segment`` plays. */
export function wordsOf(words: CutWord[], segment: CutSegment): CutWord[] {
  return words.filter(({ word_id }) => word_id >= segment.from_word && word_id <= segment.to_word);
}

/** The caption's blocks: a block never mixes two sentences or crosses a long pause, and a
 * sentence too long for two lines of ``sizePx`` is split into blocks of even length. Each
 * block lasts until the next one, or lingers a little before a longer gap. */
export function captionBlocks(words: TimedWord[], sizePx: number): CaptionBlock[] {
  const groups = phrasesOf(words).flatMap((phrase) => splitPhrase(phrase, sizePx));
  return groups.map((group, index) => {
    const lastEnd = group[group.length - 1].end;
    const nextStart = groups[index + 1]?.[0].start;
    const end =
      nextStart !== undefined && nextStart - lastEnd <= LINGER_S ? nextStart : lastEnd + LINGER_S;
    return { start: group[0].start, end, words: group };
  });
}

function phrasesOf(words: TimedWord[]): TimedWord[][] {
  const phrases: TimedWord[][] = [];
  let current: TimedWord[] = [];
  for (const word of words) {
    if (current.length && word.start - current[current.length - 1].end > PAUSE_BREAK_S) {
      phrases.push(current);
      current = [];
    }
    current.push(word);
    if (SENTENCE_END.some((mark) => word.text.endsWith(mark))) {
      phrases.push(current);
      current = [];
    }
  }
  if (current.length) {
    phrases.push(current);
  }
  return phrases;
}

function splitPhrase(phrase: TimedWord[], sizePx: number): TimedWord[][] {
  const charsPerBlock = Math.floor(MAX_LINE_WIDTH_PX / (GLYPH_WIDTH_EM * sizePx)) * MAX_LINES;
  const total = phrase.map(({ text }) => text).join(" ").length;
  const count = Math.max(1, Math.ceil(total / charsPerBlock));
  const share = total / count;
  const blocks: TimedWord[][] = Array.from({ length: count }, () => []);
  let position = 0;
  for (const word of phrase) {
    const middle = position + word.text.length / 2;
    blocks[Math.min(count - 1, Math.floor(middle / share))].push(word);
    position += word.text.length + 1;
  }
  return blocks.filter((block) => block.length);
}

/** The block on screen at ``cutSeconds``, if any. */
export function blockAt(blocks: CaptionBlock[], cutSeconds: number): CaptionBlock | undefined {
  return blocks.find(({ start, end }) => start <= cutSeconds && cutSeconds < end);
}

/** The word being said at ``cutSeconds``: only one, even where a word ends as the next
 * starts. */
export function currentWord(words: TimedWord[], cutSeconds: number): TimedWord | undefined {
  return words.find(({ start, end }) => start <= cutSeconds && cutSeconds < end);
}

const FRAME_WIDTH_PX = 1080;

/** The fonts the API knows (packages/core vertical/fonts.py), as the browser loads them. */
export const CAPTION_FONTS: Record<string, { family: string; weight: number }> = {
  "Open Sans Bold": { family: "Open Sans", weight: 700 },
};

// packages/core cuts/caption.py SHADOW_LOOKS: a hard drop shadow, (alpha 0-255, offset px).
const SHADOW_LOOKS: Record<CaptionShadow, [number, number]> = {
  none: [0, 0],
  soft: [140, 3],
  strong: [220, 5],
};

/** The caption's style as custom properties of the vertical frame. The style's px are of the
 * 1080 px wide frame; ``cqw`` is 1 % of the frame's width, so ``px / 1080 × 100`` cqw. */
export function captionCss(style: CaptionStyle): Record<string, string> {
  const font = CAPTION_FONTS[style.font] ?? CAPTION_FONTS["Open Sans Bold"];
  const [alpha, offset] = SHADOW_LOOKS[style.shadow];
  return {
    "--cap-font": `"${font.family}"`,
    "--cap-weight": String(font.weight),
    "--cap-size": frameWidth(style.size),
    "--cap-color": style.color,
    // The render strokes outside the glyph; -webkit-text-stroke is centred on its edge, and
    // the fill painted over it hides the inner half: twice the width shows the same outline.
    "--cap-stroke": frameWidth(style.border * 2),
    "--cap-stroke-color": style.border_color,
    "--cap-top": `${style.offset}%`,
    "--cap-shadow": alpha
      ? `${frameWidth(offset)} ${frameWidth(offset)} 0 rgba(0, 0, 0, ${round(alpha / 255, 3)})`
      : "none",
  };
}

function frameWidth(px: number): string {
  return `${round((px / FRAME_WIDTH_PX) * 100, 4)}cqw`;
}

function round(value: number, digits: number): number {
  return Number(value.toFixed(digits));
}
