import { formatDuration } from "../../ui/format";
import { PauseIcon, PlayIcon } from "../../ui/icons";

interface CutTransportProps {
  playing: boolean;
  onToggle: () => void;
  /** The cursor and the cut's length, in seconds of the cut. */
  cursor: number;
  duration: number;
}

/** Play/pause and the cursor's time in the cut. */
export function CutTransport({ playing, onToggle, cursor, duration }: CutTransportProps) {
  return (
    <div className="transport">
      <div className="tools" />
      <div className="tools c">
        <button
          className="play"
          type="button"
          aria-label={playing ? "Pausar" : "Reproduzir"}
          onClick={onToggle}
        >
          {playing ? <PauseIcon /> : <PlayIcon />}
        </button>
        <span className="tc" aria-label="Tempo do corte">
          <b>{formatDuration(cursor)}</b> / {formatDuration(duration)}
        </span>
      </div>
      <div className="tools r" />
    </div>
  );
}
