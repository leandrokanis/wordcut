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

/** An item of ``GET /api/sermons``: ``duration`` is null until the sermon has borders;
 * ``borders_changed`` is true when the sermon is processed and its borders differ from the
 * ones the processing used. */
export interface SermonListItem extends Sermon {
  duration: number | null;
  borders_changed: boolean;
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

/** A segment of ``GET /api/cuts/{id}``, docs/cli.md §8.2: times in sermon time. */
export interface CutSegment {
  from_word: number;
  to_word: number;
  start: number;
  end: number;
  text: string;
}

/** A word of the cut: ``text`` is the original, ``corrected`` the cut's spelling fix. */
export interface CutWord {
  word_id: number;
  text: string;
  start: number;
  end: number;
  corrected: string | null;
}

export type CaptionPosition = "top" | "center" | "bottom";

export type CaptionShadow = "none" | "soft" | "strong";

/** The caption style of ``cut caption``, docs/cli.md §8.6: ``size`` and ``border`` in px of
 * the 1080×1920 frame, ``offset`` the height of the caption's centre in % of the frame. */
export interface CaptionStyle {
  enabled: boolean;
  font: string;
  size: number;
  color: string;
  position: CaptionPosition;
  offset: number;
  border: number;
  border_color: string;
  shadow: CaptionShadow;
}

/** The nine choices of an export, docs/cli.md §8.7, in its order: ``caption`` is the
 * ``enabled`` of the cut's caption style. */
export interface RenderOptions {
  fillers: "remove" | "keep";
  stammers: "remove" | "keep";
  pauses: "original" | "natural" | "short";
  smooth_joins: boolean;
  fade: boolean;
  normalize: boolean;
  caption: boolean;
  resolution: "1080x1920" | "720x1280";
  quality: "high" | "small";
}

/** An export as ``render show`` gives it, docs/cli.md §9, without ``path``: the web downloads
 * it by ``GET /api/renders/{id}/file``. ``duration`` in seconds. */
export interface Render {
  id: number;
  cut_id: number;
  duration: number;
  created_at: string;
  options: RenderOptions;
}

/** ``GET /api/cuts/{id}/renders/estimate``: the estimated duration, in seconds. */
export interface RenderEstimate {
  duration: number;
  options: RenderOptions;
}

/** ``GET /api/cuts/{id}``, service/cuts.py ``show_cut``: ``renders`` oldest first. */
export interface Cut extends Omit<ListedCut, "start" | "end" | "segments"> {
  segments: CutSegment[];
  words: CutWord[];
  caption: CaptionStyle;
  render_options: RenderOptions;
  renders: Render[];
}

/** A segment of ``GET /api/cuts/{id}/preview``, in the order the cut plays it. */
export interface PreviewSegment {
  start: number;
  end: number;
  text: string;
  out_of_order: boolean;
}

/** ``GET /api/cuts/{id}/preview``, docs/cli.md §8.3. */
export interface CutPreview {
  cut_id: number;
  duration: number;
  segments: PreviewSegment[];
}

/** ``PUT /api/cuts/{id}/words/{word_id}``, docs/cli.md §8.5. */
export interface FixedWord extends CutWord {
  cut_id: number;
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

/** service/settings.py show_settings: the key comes masked and the cookies only as presence. */
export interface Settings {
  llm_model: string | null;
  whisper_model: string;
  /** ``"••••"`` and the key's last characters; null without a key. */
  llm_key: string | null;
  youtube_cookies: boolean;
  default_preset_id: number;
}

export type SettingsModels = Partial<Pick<Settings, "llm_model" | "whisper_model">>;

export type Level = "lenient" | "moderate" | "strict";

/** docs/cli.md §11.2: a filter or value of the code, never with its prompt text. */
export interface Criterion {
  id: string;
  name: string;
  type: "filter" | "value";
  default_level: Level;
}

/** Seconds, both ends included. */
export interface SecondsRange {
  min: number;
  max: number;
}

/** docs/cli.md §11.3: ``levels`` has every criterion of the code. */
export interface Preset {
  id: number;
  name: string;
  is_default: boolean;
  levels: Record<string, Level>;
  duration_allowed: SecondsRange;
  duration_ideal: SecondsRange;
  reorder: boolean;
  protected_words: string[];
  instructions: string;
  created_at: string;
  updated_at: string;
}

/** What ``PATCH /api/presets/{id}`` takes; ``levels`` changes only the criteria it names. */
export type PresetChange = Partial<
  Pick<
    Preset,
    | "name"
    | "levels"
    | "duration_allowed"
    | "duration_ideal"
    | "reorder"
    | "protected_words"
    | "instructions"
  >
>;

/** docs/cli.md §12: a member is only an e-mail and a role. */
export interface Member {
  email: string;
  role: Role;
  created_at: string;
  updated_at: string;
}
