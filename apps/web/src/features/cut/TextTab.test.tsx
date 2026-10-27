import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import type { Cut } from "../../api/types";
import { live, openCut } from "../../test/cutLevel";
import { apiError, type Reply } from "../../test/fakeApi";
import {
  assistant,
  cutPreview,
  processedSermon,
  rangeSentences,
  shownCut,
} from "../../test/fixtures";

type Route = Reply | (() => Reply | Promise<Reply>);

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function textPanel(): HTMLElement {
  return screen.getByRole("tabpanel");
}

test("shows the administrator each sentence of the range with a box marking how much the cut plays", async () => {
  await openCut();

  const boxes = within(textPanel()).getAllByRole("checkbox");

  expect(
    boxes.map((box) => [box.getAttribute("aria-label"), box.getAttribute("aria-checked")]),
  ).toEqual([
    ["Incluir frase 1: Irmãos, graça paz.", "true"],
    ["Incluir frase 2: Então Deus governa.", "mixed"],
    ["Incluir frase 3: Amém, igreja.", "false"],
  ]);
});

test("shows anyone else the cut's segments in the order it plays them, without boxes", async () => {
  await openCut({}, assistant());

  expect([
    within(textPanel()).queryAllByRole("checkbox"),
    Array.from(textPanel().querySelectorAll(".sent")).map((row) => row.textContent),
  ]).toEqual([[], ["0:00Deus governa.", "0:00Irmãos, graça", "0:01paz."]]);
});

/** ``shownCut`` once it plays only "Deus governa.", as the API answers the change. */
function withoutTheFirstSentence(): Cut {
  return shownCut({
    segments: [shownCut().segments[0]],
    duration: 61,
    range_sentences: rangeSentences().map((sentence) =>
      sentence.id === 41 ? { ...sentence, included: "none" } : sentence,
    ),
  });
}

function afterTheChange(put: Route = { body: withoutTheFirstSentence() }) {
  let previews = 0;
  return {
    "PUT /api/cuts/34/segments": put,
    "GET /api/cuts/34/preview": () => ({
      body: previews++ === 0 ? cutPreview() : cutPreview({ duration: 61, segments: [] }),
    }),
  };
}

test("leaving out a sentence saves the segments without it and shows the cut it makes", async () => {
  const { calls } = await openCut(afterTheChange());

  await userEvent.click(screen.getByRole("checkbox", { name: /^Incluir frase 1/ }));

  expect(await screen.findByLabelText("Tempo do corte")).toHaveTextContent("0:00 / 1:01");
  expect(calls.find(({ method }) => method === "PUT")?.body).toEqual({
    segments: [{ from_word: 1105, to_word: 1106 }],
  });
});

test("including a sentence next to a segment saves it joined to that segment", async () => {
  const { calls } = await openCut(afterTheChange());

  await userEvent.click(screen.getByRole("checkbox", { name: /^Incluir frase 3/ }));

  expect(calls.find(({ method }) => method === "PUT")?.body).toEqual({
    segments: [
      { from_word: 1105, to_word: 1108 },
      { from_word: 1101, to_word: 1102 },
      { from_word: 1103, to_word: 1103 },
    ],
  });
});

test("says why the API refused a choice and keeps the boxes as they were", async () => {
  await openCut(
    afterTheChange(apiError(400, "invalid_argument", "Um trecho sai da faixa do corte.")),
  );

  await userEvent.click(screen.getByRole("checkbox", { name: /^Incluir frase 1/ }));

  expect([
    (await within(textPanel()).findByRole("alert")).textContent,
    screen.getByRole("checkbox", { name: /^Incluir frase 1/ }).getAttribute("aria-checked"),
  ]).toEqual(["Um trecho sai da faixa do corte.", "true"]);
});

test("refuses to leave out the only sentence of the cut without asking the API", async () => {
  const only = shownCut({
    segments: [
      {
        from_word: 1101,
        to_word: 1103,
        start: 0.3,
        end: 1.9,
        text: "Irmãos, graça paz.",
      },
    ],
    range_sentences: rangeSentences().map((sentence) => ({
      ...sentence,
      included: sentence.id === 41 ? "all" : "none",
    })),
  });
  const { calls } = await openCut({ "GET /api/cuts/34": { body: only } });

  await userEvent.click(screen.getByRole("checkbox", { name: /^Incluir frase 1/ }));

  expect([
    within(textPanel()).getByRole("alert").textContent,
    calls.some(({ method }) => method === "PUT"),
  ]).toEqual(["O corte precisa de ao menos uma frase; marque outra antes de tirar esta.", false]);
});

test("says Salvo once the API saved the choice", async () => {
  await openCut(afterTheChange());

  await userEvent.click(screen.getByRole("checkbox", { name: /^Incluir frase 1/ }));

  expect(await screen.findByText("Salvo")).toBeInTheDocument();
});

test("takes no other click on the boxes while a choice is being saved", async () => {
  let answer: (reply: Reply) => void = () => {};
  const held = new Promise<Reply>((resolve) => (answer = resolve));
  await openCut(afterTheChange(() => held));

  await userEvent.click(screen.getByRole("checkbox", { name: /^Incluir frase 1/ }));
  const disabled = within(textPanel())
    .getAllByRole("checkbox")
    .map((box) => (box as HTMLInputElement).disabled);
  answer({ body: withoutTheFirstSentence() });

  expect([disabled, await screen.findByText("Salvo")]).toEqual([
    [true, true, true],
    expect.anything(),
  ]);
});

test("takes no click on the boxes while the sermon is being processed", async () => {
  await openCut({
    "GET /api/sermons/12": {
      body: processedSermon({ status: "processing", sermon_start: 1800 }),
    },
  });

  const boxes = within(textPanel()).getAllByRole("checkbox");

  expect(boxes.map((box) => (box as HTMLInputElement).disabled)).toEqual([true, true, true]);
});

test("captions the words of a sentence once it is included", async () => {
  const word = (word_id: number, text: string, start: number, end: number) => ({
    word_id,
    text,
    start,
    end,
    corrected: null,
  });
  const joined = shownCut({
    segments: [{ from_word: 1105, to_word: 1108, start: 2.5, end: 4.2, text: "…" }],
    words: [
      word(1105, "Deus", 2.5, 2.9),
      word(1106, "governa.", 2.95, 3.4),
      word(1107, "Amém,", 3.6, 3.9),
      word(1108, "igreja.", 3.95, 4.2),
    ],
  });
  let previews = 0;
  const { players } = await openCut({
    "PUT /api/cuts/34/segments": { body: joined },
    "GET /api/cuts/34/preview": () => ({
      body:
        previews++ === 0
          ? cutPreview()
          : cutPreview({
              duration: 1.7,
              segments: [{ start: 2.5, end: 4.2, text: "…", out_of_order: false }],
            }),
    }),
  });
  await userEvent.click(screen.getByRole("checkbox", { name: /^Incluir frase 3/ }));
  await screen.findByText("Salvo");

  act(() => players.current().moveTo(live(3.7)));

  expect(screen.getByRole("group", { name: "Legenda na prévia" })).toHaveTextContent("Amém,");
});
