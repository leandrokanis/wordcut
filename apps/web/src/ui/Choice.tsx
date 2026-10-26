/** A segmented control: one button per option, the chosen one pressed. Picking the chosen one
 * again does nothing. */
export function Choice<T extends string | boolean>({
  name,
  options,
  value,
  onPick,
}: {
  name: string;
  options: [T, string][];
  value: T;
  onPick: (value: T) => void;
}) {
  return (
    <div className="segctl" role="group" aria-label={name}>
      {options.map(([option, label]) => (
        <button
          key={label}
          type="button"
          aria-pressed={option === value}
          onClick={() => option !== value && onPick(option)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
