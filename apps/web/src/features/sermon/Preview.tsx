import {
  forwardRef,
  useContext,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import { sermonVideoUrl } from "../../api/client";
import type { SermonShown } from "../../api/types";
import { PlayerFactoryContext, type PlayerLike } from "./Player";

type Source = "youtube" | "video";

/** What the screen does with the preview, in seconds of the live. */
export interface PreviewHandle {
  seek(liveSeconds: number): void;
  play(): void;
  pause(): void;
}

interface PreviewProps {
  sermon: SermonShown;
  onTime: (liveSeconds: number) => void;
}

/** The 16:9 preview: the processed video inside the processed stretch, the live on YouTube
 * outside it or before processing. */
export const Preview = forwardRef<PreviewHandle, PreviewProps>(function Preview(
  { sermon, onTime },
  ref,
) {
  const players = useContext(PlayerFactoryContext);
  const processed = processedStretch(sermon);
  const resumeAt = useRef(processed?.[0] ?? sermon.live_start ?? 0);
  const [source, setSource] = useState<Source>(() => sourceAt(processed, resumeAt.current));
  const player = useRef<PlayerLike>();
  const host = useRef<HTMLDivElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const tell = useRef(onTime);
  tell.current = onTime;
  const offset = processed?.[0] ?? 0;
  const processedStart = processed?.[0];
  const processedEnd = processed?.[1];

  // Made with the layout, so the screen never shows a preview whose player does not exist yet.
  useLayoutEffect(() => {
    const start = resumeAt.current;
    const created =
      source === "video" && video.current
        ? players.video(video.current, offset)
        : host.current
          ? players.youtube(host.current, sermon.youtube_id, start)
          : undefined;
    if (!created) {
      return;
    }
    if (source === "video") {
      created.seek(start);
    }
    player.current = created;
    tell.current(start);
    const stopListening = created.onTime((liveSeconds) => {
      resumeAt.current = liveSeconds;
      tell.current(liveSeconds);
    });
    return () => {
      stopListening();
      created.destroy();
      player.current = undefined;
    };
  }, [players, source, offset, sermon.youtube_id]);

  useImperativeHandle(
    ref,
    () => ({
      seek(liveSeconds) {
        resumeAt.current = liveSeconds;
        tell.current(liveSeconds);
        const stretch: [number, number] | null =
          processedStart === undefined || processedEnd === undefined
            ? null
            : [processedStart, processedEnd];
        const wanted = sourceAt(stretch, liveSeconds);
        if (wanted === source) {
          player.current?.seek(liveSeconds);
        } else {
          setSource(wanted);
        }
      },
      play: () => player.current?.play(),
      pause: () => player.current?.pause(),
    }),
    [source, processedStart, processedEnd],
  );

  return (
    <div className="stage">
      <div className="vp">
        {source === "video" ? (
          <video
            className="frame h"
            ref={video}
            src={sermonVideoUrl(sermon.id)}
            aria-label="Prévia da pregação processada"
            preload="metadata"
            playsInline
          />
        ) : (
          <div className="frame h" ref={host} />
        )}
      </div>
    </div>
  );
});

/** Where the processed video lies in the live, once there is one. */
function processedStretch(sermon: SermonShown): [number, number] | null {
  return sermon.status === "processed" && sermon.sermon_start != null && sermon.sermon_end != null
    ? [sermon.sermon_start, sermon.sermon_end]
    : null;
}

function sourceAt(processed: [number, number] | null, liveSeconds: number): Source {
  return processed && liveSeconds >= processed[0] && liveSeconds <= processed[1]
    ? "video"
    : "youtube";
}
