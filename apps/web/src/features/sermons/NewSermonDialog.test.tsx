import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";

import { apiError, type RecordedCall, type Reply } from "../../test/fakeApi";
import { fakeShellApi } from "../../test/shellApi";
import { createdSermon, listedSermon } from "../../test/fixtures";
import { renderRoute } from "../../test/renderRoute";

const LINK = "https://youtu.be/lmnopqrstuv";

afterEach(() => {
  vi.unstubAllGlobals();
});

async function openDialog(): Promise<HTMLElement> {
  await userEvent.click(await screen.findByRole("button", { name: "Nova pregação" }));
  return screen.getByRole("dialog", { name: "Nova pregação" });
}

function field(): HTMLElement {
  return screen.getByRole("textbox", { name: "Link da live no YouTube" });
}

async function submitLink(): Promise<void> {
  await userEvent.type(field(), `${LINK}{Enter}`);
}

test("opens a modal dialog with the focus on the link field", async () => {
  fakeShellApi({ "GET /api/sermons": { body: { items: [] } } });
  renderRoute("/");

  const dialog = await openDialog();

  expect([dialog.getAttribute("aria-modal"), document.activeElement]).toEqual(["true", field()]);
});

test.each([
  ["the close button", () => userEvent.click(screen.getByRole("button", { name: "Fechar" }))],
  ["Esc", () => userEvent.keyboard("{Escape}")],
])("closes with %s", async (_, close) => {
  fakeShellApi({ "GET /api/sermons": { body: { items: [] } } });
  renderRoute("/");
  await openDialog();

  await close();

  expect(screen.queryByRole("dialog")).toBeNull();
});

function creatingReplies(created: Reply, listAfter: unknown[] = []) {
  let posted = false;
  return {
    "GET /api/sermons": () => ({ body: { items: posted ? listAfter : [] } }),
    "POST /api/sermons": () => {
      posted = true;
      return created;
    },
  };
}

test("sends only the pasted link to the API", async () => {
  const calls = fakeShellApi(creatingReplies({ status: 201, body: createdSermon() }));
  renderRoute("/");
  await openDialog();

  await submitLink();

  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(calls.filter((call) => call.method === "POST").map((call) => call.body)).toEqual([
    { url: LINK },
  ]);
});

test("shows the new sermon in the list with the live's title, date and duration", async () => {
  const created = createdSermon({
    title: "Culto de quarta",
    service_date: "2026-10-21",
    live_duration: 5430,
  });
  fakeShellApi(
    creatingReplies({ status: 201, body: created }, [
      listedSermon({ ...created, duration: null, status: "created" }),
    ]),
  );
  renderRoute("/");
  await openDialog();

  await submitLink();

  expect(await screen.findByRole("status")).toHaveTextContent(
    "Pregação criada: Culto de quarta, culto de 21/10/2026, live de 1:30:30.",
  );
  expect(screen.getByRole("listitem")).toHaveTextContent("Culto de quarta");
});

test("warns that the live has not ended without refusing the sermon", async () => {
  fakeShellApi(
    creatingReplies({ status: 201, body: createdSermon({ live_finished: false }) }, [
      listedSermon({ live_finished: false, status: "created", duration: null }),
    ]),
  );
  renderRoute("/");
  await openDialog();

  await submitLink();

  expect(await screen.findByRole("status")).toHaveTextContent("A live ainda não terminou.");
});

test.each([
  ["an invalid link", apiError(400, "invalid_argument", "Link inválido.", { argument: "link" })],
  ["a YouTube failure", apiError(502, "youtube_error", "O YouTube não respondeu.")],
])("shows the reason for %s next to the field, keeping the dialog open", async (_, reply) => {
  fakeShellApi(creatingReplies(reply));
  renderRoute("/");
  const dialog = await openDialog();

  await submitLink();

  const reason = (reply as { body: { error: { message: string } } }).body.error.message;
  await within(dialog).findByText(reason);
  expect(field()).toHaveAccessibleDescription(reason);
});

test("does not repeat the typed link in the reason", async () => {
  fakeShellApi(
    creatingReplies(apiError(400, "invalid_argument", "Link inválido.", { argument: "link" })),
  );
  renderRoute("/");
  await openDialog();

  await submitLink();

  await waitFor(() => expect(field()).toHaveAttribute("aria-invalid", "true"));
  expect(screen.getByRole("dialog")).not.toHaveTextContent(/youtu\.be/);
});

test("tells a video that already had a sermon apart, without listing it twice", async () => {
  const existing = listedSermon({ id: 12, title: "Culto de domingo" });
  let posted = false;
  fakeShellApi({
    "GET /api/sermons": { body: { items: [existing] } },
    "POST /api/sermons": () => {
      posted = true;
      return { status: 200, body: createdSermon({ id: 12, title: "Culto de domingo", created: false }) };
    },
  });
  renderRoute("/");
  await openDialog();

  await submitLink();

  expect(await screen.findByRole("status")).toHaveTextContent(
    "Esta live já tinha uma pregação: Culto de domingo.",
  );
  expect([posted, screen.getAllByRole("listitem").length]).toEqual([true, 1]);
});

/** The creation's ``POST`` waits until the test calls ``release``. */
function heldCreation() {
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let posted = false;
  const calls = fakeShellApi({
    "GET /api/sermons": () => ({
      body: { items: posted ? [listedSermon({ id: 13, title: "Culto de quarta" })] : [] },
    }),
    "POST /api/sermons": async () => {
      await held;
      posted = true;
      return { status: 201, body: createdSermon() };
    },
  });
  return { calls, release };
}

function posts(calls: RecordedCall[]): RecordedCall[] {
  return calls.filter((call) => call.method === "POST");
}

test("disables Carregar while the link is on its way", async () => {
  heldCreation();
  renderRoute("/");
  await openDialog();

  await submitLink();

  expect(screen.getByRole("button", { name: "Carregar" })).toBeDisabled();
});

test("sends the link once however many times it is confirmed", async () => {
  const { calls } = heldCreation();
  renderRoute("/");
  await openDialog();
  await submitLink();

  await userEvent.click(screen.getByRole("button", { name: "Carregar" }));
  await userEvent.type(field(), "{Enter}");
  fireEvent.submit((field() as HTMLInputElement).form as HTMLFormElement);

  expect(posts(calls)).toHaveLength(1);
});

test("follows the normal flow once the held reply arrives", async () => {
  const { calls, release } = heldCreation();
  renderRoute("/");
  await openDialog();
  await submitLink();
  await userEvent.click(screen.getByRole("button", { name: "Carregar" }));

  release();

  expect(await screen.findByRole("link", { name: /Culto de quarta/ })).toBeInTheDocument();
  expect([screen.queryByRole("dialog"), posts(calls).length]).toEqual([null, 1]);
});
