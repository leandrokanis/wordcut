import { useEffect, useRef, useState } from "react";

import { estimateRender, type ApiError } from "../../api/client";
import type { RenderOptions } from "../../api/types";

// plan.md, Decisões técnicas: the estimate waits for the user to stop changing options.
const DEBOUNCE_MS = 300;

export interface Estimate {
  /** The estimated duration of the export, in seconds, once the API answered. */
  duration?: number;
  error?: ApiError;
}

/** The duration the export of the cut with ``options`` would have: asked at once for the first
 * options, then ``DEBOUNCE_MS`` after the last change. */
export function useEstimate(cutId: number, options: RenderOptions): Estimate {
  const [estimate, setEstimate] = useState<Estimate>({});
  const asked = useRef(false);

  useEffect(() => {
    // A replaced estimate is cancelled, and its late answer dropped, so it never overwrites
    // the newer one.
    const call = new AbortController();
    const answer = (estimate: Estimate) => call.signal.aborted || setEstimate(estimate);
    const ask = () => {
      asked.current = true;
      estimateRender(cutId, options, call.signal).then(
        ({ duration }) => answer({ duration }),
        (error: ApiError) => answer({ error }),
      );
    };
    const timer = setTimeout(ask, asked.current ? DEBOUNCE_MS : 0);
    return () => {
      clearTimeout(timer);
      call.abort();
    };
  }, [cutId, options]);

  return estimate;
}
