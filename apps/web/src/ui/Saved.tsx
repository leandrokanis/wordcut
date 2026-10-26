import { useEffect, useState } from "react";

const SHOWN_MS = 1500;

/** Confirms an automatic save: show it again by changing ``savedAt``; 0 means never saved. */
export function Saved({ savedAt }: { savedAt: number }) {
  const [shownFor, setShownFor] = useState(0);

  useEffect(() => {
    if (!savedAt) {
      return;
    }
    setShownFor(savedAt);
    const timer = setTimeout(() => setShownFor(0), SHOWN_MS);
    return () => clearTimeout(timer);
  }, [savedAt]);

  const on = shownFor !== 0;
  return (
    <span className={on ? "saved on" : "saved"} role="status" aria-live="polite">
      {on ? "Salvo" : ""}
    </span>
  );
}
