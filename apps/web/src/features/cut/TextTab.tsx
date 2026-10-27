import type { Cut, CutWord, RangeSentence } from "../../api/types";
import { formatDuration } from "../../ui/format";
import { wordsOf } from "./captions";
import { offsetOf } from "./sequence";

/** What the administrator does with the sentences of the cut's range. */
export interface SentenceChoice {
  onToggle: (sentenceId: number) => void;
  /** The boxes take no click: a choice is being saved or the sermon is processing. */
  disabled: boolean;
  /** Why the last choice was not saved. */
  error?: string;
}

interface TextTabProps {
  cut: Pick<Cut, "segments" | "words" | "range_sentences">;
  /** Only for the administrator, who changes what the cut plays. */
  choice?: SentenceChoice;
}

/** The administrator sees each sentence of the cut's range with a box to play it or leave
 * it out (docs/prototype/wordcut.html ``tabTexto``); anyone else, the cut's assembled text,
 * one row per segment with where it starts in the cut. The words show the cut's spelling
 * fixes. */
export function TextTab({ cut, choice }: TextTabProps) {
  return choice ? (
    <SentenceList sentences={cut.range_sentences} words={cut.words} choice={choice} />
  ) : (
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

interface SentenceListProps {
  sentences: RangeSentence[];
  words: CutWord[];
  choice: SentenceChoice;
}

function SentenceList({ sentences, words, choice }: SentenceListProps) {
  return (
    <div className="sents choose">
      {sentences.map((sentence, index) => (
        <label key={sentence.id} className={`sent ${sentence.included === "none" ? "out" : "in"}`}>
          <input
            type="checkbox"
            checked={sentence.included === "all"}
            aria-checked={sentence.included === "part" ? "mixed" : sentence.included === "all"}
            ref={(box) => {
              if (box) {
                box.indeterminate = sentence.included === "part";
              }
            }}
            disabled={choice.disabled}
            aria-label={`Incluir frase ${index + 1}: ${sentence.text}`}
            onChange={() => choice.onToggle(sentence.id)}
          />
          <span className="tm">{formatDuration(sentence.start)}</span>
          <span>{spelled(sentence, words)}</span>
        </label>
      ))}
      {choice.error && (
        <p className="ferr" role="alert">
          {choice.error}
        </p>
      )}
    </div>
  );
}

/** The sentence with the spelling of the cut's words as they are now, fixed or undone since
 * the cut was loaded. Its words are placed by ID, so only when the IDs of the sentence run
 * one per word of its text; otherwise as the API gave it. */
function spelled(sentence: RangeSentence, words: CutWord[]): string {
  const tokens = sentence.text.split(" ");
  if (tokens.length !== sentence.last_word - sentence.first_word + 1) {
    return sentence.text;
  }
  const range = { from_word: sentence.first_word, to_word: sentence.last_word };
  for (const word of wordsOf(words, range)) {
    tokens[word.word_id - sentence.first_word] = word.corrected ?? word.text;
  }
  return tokens.join(" ");
}
