import type { Me } from "../api/types";
import { fakeApi, type RecordedCall } from "./fakeApi";
import { admin, idleMachine } from "./fixtures";

/** ``fakeApi`` with the calls every screen makes: who is calling and the machine status. */
export function fakeShellApi(
  routes: Parameters<typeof fakeApi>[0],
  me: Me = admin(),
): RecordedCall[] {
  return fakeApi({
    "GET /api/me": { body: me },
    "GET /api/status": { body: idleMachine() },
    ...routes,
  });
}
