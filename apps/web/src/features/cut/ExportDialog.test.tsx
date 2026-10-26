import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { apiError, type RecordedCall, type Reply } from "../../test/fakeApi";
import { DEFAULT_QUERY, ESTIMATE, openExportDialog } from "../../test/cutLevel";
import { churchCaption, defaultRenderOptions, shownCut } from "../../test/fixtures";

let calls: RecordedCall[];

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function openDialog(routes: Parameters<typeof openExportDialog>[0] = {}) {
  const opened = await openExportDialog(routes);
  calls = opened.calls;
  return opened.dialog;
}

test("opens Exportar 9:16 with the cut's title and the prototype's groups and options", async () => {
  const dialog = await openDialog();

  expect({
    modal: dialog.getAttribute("aria-modal"),
    title: within(dialog).getByText(shownCut().title).tagName,
    groups: within(dialog)
      .getAllByRole("heading")
      .map(({ textContent }) => textContent),
    options: within(dialog)
      .getAllByRole("group")
      .map((group) => group.getAttribute("aria-label")),
  }).toEqual({
    modal: "true",
    title: "P",
    groups: ["Exportar 9:16", "Limpeza", "Edição", "Áudio", "Vídeo"],
    options: [
      "Remover hesitações",
      "Remover gaguejos",
      "Pausas",
      "Suavizar emendas",
      "Fade no início e no fim",
      "Normalizar volume",
      "Legenda",
      "Resolução",
      "Qualidade",
    ],
  });
});

function writes() {
  return calls.filter(({ method }) => method !== "GET");
}

test.each(["Cancelar", "Fechar"])("closes with %s, saving nothing", async (button) => {
  const dialog = await openDialog();

  await userEvent.click(within(dialog).getByRole("button", { name: button }));

  expect({ open: screen.queryByRole("dialog"), writes: writes() }).toEqual({
    open: null,
    writes: [],
  });
});

function pressed(dialog: HTMLElement): Record<string, string> {
  return Object.fromEntries(
    within(dialog)
      .getAllByRole("group")
      .map((group) => [
        group.getAttribute("aria-label"),
        within(group).getByRole("button", { pressed: true }).textContent,
      ]),
  );
}

test("opens with the cut's saved options and the caption as the Legenda tab has it", async () => {
  const dialog = await openDialog({
    "GET /api/cuts/34": {
      body: shownCut({
        render_options: defaultRenderOptions({
          fillers: "keep",
          pauses: "short",
          fade: false,
          caption: true,
          resolution: "720x1280",
          quality: "small",
        }),
        caption: churchCaption({ enabled: false }),
      }),
    },
  });

  expect(pressed(dialog)).toEqual({
    "Remover hesitações": "Não",
    "Remover gaguejos": "Sim",
    Pausas: "Curtas",
    "Suavizar emendas": "Sim",
    "Fade no início e no fim": "Não",
    "Normalizar volume": "Sim",
    Legenda: "Não",
    Resolução: "720×1280",
    Qualidade: "Arquivo menor",
  });
});

function estimates() {
  return calls.filter(({ url }) => url.startsWith(`${ESTIMATE}?`));
}

test("asks the estimate once on opening and shows its duration", async () => {
  const dialog = await openDialog();

  expect({
    shown: (await within(dialog).findByText("1:01")).closest("p")?.textContent,
    asked: estimates().map(({ url }) => url),
  }).toEqual({ shown: "Duração estimada 1:01", asked: [`${ESTIMATE}?${DEFAULT_QUERY}`] });
});

