import type {
  MachineStatus,
  Me,
  SermonCreated,
  SermonListItem,
  SermonShown,
  Task,
} from "../api/types";

// Bodies shaped as packages/core service/sermons.py, service/status.py and service/tasks.py
// give them; the data is fictitious.

export function listedSermon(overrides: Partial<SermonListItem> = {}): SermonListItem {
  return {
    id: 12,
    youtube_id: "abcdefghijk",
    url: "https://www.youtube.com/watch?v=abcdefghijk",
    title: "Culto de domingo",
    service_date: "2026-10-18",
    live_duration: 7080,
    live_finished: true,
    status: "processed",
    created_at: "2026-10-18T21:10:00-03:00",
    duration: 2475,
    cut_counts: { suggested: 3, chosen: 1, discarded: 0 },
    ...overrides,
  };
}

export function createdSermon(overrides: Partial<SermonCreated> = {}): SermonCreated {
  return {
    id: 13,
    youtube_id: "lmnopqrstuv",
    url: "https://www.youtube.com/watch?v=lmnopqrstuv",
    title: "Culto de quarta",
    service_date: "2026-10-21",
    live_duration: 5430,
    live_finished: true,
    status: "created",
    created_at: "2026-10-26T10:00:00-03:00",
    created: true,
    ...overrides,
  };
}

export function admin(): Me {
  return { email: "admin@exemplo.org", role: "admin" };
}

export function assistant(): Me {
  return { email: "assistente@exemplo.org", role: "assistant" };
}

export function idleMachine(): MachineStatus {
  return { lock: { held: false }, running_tasks: [] };
}

export function runningTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 9,
    kind: "process",
    status: "running",
    sermon_id: 12,
    progress: 0.35,
    progress_message: "transcrevendo",
    pid: 4242,
    started_at: "2026-10-26T10:00:00-03:00",
    finished_at: null,
    error: null,
    result: null,
    ...overrides,
  };
}

export function busyMachine(task: Task = runningTask()): MachineStatus {
  return {
    lock: {
      held: true,
      kind: task.kind,
      resource: `sermon ${task.sermon_id ?? 0}`,
      pid: task.pid,
      started_at: task.started_at,
      task_id: task.id,
      elapsed_seconds: 185,
    },
    running_tasks: [task],
  };
}

/** A trimmed sermon as ``GET /api/sermons/{id}`` gives it, not processed yet. */
export function shownSermon(overrides: Partial<SermonShown> = {}): SermonShown {
  return {
    ...listedSermon({ status: "trimmed", duration: 2475, cut_counts: noCuts() }),
    live_start: 1800,
    live_end: 4275,
    sermon_start: null,
    sermon_end: null,
    processed_at: null,
    last_task: null,
    cuts: [],
    suggestion_error: null,
    ...overrides,
  };
}

/** ``shownSermon`` after processing: the borders were fitted to the words. */
export function processedSermon(overrides: Partial<SermonShown> = {}): SermonShown {
  return shownSermon({
    status: "processed",
    sermon_start: 1801.2,
    sermon_end: 4274.6,
    processed_at: "2026-10-18T22:30:00-03:00",
    last_task: runningTask({
      status: "succeeded",
      progress: 1,
      progress_message: null,
      finished_at: "2026-10-18T22:30:00-03:00",
    }),
    ...overrides,
  });
}

function noCuts(): SermonListItem["cut_counts"] {
  return { suggested: 0, chosen: 0, discarded: 0 };
}
