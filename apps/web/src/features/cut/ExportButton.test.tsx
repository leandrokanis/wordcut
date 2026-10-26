import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { apiError, type RecordedCall, type Reply } from "../../test/fakeApi";
import { DEFAULT_QUERY, ESTIMATE, live, openCut, openExportDialog } from "../../test/cutLevel";
import { fakeEventSource } from "../../test/fakeEventSource";
import type { ErrorBody, RenderOptions } from "../../api/types";
import {
  busyMachine,
  churchCaption,
  cutWords,
  defaultRenderOptions,
  renderTask,
  shownCut,
} from "../../test/fixtures";

let calls: RecordedCall[];

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const RENDERS = "/api/cuts/34/renders";
const LAUNCHED = {
  status: 202,
  body: { task_id: 10, kind: "render", status: "running", cut_id: 34 },
};

async function openDialog(routes: Parameters<typeof openExportDialog>[0] = {}) {
  const opened = await openExportDialog({ [`POST ${RENDERS}`]: LAUNCHED, ...routes });
  calls = opened.calls;
  return opened.dialog;
}

async function choose(dialog: HTMLElement, group: string, choice: string) {
  await userEvent.click(
    within(within(dialog).getByRole("group", { name: group })).getByRole("button", {
      name: choice,
    }),
  );
}

function launches() {
  return calls.filter(({ method, url }) => method === "POST" && url === RENDERS);
}

