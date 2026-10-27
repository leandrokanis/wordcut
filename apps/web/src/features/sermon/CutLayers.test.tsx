import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import type { ListedCut, SermonShown } from "../../api/types";
import { apiError, type RecordedCall, type Reply } from "../../test/fakeApi";
import { fakeEventSource } from "../../test/fakeEventSource";
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

// A two-hour live drawn 1000 px wide: 1 px is 7.08 s of the live.
const LIVE = 7080;
const percent = (seconds: number) => `${(seconds / LIVE) * 100}%`;
const px = (seconds: number) => (seconds / LIVE) * 1000;
// The default cut's range, 620.5 to 678.9 s of the sermon, in the live: the sermon starts
// at 1801.2 s of it.
const RANGE_START = 1801.2 + 620.5;
const RANGE_END = 1801.2 + 678.9;

let calls: RecordedCall[] = [];

async function timelineOf(
  cuts: ListedCut[],
  sermon: SermonShown = processedSermon({ live_duration: LIVE }),
  me = admin(),
  routes: Parameters<typeof fakeShellApi>[0] = {},
): Promise<HTMLElement> {
  calls = fakeShellApi(
    {
      "GET /api/sermons/12": { body: sermon },
      "GET /api/sermons/12/cuts": { body: { items: cuts } },
      "PATCH /api/cuts/34/range": { body: {} },
      "GET /api/cuts/34": { body: shownCut() },
      "GET /api/cuts/34/preview": { body: cutPreview() },
      ...routes,
    },
    me,
  );
  renderRoute("/sermons/12");
  await within(await screen.findByRole("complementary", { name: "Cortes" })).findAllByRole(
    "listitem",
  );
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
    DOMRect.fromRect({ x: 0, y: 0, width: 1000, height: 100 }),
  );
  return screen.getByRole("region", { name: "Timeline" });
}

/** Presses ``target`` at ``from`` px and lets it go at ``to`` px, through ``through``. */
function drag(target: Element, from: number, ...path: number[]) {
  fireEvent.pointerDown(target, { clientX: from });
  for (const x of path) {
    fireEvent.pointerMove(window, { clientX: x });
  }
  fireEvent.pointerUp(window, { clientX: path[path.length - 1] ?? from });
}

function rangePatches() {
  return calls
    .filter(({ method, url }) => method === "PATCH" && url === "/api/cuts/34/range")
    .map(({ body }) => body);
}

function edge(layer: HTMLElement, side: "l" | "r"): Element {
  return layer.querySelector(`[data-cutedge="${side}"]`) as Element;
}

function layersOf(timeline: HTMLElement): HTMLElement[] {
  return within(timeline).queryAllByRole("group", { name: /^Corte \d+/ });
}

test("draws one layer per cut, in the panel's order, above the video and audio tracks", async () => {
  const timeline = await timelineOf([
    listedCut({ id: 35, status: "chosen", title: "Graça" }),
    listedCut({ id: 34, status: "discarded", title: "Fé no deserto" }),
  ]);

  const heads = [...timeline.querySelectorAll(".tl-heads .th")].map((head) => head.textContent);
  expect({
    layers: layersOf(timeline).map((layer) => layer.getAttribute("aria-label")),
    heads,
  }).toEqual({
    layers: ["Corte 1: Graça", "Corte 2: Fé no deserto"],
    heads: ["", "1Graça", "2Fé no deserto", "Vídeo", "Áudio"],
  });
});

test("places each layer over the cut's range in time of the live, from the sermon's start", async () => {
  const timeline = await timelineOf(
    [listedCut({ start: 630, end: 670, range_start: 620.5, range_end: 678.9 })],
    processedSermon({ live_duration: LIVE, sermon_start: 1801.2 }),
  );

  const [layer] = layersOf(timeline);
  expect([layer.style.left, layer.style.width]).toEqual([
    percent(1801.2 + 620.5),
    percent(678.9 - 620.5),
  ]);
});

