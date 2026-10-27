import type { SermonShown } from "../../api/types";
import { useMachineStatus } from "../status/MachineStatus";
import { otherWork } from "../status/StatusBar";
import { isTrimmed } from "./bounds";
import { progressLabel } from "./stage";
import type { Processing } from "./useProcessing";

interface ProcessButtonProps {
  sermon: SermonShown;
  processing: Processing;
}

/** The level's main action before export: Processar and its progress. A processed sermon is
 * reprocessed from the Exportar menu; here it only shows why the API refused that. */
export function ProcessButton({ sermon, processing }: ProcessButtonProps) {
  const { refusal, endedError, launch } = processing;
  const busy = otherWork(useMachineStatus().status?.lock, `sermon ${sermon.id}`);
  const failure = endedError ?? (sermon.status === "failed" ? sermon.last_task?.error : null);

  if (processing.processing) {
    return (
      <div className="l2-action">
        <button className="btn primary" type="button" disabled>
          {progressLabel(processing.task)}
        </button>
      </div>
    );
  }
  if (sermon.status === "processed") {
    return refusal ? (
      <div className="l2-action">
        <p className="ferr" role="alert">
          {refusal.message}
        </p>
      </div>
    ) : null;
  }
  const trimmed = isTrimmed(sermon);
  // live_finished is only refreshed by the process itself: it warns, the API's 409 locks.
  const liveOn = refusal?.code === "live_not_finished";
  return (
    <div className="l2-action">
      {failure && (
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
      <button
        className="btn primary"
        type="button"
        disabled={!trimmed || busy !== undefined || liveOn || processing.pending}
        onClick={() => launch()}
      >
        Processar
      </button>
    </div>
  );
}
