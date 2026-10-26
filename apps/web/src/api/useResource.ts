import { useCallback, useEffect, useRef, useState } from "react";

import type { ApiError } from "./client";

export interface Resource<T> {
  data?: T;
  error?: ApiError;
  reload: () => void;
}

/** Loads ``load()`` on mount and again whenever ``key`` changes or ``reload`` is called. */
export function useResource<T>(load: () => Promise<T>, key: string): Resource<T> {
  const [state, setState] = useState<{ data?: T; error?: ApiError }>({});
  const [version, setVersion] = useState(0);
  const latestLoad = useRef(load);
  latestLoad.current = load;

  useEffect(() => {
    let current = true;
    latestLoad.current().then(
      (data) => current && setState({ data }),
      (error: ApiError) => current && setState({ error }),
    );
    return () => {
      current = false;
    };
  }, [key, version]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);
  return { ...state, reload };
}
