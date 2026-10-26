import { Link, Outlet } from "react-router-dom";

import { GearIcon } from "../ui/icons";

import { Crumbs } from "./Crumbs";
import { useMe } from "./Identity";
import { useTrail } from "./trail";

/** The three levels: the path on top and the level's screen below. */
export function Layout() {
  const trail = useTrail();
  const { role } = useMe();
  return (
    <div className="levels">
      <header className="top">
        <div className="brand">
          <b />
          Wordcut
        </div>
        <Crumbs trail={trail} />
        <span className="spacer" />
        {role === "admin" && (
          <Link className="ibtn" to="/settings" aria-label="Configurações" title="Configurações">
            <GearIcon />
          </Link>
        )}
      </header>
      <Outlet context={trail} />
    </div>
  );
}
