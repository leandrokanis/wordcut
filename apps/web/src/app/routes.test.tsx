import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { fakeShellApi } from "../test/shellApi";
import { cutPreview, listedSermon, processedSermon, shownCut } from "../test/fixtures";
import { renderRoute } from "../test/renderRoute";

afterEach(() => {
  vi.unstubAllGlobals();
});

function path(): HTMLElement {
  return screen.getByRole("navigation", { name: "Caminho" });
}

test("shows only Pregações, as the current level, on the sermon list", async () => {
  fakeShellApi({});

  renderRoute("/");
  await screen.findByRole("navigation", { name: "Caminho" });

  const current = await within(path()).findByText("Pregações");
  expect(current).toHaveAttribute("aria-current", "page");
});

test("shows the sermon's title from the API after Pregações inside a sermon", async () => {
  fakeShellApi({ "GET /api/sermons/12": { body: listedSermon({ title: "Culto de domingo" }) } });

  renderRoute("/sermons/12");
  await screen.findByRole("navigation", { name: "Caminho" });

  expect(await within(path()).findByText("Culto de domingo")).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(within(path()).getByRole("link", { name: "Pregações" })).toHaveAttribute("href", "/");
});

function cutOfSermon() {
  return {
    "GET /api/cuts/34": { body: shownCut({ title: "Fé no deserto" }) },
    "GET /api/cuts/34/preview": { body: cutPreview() },
    "GET /api/sermons/12": { body: processedSermon({ title: "Culto de domingo" }) },
  };
}

test("shows the sermon and the cut after Pregações inside a cut", async () => {
  fakeShellApi(cutOfSermon());

  renderRoute("/cuts/34");
  await screen.findByRole("navigation", { name: "Caminho" });

  await within(path()).findByText("Fé no deserto");
  expect(path()).toHaveTextContent(/^Pregações\/Culto de domingo\/Fé no deserto$/);
});

test("goes back to the sermon by clicking its title in the path", async () => {
  fakeShellApi(cutOfSermon());
  renderRoute("/cuts/34");
  await screen.findByRole("navigation", { name: "Caminho" });

  await userEvent.click(await within(path()).findByRole("link", { name: "Culto de domingo" }));

  expect(await within(path()).findByText("Culto de domingo")).toHaveAttribute(
    "aria-current",
    "page",
  );
});

test("goes back to the sermon list by clicking Pregações in the path", async () => {
  fakeShellApi(cutOfSermon());
  renderRoute("/cuts/34");
  await screen.findByRole("navigation", { name: "Caminho" });

  await userEvent.click(await within(path()).findByRole("link", { name: "Pregações" }));

  expect(await screen.findByRole("heading", { name: "Pregações" })).toBeInTheDocument();
});

test("does not make the current level a link", async () => {
  fakeShellApi(cutOfSermon());
  renderRoute("/cuts/34");
  await screen.findByRole("navigation", { name: "Caminho" });

  await within(path()).findByText("Fé no deserto");

  expect(within(path()).queryByRole("link", { name: "Fé no deserto" })).toBeNull();
});

test("opens the cut's level, with its 9:16 preview, inside a cut", async () => {
  fakeShellApi(cutOfSermon());

  renderRoute("/cuts/34");

  expect(await screen.findByLabelText("Prévia do corte")).toBeInTheDocument();
});

test("tells a missing cut apart without losing the path", async () => {
  fakeShellApi({});

  renderRoute("/cuts/99");
  await screen.findByRole("navigation", { name: "Caminho" });

  expect(await screen.findByText("Corte não encontrado.")).toBeInTheDocument();
  expect(within(path()).getByRole("link", { name: "Pregações" })).toBeInTheDocument();
});

test("tells a missing sermon apart without losing the path", async () => {
  fakeShellApi({});

  renderRoute("/sermons/99");
  await screen.findByRole("navigation", { name: "Caminho" });

  expect(await screen.findByText("Pregação não encontrada.")).toBeInTheDocument();
  expect(within(path()).getByRole("link", { name: "Pregações" })).toBeInTheDocument();
});

test("opens the settings as a screen of their own, without the path", async () => {
  fakeShellApi({});

  renderRoute("/settings");

  expect(await screen.findByRole("heading", { name: "Configurações" })).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "Caminho" })).toBeNull();
});
