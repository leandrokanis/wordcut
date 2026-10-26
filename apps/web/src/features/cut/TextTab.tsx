import type { Cut } from "../../api/types";
import { formatDuration } from "../../ui/format";
import { wordsOf } from "./captions";
import { offsetOf } from "./sequence";

/** The cut's assembled text, one row per segment with where it starts in the cut; the
 * words show the cut's spelling fixes. */
export function TextTab({ cut }: { cut: Pick<Cut, "segments" | "words"> }) {
  return (
    <div className="sents">
      {cut.segments.map((segment, index) => (
        <p key={index} className="sent in">
          <span className="tm">{formatDuration(offsetOf(cut.segments, index))}</span>
          <span>
            {wordsOf(cut.words, segment)
              .map((word) => word.corrected ?? word.text)
              .join(" ")}
          </span>
        </p>
      ))}
    </div>
  );
}
