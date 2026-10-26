import { act, renderHook } from "@testing-library/react";
import { afterEach } from "vitest";

import { fakeEventSource } from "../../test/fakeEventSource";
import { runningTask } from "../../test/fixtures";
import { useTaskEvents } from "./useTaskEvents";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("follows the task's events at its own address", () => {
  const { streams } = fakeEventSource();

  renderHook(() => useTaskEvents(9, () => {}));

  expect(streams().map(({ url }) => url)).toEqual(["/api/tasks/9/events"]);
});

test("keeps the task as its progress arrives", () => {
  const { streams } = fakeEventSource();
  const { result } = renderHook(() => useTaskEvents(9, () => {}));

  act(() => streams()[0].emit("progress", runningTask({ progress: 0.35 })));

  expect(result.current.task?.progress).toBe(0.35);
});

test.each(["done", "failed"])("closes the stream and tells the end on %s", (final) => {
  const { streams } = fakeEventSource();
  const onEnd = vi.fn();
  renderHook(() => useTaskEvents(9, onEnd));
  const ended = runningTask({ status: final === "done" ? "succeeded" : "failed" });

  act(() => streams()[0].emit(final, ended));

  expect([streams()[0].close.mock.calls.length, onEnd.mock.calls]).toEqual([1, [[ended]]]);
});

test("closes the stream when the screen goes away", () => {
  const { streams } = fakeEventSource();
  const { unmount } = renderHook(() => useTaskEvents(9, () => {}));

  unmount();

  expect(streams()[0].close).toHaveBeenCalledTimes(1);
});
