import { defaultRenderOptions } from "../../test/fixtures";
import { exportSummary } from "./exportSummary";

test.each([
  [{}, "1080p · com legenda"],
  [{ resolution: "720x1280", caption: false }, "720p · sem legenda"],
  [{ fillers: "keep" }, "1080p · com legenda · com hesitações"],
  [{ stammers: "keep" }, "1080p · com legenda · com gaguejos"],
  [{ pauses: "original" }, "1080p · com legenda · pausas originais"],
  [{ pauses: "short" }, "1080p · com legenda · pausas curtas"],
  [{ smooth_joins: false }, "1080p · com legenda · sem suavizar emendas"],
  [{ fade: false }, "1080p · com legenda · sem fade"],
  [{ normalize: false }, "1080p · com legenda · sem normalizar volume"],
  [{ quality: "small" }, "1080p · com legenda · arquivo menor"],
  [
    { fillers: "keep", pauses: "original", quality: "small", caption: false },
    "1080p · sem legenda · com hesitações · pausas originais · arquivo menor",
  ],
] as const)("sums up %o as “%s”", (changes, summary) => {
  expect(exportSummary(defaultRenderOptions(changes))).toBe(summary);
});
