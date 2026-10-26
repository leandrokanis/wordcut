import type { Criterion, Level } from "../../api/types";
import { Choice } from "../../ui/Choice";
import { FormRow } from "../../ui/FormRow";

// docs/prototype/wordcut.html LEVELS_F and LEVELS_V: what each level means for a filter and
// for a value, as the buttons' hints.
const HINTS: Record<Criterion["type"], Record<Level, string>> = {
  filter: {
    lenient: "Exclui só quando é evidente",
    moderate: "Exclui quando é provável; o limítrofe vai com alerta",
    strict: "Exclui na menor suspeita",
  },
  value: {
    lenient: "Basta tocar no tema",
    moderate: "O valor aparece com clareza",
    strict: "O valor é o centro do corte, explicado e não só citado",
  },
};

const LABELS: [Level, string][] = [
  ["lenient", "Brando"],
  ["moderate", "Moderado"],
  ["strict", "Rigoroso"],
];

/** How strictly the suggestion applies one filter or value; only its name is shown. */
export function LevelControl({
  criterion,
  value,
  onPick,
}: {
  criterion: Criterion;
  value: Level;
  onPick: (level: Level) => void;
}) {
  const hints = HINTS[criterion.type];
  return (
    <FormRow label={criterion.name}>
      <Choice
        name={`Rigidez: ${criterion.name}`}
        options={LABELS.map(([level, label]) => [level, label, hints[level]])}
        value={value}
        onPick={onPick}
      />
    </FormRow>
  );
}
