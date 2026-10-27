import type {
  CaptionStyle,
  Criterion,
  Cut,
  CutPreview,
  CutWord,
  ListedCut,
  MachineStatus,
  Me,
  Member,
  Preset,
  Render,
  RenderOptions,
  SermonCreated,
  SermonListItem,
  SermonShown,
  Settings,
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
    borders_changed: false,
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

/** An export of cut 34 running, as ``running_tasks`` lists it. */
export function renderTask(overrides: Partial<Task> = {}): Task {
  return runningTask({
    id: 10,
    kind: "render",
    sermon_id: undefined,
    cut_id: 34,
    progress_message: null,
    ...overrides,
  });
}

/** The machine locked by ``task``, on its cut or else its sermon. */
export function busyMachine(task: Task = runningTask()): MachineStatus {
  return {
    lock: {
      held: true,
      kind: task.kind,
      resource: task.cut_id === undefined ? `sermon ${task.sermon_id ?? 0}` : `cut ${task.cut_id}`,
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
    timeline: { status: "ready", error: null, task_id: null },
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

/** An item of ``GET /api/sermons/12/cuts``, as service/cuts.py ``_listed`` gives it. */
export function listedCut(overrides: Partial<ListedCut> = {}): ListedCut {
  return {
    id: 34,
    sermon_id: 12,
    status: "suggested",
    title: "Fé no deserto",
    text: "Mesmo no deserto, Deus sustenta quem confia nele.",
    duration: 58.4,
    start: 620.5,
    end: 678.9,
    segments: [{ from_word: 1201, to_word: 1230 }],
    range_start_word: 1201,
    range_end_word: 1230,
    source: "llm",
    preset_id: 1,
    edited: false,
    ...overrides,
  };
}

/** The church's caption style, as docs/cli.md §8.6 gives the default. */
export function churchCaption(overrides: Partial<CaptionStyle> = {}): CaptionStyle {
  return {
    enabled: true,
    font: "Open Sans Bold",
    size: 60,
    color: "#FFD600",
    position: "center",
    offset: 50,
    border: 3,
    border_color: "#000000",
    shadow: "soft",
    ...overrides,
  };
}

/** The words of ``shownCut``, in the order the cut plays them, in sermon time. */
export function cutWords(): CutWord[] {
  const word = (word_id: number, text: string, start: number, end: number): CutWord => ({
    word_id,
    text,
    start,
    end,
    corrected: null,
  });
  return [
    word(1105, "Deus", 2.5, 2.9),
    word(1106, "governa.", 2.95, 3.4),
    word(1101, "Irmãos,", 0.3, 0.7),
    word(1102, "graça", 0.8, 1.2),
    word(1103, "paz.", 1.35, 1.9),
  ];
}

/** ``GET /api/cuts/34`` as service/cuts.py ``show_cut`` gives it: the out-of-order example of
 * docs/cli.md §8.3, playing 2.5–3.4, then 0.3–1.2, then 1.35–1.9 of the sermon. */
export function shownCut(overrides: Partial<Cut> = {}): Cut {
  return {
    id: 34,
    sermon_id: 12,
    status: "chosen",
    title: "Fé no deserto",
    text: "Deus governa. Irmãos, graça paz.",
    duration: 2.35,
    segments: [
      { from_word: 1105, to_word: 1106, start: 2.5, end: 3.4, text: "Deus governa." },
      { from_word: 1101, to_word: 1102, start: 0.3, end: 1.2, text: "Irmãos, graça" },
      { from_word: 1103, to_word: 1103, start: 1.35, end: 1.9, text: "paz." },
    ],
    words: cutWords(),
    caption: churchCaption(),
    render_options: defaultRenderOptions(),
    renders: [],
    range_start_word: 1101,
    range_end_word: 1106,
    source: "llm",
    preset_id: 1,
    edited: false,
    ...overrides,
  };
}

/** ``GET /api/cuts/34/preview`` for ``shownCut``, docs/cli.md §8.3. */
export function cutPreview(overrides: Partial<CutPreview> = {}): CutPreview {
  return {
    cut_id: 34,
    duration: 2.35,
    segments: [
      { start: 2.5, end: 3.4, text: "Deus governa.", out_of_order: false },
      { start: 0.3, end: 1.2, text: "Irmãos, graça", out_of_order: true },
      { start: 1.35, end: 1.9, text: "paz.", out_of_order: false },
    ],
    ...overrides,
  };
}

/** The export options of docs/cli.md §8.7 with their defaults, the caption on. */
export function defaultRenderOptions(overrides: Partial<RenderOptions> = {}): RenderOptions {
  return {
    fillers: "remove",
    stammers: "remove",
    pauses: "natural",
    smooth_joins: true,
    fade: true,
    normalize: true,
    caption: true,
    resolution: "1080x1920",
    quality: "high",
    ...overrides,
  };
}

/** An export of cut 34 as ``GET /api/cuts/34/renders`` gives it, docs/cli.md §9. */
export function cutRender(overrides: Partial<Render> = {}): Render {
  return {
    id: 7,
    cut_id: 34,
    duration: 58.4,
    created_at: "2026-10-20T00:23:00-03:00",
    options: defaultRenderOptions(),
    ...overrides,
  };
}

// Shaped as service/settings.py, service/presets.py and service/members.py give them; the
// models, presets and e-mails are fictitious.

export function settings(overrides: Partial<Settings> = {}): Settings {
  return {
    llm_model: "provedor/modelo-teste",
    whisper_model: "large-v3",
    llm_key: "••••7a2c",
    youtube_cookies: false,
    default_preset_id: 1,
    ...overrides,
  };
}

/** Two filters and two values, in the catalog's order. */
export function criteria(): Criterion[] {
  return [
    { id: "triumphalism", name: "Triunfalismo", type: "filter", default_level: "strict" },
    { id: "allegory", name: "Alegoria", type: "filter", default_level: "moderate" },
    { id: "christ_centered", name: "Cristocêntrico", type: "value", default_level: "moderate" },
    { id: "practical", name: "Aplicação prática", type: "value", default_level: "lenient" },
  ];
}

export function preset(overrides: Partial<Preset> = {}): Preset {
  return {
    id: 1,
    name: "Padrão",
    is_default: true,
    levels: {
      triumphalism: "strict",
      allegory: "moderate",
      christ_centered: "moderate",
      practical: "lenient",
    },
    duration_allowed: { min: 40, max: 75 },
    duration_ideal: { min: 55, max: 65 },
    reorder: true,
    protected_words: ["não", "mas"],
    instructions: "",
    created_at: "2026-10-26T19:40:00+00:00",
    updated_at: "2026-10-26T19:40:00+00:00",
    ...overrides,
  };
}

/** The default preset and a second one. */
export function presets(): Preset[] {
  return [
    preset(),
    preset({
      id: 2,
      name: "Curtos",
      is_default: false,
      levels: {
        triumphalism: "lenient",
        allegory: "moderate",
        christ_centered: "moderate",
        practical: "strict",
      },
      duration_allowed: { min: 30, max: 50 },
      duration_ideal: { min: 35, max: 45 },
      reorder: false,
      instructions: "Prefira frases curtas.",
    }),
  ];
}

export function member(overrides: Partial<Member> = {}): Member {
  return {
    email: "assistente@exemplo.org",
    role: "assistant",
    created_at: "2026-10-26T19:40:00-03:00",
    updated_at: "2026-10-26T19:40:00-03:00",
    ...overrides,
  };
}

/** The administrator calling (``admin()``) and an assistant, by e-mail. */
export function team(): Member[] {
  return [member({ email: "admin@exemplo.org", role: "admin" }), member()];
}
