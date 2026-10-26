import { useOutletContext } from "react-router-dom";

import type { Trail } from "./trail";

/** The screen of a level that is not built yet, or why its sermon or cut is missing. */
export function LevelPlaceholder({ notFound }: { notFound: string }) {
  const { error } = useOutletContext<Trail>();
  const message = !error
    ? "Esta tela está em construção."
    : error.code === "not_found"
      ? notFound
      : error.message;
  return (
    <main className="l1">
      <div className="l1-wrap">
        <p className="note">{message}</p>
      </div>
    </main>
  );
}
