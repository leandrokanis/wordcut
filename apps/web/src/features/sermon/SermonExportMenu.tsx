import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { sermonVideoUrl } from "../../api/client";
import type { SermonShown } from "../../api/types";
import { formatDuration } from "../../ui/format";
import { useMachineStatus } from "../status/MachineStatus";
import { otherWork } from "../status/StatusBar";
import type { Processing } from "./useProcessing";

interface SermonExportMenuProps {
  sermon: SermonShown;
  processing: Processing;
}

/** The level 2 action of a processed sermon: Exportar opens the prototype's menu, which also
 * offers Reprocessar once the borders differ from the processed ones. */
export function SermonExportMenu({ sermon, processing }: SermonExportMenuProps) {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const busy = otherWork(useMachineStatus().status?.lock, `sermon ${sermon.id}`);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onPointerDown(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function onKeyDown(event: KeyboardEvent) {
    if (!open) {
      return;
    }
    const step = ARROW_STEPS[event.key];
    if (step !== undefined) {
      event.preventDefault();
      focusItem(root.current, step);
    } else if (event.key === "Escape") {
      setOpen(false);
      button.current?.focus();
    }
  }

  return (
    <div ref={root} className="l2-action exp" onKeyDown={onKeyDown}>
      <button
        ref={button}
        className="btn primary"
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls="sermon-export-menu"
        onClick={() => setOpen(!open)}
      >
        Exportar
      </button>
      {open && (
        <div className="menu" id="sermon-export-menu" role="menu">
          <a className="mi" role="menuitem" href={sermonVideoUrl(sermon.id)} download>
            <b>Pregação 16:9</b>
            <small>{videoSummary(sermon)}</small>
          </a>
          {sermon.borders_changed && (
            <button
              className="mi"
              type="button"
              role="menuitem"
              disabled={busy !== undefined || processing.pending}
              onClick={() => {
                setOpen(false);
                processing.launch(true);
              }}
            >
              <b>Reprocessar</b>
              <small>Refaz transcrição e sugestões; as edições dos cortes se perdem</small>
            </button>
          )}
          {busy !== undefined && <p className="mnote">Máquina ocupada: {busy}.</p>}
        </div>
      )}
    </div>
  );
}

const ARROW_STEPS: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 };

/** Moves the focus ``step`` items from the focused one, around the menu's ends. */
function focusItem(root: HTMLElement | null, step: number) {
  const items = Array.from(root?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
  const current = items.indexOf(document.activeElement as HTMLElement);
  const next = current === -1 ? (step > 0 ? 0 : items.length - 1) : current + step;
  items.at(next % items.length)?.focus();
}

/** The prototype's "1080p · duration", or only the resolution while the borders are unknown. */
function videoSummary({ sermon_start: start, sermon_end: end }: SermonShown): string {
  return start === null || end === null ? "1080p" : `1080p · ${formatDuration(end - start)}`;
}
