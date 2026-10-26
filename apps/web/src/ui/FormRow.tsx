import type { ReactNode } from "react";

/** A form line of the prototype: label and description on the left, the control on the right.
 * With ``controlId``, the label names that control; without it, the control names itself. */
export function FormRow({
  label,
  description,
  controlId,
  wide = false,
  children,
}: {
  label: string;
  description?: ReactNode;
  controlId?: string;
  /** The control takes the whole line below the label, as a long text does. */
  wide?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={wide ? "srow wide" : "srow"}>
      <div>
        {controlId ? (
          <label className="sl" htmlFor={controlId}>
            {label}
          </label>
        ) : (
          <span className="sl">{label}</span>
        )}
        {description && <p className="sd">{description}</p>}
      </div>
      <div className="ctl">{children}</div>
    </div>
  );
}
