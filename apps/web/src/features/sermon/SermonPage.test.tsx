import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { fakePlayers } from "../../test/fakePlayers";
import { processedSermon, shownSermon } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("shows the sermon's level, with the timeline, instead of the placeholder", async () => {
  fakeShellApi({ "GET /api/sermons/12": { body: shownSermon() } });

  renderRoute("/sermons/12");

  expect(await screen.findByRole("region", { name: "Timeline" })).toBeInTheDocument();
  expect(screen.queryByText("Esta tela está em construção.")).toBeNull();
});

test("previews the live on YouTube from the sermon's start before processing", async () => {
  fakeShellApi({ "GET /api/sermons/12": { body: shownSermon({ live_start: 1800 }) } });
  const players = fakePlayers();

  renderRoute("/sermons/12", players);
  await screen.findByRole("region", { name: "Timeline" });

  expect(players.created.map(({ kind, args }) => [kind, ...args])).toEqual([
    ["youtube", "abcdefghijk", 1800],
  ]);
});

test("previews the processed video, served by the API, once the sermon is processed", async () => {
  fakeShellApi({ "GET /api/sermons/12": { body: processedSermon({ sermon_start: 1801.2 }) } });
  const players = fakePlayers();

  renderRoute("/sermons/12", players);

  const video = await screen.findByLabelText("Prévia da pregação processada");
  expect(video).toHaveAttribute("src", "/api/sermons/12/video");
  expect(players.created.map(({ kind, args }) => [kind, ...args])).toEqual([
    ["video", video, 1801.2],
  ]);
});

test("previews the live on YouTube outside the processed stretch", async () => {
  fakeShellApi({ "GET /api/sermons/12": { body: processedSermon({ live_duration: 7080 }) } });
  const players = fakePlayers();
  renderRoute("/sermons/12", players);
  const timeline = await screen.findByRole("region", { name: "Timeline" });
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
    DOMRect.fromRect({ x: 0, y: 0, width: 1000, height: 100 }),
  );

  fireEvent.pointerDown(within(timeline).getByLabelText("Régua da live"), { clientX: 100 });

  const { kind, args } = players.current();
  expect([kind, ...args]).toEqual(["youtube", "abcdefghijk", 708]);
});

test.each(["created", "trimmed", "processing", "processed", "failed"] as const)(
  "keeps the preview and the timeline on a %s sermon, without the list's actions",
  async (status) => {
    fakeShellApi({ "GET /api/sermons/12": { body: shownSermon({ status }) } });

    renderRoute("/sermons/12");

    expect(await screen.findByRole("region", { name: "Timeline" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nova pregação" })).toBeNull();
  },
);

test("plays the preview from the transport", async () => {
  fakeShellApi({ "GET /api/sermons/12": { body: shownSermon() } });
  const players = fakePlayers();
  renderRoute("/sermons/12", players);

  await userEvent.click(await screen.findByRole("button", { name: "Reproduzir" }));

  expect(players.current().playing).toBe(true);
});
