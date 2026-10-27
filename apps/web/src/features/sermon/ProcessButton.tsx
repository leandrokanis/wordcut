import type { SermonShown } from "../../api/types";
import { useMachineStatus } from "../status/MachineStatus";
import { otherWork } from "../status/StatusBar";
import { isTrimmed } from "./bounds";
import { progressLabel } from "./stage";
import type { Processing } from "./useProcessing";

interface ProcessButtonProps {
  sermon: SermonShown;
  /** The borders of the processed sermon were saved in this session (the API does not say
   * whether they changed since the processing). */
  bordersChanged: boolean;
  processing: Processing;
}

/** The level's main action before export: Processar, its progress, and Reprocessar. */
export function ProcessButton({ sermon, bordersChanged, processing }: ProcessButtonProps) {
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
        disabled={!trimmed || busy !== undefined || liveOn || processing.pending}
        onClick={() => launch(reprocess)}
      >
        {reprocess ? "Reprocessar" : "Processar"}
      </button>
    </div>
  );
}
