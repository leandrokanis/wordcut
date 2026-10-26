/** A segmented control: one button per option, the chosen one pressed. Picking the chosen one
 * again does nothing. An option may bring a hint, shown on hover. */
export function Choice<T extends string | boolean>({
  name,
  options,
  value,
  onPick,
}: {
  name: string;
  options: [T, string, string?][];
  value: T;
  onPick: (value: T) => void;
}) {
  return (
    <div className="segctl" role="group" aria-label={name}>
      {options.map(([option, label, hint]) => (
        <button
          key={label}
          type="button"
          title={hint}
          aria-pressed={option === value}
          onClick={() => option !== value && onPick(option)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
