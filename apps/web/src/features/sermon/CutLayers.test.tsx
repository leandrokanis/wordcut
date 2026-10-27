import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import type { ListedCut, SermonShown } from "../../api/types";
import type { RecordedCall } from "../../test/fakeApi";
import { fakeEventSource } from "../../test/fakeEventSource";
import {
  admin,
  assistant,
  listedCut,
  processedSermon,
  runningTask,
  shownSermon,
} from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const LIVE = 7080;
const percent = (seconds: number) => `${(seconds / LIVE) * 100}%`;

let calls: RecordedCall[] = [];

async function timelineOf(
  cuts: ListedCut[],
  sermon: SermonShown = processedSermon({ live_duration: LIVE }),
  me = admin(),
): Promise<HTMLElement> {
  calls = fakeShellApi(
    {
      "GET /api/sermons/12": { body: sermon },
      "GET /api/sermons/12/cuts": { body: { items: cuts } },
    },
    me,
  );
  renderRoute("/sermons/12");
  await within(await screen.findByRole("complementary", { name: "Cortes" })).findAllByRole(
    "listitem",
  );
  return screen.getByRole("region", { name: "Timeline" });
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

test("places each layer in time of the live, from the sermon's start in the live", async () => {
  const timeline = await timelineOf(
    [listedCut({ start: 620.5, end: 678.9 })],
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

test.each([
  ["admin", admin()],
  ["assistant", assistant()],
])("draws the layers without handles and changes nothing when one is pressed, as %s", async (_, me) => {
  const timeline = await timelineOf([listedCut()], processedSermon({ live_duration: LIVE }), me);
  const [layer] = layersOf(timeline);

  fireEvent.pointerDown(layer, { clientX: 300 });
  fireEvent.pointerUp(window, { clientX: 400 });

  expect({
    handles: within(layer).queryAllByRole("slider").length,
    sent: calls.filter(({ method }) => method !== "GET").length,
  }).toEqual({ handles: 0, sent: 0 });
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
