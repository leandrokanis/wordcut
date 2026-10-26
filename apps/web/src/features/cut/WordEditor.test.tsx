import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import type { CutWord } from "../../api/types";
import { live, openCut, type OpenedCut } from "../../test/cutLevel";
import { apiError, type Reply } from "../../test/fakeApi";
import { cutWords, shownCut } from "../../test/fixtures";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

let opened: OpenedCut;

/** ``PUT /api/cuts/34/words/{id}`` as the API answers a fix it accepts: the original text
 * removes the fix. */
function fixed(word: CutWord, text: string): Reply {
  return { body: { ...word, cut_id: 34, corrected: text === word.text ? null : text } };
}

/** Opens cut 34 playing, with "Deus governa." on the caption. */
async function openPlaying(
  put: (text: string) => Reply | Promise<Reply> = (text) => fixed(cutWords()[0], text),
  words: CutWord[] = cutWords(),
) {
  opened = await openCut({
    "GET /api/cuts/34": { body: shownCut({ words }) },
    "PUT /api/cuts/34/words/1105": ({ body }) => put((body as { text: string }).text),
    "PUT /api/cuts/34/words/1102": ({ body }) =>
      fixed(cutWords()[3], (body as { text: string }).text),
  });
  await userEvent.click(screen.getByRole("button", { name: "Reproduzir" }));
  act(() => opened.players.current().moveTo(live(2.6)));
}

function caption(): HTMLElement {
  return screen.getByRole("group", { name: "Legenda na prévia" });
}

async function editDeus(): Promise<HTMLInputElement> {
  await userEvent.dblClick(within(caption()).getByText("Deus"));
  return screen.getByRole<HTMLInputElement>("textbox", { name: "Corrigir “Deus”" });
}

function puts(): unknown[] {
  return opened.calls.filter(({ method }) => method === "PUT").map(({ url, body }) => [url, body]);
}

test("pauses the preview and opens a field with the word, focused, on a double click", async () => {
  await openPlaying();

  const field = await editDeus();

  expect({
    playing: opened.players.current().playing,
    button: screen.getByRole("button", { name: "Reproduzir" }).isConnected,
    value: field.value,
    focused: document.activeElement === field,
  }).toEqual({ playing: false, button: true, value: "Deus", focused: true });
});

test("saves the fix with Enter, without the spaces around it, on the caption and the text", async () => {
  await openPlaying();
  const field = await editDeus();

  await userEvent.clear(field);
  await userEvent.type(field, "  DEUS {Enter}");

  expect({
    sent: puts(),
    caption: caption().textContent,
    text: screen.getByRole("tabpanel").textContent,
    saved: await screen.findByText("Salvo"),
  }).toEqual({
    sent: [["/api/cuts/34/words/1105", { text: "DEUS" }]],
    caption: "DEUS governa.",
    text: expect.stringContaining("DEUS governa."),
    saved: expect.anything(),
  });
});

test("saves the fix on leaving the field", async () => {
  await openPlaying();
  const field = await editDeus();

  await userEvent.clear(field);
  await userEvent.type(field, "DEUS");
  await act(async () => field.blur());

  expect([puts(), caption().textContent]).toEqual([
    [["/api/cuts/34/words/1105", { text: "DEUS" }]],
    "DEUS governa.",
  ]);
});

test("sends nothing when the word is left as it was", async () => {
  await openPlaying();
  const field = await editDeus();

  await userEvent.type(field, "{Enter}");

  expect([puts(), screen.queryByRole("textbox", { name: "Corrigir “Deus”" })]).toEqual([[], null]);
});

test("cancels with Esc: nothing is sent and the word stays", async () => {
  await openPlaying();
  const field = await editDeus();

  await userEvent.type(field, "zzz{Escape}");

  expect({
    sent: puts(),
    field: screen.queryByRole("textbox", { name: "Corrigir “Deus”" }),
    caption: caption().textContent,
  }).toEqual({ sent: [], field: null, caption: "Deus governa." });
});

