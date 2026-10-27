// The prototype's waveform (docs/prototype/wordcut.html, ``wave``): bars 2 px wide every
// 3 px on a 40 px track, never shorter than 6 % of it.
const BAR_STEP = 3;
const BAR_WIDTH = 2;
const TRACK_HEIGHT = 40;
const TRACK_MARGIN = 6;
const MIN_BAR = 0.06;
// More bars than a timeline at its default zoom has room for; keeps the image small.
const MAX_BARS = 1200;
const BACKGROUND = "#18203a";
const BAR_COLOR = "#8094ff";

/** The CSS image of the waveform of ``peaks``, stretched to the track's size. */
export function waveformImage(peaks: number[]): string {
  const bars = fewer(peaks, MAX_BARS);
  const width = bars.length * BAR_STEP;
  const path = bars
    .map((peak, index) => {
      const height = Math.max(MIN_BAR, Math.min(1, peak)) * (TRACK_HEIGHT - TRACK_MARGIN);
      const top = (TRACK_HEIGHT - height) / 2;
      return `M${index * BAR_STEP} ${round(top)}h${BAR_WIDTH}v${round(height)}h-${BAR_WIDTH}z`;
    })
    .join("");
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${TRACK_HEIGHT}"` +
    ` preserveAspectRatio="none"><rect width="${width}" height="${TRACK_HEIGHT}"` +
    ` fill="${BACKGROUND}"/><path d="${path}" fill="${BAR_COLOR}"/></svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

/** ``peaks`` reduced to at most ``count`` bars, each the loudest of its stretch. */
function fewer(peaks: number[], count: number): number[] {
  if (peaks.length <= count) {
    return peaks;
  }
  return Array.from({ length: count }, (_, bar) => {
    const from = Math.floor((bar * peaks.length) / count);
    const to = Math.floor(((bar + 1) * peaks.length) / count);
    return Math.max(...peaks.slice(from, to));
  });
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}