test("colors each layer as its card, by place in the list, and marks the discarded one", async () => {
  const timeline = await timelineOf([
    listedCut({ id: 35, title: "Graça" }),
    listedCut({ id: 34, status: "discarded", title: "Fé no deserto" }),
  ]);
  const cards = within(screen.getByRole("complementary", { name: "Cortes" })).getAllByRole(
    "listitem",
  );

  const color = (element: HTMLElement) => element.style.getPropertyValue("--c");
  const layers = layersOf(timeline);
  expect({
    layers: layers.map((layer) => [color(layer), layer.hasAttribute("data-discarded")]),
    distinct: color(layers[0]) !== color(layers[1]),
  }).toEqual({
    layers: cards.map((card) => [color(card), card.hasAttribute("data-discarded")]),
    distinct: true,
  });
});

function edgesOf(layer: HTMLElement): (string | undefined)[] {
  return [...layer.querySelectorAll<HTMLElement>("[data-cutedge]")].map(
    (edge) => edge.dataset.cutedge,
  );
}

test.each([
  ["an admin on a suggested cut", admin(), "suggested", ["l", "r"]],
  ["an admin on a discarded cut", admin(), "discarded", []],
  ["an assistant", assistant(), "suggested", []],
] as const)("gives the layer draggable borders only for %s", async (_, me, status, edges) => {
  const timeline = await timelineOf(
    [listedCut({ status })],
    processedSermon({ live_duration: LIVE }),
    me,
  );

  expect(edgesOf(layersOf(timeline)[0])).toEqual(edges);
});

test("draws no layer before the sermon is processed", async () => {
  fakeShellApi({
    "GET /api/sermons/12": { body: shownSermon({ status: "trimmed" }) },
    "GET /api/sermons/12/cuts": { body: { items: [listedCut()] } },
  });
  renderRoute("/sermons/12");

  const timeline = await screen.findByRole("region", { name: "Timeline" });
  expect(layersOf(timeline)).toEqual([]);
});

test("loads the cuts into the panel and the timeline once the processing is done", async () => {
  const { streams } = fakeEventSource();
  let processed = false;
  fakeShellApi({
    "GET /api/sermons/12": () => ({ body: processed ? processedSermon() : shownSermon() }),
    "GET /api/sermons/12/cuts": { body: { items: [listedCut()] } },
    "POST /api/sermons/12/process": {
      status: 202,
      body: { task_id: 9, kind: "process", status: "running", sermon_id: 12 },
    },
  });
  renderRoute("/sermons/12");
  await userEvent.click(await screen.findByRole("button", { name: "Processar" }));

  processed = true;
  act(() => streams()[0].emit("done", runningTask({ status: "succeeded", progress: 1 })));

  const panel = screen.getByRole("complementary", { name: "Cortes" });
  expect({
    card: (await within(panel).findByRole("listitem")).getAttribute("aria-label"),
    layers: layersOf(screen.getByRole("region", { name: "Timeline" })).length,
  }).toEqual({ card: "Fé no deserto", layers: 1 });
});

test("saves a dragged end border on release, both borders in time of the sermon", async () => {
  const [layer] = layersOf(await timelineOf([listedCut()]));

  drag(edge(layer, "r"), px(RANGE_END), px(RANGE_END) + 5, px(RANGE_END) + 10);

  await waitFor(() => expect(rangePatches()).toEqual([{ start: 620.5, end: 749.7 }]));
});

test.each([
  ["later", 10, 70.8],
  ["earlier", -10, -70.8],
])("saves the whole range dragged by the middle as a shift %s in the sermon", async (_, dx, by) => {
  const [layer] = layersOf(await timelineOf([listedCut()]));
  const middle = px((RANGE_START + RANGE_END) / 2);

  drag(layer, middle, middle + dx / 2, middle + dx);

  await waitFor(() => expect(rangePatches()).toEqual([{ by }]));
});

test("stops a dragged border 10 s from the other", async () => {
  const [layer] = layersOf(await timelineOf([listedCut()]));

  drag(edge(layer, "l"), px(RANGE_START), px(RANGE_START) + 200);

  await waitFor(() => expect(rangePatches()).toEqual([{ start: 668.9, end: 678.9 }]));
});

test.each([
  ["start", -1000, -620.5],
  ["end", 1000, 4274.6 - 1801.2 - 678.9],
])("stops the moved range at the %s of the sermon", async (_, dx, by) => {
  const [layer] = layersOf(await timelineOf([listedCut()]));
  const middle = px((RANGE_START + RANGE_END) / 2);

  drag(layer, middle, middle + dx);

  await waitFor(() => expect(rangePatches()).toEqual([{ by: Math.round(by * 1000) / 1000 }]));
});

