import { useRef, type PointerEvent as ReactPointerEvent } from "react";

import { formatDuration } from "../../ui/format";
import { CaptionIcon, FilmIcon } from "../../ui/icons";
import { rulerMarks } from "../sermon/Timeline";
import type { CaptionBlock } from "./captions";
import { offsetOf, type Span } from "./sequence";

interface CutTimelineProps {
  /** The segments in the order the cut plays them, in sermon time; ``out_of_order`` as
   * ``GET /api/cuts/{id}/preview`` marks it (docs/cli.md §8.3). */
  segments: (Span & { out_of_order?: boolean })[];
  duration: number;
  /** The player's position, in seconds of the cut. */
  cursor: number;
  onSeek: (cutSeconds: number) => void;
  /** The caption's blocks, drawn on the "Legenda" layer, which opens the Legenda tab. */
  blocks: CaptionBlock[];
  captionOn: boolean;
  /** The Legenda tab is open: the layer is marked as selected. */
  legendOpen: boolean;
  /** The segment selected for the segment tools, by its position in ``segments``. */
  selected?: number;
  onSelect: (index: number) => void;
}

/** Only the cut, in time of the cut: the ruler, the "Legenda" layer with the caption's blocks
 * and the "Vídeo" track with one clip per segment, one after the other. What carries
 * ``data-legend`` opens the Legenda tab (CutPage). */
export function CutTimeline({
  segments,
  duration,
  cursor,
  onSeek,
  blocks,
  captionOn,
  legendOpen,
  selected,
  onSelect,
}: CutTimelineProps) {
  const content = useRef<HTMLDivElement>(null);
  const at = (seconds: number) => `${(seconds / duration) * 100}%`;

  function seek(event: ReactPointerEvent) {
    onSeek(cutTimeAt(content.current, event.clientX, duration));
  }

  return (
    <section className="tl" aria-label="Timeline">
      <div className="tl-heads">
        <div className="th ruler-head" />
        <button
          type="button"
          className={legendOpen ? "th cap-head on" : "th cap-head"}
          aria-label="Camada Legenda"
          aria-pressed={legendOpen}
          data-legend
        >
          <CaptionIcon />
          <span className="thn">Legenda</span>
        </button>
        <div className="th video-head">
          <FilmIcon />
          <span className="thn">Vídeo</span>
        </div>
      </div>
      <div className="tl-scroll">
        <div className="tl-content" ref={content}>
          <div className="lane ruler" aria-label="Régua do corte" onPointerDown={seek}>
            {rulerMarks(duration).map(({ seconds, labelled }) => (
              <div
                key={seconds}
                className={labelled ? "tick major" : "tick"}
                style={{ left: at(seconds) }}
              >
                {labelled && <span>{formatDuration(seconds)}</span>}
              </div>
            ))}
          </div>
          <div className={legendOpen ? "lane cap on" : "lane cap"} data-legend onPointerDown={seek}>
            {!captionOn && <span className="lane-hint">Legenda desativada</span>}
            {blocks.map((block) => (
              <div
                key={block.start}
                className={captionOn ? "clip cap" : "clip cap off"}
                style={{ left: at(block.start), width: at(block.end - block.start) }}
                title={blockText(block)}
              >
                <span>{blockText(block)}</span>
              </div>
            ))}
          </div>
          <div className="lane video" onPointerDown={seek}>
            {segments.map((segment, index) => (
              <button
                key={index}
                type="button"
                className={clipClass(index === selected, segment.out_of_order)}
                aria-label={
                  segment.out_of_order
                    ? `Trecho ${index + 1}, fora da ordem da pregação`
                    : `Trecho ${index + 1}`
                }
                title={segment.out_of_order ? "Fora da ordem da pregação" : undefined}
                aria-pressed={index === selected}
                onClick={() => onSelect(index)}
                style={{
                  left: at(offsetOf(segments, index)),
                  width: at(segment.end - segment.start),
                }}
              >
                <span className="lbl">
                  <b>T{index + 1}</b> · {formatDuration(segment.end - segment.start)}
                </span>
              </button>
            ))}
          </div>
          <div className="playhead" aria-label="Cursor" style={{ left: at(cursor) }} />
        </div>
      </div>
    </section>
  );
}

function clipClass(selected: boolean, outOfOrder = false): string {
  return ["clip vid", selected && "sel", outOfOrder && "ooo"].filter(Boolean).join(" ");
}

function blockText(block: CaptionBlock): string {
  return block.words.map(({ text }) => text).join(" ");
}

/** Seconds of the cut under ``clientX``, kept inside the cut. */
function cutTimeAt(content: HTMLElement | null, clientX: number, duration: number): number {
  if (!content) {
    return 0;
  }
  const { left, width } = content.getBoundingClientRect();
  const fraction = width ? (clientX - left) / width : 0;
  return Math.min(Math.max(fraction, 0), 1) * duration;
}
