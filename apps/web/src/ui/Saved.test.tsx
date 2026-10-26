import { act, render, screen } from "@testing-library/react";
import { afterEach } from "vitest";

import { Saved } from "./Saved";

afterEach(() => {
  vi.useRealTimers();
});

test("announces Salvo politely each time something is saved, then hides it", () => {
  vi.useFakeTimers();
  const { rerender } = render(<Saved savedAt={0} />);

  rerender(<Saved savedAt={1} />);
  const announced = screen.getByRole("status");
  const shown = [announced.textContent, announced.getAttribute("aria-live")];
  act(() => {
    vi.advanceTimersByTime(1500);
  });

  expect([...shown, announced.textContent]).toEqual(["Salvo", "polite", ""]);
});

test("stays quiet before anything is saved", () => {
  render(<Saved savedAt={0} />);

  expect(screen.getByRole("status")).toHaveTextContent("");
});
