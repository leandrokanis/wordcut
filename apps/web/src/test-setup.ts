import "@testing-library/jest-dom/vitest";

// jsdom has no PointerEvent; without it, fireEvent.pointer* drops clientX.
if (typeof window.PointerEvent === "undefined") {
  window.PointerEvent = class PointerEvent extends MouseEvent {} as typeof window.PointerEvent;
}
