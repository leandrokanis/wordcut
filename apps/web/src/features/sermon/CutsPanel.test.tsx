import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import type { ListedCut, SermonShown } from "../../api/types";
import { apiError, type RecordedCall, type Reply } from "../../test/fakeApi";
import { fakeEventSource } from "../../test/fakeEventSource";
import { fakePlayers } from "../../test/fakePlayers";
import {
  admin,
  assistant,
  cutPreview,
  listedCut,
  processedSermon,
  runningTask,
  shownCut,
  shownSermon,
} from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

let calls: RecordedCall[] = [];

async function panelOf(
  cuts: ListedCut[],
  sermon: SermonShown = processedSermon(),
  routes: Parameters<typeof fakeShellApi>[0] = {},
): Promise<HTMLElement> {
  calls = fakeShellApi({
    "GET /api/sermons/12": { body: sermon },
    "GET /api/sermons/12/cuts": { body: { items: cuts } },
    "GET /api/cuts/34": { body: shownCut() },
    "GET /api/cuts/34/preview": { body: cutPreview() },
    ...routes,
  });
  renderRoute("/sermons/12");
  return screen.findByRole("complementary", { name: "Cortes" });
}

/** The card's accessible name, its title. */
function titleOf(card: HTMLElement): string | null {
  return card.getAttribute("aria-label");
}

test("shows one card per cut of the processed sermon, with title, text, duration and state", async () => {
  const panel = await panelOf([
    listedCut({ id: 34, title: "Fé no deserto", text: "Deus sustenta.", duration: 58.4 }),
    listedCut({ id: 35, status: "chosen", title: "Graça", text: "A graça alcança.", duration: 72 }),
  ]);

  const cards = await within(panel).findAllByRole("listitem");
  expect(cards.map((card) => card.textContent)).toEqual([
    expect.stringMatching(/Fé no deserto.*Deus sustenta\..*0:58.*Sugerido/),
    expect.stringMatching(/Graça.*A graça alcança\..*1:12.*Escolhido/),
  ]);
});

test("keeps the service's order, the discarded cut last and marked as discarded", async () => {
  const panel = await panelOf([
    listedCut({ id: 35, status: "chosen", title: "Graça" }),
    listedCut({ id: 36, title: "Esperança" }),
    listedCut({ id: 34, status: "discarded", title: "Fé no deserto" }),
  ]);

  const cards = await within(panel).findAllByRole("listitem");
  expect(cards.map((card) => [titleOf(card), card.hasAttribute("data-discarded")])).toEqual([
    ["Graça", false],
    ["Esperança", false],
    ["Fé no deserto", true],
  ]);
});

async function menuOf(card: HTMLElement): Promise<HTMLElement> {
  await userEvent.click(within(card).getByRole("button", { name: "Mais ações" }));
  return within(card).getByRole("menu");
}

test("offers Descartar in the menu of a kept cut and Restaurar in that of a discarded one", async () => {
  const panel = await panelOf([
    listedCut({ id: 34, title: "Fé no deserto" }),
    listedCut({ id: 35, status: "discarded", title: "Graça" }),
  ]);
  const [kept, discarded] = await within(panel).findAllByRole("listitem");

  const items = [];
  for (const card of [kept, discarded]) {
    const menu = await menuOf(card);
    items.push(within(menu).getAllByRole("menuitem").map((item) => item.textContent));
  }

  expect(items).toEqual([["Descartar"], ["Restaurar"]]);
});

test.each([
  ["Escape", () => userEvent.keyboard("{Escape}")],
  ["a click outside", () => userEvent.click(screen.getByRole("heading", { name: "Cortes" }))],
])("closes the menu on %s", async (_, close) => {
  const panel = await panelOf([listedCut()]);
  await menuOf(await within(panel).findByRole("listitem"));

  await close();

  expect(within(panel).queryByRole("menu")).toBeNull();
});

test("keeps one menu open at a time", async () => {
  const panel = await panelOf([listedCut({ id: 34 }), listedCut({ id: 35, title: "Graça" })]);
  const [first, second] = await within(panel).findAllByRole("listitem");

  await menuOf(first);
  await menuOf(second);

  expect(within(panel).getAllByRole("menu").map((menu) => second.contains(menu))).toEqual([true]);
});

test("says why a processed sermon has no cuts when the suggestion failed", async () => {
  const panel = await panelOf(
    [],
    processedSermon({
      suggestion_error: {
        code: "llm_not_configured",
        message: "O LLM não está configurado: defina a chave nas configurações.",
      },
    }),
  );

  expect(
    await within(panel).findByText(/O LLM não está configurado: defina a chave nas configurações\./),
  ).toBeInTheDocument();
});

