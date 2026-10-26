import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach } from "vitest";

import type { Preset } from "../../api/types";
import { apiError, type RecordedCall } from "../../test/fakeApi";
import { fakeIntersectionObserver } from "../../test/fakeIntersectionObserver";
import { criteria, preset, presets } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeSettingsApi, writes } from "../../test/settingsApi";

beforeEach(() => {
  fakeIntersectionObserver();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function presetPicker() {
  return screen.findByRole("combobox", { name: "Preset" });
}

function sectionOf(title: string): HTMLElement {
  return screen.getByRole("heading", { level: 2, name: title }).closest("section") as HTMLElement;
}

function pressed(name: string): string | null | undefined {
  const group = screen.getByRole("group", { name });
  return group.querySelector("[aria-pressed=true]")?.textContent;
}

test("opens on the default preset, marked as such among the others", async () => {
  fakeSettingsApi();
  renderRoute("/settings");

  const picker = (await presetPicker()) as HTMLSelectElement;

  const options = within(picker).getAllByRole("option").map((option) => option.textContent);
  expect([options, picker.selectedOptions[0].textContent]).toEqual([
    ["Padrão · padrão", "Curtos"],
    "Padrão · padrão",
  ]);
});

test("shows the chosen preset in every preset section", async () => {
  fakeSettingsApi();
  renderRoute("/settings");

  await userEvent.selectOptions(await presetPicker(), "Curtos");

  expect([
    (within(sectionOf("Presets")).getByRole("textbox", { name: "Nome" }) as HTMLInputElement)
      .value,
    pressed("Rigidez: Triunfalismo"),
    pressed("Rigidez: Aplicação prática"),
    (screen.getByRole("spinbutton", { name: "Duração final, mínimo" }) as HTMLInputElement)
      .value,
    pressed("Permitir reordenar"),
  ]).toEqual(["Curtos", "Brando", "Rigoroso", "30", "Não"]);
});

/** Answers a ``PATCH`` of preset ``id`` as the API does: the fixture with the change applied. */
function patched(id: number) {
  return (call: RecordedCall) => {
    const base = presets().find((candidate) => candidate.id === id) as Preset;
    const change = call.body as Partial<Preset>;
    return { body: { ...base, ...change, levels: { ...base.levels, ...change.levels } } };
  };
}

test("saves only the level picked for one criterion, and says Salvo", async () => {
  const calls = fakeSettingsApi({ "PATCH /api/presets/1": patched(1) });
  renderRoute("/settings");
  await presetPicker();

  await userEvent.click(
    within(screen.getByRole("group", { name: "Rigidez: Alegoria" })).getByRole("button", {
      name: "Rigoroso",
    }),
  );

  expect(await screen.findByText("Salvo")).toBeInTheDocument();
  expect([writes(calls), pressed("Rigidez: Alegoria")]).toEqual([
    [["PATCH /api/presets/1", { levels: { allegory: "strict" } }]],
    "Rigoroso",
  ]);
});

test("shows each criterion only by its name, even if a prompt text came along", async () => {
  const prompt = "Texto de prompt fictício que nunca aparece.";
  fakeSettingsApi({
    "GET /api/criteria": {
      body: { items: criteria().map((criterion) => ({ ...criterion, text: prompt })) },
    },
  });
  const { container } = renderRoute("/settings");
  await presetPicker();

  const rows = [sectionOf("Filtros"), sectionOf("Valor")].map((section) =>
    [...section.querySelectorAll(".sl")].map((label) => label.textContent),
  );
  expect([rows, container.innerHTML.includes(prompt)]).toEqual([
    [
      ["Triunfalismo", "Alegoria"],
      ["Cristocêntrico", "Aplicação prática"],
    ],
    false,
  ]);
});

/** Lets ``ms`` of the fake clock pass, and the API answer. */
async function wait(ms: number) {
  await act(() => vi.advanceTimersByTimeAsync(ms));
}

/** Types ``text`` into ``field`` as successive keys, each a change of the whole value. */
function keys(field: HTMLElement, text: string) {
  for (let end = 1; end <= text.length; end += 1) {
    fireEvent.change(field, { target: { value: text.slice(0, end) } });
  }
}

test("saves the additional instructions once, 400 ms after the last key", async () => {
  const calls = fakeSettingsApi({ "PATCH /api/presets/1": patched(1) });
  renderRoute("/settings");
  await presetPicker();
  vi.useFakeTimers();

  keys(screen.getByRole("textbox", { name: "Instruções adicionais" }), "Seja breve.");
  await wait(399);
  const early = writes(calls).length;
  await wait(1);

  expect([early, writes(calls)]).toEqual([
    0,
    [["PATCH /api/presets/1", { instructions: "Seja breve." }]],
  ]);
});

test("saves a duration range as whole seconds once the typing pauses", async () => {
  const calls = fakeSettingsApi({ "PATCH /api/presets/1": patched(1) });
  renderRoute("/settings");
  await presetPicker();
  vi.useFakeTimers();

  keys(screen.getByRole("spinbutton", { name: "Duração ideal, máximo" }), "70");
  await wait(400);

  expect(writes(calls)).toEqual([
    ["PATCH /api/presets/1", { duration_ideal: { min: 55, max: 70 } }],
  ]);
});

test("keeps a refused duration on screen with the API's reason, and no Salvo", async () => {
  fakeSettingsApi({
    "PATCH /api/presets/1": apiError(
      400,
      "invalid_argument",
      "A duração ideal precisa caber na duração permitida.",
    ),
  });
  renderRoute("/settings");
  await presetPicker();
  vi.useFakeTimers();
  const field = screen.getByRole("spinbutton", { name: "Duração ideal, máximo" });

  keys(field, "90");
  await wait(400);

  const formato = sectionOf("Formato");
  expect([
    within(formato).getByRole("alert").textContent,
    (field as HTMLInputElement).value,
    screen.queryByText("Salvo"),
  ]).toEqual(["A duração ideal precisa caber na duração permitida.", "90", null]);
});

test("saves Permitir reordenar as soon as it is picked", async () => {
  const calls = fakeSettingsApi({ "PATCH /api/presets/1": patched(1) });
  renderRoute("/settings");
  await presetPicker();

  await userEvent.click(
    within(screen.getByRole("group", { name: "Permitir reordenar" })).getByRole("button", {
      name: "Não",
    }),
  );

  await screen.findByText("Salvo");
  expect(writes(calls)).toEqual([["PATCH /api/presets/1", { reorder: false }]]);
});

test("saves the protected words as a trimmed list, without empty ones", async () => {
  const calls = fakeSettingsApi({ "PATCH /api/presets/1": patched(1) });
  renderRoute("/settings");
  await presetPicker();
  vi.useFakeTimers();

  fireEvent.change(screen.getByRole("textbox", { name: "Palavras protegidas" }), {
    target: { value: "a, b ,c,, " },
  });
  await wait(400);

  expect(writes(calls)).toEqual([
    ["PATCH /api/presets/1", { protected_words: ["a", "b", "c"] }],
  ]);
});

function nameField(): HTMLInputElement {
  return within(sectionOf("Presets")).getByRole("textbox", { name: "Nome" }) as HTMLInputElement;
}

test("renames the preset with Enter, in the picker too", async () => {
  const calls = fakeSettingsApi({ "PATCH /api/presets/2": patched(2) });
  renderRoute("/settings");
  await userEvent.selectOptions(await presetPicker(), "Curtos");

  await userEvent.clear(nameField());
  await userEvent.type(nameField(), "Bem curtos{Enter}");

  expect(await screen.findByRole("option", { name: "Bem curtos" })).toBeInTheDocument();
  expect(writes(calls)).toEqual([["PATCH /api/presets/2", { name: "Bem curtos" }]]);
});

test("keeps a repeated name unsaved, with the API's reason beside it", async () => {
  fakeSettingsApi({
    "PATCH /api/presets/2": apiError(400, "invalid_argument", "Já existe um preset com esse nome."),
  });
  renderRoute("/settings");
  await userEvent.selectOptions(await presetPicker(), "Curtos");

  await userEvent.clear(nameField());
  await userEvent.type(nameField(), "Padrão");
  await userEvent.tab();

  const presetsSection = sectionOf("Presets");
  expect([
    (await within(presetsSection).findByRole("alert")).textContent,
    screen.queryByText("Salvo"),
  ]).toEqual(["Já existe um preset com esse nome.", null]);
});

test("saves a waiting change on its own preset before showing another", async () => {
  const calls = fakeSettingsApi({ "PATCH /api/presets/1": patched(1) });
  renderRoute("/settings");
  const picker = await presetPicker();
  vi.useFakeTimers();

  keys(screen.getByRole("textbox", { name: "Instruções adicionais" }), "Só o texto.");
  fireEvent.change(picker, { target: { value: "2" } });
  await wait(0);
  const atSwitch = writes(calls);
  await wait(400);

  expect([atSwitch, writes(calls)]).toEqual([
    [["PATCH /api/presets/1", { instructions: "Só o texto." }]],
    [["PATCH /api/presets/1", { instructions: "Só o texto." }]],
  ]);
});

function selectedPreset(): string | undefined {
  return (screen.getByRole("combobox", { name: "Preset" }) as HTMLSelectElement).selectedOptions[0]
    ?.textContent ?? undefined;
}

test("duplicates the shown preset as Cópia de <nome> and shows the copy", async () => {
  const copy = preset({ id: 3, name: "Cópia de Padrão", is_default: false });
  const calls = fakeSettingsApi({ "POST /api/presets": { status: 201, body: copy } });
  renderRoute("/settings");
  await presetPicker();

  await userEvent.click(screen.getByRole("button", { name: "Duplicar" }));

  await screen.findByRole("option", { name: "Cópia de Padrão" });
  expect([writes(calls), selectedPreset()]).toEqual([
    [["POST /api/presets", { name: "Cópia de Padrão", from_id: 1 }]],
    "Cópia de Padrão",
  ]);
});

test("makes the shown preset the default, moving the mark from the old one", async () => {
  const calls = fakeSettingsApi({
    "POST /api/presets/2/set-default": { body: { ...presets()[1], is_default: true } },
  });
  renderRoute("/settings");
  await userEvent.selectOptions(await presetPicker(), "Curtos");

  await userEvent.click(screen.getByRole("button", { name: "Tornar padrão" }));

  await screen.findByText("Preset padrão");
  const options = within(screen.getByRole("combobox", { name: "Preset" }))
    .getAllByRole("option")
    .map((option) => option.textContent);
  expect([writes(calls), options]).toEqual([
    [["POST /api/presets/2/set-default", {}]],
    ["Padrão", "Curtos · padrão"],
  ]);
});

function presetNames(): (string | null)[] {
  return within(screen.getByRole("combobox", { name: "Preset" }))
    .getAllByRole("option")
    .map((option) => option.textContent);
}

test("keeps the default preset from being deleted", async () => {
  fakeSettingsApi();
  renderRoute("/settings");
  await presetPicker();

  expect(screen.getByRole("button", { name: "Apagar" })).toBeDisabled();
});

test("deletes another preset and goes back to the default one", async () => {
  const calls = fakeSettingsApi({ "DELETE /api/presets/2": { body: { id: 2, deleted: true } } });
  renderRoute("/settings");
  await userEvent.selectOptions(await presetPicker(), "Curtos");

  await userEvent.click(screen.getByRole("button", { name: "Apagar" }));

  await screen.findByText("Preset padrão");
  expect([writes(calls), presetNames(), selectedPreset()]).toEqual([
    [["DELETE /api/presets/2", undefined]],
    ["Padrão · padrão"],
    "Padrão · padrão",
  ]);
});

test("keeps a preset the API refused to delete, with its reason", async () => {
  fakeSettingsApi({
    "DELETE /api/presets/2": apiError(409, "default_preset", "O preset padrão não pode ser apagado."),
  });
  renderRoute("/settings");
  await userEvent.selectOptions(await presetPicker(), "Curtos");

  await userEvent.click(screen.getByRole("button", { name: "Apagar" }));

  expect([
    (await within(sectionOf("Presets")).findByRole("alert")).textContent,
    presetNames(),
    screen.queryByText("Salvo"),
  ]).toEqual(["O preset padrão não pode ser apagado.", ["Padrão · padrão", "Curtos"], null]);
});

test("tells why a copy could not be made, adding nothing", async () => {
  fakeSettingsApi({
    "POST /api/presets": apiError(400, "invalid_argument", "Já existe um preset com esse nome."),
  });
  renderRoute("/settings");
  await presetPicker();

  await userEvent.click(screen.getByRole("button", { name: "Duplicar" }));

  expect([
    (await within(sectionOf("Presets")).findByRole("alert")).textContent,
    presetNames(),
  ]).toEqual(["Já existe um preset com esse nome.", ["Padrão · padrão", "Curtos"]]);
});
