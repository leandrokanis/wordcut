import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import type { SermonShown } from "../../api/types";
import { apiError, type RecordedCall } from "../../test/fakeApi";
import { fakeEventSource } from "../../test/fakeEventSource";
import { fakePlayers, type FakePlayers } from "../../test/fakePlayers";
import { processedSermon, runningTask, shownSermon } from "../../test/fixtures";
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

describe("while the sermon processes", () => {
  let calls: RecordedCall[];

  const LAUNCHED = {
    status: 202,
    body: { task_id: 9, kind: "process", status: "running", sermon_id: 12 },
  };

  async function openSermon(
    sermon: SermonShown = shownSermon(),
    routes: Parameters<typeof fakeShellApi>[0] = {},
    players: FakePlayers = fakePlayers(),
  ) {
    calls = fakeShellApi({
      "GET /api/sermons/12": { body: sermon },
      "POST /api/sermons/12/process": LAUNCHED,
      "PATCH /api/sermons/12": ({ body }: RecordedCall) => {
        const { start, end } = body as { start: number; end: number };
        return { body: shownSermon({ live_start: start, live_end: end }) };
      },
      ...routes,
    });
    renderRoute("/sermons/12", players);
    await screen.findByRole("region", { name: "Timeline" });
  }

  async function launch() {
    await userEvent.click(screen.getByRole("button", { name: "Processar" }));
  }

  /** Drags the start border, at 1800 s of the 7080 s live, if the screen offers it. */
  function dragStart() {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
      DOMRect.fromRect({ x: 0, y: 0, width: 1000, height: 100 }),
    );
    const timeline = screen.getByRole("region", { name: "Timeline" });
    const start = within(timeline).queryByRole("slider", { name: "Início da pregação" });
    if (start) {
      fireEvent.pointerDown(start, { clientX: 254 });
      fireEvent.pointerMove(start, { clientX: 300 });
      fireEvent.pointerUp(start, { clientX: 300 });
    }
  }

  function borderSaves() {
    return calls.filter(({ method }) => method === "PATCH");
  }

  test("follows the launched task and locks the borders once the API accepts it", async () => {
    const { streams } = fakeEventSource();
    await openSermon();

    await launch();
    dragStart();

    expect({ streams: streams().map(({ url }) => url), saves: borderSaves().length }).toEqual({
      streams: ["/api/tasks/9/events"],
      saves: 0,
    });
  });

  const BUSY = "A máquina está ocupada: processando a pregação 7.";

  test("keeps the borders free when the API refuses the processing", async () => {
    const { streams } = fakeEventSource();
    await openSermon(shownSermon(), {
      "POST /api/sermons/12/process": apiError(409, "busy", BUSY),
    });

    await launch();
    await screen.findByText(BUSY);
    dragStart();

    expect({ streams: streams().length, saves: borderSaves().length }).toEqual({
      streams: 0,
      saves: 1,
    });
  });

  test("follows the task that was already running when the sermon opens", async () => {
    const { streams } = fakeEventSource();

    await openSermon(shownSermon({ status: "processing", last_task: runningTask({ id: 15 }) }));

    expect(streams().map(({ url }) => url)).toEqual(["/api/tasks/15/events"]);
  });

  /** Tries every way of changing the borders or playing, and says what the screen allowed. */
  function tryToEdit() {
    const enabled = (name: RegExp) => {
      const button = screen.queryByRole("button", { name });
      return button && !button.hasAttribute("disabled");
    };
    const allowed = {
      startHere: enabled(/Início aqui/),
      endHere: enabled(/Fim aqui/),
      play: enabled(/^Reproduzir$/),
      process: enabled(/^Processa/),
    };
    vi.useFakeTimers();
    dragStart();
    fireEvent.keyDown(document.body, { key: "i" });
    fireEvent.keyDown(document.body, { key: "o" });
    act(() => vi.advanceTimersByTime(500));
    vi.useRealTimers();
    return { ...allowed, edits: borderSaves().length > 0 };
  }

  const LOCKED = { edits: false, startHere: false, endHere: false, play: false, process: false };

  test("locks the editor as soon as the API accepts the processing, before any progress", async () => {
    fakeEventSource();
    await openSermon();

    await launch();

    expect(tryToEdit()).toEqual(LOCKED);
  });

  test("locks the editor of a sermon that was already processing when it opens", async () => {
    fakeEventSource();

    await openSermon(shownSermon({ status: "processing", last_task: runningTask({ id: 15 }) }));

    expect(tryToEdit()).toEqual(LOCKED);
  });

  test("pauses the preview that was playing once the processing starts", async () => {
    fakeEventSource();
    const players = fakePlayers();
    await openSermon(shownSermon(), {}, players);
    await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));

    await launch();

    expect(players.current().playing).toBe(false);
  });

  test("keeps Processar off while the API has not answered, launching once", async () => {
    fakeEventSource();
    let answer: (reply: typeof LAUNCHED) => void = () => {};
    await openSermon(shownSermon(), {
      "POST /api/sermons/12/process": () => new Promise((resolve) => (answer = resolve)),
    });

    await launch();
    const button = screen.getByRole("button", { name: "Processar" });
    await userEvent.click(button);
    const pending = {
      disabled: button.hasAttribute("disabled"),
      posts: calls.filter(({ method }) => method === "POST").length,
    };
    await act(async () => answer(LAUNCHED));

    expect(pending).toEqual({ disabled: true, posts: 1 });
  });

  const FAILED = { code: "youtube_error", message: "O YouTube recusou o download." };

  test.each([
    ["done", runningTask({ status: "succeeded", progress: 1 }), processedSermon(), null],
    [
      "failed",
      runningTask({ status: "failed", error: FAILED }),
      shownSermon({
        status: "failed",
        last_task: runningTask({ status: "failed", error: FAILED }),
      }),
      true,
    ],
  ] as const)(
    "frees the editor and reloads the sermon when the task is %s, without reloading the page",
    async (event, task, after, process) => {
      const { streams } = fakeEventSource();
      let ended = false;
      await openSermon(shownSermon(), {
        "GET /api/sermons/12": () => ({ body: ended ? after : shownSermon() }),
      });
      await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));
      await launch();

      const loads = () =>
        calls.filter(({ method, url }) => method === "GET" && url === "/api/sermons/12").length;
      const before = loads();

      ended = true;
      act(() => streams()[0].emit(event, task));
      await waitFor(() => expect(loads()).toBeGreaterThan(before));
      await screen.findByRole("slider", { name: "Início da pregação" });

      expect(tryToEdit()).toEqual({
        edits: true,
        startHere: true,
        endHere: true,
        play: true,
        process,
      });
    },
  );
});