test("says so when the processed sermon has no cuts and no suggestion error", async () => {
  const panel = await panelOf([]);

  expect(await within(panel).findByText("Nenhum corte nesta pregação.")).toBeInTheDocument();
});

test.each(["created", "trimmed", "failed"] as const)(
  "tells a %s sermon that the cuts come after processing, without asking for them",
  async (status) => {
    const panel = await panelOf([listedCut()], shownSermon({ status }));

    const note = await within(panel).findByText("Os cortes aparecem depois do processamento.");
    expect({
      shown: note.isConnected,
      asked: calls.some(({ url }) => url === "/api/sermons/12/cuts"),
    }).toEqual({ shown: true, asked: false });
  },
);

test("shows the API's message when the cuts cannot be loaded", async () => {
  fakeShellApi({
    "GET /api/sermons/12": { body: processedSermon() },
    "GET /api/sermons/12/cuts": apiError(502, "unavailable", "A API não respondeu."),
  });
  renderRoute("/sermons/12");
  const panel = await screen.findByRole("complementary", { name: "Cortes" });

  expect(await within(panel).findByRole("alert")).toHaveTextContent("A API não respondeu.");
});

/** The cut's level: its 9:16 preview. */
const CUT_LEVEL = "Prévia do corte";

function sent(): string[] {
  return calls
    .filter(({ method }) => method !== "GET")
    .map(({ method, url }) => `${method} ${url}`);
}

/** A reply the test holds until it calls ``release``. */
function held(reply: Reply): { route: () => Promise<Reply>; release: () => void } {
  let release = () => {};
  const route = () => new Promise<Reply>((resolve) => (release = () => resolve(reply)));
  return { route, release: () => release() };
}

test("opens a suggested cut by choosing it, and goes to its level once the API answers", async () => {
  const choose = held({ body: listedCut({ status: "chosen" }) });
  const panel = await panelOf([listedCut({ id: 34 })], processedSermon(), {
    "POST /api/cuts/34/choose": choose.route,
  });

  await userEvent.click(await within(panel).findByRole("button", { name: /Fé no deserto/ }));
  const before = { sent: sent(), cutLevel: screen.queryByLabelText(CUT_LEVEL) !== null };
  await act(async () => choose.release());

  expect({ before, after: await screen.findByLabelText(CUT_LEVEL) }).toEqual({
    before: { sent: ["POST /api/cuts/34/choose"], cutLevel: false },
    after: expect.anything(),
  });
});

test("opens a chosen cut without choosing it again", async () => {
  const panel = await panelOf([listedCut({ id: 34, status: "chosen" })]);

  await userEvent.click(await within(panel).findByRole("button", { name: /Fé no deserto/ }));

  expect({ cutLevel: await screen.findByLabelText(CUT_LEVEL), sent: sent() }).toEqual({
    cutLevel: expect.anything(),
    sent: [],
  });
});

test("does not open a discarded cut", async () => {
  const panel = await panelOf([listedCut({ id: 34, status: "discarded" })]);

  await userEvent.click(await within(panel).findByRole("button", { name: /Fé no deserto/ }));

  expect({ cutLevel: screen.queryByLabelText(CUT_LEVEL), sent: sent() }).toEqual({
    cutLevel: null,
    sent: [],
  });
});

test("stays on the sermon with the API's message when choosing the cut fails", async () => {
  const panel = await panelOf([listedCut({ id: 34 })], processedSermon(), {
    "POST /api/cuts/34/choose": apiError(404, "not_found", "Corte 34 não existe."),
  });

  await userEvent.click(await within(panel).findByRole("button", { name: /Fé no deserto/ }));

  expect({
    alert: (await within(panel).findByRole("alert")).textContent,
    cutLevel: screen.queryByLabelText(CUT_LEVEL),
  }).toEqual({ alert: "Corte 34 não existe.", cutLevel: null });
});

/** ``GET /api/sermons/12/cuts`` answering ``before`` until a transition, ``after`` from then. */
function cutsAround(before: ListedCut[], after: ListedCut[]) {
  return () => ({ body: { items: sent().length ? after : before } });
}

test("discards from the menu and shows the list as the service gives it again", async () => {
  const kept = listedCut({ id: 35, title: "Graça" });
  const panel = await panelOf([], processedSermon(), {
    "GET /api/sermons/12/cuts": cutsAround(
      [listedCut({ id: 34 }), kept],
      [kept, listedCut({ id: 34, status: "discarded" })],
    ),
    "POST /api/cuts/34/discard": { body: listedCut({ id: 34, status: "discarded" }) },
  });
  const card = await within(panel).findByRole("listitem", { name: "Fé no deserto" });

  await userEvent.click(within(await menuOf(card)).getByRole("menuitem", { name: "Descartar" }));

  await within(panel).findByText("Descartado");
  expect({
    sent: sent(),
    asked: calls.filter(({ url }) => url === "/api/sermons/12/cuts").length,
    order: within(panel).getAllByRole("listitem").map(titleOf),
  }).toEqual({
    sent: ["POST /api/cuts/34/discard"],
    asked: 2,
    order: ["Graça", "Fé no deserto"],
  });
});

