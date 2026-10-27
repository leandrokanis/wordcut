import { useRef, useState, type CSSProperties } from "react";

import { listRenders } from "../../api/client";
import type { CutStatus, ListedCut } from "../../api/types";
import { useResource } from "../../api/useResource";
import { formatDuration } from "../../ui/format";
import { DotsIcon } from "../../ui/icons";
import { useDismiss } from "../../ui/useDismiss";

const STATUS_LABELS: Record<CutStatus, string> = {
  suggested: "Sugerido",
  chosen: "Escolhido",
  discarded: "Descartado",
};

// The prototype's cut colors, given by the cut's place in the list.
const CUT_COLORS = ["#7b93ff", "#4cc38a", "#f0a43a", "#d77bff"];

/** The color of the cut at ``index`` of the list, the same on its card and on its layer. */
export function cutColor(index: number): string {
  return CUT_COLORS[index % CUT_COLORS.length];
}

interface CutCardProps {
  cut: ListedCut;
  /** The cut's place in the list, from 1. */
  number: number;
  /** Opens the cut's level; null when the cut cannot be opened. */
  onOpen: (() => void) | null;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onCloseMenu: () => void;
  /** Discards the cut, or restores it when it is discarded. */
  onToggleDiscard: () => void;
  /** Deletes the cut once confirmed; null when the caller may not (1.2.b.1). */
  onDelete: (() => void) | null;
}

/** One cut in the panel: its number, title, assembled text, duration and state. A discarded
 * cut is marked ``data-discarded``. */
export function CutCard({
  cut,
  number,
  onOpen,
  menuOpen,
  onToggleMenu,
  onCloseMenu,
  onToggleDiscard,
  onDelete,
}: CutCardProps) {
  const discarded = cut.status === "discarded";
  const top = useRef<HTMLDivElement>(null);
  useDismiss(top, menuOpen, onCloseMenu);
  const [confirming, setConfirming] = useState(false);

  function askToDelete() {
    onCloseMenu();
    setConfirming(true);
  }
  return (
    <li
      className="cc"
      aria-label={cut.title}
      data-discarded={discarded || undefined}
      style={{ "--c": cutColor(number - 1) } as CSSProperties}
    >
      <div className="cc-top" ref={top}>
        <button
          className="cc-main"
          type="button"
          disabled={!onOpen}
          onClick={onOpen ?? undefined}
        >
          <i className="rnum">{number}</i>
          <span className="cc-title">{cut.title}</span>
        </button>
        <button
          className="ibtn sm"
          type="button"
          aria-label="Mais ações"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          onClick={onToggleMenu}
        >
          <DotsIcon />
        </button>
        {menuOpen && (
          <div className="cmenu" role="menu">
            <button
              className="mi"
              type="button"
              role="menuitem"
              onClick={onToggleDiscard}
            >
              <b>{discarded ? "Restaurar" : "Descartar"}</b>
            </button>
            {onDelete && (
              <button
                className="mi danger"
                type="button"
                role="menuitem"
                onClick={askToDelete}
              >
                <b>Apagar</b>
              </button>
            )}
          </div>
        )}
      </div>
      {confirming && onDelete && (
        <DeleteConfirmation
          cutId={cut.id}
          onConfirm={() => {
            setConfirming(false);
            onDelete();
          }}
          onCancel={() => setConfirming(false)}
        />
      )}
      <p className="cc-quote">{cut.text}</p>
      <div className="cc-meta">
        <span className="mono">{formatDuration(cut.duration)}</span>
        <span className="cc-st">{STATUS_LABELS[cut.status]}</span>
      </div>
    </li>
  );
}

interface DeleteConfirmationProps {
  cutId: number;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Asks before deleting the cut, saying how many exports go with it, as the sermon's card asks
 * (plan of 1.2.b.1, gap L6); it waits for the count before offering Apagar. */
function DeleteConfirmation({
  cutId,
  onConfirm,
  onCancel,
}: DeleteConfirmationProps) {
  const exports = useResource(() => listRenders(cutId), `renders:${cutId}`);
  if (!exports.data && !exports.error) {
    return null;
  }
  return (
    <div className="cc-confirm">
      <span>{question(exports.data?.length)}</span>
      <div className="row">
        <button className="btn sm danger" type="button" onClick={onConfirm}>
          Apagar
        </button>
        <button className="btn sm ghost" type="button" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

/** The question for a cut with ``exports`` exports; unknown when they could not be listed. */
function question(exports: number | undefined): string {
  if (exports === undefined) {
    return "Apagar o corte e as exportações dele?";
  }
  if (exports === 0) {
    return "Apagar o corte?";
  }
  return `Apagar o corte e ${exports} ${exports === 1 ? "exportação" : "exportações"}?`;
}
