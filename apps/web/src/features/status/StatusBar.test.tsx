import { act, render, screen } from "@testing-library/react";
import { afterEach } from "vitest";

import { fakeApi } from "../../test/fakeApi";
import { busyMachine, idleMachine, runningTask } from "../../test/fixtures";
import { MachineStatusProvider } from "./MachineStatus";
import { StatusBar } from "./StatusBar";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function renderBar() {
  return render(
    <MachineStatusProvider>
      <StatusBar />
    </MachineStatusProvider>,
  );
}

test("says the machine is free when nobody holds the lock", async () => {
  fakeApi({ "GET /api/status": { body: idleMachine() } });

  renderBar();

  expect(await screen.findByRole("contentinfo")).toHaveTextContent("Máquina livre");
});

test("says what holds the machine, for how long and how far it got", async () => {
  fakeApi({ "GET /api/status": { body: busyMachine(runningTask({ progress: 0.35 })) } });

  renderBar();

  expect(await screen.findByRole("contentinfo")).toHaveTextContent(
    "Ocupada: processando a pregação 12 · há 3 min35%",
  );
});

test("keeps the machine free while only a suggestion runs, and says so", async () => {
  fakeApi({
    "GET /api/status": {
      body: { lock: { held: false }, running_tasks: [runningTask({ kind: "suggest" })] },
    },
  });

  renderBar();

  expect(await screen.findByRole("contentinfo")).toHaveTextContent(
    "Máquina livre · sugerindo cortes da pregação 12",
  );
});

function pollIntervals(): void {
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
}

async function nextPoll(): Promise<void> {
  await act(async () => {
    vi.advanceTimersByTime(3000);
  });
}

function statusReplies(...bodies: unknown[]) {
  let call = 0;
  return {
    "GET /api/status": () => {
      const body = bodies[Math.min(call, bodies.length - 1)];
      call += 1;
      return body instanceof Error ? { reject: body } : { body };
    },
  };
}

test("updates by itself every 3 seconds", async () => {
  pollIntervals();
  fakeApi(statusReplies(idleMachine(), busyMachine()));
  renderBar();
  await screen.findByText("Máquina livre");

  await nextPoll();

  expect(await screen.findByRole("contentinfo")).toHaveTextContent(/^Ocupada/);
});

test("stops asking once the bar is gone", async () => {
  pollIntervals();
  const calls = fakeApi(statusReplies(idleMachine()));
  const { unmount } = renderBar();
  await screen.findByText("Máquina livre");

  unmount();
  await nextPoll();

  expect(calls).toHaveLength(1);
});

test("says the status is unavailable while the API is down and recovers after", async () => {
  pollIntervals();
  fakeApi(statusReplies(new TypeError("Failed to fetch"), idleMachine()));
  renderBar();
  const unavailable = await screen.findByText("Estado da máquina indisponível");

  await nextPoll();

  expect([unavailable.isConnected, screen.getByRole("contentinfo").textContent]).toEqual([
    false,
    "Máquina livre",
  ]);
});

test("waits the 3 seconds before asking again", async () => {
  pollIntervals();
  const calls = fakeApi(statusReplies(idleMachine()));
  renderBar();
  await screen.findByText("Máquina livre");

  await act(async () => {
    vi.advanceTimersByTime(2999);
  });

  expect(calls).toHaveLength(1);
});
