import { act, fireEvent, screen, within } from "@testing-library/react";
import { afterEach } from "vitest";

import type { RecordedCall } from "../../test/fakeApi";
import { fakePlayers, type FakePlayers } from "../../test/fakePlayers";
import { shownSermon } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

/** jsdom lays nothing out: the timeline is 1000 px wide from x = 0. */
function layOutTimeline() {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
    DOMRect.fromRect({ x: 0, y: 0, width: 1000, height: 100 }),
  );
}

let calls: RecordedCall[] = [];
let players: FakePlayers;

async function timelineOf(sermon = shownSermon()): Promise<HTMLElement> {
  calls = fakeShellApi({ "GET /api/sermons/12": { body: sermon } });
  players = fakePlayers();
  renderRoute("/sermons/12", players);
  return screen.findByRole("region", { name: "Timeline" });
}

test("labels the clip as the sermon, with its length, once it has borders", async () => {
  const timeline = await timelineOf(shownSermon({ live_start: 1800, live_end: 4275 }));

  expect(within(timeline).getByText("Pregação · 41:15")).toBeInTheDocument();
});

test("labels the clip as the whole live while the sermon has no borders", async () => {
  const timeline = await timelineOf(
    shownSermon({ status: "created", live_start: null, live_end: null, live_duration: 7080 }),
  );

  expect(within(timeline).getByText("Live inteira · 1:58:00")).toBeInTheDocument();
});

const LIVE = 7080;
const percent = (seconds: number) => `${(seconds / LIVE) * 100}%`;

test("draws the clip between the borders, over the whole live faded behind it", async () => {
  const timeline = await timelineOf(
    shownSermon({ live_start: 1800, live_end: 4275, live_duration: LIVE }),
  );

  const clip = within(timeline).getByRole("group", { name: "Pregação na live" });
  const faded = timeline.querySelector("[data-faded]");
  expect([clip.style.left, clip.style.width, faded?.getAttribute("style")]).toEqual([
    percent(1800),
    percent(2475),
    "left: 0%; width: 100%;",
  ]);
});

test("marks the ruler in time of the live, every 15 minutes of a two-hour live", async () => {
  const timeline = await timelineOf(shownSermon({ live_duration: LIVE }));

  const ruler = within(timeline).getByLabelText("Régua da live");
  expect(within(ruler).getAllByText(/\d/).map((mark) => mark.textContent)).toEqual([
    "0:00",
    "15:00",
    "30:00",
    "45:00",
    "1:00:00",
    "1:15:00",
    "1:30:00",
    "1:45:00",
  ]);
});

test("draws no thumbnails nor waveform, which the API does not serve", async () => {
  const timeline = await timelineOf();

  expect({
    images: timeline.querySelectorAll("img, canvas").length,
    calls: calls.map(({ method, url }) => `${method} ${url}`).sort(),
  }).toEqual({
    images: 0,
    calls: ["GET /api/me", "GET /api/sermons/12", "GET /api/sermons/12", "GET /api/status"],
  });
});

test("keeps the screen when the live's duration is unknown", async () => {
  const timeline = await timelineOf(
    shownSermon({ status: "created", live_duration: null, live_start: null, live_end: null }),
  );

  expect(within(timeline).getByText("Duração da live indisponível.")).toBeInTheDocument();
});

test("moves the cursor as the player plays", async () => {
  const timeline = await timelineOf(shownSermon({ live_duration: LIVE }));

  act(() => players.current().moveTo(3540));

  expect(within(timeline).getByLabelText("Cursor").style.left).toBe("50%");
});

test("seeks the player to the time clicked on the ruler", async () => {
  const timeline = await timelineOf(shownSermon({ live_duration: LIVE }));
  layOutTimeline();

  fireEvent.pointerDown(within(timeline).getByLabelText("Régua da live"), { clientX: 250 });

  expect(players.current().seeks).toEqual([1770]);
});
