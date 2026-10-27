import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { showSermon } from "../../api/client";
import type { SermonShown } from "../../api/types";
import { useResource } from "../../api/useResource";
import { Saved } from "../../ui/Saved";
import { isTrimmed, savedBounds } from "./bounds";
import { useClipEdges, type Edge } from "./ClipEdges";
import { cutLayers } from "./CutLayers";
import { CutsPanel, useSermonCuts } from "./CutsPanel";
import { Preview, type PreviewHandle } from "./Preview";
import { ProcessButton } from "./ProcessButton";
import { Timeline } from "./Timeline";
import { Transport } from "./Transport";
import { useProcessing } from "./useProcessing";

/** Level 2: the cuts panel beside the 16:9 preview and the timeline of one sermon. */
export function SermonPage() {
  const id = Number(useParams().id);
  const sermon = useResource(() => showSermon(id), `sermon:${id}`);
  const preview = useRef<PreviewHandle>(null);
  const [cursor, setCursor] = useState(0);
  const [patched, setPatched] = useState<SermonShown>();
  const [bordersChanged, setBordersChanged] = useState(false);
  const shown = patched ?? sermon.data;
  const cuts = useSermonCuts(sermon.data);
  // A fresh load of the sermon already has the borders the PATCH saved.
  useEffect(() => setPatched(undefined), [sermon.data]);

  const liveDuration = shown?.live_duration ?? null;
  const edges = useClipEdges({
    sermonId: id,
    saved: shown ? savedBounds(shown, liveDuration ?? 0) : { start: 0, end: 0 },
    liveDuration: liveDuration ?? 0,
    onSaved(saved) {
      setPatched(saved);
      setBordersChanged(saved.status === "processed");
    },
  });

  function moveEdge(edge: Edge, liveSeconds: number) {
    preview.current?.seek(edges.move(edge, liveSeconds));
  }

  const processing = useProcessing(shown, () => {
    setBordersChanged(false);
    sermon.reload();
  });
  const editable = shown !== undefined && !processing.processing && shown.status !== "processing";
  useEffect(() => {
    if (processing.processing) {
      preview.current?.pause();
    }
  }, [processing.processing]);
  const markAtCursor = editable ? (edge: Edge) => edges.mark(edge, cursor) : null;
  useMarkKeys(markAtCursor);

  if (sermon.error) {
    return (
      <main className="l1">
        <div className="l1-wrap">
          <p className="note">
            {sermon.error.code === "not_found" ? "Pregação não encontrada." : sermon.error.message}
          </p>
        </div>
      </main>
    );
  }
  if (!shown) {
    return null;
  }
  return (
    <div className="l2">
      <CutsPanel sermon={shown} cuts={cuts} processing={!editable} task={processing.task} />
      <main className="work">
        <div className="l2-bar">
          <span className="spacer" />
          <Saved savedAt={edges.savedAt} />
          <ProcessButton sermon={shown} bordersChanged={bordersChanged} processing={processing} />
        </div>
        <Preview
          key={shown.status === "processed" ? "processed" : "live"}
          ref={preview}
          sermon={shown}
          onTime={setCursor}
        />
        <Transport
          preview={preview}
          cursor={cursor}
          liveDuration={liveDuration}
          onMark={markAtCursor}
          locked={!editable}
        />
        {edges.error && (
          <p className="ferr edge-error" role="alert">
            {edges.error}
          </p>
        )}
        <Timeline
          liveDuration={liveDuration}
          bounds={edges.bounds}
          trimmed={isTrimmed(shown) || edges.moving}
          cursor={cursor}
          onSeek={(liveSeconds) => preview.current?.seek(liveSeconds)}
          onEdgeMove={editable ? moveEdge : null}
          onEdgeRelease={edges.release}
          layers={cutLayers(shown, cuts.data)}
        />
      </main>
    </div>
  );
}

const MARK_KEYS: Record<string, Edge> = { i: "start", o: "end" };

/** I and O bring the borders to the cursor, unless the user is typing or holds a modifier. */
function useMarkKeys(mark: ((edge: Edge) => void) | null) {
  const latest = useRef(mark);
  latest.current = mark;

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const edge = MARK_KEYS[event.key.toLowerCase()];
      if (!edge || !latest.current || event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }
      if (isTyping(event.target)) {
        return;
      }
      latest.current(edge);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
}

function isTyping(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || target.closest("input, textarea, select") !== null)
  );
}
