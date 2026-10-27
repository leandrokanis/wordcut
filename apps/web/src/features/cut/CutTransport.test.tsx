import { act, cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach } from "vitest";

import { AppRoutes } from "../../app/routes";

import { cutPlaying, editableCut, live, openCut, type OpenedCut } from "../../test/cutLevel";
import { apiError, type RecordedCall, type Reply } from "../../test/fakeApi";
import { fakePlayers } from "../../test/fakePlayers";
import { assistant, cutPreview, processedSermon, shownCut } from "../../test/fixtures";
import { fakeShellApi } from "../../test/shellApi";
import { PlayerFactoryContext } from "../sermon/Player";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// The segments of ``shownCut``, by their first word.
const RANGES: Record<number, { from_word: number; to_word: number }> = {
  1105: { from_word: 1105, to_word: 1106 },
  1101: { from_word: 1101, to_word: 1102 },
  1103: { from_word: 1103, to_word: 1103 },
};

function lastPut(calls: RecordedCall[]): unknown {
  return calls.filter(({ method }) => method === "PUT").pop()?.body;
}

async function select(segment: number) {
  await userEvent.click(
    within(screen.getByRole("region", { name: "Timeline" })).getByRole("button", {
      name: new RegExp(`^Trecho ${segment}`),
    }),
  );
}

test.each([
  ["right", "next", [1105, 1103, 1101]],
  ["left", "previous", [1101, 1105, 1103]],
])(
  "moving a segment to the %s saves the cut with it swapped with the %s one",
  async (side, _neighbour, order) => {
    const { calls } = await openCut(editableCut());
    await select(2);

    await userEvent.click(
      screen.getByRole("button", {
        name: `Mover o trecho para a ${side === "right" ? "direita" : "esquerda"}`,
      }),
    );

    expect(lastPut(calls)).toEqual({
      segments: order.map((first) => RANGES[first]),
    });
  },
);

/** The names of the "Vídeo" track's segments, in the order the cut plays them. */
function clips(): (string | null)[] {
  return within(screen.getByRole("region", { name: "Timeline" }))
    .getAllByRole("button", { name: /^Trecho/ })
    .map((clip) => clip.getAttribute("aria-label"));
}

test("shows the cut in its new order after a move, marking the segment out of order", async () => {
  await openCut(editableCut());
  await select(2);

  await userEvent.click(screen.getByRole("button", { name: "Mover o trecho para a direita" }));
  await screen.findByText("Salvo");

  expect(clips()).toEqual([
    "Trecho 1",
    "Trecho 2, fora da ordem da pregação",
    "Trecho 3, fora da ordem da pregação",
  ]);
});

/** The segments of the "Vídeo" track pressed as selected. */
function selectedClips(): (string | null)[] {
  return within(screen.getByRole("region", { name: "Timeline" }))
    .queryAllByRole("button", { name: /^Trecho/, pressed: true })
    .map((clip) => clip.getAttribute("aria-label"));
}

test("keeps the moved segment selected at its new place", async () => {
  await openCut(editableCut());
  await select(2);

  await userEvent.click(screen.getByRole("button", { name: "Mover o trecho para a direita" }));
  await screen.findByText("Salvo");

  expect(selectedClips()).toEqual(["Trecho 3, fora da ordem da pregação"]);
});

/** Cut 34 playing "Irmãos, graça paz. Então Deus governa." as one segment, then "Amém,
 * igreja.": 3.1 s and 0.6 s. */
const TWO_SENTENCES = cutPlaying([
  { from_word: 1101, to_word: 1106 },
  { from_word: 1107, to_word: 1108 },
]);

function moveTo(opened: OpenedCut, sermonSeconds: number) {
  act(() => opened.players.current().moveTo(live(sermonSeconds)));
}

async function splitAtSermon(sermonSeconds: number) {
  const opened = await openCut(editableCut(TWO_SENTENCES));
  moveTo(opened, sermonSeconds);
  await select(1);
  await userEvent.click(
    screen.getByRole("button", {
      name: "Dividir o trecho no cursor, entre frases",
    }),
  );
  await screen.findByText("Salvo");
  return opened;
}

test("splitting a segment saves it as two at the sentence boundary nearest the cursor", async () => {
  const { calls } = await splitAtSermon(1.95);

  expect(lastPut(calls)).toEqual({
    segments: [
      { from_word: 1101, to_word: 1103 },
      { from_word: 1104, to_word: 1106 },
      { from_word: 1107, to_word: 1108 },
    ],
  });
});

