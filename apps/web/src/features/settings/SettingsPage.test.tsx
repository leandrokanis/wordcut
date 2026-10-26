import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach } from "vitest";

import {
  fakeIntersectionObserver,
  type FakeIntersection,
} from "../../test/fakeIntersectionObserver";
import { admin, assistant } from "../../test/fixtures";
import { apiError } from "../../test/fakeApi";
import { renderRoute } from "../../test/renderRoute";
import { fakeSettingsApi } from "../../test/settingsApi";
import { fakeShellApi } from "../../test/shellApi";

const SECTION_TITLES = ["Modelo", "Presets", "Filtros", "Valor", "Formato", "Pessoas"];

let intersection: FakeIntersection;

beforeEach(() => {
  intersection = fakeIntersectionObserver();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function sectionMenu() {
  return screen.findByRole("navigation", { name: "Seções das configurações" });
}

// Item 21 fixed seven links; item 26 (L1) drops Processamentos, which is not in its spec.
test("gives the administrator a navigation of its own over the prototype's sections", async () => {
  fakeShellApi({}, admin());

  renderRoute("/settings");

  const navigation = await sectionMenu();
  expect(within(navigation).getAllByRole("link").map((link) => link.textContent)).toEqual([
    "Voltar às pregações",
    ...SECTION_TITLES,
  ]);
});

test("lays every section out on the same scroll, one heading per menu entry", async () => {
  fakeShellApi({}, admin());

  renderRoute("/settings");
  await sectionMenu();

  expect(
    screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent),
  ).toEqual(SECTION_TITLES);
});

function currentLinks(navigation: HTMLElement) {
  return within(navigation)
    .getAllByRole("link")
    .filter((link) => link.getAttribute("aria-current") === "true")
    .map((link) => link.textContent);
}

test("jumps to the section a menu entry names and marks only that entry", async () => {
  fakeShellApi({}, admin());
  const scrolled: Element[] = [];
  Element.prototype.scrollIntoView = vi.fn(function (this: Element) {
    scrolled.push(this);
  });
  renderRoute("/settings");
  const navigation = await sectionMenu();

  await userEvent.click(within(navigation).getByRole("link", { name: "Formato" }));

  const formato = screen.getByRole("heading", { level: 2, name: "Formato" }).closest("section");
  expect([scrolled, currentLinks(navigation)]).toEqual([[formato], ["Formato"]]);
});

function section(title: string): Element {
  const heading = screen.getByRole("heading", { level: 2, name: title });
  return heading.closest("section") as Element;
}

test("follows the scroll: the menu marks the first section in the reading band", async () => {
  fakeShellApi({}, admin());
  renderRoute("/settings");
  const navigation = await sectionMenu();

  act(() => {
    intersection.intersect(section("Valor"), true);
    intersection.intersect(section("Filtros"), true);
  });
  const both = currentLinks(navigation);
  act(() => intersection.intersect(section("Filtros"), false));

  expect([both, currentLinks(navigation)]).toEqual([["Filtros"], ["Valor"]]);
});

/** What the observers watch farthest down the page: the bottom of the settings. */
function bottomOfPage(): Element {
  const watched = intersection.observers.flatMap((observer) => [...observer.observed]);
  return watched.reduce((last, element) =>
    last.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING ? element : last,
  );
}

test("marks the last section once the scroll reaches the bottom, short as it may be", async () => {
  fakeShellApi({}, admin());
  renderRoute("/settings");
  const navigation = await sectionMenu();
  act(() => intersection.intersect(section("Formato"), true));

  act(() => intersection.intersect(bottomOfPage(), true));

  expect(currentLinks(navigation)).toEqual(["Pessoas"]);
});

test("stops watching the scroll when the settings close", async () => {
  fakeShellApi({}, admin());
  const { unmount } = renderRoute("/settings");
  await sectionMenu();

  unmount();

  expect(intersection.observers.map((observer) => observer.disconnected)).toEqual([true, true]);
});

test("refuses the settings to an assistant who opens them directly", async () => {
  fakeShellApi({}, assistant());

  renderRoute("/settings");

  expect(
    await screen.findByText("Só o administrador acessa as configurações."),
  ).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "Seções das configurações" })).toBeNull();
});

test("asks the API nothing of the administrator's for an assistant", async () => {
  const calls = fakeSettingsApi({}, assistant());

  renderRoute("/settings");
  await screen.findByText("Só o administrador acessa as configurações.");

  const admin = /^\/api\/(settings|presets|criteria|members)/;
  expect(calls.filter((call) => admin.test(call.url))).toEqual([]);
});

test("shows the API's reason where a section could not load, keeping the others", async () => {
  fakeSettingsApi({
    "GET /api/members": apiError(500, "internal_error", "Falha ao ler a equipe."),
  });

  renderRoute("/settings");
  await sectionMenu();

  const pessoas = section("Pessoas") as HTMLElement;
  expect(await within(pessoas).findByRole("alert")).toHaveTextContent("Falha ao ler a equipe.");
  expect(await screen.findByRole("textbox", { name: "Modelo" })).toBeInTheDocument();
});
