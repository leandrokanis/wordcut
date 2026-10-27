import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
} from "react";

import type { CutStatus, ListedCut, SermonShown } from "../../api/types";
import { formatDuration } from "../../ui/format";
import { cutColor } from "./CutCard";

// The prototype's cut range: at least 10 s, and a press that moves 3 px or less is a click.
export const MIN_RANGE_SECONDS = 10;
const CLICK_SLOP_PX = 3;

/** A cut as the level 2 timeline draws it, over its range. */
export interface CutLayer {
  id: number;
  /** The cut's place in the panel, from 1. */
  number: number;
  title: string;
  color: string;
  status: CutStatus;
  discarded: boolean;
  /** Whether its range may be dragged: by an administrator, on a cut not discarded. */
  editable: boolean;
  duration: number;
  /** Where the sermon starts in the live, which sermon time counts from (ADR-0023). */
  base: number;
  /** The sermon's length: a range never leaves 0 to ``limit`` of sermon time. */
  limit: number;
  /** The cut's range, in sermon time. */
  range: SermonRange;
}

export interface SermonRange {
  start: number;
  end: number;
}

/** What a drag asks the API: the new borders, or the shift of the whole range. */
export type RangeChange = SermonRange | { by: number };

/** The layers of the processed sermon's cuts, in the panel's order. The cuts' times are in
 * sermon time; the processed video starts at ``sermon_start`` of the live (ADR-0023). */
export function cutLayers(
  sermon: SermonShown,
  cuts: ListedCut[] | undefined,
  admin: boolean,
): CutLayer[] {
  const sermonStart = sermon.sermon_start;
  if (sermon.status !== "processed" || sermonStart === null || !cuts) {
    return [];
  }
  const sermonEnd = sermon.sermon_end ?? sermon.live_duration ?? Infinity;
  return cuts.map((cut, index) => ({
    id: cut.id,
    number: index + 1,
    title: cut.title,
    color: cutColor(index),
    status: cut.status,
    discarded: cut.status === "discarded",
    editable: admin && cut.status !== "discarded",
    duration: cut.duration,
    base: sermonStart,
    limit: sermonEnd - sermonStart,
    range: { start: cut.range_start, end: cut.range_end },
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

interface CutLayerLaneProps {
  layer: CutLayer;
  at: (seconds: number) => string;
  liveDuration: number;
  /** Saves the change; the layer shows the dragged range until it settles. */
  onChange: (layer: CutLayer, change: RangeChange) => Promise<unknown>;
  onOpen: (layer: CutLayer) => void;
}

/** The cut's range on its own lane. An editable layer drags by its borders
 * (``data-cutedge``) or by the middle, as the prototype, and saves on release; a press
 * without a drag opens the cut. A discarded cut is marked ``data-discarded`` and, as its
 * card in the panel, neither drags nor opens. */
export function CutLayerLane({ layer, at, liveDuration, onChange, onOpen }: CutLayerLaneProps) {
  const [draft, setDraft] = useState<SermonRange>();
  const endDrag = useRef<() => void>();
  const range = draft ?? layer.range;

  // A drag still open when the layer goes away must not keep listening to the window.
  useEffect(() => () => endDrag.current?.(), []);

  function press(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    event.stopPropagation();
    const edge = (event.target as Element).closest<HTMLElement>("[data-cutedge]")?.dataset.cutedge;
    const mode = !layer.editable ? "click" : edge === "l" || edge === "r" ? edge : "move";
    const width = event.currentTarget.closest(".tl-content")?.getBoundingClientRect().width || 1;
    const x0 = event.clientX;
    let next: SermonRange | undefined;
    const move = (moveEvent: PointerEvent) => {
      const dx = moveEvent.clientX - x0;
      if (mode === "click" || (next === undefined && Math.abs(dx) <= CLICK_SLOP_PX)) {
        return;
      }
      next = dragged(layer, mode, (dx / width) * liveDuration);
      setDraft(next);
    };
    const stopListening = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", release);
      endDrag.current = undefined;
    };
    const release = () => {
      stopListening();
      if (!next) {
        if (!layer.discarded) {
          onOpen(layer);
        }
        return;
      }
      const change =
        mode === "move"
          ? { by: milliseconds(next.start - layer.range.start) }
          : { start: milliseconds(next.start), end: milliseconds(next.end) };
      onChange(layer, change).finally(() => setDraft(undefined));
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", release);
    endDrag.current = stopListening;
  }

  return (
    <div className="lane cut">
      <div
        className="clip ct"
        role="group"
        aria-label={`Corte ${layer.number}: ${layer.title}`}
        data-discarded={layer.discarded || undefined}
        onPointerDown={press}
        style={
          {
            left: at(layer.base + range.start),
            width: at(range.end - range.start),
            "--c": layer.color,
          } as CSSProperties
        }
      >
        {layer.editable && <span className="trim l" data-cutedge="l" aria-hidden="true" />}
        {layer.editable && <span className="trim r" data-cutedge="r" aria-hidden="true" />}
        <span className="lbl">{formatDuration(layer.duration)}</span>
      </div>
    </div>
  );
}

/** The layer's range dragged ``seconds`` by a border or by the middle, as the prototype
 * keeps it: inside the sermon, and a border at least 10 s from the other. */
function dragged(layer: CutLayer, mode: "l" | "r" | "move", seconds: number): SermonRange {
  const { start, end } = layer.range;
  if (mode === "l") {
    return { start: clamp(start + seconds, 0, end - MIN_RANGE_SECONDS), end };
  }
  if (mode === "r") {
    return {
      start,
      end: clamp(end + seconds, start + MIN_RANGE_SECONDS, layer.limit),
    };
  }
  const shift = clamp(seconds, -start, layer.limit - end);
  return { start: start + shift, end: end + shift };
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high);
}

function milliseconds(seconds: number): number {
  return Math.round(seconds * 1000) / 1000;
}
