import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { Me } from "../api/types";
import type { RecordedCall } from "./fakeApi";
import { fakePlayers, type FakePlayers } from "./fakePlayers";
import { cutPreview, defaultRenderOptions, processedSermon, shownCut } from "./fixtures";
import { renderRoute } from "./renderRoute";
import { fakeShellApi } from "./shellApi";

/** Where the processed video of the cut's sermon starts in the live. */
export const SERMON_START = 1800;

/** Seconds of the live at ``sermonSeconds`` of the sermon. */
export const live = (sermonSeconds: number) => SERMON_START + sermonSeconds;

export interface OpenedCut {
  calls: RecordedCall[];
  players: FakePlayers;
  video: HTMLElement;
}

/** Opens the level of cut 34 (``shownCut``) with doubles of the API and the players, for the
 * administrator unless ``me`` says otherwise. */
export async function openCut(
  routes: Parameters<typeof fakeShellApi>[0] = {},
  me?: Me,
): Promise<OpenedCut> {
  const calls = fakeShellApi(
    {
      "GET /api/cuts/34": { body: shownCut() },
      "GET /api/cuts/34/preview": { body: cutPreview() },
      "GET /api/sermons/12": { body: processedSermon({ sermon_start: SERMON_START }) },
      ...routes,
    },
    me,
  );
  const players = fakePlayers();
  renderRoute("/cuts/34", players);
  const video = await screen.findByLabelText("Prévia do corte");
  return { calls, players, video };
}

export const ESTIMATE = "/api/cuts/34/renders/estimate";

/** The estimate's query for ``defaultRenderOptions``, in the order the web sends it. */
export const DEFAULT_QUERY =
  "fillers=remove&stammers=remove&pauses=natural&smooth_joins=true&fade=true&normalize=true" +
  "&caption=true&resolution=1080x1920&quality=high";

/** Opens cut 34 and its Exportar 9:16 dialog; the default options are estimated at 61 s. */
export async function openExportDialog(
  routes: Parameters<typeof fakeShellApi>[0] = {},
): Promise<OpenedCut & { dialog: HTMLElement }> {
  const opened = await openCut({
    [`GET ${ESTIMATE}?${DEFAULT_QUERY}`]: {
      body: { duration: 61, options: defaultRenderOptions() },
    },
    ...routes,
  });
  await userEvent.click(screen.getByRole("button", { name: "Exportar" }));
  await userEvent.click(screen.getByRole("button", { name: /Exportar 9:16…/ }));
  return { ...opened, dialog: screen.getByRole("dialog", { name: "Exportar 9:16" }) };
}
