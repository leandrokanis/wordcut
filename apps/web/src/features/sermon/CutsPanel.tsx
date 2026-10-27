import { useState } from "react";
import { useNavigate, type NavigateFunction } from "react-router-dom";

import {
  chooseCut,
  discardCut,
  listCuts,
  restoreCut,
  type ApiError,
} from "../../api/client";
import type { ListedCut, SermonShown, Task } from "../../api/types";
import { useResource, type Resource } from "../../api/useResource";
import { CutCard } from "./CutCard";
import { processSteps } from "./stage";

/** The cuts of the sermon, asked for again whenever the sermon is processed anew. */
export function useSermonCuts(sermon: SermonShown | undefined): Resource<ListedCut[]> {
  const processed = sermon?.status === "processed";
  return useResource(
    () => (processed && sermon ? listCuts(sermon.id) : Promise.resolve([])),
    `cuts:${sermon?.id}:${sermon?.status}:${sermon?.processed_at}`,
  );
}

interface CutsPanelProps {
  sermon: SermonShown;
  cuts: Resource<ListedCut[]>;
  /** The sermon is processing: the panel shows the steps of ``task`` instead of the cuts. */
  processing: boolean;
  task?: Task;
}

/** Level 2's side panel: the cuts of the sermon, in the service's order. */
export function CutsPanel({ sermon, cuts, processing, task }: CutsPanelProps) {
  return (
    <aside className="side" aria-label="Cortes">
      <div className="side-h">
        <h2>Cortes</h2>
      </div>
      <div className="side-b">
        {processing ? <ProcessingSteps task={task} /> : <PanelBody sermon={sermon} cuts={cuts} />}
      </div>
    </aside>
  );
}

/** The steps of the processing, after docs/prototype/wordcut.html (stepsHtml). */
function ProcessingSteps({ task }: { task?: Task }) {
  return (
    <div role="status" aria-label="Processando a pregação">
      <ol className="steps">
        {processSteps(task).map((step) => {
          const percent = Math.round(step.progress * 100);
          return (
            <li
              key={step.name}
              className={`step ${step.state === "running" ? "run" : step.state === "done" ? "done" : ""}`}
              aria-current={step.state === "running" ? "step" : undefined}
            >
              <span className="ic" aria-hidden="true">
                {step.state === "done" ? "✓" : ""}
              </span>
              <span>{step.name}</span>
              <span className="tc">{percent}%</span>
              <span
                className="progress"
                role="progressbar"
                aria-label={step.name}
                aria-valuenow={percent}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <i style={{ width: `${percent}%` }} />
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/** Goes to the cut's level; opening a suggested cut marks it chosen first (1.1.e). */
export function openCut(
  cut: { id: number; status: ListedCut["status"] },
  navigate: NavigateFunction,
): Promise<void> {
  const chosen = cut.status === "suggested" ? chooseCut(cut.id) : Promise.resolve();
  return chosen.then(() => navigate(`/cuts/${cut.id}`));
}

function PanelBody({ sermon, cuts }: Pick<CutsPanelProps, "sermon" | "cuts">) {
  const [menuOf, setMenuOf] = useState<number>();
  const [failure, setFailure] = useState<ApiError>();
  const navigate = useNavigate();

  function open(cut: ListedCut) {
    setFailure(undefined);
    openCut(cut, navigate).catch((error: ApiError) => setFailure(error));
  }

  // The list is asked for again rather than reordered here: the order is the service's.
  function toggleDiscard(cut: ListedCut) {
    setMenuOf(undefined);
    setFailure(undefined);
    const change = cut.status === "discarded" ? restoreCut : discardCut;
    change(cut.id).then(cuts.reload, (error: ApiError) => setFailure(error));
  }

  if (sermon.status !== "processed") {
    return <EmptyPanel message="Os cortes aparecem depois do processamento." />;
  }
  if (cuts.error) {
    return (
      <p className="ferr" role="alert">
        {cuts.error.message}
      </p>
    );
  }
  if (!cuts.data) {
    return null;
  }
  return (
    <>
      {failure && (
        <p className="ferr" role="alert">
          {failure.message}
        </p>
      )}
      {sermon.suggestion_error && (
        <p className="ferr" role="alert">
          A sugestão de cortes falhou: {sermon.suggestion_error.message}
        </p>
      )}
      {cuts.data.length === 0 && !sermon.suggestion_error && (
        <EmptyPanel message="Nenhum corte nesta pregação." />
      )}
      {cuts.data.length > 0 && (
        <ul className="cclist">
          {cuts.data.map((cut, index) => (
            <CutCard
              key={cut.id}
              cut={cut}
              number={index + 1}
              onOpen={cut.status === "discarded" ? null : () => open(cut)}
              menuOpen={menuOf === cut.id}
              onToggleMenu={() => setMenuOf(menuOf === cut.id ? undefined : cut.id)}
              onCloseMenu={() => setMenuOf(undefined)}
              onToggleDiscard={() => toggleDiscard(cut)}
            />
          ))}
        </ul>
      )}
    </>
  );
}

function EmptyPanel({ message }: { message: string }) {
  return (
    <div className="emptyp">
      <p>{message}</p>
    </div>
  );
}
