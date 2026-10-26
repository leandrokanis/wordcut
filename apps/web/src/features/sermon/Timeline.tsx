import { useEffect, useRef, type PointerEvent as ReactPointerEvent } from "react";

import { formatDuration } from "../../ui/format";
import { FilmIcon } from "../../ui/icons";
import type { Bounds } from "./bounds";
import type { Edge } from "./ClipEdges";
import { CutLayerHead, CutLayerLane, type CutLayer } from "./CutLayers";

// The ruler's steps, in seconds, as the prototype picks them: about 8 labelled marks.
const RULER_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];
const LABELLED_MARKS = 8;
const MARKS_PER_STEP = 5;

interface TimelineProps {
  /** Null when the API does not know the live's length. */
  liveDuration: number | null;
  bounds: Bounds;
  trimmed: boolean;
  /** The player's position. */
  cursor: number;
  onSeek: (liveSeconds: number) => void;
  /** Null while the borders cannot change: no handles are drawn. */
  onEdgeMove: ((edge: Edge, liveSeconds: number) => void) | null;
  onEdgeRelease: () => void;
  /** The cuts, drawn read only above the video track. */
  layers?: CutLayer[];
}

/** The live in time of the live: the ruler and the "Vídeo" track with the sermon's clip.
 * The whole live lies faded behind the clip, marked ``data-faded``: what the borders cut. */
export function Timeline({ liveDuration, ...track }: TimelineProps) {
  if (!liveDuration) {
    return (
      <section className="tl" aria-label="Timeline">
        <p className="tl-empty">Duração da live indisponível.</p>
      </section>
    );
  }
  return <LiveTimeline liveDuration={liveDuration} {...track} />;
}

function LiveTimeline({
  liveDuration,
  bounds,
  trimmed,
  cursor,
  onSeek,
  onEdgeMove,
  onEdgeRelease,
  layers = [],
}: TimelineProps & { liveDuration: number }) {
  const content = useRef<HTMLDivElement>(null);
  const endDrag = useRef<() => void>();
  const timeAt = (clientX: number) => liveTimeAt(content.current, clientX, liveDuration);

  // A drag still open when the screen goes away must not keep listening to the window.
  useEffect(() => () => endDrag.current?.(), []);

  function startDrag(edge: Edge, event: ReactPointerEvent) {
    event.preventDefault();
    event.stopPropagation();
    const move = (moveEvent: PointerEvent) => onEdgeMove?.(edge, timeAt(moveEvent.clientX));
    const stopListening = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", release);
      endDrag.current = undefined;
    };
    const release = () => {
      stopListening();
      onEdgeRelease();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", release);
    endDrag.current = stopListening;
  }

  const handle = (edge: Edge, side: "l" | "r", name: string) => (
    <span
      className={`trim ${side}`}
      role="slider"
      tabIndex={0}
      aria-label={name}
      aria-valuemin={0}
      aria-valuemax={liveDuration}
      aria-valuenow={bounds[edge]}
      aria-valuetext={formatDuration(bounds[edge])}
      onPointerDown={(event) => startDrag(edge, event)}
    />
  );
  const at = (seconds: number) => `${(seconds / liveDuration) * 100}%`;
  const label = trimmed
    ? `Pregação · ${formatDuration(bounds.end - bounds.start)}`
    : `Live inteira · ${formatDuration(liveDuration)}`;
  return (
    <section className="tl" aria-label="Timeline">
      <div className="tl-heads">
        <div className="th ruler-head" />
        {layers.map((layer) => (
          <CutLayerHead key={layer.id} layer={layer} />
        ))}
        <div className="th video-head">
          <FilmIcon />
          <span className="thn">Vídeo</span>
        </div>
      </div>
      <div className="tl-scroll">
        <div className="tl-content" ref={content}>
          <div
            className="lane ruler"
            aria-label="Régua da live"
            onPointerDown={(event) => onSeek(timeAt(event.clientX))}
          >
            {rulerMarks(liveDuration).map(({ seconds, labelled }) => (
              <div
                key={seconds}
                className={labelled ? "tick major" : "tick"}
                style={{ left: at(seconds) }}
              >
                {labelled && <span>{formatDuration(seconds)}</span>}
              </div>
            ))}
          </div>
          {layers.map((layer) => (
            <CutLayerLane key={layer.id} layer={layer} at={at} />
          ))}
          <div className="lane video">
            <div className="clip vid ghost" data-faded style={{ left: "0%", width: "100%" }} />
            <div
              className={trimmed ? "clip vid trimclip on" : "clip vid trimclip"}
              role="group"
              aria-label="Pregação na live"
              style={{ left: at(bounds.start), width: at(bounds.end - bounds.start) }}
            >
              {onEdgeMove && handle("start", "l", "Início da pregação")}
              {onEdgeMove && handle("end", "r", "Fim da pregação")}
              <span className="lbl">{label}</span>
            </div>
          </div>
          <div className="playhead" aria-label="Cursor" style={{ left: at(cursor) }} />
        </div>
      </div>
    </section>
  );
}

/** The ruler's marks over ``duration`` seconds: about 8 labelled ones. */
export function rulerMarks(duration: number): { seconds: number; labelled: boolean }[] {
  const step =
    RULER_STEPS.find((candidate) => candidate >= duration / LABELLED_MARKS) ??
    RULER_STEPS[RULER_STEPS.length - 1];
  const minor = step / MARKS_PER_STEP;
  const marks = [];
  for (let index = 0; index * minor <= duration; index++) {
    marks.push({ seconds: index * minor, labelled: index % MARKS_PER_STEP === 0 });
  }
  return marks;
}

/** The time of the live under ``clientX``, kept inside the live. */
function liveTimeAt(content: HTMLElement | null, clientX: number, liveDuration: number): number {
  if (!content) {
    return 0;
  }
  const { left, width } = content.getBoundingClientRect();
  const fraction = width ? (clientX - left) / width : 0;
  return Math.round(Math.min(Math.max(fraction, 0), 1) * liveDuration);
}
