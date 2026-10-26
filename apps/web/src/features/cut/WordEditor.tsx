import { useLayoutEffect, useRef, type KeyboardEvent } from "react";

import type { TimedWord } from "./captions";

interface WordEditorProps {
  word: TimedWord;
  /** Saves ``text``; answers whether the API accepted it. */
  onSave: (text: string) => Promise<boolean>;
  onClose: () => void;
}

/** The field that replaces a caption word to fix its spelling: Enter or leaving it saves, Esc
 * cancels. A refused text keeps the field open, so the user corrects it or cancels. */
export function WordEditor({ word, onSave, onClose }: WordEditorProps) {
  const field = useRef<HTMLInputElement>(null);
  const saving = useRef(false);
  const closed = useRef(false);
  const refused = useRef<string>();

  useLayoutEffect(() => {
    field.current?.focus();
    field.current?.select();
  }, []);

  function close() {
    closed.current = true;
    onClose();
  }

  async function commit() {
    const text = (field.current?.value ?? "").trim();
    // A blur may follow Enter while its PUT is on the way: it must not send the text again.
    if (closed.current || saving.current || text === refused.current) {
      return;
    }
    if (text === word.text) {
      close();
      return;
    }
    saving.current = true;
    const accepted = await onSave(text);
    saving.current = false;
    if (accepted) {
      close();
    } else {
      refused.current = text;
      field.current?.select();
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      void commit();
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close();
    }
  }

  return (
    <input
      ref={field}
      className="cw-in"
      defaultValue={word.text}
      size={Math.max(2, word.text.length)}
      spellCheck={false}
      aria-label={`Corrigir “${word.original}”`}
      onKeyDown={onKeyDown}
      onBlur={() => void commit()}
      onInput={(event) => {
        event.currentTarget.size = Math.max(2, event.currentTarget.value.length);
      }}
    />
  );
}
