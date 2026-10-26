/** A segment of the cut, in sermon time. */
export interface Span {
  start: number;
  end: number;
}

/** What the preview does at sermon time ``t`` while it plays segment ``index``. */
export type Step = { kind: "stay" } | { kind: "seek"; index: number; to: number } | { kind: "end" };

/** The next step of the sequence. It goes by the segment playing, never by the time alone:
 * a segment out of order may lie inside another one's time (docs/cli.md §8.3). */
export function next(segments: Span[], index: number, t: number): Step {
  if (t < segments[index].end) {
    return { kind: "stay" };
  }
  const following = index + 1;
  return following < segments.length
    ? { kind: "seek", index: following, to: segments[following].start }
    : { kind: "end" };
}

/** Seconds of the cut, from 0, at sermon time ``t`` inside segment ``index``. */
export function cutTimeOf(segments: Span[], index: number, t: number): number {
  const segment = segments[index];
  const inside = Math.min(Math.max(t - segment.start, 0), segment.end - segment.start);
  return offsetOf(segments, index) + inside;
}

/** The segment and sermon time at ``cutSeconds`` of the cut, kept inside the cut. */
export function pointAt(segments: Span[], cutSeconds: number): { index: number; t: number } {
  let left = Math.max(cutSeconds, 0);
  for (const [index, segment] of segments.entries()) {
    const span = segment.end - segment.start;
    if (left < span || index === segments.length - 1) {
      return { index, t: segment.start + Math.min(left, span) };
    }
    left -= span;
  }
  return { index: 0, t: 0 };
}

/** Where segment ``index`` starts in the cut. */
export function offsetOf(segments: Span[], index: number): number {
  return segments.slice(0, index).reduce((sum, { start, end }) => sum + end - start, 0);
}

// ADR-0023: the cut's segments and words are in sermon time; the player speaks seconds of the
// live, and the processed video starts at ``sermon_start`` of the live. Only these two convert.

/** Seconds of the live at ``sermonSeconds`` of the sermon. */
export function toLive(sermonStart: number, sermonSeconds: number): number {
  return sermonStart + sermonSeconds;
}

/** Seconds of the sermon at ``liveSeconds`` of the live. */
export function toSermon(sermonStart: number, liveSeconds: number): number {
  return liveSeconds - sermonStart;
}
