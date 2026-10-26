import { screen } from "@testing-library/react";
import { afterEach } from "vitest";

import { fakeShellApi } from "../../test/shellApi";
import { busyMachine, listedSermon, runningTask } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";

afterEach(() => {
  vi.unstubAllGlobals();
});

function listed(items: unknown[]) {
  return { "GET /api/sermons": { body: { items } } };
}

test("lists each sermon in the API's order with its date, title, duration and state", async () => {
  fakeShellApi(
    listed([
      listedSermon({ id: 12, title: "Culto de domingo", service_date: "2026-10-18" }),
      listedSermon({
        id: 11,
        title: "Culto de quarta",
        service_date: "2026-10-14",
        duration: 1830,
        status: "trimmed",
      }),
    ]),
  );

  renderRoute("/");

  const items = await screen.findAllByRole("listitem");
  expect(items.map((item) => item.textContent)).toEqual([
    "18/10/2026Culto de domingoPronta41:15",
    "14/10/2026Culto de quartaDelimitada30:30",
  ]);
});

test("opens a sermon from its item", async () => {
  fakeShellApi(listed([listedSermon({ id: 12, title: "Culto de domingo" })]));

  renderRoute("/");

  expect(await screen.findByRole("link", { name: /Culto de domingo/ })).toHaveAttribute(
    "href",
    "/sermons/12",
  );
});

test("says the duration is still to be set for a sermon without borders", async () => {
  fakeShellApi(listed([listedSermon({ status: "created", duration: null })]));

  renderRoute("/");

  expect(await screen.findByRole("listitem")).toHaveTextContent("Duração a delimitar");
});

test.each([
  ["created", "A delimitar"],
  ["trimmed", "Delimitada"],
  ["processing", "Processando"],
  ["processed", "Pronta"],
  ["failed", "Falhou"],
] as const)("names the %s state in Portuguese", async (status, label) => {
  fakeShellApi(listed([listedSermon({ status })]));

  renderRoute("/");

  expect(await screen.findByRole("listitem")).toHaveTextContent(label);
});

test("offers Nova pregação when there is no sermon yet", async () => {
  fakeShellApi(listed([]));

  renderRoute("/");

  expect(await screen.findByText("Nenhuma pregação ainda.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Nova pregação" })).toBeInTheDocument();
});

test("explains that the API is down instead of showing a blank list", async () => {
  fakeShellApi({ "GET /api/sermons": { reject: new TypeError("Failed to fetch") } });

  renderRoute("/");

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Não foi possível carregar as pregações.",
  );
});

test.each(["/sermons/12", "/cuts/34", "/settings"])(
  "has no Nova pregação outside the sermon list (%s)",
  async (route) => {
    fakeShellApi({});

    renderRoute(route);

    await screen.findByRole("main");
    expect(screen.queryByRole("button", { name: "Nova pregação" })).toBeNull();
  },
);

test("shows how far a sermon being processed got, from the machine status", async () => {
  fakeShellApi({
    ...listed([listedSermon({ id: 12, status: "processing", duration: 2475 })]),
    "GET /api/status": { body: busyMachine(runningTask({ sermon_id: 12, progress: 0.42 })) },
  });

  renderRoute("/");

  expect(await screen.findByText("Processando 42%")).toBeInTheDocument();
});
