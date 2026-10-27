import type {
  CaptionStyle,
  Criterion,
  Cut,
  CutPreview,
  ErrorBody,
  FixedWord,
  ListedCut,
  MachineStatus,
  Me,
  Member,
  Preset,
  PresetChange,
  Render,
  RenderEstimate,
  RenderOptions,
  Role,
  Sermon,
  SermonCreated,
  SermonListItem,
  SermonShown,
  Settings,
  SettingsModels,
  TaskLaunched,
  ThumbnailsLayout,
  Waveform,
} from "./types";

/** A failed call: the API's error object, with the HTTP status. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(status: number, { code, message, details }: ErrorBody["error"]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const UNAVAILABLE_MESSAGE = "A API não respondeu. Tente de novo em instantes.";
const NETWORK_MESSAGE = "Sem conexão com a API. Confira a rede e tente de novo.";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(0, { code: "network_error", message: NETWORK_MESSAGE });
  }
  const body = await jsonOf(response);
  if (response.ok && body !== undefined) {
    return body as T;
  }
  if (isErrorBody(body)) {
    throw new ApiError(response.status, body.error);
  }
  throw new ApiError(response.status, { code: "unavailable", message: UNAVAILABLE_MESSAGE });
}

function send<T>(method: "POST" | "PATCH" | "PUT", path: string, body: object): Promise<T> {
  return request(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function post<T>(path: string, body: object): Promise<T> {
  return send("POST", path, body);
}

async function jsonOf(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

function isErrorBody(body: unknown): body is ErrorBody {
  return typeof body === "object" && body !== null && "error" in body;
}

export async function listSermons(): Promise<SermonListItem[]> {
  return (await request<{ items: SermonListItem[] }>("/api/sermons")).items;
}

export function getSermon(id: number): Promise<Sermon> {
  return request(`/api/sermons/${id}`);
}

/** The sermon with its borders, last task and cuts, as the level 2 screen shows it. */
export function showSermon(id: number): Promise<SermonShown> {
  return request(`/api/sermons/${id}`);
}

/** Saves the sermon's borders, in seconds of the live. */
export function trimSermon(id: number, start: number, end: number): Promise<SermonShown> {
  return send("PATCH", `/api/sermons/${id}`, { start, end });
}

/** Launches the processing; ``force`` discards the edits of the cuts of a processed sermon. */
export function processSermon(id: number, force = false): Promise<TaskLaunched> {
  return post(`/api/sermons/${id}/process`, force ? { force } : {});
}

/** Prepares the thumbnails and the waveform of the sermon's timeline again. */
export function prepareSermon(id: number): Promise<TaskLaunched> {
  return post(`/api/sermons/${id}/prepare`, {});
}

export function getThumbnailsLayout(sermonId: number): Promise<ThumbnailsLayout> {
  return request(`/api/sermons/${sermonId}/thumbnails.json`);
}

/** The strip of thumbnails; ``version`` changes once the strip is prepared again. */
export function thumbnailsUrl(sermonId: number, version: number): string {
  return `/api/sermons/${sermonId}/thumbnails?v=${version}`;
}

export function getWaveform(sermonId: number): Promise<Waveform> {
  return request(`/api/sermons/${sermonId}/waveform`);
}

/** The cuts of the sermon in the service's order: the discarded ones last. */
export async function listCuts(sermonId: number): Promise<ListedCut[]> {
  return (await request<{ items: ListedCut[] }>(`/api/sermons/${sermonId}/cuts`)).items;
}

/** Marks the cut ``chosen``; answers the cut as ``GET /api/cuts/{id}`` shows it. */
export function chooseCut(id: number): Promise<Cut> {
  return post(`/api/cuts/${id}/choose`, {});
}

/** Marks the cut ``discarded``, answering as ``chooseCut``. */
export function discardCut(id: number): Promise<Cut> {
  return post(`/api/cuts/${id}/discard`, {});
}

/** Brings a discarded cut back to ``suggested``, answering as ``chooseCut``. */
export function restoreCut(id: number): Promise<Cut> {
  return post(`/api/cuts/${id}/restore`, {});
}

export function getCut(id: number): Promise<Cut> {
  return request(`/api/cuts/${id}`);
}

/** The sequence the level 3 preview plays; never waits for the processing lock. */
export function previewCut(id: number): Promise<CutPreview> {
  return request(`/api/cuts/${id}/preview`);
}

/** Makes ``segments`` what the cut plays, in that order (docs/cli.md §8.10); administrator
 * only. Answers the cut as ``getCut``. */
export function putCutSegments(
  id: number,
  segments: { from_word: number; to_word: number }[],
): Promise<Cut> {
  return send("PUT", `/api/cuts/${id}/segments`, { segments });
}

/** Creates a chosen cut of the sermon over ``{start, end}``, in sermon time, snapped to
 * sentences; answers it as ``GET /api/cuts/{id}`` shows it (docs/cli.md §8.8). */
export function createCut(sermonId: number, range: { start: number; end: number }): Promise<Cut> {
  return post(`/api/sermons/${sermonId}/cuts`, range);
}

/** Resizes the cut's range to ``{start, end}`` or moves it ``{by}`` seconds, in sermon time;
 * answers the cut as ``GET /api/cuts/{id}`` shows it (docs/cli.md §8.9). */
