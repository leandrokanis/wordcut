import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { openCut, openExportDialog } from "../../test/cutLevel";
import { fakeEventSource } from "../../test/fakeEventSource";
import { cutRender, defaultRenderOptions, renderTask, shownCut } from "../../test/fixtures";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

/** ``GET /api/cuts/34`` gives the exports oldest first (docs/cli.md §8.2). */
const OLDER = cutRender({ id: 7, duration: 58.4, created_at: "2026-10-20T00:23:00-03:00" });
const NEWER = cutRender({
  id: 8,
  duration: 47.8,
  created_at: "2026-10-21T19:05:00-03:00",
  options: defaultRenderOptions({ resolution: "720x1280", caption: false }),
});

async function openMenu(renders = [OLDER, NEWER]) {
  const opened = await openCut({ "GET /api/cuts/34": { body: shownCut({ renders }) } });
  await userEvent.click(screen.getByRole("button", { name: "Exportar" }));
  return opened;
}

test("lists the cut's exports in the Exportar menu, newest first, with date, duration and options", async () => {
  await openMenu();

  expect(
    within(screen.getByRole("list", { name: "Exportações" }))
      .getAllByRole("listitem")
      .map(({ textContent }) => textContent),
  ).toEqual([
    "21/10/2026 19:059:16 · 0:47 · 720p · sem legendaBaixar",
    "20/10/2026 00:239:16 · 0:58 · 1080p · com legendaBaixar",
  ]);
});

test("downloads each export from the API's file route, without a call of its own", async () => {
  const { calls } = await openMenu();
  const links = screen.getAllByRole("link", { name: /Baixar/ });
  const before = calls.length;
  // jsdom does not navigate: the browser's download is not part of the test.
  const stayHere = (event: Event) => event.preventDefault();
  document.addEventListener("click", stayHere);

  await userEvent.click(links[1]);
  document.removeEventListener("click", stayHere);

  expect({
    links: links.map((link) => [link.getAttribute("href"), link.hasAttribute("download")]),
    calls: calls.length - before,
  }).toEqual({
    links: [
      ["/api/renders/8/file", true],
      ["/api/renders/7/file", true],
    ],
    calls: 0,
  });
});

test("shows no Exportações in the menu while the cut has none", async () => {
  await openMenu([]);

  expect({
    list: screen.queryByRole("list", { name: "Exportações" }),
    offer: screen.getByRole("button", { name: /Exportar 9:16…/ }).tagName,
  }).toEqual({ list: null, offer: "BUTTON" });
});

test("lists the new export once the export is done", async () => {
  const { streams } = fakeEventSource();
  const finished = cutRender({ id: 9, created_at: "2026-10-26T10:00:00-03:00" });
  const { dialog } = await openExportDialog({
    "GET /api/cuts/34": { body: shownCut({ renders: [OLDER] }) },
    "POST /api/cuts/34/renders": {
      status: 202,
      body: { task_id: 10, kind: "render", status: "running", cut_id: 34 },
    },
    "GET /api/cuts/34/renders": { body: { items: [finished, OLDER] } },
  });
  await userEvent.click(within(dialog).getByRole("button", { name: "Exportar" }));
  await waitFor(() => expect(streams()).toHaveLength(1));
  act(() => streams()[0].emit("done", renderTask({ status: "succeeded", progress: 1 })));

  await userEvent.click(await screen.findByRole("button", { name: "Exportar" }));

  await waitFor(() =>
    expect(
      screen.getAllByRole("link", { name: /Baixar/ }).map((link) => link.getAttribute("href")),
    ).toEqual(["/api/renders/9/file", "/api/renders/7/file"]),
  );
});
