import { useEffect, useRef, useState } from "react";

import type { Task } from "../../api/types";

export interface TaskEvents {
  /** The task as the last event gave it. */
  task?: Task;
}

/** Follows a task by its events (SSE, docs/api.md §3) until ``done`` or ``failed``, and tells
 * ``onEnd`` the finished task. */
export function useTaskEvents(
  taskId: number | undefined,
  onEnd: (task: Task) => void,
): TaskEvents {
  // Kept with its id, so a new task does not show the last one's progress.
  const [last, setLast] = useState<{ id: number; task: Task }>();
  const tellEnd = useRef(onEnd);
  tellEnd.current = onEnd;

  useEffect(() => {
    if (taskId === undefined) {
      return;
    }
    const source = new EventSource(`/api/tasks/${taskId}/events`);
    const read = (event: MessageEvent<string>): Task => JSON.parse(event.data);
    const setTask = (task: Task) => setLast({ id: taskId, task });
    source.addEventListener("progress", (event) => setTask(read(event)));
    // docs/api.md §3: the client MUST close on the final event, or the browser reconnects and
    // gets it again.
    const end = (event: MessageEvent<string>) => {
      source.close();
      const ended = read(event);
      setTask(ended);
      tellEnd.current(ended);
    };
    source.addEventListener("done", end);
    source.addEventListener("failed", end);
    return () => source.close();
  }, [taskId]);

  return { task: last?.id === taskId ? last?.task : undefined };
}
