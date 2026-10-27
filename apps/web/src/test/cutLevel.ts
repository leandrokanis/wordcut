import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { Cut, CutPreview, CutWord, Me } from "../api/types";
import type { RecordedCall, Reply } from "./fakeApi";
import { fakePlayers, type FakePlayers } from "./fakePlayers";
import {
  cutPreview,
  defaultRenderOptions,
  processedSermon,
  rangeSentences,
  shownCut,
} from "./fixtures";
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

/** The words of the range of ``shownCut``, in sermon time; ``cutWords`` without 1104, 1107
 * and 1108, which it does not play. */
const RANGE_WORDS: CutWord[] = [
  [1101, "Irmãos,", 0.3, 0.7],
  [1102, "graça", 0.8, 1.2],
  [1103, "paz.", 1.35, 1.9],
  [1104, "Então", 2.0, 2.4],
  [1105, "Deus", 2.5, 2.9],
  [1106, "governa.", 2.95, 3.4],
  [1107, "Amém,", 3.6, 3.9],
  [1108, "igreja.", 3.95, 4.2],
].map(([word_id, text, start, end]) => ({
  word_id: word_id as number,
  text: text as string,
  start: start as number,
  end: end as number,
  corrected: null,
}));

type Ranges = { from_word: number; to_word: number }[];

/** Cut 34 playing ``ranges``, as ``GET /api/cuts/34`` gives it after ``cut segments``. */
export function cutPlaying(ranges: Ranges): Cut {
  const wordsOf = ({ from_word, to_word }: Ranges[number]) =>
    RANGE_WORDS.filter(({ word_id }) => from_word <= word_id && word_id <= to_word);
  const segments = ranges.map((range) => {
    const words = wordsOf(range);
    return {
      ...range,
      start: words[0].start,
      end: words[words.length - 1].end,
      text: words.map(({ text }) => text).join(" "),
    };
  });
  const played = new Set(ranges.flatMap(wordsOf).map(({ word_id }) => word_id));
  return shownCut({
    segments,
    duration: segments.reduce((sum, { start, end }) => sum + end - start, 0),
    words: ranges.flatMap(wordsOf),
    edited: true,
    range_sentences: rangeSentences().map((sentence) => {
      const ids = RANGE_WORDS.map(({ word_id }) => word_id).filter(
        (id) => sentence.first_word <= id && id <= sentence.last_word,
      );
      const count = ids.filter((id) => played.has(id)).length;
      return {
        ...sentence,
        included: count === ids.length ? "all" : count ? "part" : "none",
      };
    }),
  });
}

/** ``GET /api/cuts/34/preview`` of ``cut``, docs/cli.md §8.3. */
export function previewOf(cut: Cut): CutPreview {
  return cutPreview({
    duration: cut.duration,
    segments: cut.segments.map(({ start, end, text }, index) => ({
      start,
      end,
      text,
      out_of_order: index > 0 && start < cut.segments[index - 1].end,
    })),
  });
}

/** Routes that keep cut 34 as ``PUT /api/cuts/34/segments`` leaves it, starting from
 * ``start``; ``refuse`` answers a PUT instead, when it gives a reply. */
export function editableCut(
  start: Cut = shownCut(),
  refuse: (call: RecordedCall) => Reply | undefined | Promise<Reply | undefined> = () => undefined,
) {
  let current = start;
  return {
    "GET /api/cuts/34": () => ({ body: current }),
    "GET /api/cuts/34/preview": () => ({ body: previewOf(current) }),
    "PUT /api/cuts/34/segments": async (call: RecordedCall) => {
      const refused = await refuse(call);
      if (refused) {
        return refused;
      }
      current = cutPlaying((call.body as { segments: Ranges }).segments);
      return { body: current };
    },
  };
}
