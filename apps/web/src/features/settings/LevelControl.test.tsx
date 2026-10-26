import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { Level } from "../../api/types";
import { criteria } from "../../test/fixtures";
import { LevelControl } from "./LevelControl";

const [triumphalism] = criteria();

const LEVELS: [string, Level, Level][] = [
  ["Brando", "lenient", "strict"],
  ["Moderado", "moderate", "lenient"],
  ["Rigoroso", "strict", "moderate"],
];

test.each(LEVELS)("presses %s for the level %s", (label, level) => {
  render(<LevelControl criterion={triumphalism} value={level} onPick={() => {}} />);

  const group = screen.getByRole("group", { name: "Rigidez: Triunfalismo" });
  const pressed = [...group.querySelectorAll("[aria-pressed=true]")].map((b) => b.textContent);
  expect(pressed).toEqual([label]);
});

test.each(LEVELS)("picks %s as %s", async (label, level, from) => {
  const onPick = vi.fn();
  render(<LevelControl criterion={triumphalism} value={from} onPick={onPick} />);

  await userEvent.click(screen.getByRole("button", { name: label }));

  expect(onPick.mock.calls).toEqual([[level]]);
});
