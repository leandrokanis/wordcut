import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import type { ListedCut, SermonShown } from "../../api/types";
import { apiError, type RecordedCall, type Reply } from "../../test/fakeApi";
import { listedCut, processedSermon, shownSermon } from "../../test/fixtures";
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
    "GET /api/cuts/34": {
      body: { id: 34, sermon_id: 12, title: "Fé no deserto", status: "chosen" },
    },
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

test.each(["created", "trimmed", "processing", "failed"] as const)(
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

const CUT_LEVEL = "Esta tela está em construção.";

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
  const before = { sent: sent(), cutLevel: screen.queryByText(CUT_LEVEL) !== null };
  await act(async () => choose.release());

  expect({ before, after: await screen.findByText(CUT_LEVEL) }).toEqual({
    before: { sent: ["POST /api/cuts/34/choose"], cutLevel: false },
    after: expect.anything(),
  });
});

test("opens a chosen cut without choosing it again", async () => {
  const panel = await panelOf([listedCut({ id: 34, status: "chosen" })]);

  await userEvent.click(await within(panel).findByRole("button", { name: /Fé no deserto/ }));

  expect({ cutLevel: await screen.findByText(CUT_LEVEL), sent: sent() }).toEqual({
    cutLevel: expect.anything(),
    sent: [],
  });
});

test("does not open a discarded cut", async () => {
  const panel = await panelOf([listedCut({ id: 34, status: "discarded" })]);

  await userEvent.click(await within(panel).findByRole("button", { name: /Fé no deserto/ }));

  expect({ cutLevel: screen.queryByText(CUT_LEVEL), sent: sent() }).toEqual({
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
    cutLevel: screen.queryByText(CUT_LEVEL),
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
  await screen.findByText(CUT_LEVEL);

  expect(sent()).toEqual(["POST /api/cuts/35/discard", "POST /api/cuts/34/choose"]);
});