test("splitting a segment keeps the cut's duration", async () => {
  await splitAtSermon(1.95);

  expect(screen.getByLabelText("Tempo do corte")).toHaveTextContent(/\/ 0:03$/);
});

test("selects the first half of the segment split", async () => {
  await splitAtSermon(1.95);

  expect(selectedClips()).toEqual(["Trecho 1"]);
});

function tool(name: string): HTMLButtonElement {
  return screen.getByRole("button", { name }) as HTMLButtonElement;
}

const SPLIT = "Dividir o trecho no cursor, entre frases";
const LEFT = "Mover o trecho para a esquerda";
const RIGHT = "Mover o trecho para a direita";
const REMOVE = "Remover o trecho";

test("cannot split a segment of one sentence", async () => {
  const opened = await openCut(editableCut());
  moveTo(opened, 2.6);
  await select(1);

  expect(tool(SPLIT)).toBeDisabled();
});

test("cannot split a segment the cursor is not on", async () => {
  await openCut(editableCut(TWO_SENTENCES));
  await select(2);

  expect(tool(SPLIT)).toBeDisabled();
});

test("removing a segment saves the cut without it and shows it shorter", async () => {
  const { calls } = await openCut(editableCut());
  await select(1);

  await userEvent.click(tool(REMOVE));
  await screen.findByText("Salvo");

  expect([lastPut(calls), screen.getByLabelText("Tempo do corte").textContent]).toEqual([
    { segments: [RANGES[1101], RANGES[1103]] },
    "0:00 / 0:01",
  ]);
});

test("clears the selection once the segment is removed", async () => {
  await openCut(editableCut());
  await select(1);

  await userEvent.click(tool(REMOVE));
  await screen.findByText("Salvo");

  expect(selectedClips()).toEqual([]);
});

test("offers no segment action before a segment is selected", async () => {
  await openCut(editableCut());

  expect([SPLIT, LEFT, RIGHT, REMOVE].map((name) => tool(name).disabled)).toEqual([
    true,
    true,
    true,
    true,
  ]);
});

test("cannot move the first segment left nor the last one right", async () => {
  await openCut(editableCut());
  await select(1);
  const first = [tool(LEFT).disabled, tool(RIGHT).disabled];
  await select(3);

  expect([first, [tool(LEFT).disabled, tool(RIGHT).disabled]]).toEqual([
    [true, false],
    [false, true],
  ]);
});

test("cannot remove the only segment of the cut", async () => {
  await openCut(editableCut(cutPlaying([{ from_word: 1101, to_word: 1103 }])));
  await select(1);

  expect(tool(REMOVE)).toBeDisabled();
});

test("takes no other segment action while a change is being saved", async () => {
  let answer: (reply: Reply | undefined) => void = () => {};
  const held = new Promise<Reply | undefined>((resolve) => (answer = resolve));
  await openCut(editableCut(undefined, () => held));
  await select(2);

  await userEvent.click(tool(RIGHT));
  const disabled = [SPLIT, LEFT, RIGHT, REMOVE].map((name) => tool(name).disabled);
  answer(undefined);
  await screen.findByText("Salvo");

  expect(disabled).toEqual([true, true, true, true]);
});

test("takes no segment action while the sermon is being processed", async () => {
  await openCut({
    ...editableCut(),
    "GET /api/sermons/12": {
      body: processedSermon({ status: "processing", sermon_start: 1800 }),
    },
  });
  await select(2);

  expect([SPLIT, LEFT, RIGHT, REMOVE].map((name) => tool(name).disabled)).toEqual([
    true,
    true,
    true,
    true,
  ]);
});

test("shows the assistant the segment actions off, saying only the administrator changes the content", async () => {
  await openCut(editableCut(), assistant());
  await select(2);

  const off = screen
    .getAllByRole("button", { name: /\(só o administrador\)$/ })
    .map((button) => [
      button.getAttribute("aria-label"),
      button.title,
      (button as HTMLButtonElement).disabled,
    ]);

  expect(off.slice(2)).toEqual(
    [SPLIT, LEFT, RIGHT, REMOVE].map((name) => [
      `${name} (só o administrador)`,
      "Só o administrador muda o conteúdo",
      true,
    ]),
  );
});

test("saves nothing for the assistant", async () => {
  const { calls } = await openCut(editableCut(), assistant());
  await select(2);

  await userEvent.click(screen.getByRole("button", { name: `${RIGHT} (só o administrador)` }));

  expect(calls.some(({ method }) => method === "PUT")).toBe(false);
});

