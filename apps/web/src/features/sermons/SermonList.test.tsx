import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { apiError, type RecordedCall } from "../../test/fakeApi";
import { fakeShellApi } from "../../test/shellApi";
import {
  assistant,
  busyMachine,
  listedSermon,
  runningTask,
} from "../../test/fixtures";
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
      listedSermon({
        id: 12,
        title: "Culto de domingo",
        service_date: "2026-10-18",
      }),
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

  expect(
    await screen.findByRole("link", { name: /Culto de domingo/ }),
  ).toHaveAttribute("href", "/sermons/12");
});

test("says the duration is still to be set for a sermon without borders", async () => {
  fakeShellApi(listed([listedSermon({ status: "created", duration: null })]));

  renderRoute("/");

  expect(await screen.findByRole("listitem")).toHaveTextContent(
    "Duração a delimitar",
  );
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

  expect(
    await screen.findByText("Nenhuma pregação ainda."),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Nova pregação" }),
  ).toBeInTheDocument();
});

test("explains that the API is down instead of showing a blank list", async () => {
  fakeShellApi({
    "GET /api/sermons": { reject: new TypeError("Failed to fetch") },
  });

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
    "GET /api/status": {
      body: busyMachine(runningTask({ sermon_id: 12, progress: 0.42 })),
    },
  });

  renderRoute("/");

  expect(await screen.findByText("Processando 42%")).toBeInTheDocument();
});

/** The list of two sermons, 12 and 11, that loses 12 once ``DELETE /api/sermons/12`` was
 * called; the recorded calls. */
function deletableList(): RecordedCall[] {
  const both = [
    listedSermon({ id: 12, title: "Culto de domingo" }),
    listedSermon({ id: 11, title: "Culto de quarta" }),
  ];
  const calls: RecordedCall[] = fakeShellApi({
    "GET /api/sermons": () => ({
      body: { items: deleted(calls) ? both.slice(1) : both },
    }),
    "DELETE /api/sermons/12": { body: { id: 12, deleted: true } },
  });
  return calls;
}

function deleted(calls: RecordedCall[]): boolean {
  return calls.some((call) => call.method === "DELETE");
}

async function cardOf(title: string): Promise<HTMLElement> {
  const link = await screen.findByRole("link", { name: new RegExp(title) });
  return link.closest("li") as HTMLElement;
}

async function askToDelete(card: HTMLElement) {
  await userEvent.click(
    within(card).getByRole("button", { name: "Mais ações" }),
  );
  await userEvent.click(within(card).getByRole("menuitem", { name: "Apagar" }));
}

test("an administrator deletes a sermon from its menu once confirmed, and it leaves the list", async () => {
  const calls = deletableList();
  renderRoute("/");
  await askToDelete(await cardOf("Culto de domingo"));

  await userEvent.click(screen.getByRole("button", { name: "Apagar" }));

  await waitFor(() =>
    expect(screen.queryByRole("link", { name: /Culto de domingo/ })).toBeNull(),
  );
  expect(
    calls.filter((call) => call.method === "DELETE").map((call) => call.url),
  ).toEqual(["/api/sermons/12"]);
});

test.each([
  [{ suggested: 3, chosen: 1, discarded: 0 }, "Apagar a pregação e 4 cortes?"],
  [{ suggested: 1, chosen: 1, discarded: 1 }, "Apagar a pregação e 3 cortes?"],
  [{ suggested: 0, chosen: 0, discarded: 1 }, "Apagar a pregação e 1 corte?"],
  [{ suggested: 0, chosen: 0, discarded: 0 }, "Apagar a pregação e 0 cortes?"],
])(
  "the confirmation counts every cut that goes with the sermon (%o)",
  async (counts, asked) => {
    fakeShellApi(listed([listedSermon({ id: 12, cut_counts: counts })]));
    renderRoute("/");

    await askToDelete(await cardOf("Culto de domingo"));

    expect(screen.getByText(asked)).toBeInTheDocument();
  },
);

test("Cancelar closes the confirmation without deleting anything", async () => {
  const calls = deletableList();
  renderRoute("/");
  await askToDelete(await cardOf("Culto de domingo"));

  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));

  expect([
    screen.queryByText(/Apagar a pregação/),
    deleted(calls),
    screen.getByRole("link", { name: /Culto de domingo/ }),
  ]).toEqual([null, false, expect.anything()]);
});

test("an assistant has no menu to delete a sermon", async () => {
  fakeShellApi(listed([listedSermon({ id: 12 })]), assistant());
  renderRoute("/");

  await cardOf("Culto de domingo");

  expect(screen.queryByRole("button", { name: "Mais ações" })).toBeNull();
});

test("a sermon that cannot be deleted stays listed with the reason", async () => {
  const calls = fakeShellApi({
    ...listed([listedSermon({ id: 12 })]),
    "DELETE /api/sermons/12": apiError(
      409,
      "busy",
      "A pregação 12 tem uma tarefa process em andamento (tarefa 7).",
    ),
  });
  renderRoute("/");
  const card = await cardOf("Culto de domingo");
  await askToDelete(card);

  await userEvent.click(screen.getByRole("button", { name: "Apagar" }));

  expect(await within(card).findByRole("alert")).toHaveTextContent(
    "A pregação 12 tem uma tarefa process em andamento (tarefa 7).",
  );
  expect([
    deleted(calls),
    screen.getByRole("link", { name: /Culto de domingo/ }),
  ]).toEqual([true, expect.anything()]);
});

test.each([
  ["Escape", () => userEvent.keyboard("{Escape}")],
  [
    "a press outside",
    () => userEvent.click(screen.getByRole("heading", { name: "Pregações" })),
  ],
])("%s closes the sermon's menu", async (_, dismiss) => {
  fakeShellApi(listed([listedSermon({ id: 12 })]));
  renderRoute("/");
  const card = await cardOf("Culto de domingo");
  await userEvent.click(
    within(card).getByRole("button", { name: "Mais ações" }),
  );

  await dismiss();

  expect(within(card).queryByRole("menu")).toBeNull();
});
