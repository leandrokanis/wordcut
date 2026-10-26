import type {
  CaptionStyle,
  Cut,
  CutPreview,
  ErrorBody,
  FixedWord,
  ListedCut,
  MachineStatus,
  Me,
  Sermon,
  SermonCreated,
  SermonListItem,
  SermonShown,
  TaskLaunched,
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

export function createSermon(url: string): Promise<SermonCreated> {
  return post("/api/sermons", { url });
}

export function getMe(): Promise<Me> {
  return request("/api/me");
}

export function getStatus(): Promise<MachineStatus> {
  return request("/api/status");
}