test("says why the API refused a change and keeps the cut as it was", async () => {
  await openCut(
    editableCut(undefined, () =>
      apiError(400, "invalid_argument", "Um trecho sai da faixa do corte."),
    ),
  );
  await select(2);

  await userEvent.click(tool(RIGHT));

  expect([(await screen.findByRole("alert")).textContent, clips()]).toEqual([
    "Um trecho sai da faixa do corte.",
    ["Trecho 1", "Trecho 2, fora da ordem da pregação", "Trecho 3"],
  ]);
});

const UNDO = "Desfazer";
const REDO = "Refazer";

async function moveSecondRight() {
  await select(2);
  await userEvent.click(tool(RIGHT));
  await screen.findByRole("button", { name: "Trecho 3, fora da ordem da pregação" });
}

test("undoing a move saves the cut as it was before it", async () => {
  const { calls } = await openCut(editableCut());
  await moveSecondRight();

  await userEvent.click(tool(UNDO));

  expect(lastPut(calls)).toEqual({ segments: [RANGES[1105], RANGES[1101], RANGES[1103]] });
});

test("redoing an undone move saves the cut with the move again", async () => {
  const { calls } = await openCut(editableCut());
  await moveSecondRight();
  await userEvent.click(tool(UNDO));
  await screen.findByRole("button", { name: "Trecho 2, fora da ordem da pregação" });

  await userEvent.click(tool(REDO));

  expect(lastPut(calls)).toEqual({ segments: [RANGES[1105], RANGES[1103], RANGES[1101]] });
});

test.each([
  ["Ctrl+Z", "{Control>}z{/Control}"],
  ["Cmd+Z", "{Meta>}z{/Meta}"],
])("%s undoes the last change", async (_keys, keys) => {
  const { calls } = await openCut(editableCut());
  await moveSecondRight();

  await userEvent.keyboard(keys);

  expect(lastPut(calls)).toEqual({ segments: [RANGES[1105], RANGES[1101], RANGES[1103]] });
});

test("Ctrl+Shift+Z redoes the last change undone", async () => {
  const { calls } = await openCut(editableCut());
  await moveSecondRight();
  await userEvent.click(tool(UNDO));
  await screen.findByRole("button", { name: "Trecho 2, fora da ordem da pregação" });

  await userEvent.keyboard("{Control>}{Shift>}Z{/Shift}{/Control}");

  expect(lastPut(calls)).toEqual({ segments: [RANGES[1105], RANGES[1103], RANGES[1101]] });
});

test("Ctrl+Z undoes ticking a sentence in Texto", async () => {
  const { calls } = await openCut(editableCut());
  await userEvent.click(screen.getByRole("checkbox", { name: /^Incluir frase 1/ }));
  await screen.findByText("Salvo");

  await userEvent.keyboard("{Control>}z{/Control}");

  expect(lastPut(calls)).toEqual({ segments: [RANGES[1105], RANGES[1101], RANGES[1103]] });
});

test("offers neither undo nor redo before any change", async () => {
  await openCut(editableCut());

  expect([tool(UNDO).disabled, tool(REDO).disabled]).toEqual([true, true]);
});

test("a new change after an undo leaves nothing to redo", async () => {
  await openCut(editableCut());
  await moveSecondRight();
  await userEvent.click(tool(UNDO));
  await screen.findByRole("button", { name: "Trecho 2, fora da ordem da pregação" });

  await select(1);
  await userEvent.click(tool(REMOVE));
  await screen.findByText("Salvo");

  expect(tool(REDO)).toBeDisabled();
});

test("clears the selection once a change is undone", async () => {
  await openCut(editableCut());
  await moveSecondRight();

  await userEvent.click(tool(UNDO));
  await screen.findByRole("button", { name: "Trecho 2, fora da ordem da pregação" });

  expect(selectedClips()).toEqual([]);
});

test("Ctrl+Z in a text field leaves the cut alone", async () => {
  const opened = await openCut(editableCut());
  await moveSecondRight();
  moveTo(opened, 2.6);
  await userEvent.dblClick(
    within(screen.getByRole("group", { name: "Legenda na prévia" })).getByText("Deus"),
  );
  const puts = opened.calls.filter(({ method }) => method === "PUT").length;

  await userEvent.keyboard("{Control>}z{/Control}");

  expect([
    document.activeElement?.getAttribute("aria-label"),
    opened.calls.filter(({ method }) => method === "PUT").length,
  ]).toEqual(["Corrigir “Deus”", puts]);
});

