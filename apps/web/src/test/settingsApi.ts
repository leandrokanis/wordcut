import type { Me } from "../api/types";
import type { fakeApi, RecordedCall } from "./fakeApi";
import { admin, criteria, presets, settings, team } from "./fixtures";
import { fakeShellApi } from "./shellApi";

/** ``fakeShellApi`` with what the settings screen reads, from the fixtures; ``routes`` add to
 * or replace them. */
export function fakeSettingsApi(
  routes: Parameters<typeof fakeApi>[0] = {},
  me: Me = admin(),
): RecordedCall[] {
  return fakeShellApi(
    {
      "GET /api/settings": { body: settings() },
      "GET /api/criteria": { body: { items: criteria() } },
      "GET /api/presets": { body: { items: presets() } },
      "GET /api/members": { body: { items: team() } },
      ...routes,
    },
    me,
  );
}

/** The calls that changed something, as "METHOD /path" and body. */
export function writes(calls: RecordedCall[]): [string, unknown][] {
  return calls
    .filter((call) => call.method !== "GET")
    .map((call) => [`${call.method} ${call.url}`, call.body]);
}
