import { render, screen } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { App } from "./App";

function serveHealth(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      url === "/api/health"
        ? new Response(JSON.stringify(body), { status })
        : new Response(null, { status: 404 }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("shows the status the API reports", async () => {
  serveHealth(200, { status: "ok" });

  render(<App />);

  expect(await screen.findByText("API: ok")).toBeInTheDocument();
});

test("shows the API as unavailable when the health check fails", async () => {
  serveHealth(503, { detail: "starting" });

  render(<App />);

  expect(await screen.findByText("API: indisponível")).toBeInTheDocument();
});
