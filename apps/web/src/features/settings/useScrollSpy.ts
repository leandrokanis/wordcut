import { useEffect, useState, type RefObject } from "react";

// The reading band is the top third of the viewport: the section crossing it is the one read.
const READING_BAND = "0px 0px -66% 0px";

export interface ScrollSpy {
  /** The section the reader is on. */
  current?: string;
  /** Scrolls to the section ``id`` and makes it the current one. */
  jump(id: string): void;
}

/** Follows which of the sections ``ids`` (element ids, in page order) is being read: the first
 * one in the reading band, or the last one once ``bottom``, the end of the page, is in view. */
export function useScrollSpy(ids: string[], bottom: RefObject<Element>): ScrollSpy {
  const [current, setCurrent] = useState<string>();
  const key = ids.join(" ");

  useEffect(() => {
    const order = key.split(" ");
    const inBand = new Set<string>();
    let atBottom = false;

    function follow() {
      const read = atBottom ? order[order.length - 1] : order.find((id) => inBand.has(id));
      if (read) {
        setCurrent(read);
      }
    }

    const band = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            inBand.add(entry.target.id);
          } else {
            inBand.delete(entry.target.id);
          }
        }
        follow();
      },
      { rootMargin: READING_BAND },
    );
    for (const id of order) {
      const section = document.getElementById(id);
      if (section) {
        band.observe(section);
      }
    }
    const end = new IntersectionObserver((entries) => {
      atBottom = entries[entries.length - 1].isIntersecting;
      follow();
    });
    if (bottom.current) {
      end.observe(bottom.current);
    }
    return () => {
      band.disconnect();
      end.disconnect();
    };
  }, [key, bottom]);

  function jump(id: string) {
    setCurrent(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return { current, jump };
}
