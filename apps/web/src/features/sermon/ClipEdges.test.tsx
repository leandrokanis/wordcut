import { act, fireEvent, screen, within } from "@testing-library/react";
import { afterEach } from "vitest";

import { apiError, type RecordedCall } from "../../test/fakeApi";
import { fakePlayers, type FakePlayers } from "../../test/fakePlayers";
import { shownSermon } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

// A two-hour live drawn 1000 px wide: 1 px is 7.08 s of the live.
const LIVE = 7080;
const at = (seconds: number) => (seconds / LIVE) * 1000;

let calls: RecordedCall[];
let players: FakePlayers;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function openSermon(routes: Parameters<typeof fakeShellApi>[0] = {}) {
  calls = fakeShellApi({
    "GET /api/sermons/12": { body: shownSermon({ live_start: 1800, live_end: 4275 }) },
    "PATCH /api/sermons/12": ({ body }) => ({ body: patched(body) }),
    ...routes,
  });
  players = fakePlayers();
  renderRoute("/sermons/12", players);
  const timeline = await screen.findByRole("region", { name: "Timeline" });
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
    DOMRect.fromRect({ x: 0, y: 0, width: 1000, height: 100 }),
  );
  return timeline;
}

function patched(body: unknown) {
  const { start, end } = body as { start: number; end: number };
  return shownSermon({ live_start: start, live_end: end, duration: end - start });
}

function edge(timeline: HTMLElement, name: "Início da pregação" | "Fim da pregação") {
  return within(timeline).getByRole("slider", { name });
}

function patches() {
  return calls.filter(({ method }) => method === "PATCH");
}

test("shows the border's frame in the preview while dragging it", async () => {
  const timeline = await openSermon();
  const start = edge(timeline, "Início da pregação");

  fireEvent.pointerDown(start, { clientX: at(1800) });
  fireEvent.pointerMove(start, { clientX: at(2124) });
  fireEvent.pointerMove(start, { clientX: at(2478) });

  expect(players.current().seeks).toEqual([2124, 2478]);
});

test("saves the borders once, as numbers, when the dragged border is released", async () => {
  const timeline = await openSermon();
  const start = edge(timeline, "Início da pregação");

  fireEvent.pointerDown(start, { clientX: at(1800) });
  fireEvent.pointerMove(start, { clientX: at(2124) });
  fireEvent.pointerMove(start, { clientX: at(2478) });
  fireEvent.pointerUp(start, { clientX: at(2478) });

  expect(patches().map(({ url, body }) => [url, body])).toEqual([
    ["/api/sermons/12", { start: 2478, end: 4275 }],
  ]);
});

test("stops a dragged border a minute away from the other", async () => {
  const timeline = await openSermon();
  const start = edge(timeline, "Início da pregação");

  fireEvent.pointerDown(start, { clientX: at(1800) });
  fireEvent.pointerMove(start, { clientX: at(5000) });

  expect(start).toHaveAttribute("aria-valuenow", "4215");
});

test("stops the dragged end border a minute after the start", async () => {
  const timeline = await openSermon();
  const end = edge(timeline, "Fim da pregação");

  fireEvent.pointerDown(end, { clientX: at(4275) });
  fireEvent.pointerMove(end, { clientX: at(1000) });

  expect(end).toHaveAttribute("aria-valuenow", "1860");
});

function dragStartTo(timeline: HTMLElement, seconds: number) {
  const start = edge(timeline, "Início da pregação");
  fireEvent.pointerDown(start, { clientX: at(1800) });
  fireEvent.pointerMove(start, { clientX: at(seconds) });
  fireEvent.pointerUp(start, { clientX: at(seconds) });
}

test("says Salvo only once the API has saved the borders", async () => {
  let answer = () => {};
  const timeline = await openSermon({
    "PATCH /api/sermons/12": ({ body }) =>
      new Promise((resolve) => {
        answer = () => resolve({ body: patched(body) });
      }),
  });

  dragStartTo(timeline, 2124);
  const before = screen.queryByText("Salvo");
  act(() => answer());

  expect([before, await screen.findByText("Salvo")]).toEqual([null, expect.anything()]);
});

test.each([
  [apiError(409, "sermon_too_short", "A pregação precisa ter pelo menos 60 s.")],
  [apiError(409, "busy", "Máquina ocupada: processando a pregação 7.")],
  [apiError(400, "invalid_argument", "As bordas precisam ficar dentro da live.")],
])("shows why the borders were not saved and puts them back: %j", async (reply) => {
  const timeline = await openSermon({ "PATCH /api/sermons/12": reply });

  dragStartTo(timeline, 2124);
  const message = (reply as { body: { error: { message: string } } }).body.error.message;
  await screen.findByText(message);

  expect([
    edge(timeline, "Início da pregação").getAttribute("aria-valuenow"),
    screen.queryByText("Salvo"),
  ]).toEqual(["1800", null]);
});

