import { vi } from "vitest";

/** A double of the browser's ``EventSource``: the test emits the server's events. */
export class FakeEventSource {
  static instances: FakeEventSource[] = [];

  readonly url: string;
  readonly close = vi.fn();
  private readonly listeners = new Map<string, Set<(event: MessageEvent) => void>>();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    const listeners = this.listeners.get(type) ?? new Set();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.get(type)?.delete(listener);
  }

  /** Delivers an event as the API sends it: ``data`` is the task, as JSON (docs/api.md §3). */
  emit(type: string, data: unknown) {
    const event = new MessageEvent(type, { data: JSON.stringify(data) });
    this.listeners.get(type)?.forEach((listener) => listener(event));
  }
}

/** Replaces ``EventSource``; ``streams()`` lists the ones the code opened, oldest first. */
export function fakeEventSource(): { streams: () => FakeEventSource[] } {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  return { streams: () => FakeEventSource.instances };
}