test("says why the API refused an undo and keeps the cut and what can be undone", async () => {
  let refuse = false;
  await openCut(
    editableCut(undefined, () =>
      refuse ? apiError(409, "busy", "Outra mudança está sendo gravada.") : undefined,
    ),
  );
  await moveSecondRight();
  refuse = true;

  await userEvent.click(tool(UNDO));

  expect([
    (await screen.findByRole("alert")).textContent,
    clips(),
    tool(UNDO).disabled,
    tool(REDO).disabled,
  ]).toEqual([
    "Outra mudança está sendo gravada.",
    ["Trecho 1", "Trecho 2, fora da ordem da pregação", "Trecho 3, fora da ordem da pregação"],
    false,
    true,
  ]);
});

test("takes no undo while a change is being saved", async () => {
  let answer: (reply: Reply | undefined) => void = () => {};
  let hold = false;
  await openCut(
    editableCut(undefined, () =>
      hold ? new Promise<Reply | undefined>((resolve) => (answer = resolve)) : undefined,
    ),
  );
  await moveSecondRight();
  hold = true;

  await select(1);
  await userEvent.click(tool(REMOVE));
  const disabled = tool(UNDO).disabled;
  answer(undefined);
  await screen.findByText("Salvo");

  expect(disabled).toBe(true);
});

test("keeps the undo of a session only: the cut opened again has nothing to undo", async () => {
  await openCut(editableCut());
  await moveSecondRight();
  cleanup();

  await openCut(editableCut());

  expect(tool(UNDO)).toBeDisabled();
});

test("offers the assistant no undo, by button or by key", async () => {
  const { calls } = await openCut(editableCut(), assistant());

  await userEvent.keyboard("{Control>}z{/Control}");

  expect([
    screen.getByRole("button", { name: /^Desfazer/ }).hasAttribute("disabled"),
    calls.some(({ method }) => method === "PUT"),
  ]).toEqual([true, false]);
});

/** Goes to another cut without leaving the cut level, as typing its address would. */
function GoTo({ path }: { path: string }) {
  const navigate = useNavigate();
  return (
    <button type="button" onClick={() => navigate(path)}>
      Ir para {path}
    </button>
  );
}

test("forgets what can be undone when another cut opens", async () => {
  const calls = fakeShellApi({
    ...editableCut(),
    "GET /api/cuts/35": { body: shownCut({ id: 35 }) },
    "GET /api/cuts/35/preview": { body: cutPreview({ cut_id: 35 }) },
    "GET /api/sermons/12": { body: processedSermon({ sermon_start: 1800 }) },
  });
  render(
    <PlayerFactoryContext.Provider value={fakePlayers()}>
      <MemoryRouter initialEntries={["/cuts/34"]}>
        <AppRoutes />
        <GoTo path="/cuts/35" />
      </MemoryRouter>
    </PlayerFactoryContext.Provider>,
  );
  await screen.findByLabelText("Prévia do corte");
  await moveSecondRight();
  const puts = calls.filter(({ method }) => method === "PUT").length;

  await userEvent.click(screen.getByRole("button", { name: "Ir para /cuts/35" }));
  await screen.findByRole("button", { name: "Trecho 2, fora da ordem da pregação" });
  await userEvent.keyboard("{Control>}z{/Control}");

  expect([tool(UNDO).disabled, calls.filter(({ method }) => method === "PUT").length]).toEqual([
    true,
    puts,
  ]);
});

/** The duration chip of the transport, as [text, class, title]. */
function chip(): [string | null, string, string] {
  const shown = screen.getByLabelText("Duração do corte");
  return [shown.textContent, shown.className, shown.title];
}

test.each([
  [39, "0:39", "chip mono warn", "Abaixo da meta de 40 a 75 s"],
  [40, "0:40", "chip mono ok", "Dentro da meta de 40 a 75 s"],
  [75, "1:15", "chip mono ok", "Dentro da meta de 40 a 75 s"],
  [76, "1:16", "chip mono warn", "Acima da meta de 40 a 75 s"],
])("shows a cut of %s s against the 40–75 s goal", async (duration, text, className, title) => {
  await openCut({ "GET /api/cuts/34/preview": { body: cutPreview({ duration }) } });

  expect(chip()).toEqual([text, className, title]);
});

test("shows the cut's new duration against the goal after a change", async () => {
  await openCut(editableCut());
  await select(1);

  await userEvent.click(tool(REMOVE));
  await screen.findByText("Salvo");

  expect(chip()[0]).toBe("0:01");
});
