import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import type { SermonShown } from "../../api/types";
import { apiError, type RecordedCall } from "../../test/fakeApi";
import { fakeEventSource } from "../../test/fakeEventSource";
import { busyMachine, processedSermon, runningTask, shownSermon } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

let calls: RecordedCall[];

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const LAUNCHED = { status: 202, body: { task_id: 9, kind: "process", status: "running", sermon_id: 12 } };

async function openSermon(sermon: SermonShown, routes: Parameters<typeof fakeShellApi>[0] = {}) {
  calls = fakeShellApi({
    "GET /api/sermons/12": { body: sermon },
    "POST /api/sermons/12/process": LAUNCHED,
    ...routes,
  });
  renderRoute("/sermons/12");
  await screen.findByRole("region", { name: "Timeline" });
}

function processPosts() {
  return calls.filter(({ method, url }) => method === "POST" && url.endsWith("/process"));
}

test("offers Processar, not Exportar, on a trimmed sermon", async () => {
  await openSermon(shownSermon({ status: "trimmed" }));

  expect([
    screen.getByRole("button", { name: "Processar" }).hasAttribute("disabled"),
    screen.queryByRole("button", { name: /Exportar/ }),
  ]).toEqual([false, null]);
});

test("keeps Processar off until the sermon has borders, saying so", async () => {
  await openSermon(shownSermon({ status: "created", live_start: null, live_end: null }));

  expect([
    screen.getByRole("button", { name: "Processar" }).hasAttribute("disabled"),
    screen.getByText("Ajuste as bordas do vídeo para processar.").tagName,
  ]).toEqual([true, "P"]);
});

test("launches the processing without force and follows its events", async () => {
  const { streams } = fakeEventSource();
  await openSermon(shownSermon());

  await userEvent.click(screen.getByRole("button", { name: "Processar" }));

  expect({
    posts: processPosts().map(({ body }) => body),
    streams: streams().map(({ url }) => url),
  }).toEqual({ posts: [{}], streams: ["/api/tasks/9/events"] });
});

async function launchAndFollow(sermon = shownSermon(), routes = {}) {
  const { streams } = fakeEventSource();
  await openSermon(sermon, routes);
  await userEvent.click(screen.getByRole("button", { name: "Processar" }));
  return streams()[0];
}

test("shows the progress on the button as the events arrive", async () => {
  const stream = await launchAndFollow();

  act(() => stream.emit("progress", runningTask({ progress: 0.35 })));

  expect(screen.getByRole("button", { name: "Processando 35%" })).toBeDisabled();
});

/** The sermon's GET answers as the API would before and after the task ends. */
function sermonUntilEnd(before: SermonShown, after: SermonShown) {
  let ended = false;
  return {
    routes: { "GET /api/sermons/12": () => ({ body: ended ? after : before }) },
    end: () => {
      ended = true;
    },
  };
}

test("reloads the sermon, now processed, when the task is done", async () => {
  const api = sermonUntilEnd(shownSermon(), processedSermon());
  const stream = await launchAndFollow(shownSermon(), api.routes);

  api.end();
  act(() => stream.emit("done", runningTask({ status: "succeeded", progress: 1 })));

  expect(await screen.findByLabelText("Prévia da pregação processada")).toBeInTheDocument();
});

const DOWNLOAD_FAILED = { code: "youtube_error", message: "O YouTube recusou o download." };

function failedTask() {
  return runningTask({ status: "failed", error: DOWNLOAD_FAILED });
}

test("says why the processing failed and offers Processar again", async () => {
  const failed = shownSermon({ status: "failed", last_task: failedTask() });
  const api = sermonUntilEnd(shownSermon(), failed);
  const stream = await launchAndFollow(shownSermon(), api.routes);

  api.end();
  act(() => stream.emit("failed", failedTask()));

  expect([
    (await screen.findByRole("alert")).textContent,
    screen.getByRole("button", { name: "Processar" }).hasAttribute("disabled"),
  ]).toEqual(["O processamento falhou: O YouTube recusou o download.", false]);
});

