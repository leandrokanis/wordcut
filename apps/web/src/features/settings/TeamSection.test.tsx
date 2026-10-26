import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach } from "vitest";

import { fakeIntersectionObserver } from "../../test/fakeIntersectionObserver";
import { apiError, type RecordedCall } from "../../test/fakeApi";
import { admin, assistant, member, team } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeSettingsApi, writes } from "../../test/settingsApi";

beforeEach(() => {
  fakeIntersectionObserver();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function teamSection(): Promise<HTMLElement> {
  await screen.findByRole("navigation", { name: "Seções das configurações" });
  const heading = screen.getByRole("heading", { level: 2, name: "Pessoas" });
  const section = heading.closest("section") as HTMLElement;
  await within(section).findByRole("combobox", { name: "Papel de admin@exemplo.org" });
  return section;
}

function roleOf(section: HTMLElement, email: string): string | undefined {
  const select = within(section).getByRole("combobox", { name: `Papel de ${email}` });
  return (select as HTMLSelectElement).selectedOptions[0]?.textContent ?? undefined;
}

test("lists the team by e-mail, each with its role and a way out", async () => {
  fakeSettingsApi();
  renderRoute("/settings");
  const section = await teamSection();

  expect([
    roleOf(section, "admin@exemplo.org"),
    roleOf(section, "assistente@exemplo.org"),
    within(section)
      .getAllByRole("button", { name: /^Remover / })
      .map((button) => button.getAttribute("aria-label")),
  ]).toEqual([
    "Administrador",
    "Assistente",
    ["Remover admin@exemplo.org", "Remover assistente@exemplo.org"],
  ]);
});

/** ADR-0021: the e-mail goes only in the body, never in a path. */
function urlsWithEmail(calls: RecordedCall[]): string[] {
  return calls.map((call) => call.url).filter((url) => url.includes("@"));
}

test("changes a role by the e-mail in the body, and says Salvo", async () => {
  const calls = fakeSettingsApi({
    "POST /api/members/set-role": { body: member({ role: "admin" }) },
  });
  renderRoute("/settings");
  const section = await teamSection();

  await userEvent.selectOptions(
    within(section).getByRole("combobox", { name: "Papel de assistente@exemplo.org" }),
    "Administrador",
  );

  await screen.findByText("Salvo");
  expect([writes(calls), urlsWithEmail(calls), roleOf(section, "assistente@exemplo.org")]).toEqual([
    [["POST /api/members/set-role", { email: "assistente@exemplo.org", role: "admin" }]],
    [],
    "Administrador",
  ]);
});

const LAST_ADMIN = apiError(409, "last_admin", "A equipe precisa de ao menos um administrador.");

test("puts the role back when the API keeps the last administrator", async () => {
  fakeSettingsApi({ "POST /api/members/set-role": LAST_ADMIN });
  renderRoute("/settings");
  const section = await teamSection();

  await userEvent.selectOptions(
    within(section).getByRole("combobox", { name: "Papel de admin@exemplo.org" }),
    "Assistente",
  );

  expect([
    (await within(section).findByRole("alert")).textContent,
    roleOf(section, "admin@exemplo.org"),
    screen.queryByText("Salvo"),
  ]).toEqual(["A equipe precisa de ao menos um administrador.", "Administrador", null]);
});

function emails(section: HTMLElement): (string | null)[] {
  return [...section.querySelectorAll(".team .mono")].map((cell) => cell.textContent);
}

test("removes a member by the e-mail in the body", async () => {
  const calls = fakeSettingsApi({
    "POST /api/members/remove": { body: { email: "assistente@exemplo.org", removed: true } },
  });
  renderRoute("/settings");
  const section = await teamSection();

  await userEvent.click(
    within(section).getByRole("button", { name: "Remover assistente@exemplo.org" }),
  );

  await screen.findByText("Salvo");
  expect([writes(calls), urlsWithEmail(calls), emails(section)]).toEqual([
    [["POST /api/members/remove", { email: "assistente@exemplo.org" }]],
    [],
    ["admin@exemplo.org"],
  ]);
});

test("keeps the last administrator on the team when the API refuses to remove it", async () => {
  fakeSettingsApi({ "POST /api/members/remove": LAST_ADMIN });
  renderRoute("/settings");
  const section = await teamSection();

  await userEvent.click(within(section).getByRole("button", { name: "Remover admin@exemplo.org" }));

  expect([
    (await within(section).findByRole("alert")).textContent,
    emails(section),
  ]).toEqual([
    "A equipe precisa de ao menos um administrador.",
    ["admin@exemplo.org", "assistente@exemplo.org"],
  ]);
});

test("gives access to a new e-mail with the role chosen, as the API stores it", async () => {
  const calls = fakeSettingsApi({
    "POST /api/members": {
      status: 201,
      body: member({ email: "nova@exemplo.org", role: "admin" }),
    },
  });
  renderRoute("/settings");
  const section = await teamSection();
  const field = within(section).getByRole("textbox", { name: "E-mail" });

  await userEvent.selectOptions(
    within(section).getByRole("combobox", { name: "Papel do novo membro" }),
    "Administrador",
  );
  await userEvent.type(field, "Nova@Exemplo.org{Enter}");

  await screen.findByText("Salvo");
  expect([writes(calls), emails(section), (field as HTMLInputElement).value]).toEqual([
    [["POST /api/members", { email: "Nova@Exemplo.org", role: "admin" }]],
    ["admin@exemplo.org", "assistente@exemplo.org", "nova@exemplo.org"],
    "",
  ]);
});

test("tells why an e-mail was refused, adding no one and not repeating it", async () => {
  fakeSettingsApi({
    "POST /api/members": apiError(400, "invalid_argument", "E-mail inválido."),
  });
  renderRoute("/settings");
  const section = await teamSection();

  await userEvent.type(within(section).getByRole("textbox", { name: "E-mail" }), "sem-arroba{Enter}");

  const reason = await within(section).findByRole("alert");
  expect([reason.textContent, emails(section), screen.queryByText("Salvo")]).toEqual([
    "E-mail inválido.",
    ["admin@exemplo.org", "assistente@exemplo.org"],
    null,
  ]);
});

test("sends an administrator who gives up the role to the refusal, as an assistant", async () => {
  let me = admin();
  fakeSettingsApi({
    "GET /api/me": () => ({ body: me }),
    "GET /api/members": {
      body: { items: [...team(), member({ email: "outro-admin@exemplo.org", role: "admin" })] },
    },
    "POST /api/members/set-role": () => {
      me = assistant();
      return { body: member({ email: "admin@exemplo.org", role: "assistant" }) };
    },
  });
  renderRoute("/settings");
  const section = await teamSection();

  await userEvent.selectOptions(
    within(section).getByRole("combobox", { name: "Papel de admin@exemplo.org" }),
    "Assistente",
  );

  expect(
    await screen.findByText("Só o administrador acessa as configurações."),
  ).toBeInTheDocument();
});