function held(reply: Reply) {
  let release = () => {};
  const route = () => new Promise<Reply>((resolve) => (release = () => resolve(reply)));
  return { route, release: () => release() };
}

test("shows the dragged range before the API answers, and the saved one once it does", async () => {
  const saved = held({ body: {} });
  let reloaded = false;
  const timeline = await timelineOf([listedCut()], undefined, undefined, {
    "PATCH /api/cuts/34/range": () => {
      reloaded = true;
      return saved.route();
    },
    "GET /api/sermons/12/cuts": () => ({
      body: {
        items: [listedCut(reloaded ? { range_start: 600, range_end: 678.9 } : {})],
      },
    }),
  });
  const [layer] = layersOf(timeline);

  drag(edge(layer, "l"), px(RANGE_START), px(RANGE_START) - 3, px(RANGE_START) - 10);
  const dragging = layer.style.left;
  await act(async () => saved.release());

  await waitFor(() =>
    expect({ dragging, saved: layersOf(timeline)[0].style.left }).toEqual({
      dragging: percent(RANGE_START - 70.8),
      saved: percent(1801.2 + 600),
    }),
  );
});

test("brings the layer back and says why when the API refuses the range", async () => {
  const timeline = await timelineOf([listedCut()], undefined, undefined, {
    "PATCH /api/cuts/34/range": apiError(
      400,
      "invalid_argument",
      "Nenhuma frase escolhida ficaria na faixa; o corte não pode ficar vazio.",
    ),
  });
  const [layer] = layersOf(timeline);

  drag(edge(layer, "r"), px(RANGE_END), px(RANGE_END) + 50);

  expect({
    alert: (await screen.findByRole("alert")).textContent,
    left: layersOf(timeline)[0].style.left,
    width: layersOf(timeline)[0].style.width,
  }).toEqual({
    alert: "Nenhuma frase escolhida ficaria na faixa; o corte não pode ficar vazio.",
    left: percent(RANGE_START),
    width: percent(678.9 - 620.5),
  });
});

const CUT_LEVEL = "Prévia do corte";

test.each([
  ["a press of the administrator that moves 3 px or less", admin(), "chosen", 3],
  ["a drag of the assistant", assistant(), "chosen", 40],
] as const)("opens the cut without changing its range on %s", async (_, me, status, dx) => {
  const [layer] = layersOf(
    await timelineOf([listedCut({ status })], processedSermon({ live_duration: LIVE }), me),
  );
  const middle = px((RANGE_START + RANGE_END) / 2);

  drag(layer, middle, middle + dx);

  expect({
    cutLevel: await screen.findByLabelText(CUT_LEVEL),
    sent: rangePatches(),
  }).toEqual({
    cutLevel: expect.anything(),
    sent: [],
  });
});

test.each([
  ["a click of the administrator", admin(), 0],
  ["a drag of the administrator", admin(), 40],
  ["a click of the assistant", assistant(), 0],
] as const)("does not open a discarded cut nor change its range on %s", async (_, me, dx) => {
  const [layer] = layersOf(
    await timelineOf(
      [listedCut({ status: "discarded" })],
      processedSermon({ live_duration: LIVE }),
      me,
    ),
  );
  const middle = px((RANGE_START + RANGE_END) / 2);

  drag(layer, middle, middle + dx);
  await act(async () => {});

  expect({
    cutLevel: screen.queryByLabelText(CUT_LEVEL),
    sent: calls.filter(({ method }) => method !== "GET").length,
  }).toEqual({ cutLevel: null, sent: 0 });
});

test("opens a suggested cut from its layer by choosing it, as its card does", async () => {
  const timeline = await timelineOf([listedCut({ status: "suggested" })], undefined, undefined, {
    "POST /api/cuts/34/choose": { body: shownCut() },
  });

  drag(layersOf(timeline)[0], 500);

  expect({
    cutLevel: await screen.findByLabelText(CUT_LEVEL),
    sent: calls
      .filter(({ method }) => method !== "GET")
      .map(({ method, url }) => `${method} ${url}`),
  }).toEqual({
    cutLevel: expect.anything(),
    sent: ["POST /api/cuts/34/choose"],
  });
});
