import type { RenderOptions } from "../../api/types";

// docs/prototype/wordcut.html xSummary: the resolution, the caption and what departs from the
// defaults of docs/cli.md §8.7, each with how the summary says it.
const DEPARTURES: [(options: RenderOptions) => boolean, string][] = [
  [({ fillers }) => fillers === "keep", "com hesitações"],
  [({ stammers }) => stammers === "keep", "com gaguejos"],
  [({ pauses }) => pauses === "original", "pausas originais"],
  [({ pauses }) => pauses === "short", "pausas curtas"],
  [({ smooth_joins }) => !smooth_joins, "sem suavizar emendas"],
  [({ fade }) => !fade, "sem fade"],
  [({ normalize }) => !normalize, "sem normalizar volume"],
  [({ quality }) => quality === "small", "arquivo menor"],
];

/** An export's options in a few words, as "1080p · com legenda · sem fade". */
export function exportSummary(options: RenderOptions): string {
  return [
    options.resolution === "1080x1920" ? "1080p" : "720p",
    options.caption ? "com legenda" : "sem legenda",
    ...DEPARTURES.filter(([departs]) => departs(options)).map(([, words]) => words),
  ].join(" · ");
}
