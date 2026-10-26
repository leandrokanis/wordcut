import { useState } from "react";

import { getCut, listRenders } from "../../api/client";
import type { Cut, Render, RenderOptions } from "../../api/types";

export interface CutExports {
  /** The options the next export uses, as the API last gave them. */
  options: RenderOptions;
  /** The cut's exports, newest first. */
  renders: Render[];
  /** Reads both again, after an export saved its options and registered itself. */
  refresh(): void;
}

/** The export options and the exports of ``cut``, starting from ``GET /api/cuts/{id}``. */
export function useCutExports(cut: Cut): CutExports {
  const [options, setOptions] = useState(cut.render_options);
  const [renders, setRenders] = useState(() => [...cut.renders].reverse());

  function refresh() {
    getCut(cut.id).then(({ render_options }) => setOptions(render_options), keepShown);
    listRenders(cut.id).then(setRenders, keepShown);
  }

  return { options, renders, refresh };
}

/** A failed re-read keeps what is shown; the next export reads it again. */
function keepShown() {}