test("restores from the menu and shows the cut suggested again", async () => {
  const panel = await panelOf([], processedSermon(), {
    "GET /api/sermons/12/cuts": cutsAround(
      [listedCut({ id: 34, status: "discarded" })],
      [listedCut({ id: 34 })],
    ),
    "POST /api/cuts/34/restore": { body: listedCut({ id: 34 }) },
  });
  const card = await within(panel).findByRole("listitem", { name: "Fé no deserto" });

  await userEvent.click(within(await menuOf(card)).getByRole("menuitem", { name: "Restaurar" }));

  expect({
    state: (await within(panel).findByText("Sugerido")).isConnected,
    sent: sent(),
  }).toEqual({ state: true, sent: ["POST /api/cuts/34/restore"] });
});

test("keeps the card as it was, with the API's message, when discarding fails", async () => {
  const panel = await panelOf([listedCut({ id: 34 })], processedSermon(), {
    "POST /api/cuts/34/discard": apiError(404, "not_found", "Corte 34 não existe."),
  });
  const card = await within(panel).findByRole("listitem", { name: "Fé no deserto" });

  await userEvent.click(within(await menuOf(card)).getByRole("menuitem", { name: "Descartar" }));

  expect({
    alert: (await within(panel).findByRole("alert")).textContent,
    discarded: within(panel).getByRole("listitem").hasAttribute("data-discarded"),
  }).toEqual({ alert: "Corte 34 não existe.", discarded: false });
});

test("never asks the API to change a cut's content", async () => {
  const panel = await panelOf(
    [listedCut({ id: 34 }), listedCut({ id: 35, title: "Graça" })],
    processedSermon(),
    {
      "POST /api/cuts/35/discard": { body: listedCut({ id: 35, status: "discarded" }) },
      "POST /api/cuts/34/choose": { body: listedCut({ id: 34, status: "chosen" }) },
    },
  );
  const other = await within(panel).findByRole("listitem", { name: "Graça" });
  await userEvent.click(within(await menuOf(other)).getByRole("menuitem", { name: "Descartar" }));
  await userEvent.click(within(panel).getByRole("button", { name: /Fé no deserto/ }));
  await screen.findByLabelText(CUT_LEVEL);

  expect(sent()).toEqual(["POST /api/cuts/35/discard", "POST /api/cuts/34/choose"]);
});

describe("while the sermon processes", () => {
  const STEPS = [
    "Baixar a faixa em 1080p",
    "Transcrever palavra por palavra",
    "Cortar a pregação em 16:9",
    "Sugerir cortes",
  ];

  /** Opens a sermon processing task 15, whose next event is ``progress`` at ``fraction``. */
  async function processingPanel(fraction: number, message: string) {
    const { streams } = fakeEventSource();
    const panel = await panelOf(
      [],
      shownSermon({ status: "processing", last_task: runningTask({ id: 15, progress: 0 }) }),
    );
    act(() =>
      streams()[0].emit(
        "progress",
        runningTask({ id: 15, progress: fraction, progress_message: message }),
      ),
    );
    return within(panel).getByRole("status");
  }

  /** Each step's name, its progress in percent and whether it is the one under way. */
  function stepsOf(status: HTMLElement) {
    return within(status)
      .getAllByRole("listitem")
      .map((step) => [
        within(step).getByRole("progressbar").getAttribute("aria-label"),
        Number(within(step).getByRole("progressbar").getAttribute("aria-valuenow")),
        step.getAttribute("aria-current") === "step",
      ]);
  }

  test("shows the prototype's steps, each with its own share of the progress", async () => {
    const status = await processingPanel(0.6, "transcrevendo");

    expect(stepsOf(status)).toEqual([
      [STEPS[0], 100, false],
      [STEPS[1], 50, true],
      [STEPS[2], 0, false],
      [STEPS[3], 0, false],
    ]);
  });

  test("tells a processing sermon that it is processing, not that the cuts come after", async () => {
    const status = await processingPanel(0.12, "baixando");

    expect([status.getAttribute("aria-label"), screen.queryByText(/Os cortes aparecem/)]).toEqual([
      "Processando a pregação",
      null,
    ]);
  });

  test.each([
    ["sincronizando", 0.3, [86, 0, 0, 0], 0],
    ["gravando", 0.95, [100, 100, 91, 0], 2],
    ["sugerindo", 0.96, [100, 100, 100, 0], 3],
  ])("counts %s at %s in the step it belongs to", async (message, fraction, percents, current) => {
    const status = await processingPanel(fraction, message);

    expect(stepsOf(status)).toEqual(
      STEPS.map((name, index) => [name, percents[index], index === current]),
    );
  });

  test("shows the steps as soon as the API accepts a processing launched here", async () => {
    fakeEventSource();
    const panel = await panelOf([], shownSermon(), {
      "POST /api/sermons/12/process": {
        status: 202,
        body: { task_id: 9, kind: "process", status: "running", sermon_id: 12 },
      },
    });

    await userEvent.click(screen.getByRole("button", { name: "Processar" }));

    expect([
      within(panel).getByRole("status").getAttribute("aria-label"),
      within(panel).queryByText(/Os cortes aparecem/),
    ]).toEqual(["Processando a pregação", null]);
  });
});

