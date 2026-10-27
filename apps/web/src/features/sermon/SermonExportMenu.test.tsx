import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach } from "vitest";

import type { SermonShown } from "../../api/types";
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

async function openSermon(sermon: SermonShown, routes: Parameters<typeof fakeShellApi>[0] = {}) {
  fakeShellApi({ [`GET /api/sermons/${sermon.id}`]: { body: sermon }, ...routes });
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
