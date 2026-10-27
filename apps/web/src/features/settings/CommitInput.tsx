import { useRef, useState, type InputHTMLAttributes } from "react";

import type { ApiError } from "../../api/client";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> & {
  id: string;
  /** The saved text. */
  value: string;
  /** Saves ``text``; a rejection with the API's error shows its message below the field. */
  save: (text: string) => Promise<unknown>;
};

/** A text the API validates: saved with Enter or on leaving the field, only when it changed. */
export function CommitInput({ id, value, save, className = "input", ...rest }: Props) {
  const [draft, setDraft] = useState(value);
  const [shown, setShown] = useState(value);
  const [error, setError] = useState<string>();
  const tried = useRef<string>();

  // Adjusted while rendering, not in an effect: an effect runs after paint and could
  // overwrite what the user already typed into the freshly mounted field.
  if (value !== shown) {
    setShown(value);
    setDraft(value);
  }

  function commit() {
    // The text the API refused is not sent again until it changes.
    if (draft === value || draft === tried.current) {
      return;
    }
    tried.current = draft;
    setError(undefined);
    save(draft).then(
      () => (tried.current = undefined),
      (refusal: ApiError) => setError(refusal.message),
    );
  }

  const errorId = `${id}-error`;
  return (
    <div className="field">
      <input
        {...rest}
        id={id}
        className={className}
        value={draft}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commit();
          }
        }}
      />
      {error && (
        <p className="ferr" id={errorId} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
