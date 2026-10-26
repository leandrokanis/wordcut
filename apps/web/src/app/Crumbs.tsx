import { Fragment } from "react";
import { Link } from "react-router-dom";

import type { Trail } from "./trail";

interface Crumb {
  label: string;
  to?: string;
}

const PENDING = "…";

export function Crumbs({ trail }: { trail: Trail }) {
  const crumbs = crumbsOf(trail);
  return (
    <nav className="crumbs" aria-label="Caminho">
      {crumbs.map((crumb, index) => (
        <Fragment key={index}>
          {index > 0 && <span className="crsep">/</span>}
          {index === crumbs.length - 1 ? (
            <span className="cr cur" aria-current="page">
              {crumb.label}
            </span>
          ) : crumb.to ? (
            <Link className="cr" to={crumb.to}>
              {crumb.label}
            </Link>
          ) : (
            <span className="cr">{crumb.label}</span>
          )}
        </Fragment>
      ))}
    </nav>
  );
}

function crumbsOf({ level, sermon, cut }: Trail): Crumb[] {
  const crumbs: Crumb[] = [{ label: "Pregações", to: "/" }];
  if (level !== "sermons") {
    crumbs.push({
      label: sermon?.title ?? PENDING,
      to: sermon && `/sermons/${sermon.id}`,
    });
  }
  if (level === "cut") {
    crumbs.push({ label: cut?.title ?? PENDING });
  }
  return crumbs;
}