/** Opens the sermon with the cursor at ``cursor`` and the clock under the test's control. */
async function openAtCursor(cursor: number, routes: Parameters<typeof fakeShellApi>[0] = {}) {
  const timeline = await openSermon(routes);
  act(() => players.current().moveTo(cursor));
  vi.useFakeTimers();
  return timeline;
}

afterEach(() => {
  vi.useRealTimers();
});

function press(key: string, init: KeyboardEventInit = {}, target: Element = document.body) {
  fireEvent.keyDown(target, { key, ...init });
}

function patchedBodies() {
  return patches().map(({ body }) => body);
}

test("brings the start to the cursor with I and saves it half a second later", async () => {
  await openAtCursor(2000);

  press("i");
  const before = patchedBodies();
  act(() => vi.advanceTimersByTime(500));

  expect([before, patchedBodies()]).toEqual([[], [{ start: 2000, end: 4275 }]]);
});

test("saves I and O pressed in a row as one change", async () => {
  await openAtCursor(2000);

  press("i");
  act(() => vi.advanceTimersByTime(200));
  act(() => players.current().moveTo(4000));
  press("o");
  act(() => vi.advanceTimersByTime(500));

  expect(patchedBodies()).toEqual([{ start: 2000, end: 4000 }]);
});

test("saves half a second after the last press, not the first", async () => {
  await openAtCursor(2000);

  press("i");
  act(() => vi.advanceTimersByTime(400));
  act(() => players.current().moveTo(2100));
  press("i");
  act(() => vi.advanceTimersByTime(400));
  const before = patchedBodies();
  act(() => vi.advanceTimersByTime(100));

  expect([before, patchedBodies()]).toEqual([[], [{ start: 2100, end: 4275 }]]);
});

test.each([
  ["i", 4250, "O início precisa ficar antes do fim, com pelo menos 1 min de pregação."],
  ["o", 1830, "O fim precisa ficar depois do início, com pelo menos 1 min de pregação."],
])("refuses %s under a minute from the other border, saying why", async (key, cursor, why) => {
  await openAtCursor(cursor);

  press(key);
  act(() => vi.advanceTimersByTime(500));

  expect([screen.getByRole("alert").textContent, patchedBodies()]).toEqual([why, []]);
});

test("leaves the borders alone while the sermon is processing", async () => {
  const timeline = await openAtCursor(2000, {
    "GET /api/sermons/12": { body: shownSermon({ status: "processing" }) },
  });

  press("i");
  act(() => vi.advanceTimersByTime(500));

  expect([within(timeline).queryAllByRole("slider").length, patchedBodies()]).toEqual([0, []]);
});

test("ignores I typed into a text field", async () => {
  await openAtCursor(2000);
  const field = document.body.appendChild(document.createElement("input"));

  press("i", {}, field);
  act(() => vi.advanceTimersByTime(500));

  field.remove();
  expect(patchedBodies()).toEqual([]);
});

test.each([{ ctrlKey: true }, { metaKey: true }, { altKey: true }])(
  "ignores I with a modifier held: %j",
  async (modifier) => {
    await openAtCursor(2000);

    press("i", modifier);
    act(() => vi.advanceTimersByTime(500));

    expect(patchedBodies()).toEqual([]);
  },
);

test("brings the end to the cursor with the Fim aqui button", async () => {
  await openAtCursor(4000);

  fireEvent.click(screen.getByRole("button", { name: /Fim aqui/ }));
  act(() => vi.advanceTimersByTime(500));

  expect(patchedBodies()).toEqual([{ start: 1800, end: 4000 }]);
});

test("disables Início aqui and Fim aqui while the sermon is processing", async () => {
  await openAtCursor(2000, {
    "GET /api/sermons/12": { body: shownSermon({ status: "processing" }) },
  });

  const buttons = [/Início aqui/, /Fim aqui/].map((name) => screen.getByRole("button", { name }));

  expect(buttons.map((button) => button.hasAttribute("disabled"))).toEqual([true, true]);
});

test("labels the whole live as the sermon as soon as a border is marked", async () => {
  const timeline = await openAtCursor(2000, {
    "GET /api/sermons/12": {
      body: shownSermon({ status: "created", live_start: null, live_end: null }),
    },
  });

  press("i");

  expect(within(timeline).getByText("Pregação · 1:24:40")).toBeInTheDocument();
});
