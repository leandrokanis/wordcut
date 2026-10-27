import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { apiError, type RecordedCall } from "../../test/fakeApi";
import { fakeEventSource } from "../../test/fakeEventSource";
import { fakePlayers, type FakePlayers } from "../../test/fakePlayers";
import { runningTask, shownSermon } from "../../test/fixtures";
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

const LAYOUT = { width: 160, height: 90, times: [0, 1770, 3540, 5310] };
const PEAKS = { buckets: 4, peaks: [0.1, 1, 0.5, 0] };

/** The timeline of a sermon whose media is prepared, served by the API. */
async function preparedTimelineOf(sermon = shownSermon({ live_duration: LIVE })) {
  calls = fakeShellApi({
    "GET /api/sermons/12": { body: sermon },
    "GET /api/sermons/12/thumbnails.json": { body: LAYOUT },
    "GET /api/sermons/12/waveform": { body: PEAKS },
  });
  players = fakePlayers();
  renderRoute("/sermons/12", players);
  return screen.findByRole("region", { name: "Timeline" });
}

/** The prototype's ``innerBg``: the clip shows only its stretch of the whole live's image, as
 * the browser writes it back. */
function innerBackground(start: number, end: number) {
  return {
    size: `${(LIVE / (end - start)) * 100}% 100%`,
    position: `${(start / (LIVE - (end - start))) * 100}% 0px`,
  };
}

