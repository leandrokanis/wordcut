import { Outlet } from "react-router-dom";

import { MachineStatusProvider } from "../features/status/MachineStatus";
import { StatusBar } from "../features/status/StatusBar";
import { IdentityGate } from "./Identity";

/** Every screen: only for a team member, with the status bar in the footer. */
export function Shell() {
  return (
    <IdentityGate>
      <MachineStatusProvider>
        <div className="app">
          <Outlet />
          <StatusBar />
        </div>
      </MachineStatusProvider>
    </IdentityGate>
  );
}