test.each([
  ["Remover hesitações", "Não", "fillers=remove", "fillers=keep"],
  ["Remover gaguejos", "Não", "stammers=remove", "stammers=keep"],
  ["Pausas", "Curtas", "pauses=natural", "pauses=short"],
  ["Pausas", "Originais", "pauses=natural", "pauses=original"],
  ["Suavizar emendas", "Não", "smooth_joins=true", "smooth_joins=false"],
  ["Fade no início e no fim", "Não", "fade=true", "fade=false"],
  ["Normalizar volume", "Não", "normalize=true", "normalize=false"],
  ["Legenda", "Não", "caption=true", "caption=false"],
  ["Resolução", "720×1280", "resolution=1080x1920", "resolution=720x1280"],
  ["Qualidade", "Arquivo menor", "quality=high", "quality=small"],
])("asks the estimate again when %s changes to %s", async (group, choice, from, to) => {
  const query = DEFAULT_QUERY.replace(from, to);
  const dialog = await openDialog({
    [`GET ${ESTIMATE}?${query}`]: { body: { duration: 47.8, options: defaultRenderOptions() } },
  });
  await within(dialog).findByText("1:01");

  await userEvent.click(
    within(within(dialog).getByRole("group", { name: group })).getByRole("button", {
      name: choice,
    }),
  );

  expect({
    shown: (await within(dialog).findByText("0:47")).tagName,
    last: estimates().at(-1)?.url,
  }).toEqual({ shown: "B", last: `${ESTIMATE}?${query}` });
});

function choose(dialog: HTMLElement, group: string, choice: string) {
  fireEvent.click(
    within(within(dialog).getByRole("group", { name: group })).getByRole("button", {
      name: choice,
    }),
  );
}

test("waits 300 ms after the last change to ask the estimate, with the last options", async () => {
  const dialog = await openDialog();
  await within(dialog).findByText("1:01");
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });

  choose(dialog, "Fade no início e no fim", "Não");
  choose(dialog, "Pausas", "Curtas");
  choose(dialog, "Remover hesitações", "Não");
  act(() => vi.advanceTimersByTime(299));
  const early = estimates().length;
  act(() => vi.advanceTimersByTime(1));

  expect({
    early,
    asked: estimates()
      .slice(1)
      .map(({ url }) => url),
  }).toEqual({
    early: 1,
    asked: [
      `${ESTIMATE}?fillers=keep&stammers=remove&pauses=short&smooth_joins=true&fade=false` +
        "&normalize=true&caption=true&resolution=1080x1920&quality=high",
    ],
  });
});

test("cancels the estimate a newer one replaces, and never shows its late answer", async () => {
  const older = DEFAULT_QUERY.replace("fade=true", "fade=false");
  const newer = older.replace("pauses=natural", "pauses=short");
  let release: (reply: Reply) => void = () => {};
  const dialog = await openDialog({
    [`GET ${ESTIMATE}?${older}`]: () => new Promise<Reply>((resolve) => (release = resolve)),
    [`GET ${ESTIMATE}?${newer}`]: { body: { duration: 47.8, options: defaultRenderOptions() } },
  });
  await within(dialog).findByText("1:01");
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });

  choose(dialog, "Fade no início e no fim", "Não");
  act(() => vi.advanceTimersByTime(300));
  choose(dialog, "Pausas", "Curtas");
  await act(async () => vi.advanceTimersByTime(300));
  await act(async () => release({ body: { duration: 99, options: defaultRenderOptions() } }));

  expect({
    shown: within(dialog).getByText(/Duração estimada/).textContent,
    olderAborted: estimates().find(({ url }) => url.endsWith(older))?.signal?.aborted,
  }).toEqual({ shown: "Duração estimada 0:47", olderAborted: true });
});

test.each([
  [
    "a refusal",
    apiError(400, "invalid_argument", "Valor inválido para pauses."),
    "Valor inválido para pauses.",
  ],
  [
    "no network",
    { reject: new TypeError("Failed to fetch") },
    "Sem conexão com a API. Confira a rede e tente de novo.",
  ],
])("says why the estimate failed on %s, keeping Exportar", async (_, reply, reason) => {
  const dialog = await openDialog({ [`GET ${ESTIMATE}?${DEFAULT_QUERY}`]: reply });

  expect({
    reason: (await within(dialog).findByText(reason)).getAttribute("role"),
    exportar: within(dialog).getByRole("button", { name: "Exportar" }).hasAttribute("disabled"),
  }).toEqual({ reason: "alert", exportar: false });
});