export function patchCutRange(
  id: number,
  change: { start: number; end: number } | { by: number },
): Promise<Cut> {
  return send("PATCH", `/api/cuts/${id}/range`, change);
}

/** Changes only the given fields of the cut's caption style; answers the whole style. */
export function patchCaption(id: number, fields: Partial<CaptionStyle>): Promise<CaptionStyle> {
  return send("PATCH", `/api/cuts/${id}/caption`, fields);
}

/** Brings the cut's caption back to the church's style, switched on. */
export function resetCaption(id: number): Promise<CaptionStyle> {
  return request(`/api/cuts/${id}/caption`, { method: "DELETE" });
}

/** Fixes the spelling of one word of the cut; the original text removes the fix. */
export function fixWord(id: number, wordId: number, text: string): Promise<FixedWord> {
  return send("PUT", `/api/cuts/${id}/words/${wordId}`, { text });
}

// docs/cli.md §8.7: the nine export options, in its order, so the query is always the same.
const RENDER_OPTION_NAMES: (keyof RenderOptions)[] = [
  "fillers",
  "stammers",
  "pauses",
  "smooth_joins",
  "fade",
  "normalize",
  "caption",
  "resolution",
  "quality",
];

/** How long the export with ``options`` would last; saves nothing and takes no lock. The
 * switches go in the query as ``true``/``false`` (docs/api.md §2). */
export function estimateRender(
  id: number,
  options: RenderOptions,
  signal?: AbortSignal,
): Promise<RenderEstimate> {
  const query = new URLSearchParams(
    RENDER_OPTION_NAMES.map((name) => [name, String(options[name])]),
  );
  return request(`/api/cuts/${id}/renders/estimate?${query}`, { signal });
}

/** Launches the ``render`` task; the API saves ``options`` on the cut once it accepts it. */
export function startRender(id: number, options: RenderOptions): Promise<TaskLaunched> {
  const body = Object.fromEntries(RENDER_OPTION_NAMES.map((name) => [name, options[name]]));
  return post(`/api/cuts/${id}/renders`, body);
}

/** The exports of the cut, newest first. */
export async function listRenders(cutId: number): Promise<Render[]> {
  return (await request<{ items: Render[] }>(`/api/cuts/${cutId}/renders`)).items;
}

/** Where the browser plays or downloads the processed 16:9 video, named by the API. */
export function sermonVideoUrl(sermonId: number): string {
  return `/api/sermons/${sermonId}/video`;
}

/** Where the browser downloads the export's video, named by the API. */
export function renderFileUrl(renderId: number): string {
  return `/api/renders/${renderId}/file`;
}

export function createSermon(url: string): Promise<SermonCreated> {
  return post("/api/sermons", { url });
}

export function getMe(): Promise<Me> {
  return request("/api/me");
}

export function getStatus(): Promise<MachineStatus> {
  return request("/api/status");
}

// The administrator's routes of docs/api.md §2 (ADR-0021: the e-mail goes only in the body).

export function getSettings(): Promise<Settings> {
  return request("/api/settings");
}

/** Saves the models given; a blank one is refused with 400. */
export function patchSettings(models: SettingsModels): Promise<Settings> {
  return send("PATCH", "/api/settings", models);
}

/** Stores the LLM key; the answer brings it back only masked. */
export function putLlmKey(value: string): Promise<Settings> {
  return send("PUT", "/api/settings/llm-key", { value });
}

/** Stores the YouTube cookies (Netscape ``cookies.txt``); the answer tells only that they exist. */
export function putYoutubeCookies(value: string): Promise<Settings> {
  return send("PUT", "/api/settings/youtube-cookies", { value });
}

export async function listCriteria(): Promise<Criterion[]> {
  return (await request<{ items: Criterion[] }>("/api/criteria")).items;
}

export async function listPresets(): Promise<Preset[]> {
  return (await request<{ items: Preset[] }>("/api/presets")).items;
}

/** A new preset, a copy of ``fromId``; never the default. */
export function createPreset(name: string, fromId: number): Promise<Preset> {
  return post("/api/presets", { name, from_id: fromId });
}

export function patchPreset(id: number, change: PresetChange): Promise<Preset> {
  return send("PATCH", `/api/presets/${id}`, change);
}

export function setDefaultPreset(id: number): Promise<Preset> {
  return post(`/api/presets/${id}/set-default`, {});
}

/** The default preset cannot be deleted: 409 ``default_preset``. */
export function deletePreset(id: number): Promise<{ id: number; deleted: true }> {
  return request(`/api/presets/${id}`, { method: "DELETE" });
}

export async function listMembers(): Promise<Member[]> {
  return (await request<{ items: Member[] }>("/api/members")).items;
}

export function addMember(email: string, role: Role): Promise<Member> {
  return post("/api/members", { email, role });
}

/** 409 ``last_admin`` when it would leave the team without an administrator. */
export function setMemberRole(email: string, role: Role): Promise<Member> {
  return post("/api/members/set-role", { email, role });
}

/** 409 ``last_admin`` when it would leave the team without an administrator. */
export function removeMember(email: string): Promise<{ email: string; removed: true }> {
  return post("/api/members/remove", { email });
}
