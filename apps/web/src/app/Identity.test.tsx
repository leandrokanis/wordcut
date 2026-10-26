import { screen, within } from "@testing-library/react";
import { afterEach } from "vitest";

import { apiError, fakeApi } from "../test/fakeApi";
import { admin, assistant } from "../test/fixtures";
import { renderRoute } from "../test/renderRoute";
import { fakeShellApi } from "../test/shellApi";

afterEach(() => {
  vi.unstubAllGlobals();
});

test.each([
  [401, "unauthenticated", "Você não está identificado."],
  [403, "forbidden", "Seu e-mail não faz parte da equipe."],
])("explains a %i on GET /api/me without loading any sermon", async (status, code, title) => {
  const calls = fakeApi({
    "GET /api/me": apiError(status, code, "Acesso recusado."),
    "GET /api/sermons": { body: { items: [] } },
  });

  renderRoute("/");

  expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
  expect(calls.map((call) => call.url)).toEqual(["/api/me"]);
});

test("explains that the API is down when it cannot tell who is calling", async () => {
  fakeApi({ "GET /api/me": { status: 502, raw: "<html>502 Bad Gateway</html>" } });

  renderRoute("/");

  expect(await screen.findByRole("heading", { name: "A API não respondeu." })).toBeInTheDocument();
});

test.each(["/", "/sermons/12", "/cuts/34", "/settings"])(
  "keeps the status bar in the footer of %s",
  async (route) => {
    fakeShellApi({});

    renderRoute(route);

    const footer = await screen.findByRole("contentinfo");
    expect(await within(footer).findByText("Máquina livre")).toBeInTheDocument();
  },
);

test("offers Configurações to an administrator", async () => {
  fakeShellApi({ "GET /api/sermons": { body: { items: [] } } }, admin());

  renderRoute("/");

  expect(await screen.findByRole("link", { name: "Configurações" })).toHaveAttribute(
    "href",
    "/settings",
  );
});

test("does not offer Configurações to an assistant", async () => {
  fakeShellApi({ "GET /api/sermons": { body: { items: [] } } }, assistant());

  renderRoute("/");

  await screen.findByRole("navigation", { name: "Caminho" });
  expect(screen.queryByRole("link", { name: "Configurações" })).toBeNull();
});
