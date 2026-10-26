import "@testing-library/jest-dom/vitest";

// jsdom has no PointerEvent; without it, fireEvent.pointer* drops clientX.
if (typeof window.PointerEvent === "undefined") {
  window.PointerEvent = class PointerEvent extends MouseEvent {} as typeof window.PointerEvent;
}

// jsdom has no IntersectionObserver; an inert one lets the screens that watch the scroll render.
// A test that drives it uses fakeIntersectionObserver.
if (typeof window.IntersectionObserver === "undefined") {
  window.IntersectionObserver = class IntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [];
    }
  } as unknown as typeof window.IntersectionObserver;
}
