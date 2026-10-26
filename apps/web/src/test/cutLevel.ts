import { screen } from "@testing-library/react";

import type { RecordedCall } from "./fakeApi";
import { fakePlayers, type FakePlayers } from "./fakePlayers";
import { cutPreview, processedSermon, shownCut } from "./fixtures";
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

/** Opens the level of cut 34 (``shownCut``) with doubles of the API and the players. */
export async function openCut(routes: Parameters<typeof fakeShellApi>[0] = {}): Promise<OpenedCut> {
  const calls = fakeShellApi({
    "GET /api/cuts/34": { body: shownCut() },
    "GET /api/cuts/34/preview": { body: cutPreview() },
    "GET /api/sermons/12": { body: processedSermon({ sermon_start: SERMON_START }) },
    ...routes,
  });
  const players = fakePlayers();
  renderRoute("/cuts/34", players);
  const video = await screen.findByLabelText("Prévia do corte");
  return { calls, players, video };
}
