import { useState, type KeyboardEvent } from "react";

import type { RenderOptions } from "../../api/types";
import { Choice } from "../../ui/Choice";
import { formatDuration } from "../../ui/format";
import { FormRow } from "../../ui/FormRow";
import { CloseIcon } from "../../ui/icons";
import { useEstimate } from "./useEstimate";

type Option = keyof RenderOptions;

interface Row<O extends Option = Option> {
  option: O;
  label: string;
  description?: string;
  choices: [RenderOptions[O], string][];
}

const SWITCH: [boolean, string][] = [
  [false, "Não"],
  [true, "Sim"],
];
const REMOVE: ["keep" | "remove", string][] = [
  ["keep", "Não"],
  ["remove", "Sim"],
];

// docs/prototype/wordcut.html exportDialog: its groups, labels and choices, mapped onto the
// options of docs/cli.md §8.7.
const GROUPS: [string, Row[]][] = [
  [
    "Limpeza",
    [
      {
        option: "fillers",
        label: "Remover hesitações",
        description: "“hã”, “né”, “ahn”…",
        choices: REMOVE,
      },
      {
        option: "stammers",
        label: "Remover gaguejos",
        description: "Palavras e frases repetidas ao recomeçar.",
        choices: REMOVE,
      },
      {
        option: "pauses",
        label: "Pausas",
        choices: [
          ["original", "Originais"],
          ["natural", "Naturais"],
          ["short", "Curtas"],
        ],
      },
    ],
  ],
  [
    "Edição",
    [
      {
        option: "smooth_joins",
        label: "Suavizar emendas",
        description: "Fade curto no áudio entre trechos.",
        choices: SWITCH,
      },
      { option: "fade", label: "Fade no início e no fim", choices: SWITCH },
    ],
  ],
  [
    "Áudio",
    [
      {
        option: "normalize",
        label: "Normalizar volume",
        description: "Nível de redes sociais (−14 LUFS).",
        choices: SWITCH,
      },
    ],
  ],
  [
    "Vídeo",
    [
      {
        option: "caption",
        label: "Legenda",
        description: "O estilo fica na aba Legenda.",
        choices: SWITCH,
      },
      {
        option: "resolution",
        label: "Resolução",
        choices: [
          ["1080x1920", "1080×1920"],
          ["720x1280", "720×1280"],
        ],
      },
      {
        option: "quality",
        label: "Qualidade",
        choices: [
          ["high", "Alta"],
          ["small", "Arquivo menor"],
        ],
      },
    ],
  ],
];

interface ExportDialogProps {
  cutId: number;
  title: string;
  /** The options the dialog opens with: the cut's, with the caption as the Legenda tab has it. */
  initial: RenderOptions;
  /** What holds the machine; exporting waits for it. */
  busy?: string;
  /** The export is being launched. */
  sending: boolean;
  /** The cut's caption or spelling is still being saved: exporting now would miss it. */
  saving: boolean;
  /** Why the API refused to launch it. */
  refusal?: string;
  onClose: () => void;
  onExport: (options: RenderOptions) => void;
}

/** Exportar 9:16: the export's options in the prototype's groups. */
export function ExportDialog({
  cutId,
  title,
  initial,
  busy,
  sending,
  saving,
  refusal,
  onClose,
  onExport,
}: ExportDialogProps) {
  const [options, setOptions] = useState(initial);
  const estimate = useEstimate(cutId, options);

  function closeOnEscape(event: KeyboardEvent) {
    if (event.key === "Escape") {
      onClose();
    }
  }

  function pick<O extends Option>(option: O, value: RenderOptions[O]) {
    setOptions((current) => ({ ...current, [option]: value }));
  }

  return (
    <div className="modal-bg" onKeyDown={closeOnEscape}>
      <div className="modal xmodal" role="dialog" aria-modal="true" aria-labelledby="export-title">
        <div className="row">
          <div className="xhead">
            <h2 id="export-title">Exportar 9:16</h2>
            <p className="note">{title}</p>
          </div>
          <button className="ibtn sm" type="button" aria-label="Fechar" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <div className="xbody">
          {GROUPS.map(([group, rows]) => (
            <section className="xsec" key={group}>
              <h3>{group}</h3>
              {rows.map((row) => (
                <FormRow key={row.option} label={row.label} description={row.description}>
                  <Choice
                    name={row.label}
                    options={row.choices}
                    value={options[row.option]}
                    onPick={(value) => pick(row.option, value)}
                  />
                </FormRow>
              ))}
            </section>
          ))}
        </div>
        <div className="xfoot">
          <p className="note">
            Duração estimada{" "}
            <b className="mono">
              {estimate.duration === undefined ? "…" : formatDuration(estimate.duration)}
            </b>
          </p>
          {estimate.error && (
            <p className="ferr" role="alert">
              {estimate.error.message}
            </p>
          )}
          {busy !== undefined && <p className="note">Máquina ocupada: {busy}.</p>}
          {refusal && (
            <p className="ferr" role="alert">
              {refusal}
            </p>
          )}
          <span className="spacer" />
          <button className="btn ghost" type="button" onClick={onClose}>
            Cancelar
          </button>
          <button
            className="btn primary"
            type="button"
            disabled={busy !== undefined || sending || saving}
            onClick={() => onExport(options)}
          >
            {saving ? "Salvando…" : "Exportar"}
          </button>
        </div>
      </div>
    </div>
  );
}
