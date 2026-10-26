import { useState, type CSSProperties, type ReactNode } from "react";

import type { ApiError } from "../../api/client";

import type { CaptionPosition, CaptionShadow, CutWord } from "../../api/types";
import { Choice } from "../../ui/Choice";
import { CAPTION_FONTS } from "./captions";
import type { CaptionField, CaptionStyleState } from "./useCaptionStyle";

// The ranges of docs/cli.md §8.6, in px of the 1080×1920 frame and % of its height.
const SIZE_PX = { min: 24, max: 160 };
const OFFSET_PERCENT = { min: 10, max: 90 };
const BORDER_PX = { min: 0, max: 12 };

const TEXT_COLORS: [string, string][] = [
  ["#FFD600", "Amarelo"],
  ["#FFFFFF", "Branco"],
  ["#00E5FF", "Ciano"],
  ["#FF9F1C", "Laranja"],
  ["#FF5C8A", "Rosa"],
];
const BORDER_COLORS: [string, string][] = [
  ["#000000", "Preto"],
  ["#FFFFFF", "Branco"],
];
const SWITCH: [boolean, string][] = [
  [false, "Não"],
  [true, "Sim"],
];
const POSITIONS: [CaptionPosition, string][] = [
  ["top", "Topo"],
  ["center", "Centro"],
  ["bottom", "Base"],
];
const SHADOWS: [CaptionShadow, string][] = [
  ["none", "Não"],
  ["soft", "Suave"],
  ["strong", "Forte"],
];

interface CaptionTabProps {
  caption: CaptionStyleState;
  /** The cut's words, the fixed ones listed under "Correções de grafia". */
  words: CutWord[];
  /** Undoes the word's fix; answers the API's refusal, if any. */
  onUndo: (word: CutWord) => Promise<ApiError | undefined>;
}

/** The Legenda tab: the cut's caption style, one row per control, label on the left and the
 * control on the right, and the cut's spelling fixes. There is no save button: each change
 * saves by itself. */
export function CaptionTab({ caption, words, onUndo }: CaptionTabProps) {
  const { style, errors, change } = caption;
  const fieldProps = (field: CaptionField) => ({
    "aria-invalid": errors[field] ? true : undefined,
    "aria-describedby": errors[field] ? errorId(field) : undefined,
  });
  const range = (field: "size" | "offset" | "border", name: string, limits: typeof SIZE_PX) => (
    <input
      type="range"
      className="rng"
      min={limits.min}
      max={limits.max}
      step={1}
      value={style[field]}
      aria-label={name}
      {...fieldProps(field)}
      onChange={(event) => change(field, Number(event.target.value))}
    />
  );
  const fonts = [...new Set([style.font, ...Object.keys(CAPTION_FONTS)])];

  return (
    <>
      <section className="sgroup lform">
        <h3>Estilo</h3>
        <Row label="Legenda" error={errors.enabled} field="enabled">
          <Choice
            name="Legenda"
            options={SWITCH}
            value={style.enabled}
            onPick={(enabled) => change("enabled", enabled)}
          />
        </Row>
        {style.enabled && (
          <>
            <Row label="Fonte" error={errors.font} field="font">
              <select
                className="input"
                aria-label="Fonte"
                value={style.font}
                {...fieldProps("font")}
                onChange={(event) => change("font", event.target.value)}
              >
                {fonts.map((font) => (
                  <option key={font}>{font}</option>
                ))}
              </select>
            </Row>
            <Row label="Tamanho" error={errors.size} field="size">
              {range("size", "Tamanho", SIZE_PX)}
              <span className="unit mono lval">{style.size} px</span>
            </Row>
            <Row label="Cor" error={errors.color} field="color">
              <Swatches
                name="Cor"
                colors={TEXT_COLORS}
                value={style.color}
                onPick={(color) => change("color", color)}
              />
            </Row>
            <Row label="Posição" error={errors.position} field="position">
              <Choice
                name="Posição"
                options={POSITIONS}
                value={style.position}
                onPick={(position) => change("position", position)}
              />
            </Row>
            <Row label="Altura" error={errors.offset} field="offset">
              {range("offset", "Altura da legenda", OFFSET_PERCENT)}
              <span className="unit mono lval">{style.offset}%</span>
            </Row>
            <Row label="Borda" error={errors.border} field="border">
              {range("border", "Espessura da borda", BORDER_PX)}
              <span className="unit mono lval">{style.border} px</span>
            </Row>
            <Row label="Cor da borda" error={errors.border_color} field="border_color">
              <Swatches
                name="Cor da borda"
                colors={BORDER_COLORS}
                value={style.border_color}
                onPick={(color) => change("border_color", color)}
              />
            </Row>
            <Row label="Sombra" error={errors.shadow} field="shadow">
              <Choice
                name="Sombra"
                options={SHADOWS}
                value={style.shadow}
                onPick={(shadow) => change("shadow", shadow)}
              />
            </Row>
          </>
        )}
        <div className="lrow">
          <span />
          <div className="ctl">
            <button className="btn sm ghost" type="button" onClick={caption.reset}>
              Restaurar padrão
            </button>
          </div>
          {caption.resetError && (
            <p className="ferr" role="alert">
              {caption.resetError}
            </p>
          )}
        </div>
      </section>
      <SpellingFixes words={words} onUndo={onUndo} />
    </>
  );
}

/** The words of the cut whose spelling was fixed: original → fix, each with Desfazer, which
 * saves the original again (docs/api.md, ``PUT /api/cuts/{id}/words/{word_id}``). */
function SpellingFixes({ words, onUndo }: Pick<CaptionTabProps, "words" | "onUndo">) {
  const [error, setError] = useState<string>();
  const fixed = words.filter(({ corrected }) => corrected !== null);

  async function undo(word: CutWord) {
    setError((await onUndo(word))?.message);
  }

  return (
    <section className="sgroup">
      <h3 id="spelling-fixes">Correções de grafia</h3>
      {fixed.length ? (
        <ul className="versions" aria-labelledby="spelling-fixes">
          {fixed.map((word) => (
            <li key={word.word_id}>
              <span>
                {word.text} → <b>{word.corrected}</b>
              </span>
              <button className="btn sm ghost" type="button" onClick={() => void undo(word)}>
                Desfazer
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="note">Nenhuma correção.</p>
      )}
      {error && (
        <p className="ferr" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

function errorId(field: CaptionField): string {
  return `caption-${field}-error`;
}

function Row({
  label,
  field,
  error,
  children,
}: {
  label: string;
  field: CaptionField;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="lrow">
      <span className="sl">{label}</span>
      <div className="ctl">{children}</div>
      {error && (
        <p className="ferr" id={errorId(field)} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

function Swatches({
  name,
  colors,
  value,
  onPick,
}: {
  name: string;
  colors: [string, string][];
  value: string;
  onPick: (color: string) => void;
}) {
  const current = value.toUpperCase();
  return (
    <div className="swatches" role="group" aria-label={name}>
      {colors.map(([color, label]) => (
        <button
          key={color}
          type="button"
          className="sw"
          style={{ "--sw": color } as CSSProperties}
          aria-pressed={current === color}
          aria-label={label}
          title={label}
          onClick={() => current !== color && onPick(color)}
        />
      ))}
      <input
        type="color"
        className="pick"
        value={value.toLowerCase()}
        aria-label="Outra cor"
        title="Outra cor"
        onChange={(event) => onPick(event.target.value.toUpperCase())}
      />
    </div>
  );
}
