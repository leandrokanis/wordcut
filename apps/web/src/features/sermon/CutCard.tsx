import { useEffect, useRef, type CSSProperties, type RefObject } from "react";

import type { CutStatus, ListedCut } from "../../api/types";
import { formatDuration } from "../../ui/format";
import { DotsIcon } from "../../ui/icons";

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
}: CutCardProps) {
  const discarded = cut.status === "discarded";
  const top = useRef<HTMLDivElement>(null);
  useDismiss(top, menuOpen, onCloseMenu);
  return (
    <li
      className="cc"
      aria-label={cut.title}
      data-discarded={discarded || undefined}
      style={{ "--c": cutColor(number - 1) } as CSSProperties}
    >
      <div className="cc-top" ref={top}>
        <button className="cc-main" type="button" disabled={!onOpen} onClick={onOpen ?? undefined}>
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
            <button className="mi" type="button" role="menuitem" onClick={onToggleDiscard}>
              <b>{discarded ? "Restaurar" : "Descartar"}</b>
            </button>
          </div>
        )}
      </div>
      <p className="cc-quote">{cut.text}</p>
      <div className="cc-meta">
        <span className="mono">{formatDuration(cut.duration)}</span>
        <span className="cc-st">{STATUS_LABELS[cut.status]}</span>
      </div>
    </li>
  );
}

/** Closes an open menu on Escape or on a press outside ``area``, as the prototype's menus do. */
function useDismiss(area: RefObject<HTMLElement>, open: boolean, close: () => void) {
  const latestClose = useRef(close);
  latestClose.current = close;

  useEffect(() => {
    if (!open) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        latestClose.current();
      }
    }
    function onPointerDown(event: PointerEvent) {
      if (!area.current?.contains(event.target as Node)) {
        latestClose.current();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [area, open]);
}
