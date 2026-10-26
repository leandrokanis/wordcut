import { Fragment, type CSSProperties, type ReactNode } from "react";

import type { CaptionStyle } from "../../api/types";
import { blockAt, captionCss, currentWord, type CaptionBlock, type TimedWord } from "./captions";

interface CaptionOverlayProps {
  blocks: CaptionBlock[];
  style: CaptionStyle;
  /** The player's position, in seconds of the cut. */
  cursor: number;
  /** A double click on a word asks to fix its spelling. */
  onEdit: (word: TimedWord) => void;
  /** The word being fixed and the field that replaces it. */
  editing?: { wordId: number; field: ReactNode };
  /** Why the API refused the fix, shown by the caption. */
  error?: string;
}

/** The caption over the 9:16 preview, drawn by the browser with the cut's style: an
 * approximation of the render, which the export gives (FR-002). Nothing is drawn while the
 * caption is off or between blocks. */
export function CaptionOverlay({
  blocks,
  style,
  cursor,
  onEdit,
  editing,
  error,
}: CaptionOverlayProps) {
  const block = style.enabled ? blockAt(blocks, cursor) : undefined;
  if (!block) {
    return null;
  }
  const now = currentWord(block.words, cursor);
  return (
    <>
      <div
        className="caption"
        role="group"
        aria-label="Legenda na prévia"
        style={captionCss(style) as CSSProperties}
      >
        {block.words.map((word, index) => (
          <Fragment key={word.word_id}>
            {index > 0 && " "}
            {editing?.wordId === word.word_id ? (
              editing.field
            ) : (
              <span
                className="cw"
                aria-current={word === now ? "true" : undefined}
                title="Clique duas vezes para corrigir"
                onDoubleClick={(event) => {
                  event.preventDefault();
                  onEdit(word);
                }}
              >
                {word.text}
              </span>
            )}
          </Fragment>
        ))}
      </div>
      {error && (
        <p className="cap-err" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
