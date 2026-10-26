import { afterEach } from "vitest";

import { apiError, fakeApi } from "../test/fakeApi";
import { admin, createdSermon, listedSermon } from "../test/fixtures";
import { ApiError, createSermon, getMe, listSermons } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) {
      return error;
    }
    throw error;
  }
  throw new Error("expected the call to fail");
}

test("returns the body the API sends on success", async () => {
  const sermon = listedSermon();
  fakeApi({ "GET /api/sermons": { body: { items: [sermon] } } });

  expect(await listSermons()).toEqual([sermon]);
});

test("turns an error body into an error with its status, code, message and details", async () => {
  fakeApi({
    "POST /api/sermons": apiError(400, "invalid_argument", "Link inválido.", {
      argument: "link",
    }),
  });

  const error = await failure(createSermon("https://exemplo.org/video"));

  const { status, code, message, details } = error;
  expect({ status, code, message, details }).toEqual({
    status: 400,
    code: "invalid_argument",
    message: "Link inválido.",
    details: { argument: "link" },
  });
});

test("reports a body that is not the API's JSON as the API being unavailable", async () => {
  fakeApi({ "GET /api/sermons": { status: 502, raw: "<html>502 Bad Gateway</html>" } });

  const error = await failure(listSermons());

  expect([error.status, error.code]).toEqual([502, "unavailable"]);
});

test("reports a request that never reached the API as a network error", async () => {
  fakeApi({ "GET /api/sermons": { reject: new TypeError("Failed to fetch") } });

  const error = await failure(listSermons());

  expect(error.code).toBe("network_error");
});

test("reads who is calling from GET /api/me", async () => {
  fakeApi({ "GET /api/me": { body: admin() } });

  expect(await getMe()).toEqual(admin());
});

test.each([
  [401, "unauthenticated"],
  [403, "forbidden"],
])("tells a %i from the other identity failure by its code", async (status, code) => {
  fakeApi({ "GET /api/me": apiError(status, code, "Acesso recusado.") });

  expect((await failure(getMe())).code).toBe(code);
});

test("posts the link as JSON with only the url field", async () => {
  const calls = fakeApi({ "POST /api/sermons": { status: 201, body: createdSermon() } });

  await createSermon("https://youtu.be/lmnopqrstuv");

  expect([calls[0].headers.get("Content-Type"), calls[0].body]).toEqual([
    "application/json",
    { url: "https://youtu.be/lmnopqrstuv" },
  ]);
});
