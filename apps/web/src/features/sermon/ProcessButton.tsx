import { useState } from "react";

import { processSermon, type ApiError } from "../../api/client";
import type { SermonShown, Task } from "../../api/types";
import { useMachineStatus } from "../status/MachineStatus";
import { otherWork } from "../status/StatusBar";
import { isTrimmed } from "./bounds";
import { useTaskEvents } from "./useTaskEvents";

interface ProcessButtonProps {
  sermon: SermonShown;
  /** The borders of the processed sermon were saved in this session (the API does not say
   * whether they changed since the processing). */
  bordersChanged: boolean;
  /** The task ended, done or failed: the sermon changed on the API. */
  onEnd: () => void;
}

/** The level's main action before export: Processar, its progress, and Reprocessar. */
export function ProcessButton({ sermon, bordersChanged, onEnd }: ProcessButtonProps) {
  const [launched, setLaunched] = useState<number>();
  const [endedError, setEndedError] = useState<Task["error"]>(null);
  const [refusal, setRefusal] = useState<ApiError>();
  const running = runningTaskOf(sermon);
  const taskId = launched ?? running?.id;
  const events = useTaskEvents(taskId, (task) => {
    setLaunched(undefined);
    setEndedError(task.error);
    onEnd();
  });
  const busy = otherWork(useMachineStatus().status?.lock, `sermon ${sermon.id}`);
  const failure = endedError ?? (sermon.status === "failed" ? sermon.last_task?.error : null);
  const following = taskId !== undefined;
  const progress = events.task?.progress ?? running?.progress ?? 0;

  function launch(force = false) {
    setEndedError(null);
    setRefusal(undefined);
    processSermon(sermon.id, force).then(
      (task) => setLaunched(task.task_id),
      (error: ApiError) => setRefusal(error),
    );
  }

  if (following) {
    return (
      <div className="l2-action">
        <button className="btn primary" type="button" disabled>
          Processando {Math.round(progress * 100)}%
        </button>
      </div>
    );
  }
  const reprocess = sermon.status === "processed";
  if (reprocess && !bordersChanged) {
    return null;
  }
  const trimmed = isTrimmed(sermon);
  // live_finished is only refreshed by the process itself: it warns, the API's 409 locks.
  const liveOn = refusal?.code === "live_not_finished";
  return (
    <div className="l2-action">
      {failure && !reprocess && (
        <p className="ferr" role="alert">
          O processamento falhou: {failure.message}
        </p>
      )}
      {refusal && (
        <p className="ferr" role="alert">
          {refusal.message}
        </p>
      )}
      {!trimmed && <p className="note">Ajuste as bordas do vídeo para processar.</p>}
      {busy !== undefined && <p className="note">Máquina ocupada: {busy}.</p>}
      {!sermon.live_finished && !liveOn && (
        <p className="note">
          A live pode não ter terminado. Se ainda estiver no ar, processe depois do fim da
          transmissão.
        </p>
      )}
      {reprocess && (
        <p className="note">
          Reprocessar refaz a transcrição e as sugestões; as edições dos cortes se perdem.
        </p>
      )}
      <button
        className="btn primary"
        type="button"
        disabled={!trimmed || busy !== undefined || liveOn}
        onClick={() => launch(reprocess)}
      >
        {reprocess ? "Reprocessar" : "Processar"}
      </button>
    </div>
  );
}

/** The process task of a sermon that was processing when it was loaded. */
function runningTaskOf(sermon: SermonShown): Task | undefined {
  const task = sermon.last_task;
  return sermon.status === "processing" && task?.status === "running" ? task : undefined;
}
