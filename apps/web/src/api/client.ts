import type {
  Cut,
  ErrorBody,
  MachineStatus,
  Me,
  Sermon,
  SermonCreated,
  SermonListItem,
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

function post<T>(path: string, body: object): Promise<T> {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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

export function getCut(id: number): Promise<Cut> {
  return request(`/api/cuts/${id}`);
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
