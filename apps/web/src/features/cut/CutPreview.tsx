import {
  forwardRef,
  useContext,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  type ReactNode,
} from "react";

import { sermonVideoUrl } from "../../api/client";
import { PlayerFactoryContext, type PlayerLike } from "../sermon/Player";
import { cutTimeOf, next, pointAt, toLive, toSermon, type Span } from "./sequence";

/** What the cut's screen does with the preview, in seconds of the cut. */
export interface CutPreviewHandle {
  play(): void;
  pause(): void;
  seek(cutSeconds: number): void;
}

interface CutPreviewProps {
  sermonId: number;
  /** Where the processed video starts in the live. */
  sermonStart: number;
  /** The segments in the order the cut plays them, in sermon time. */
  segments: Span[];
  onTime: (cutSeconds: number) => void;
  /** The last segment ended and the preview paused. */
  onEnd: () => void;
  children?: ReactNode;
}

/** The 9:16 preview without rendering: the sermon's processed video, cropped at the centre of
 * the vertical frame, jumping from segment to segment. The level 3 never loads YouTube
 * (ADR-0023). */
export const CutPreview = forwardRef<CutPreviewHandle, CutPreviewProps>(function CutPreview(
  { sermonId, sermonStart, segments, onTime, onEnd, children },
  ref,
) {
  const players = useContext(PlayerFactoryContext);
  const video = useRef<HTMLVideoElement>(null);
  const player = useRef<PlayerLike>();
  const index = useRef(0);
  const ended = useRef(false);
  const tell = useRef(onTime);
  tell.current = onTime;
  const end = useRef(onEnd);
  end.current = onEnd;

  // Made with the layout, so the screen never shows a preview whose player does not exist yet.
  useLayoutEffect(() => {
    if (!video.current || segments.length === 0) {
      return;
    }
    const created = players.video(video.current, sermonStart);
    player.current = created;
    index.current = 0;
    ended.current = false;
    created.seek(toLive(sermonStart, segments[0].start));
    tell.current(0);
    const stopListening = created.onTime((liveSeconds) => {
      const t = toSermon(sermonStart, liveSeconds);
      const step = next(segments, index.current, t);
      if (step.kind === "seek") {
        index.current = step.index;
        created.seek(toLive(sermonStart, step.to));
        tell.current(cutTimeOf(segments, step.index, step.to));
      } else if (step.kind === "end") {
        created.pause();
        ended.current = true;
        tell.current(cutTimeOf(segments, index.current, t));
        end.current();
      } else {
        tell.current(cutTimeOf(segments, index.current, t));
      }
    });
    return () => {
      stopListening();
      created.destroy();
      player.current = undefined;
    };
  }, [players, sermonStart, segments]);

  useImperativeHandle(ref, () => {
    function seek(cutSeconds: number) {
      const point = pointAt(segments, cutSeconds);
      index.current = point.index;
      ended.current = false;
      player.current?.seek(toLive(sermonStart, point.t));
      tell.current(cutTimeOf(segments, point.index, point.t));
    }
    return {
      play() {
        if (ended.current) {
          seek(0);
        }
        player.current?.play();
      },
      pause: () => player.current?.pause(),
      seek,
    };
  }, [segments, sermonStart]);

  return (
    <div className="stage">
      <div className="vp">
        <div className="frame v">
          <video
            ref={video}
            src={sermonVideoUrl(sermonId)}
            aria-label="Prévia do corte"
            preload="metadata"
            playsInline
          />
          {children}
        </div>
      </div>
    </div>
  );
});
