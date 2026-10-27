import { useEffect, useRef, type RefObject } from "react";

/** Closes an open menu on Escape or on a press outside ``area``, as the prototype's menus do. */
export function useDismiss(
  area: RefObject<HTMLElement>,
  open: boolean,
  close: () => void,
) {
  const latestClose = useRef(close);
  latestClose.current = close;

  useEffect(() => {
    if (!open) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        latestClose.current();
      }
    }
    function onPointerDown(event: PointerEvent) {
      if (!area.current?.contains(event.target as Node)) {
        latestClose.current();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [area, open]);
}