test("launches the export with the dialog's nine options as JSON, and closes it", async () => {
  fakeEventSource();
  const dialog = await openDialog();
  await choose(dialog, "Remover gaguejos", "Não");
  await choose(dialog, "Fade no início e no fim", "Não");
  await choose(dialog, "Resolução", "720×1280");

  await userEvent.click(within(dialog).getByRole("button", { name: "Exportar" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(launches().map(({ body }) => body)).toEqual([
    defaultRenderOptions({ stammers: "keep", fade: false, resolution: "720x1280" }),
  ]);
});

async function launch(routes: Parameters<typeof openExportDialog>[0] = {}) {
  const { streams } = fakeEventSource();
  const dialog = await openDialog(routes);
  await userEvent.click(within(dialog).getByRole("button", { name: "Exportar" }));
  return streams;
}

test("follows the export's events, its progress on the level's button", async () => {
  const streams = await launch();
  await waitFor(() => expect(streams()).toHaveLength(1));

  act(() => streams()[0].emit("progress", renderTask({ progress: 0.35 })));

  expect({
    url: streams()[0].url,
    disabled: screen.getByRole("button", { name: "Exportando 35%" }).hasAttribute("disabled"),
  }).toEqual({ url: "/api/tasks/10/events", disabled: true });
});

function reads(url: string) {
  return calls.filter((call) => call.method === "GET" && call.url === url).length;
}

test("closes the events on done, offers Exportar again and reads the cut and its exports", async () => {
  const streams = await launch({ [`GET ${RENDERS}`]: { body: { items: [] } } });
  await waitFor(() => expect(streams()).toHaveLength(1));
  const cutReads = reads("/api/cuts/34");

  act(() => streams()[0].emit("done", renderTask({ status: "succeeded", progress: 1 })));

  await waitFor(() => expect(reads(RENDERS)).toBe(1));
  expect({
    closed: streams()[0].close.mock.calls.length > 0,
    exportar: screen.getByRole("button", { name: "Exportar" }).hasAttribute("disabled"),
    cutRead: reads("/api/cuts/34") - cutReads,
  }).toEqual({ closed: true, exportar: false, cutRead: 1 });
});

test("says why the export failed, closing the events and registering nothing", async () => {
  const streams = await launch();
  await waitFor(() => expect(streams()).toHaveLength(1));

  act(() =>
    streams()[0].emit(
      "failed",
      renderTask({
        status: "failed",
        error: { code: "internal_error", message: "A renderização falhou." },
      }),
    ),
  );

  expect({
    alert: (await screen.findByRole("alert")).textContent,
    closed: streams()[0].close.mock.calls.length > 0,
    exportsRead: reads(RENDERS),
  }).toEqual({
    alert: "A exportação falhou: A renderização falhou.",
    closed: true,
    exportsRead: 0,
  });
});

test("keeps Exportar off while the machine works for another resource, saying so", async () => {
  const dialog = await openDialog({ "GET /api/status": { body: busyMachine() } });

  expect({
    note: (await within(dialog).findByText(/^Máquina ocupada/)).textContent,
    exportar: within(dialog).getByRole("button", { name: "Exportar" }).hasAttribute("disabled"),
  }).toEqual({ note: "Máquina ocupada: processando a pregação 12.", exportar: true });
});

test.each([
  ["busy", apiError(409, "busy", "Máquina ocupada: exportando o corte 35.")],
  ["sermon_not_processed", apiError(409, "sermon_not_processed", "Processe a pregação antes.")],
  ["invalid_argument", apiError(400, "invalid_argument", "Valor inválido para pauses.")],
])("says why the API refused the export (%s), following nothing", async (_, refusal) => {
  const streams = await launch({ [`POST ${RENDERS}`]: refusal });
  const dialog = screen.getByRole("dialog", { name: "Exportar 9:16" });

  expect({
    reason: (await within(dialog).findByRole("alert")).textContent,
    streams: streams().length,
  }).toEqual({ reason: (refusal as { body: ErrorBody }).body.error.message, streams: 0 });
});

test("follows its own export, running when the cut is opened, without exporting again", async () => {
  const { streams } = fakeEventSource();
  await openCut({ "GET /api/status": { body: busyMachine(renderTask({ progress: 0.35 })) } });

  expect({
    disabled: (await screen.findByRole("button", { name: "Exportando 35%" })).hasAttribute(
      "disabled",
    ),
    followed: streams().map(({ url }) => url),
  }).toEqual({ disabled: true, followed: ["/api/tasks/10/events"] });
});

test("keeps Exportar off while the cut's own lock is held by an export it cannot follow", async () => {
  const cliExport = busyMachine(renderTask());
  const dialog = await openDialog({
    "GET /api/status": { body: { ...cliExport, running_tasks: [] } },
  });

  expect({
    note: (await within(dialog).findByText(/^Máquina ocupada/)).textContent,
    exportar: within(dialog).getByRole("button", { name: "Exportar" }).hasAttribute("disabled"),
  }).toEqual({ note: "Máquina ocupada: exportando o corte 34.", exportar: true });
});

/** ``GET /api/cuts/34`` and the launch as the API answers them: the launch saves its options. */
function savingRoutes() {
  let saved = defaultRenderOptions();
  return {
    "GET /api/cuts/34": () => ({ body: shownCut({ render_options: saved }) }),
    [`POST ${RENDERS}`]: (call: RecordedCall) => {
      saved = call.body as RenderOptions;
      return LAUNCHED;
    },
    [`GET ${RENDERS}`]: { body: { items: [] } },
  };
}

async function reopenDialog() {
  await userEvent.click(screen.getByRole("button", { name: "Exportar" }));
  await userEvent.click(screen.getByRole("button", { name: /Exportar 9:16…/ }));
  return screen.getByRole("dialog", { name: "Exportar 9:16" });
}

test("reopens the dialog with the options the finished export used", async () => {
  const { streams } = fakeEventSource();
  const dialog = await openDialog(savingRoutes());
  await choose(dialog, "Fade no início e no fim", "Não");
  await userEvent.click(within(dialog).getByRole("button", { name: "Exportar" }));
  await waitFor(() => expect(streams()).toHaveLength(1));
  act(() => streams()[0].emit("done", renderTask({ status: "succeeded", progress: 1 })));
  await waitFor(() => expect(reads(RENDERS)).toBe(1));

  const reopened = await reopenDialog();

  await waitFor(() =>
    expect(
      within(within(reopened).getByRole("group", { name: "Fade no início e no fim" })).getByRole(
        "button",
        { pressed: true },
      ),
    ).toHaveTextContent("Não"),
  );
});

test("shows on the Legenda tab the caption switch the accepted export saved", async () => {
  fakeEventSource();
  const dialog = await openDialog();
  await choose(dialog, "Legenda", "Não");
  await userEvent.click(within(dialog).getByRole("button", { name: "Exportar" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());

  await userEvent.click(screen.getByRole("tab", { name: "Legenda" }));

  expect({
    legenda: within(screen.getByRole("group", { name: "Legenda" })).getByRole("button", {
      pressed: true,
    }).textContent,
    patches: calls.filter(({ method }) => method === "PATCH").length,
  }).toEqual({ legenda: "Não", patches: 0 });
});

function held(): { route: () => Promise<Reply>; release: (reply: Reply) => void } {
  let release: (reply: Reply) => void = () => {};
  return {
    route: () => new Promise<Reply>((resolve) => (release = resolve)),
    release: (reply) => release(reply),
  };
}

test("waits for the caption's pending save before exporting, saying Salvando…", async () => {
  const patch = held();
  ({ calls } = await openCut({
    [`GET ${ESTIMATE}?${DEFAULT_QUERY}`]: {
      body: { duration: 61, options: defaultRenderOptions() },
    },
    "PATCH /api/cuts/34/caption": patch.route,
  }));
  await userEvent.click(screen.getByRole("tab", { name: "Legenda" }));
  await userEvent.click(
    within(screen.getByRole("group", { name: "Posição" })).getByRole("button", { name: "Topo" }),
  );
  const dialog = await reopenDialog();
  const pending = within(dialog)
    .getByRole("button", { name: "Salvando…" })
    .hasAttribute("disabled");

  await waitFor(() => expect(calls.some(({ method }) => method === "PATCH")).toBe(true));
  await act(async () => patch.release({ body: churchCaption({ position: "top" }) }));

  expect({
    pending,
    after: within(dialog).getByRole("button", { name: "Exportar" }).hasAttribute("disabled"),
  }).toEqual({ pending: true, after: false });
});

test("waits for a spelling fix being saved before exporting, saying Salvando…", async () => {
  const put = held();
  const opened = await openCut({
    [`GET ${ESTIMATE}?${DEFAULT_QUERY}`]: {
      body: { duration: 61, options: defaultRenderOptions() },
    },
    "PUT /api/cuts/34/words/1105": put.route,
  });
  calls = opened.calls;
  await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));
  act(() => opened.players.current().moveTo(live(2.6)));
  await userEvent.dblClick(
    within(screen.getByRole("group", { name: "Legenda na prévia" })).getByText("Deus"),
  );
  await userEvent.clear(screen.getByRole("textbox"));
  await userEvent.type(screen.getByRole("textbox"), "DEUS{Enter}");
  const dialog = await reopenDialog();
  const pending = within(dialog)
    .getByRole("button", { name: "Salvando…" })
    .hasAttribute("disabled");

  await act(async () => put.release({ body: { ...cutWords()[0], cut_id: 34, corrected: "DEUS" } }));

  expect({
    pending,
    after: within(dialog).getByRole("button", { name: "Exportar" }).hasAttribute("disabled"),
  }).toEqual({ pending: true, after: false });
});

test("waits for the church's caption style being restored before exporting", async () => {
  const restore = held();
  ({ calls } = await openCut({
    [`GET ${ESTIMATE}?${DEFAULT_QUERY}`]: {
      body: { duration: 61, options: defaultRenderOptions() },
    },
    "DELETE /api/cuts/34/caption": restore.route,
  }));
  await userEvent.click(screen.getByRole("tab", { name: "Legenda" }));
  await userEvent.click(screen.getByRole("button", { name: "Restaurar padrão" }));
  const dialog = await reopenDialog();
  const pending = within(dialog)
    .getByRole("button", { name: "Salvando…" })
    .hasAttribute("disabled");

  await act(async () => restore.release({ body: churchCaption() }));

  expect({
    pending,
    after: within(dialog).getByRole("button", { name: "Exportar" }).hasAttribute("disabled"),
  }).toEqual({ pending: true, after: false });
});
