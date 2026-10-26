import { useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { useParams } from "react-router-dom";

import { getCut, previewCut, showSermon, type ApiError } from "../../api/client";
import type { Cut, CutPreview as Sequence, SermonShown } from "../../api/types";
import { useResource } from "../../api/useResource";
import { CaptionOverlay } from "./CaptionOverlay";
import { CaptionTab } from "./CaptionTab";
import { captionBlocks, timedWords, type TimedWord } from "./captions";
import { CutPreview, type CutPreviewHandle } from "./CutPreview";
import { CutSide, type Tab } from "./CutSide";
import { CutTimeline } from "./CutTimeline";
import { CutTransport } from "./CutTransport";
import { ExportButton } from "./ExportButton";
import { TextTab } from "./TextTab";
import { useCaptionStyle } from "./useCaptionStyle";
import { useWordFixes } from "./useWordFixes";
import { WordEditor } from "./WordEditor";

interface Loaded {
  cut: Cut;
  sequence: Sequence;
  sermon: SermonShown;
}

async function loadCut(id: number): Promise<Loaded> {
  const [cut, sequence] = await Promise.all([getCut(id), previewCut(id)]);
  return { cut, sequence, sermon: await showSermon(cut.sermon_id) };
}

/** Level 3: the 9:16 preview of one cut, its timeline and the Texto and Legenda tabs. */
export function CutPage() {
  const id = Number(useParams().id);
  const loaded = useResource(() => loadCut(id), `cut:${id}`);

  if (loaded.error) {
    return (
      <Note>
        {loaded.error.code === "not_found" ? "Corte não encontrado." : loaded.error.message}
      </Note>
    );
  }
  if (!loaded.data) {
    return null;
  }
  const { cut, sequence, sermon } = loaded.data;
  if (sermon.sermon_start === null) {
    return <Note>A prévia do corte precisa da pregação processada.</Note>;
  }
  return <CutLevel key={cut.id} cut={cut} sequence={sequence} sermonStart={sermon.sermon_start} />;
}

function Note({ children }: { children: string }) {
  return (
    <main className="l1">
      <div className="l1-wrap">
        <p className="note">{children}</p>
      </div>
    </main>
  );
}

interface CutLevelProps {
  cut: Cut;
  sequence: Sequence;
  /** Where the processed video starts in the live. */
  sermonStart: number;
}

function CutLevel({ cut, sequence, sermonStart }: CutLevelProps) {
  const preview = useRef<CutPreviewHandle>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [tab, setTab] = useState<Tab>("text");
  const [savedAt, setSavedAt] = useState(0);
  const markSaved = () => setSavedAt(Date.now());
  const caption = useCaptionStyle(cut.id, cut.caption, markSaved);
  const fixes = useWordFixes(cut.id, cut.words, markSaved);
  const [editing, setEditing] = useState<TimedWord>();
  const [fixError, setFixError] = useState<string>();
  const fixed = useMemo(() => ({ ...cut, words: fixes.words }), [cut, fixes.words]);
  const size = caption.style.size;
  const blocks = useMemo(() => captionBlocks(timedWords(fixed), size), [fixed, size]);

  function toggle() {
    if (playing) {
      preview.current?.pause();
    } else {
      preview.current?.play();
    }
    setPlaying(!playing);
  }

  function edit(word: TimedWord) {
    preview.current?.pause();
    setPlaying(false);
    setFixError(undefined);
    setEditing(word);
  }

  async function saveWord(word: TimedWord, text: string): Promise<boolean> {
    const error = await fixes.fix(word.word_id, text);
    setFixError(error && refusal(error, word));
    return !error;
  }

  function closeEditor() {
    setEditing(undefined);
    setFixError(undefined);
  }

  // docs/prototype/wordcut.html setLegendTab: the caption layer opens Legenda; any other area
  // closes it, except the panel itself and the caption's words being fixed.
  function followClick(event: ReactPointerEvent) {
    const target = event.target as Element;
    if (target.closest("[data-legend]")) {
      setTab("caption");
    } else if (!target.closest(".side, .caption .cw, .cw-in")) {
      setTab("text");
    }
  }

  return (
    <div className="l3" onPointerDown={followClick}>
      <CutSide tab={tab} onTab={setTab} savedAt={savedAt}>
        {tab === "text" ? (
          <TextTab cut={fixed} />
        ) : (
          <CaptionTab
            caption={caption}
            words={fixes.words}
            onUndo={(word) => fixes.fix(word.word_id, word.text)}
          />
        )}
      </CutSide>
      <main className="work">
        <div className="l2-bar">
          <span className="spacer" />
          <ExportButton
            cut={cut}
            captionOn={caption.style.enabled}
            saving={caption.saving || fixes.saving}
            onCaptionSaved={(enabled) => caption.adopt({ enabled })}
          />
        </div>
        <CutPreview
          ref={preview}
          sermonId={cut.sermon_id}
          sermonStart={sermonStart}
          segments={sequence.segments}
          onTime={setCursor}
          onEnd={() => setPlaying(false)}
        >
          <CaptionOverlay
            blocks={blocks}
            style={caption.style}
            cursor={cursor}
            onEdit={edit}
            editing={
              editing && {
                wordId: editing.word_id,
                field: (
                  <WordEditor
                    word={editing}
                    onSave={(text) => saveWord(editing, text)}
                    onClose={closeEditor}
                  />
                ),
              }
            }
            error={fixError}
          />
        </CutPreview>
        <CutTransport
          playing={playing}
          onToggle={toggle}
          cursor={cursor}
          duration={sequence.duration}
        />
        <CutTimeline
          segments={sequence.segments}
          duration={sequence.duration}
          cursor={cursor}
          onSeek={(cutSeconds) => preview.current?.seek(cutSeconds)}
          blocks={blocks}
          captionOn={caption.style.enabled}
          legendOpen={tab === "caption"}
        />
      </main>
    </div>
  );
}

/** What the caption says when the API refuses a fix. It never repeats the typed text
 * (ADR-0015). */
function refusal(error: ApiError, word: TimedWord): string {
  return error.code === "spelling_too_different"
    ? `Bloqueado: não é uma correção de grafia de “${word.original}” e mudaria o que foi dito. Só o administrador altera o conteúdo.`
    : error.message;
}
