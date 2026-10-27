import { useEffect, useState, type RefObject } from "react";

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
  /** The sermon is processing: nothing plays. */
  locked: boolean;
}

/** Play/pause and the cursor's time in the live. */
export function Transport({ preview, cursor, liveDuration, onMark, locked }: TransportProps) {
  const [playing, setPlaying] = useState(false);
  // The page pauses the preview as the processing starts; play must not read Pausar after it.
  useEffect(() => {
    if (locked) {
      setPlaying(false);
    }
  }, [locked]);

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
          disabled={locked}
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