test("draws the live's thumbnails faded behind the video track and cropped in the clip", async () => {
  const timeline = await preparedTimelineOf();
  const track = within(timeline).getByLabelText("Faixa Vídeo");

  await waitFor(() => expect(track.querySelector("[data-faded]")).toHaveStyle({
    backgroundImage: `url(/api/sermons/12/thumbnails?v=1)`,
  }));
  const clip = within(track).getByRole("group", { name: "Pregação na live" });
  const inner = innerBackground(1800, 4275);
  expect([clip.style.backgroundImage, clip.style.backgroundSize, clip.style.backgroundPosition]).toEqual([
    'url("/api/sermons/12/thumbnails?v=1")',
    inner.size,
    inner.position,
  ]);
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

test("draws the live's waveform faded behind the audio track and cropped in the clip", async () => {
  const timeline = await preparedTimelineOf();
  const track = within(timeline).getByLabelText("Faixa Áudio");
  const faded = track.querySelector("[data-faded]") as HTMLElement;

  await waitFor(() => expect(faded.style.backgroundImage).toMatch(/^url\("data:image\/svg\+xml,/));
  const clip = within(track).getByLabelText("Áudio da pregação");
  const inner = innerBackground(1800, 4275);
  expect([clip.style.backgroundImage, clip.style.backgroundSize, clip.style.backgroundPosition]).toEqual([
    faded.style.backgroundImage,
    inner.size,
    inner.position,
  ]);
});

test("draws a bar for each peak, as tall as the peak, in time order", async () => {
  const timeline = await preparedTimelineOf();
  const faded = within(timeline).getByLabelText("Faixa Áudio").querySelector("[data-faded]");

  await waitFor(() => expect((faded as HTMLElement).style.backgroundImage).not.toBe(""));
  const svg = decodeURIComponent((faded as HTMLElement).style.backgroundImage);
  const heights = [...svg.matchAll(/v([\d.]+)h-2z/g)].map(([, height]) => Number(height));
  expect(heights).toEqual([3.4, 34, 17, 2]);
});

const PREPARING = { status: "pending", error: null, task_id: 31 } as const;

test("tells the media is being prepared, with plain tracks and the borders still editable", async () => {
  fakeEventSource();
  const timeline = await timelineOf(shownSermon({ live_duration: LIVE, timeline: PREPARING }));

  expect({
    note: within(timeline).queryByText("Preparando a timeline…") !== null,
    handles: within(timeline).getAllByRole("slider").length,
    images: [...timeline.querySelectorAll<HTMLElement>("[data-faded]")].map(
      (faded) => faded.style.backgroundImage,
    ),
    media: calls.filter(({ url }) => /thumbnails|waveform/.test(url)).length,
  }).toEqual({ note: true, handles: 2, images: ["", ""], media: 0 });
});

test("draws the thumbnails and the waveform once the preparation ends, without reloading", async () => {
  const events = fakeEventSource();
  let sermon = shownSermon({ live_duration: LIVE, timeline: PREPARING });
  calls = fakeShellApi({
    "GET /api/sermons/12": () => ({ body: sermon }),
    "GET /api/sermons/12/thumbnails.json": { body: LAYOUT },
    "GET /api/sermons/12/waveform": { body: PEAKS },
  });
  renderRoute("/sermons/12", fakePlayers());
  const timeline = await screen.findByRole("region", { name: "Timeline" });
  const [stream] = events.streams();

  sermon = shownSermon({ live_duration: LIVE });
  act(() => stream.emit("done", runningTask({ id: 31, kind: "prepare", status: "succeeded" })));

  const video = within(timeline).getByLabelText("Faixa Vídeo").querySelector("[data-faded]");
  await waitFor(() =>
    expect(video).toHaveStyle({ backgroundImage: "url(/api/sermons/12/thumbnails?v=1)" }),
  );
  expect([stream.url, within(timeline).queryByText("Preparando a timeline…")]).toEqual([
    "/api/tasks/31/events",
    null,
  ]);
});

const FAILED = {
  status: "failed",
  error: { code: "youtube_error", message: "Não foi possível preparar." },
  task_id: null,
} as const;

test("warns that the media failed and prepares it again on Tentar de novo", async () => {
  fakeEventSource();
  calls = fakeShellApi({
    "GET /api/sermons/12": { body: shownSermon({ live_duration: LIVE, timeline: FAILED }) },
    "POST /api/sermons/12/prepare": {
      status: 202,
      body: { task_id: 32, kind: "prepare", status: "running", sermon_id: 12 },
    },
  });
  renderRoute("/sermons/12", fakePlayers());
  const timeline = await screen.findByRole("region", { name: "Timeline" });
  const warning = within(timeline).getByRole("status");
  const told = warning.textContent;

  await userEvent.click(within(warning).getByRole("button", { name: "Tentar de novo" }));

  expect([
    told?.startsWith("Miniaturas e forma de onda indisponíveis."),
    calls.filter(({ method }) => method === "POST").map(({ url }) => url),
    await within(timeline).findByText("Preparando a timeline…"),
  ]).toEqual([true, ["/api/sermons/12/prepare"], expect.anything()]);
});

test("draws only the waveform, without a warning, for a live without thumbnails", async () => {
  calls = fakeShellApi({
    "GET /api/sermons/12": { body: shownSermon({ live_duration: LIVE }) },
    "GET /api/sermons/12/thumbnails.json": apiError(404, "not_found", "Sem miniaturas."),
    "GET /api/sermons/12/waveform": { body: PEAKS },
  });
  renderRoute("/sermons/12", fakePlayers());
  const timeline = await screen.findByRole("region", { name: "Timeline" });
  const [video, audio] = [...timeline.querySelectorAll<HTMLElement>("[data-faded]")];

  await waitFor(() => expect(audio.style.backgroundImage).not.toBe(""));
  expect([video.style.backgroundImage, within(timeline).queryByRole("status")]).toEqual(["", null]);
});

test("opening a sermon whose media is ready never prepares it again", async () => {
  const timeline = await preparedTimelineOf();
  const audio = within(timeline).getByLabelText("Faixa Áudio").querySelector("[data-faded]");

  await waitFor(() => expect((audio as HTMLElement).style.backgroundImage).not.toBe(""));
  expect(calls.filter(({ method }) => method === "POST")).toEqual([]);
});
