import { useState } from "react";

import {
  createPreset,
  deletePreset,
  listCriteria,
  listPresets,
  patchPreset,
  setDefaultPreset,
  type ApiError,
} from "../../api/client";
import type { Criterion, Level, Preset, PresetChange, SecondsRange } from "../../api/types";
import { useResource } from "../../api/useResource";
import { Choice } from "../../ui/Choice";
import { FormRow } from "../../ui/FormRow";
import { LevelControl } from "./LevelControl";
import { Loading, Section } from "./Section";
import { CommitInput } from "./CommitInput";
import { AUTOSAVE_MS, usePresetDrafts } from "./usePresetDrafts";

// docs/prototype/wordcut.html SPAGES: the sections that show the chosen preset.
const PRESET_SECTIONS = [
  { id: "presets", title: "Presets" },
  { id: "filtros", title: "Filtros" },
  { id: "valor", title: "Valor" },
  { id: "formato", title: "Formato" },
];

type RangeField = "duration_allowed" | "duration_ideal";
type RangeDraft = Record<keyof SecondsRange, string>;

const WHOLE_SECONDS = /^\d+$/;

const SWITCH: [boolean, string][] = [
  [false, "Não"],
  [true, "Sim"],
];

/** Presets, Filtros, Valor and Formato under one picker of the preset they show. */
export function PresetSections({ onSaved }: { onSaved: () => void }) {
  const presets = useResource(listPresets, "presets");
  const criteria = useResource(listCriteria, "criteria");
  if (!presets.data || !criteria.data) {
    const error = presets.error ?? criteria.error;
    return (
      <div className="sgrp">
        {PRESET_SECTIONS.map((section) => (
          <Section key={section.id} id={section.id} title={section.title}>
            <Loading error={error} />
          </Section>
        ))}
      </div>
    );
  }
  return <PresetEditor initial={presets.data} criteria={criteria.data} onSaved={onSaved} />;
}

