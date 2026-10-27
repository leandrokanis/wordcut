import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach } from "vitest";

import type { SermonShown } from "../../api/types";
import { apiError, type RecordedCall } from "../../test/fakeApi";
import { fakeEventSource } from "../../test/fakeEventSource";
import { busyMachine, processedSermon, runningTask } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

let spying: AbortController;

beforeEach(() => {
  spying = new AbortController();
});

afterEach(() => {
  spying.abort();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

let calls: RecordedCall[];

async function openSermon(sermon: SermonShown, routes: Parameters<typeof fakeShellApi>[0] = {}) {
  calls = fakeShellApi({ [`GET /api/sermons/${sermon.id}`]: { body: sermon }, ...routes });
  renderRoute(`/sermons/${sermon.id}`);
  await screen.findByRole("region", { name: "Timeline" });
}

async function openMenu() {
  await userEvent.click(screen.getByRole("button", { name: "Exportar" }));
}

test.each([12, 31])(
  "offers the processed sermon %i's 16:9 video for download, named by the API",
  async (id) => {
    await openSermon(processedSermon({ id }));

    await openMenu();

    const item = screen.getByRole("menuitem", { name: /Pregação 16:9/ });
    expect([item.getAttribute("href"), item.getAttribute("download")]).toEqual([
      `/api/sermons/${id}/video`,
      "",
    ]);
  },
);

test.each([
  [1801.2, 4274.6, "1080p · 41:13"],
  [600, 4323.5, "1080p · 1:02:03"],
])(
  "shows the resolution and the duration of the sermon from %s s to %s s",
  async (sermonStart, sermonEnd, subtitle) => {
    await openSermon(
      processedSermon({
        live_start: 0,
        live_end: 7000,
        sermon_start: sermonStart,
        sermon_end: sermonEnd,
      }),
    );

    await openMenu();

    expect(screen.getByRole("menuitem", { name: /Pregação 16:9/ })).toHaveTextContent(subtitle);
  },
);

test("shows only the resolution when the API gives no borders of the sermon", async () => {
  await openSermon(processedSermon({ sermon_start: null, sermon_end: null }));

  await openMenu();

  expect(screen.getByRole("menuitem", { name: /Pregação 16:9/ })).toHaveTextContent(
    /^Pregação 16:9\s*1080p$/,
  );
});

test("offers the download while another heavy task holds the machine, saying it is busy", async () => {
  await openSermon(processedSermon(), {
    "GET /api/status": { body: busyMachine(runningTask({ id: 20, sermon_id: 7 })) },
  });

  await openMenu();

  const note = await within(screen.getByRole("menu")).findByText(
    "Máquina ocupada: processando a pregação 7.",
  );
  const item = screen.getByRole("menuitem", { name: /Pregação 16:9/ });
  expect([note.tagName, item.getAttribute("href"), item.getAttribute("aria-disabled")]).toEqual([
    "P",
    "/api/sermons/12/video",
    null,
  ]);
});

/** Counts the activations of the download link, which jsdom cannot follow. */
function spyDownloads() {
  const downloads: string[] = [];
  document.addEventListener("click", (event) => {
    const link = event.target instanceof Element ? event.target.closest("a[download]") : null;
    if (link) {
      downloads.push(link.getAttribute("href") ?? "");
      event.preventDefault();
    }
  }, { signal: spying.signal });
  return downloads;
}

test("closes with Esc from an item without downloading, giving the focus back to Exportar", async () => {
  await openSermon(processedSermon());
  const downloads = spyDownloads();
  await openMenu();
  await userEvent.keyboard("{ArrowDown}");

  await userEvent.keyboard("{Escape}");

  expect([screen.queryByRole("menu"), downloads, document.activeElement]).toEqual([
    null,
    [],
    screen.getByRole("button", { name: "Exportar" }),
  ]);
});

test("closes on a click outside the menu without downloading", async () => {
  await openSermon(processedSermon());
  const downloads = spyDownloads();
  await openMenu();

  await userEvent.click(screen.getByRole("region", { name: "Timeline" }));

  expect([screen.queryByRole("menu"), downloads]).toEqual([null, []]);
});

test.each(["{ArrowDown}", "{ArrowUp}", "{ArrowDown}{ArrowDown}"])(
  "moves the focus among the menu's items with %s",
  async (keys) => {
    await openSermon(processedSermon());
    await openMenu();

    await userEvent.keyboard(keys);

    expect(document.activeElement).toBe(screen.getByRole("menuitem", { name: /Pregação 16:9/ }));
  },
);

const REPROCESS_NOTE = "Refaz transcrição e sugestões; as edições dos cortes se perdem";

test("offers Reprocessar on a sermon loaded with its borders changed since the processing", async () => {
  await openSermon(processedSermon({ borders_changed: true }));

  await openMenu();

  expect(screen.getByRole("menuitem", { name: /Reprocessar/ })).toHaveTextContent(
    `Reprocessar${REPROCESS_NOTE}`,
  );
});

const LAUNCHED = {
  status: 202,
  body: { task_id: 9, kind: "process", status: "running", sermon_id: 12 },
};

function processPosts() {
  return calls.filter(({ method, url }) => method === "POST" && url.endsWith("/process"));
}

test("reprocesses with force from the menu, the only way the API discards the cuts' edits", async () => {
  fakeEventSource();
  await openSermon(processedSermon({ borders_changed: true }), {
    "POST /api/sermons/12/process": LAUNCHED,
  });
  await openMenu();

  await userEvent.click(screen.getByRole("menuitem", { name: /Reprocessar/ }));

  expect(processPosts().map(({ body }) => body)).toEqual([{ force: true }]);
});

test("offers no Reprocessar while the borders are the processed ones", async () => {
  await openSermon(processedSermon({ borders_changed: false }));

  await openMenu();

  expect(screen.queryByRole("menuitem", { name: /Reprocessar/ })).toBeNull();
});

test("keeps Reprocessar off while another heavy task holds the machine", async () => {
  await openSermon(processedSermon({ borders_changed: true }), {
    "GET /api/status": { body: busyMachine(runningTask({ id: 20, sermon_id: 7 })) },
  });

  await openMenu();
  await within(screen.getByRole("menu")).findByText("Máquina ocupada: processando a pregação 7.");

  expect(screen.getByRole("menuitem", { name: /Reprocessar/ })).toBeDisabled();
});

/** Drags the start border of the 7080 s live and waits for the save. */
async function moveBorder() {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
    DOMRect.fromRect({ x: 0, y: 0, width: 1000, height: 100 }),
  );
  const timeline = screen.getByRole("region", { name: "Timeline" });
  const start = within(timeline).getByRole("slider", { name: "Início da pregação" });
  fireEvent.pointerDown(start, { clientX: 254 });
  fireEvent.pointerMove(start, { clientX: 300 });
  fireEvent.pointerUp(start, { clientX: 300 });
  await vi.waitFor(() => {
    expect(calls.filter(({ method }) => method === "PATCH")).toHaveLength(1);
  });
}

function patchAnswering(changed: boolean) {
  return {
    "PATCH /api/sermons/12": ({ body }: RecordedCall) => {
      const { start, end } = body as { start: number; end: number };
      return {
        body: processedSermon({ live_start: start, live_end: end, borders_changed: changed }),
      };
    },
  };
}

test("offers Reprocessar only in the menu once a saved border change makes it differ", async () => {
  await openSermon(processedSermon(), patchAnswering(true));
  await moveBorder();

  await openMenu();
  await screen.findByRole("menuitem", { name: /Reprocessar/ });

  expect(screen.getAllByText("Reprocessar")).toHaveLength(1);
});

test("drops Reprocessar once the saved borders are back to the processed ones", async () => {
  await openSermon(processedSermon({ borders_changed: true }), patchAnswering(false));
  await moveBorder();

  await openMenu();

  await vi.waitFor(() => {
    expect(screen.queryByRole("menuitem", { name: /Reprocessar/ })).toBeNull();
  });
});

test("says why the API refused the reprocessing, in the level's bar", async () => {
  const busy = "A máquina está ocupada: processando a pregação 7.";
  await openSermon(processedSermon({ borders_changed: true }), {
    "POST /api/sermons/12/process": apiError(409, "busy", busy),
  });
  await openMenu();

  await userEvent.click(screen.getByRole("menuitem", { name: /Reprocessar/ }));

  expect((await screen.findByText(busy)).getAttribute("role")).toBe("alert");
});

test("drops Reprocessar once the reprocessing is done and the sermon reloads", async () => {
  const { streams } = fakeEventSource();
  let done = false;
  await openSermon(processedSermon({ borders_changed: true }), {
    "GET /api/sermons/12": () => ({
      body: processedSermon({ borders_changed: !done }),
    }),
    "POST /api/sermons/12/process": LAUNCHED,
  });
  await openMenu();
  await userEvent.click(screen.getByRole("menuitem", { name: /Reprocessar/ }));

  done = true;
  act(() => streams()[0].emit("done", runningTask({ status: "succeeded", progress: 1 })));
  await openMenu();

  expect(screen.queryByRole("menuitem", { name: /Reprocessar/ })).toBeNull();
});
