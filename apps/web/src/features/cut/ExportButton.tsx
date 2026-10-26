import { useState } from "react";

import { startRender, type ApiError } from "../../api/client";
import type { Cut, MachineStatus, RenderOptions, Task } from "../../api/types";
import { useTaskEvents } from "../sermon/useTaskEvents";
import { useMachineStatus } from "../status/MachineStatus";
import { lockedWork } from "../status/StatusBar";
import { ExportDialog } from "./ExportDialog";
import { RendersList } from "./RendersList";
import { useCutExports } from "./useCutExports";

interface ExportButtonProps {
  cut: Cut;
  /** Whether the caption is on, as the Legenda tab has it now. */
  captionOn: boolean;
  /** A change of the caption or of the spelling is still being saved. */
  saving: boolean;
  /** The API accepted an export that switched the caption ``on`` or off on the cut. */
  onCaptionSaved: (on: boolean) => void;
}

/** The level 3 action: Exportar opens the prototype's menu, with "Exportar 9:16…". */
export function ExportButton({ cut, captionOn, saving, onCaptionSaved }: ExportButtonProps) {
  const exports = useCutExports(cut);
  const status = useMachineStatus().status;
  // The polled status lags behind the task's events: a task they ended is not followed again.
  const [ended, setEnded] = useState<number[]>([]);
  const busy = lockingWork(status, ended);
  const running = ownExport(status, cut.id, ended);
  const [menuOpen, setMenuOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [launched, setLaunched] = useState<number>();
  const [failure, setFailure] = useState<Task["error"]>(null);
  const [sending, setSending] = useState(false);
  const [refusal, setRefusal] = useState<string>();
  const taskId = launched ?? running?.id;
  const events = useTaskEvents(taskId, (task) => {
    setLaunched(undefined);
    setEnded((current) => [...current, task.id]);
    if (task.status === "failed") {
      setFailure(task.error);
    } else {
      exports.refresh();
    }
  });

  function launch(chosen: RenderOptions) {
    setFailure(null);
    setRefusal(undefined);
    setSending(true);
    startRender(cut.id, chosen).then(
      (task) => {
        onCaptionSaved(chosen.caption);
        setSending(false);
        setDialogOpen(false);
        setLaunched(task.task_id);
      },
      (error: ApiError) => {
        setSending(false);
        setRefusal(error.message);
      },
    );
  }

  function openDialog() {
    setMenuOpen(false);
    setRefusal(undefined);
    setDialogOpen(true);
  }

  if (taskId !== undefined) {
    const progress = events.task?.progress ?? running?.progress ?? 0;
    return (
      <div className="l2-action exp">
        <button className="btn primary" type="button" disabled>
          Exportando {Math.round(progress * 100)}%
        </button>
      </div>
    );
  }

  return (
    <div className="l2-action exp">
      {failure && (
        <p className="ferr" role="alert">
          A exportação falhou: {failure.message}
        </p>
      )}
      <button
        className="btn primary"
        type="button"
        aria-expanded={menuOpen}
        aria-controls="export-menu"
        onClick={() => setMenuOpen(!menuOpen)}
      >
        Exportar
      </button>
      {menuOpen && (
        <div className="menu" id="export-menu">
          <button className="mi" type="button" onClick={openDialog}>
            <b>Exportar 9:16…</b>
            <small>Escolher limpeza, edição, áudio e vídeo</small>
          </button>
          {busy !== undefined && <p className="mnote">Máquina ocupada: {busy}.</p>}
          <RendersList renders={exports.renders} />
        </div>
      )}
      {dialogOpen && (
        <ExportDialog
          cutId={cut.id}
          title={cut.title}
          initial={{ ...exports.options, caption: captionOn }}
          onClose={() => setDialogOpen(false)}
          busy={busy}
          sending={sending}
          saving={saving}
          refusal={refusal}
          onExport={launch}
        />
      )}
    </div>
  );
}

/** The export of the cut the machine runs, unless its events already ended it. */
function ownExport(
  status: MachineStatus | undefined,
  cutId: number,
  ended: number[],
): Task | undefined {
  return status?.running_tasks.find(
    (task) => task.kind === "render" && task.cut_id === cutId && !ended.includes(task.id),
  );
}

/** What holds the machine, even for this cut, unless the task's events already ended it. */
function lockingWork(status: MachineStatus | undefined, ended: number[]): string | undefined {
  const lock = status?.lock;
  if (!lock?.held || (lock.task_id !== null && ended.includes(lock.task_id))) {
    return undefined;
  }
  return lockedWork(lock) || "outra tarefa";
}