describe("Novo corte", () => {
  // The processed sermon starts 1800 s into the live and lasts 2400 s.
  const SERMON_START = 1800;
  const LENGTH = 2400;

  /** The panel of the processed sermon for ``me``, the cursor at ``sermonSeconds``. */
  async function panelAt(
    sermonSeconds: number,
    routes: Parameters<typeof fakeShellApi>[0] = {},
    me = admin(),
  ): Promise<HTMLElement> {
    const players = fakePlayers();
    calls = fakeShellApi(
      {
        "GET /api/sermons/12": {
          body: processedSermon({ sermon_start: SERMON_START, sermon_end: SERMON_START + LENGTH }),
        },
        "GET /api/sermons/12/cuts": { body: { items: [listedCut({ id: 35, status: "chosen" })] } },
        "GET /api/cuts/34": { body: shownCut() },
        "GET /api/cuts/34/preview": { body: cutPreview() },
        ...routes,
      },
      me,
    );
    renderRoute("/sermons/12", players);
    const panel = await screen.findByRole("complementary", { name: "Cortes" });
    await within(panel).findByRole("listitem");
    act(() => players.current().moveTo(SERMON_START + sermonSeconds));
    return panel;
  }

  const created = { "POST /api/sermons/12/cuts": { status: 201, body: shownCut({ id: 34 }) } };

  function bodiesSent(): unknown[] {
    return calls.filter(({ method }) => method === "POST").map(({ body }) => body);
  }

  test("creates a cut of 60 s from the cursor, in sermon time, and opens its level", async () => {
    const panel = await panelAt(600, created);

    await userEvent.click(within(panel).getByRole("button", { name: "Novo corte" }));

    expect({ cutLevel: await screen.findByLabelText(CUT_LEVEL), sent: bodiesSent() }).toEqual({
      cutLevel: expect.anything(),
      sent: [{ start: 600, end: 660 }],
    });
  });

  test.each([
    ["less than 60 s from the end", 2370, { start: 2370, end: 2400 }],
    ["less than 10 s from the end", 2395, { start: 2390, end: 2400 }],
  ])("near the end, %s, the range ends at the sermon's end and lasts 10 s at least", async (
    _,
    cursor,
    range,
  ) => {
    const panel = await panelAt(cursor, created);

    await userEvent.click(within(panel).getByRole("button", { name: "Novo corte" }));

    await screen.findByLabelText(CUT_LEVEL);
    expect(bodiesSent()).toEqual([range]);
  });

  test("is not offered to an assistant", async () => {
    const panel = await panelAt(600, created, assistant());

    expect(within(panel).queryByRole("button", { name: "Novo corte" })).toBeNull();
  });

  test("stays on the sermon with the API's message when the cut is refused", async () => {
    const panel = await panelAt(600, {
      "POST /api/sermons/12/cuts": apiError(
        400,
        "invalid_argument",
        "A faixa precisa ter ao menos 10 s depois de encostar nas frases.",
      ),
    });

    await userEvent.click(within(panel).getByRole("button", { name: "Novo corte" }));

    expect({
      alert: (await within(panel).findByRole("alert")).textContent,
      cutLevel: screen.queryByLabelText(CUT_LEVEL),
    }).toEqual({
      alert: "A faixa precisa ter ao menos 10 s depois de encostar nas frases.",
      cutLevel: null,
    });
  });

  test("cannot be pressed again while the cut is being created", async () => {
    const creating = held({ status: 201, body: shownCut({ id: 34 }) });
    const panel = await panelAt(600, { "POST /api/sermons/12/cuts": creating.route });
    const button = within(panel).getByRole("button", { name: "Novo corte" });

    await userEvent.click(button);
    await userEvent.click(button);

    expect({ disabled: button.hasAttribute("disabled"), sent: bodiesSent().length }).toEqual({
      disabled: true,
      sent: 1,
    });
  });
});
