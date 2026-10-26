import type { CSSProperties } from "react";

import type { ListedCut, SermonShown } from "../../api/types";
import { formatDuration } from "../../ui/format";
import { cutColor } from "./CutCard";

/** A cut as the level 2 timeline draws it: read only, in time of the live. */
export interface CutLayer {
  id: number;
  /** The cut's place in the panel, from 1. */
  number: number;
  title: string;
  color: string;
  discarded: boolean;
  duration: number;
  liveStart: number;
  /** From the earliest start to the latest end of the cut's segments. */
  span: number;
}

/** The layers of the processed sermon's cuts, in the panel's order. The cuts' times are in
 * sermon time; the processed video starts at ``sermon_start`` of the live (ADR-0023). */
export function cutLayers(sermon: SermonShown, cuts: ListedCut[] | undefined): CutLayer[] {
  const sermonStart = sermon.sermon_start;
  if (sermon.status !== "processed" || sermonStart === null || !cuts) {
    return [];
  }
  return cuts.map((cut, index) => ({
    id: cut.id,
    number: index + 1,
    title: cut.title,
    color: cutColor(index),
    discarded: cut.status === "discarded",
    duration: cut.duration,
    liveStart: sermonStart + cut.start,
    span: cut.end - cut.start,
  }));
}

export function CutLayerHead({ layer }: { layer: CutLayer }) {
  return (
    <div className="th cut-head" title={layer.title}>
      <i className="rnum" style={{ "--c": layer.color } as CSSProperties}>
        {layer.number}
      </i>
      <span className="thn">{layer.title}</span>
    </div>
  );
}

/** The cut's stretch on its own lane, without handles: editing it is 2.1.c, a later wave. A
 * discarded cut is marked ``data-discarded``. */
export function CutLayerLane({ layer, at }: { layer: CutLayer; at: (seconds: number) => string }) {
  return (
    <div className="lane cut">
      <div
        className="clip ct"
        role="group"
        aria-label={`Corte ${layer.number}: ${layer.title}`}
        data-discarded={layer.discarded || undefined}
        style={
          {
            left: at(layer.liveStart),
            width: at(layer.span),
            "--c": layer.color,
          } as CSSProperties
        }
      >
        <span className="lbl">{formatDuration(layer.duration)}</span>
      </div>
    </div>
  );
}
