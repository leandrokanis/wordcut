import { useEffect, useRef, useState } from "react";

import { patchCaption, resetCaption, type ApiError } from "../../api/client";
import type { CaptionStyle } from "../../api/types";

// Requisitos gerais de interface: a change saves by itself, once the user pauses on it.
const AUTOSAVE_MS = 400;

export type CaptionField = keyof CaptionStyle;

export interface CaptionStyleState {
  /** The saved style with the changes still waiting to be saved. */
  style: CaptionStyle;
  /** Why the API refused a field's last change, by field. */
  errors: Partial<Record<CaptionField, string>>;
  /** Why restoring the church's style failed. */
  resetError?: string;
  /** A change is waiting to be saved or being saved. */
  saving: boolean;
  change<F extends CaptionField>(field: F, value: CaptionStyle[F]): void;
  reset(): void;
  /** Takes ``fields`` as saved: another call of the API already saved them. */
  adopt(fields: Partial<CaptionStyle>): void;
}

/** The cut's caption style, saved field by field ``AUTOSAVE_MS`` after its last change with
 * ``PATCH /api/cuts/{id}/caption``; the API's answer, the whole style, becomes the saved one. */
export function useCaptionStyle(
  cutId: number,
  initial: CaptionStyle,
  onSaved: () => void,
): CaptionStyleState {
  const [saved, setSaved] = useState(initial);
  const [drafts, setDrafts] = useState<Partial<CaptionStyle>>({});
  const [errors, setErrors] = useState<CaptionStyleState["errors"]>({});
  const [resetError, setResetError] = useState<string>();
  const [resetting, setResetting] = useState(false);
  const timers = useRef(new Map<CaptionField, ReturnType<typeof setTimeout>>());
  const generation = useRef(0);
  const tellSaved = useRef(onSaved);
  tellSaved.current = onSaved;

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((timer) => clearTimeout(timer));
  }, []);

  /** Drops the field's draft unless the user changed it again while it was being saved. */
  function dropDraft(field: CaptionField, value: unknown) {
    setDrafts((current) => (current[field] === value ? without(current, field) : current));
  }

  function save<F extends CaptionField>(field: F, value: CaptionStyle[F]) {
    timers.current.delete(field);
    const started = generation.current;
    patchCaption(cutId, { [field]: value }).then(
      (style) => {
        if (started !== generation.current) {
          return;
        }
        setSaved(style);
        dropDraft(field, value);
        tellSaved.current();
      },
      (error: ApiError) => {
        if (started !== generation.current) {
          return;
        }
        dropDraft(field, value);
        setErrors((current) => ({ ...current, [field]: error.message }));
      },
    );
  }

  function change<F extends CaptionField>(field: F, value: CaptionStyle[F]) {
    setDrafts((current) => ({ ...current, [field]: value }));
    setErrors((current) => without(current, field));
    clearTimeout(timers.current.get(field));
    timers.current.set(
      field,
      setTimeout(() => save(field, value), AUTOSAVE_MS),
    );
  }

  function reset() {
    timers.current.forEach((timer) => clearTimeout(timer));
    timers.current.clear();
    generation.current += 1;
    setDrafts({});
    setErrors({});
    setResetError(undefined);
    setResetting(true);
    resetCaption(cutId)
      .then(
        (style) => {
          setSaved(style);
          tellSaved.current();
        },
        (error: ApiError) => setResetError(error.message),
      )
      .finally(() => setResetting(false));
  }

  function adopt(fields: Partial<CaptionStyle>) {
    setSaved((current) => ({ ...current, ...fields }));
  }

  return {
    style: { ...saved, ...drafts },
    errors,
    resetError,
    saving: resetting || Object.keys(drafts).length > 0,
    change,
    reset,
    adopt,
  };
}

function without<T extends object>(record: T, key: keyof T): T {
  return Object.fromEntries(Object.entries(record).filter(([name]) => name !== key)) as T;
}
