import { act, fireEvent, screen, within } from "@testing-library/react";
import { afterEach } from "vitest";

import { live, openCut, type OpenedCut } from "../../test/cutLevel";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

let opened: OpenedCut;

async function openTabs() {
  opened = await openCut();
  return screen.getByRole("tablist");
}

function selectedTab(): string | null {
  return screen.getByRole("tab", { selected: true }).textContent;
}

function captionLayer(): HTMLElement {
  return within(screen.getByRole("region", { name: "Timeline" })).getByRole("button", {
    name: "Camada Legenda",
  });
}

test("opens on Texto, with the sentences of the cut's range for the administrator", async () => {
  await openTabs();

  const panel = screen.getByRole("tabpanel");
  expect([selectedTab(), panel.textContent]).toEqual([
    "Texto",
    expect.stringMatching(/Irmãos, graça paz\..*Então Deus governa\..*Amém, igreja\./),
  ]);
});

test("opens Legenda from the caption layer of the timeline", async () => {
  await openTabs();

  fireEvent.pointerDown(captionLayer());

  expect(selectedTab()).toBe("Legenda");
});

test("goes back to Texto when Legenda is closed", async () => {
  await openTabs();
  fireEvent.pointerDown(captionLayer());

  fireEvent.click(screen.getByRole("button", { name: "Fechar legenda" }));

  expect(selectedTab()).toBe("Texto");
});

test.each([
  ["the preview", () => screen.getByLabelText("Prévia do corte")],
  ["the video track", () => screen.getByRole("group", { name: "Trecho 1" })],
  ["the transport", () => screen.getByLabelText("Tempo do corte")],
])("goes back to Texto on a click on %s", async (_area, area) => {
  await openTabs();
  fireEvent.pointerDown(captionLayer());

  fireEvent.pointerDown(area());

  expect(selectedTab()).toBe("Texto");
});

test("keeps Legenda on a click inside the panel or on a word of the caption", async () => {
  await openTabs();
  fireEvent.pointerDown(captionLayer());
  act(() => opened.players.current().moveTo(live(2.6)));

  fireEvent.pointerDown(screen.getByRole("tabpanel"));
  fireEvent.pointerDown(
    within(screen.getByRole("group", { name: "Legenda na prévia" })).getByText("Deus"),
  );

  expect(selectedTab()).toBe("Legenda");
});

test("switches between the tabs by their names", async () => {
  await openTabs();

  fireEvent.click(screen.getByRole("tab", { name: "Legenda" }));
  const legenda = selectedTab();
  fireEvent.click(screen.getByRole("tab", { name: "Texto" }));

  expect([legenda, selectedTab()]).toEqual(["Legenda", "Texto"]);
});
