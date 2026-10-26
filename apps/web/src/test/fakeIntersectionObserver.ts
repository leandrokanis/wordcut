import { vi } from "vitest";

export interface FakeObserver {
  readonly options?: IntersectionObserverInit;
  readonly observed: Set<Element>;
  disconnected: boolean;
}

export interface FakeIntersection {
  readonly observers: FakeObserver[];
  /** Tells every live observer of ``target`` that it entered or left its area. */
  intersect(target: Element, isIntersecting: boolean): void;
}

/** Replaces ``IntersectionObserver``, which jsdom lacks, with a double the test drives. */
export function fakeIntersectionObserver(): FakeIntersection {
  const observers: (FakeObserver & { callback: IntersectionObserverCallback })[] = [];

  class Double {
    readonly observed = new Set<Element>();
    disconnected = false;

    constructor(
      readonly callback: IntersectionObserverCallback,
      readonly options?: IntersectionObserverInit,
    ) {
      observers.push(this);
    }

    observe(target: Element) {
      this.observed.add(target);
    }

    unobserve(target: Element) {
      this.observed.delete(target);
    }

    disconnect() {
      this.disconnected = true;
      this.observed.clear();
    }

    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  }

  vi.stubGlobal("IntersectionObserver", Double);
  return {
    observers,
    intersect(target, isIntersecting) {
      for (const observer of observers) {
        if (!observer.disconnected && observer.observed.has(target)) {
          const entry = { target, isIntersecting } as IntersectionObserverEntry;
          observer.callback([entry], observer as unknown as IntersectionObserver);
        }
      }
    },
  };
}
