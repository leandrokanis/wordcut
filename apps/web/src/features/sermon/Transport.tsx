import { useState, type RefObject } from "react";

import { formatDuration } from "../../ui/format";
import { PauseIcon, PlayIcon } from "../../ui/icons";
import type { Edge } from "./ClipEdges";
import type { PreviewHandle } from "./Preview";

interface TransportProps {
  preview: RefObject<PreviewHandle>;
  cursor: number;
  liveDuration: number | null;
  /** Null while the borders cannot change. */
  onMark: ((edge: Edge) => void) | null;
}

/** Play/pause and the cursor's time in the live. */
export function Transport({ preview, cursor, liveDuration, onMark }: TransportProps) {
  const [playing, setPlaying] = useState(false);

  function toggle() {
    if (playing) {
      preview.current?.pause();
    } else {
      preview.current?.play();
    }
    setPlaying(!playing);
  }

  return (
    <div className="transport">
      <div className="tools">
        <button
          className="btn sm"
          type="button"
          disabled={!onMark}
          title="Puxa a borda inicial até o cursor"
          onClick={() => onMark?.("start")}
        >
          Início aqui <span className="kbd">I</span>
        </button>
        <button
          className="btn sm"
          type="button"
          disabled={!onMark}
          title="Puxa a borda final até o cursor"
          onClick={() => onMark?.("end")}
        >
          Fim aqui <span className="kbd">O</span>
        </button>
      </div>
      <div className="tools c">
        <button
          className="play"
          type="button"
          aria-label={playing ? "Pausar" : "Reproduzir"}
          onClick={toggle}
        >
          {playing ? <PauseIcon /> : <PlayIcon />}
        </button>
        <span className="tc">
          <b>{formatDuration(cursor)}</b>
          {liveDuration != null && ` / ${formatDuration(liveDuration)}`}
        </span>
      </div>
      <div className="tools r" />
    </div>
  );
}