function PresetEditor({
  initial,
  criteria,
  onSaved,
}: {
  initial: Preset[];
  criteria: Criterion[];
  onSaved: () => void;
}) {
  const [presets, setPresets] = useState(initial);
  const [selectedId, setSelectedId] = useState(
    () => (initial.find((preset) => preset.is_default) ?? initial[0]).id,
  );
  const preset = presets.find((candidate) => candidate.id === selectedId) ?? presets[0];

  function replace(saved: Preset) {
    setPresets((current) =>
      current.map((candidate) => (candidate.id === saved.id ? saved : candidate)),
    );
  }

  async function save(id: number, change: PresetChange): Promise<Preset> {
    const saved = await patchPreset(id, change);
    replace(saved);
    onSaved();
    return saved;
  }

  const drafts = usePresetDrafts(save);
  const [actionError, setActionError] = useState<string>();

  /** Runs an action on the presets, with the waiting changes saved first. */
  async function runAction(action: () => Promise<void>) {
    setActionError(undefined);
    await drafts.flush();
    try {
      await action();
      onSaved();
    } catch (refusal) {
      setActionError((refusal as ApiError).message);
    }
  }

  function makeDefault() {
    return runAction(async () => {
      const chosen = await setDefaultPreset(preset.id);
      setPresets((current) =>
        current.map((candidate) =>
          candidate.id === chosen.id ? chosen : { ...candidate, is_default: false },
        ),
      );
    });
  }

  function remove() {
    return runAction(async () => {
      await deletePreset(preset.id);
      const left = presets.filter((candidate) => candidate.id !== preset.id);
      setPresets(left);
      setSelectedId((left.find((candidate) => candidate.is_default) ?? left[0]).id);
    });
  }

  function duplicate() {
    return runAction(async () => {
      const copy = await createPreset(`Cópia de ${preset.name}`, preset.id);
      setPresets((current) => [...current, copy]);
      setSelectedId(copy.id);
    });
  }

  function show(id: number) {
    void drafts.flush();
    setSelectedId(id);
  }

  /** The draft of ``key`` on the shown preset, or ``saved``. */
  function shown<T>(key: string, saved: T): T {
    return drafts.draft<T>(preset.id, key) ?? saved;
  }

  function refusal(key: string) {
    const message = drafts.error(preset.id, key);
    return (
      message && (
        <p className="ferr" role="alert">
          {message}
        </p>
      )
    );
  }

  function rangeRow(field: RangeField, label: string, description: string) {
    const saved = preset[field];
    const range = shown<RangeDraft>(field, { min: String(saved.min), max: String(saved.max) });

    function edit(end: keyof SecondsRange, text: string) {
      const next = { ...range, [end]: text };
      // A half-typed range is only shown; the API gets whole seconds at both ends.
      const whole = WHOLE_SECONDS.test(next.min) && WHOLE_SECONDS.test(next.max);
      const change = whole ? { [field]: { min: Number(next.min), max: Number(next.max) } } : undefined;
      drafts.change(preset.id, field, next, change, AUTOSAVE_MS);
    }

    return (
      <FormRow label={label} description={description}>
        <div className="field">
          <div className="ctl">
            {(["min", "max"] as const).map((end, index) => (
              <span className="ctl" key={end}>
                {index > 0 && <span className="unit">–</span>}
                <input
                  className="input mono num"
                  type="number"
                  min={1}
                  inputMode="numeric"
                  aria-label={`${label}, ${end === "min" ? "mínimo" : "máximo"}`}
                  value={range[end]}
                  onChange={(event) => edit(end, event.target.value)}
                />
              </span>
            ))}
            <span className="unit">s</span>
          </div>
          {refusal(field)}
        </div>
      </FormRow>
    );
  }

  function levelRow(criterion: Criterion) {
    const key = `levels.${criterion.id}`;
    return (
      <LevelControl
        key={criterion.id}
        criterion={criterion}
        value={
          drafts.draft<Level>(preset.id, key) ??
          preset.levels[criterion.id] ??
          criterion.default_level
        }
        onPick={(level) =>
          drafts.change(preset.id, key, level, { levels: { [criterion.id]: level } })
        }
      />
    );
  }

  return (
    <div className="sgrp">
      <div className="s-top">
        <label className="sl" htmlFor="preset-picker">
          Preset
        </label>
        <select
          className="input"
          id="preset-picker"
          value={preset.id}
          onChange={(event) => show(Number(event.target.value))}
        >
          {presets.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.is_default ? `${candidate.name} · padrão` : candidate.name}
            </option>
          ))}
        </select>
      </div>
      <Section id="presets" title="Presets">
        <div className="scard">
          <FormRow
            label="Nome"
            description="Como o preset aparece na lista e nas sugestões."
            controlId="preset-name"
          >
            <CommitInput
              key={preset.id}
              id="preset-name"
              value={preset.name}
              save={(name) => save(preset.id, { name })}
            />
          </FormRow>
          <FormRow label="Padrão" description="Usado na sugestão automática de cada pregação.">
            {preset.is_default ? (
              <span className="chip ok">Preset padrão</span>
            ) : (
              <button className="btn" type="button" onClick={makeDefault}>
                Tornar padrão
              </button>
            )}
          </FormRow>
          <FormRow label="Cópia e remoção" description="Duplicar cria um preset novo a partir deste.">
            <div className="field">
              <div className="ctl">
                <button className="btn" type="button" onClick={duplicate}>
                  Duplicar
                </button>
                <button
                  className="btn ghost danger"
                  type="button"
                  disabled={preset.is_default}
                  title={preset.is_default ? "O preset padrão não pode ser apagado" : undefined}
                  onClick={remove}
                >
                  Apagar
                </button>
              </div>
              {actionError && (
                <p className="ferr" role="alert">
                  {actionError}
                </p>
              )}
            </div>
          </FormRow>
        </div>
        <div className="scard">
          <FormRow
            label="Instruções adicionais"
            description="Texto livre acrescentado ao prompt, para orientar ou refinar as sugestões deste preset."
            controlId="preset-instructions"
            wide
          >
            <div className="field">
              <textarea
                className="input"
                id="preset-instructions"
                rows={6}
                value={shown("instructions", preset.instructions)}
                onChange={(event) => {
                  const instructions = event.target.value;
                  drafts.change(preset.id, "instructions", instructions, { instructions }, AUTOSAVE_MS);
                }}
              />
              {refusal("instructions")}
            </div>
          </FormRow>
        </div>
      </Section>
      <Section id="filtros" title="Filtros">
        <div className="scard">
          {criteria.filter((criterion) => criterion.type === "filter").map(levelRow)}
        </div>
      </Section>
      <Section id="valor" title="Valor">
        <div className="scard">
          {criteria.filter((criterion) => criterion.type === "value").map(levelRow)}
        </div>
      </Section>
      <Section id="formato" title="Formato">
        <div className="scard">
          {rangeRow("duration_allowed", "Duração final", "Depois da limpeza das hesitações.")}
          {rangeRow("duration_ideal", "Duração ideal", "Faixa que o modelo procura atingir.")}
          <FormRow label="Permitir reordenar" description="Ex.: gancho tirado da conclusão.">
            <div className="field">
              <Choice
                name="Permitir reordenar"
                options={SWITCH}
                value={shown("reorder", preset.reorder)}
                onPick={(reorder) => drafts.change(preset.id, "reorder", reorder, { reorder })}
              />
              {refusal("reorder")}
            </div>
          </FormRow>
          <FormRow
            label="Palavras protegidas"
            description="Nunca removidas ao limpar hesitações ou escolher frases. Separadas por vírgula."
            controlId="preset-protected"
          >
            <div className="field">
              <input
                className="input"
                id="preset-protected"
                value={shown("protected_words", preset.protected_words.join(", "))}
                onChange={(event) => {
                  const text = event.target.value;
                  const words = text
                    .split(",")
                    .map((word) => word.trim())
                    .filter(Boolean);
                  drafts.change(
                    preset.id,
                    "protected_words",
                    text,
                    { protected_words: words },
                    AUTOSAVE_MS,
                  );
                }}
              />
              {refusal("protected_words")}
            </div>
          </FormRow>
        </div>
      </Section>
    </div>
  );
}
