import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { type RecordedCall } from "../../test/fakeApi";
import { type FakePlayers, fakePlayers } from "../../test/fakePlayers";
import { live, openCut as openCutLevel, SERMON_START } from "../../test/cutLevel";
import { busyMachine, churchCaption, cutWords, shownCut } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

let calls: RecordedCall[];
let players: FakePlayers;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function openCut(routes: Parameters<typeof fakeShellApi>[0] = {}) {
  const opened = await openCutLevel(routes);
  ({ calls, players } = opened);
  return opened.video;
}

function moveTo(sermonSeconds: number) {
  act(() => players.current().moveTo(live(sermonSeconds)));
}

test("previews the cut on the sermon's processed video, never on YouTube", async () => {
  const video = await openCut();

  expect(video).toHaveAttribute("src", "/api/sermons/12/video");
  expect(players.created.map(({ kind, args }) => [kind, ...args])).toEqual([
    ["video", video, SERMON_START],
  ]);
});

test("plays the segments in the cut's order, skipping the gaps, in time of the live", async () => {
  await openCut();
  await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));

  moveTo(3.0);
  moveTo(3.4);
  moveTo(0.9);
  moveTo(1.25);

  expect(players.current().seeks).toEqual([live(2.5), live(0.3), live(1.35)]);
});

test("pauses at the end of the last segment", async () => {
  await openCut();
  await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));

  moveTo(3.4);
  moveTo(1.2);
  moveTo(1.9);

  expect(players.current().playing).toBe(false);
  expect(screen.getByRole("button", { name: "Reproduzir" })).toBeInTheDocument();
});

test("does not go back into the first segment while the third, out of order, plays", async () => {
  await openCut();
  await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));

  moveTo(3.4);
  moveTo(1.2);
  moveTo(2.6);

  expect(players.current().seeks).toEqual([live(2.5), live(0.3), live(1.35)]);
  expect(players.current().playing).toBe(false);
});

// The cut's timeline drawn 1000 px wide: 1 px is 2.35 ms of the cut.
const CUT = 2.35;
const atCut = (cutSeconds: number) => (cutSeconds / CUT) * 1000;

function timelineOf(): HTMLElement {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
    DOMRect.fromRect({ x: 0, y: 0, width: 1000, height: 100 }),
  );
  return screen.getByRole("region", { name: "Timeline" });
}

test("draws each segment on the cut's timeline in proportion to the cut's duration", async () => {
  await openCut();

  const widths = within(timelineOf())
    .getAllByRole("group", { name: /^Trecho/ })
    .map((clip) => parseFloat(clip.style.width));

  expect(widths.map((width) => width.toFixed(3))).toEqual(
    [0.9, 0.9, 0.55].map((span) => ((span / CUT) * 100).toFixed(3)),
  );
});

test("takes the preview to the right point of the right segment from the timeline", async () => {
  await openCut();

  fireEvent.pointerDown(within(timelineOf()).getByLabelText("Régua do corte"), {
    clientX: atCut(2.05),
  });

  const seeks = players.current().seeks;
  expect(seeks[seeks.length - 1]).toBeCloseTo(live(1.6), 6);
  expect(screen.getByLabelText("Tempo do corte")).toHaveTextContent("0:02 / 0:02");
});

test("plays a segment again from the timeline after the end, from the point clicked", async () => {
  await openCut();
  await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));
  moveTo(3.4);
  moveTo(1.2);
  moveTo(1.9);

  fireEvent.pointerDown(within(timelineOf()).getByLabelText("Régua do corte"), {
    clientX: atCut(0.45),
  });
  moveTo(3.4);

  expect(
    players
      .current()
      .seeks.slice(-2)
      .map((seek) => seek.toFixed(3)),
  ).toEqual([live(2.95), live(0.3)].map((seek) => seek.toFixed(3)));
});

test("plays the sequence the API's preview gives", async () => {
  await openCut();

  expect(calls.map(({ method, url }) => `${method} ${url}`)).toContain("GET /api/cuts/34/preview");
});

test("loads and plays the preview while the processing lock is held", async () => {
  await openCut({ "GET /api/status": { body: busyMachine() } });

  await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));

  expect(players.current().playing).toBe(true);
});

test("says the cut is missing when the API does not know it", async () => {
  fakeShellApi({});

  renderRoute("/cuts/99", fakePlayers());

  expect(await screen.findByText("Corte não encontrado.")).toBeInTheDocument();
});

/** The caption's words marked as the one being said. */
function saidNow(): string[] {
  const caption = screen.queryByRole("group", { name: "Legenda na prévia" });
  return caption
    ? Array.from(caption.querySelectorAll('[aria-current="true"]')).map(
        (word) => word.textContent ?? "",
      )
    : [];
}

function captionText(): string | null {
  return screen.queryByRole("group", { name: "Legenda na prévia" })?.textContent ?? null;
}

test("follows the speech word by word, across the jump between segments", async () => {
  await openCut();
  const seen: [string | null, string[]][] = [];
  const look = (sermonSeconds: number) => {
    moveTo(sermonSeconds);
    seen.push([captionText(), saidNow()]);
  };

  look(2.6);
  look(2.92);
  look(3.0);
  look(3.4);
  look(1.0);
  look(1.2);

  expect(seen).toEqual([
    ["Deus governa.", ["Deus"]],
    ["Deus governa.", []],
    ["Deus governa.", ["governa."]],
    ["Irmãos, graça paz.", ["Irmãos,"]],
    ["Irmãos, graça paz.", ["graça"]],
    ["Irmãos, graça paz.", ["paz."]],
  ]);
});

test("shows the cut's spelling fix in the caption", async () => {
  const words = cutWords().map((word) =>
    word.word_id === 1105 ? { ...word, corrected: "DEUS" } : word,
  );
  await openCut({ "GET /api/cuts/34": { body: shownCut({ words }) } });

  moveTo(2.6);

  expect(saidNow()).toEqual(["DEUS"]);
});

test("draws no caption while the cut's caption is off", async () => {
  await openCut({
    "GET /api/cuts/34": { body: shownCut({ caption: churchCaption({ enabled: false }) }) },
  });

  moveTo(2.6);

  expect(captionText()).toBeNull();
});

test("draws the caption with the cut's style", async () => {
  await openCut({
    "GET /api/cuts/34": {
      body: shownCut({ caption: churchCaption({ size: 108, offset: 20, color: "#FFFFFF" }) }),
    },
  });
  moveTo(2.6);

  const caption = screen.getByRole("group", { name: "Legenda na prévia" });
  expect(
    ["--cap-size", "--cap-top", "--cap-color"].map((name) => caption.style.getPropertyValue(name)),
  ).toEqual(["10cqw", "20%", "#FFFFFF"]);
});
