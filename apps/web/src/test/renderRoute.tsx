import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../app/routes";
import { PlayerFactoryContext, type PlayerFactory } from "../features/sermon/Player";
import { fakePlayers } from "./fakePlayers";

/** Renders the application's own route table at ``path``, with doubles of the players. */
export function renderRoute(path: string, players: PlayerFactory = fakePlayers()) {
  return render(
    <PlayerFactoryContext.Provider value={players}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </PlayerFactoryContext.Provider>,
  );
}
