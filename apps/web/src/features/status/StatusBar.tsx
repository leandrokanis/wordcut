import type { Lock, MachineStatus } from "../../api/types";
import { useMachineStatus } from "./MachineStatus";

const KIND_LABELS: Record<string, string> = {
  process: "processando",
  render: "exportando",
  suggest: "sugerindo cortes",
};

const RESOURCE_LABELS: Record<string, string> = {
  sermon: "a pregação",
  cut: "o corte",
};

export function StatusBar() {
  const { status, error } = useMachineStatus();
  return (
    <footer className="sbar">
      {status && <MachineSummary status={status} />}
      {error && (
        <span className="sb-i">
          <span className="dot off" />
          Estado da máquina indisponível
        </span>
      )}
    </footer>
  );
}

function MachineSummary({ status: { lock, running_tasks } }: { status: MachineStatus }) {
  if (!lock.held) {
    const suggestion = running_tasks.find((task) => task.kind === "suggest");
    return (
      <span className="sb-i">
        <span className="dot" />
        Máquina livre
        {suggestion && ` · ${KIND_LABELS.suggest} da pregação ${suggestion.sermon_id}`}
      </span>
    );
  }
  const progress = running_tasks.find((task) => task.id === lock.task_id)?.progress;
  return (
    <>
      <span className="sb-i">
        <span className="dot busy" />
        {busyText(lock)}
      </span>
      {progress != null && <Progress fraction={progress} />}
    </>
  );
}

function busyText(lock: Extract<Lock, { held: true }>): string {
  const what = [KIND_LABELS[lock.kind ?? ""] ?? lock.kind, resourceText(lock.resource)]
    .filter(Boolean)
    .join(" ");
  const since =
    lock.elapsed_seconds == null
      ? ""
      : ` · há ${Math.max(1, Math.round(lock.elapsed_seconds / 60))} min`;
  return `Ocupada${what ? `: ${what}` : ""}${since}`;
}

function resourceText(resource: string | null): string {
  const [type, id] = (resource ?? "").split(" ");
  return RESOURCE_LABELS[type] ? `${RESOURCE_LABELS[type]} ${id}` : (resource ?? "");
}

function Progress({ fraction }: { fraction: number }) {
  const percent = Math.round(fraction * 100);
  return (
    <>
      <span
        className="sb-prog"
        role="progressbar"
        aria-label="Progresso da tarefa"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <i style={{ width: `${percent}%` }} />
      </span>
      <span className="mono">{percent}%</span>
    </>
  );
}
