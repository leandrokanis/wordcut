import type { ReactNode } from "react";

/** One section of the settings, reached from the menu by ``id``. */
export function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section className="ssec" id={id} aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}

/** What a section shows while its data loads or when the API refused it. */
export function Loading({ error }: { error?: { message: string } }) {
  return error ? (
    <p className="ferr" role="alert">
      {error.message}
    </p>
  ) : (
    <p className="note">Carregando…</p>
  );
}
