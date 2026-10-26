import { screen, within } from "@testing-library/react";
import { afterEach } from "vitest";

import { admin, assistant } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeShellApi } from "../../test/shellApi";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("gives the administrator a navigation of its own over the sections", async () => {
  fakeShellApi({}, admin());

  renderRoute("/settings");

  const navigation = await screen.findByRole("navigation", { name: "Seções das configurações" });
  expect(within(navigation).getAllByRole("link").map((link) => link.textContent)).toEqual([
    "Voltar às pregações",
    "Modelo",
    "Presets",
    "Filtros",
    "Valor",
    "Formato",
    "Pessoas",
    "Processamentos",
  ]);
});

test("refuses the settings to an assistant who opens them directly", async () => {
  fakeShellApi({}, assistant());

  renderRoute("/settings");

  expect(
    await screen.findByText("Só o administrador acessa as configurações."),
  ).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "Seções das configurações" })).toBeNull();
});
