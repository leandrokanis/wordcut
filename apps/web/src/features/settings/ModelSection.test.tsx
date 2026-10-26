import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach } from "vitest";

import { apiError } from "../../test/fakeApi";
import { fakeIntersectionObserver } from "../../test/fakeIntersectionObserver";
import { settings } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";
import { fakeSettingsApi, writes } from "../../test/settingsApi";

beforeEach(() => {
  fakeIntersectionObserver();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function modelSection() {
  const heading = await screen.findByRole("heading", { level: 2, name: "Modelo" });
  return heading.closest("section") as HTMLElement;
}

test("shows the models, the key only masked and whether the cookies are there", async () => {
  fakeSettingsApi({ "GET /api/settings": { body: settings({ youtube_cookies: true }) } });
  renderRoute("/settings");
  const section = await modelSection();

  const llm = await within(section).findByRole("textbox", { name: "Modelo" });
  const whisper = within(section).getByRole("textbox", { name: "Modelo do WhisperX" });
  expect([
    (llm as HTMLInputElement).value,
    (whisper as HTMLInputElement).value,
    within(section).getByText("Atual: ••••7a2c").textContent,
    within(section).getByText("Presentes").textContent,
  ]).toEqual(["provedor/modelo-teste", "large-v3", "Atual: ••••7a2c", "Presentes"]);
});

test("saves a changed model once it is confirmed with Enter, and says Salvo", async () => {
  const calls = fakeSettingsApi({
    "PATCH /api/settings": { body: settings({ llm_model: "provedor/outro" }) },
  });
  renderRoute("/settings");
  const llm = await screen.findByRole("textbox", { name: "Modelo" });

  await userEvent.clear(llm);
  await userEvent.type(llm, "provedor/outro{Enter}");

  expect(await screen.findByText("Salvo")).toBeInTheDocument();
  expect(writes(calls)).toEqual([["PATCH /api/settings", { llm_model: "provedor/outro" }]]);
});

test("keeps a blank model unsaved, with the API's reason beside the field and no Salvo", async () => {
  fakeSettingsApi({
    "PATCH /api/settings": apiError(400, "invalid_argument", "O modelo não pode ficar em branco."),
  });
  renderRoute("/settings");
  const llm = await screen.findByRole("textbox", { name: "Modelo" });

  await userEvent.clear(llm);
  await userEvent.tab();

  const reason = await screen.findByRole("alert");
  expect([reason.textContent, llm.getAttribute("aria-describedby"), screen.queryByText("Salvo")])
    .toEqual(["O modelo não pode ficar em branco.", reason.id, null]);
});

test("leaves an unchanged model alone when the field loses focus", async () => {
  const calls = fakeSettingsApi();
  renderRoute("/settings");
  const whisper = await screen.findByRole("textbox", { name: "Modelo do WhisperX" });

  await userEvent.click(whisper);
  await userEvent.tab();

  expect(writes(calls)).toEqual([]);
});

// Fictitious secrets: none of them ever reaches the screen or the console once sent.
const KEY = "sk-teste-ficticia-9f3a";

function spyConsole() {
  return (["log", "info", "warn", "error", "debug"] as const).map((method) =>
    vi.spyOn(console, method).mockImplementation(() => {}),
  );
}

function logged(spies: ReturnType<typeof spyConsole>): string {
  return JSON.stringify(spies.flatMap((spy) => spy.mock.calls));
}

test("sends a pasted key with Enter and shows only the mask the API answers", async () => {
  const spies = spyConsole();
  const calls = fakeSettingsApi({
    "PUT /api/settings/llm-key": { body: settings({ llm_key: "••••9f3a" }) },
  });
  const { container } = renderRoute("/settings");
  const field = await screen.findByLabelText("Nova chave");

  await userEvent.type(field, `${KEY}{Enter}`);

  await screen.findByText("Atual: ••••9f3a");
  expect([
    writes(calls),
    (field as HTMLInputElement).value,
    container.innerHTML.includes(KEY),
    logged(spies).includes(KEY),
  ]).toEqual([[["PUT /api/settings/llm-key", { value: KEY }]], "", false, false]);
});

test("sends no key when Enter finds the field blank", async () => {
  const calls = fakeSettingsApi();
  renderRoute("/settings");
  const field = await screen.findByLabelText("Nova chave");

  await userEvent.type(field, "   {Enter}");

  expect(writes(calls)).toEqual([]);
});

test.each([
  [
    apiError(409, "config_not_writable", "A configuração não pode ser gravada por aqui."),
    "A configuração não pode ser gravada por aqui. Grave pela CLI no host: " +
      "wordcut settings set-key < chave.txt",
  ],
  [
    apiError(400, "invalid_argument", "A chave não pode ser gravada."),
    "A chave não pode ser gravada.",
  ],
])("tells why the key was refused, never showing or logging the key", async (reply, reason) => {
  const spies = spyConsole();
  fakeSettingsApi({ "PUT /api/settings/llm-key": reply });
  const { container } = renderRoute("/settings");
  const field = await screen.findByLabelText("Nova chave");

  await userEvent.type(field, `${KEY}{Enter}`);

  const alert = await screen.findByRole("alert");
  expect([
    alert.textContent,
    (field as HTMLInputElement).value,
    screen.getByText("Atual: ••••7a2c").textContent,
    container.innerHTML.includes(KEY),
    logged(spies).includes(KEY),
  ]).toEqual([reason, "", "Atual: ••••7a2c", false, false]);
});

const COOKIES = "# Netscape HTTP Cookie File\n.exemplo.org\tTRUE\t/\tTRUE\t0\tSID\tficticio-4b1e\n";

function cookiesFile(): File {
  return new File([COOKIES], "cookies.txt", { type: "text/plain" });
}

test("sends the chosen cookies file as it is and then only says they are there", async () => {
  const calls = fakeSettingsApi({
    "PUT /api/settings/youtube-cookies": { body: settings({ youtube_cookies: true }) },
  });
  const { container } = renderRoute("/settings");
  const picker = await screen.findByLabelText("Arquivo de cookies");

  await userEvent.upload(picker, cookiesFile());

  await screen.findByText("Presentes");
  expect([
    writes(calls),
    (picker as HTMLInputElement).value,
    container.innerHTML.includes("ficticio-4b1e"),
  ]).toEqual([[["PUT /api/settings/youtube-cookies", { value: COOKIES }]], "", false]);
});

test.each([
  [
    apiError(400, "invalid_argument", "Os cookies não estão no formato Netscape."),
    "Os cookies não estão no formato Netscape.",
  ],
  [
    apiError(409, "config_not_writable", "A configuração não pode ser gravada por aqui."),
    "A configuração não pode ser gravada por aqui. Grave pela CLI no host: " +
      "wordcut settings set-cookies < cookies.txt",
  ],
])("tells why the cookies were refused, never showing or logging them", async (reply, reason) => {
  const spies = spyConsole();
  fakeSettingsApi({ "PUT /api/settings/youtube-cookies": reply });
  const { container } = renderRoute("/settings");
  const picker = await screen.findByLabelText("Arquivo de cookies");

  await userEvent.upload(picker, cookiesFile());

  expect(await screen.findByRole("alert")).toHaveTextContent(reason);
  expect([
    screen.queryByText("Ausentes")?.textContent,
    container.innerHTML.includes("ficticio-4b1e"),
    logged(spies).includes("ficticio-4b1e"),
  ]).toEqual(["Ausentes", false, false]);
});
