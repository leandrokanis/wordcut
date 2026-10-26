// Response bodies of the API, as docs/api.md §2 and the core service layer give them.

export type Role = "assistant" | "admin";

export interface Me {
  email: string;
  role: Role;
}

export type SermonStatus = "created" | "trimmed" | "processing" | "processed" | "failed";

export type CutStatus = "suggested" | "chosen" | "discarded";

/** The sermon as service/sermons.py ``_sermon`` gives it. */
export interface Sermon {
  id: number;
  youtube_id: string;
  url: string;
  title: string;
  service_date: string;
  live_duration: number;
  live_finished: boolean;
  status: SermonStatus;
  created_at: string;
}

/** An item of ``GET /api/sermons``: ``duration`` is null until the sermon has borders. */
export interface SermonListItem extends Sermon {
  duration: number | null;
  cut_counts: Record<CutStatus, number>;
}

/** ``POST /api/sermons``: ``created`` is false when the video already had a sermon. */
export interface SermonCreated extends Sermon {
  created: boolean;
}

/** A cut as service/sermons.py ``shown_cut`` gives it inside the sermon. */
export interface SermonCut {
  id: number;
  status: CutStatus;
  title: string;
}

/** ``GET /api/sermons/{id}``, service/sermons.py ``_shown``: the borders are null until the
 * sermon is trimmed, and ``sermon_start``/``sermon_end`` until it is processed. */
export interface SermonShown extends Omit<SermonListItem, "live_duration"> {
  live_duration: number | null;
  live_start: number | null;
  live_end: number | null;
  sermon_start: number | null;
  sermon_end: number | null;
  processed_at: string | null;
  last_task: Task | null;
  cuts: SermonCut[];
  suggestion_error: { code: string; message: string } | null;
}

/** An item of ``GET /api/sermons/{id}/cuts``, service/cuts.py ``_spanned``: ``text`` is the
 * assembled text and ``duration`` the sum of the segments' spans, in seconds; ``start`` and
 * ``end`` are the earliest start and the latest end of the segments, in sermon time. */
export interface ListedCut extends SermonCut {
  sermon_id: number;
  text: string;
  duration: number;
  start: number;
  end: number;
  segments: { from_word: number; to_word: number }[];
  range_start_word: number;
  range_end_word: number;
  source: string;
  preset_id: number | null;
  edited: boolean;
}

/** The 202 of a route that launches a task. */
export interface TaskLaunched {
  task_id: number;
  kind: TaskKind;
  status: "running";
  sermon_id?: number;
  cut_id?: number;
}

/** The fields of ``GET /api/cuts/{id}`` the web reads so far. */
export interface Cut {
  id: number;
  sermon_id: number;
  title: string;
  status: CutStatus;
}

export type TaskKind = "process" | "render" | "suggest";

/** A task as service/tasks.py ``shown_task`` gives it. */
export interface Task {
  id: number;
  kind: TaskKind;
  status: "running" | "succeeded" | "failed";
  sermon_id?: number;
  cut_id?: number;
  progress: number | null;
  progress_message: string | null;
  pid: number | null;
  started_at: string;
  finished_at: string | null;
  error: ErrorBody["error"] | null;
  result: unknown;
}

/** service/status.py: the lock fields are null while the holder has not written them. */
export type Lock =
  | { held: false }
  | {
      held: true;
      kind: string | null;
      resource: string | null;
      pid: number | null;
      started_at: string | null;
      task_id: number | null;
      elapsed_seconds: number | null;
    };

export interface MachineStatus {
  lock: Lock;
  running_tasks: Task[];
}

export interface ErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
