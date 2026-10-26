import { useMatch } from "react-router-dom";

import { getCut, getSermon, type ApiError } from "../api/client";
import type { Cut, Sermon } from "../api/types";
import { useResource } from "../api/useResource";

export type Level = "sermons" | "sermon" | "cut";

/** Where the user is in the three levels, with the titles the path shows. */
export interface Trail {
  level: Level;
  sermon?: Sermon;
  cut?: Cut;
  error?: ApiError;
}

export function useTrail(): Trail {
  const sermonId = useMatch("/sermons/:id")?.params.id;
  const cutId = useMatch("/cuts/:id")?.params.id;
  const level: Level = cutId ? "cut" : sermonId ? "sermon" : "sermons";
  const { data, error } = useResource(
    () => loadTitles(Number(sermonId), Number(cutId)),
    `${level}:${cutId ?? sermonId ?? ""}`,
  );
  return { level, ...data, error };
}

async function loadTitles(
  sermonId: number,
  cutId: number,
): Promise<{ sermon?: Sermon; cut?: Cut }> {
  if (cutId) {
    const cut = await getCut(cutId);
    return { cut, sermon: await getSermon(cut.sermon_id) };
  }
  if (sermonId) {
    return { sermon: await getSermon(sermonId) };
  }
  return {};
}
