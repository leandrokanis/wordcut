import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  chooseCut,
  discardCut,
  listCuts,
  restoreCut,
  type ApiError,
} from "../../api/client";
import type { ListedCut, SermonShown } from "../../api/types";
import { useResource, type Resource } from "../../api/useResource";
import { CutCard } from "./CutCard";

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
}

/** Level 2's side panel: the cuts of the sermon, in the service's order. */
export function CutsPanel({ sermon, cuts }: CutsPanelProps) {
  return (
    <aside className="side" aria-label="Cortes">
      <div className="side-h">
        <h2>Cortes</h2>
      </div>
      <div className="side-b">
        <PanelBody sermon={sermon} cuts={cuts} />
      </div>
    </aside>
  );
}

function PanelBody({ sermon, cuts }: CutsPanelProps) {
  const [menuOf, setMenuOf] = useState<number>();
  const [failure, setFailure] = useState<ApiError>();
  const navigate = useNavigate();

  // Opening a suggested cut marks it chosen (1.1.e); a discarded one is restored first.
  function open(cut: ListedCut) {
    const chosen = cut.status === "suggested" ? chooseCut(cut.id) : Promise.resolve();
    setFailure(undefined);
    chosen.then(
      () => navigate(`/cuts/${cut.id}`),
      (error: ApiError) => setFailure(error),
    );
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
