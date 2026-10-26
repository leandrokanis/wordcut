import { vi } from "vitest";

export interface RecordedCall {
  method: string;
  url: string;
  headers: Headers;
  body: unknown;
  /** The ``AbortSignal`` the code gave ``fetch``, to see whether it cancelled the call. */
  signal?: AbortSignal;
}

export type Reply =
  | { status?: number; body?: unknown; raw?: string }
  | { reject: Error };

type Route = Reply | ((call: RecordedCall) => Reply | Promise<Reply>);

/** Replaces ``fetch`` with a double keyed by "METHOD /path"; any other request gets a 404
 * ``not_found``, so a forgotten call shows up instead of reaching the network. A route may
 * answer with a promise, to hold the reply until the test releases it. */
export function fakeApi(routes: Record<string, Route>): RecordedCall[] {
  const calls: RecordedCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const call: RecordedCall = {
        method: init.method ?? "GET",
        url: input,
        headers: new Headers(init.headers),
        body: typeof init.body === "string" ? JSON.parse(init.body) : undefined,
        signal: init.signal ?? undefined,
      };
      calls.push(call);
      const route = routes[`${call.method} ${call.url}`];
      const reply = typeof route === "function" ? await route(call) : route;
      return respond(reply ?? notFound());
    }),
  );
  return calls;
}

export function apiError(
  status: number,
  code: string,
  message: string,
  details?: Record<string, unknown>,
): Reply {
  return { status, body: { error: { code, message, ...(details && { details }) } } };
}

function notFound(): Reply {
  return apiError(404, "not_found", "Rota não prevista no teste.");
}

function respond(reply: Reply): Response {
  if ("reject" in reply) {
    throw reply.reject;
  }
  const text = reply.raw ?? JSON.stringify(reply.body ?? {});
  return new Response(text, { status: reply.status ?? 200 });
}
