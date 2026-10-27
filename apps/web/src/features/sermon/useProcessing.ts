import { useState } from "react";

import { processSermon, type ApiError } from "../../api/client";
import type { SermonShown, Task } from "../../api/types";
import { useTaskEvents } from "./useTaskEvents";

export interface Processing {
  /** A task of this sermon is being followed: launched here and accepted, or running when
   * the sermon was loaded. */
  processing: boolean;
  /** The launch was asked for and the API has not answered yet. */
  pending: boolean;
  /** The followed task as the last event gave it, or as the sermon's ``last_task``. */
  task?: Task;
  /** Why the API refused the last launch. */
  refusal?: ApiError;
  /** The error of the task that ended in this session, if it failed. */
  endedError: Task["error"];
  /** Asks the API to process the sermon; ``force`` discards the cuts' edits. */
  launch(force?: boolean): void;
}

/** The processing of ``sermon``: launches it, follows its events and tells ``onEnd`` once it
 * is done or failed. */
export function useProcessing(sermon: SermonShown | undefined, onEnd: () => void): Processing {
  const [launched, setLaunched] = useState<number>();
  const [ended, setEnded] = useState<number>();
  const [pending, setPending] = useState(false);
  const [endedError, setEndedError] = useState<Task["error"]>(null);
  const [refusal, setRefusal] = useState<ApiError>();
  const running = sermon && runningTaskOf(sermon);
  const taskId = launched ?? (running?.id !== ended ? running?.id : undefined);
  const events = useTaskEvents(taskId, (task) => {
    setLaunched(undefined);
    setEnded(task.id);
    setEndedError(task.error);
    onEnd();
  });

  function launch(force = false) {
    if (!sermon) {
      return;
    }
    setEndedError(null);
    setRefusal(undefined);
    setPending(true);
    processSermon(sermon.id, force).then(
      (task) => {
        setPending(false);
        setLaunched(task.task_id);
      },
      (error: ApiError) => {
        setPending(false);
        setRefusal(error);
      },
    );
  }

  return {
    processing: taskId !== undefined,
    pending,
    task: events.task ?? (launched === undefined && taskId !== undefined ? running : undefined),
    refusal,
    endedError,
    launch,
  };
}

/** The process task of a sermon that was processing when it was loaded. */
function runningTaskOf(sermon: SermonShown): Task | undefined {
  const task = sermon.last_task;
  return sermon.status === "processing" && task?.status === "running" ? task : undefined;
}