test("sends one PUT for Enter and the blur that follows it", async () => {
  let release = () => {};
  await openPlaying(
    (text) => new Promise((resolve) => (release = () => resolve(fixed(cutWords()[0], text)))),
  );
  const field = await editDeus();
  await userEvent.clear(field);
  await userEvent.type(field, "DEUS{Enter}");

  fireEvent.blur(field);
  await act(async () => release());

  expect(puts()).toEqual([["/api/cuts/34/words/1105", { text: "DEUS" }]]);
});

test("shows the spelling lock's block by the caption, without the typed text, and keeps the word", async () => {
  await openPlaying(() =>
    apiError(409, "spelling_too_different", "A correção muda o que foi dito.", {
      distance: 4,
      limit: 1,
      original: "Deus",
    }),
  );
  const field = await editDeus();
  await userEvent.clear(field);
  await userEvent.type(field, "Zebra{Enter}");

  const alert = await within(
    screen.getByLabelText("Prévia do corte").closest(".frame") as HTMLElement,
  ).findByRole("alert");
  const stillOpen = document.activeElement === field && field.value === "Zebra";
  await userEvent.type(field, "{Escape}");

  expect({
    alert: alert.textContent,
    stillOpen,
    caption: caption().textContent,
  }).toEqual({
    alert:
      "Bloqueado: não é uma correção de grafia de “Deus” e mudaria o que foi dito. Só o administrador altera o conteúdo.",
    stillOpen: true,
    caption: "Deus governa.",
  });
});

test("does not send the blocked text again when the field is left", async () => {
  await openPlaying(() =>
    apiError(409, "spelling_too_different", "A correção muda o que foi dito.", {
      original: "Deus",
    }),
  );
  const field = await editDeus();
  await userEvent.clear(field);
  await userEvent.type(field, "Zebra{Enter}");
  await screen.findByRole("alert");

  await act(async () => field.blur());

  expect(puts()).toHaveLength(1);
});

test("shows the API's reason for an invalid fix and keeps the word", async () => {
  await openPlaying(() =>
    apiError(400, "invalid_argument", "Use uma palavra só.", { argument: "text" }),
  );
  const field = await editDeus();
  await userEvent.clear(field);
  await userEvent.type(field, "Deus Pai{Enter}");

  expect((await screen.findByRole("alert")).textContent).toBe("Use uma palavra só.");
  await userEvent.type(field, "{Escape}");
  expect(caption().textContent).toBe("Deus governa.");
});

function fixesList(): HTMLElement {
  fireEvent.click(screen.getByRole("tab", { name: "Legenda" }));
  return screen.getByRole("list", { name: "Correções de grafia" });
}

test("lists the cut's fixes on the Legenda tab, the one just made too", async () => {
  await openPlaying(
    undefined,
    cutWords().map((word) => (word.word_id === 1102 ? { ...word, corrected: "Graça" } : word)),
  );
  const field = await editDeus();
  await userEvent.clear(field);
  await userEvent.type(field, "DEUS{Enter}");
  await screen.findByText("Salvo");

  expect(
    within(fixesList())
      .getAllByRole("listitem")
      .map((item) => item.textContent),
  ).toEqual(["Deus → DEUSDesfazer", "graça → GraçaDesfazer"]);
});

test("undoes a fix by sending the original word", async () => {
  await openPlaying(
    undefined,
    cutWords().map((word) => (word.word_id === 1102 ? { ...word, corrected: "Graça" } : word)),
  );
  const list = fixesList();

  await userEvent.click(within(list).getByRole("button", { name: "Desfazer" }));

  expect({
    sent: puts(),
    left: await screen.findByText("Nenhuma correção."),
  }).toEqual({
    sent: [["/api/cuts/34/words/1102", { text: "graça" }]],
    left: expect.anything(),
  });
});
