import {
  useEffect,
  useMemo,
  useRef,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { formatDuration } from "../../ui/format";
import { FilmIcon, WaveIcon } from "../../ui/icons";
import type { Bounds } from "./bounds";
import type { Edge } from "./ClipEdges";
import { CutLayerHead, CutLayerLane, type CutLayer, type RangeChange } from "./CutLayers";
import type { TimelineMedia } from "./useTimelineMedia";
import { waveformImage } from "./waveform";

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
  /** The cuts, drawn above the video track. */
  layers?: CutLayer[];
  /** Saves a cut's range dragged on its layer. */
  onCutChange?: (layer: CutLayer, change: RangeChange) => Promise<unknown>;
  /** Opens a cut whose layer was pressed without a drag. */
  onCutOpen?: (layer: CutLayer) => void;
  /** The thumbnails and the waveform of the live, and how their preparation goes. */
  media?: TimelineMedia;
}

/** The live in time of the live: the ruler, the "Vídeo" track with the sermon's clip over
 * the live's thumbnails and the "Áudio" track with its waveform. The whole live lies faded
 * behind each clip, marked ``data-faded``: what the borders cut. */
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
  onCutChange = () => Promise.resolve(),
  onCutOpen = () => {},
  media,
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
  const thumbnails = media?.thumbnails && `url(${media.thumbnails})`;
  const peaks = media?.peaks;
  const wave = useMemo(() => peaks && waveformImage(peaks), [peaks]);
  const clipPlace = { left: at(bounds.start), width: at(bounds.end - bounds.start) };
  const inner = (image: string | undefined) =>
    image ? innerBackground(image, bounds, liveDuration) : {};
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
        <div className="th audio-head">
          <WaveIcon />
          <span className="thn">Áudio</span>
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
            <CutLayerLane
              key={layer.id}
              layer={layer}
              at={at}
              liveDuration={liveDuration}
              onChange={onCutChange}
              onOpen={onCutOpen}
            />
          ))}
          <div className="lane video" aria-label="Faixa Vídeo">
            <div
              className="clip vid ghost"
              data-faded
              style={{ left: "0%", width: "100%", backgroundImage: thumbnails }}
            />
            <div
              className={trimmed ? "clip vid trimclip on" : "clip vid trimclip"}
              role="group"
              aria-label="Pregação na live"
              style={{ ...clipPlace, ...inner(thumbnails) }}
            >
              {onEdgeMove && handle("start", "l", "Início da pregação")}
              {onEdgeMove && handle("end", "r", "Fim da pregação")}
              <span className="lbl">{label}</span>
            </div>
          </div>
          <div className="lane audio" aria-label="Faixa Áudio">
            <div
              className="clip aud ghost"
              data-faded
              style={{ left: "0%", width: "100%", backgroundImage: wave }}
            />
            <div
              className="clip aud"
              aria-label="Áudio da pregação"
              style={{ ...clipPlace, ...inner(wave) }}
            />
          </div>
          <div className="playhead" aria-label="Cursor" style={{ left: at(cursor) }} />
        </div>
      </div>
      {media && <MediaNote media={media} />}
    </section>
  );
}

/** Says that the thumbnails and the waveform are being prepared, or that they failed. */
function MediaNote({ media }: { media: TimelineMedia }) {
  if (media.status === "pending") {
    return <p className="tl-note">Preparando a timeline…</p>;
  }
  if (media.status === "ready") {
    return null;
  }
  return (
    <p className="tl-note" role="status">
      Miniaturas e forma de onda indisponíveis.
      <button type="button" className="btn sm ghost" onClick={media.retry}>
        Tentar de novo
      </button>
      {media.refusal && <span className="ferr">{media.refusal.message}</span>}
    </p>
  );
}

/** The prototype's ``innerBg``: the clip shows only its stretch of the whole live's image. */
function innerBackground(image: string, bounds: Bounds, liveDuration: number): CSSProperties {
  const span = bounds.end - bounds.start;
  if (span <= 0) {
    return {};
  }
  const position = span >= liveDuration ? 0 : (bounds.start / (liveDuration - span)) * 100;
  return {
    backgroundImage: image,
    backgroundSize: `${(liveDuration / span) * 100}% 100%`,
    backgroundPosition: `${position}% 0`,
  };
}

/** The ruler's marks over ``duration`` seconds: about 8 labelled ones. */
export function rulerMarks(duration: number): { seconds: number; labelled: boolean }[] {
  const step =
    RULER_STEPS.find((candidate) => candidate >= duration / LABELLED_MARKS) ??
    RULER_STEPS[RULER_STEPS.length - 1];
  const minor = step / MARKS_PER_STEP;
  const marks = [];
  for (let index = 0; index * minor <= duration; index++) {
    marks.push({
      seconds: index * minor,
      labelled: index % MARKS_PER_STEP === 0,
    });
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
