import type { ReactNode } from "react";

import { CloseIcon } from "../../ui/icons";
import { Saved } from "../../ui/Saved";

export type Tab = "text" | "caption";

const TABS: [Tab, string][] = [
  ["text", "Texto"],
  ["caption", "Legenda"],
];

interface CutSideProps {
  tab: Tab;
  onTab: (tab: Tab) => void;
  /** Changing it shows "Salvo"; 0 means never saved. */
  savedAt: number;
  children: ReactNode;
}

/** The cut's side panel: the Texto and Legenda tabs, the automatic save's "Salvo" and, on
 * Legenda, the button that closes it back to Texto. */
export function CutSide({ tab, onTab, savedAt, children }: CutSideProps) {
  return (
    <aside className="side" aria-label="Painel do corte">
      <div className="side-h">
        <div className="ptabs" role="tablist">
          {TABS.map(([name, label]) => (
            <button
              key={name}
              type="button"
              role="tab"
              id={`tab-${name}`}
              aria-selected={tab === name}
              aria-controls="cut-tabpanel"
              onClick={() => onTab(name)}
            >
              {label}
            </button>
          ))}
        </div>
        <span className="spacer" />
        <Saved savedAt={savedAt} />
        {tab === "caption" && (
          <button
            className="ibtn sm"
            type="button"
            aria-label="Fechar legenda"
            onClick={() => onTab("text")}
          >
            <CloseIcon />
          </button>
        )}
      </div>
      <div className="side-b" role="tabpanel" id="cut-tabpanel" aria-labelledby={`tab-${tab}`}>
        {children}
      </div>
    </aside>
  );
}
