import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { getStatus, type ApiError } from "../../api/client";
import type { MachineStatus } from "../../api/types";

export interface MachineState {
  status?: MachineStatus;
  error?: ApiError;
}

const POLL_MS = 3000;

const MachineStatusContext = createContext<MachineState>({});

/** Polls GET /api/status for the screens below it; the task events (SSE) come in item 22. */
export function MachineStatusProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<MachineState>({});

  useEffect(() => {
    let mounted = true;
    const poll = () =>
      getStatus().then(
        (status) => mounted && setState({ status }),
        (error: ApiError) => mounted && setState({ error }),
      );
    poll();
    const timer = setInterval(poll, POLL_MS);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  return <MachineStatusContext.Provider value={state}>{children}</MachineStatusContext.Provider>;
}

export function useMachineStatus(): MachineState {
  return useContext(MachineStatusContext);
}
