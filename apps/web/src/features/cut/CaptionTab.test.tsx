import { act, fireEvent, screen, within } from "@testing-library/react";
import { afterEach } from "vitest";

import type { CaptionPosition, CaptionStyle } from "../../api/types";
import { live, openCut, type OpenedCut } from "../../test/cutLevel";
import { apiError, type Reply } from "../../test/fakeApi";
import { churchCaption, shownCut } from "../../test/fixtures";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// docs/cli.md §8.6: the position takes the height to 20, 50 or 78 % of the frame.
const POSITION_OFFSET: Record<CaptionPosition, number> = { top: 20, center: 50, bottom: 78 };

/** ``PATCH /api/cuts/34/caption`` as the API answers it: the whole style. */
function patched(saved: CaptionStyle, fields: Partial<CaptionStyle>): CaptionStyle {
  const offset =
    fields.position && fields.offset === undefined ? POSITION_OFFSET[fields.position] : undefined;
  return { ...saved, ...fields, ...(offset !== undefined && { offset }) };
}

let opened: OpenedCut;

/** Opens the Legenda tab of cut 34 over a word of its caption, with the clock faked. */
async function openCaption(
  caption: CaptionStyle = churchCaption(),
  patch: (fields: Partial<CaptionStyle>) => Reply = (fields) => ({
    body: patched(caption, fields),
  }),
) {
  opened = await openCut({
    "GET /api/cuts/34": { body: shownCut({ caption }) },
    "PATCH /api/cuts/34/caption": ({ body }) => patch(body as Partial<CaptionStyle>),
    "DELETE /api/cuts/34/caption": { body: churchCaption() },
  });
  act(() => opened.players.current().moveTo(live(2.6)));
  fireEvent.click(screen.getByRole("tab", { name: "Legenda" }));
  vi.useFakeTimers();
  return screen.getByRole("tabpanel");
}

/** Lets the 400 ms of the automatic save pass, and the API answer. */
async function settle(ms = 400) {
  await act(() => vi.advanceTimersByTimeAsync(ms));
}

function patches(): unknown[] {
  return opened.calls.filter(({ method }) => method === "PATCH").map(({ body }) => body);
}

/** The caption over the preview, not the form's group of the same name. */
function overlay(): HTMLElement | null {
  return document.querySelector(".frame .caption");
}

function overlayStyle(name: string): string | undefined {
  return overlay()?.style.getPropertyValue(name);
}

function pick(panel: HTMLElement, group: string, option: string) {
  fireEvent.click(
    within(within(panel).getByRole("group", { name: group })).getByRole("button", {
      name: option,
    }),
  );
}

function slide(panel: HTMLElement, name: string, value: number) {
  fireEvent.change(within(panel).getByRole("slider", { name }), { target: { value } });
}

test("lays out every control of the style in rows, without a save button", async () => {
  const panel = await openCaption();

  const found = [
    within(panel).getByRole("group", { name: "Legenda" }),
    within(panel).getByRole("combobox", { name: "Fonte" }),
    within(panel).getByRole("slider", { name: "Tamanho" }),
    within(panel).getByRole("group", { name: "Cor" }),
    within(panel).getByRole("group", { name: "Posição" }),
    within(panel).getByRole("slider", { name: "Altura da legenda" }),
    within(panel).getByRole("slider", { name: "Espessura da borda" }),
    within(panel).getByRole("group", { name: "Cor da borda" }),
    within(panel).getByRole("group", { name: "Sombra" }),
    within(panel).getByRole("button", { name: "Restaurar padrão" }),
  ];

  expect({
    rows: found.every((control) => control.closest(".lrow") !== null),
    save: within(panel).queryByRole("button", { name: /Salvar|Aplicar/ }),
  }).toEqual({ rows: true, save: null });
});

test.each([
  [
    "Tamanho",
    (panel: HTMLElement) => slide(panel, "Tamanho", 108),
    { size: 108 },
    "--cap-size",
    "10cqw",
  ],
  [
    "Cor",
    (panel: HTMLElement) => pick(panel, "Cor", "Branco"),
    { color: "#FFFFFF" },
    "--cap-color",
    "#FFFFFF",
  ],
  [
    "Outra cor",
    (panel: HTMLElement) =>
      fireEvent.change(
        within(within(panel).getByRole("group", { name: "Cor" })).getByLabelText("Outra cor"),
        { target: { value: "#00e5ff" } },
      ),
    { color: "#00E5FF" },
    "--cap-color",
    "#00E5FF",
  ],
  [
    "Posição",
    (panel: HTMLElement) => pick(panel, "Posição", "Topo"),
    { position: "top" },
    "--cap-top",
    "20%",
  ],
  [
    "Altura",
    (panel: HTMLElement) => slide(panel, "Altura da legenda", 30),
    { offset: 30 },
    "--cap-top",
    "30%",
  ],
  [
    "Borda",
    (panel: HTMLElement) => slide(panel, "Espessura da borda", 6),
    { border: 6 },
    "--cap-stroke",
    "1.1111cqw",
  ],
  [
    "Cor da borda",
    (panel: HTMLElement) => pick(panel, "Cor da borda", "Branco"),
    { border_color: "#FFFFFF" },
    "--cap-stroke-color",
    "#FFFFFF",
  ],
  [
    "Sombra",
    (panel: HTMLElement) => pick(panel, "Sombra", "Forte"),
    { shadow: "strong" },
    "--cap-shadow",
    "0.463cqw 0.463cqw 0 rgba(0, 0, 0, 0.863)",
  ],
])(
  "saves %s by itself, only that field, and the preview shows it",
  async (_name, change, body, property, value) => {
    const panel = await openCaption();

    change(panel);
    await settle();

    expect([patches(), overlayStyle(property)]).toEqual([[body], value]);
  },
);