test("follows the task already running when the sermon opens", async () => {
  const { streams } = fakeEventSource();

  await openSermon(
    shownSermon({ status: "processing", last_task: runningTask({ id: 15, progress: 0.35 }) }),
  );

  expect({
    streams: streams().map(({ url }) => url),
    button: screen.getByRole("button", { name: "Processando 35%" }).hasAttribute("disabled"),
  }).toEqual({ streams: ["/api/tasks/15/events"], button: true });
});

const BUSY = "A máquina está ocupada: processando a pregação 7.";

test("says what keeps the machine busy and launches nothing", async () => {
  const { streams } = fakeEventSource();
  await openSermon(shownSermon(), {
    "POST /api/sermons/12/process": apiError(409, "busy", BUSY),
  });

  await userEvent.click(screen.getByRole("button", { name: "Processar" }));

  expect([(await screen.findByRole("alert")).textContent, streams().length]).toEqual([BUSY, 0]);
});

test("keeps Processar off while the machine works on another sermon, saying on what", async () => {
  await openSermon(shownSermon(), {
    "GET /api/status": { body: busyMachine(runningTask({ id: 20, sermon_id: 7 })) },
  });

  const note = await screen.findByText("Máquina ocupada: processando a pregação 7.");

  expect([note.tagName, screen.getByRole("button", { name: "Processar" })]).toEqual([
    "P",
    expect.objectContaining({ disabled: true }),
  ]);
});

const LIVE_ON = "A live ainda não terminou; processe depois do fim da transmissão.";

test("warns that the live may still be on, without locking Processar", async () => {
  await openSermon(shownSermon({ live_finished: false }));

  expect([
    screen.getByText(/A live pode não ter terminado/).tagName,
    screen.getByRole("button", { name: "Processar" }).hasAttribute("disabled"),
  ]).toEqual(["P", false]);
});

test("locks Processar with the reason once the API says the live is on", async () => {
  await openSermon(shownSermon({ live_finished: false }), {
    "POST /api/sermons/12/process": apiError(409, "live_not_finished", LIVE_ON),
  });

  await userEvent.click(screen.getByRole("button", { name: "Processar" }));

  expect([
    (await screen.findByRole("alert")).textContent,
    screen.getByRole("button", { name: "Processar" }).hasAttribute("disabled"),
  ]).toEqual([LIVE_ON, true]);
});

async function openProcessedAndMoveBorder() {
  const routes = {
    "PATCH /api/sermons/12": ({ body }: RecordedCall) => {
      const { start, end } = body as { start: number; end: number };
      return { body: processedSermon({ live_start: start, live_end: end }) };
    },
  };
  await openSermon(processedSermon({ live_duration: 7080 }), routes);
  const before = screen.queryByRole("button", { name: "Reprocessar" });
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
    DOMRect.fromRect({ x: 0, y: 0, width: 1000, height: 100 }),
  );
  const timeline = screen.getByRole("region", { name: "Timeline" });
  const start = within(timeline).getByRole("slider", { name: "Início da pregação" });
  fireEvent.pointerDown(start, { clientX: 254 });
  fireEvent.pointerMove(start, { clientX: 300 });
  fireEvent.pointerUp(start, { clientX: 300 });
  return before;
}

test("offers Reprocessar, warning that the cuts' edits are lost, once the borders change", async () => {
  const before = await openProcessedAndMoveBorder();

  await screen.findByRole("button", { name: "Reprocessar" });

  expect([before, screen.getByText(/as edições dos cortes se perdem/).tagName]).toEqual([
    null,
    "P",
  ]);
});

test("reprocesses with force, the only way the API discards the cuts' edits", async () => {
  fakeEventSource();
  await openProcessedAndMoveBorder();

  await userEvent.click(await screen.findByRole("button", { name: "Reprocessar" }));

  expect(processPosts().map(({ body }) => body)).toEqual([{ force: true }]);
});
