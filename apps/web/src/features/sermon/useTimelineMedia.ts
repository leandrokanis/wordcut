import { useEffect, useState } from "react";

import {
  getThumbnailsLayout,
  getWaveform,
  prepareSermon,
  thumbnailsUrl,
  type ApiError,
} from "../../api/client";
import type { SermonShown, TimelineState } from "../../api/types";
import { useTaskEvents } from "./useTaskEvents";

export interface TimelineMedia {
  /** ``pending`` too while a preparation launched here runs. */
  status: TimelineState["status"];
  /** The strip of thumbnails, once prepared and when the live has storyboards. */
  thumbnails?: string;
  /** The peaks of the whole live, once prepared. */
  peaks?: number[];
  /** Why the API refused the last "Tentar de novo". */
  refusal?: ApiError;
  /** Prepares the thumbnails and the waveform again. */
  retry(): void;
}

interface Loaded {
  version: number;
  thumbnails?: string;
  peaks?: number[];
}

/** The thumbnails and the waveform of ``sermon``'s timeline: loaded once ready, followed by
 * the events of its ``prepare`` task while it runs, and ``onPrepared`` told when it ends. */
export function useTimelineMedia(
  sermon: SermonShown | undefined,
  onPrepared: () => void,
): TimelineMedia {
  const [launched, setLaunched] = useState<number>();
  const [ended, setEnded] = useState<number>();
  const [refusal, setRefusal] = useState<ApiError>();
  const [loaded, setLoaded] = useState<Loaded>({ version: 0 });
  const timeline = sermon?.timeline;
  const running = timeline?.status === "pending" ? (timeline.task_id ?? undefined) : undefined;
  const taskId = launched ?? (running !== ended ? running : undefined);
  useTaskEvents(taskId, (task) => {
    setLaunched(undefined);
    setEnded(task.id);
    onPrepared();
  });
  const status = taskId !== undefined ? "pending" : (timeline?.status ?? "pending");
  const sermonId = sermon?.id;

  useEffect(() => {
    if (sermonId === undefined || status !== "ready") {
      return;
    }
    let current = true;
    // A live without storyboards has no thumbnails: their 404 only leaves the track plain.
    Promise.all([
      getThumbnailsLayout(sermonId).catch(() => undefined),
      getWaveform(sermonId).catch(() => undefined),
    ]).then(([layout, waveform]) => {
      if (!current) {
        return;
      }
      setLoaded(({ version }) => ({
        version: version + 1,
        thumbnails: layout && thumbnailsUrl(sermonId, version + 1),
        peaks: waveform?.peaks,
      }));
    });
    return () => {
      current = false;
    };
  }, [sermonId, status]);

  function retry() {
    if (sermonId === undefined) {
      return;
    }
    setRefusal(undefined);
    prepareSermon(sermonId).then(
      (task) => setLaunched(task.task_id),
      (error: ApiError) => setRefusal(error),
    );
  }

  return { status, thumbnails: loaded.thumbnails, peaks: loaded.peaks, refusal, retry };
}