test("saves the font chosen among the fonts the API knows", async () => {
  const panel = await openCaption(churchCaption({ font: "Montserrat Bold" }));
  const font = within(panel).getByRole("combobox", { name: "Fonte" });
  const options = within(font)
    .getAllByRole("option")
    .map((option) => option.textContent);

  fireEvent.change(font, { target: { value: "Open Sans Bold" } });
  await settle();

  expect([options, patches(), overlayStyle("--cap-font")]).toEqual([
    ["Montserrat Bold", "Open Sans Bold"],
    [{ font: "Open Sans Bold" }],
    '"Open Sans"',
  ]);
});

test("turns the caption off and takes it out of the preview", async () => {
  const panel = await openCaption();

  pick(panel, "Legenda", "Não");
  await settle();

  expect([patches(), overlay()]).toEqual([[{ enabled: false }], null]);
});

test("takes the height to the position's, as the API answers", async () => {
  const panel = await openCaption();

  pick(panel, "Posição", "Base");
  await settle();

  expect(within(panel).getByRole("slider", { name: "Altura da legenda" })).toHaveValue("78");
});

test("waits 400 ms after the change before saving", async () => {
  const panel = await openCaption();

  slide(panel, "Tamanho", 70);
  await settle(399);
  const before = patches().length;
  await settle(1);

  expect([before, patches()]).toEqual([0, [{ size: 70 }]]);
});

test("saves quick changes to the same field once, with the last value", async () => {
  const panel = await openCaption();

  slide(panel, "Tamanho", 70);
  await settle(100);
  slide(panel, "Tamanho", 80);
  await settle(100);
  slide(panel, "Tamanho", 90);
  await settle();

  expect(patches()).toEqual([{ size: 90 }]);
});

test("says Salvo once the API saved the change", async () => {
  const panel = await openCaption();

  pick(panel, "Sombra", "Não");
  const before = screen.queryByText("Salvo");
  await settle();

  expect([before, screen.queryByText("Salvo")?.textContent]).toEqual([null, "Salvo"]);
});

test("shows the API's reason next to the field and keeps the saved value on a 400", async () => {
  const panel = await openCaption(churchCaption(), () =>
    apiError(400, "invalid_argument", "O tamanho vai de 24 a 160 px.", {
      argument: "size",
      min: 24,
      max: 160,
    }),
  );

  slide(panel, "Tamanho", 170);
  await settle();

  const size = within(panel).getByRole("slider", { name: "Tamanho" });
  expect({
    invalid: size.getAttribute("aria-invalid"),
    value: (size as HTMLInputElement).value,
    preview: overlayStyle("--cap-size"),
    saved: screen.queryByText("Salvo"),
  }).toEqual({ invalid: "true", value: "60", preview: "5.5556cqw", saved: null });
  expect(size).toHaveAccessibleDescription("O tamanho vai de 24 a 160 px.");
});

test("restores the church's style, switched on, in the form and in the preview", async () => {
  const panel = await openCaption(churchCaption({ size: 108, color: "#FFFFFF" }));

  fireEvent.click(within(panel).getByRole("button", { name: "Restaurar padrão" }));
  await settle(0);

  expect({
    deleted: opened.calls.some(({ method }) => method === "DELETE"),
    size: (within(panel).getByRole("slider", { name: "Tamanho" }) as HTMLInputElement).value,
    preview: [overlayStyle("--cap-size"), overlayStyle("--cap-color")],
  }).toEqual({ deleted: true, size: "60", preview: ["5.5556cqw", "#FFD600"] });
});

test("drops a change still waiting when the style is restored", async () => {
  const panel = await openCaption();

  slide(panel, "Tamanho", 90);
  fireEvent.click(within(panel).getByRole("button", { name: "Restaurar padrão" }));
  await settle();

  expect(patches()).toEqual([]);
});
