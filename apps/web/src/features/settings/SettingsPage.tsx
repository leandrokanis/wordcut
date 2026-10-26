import { Link } from "react-router-dom";

import { useMe } from "../../app/Identity";
import { BackIcon } from "../../ui/icons";

// The groups of docs/prototype/wordcut.html; their content comes in item 26.
const SECTIONS = [
  { id: "modelo", title: "Modelo" },
  { id: "presets", title: "Presets" },
  { id: "filtros", title: "Filtros" },
  { id: "valor", title: "Valor" },
  { id: "formato", title: "Formato" },
  { id: "pessoas", title: "Pessoas" },
  { id: "processamentos", title: "Processamentos" },
];

/** A full screen of its own, only for the administrator. */
export function SettingsPage() {
  const { role } = useMe();
  if (role !== "admin") {
    return (
      <main className="gate">
        <div>
          <h1>Configurações</h1>
          <p className="note">Só o administrador acessa as configurações.</p>
          <p>
            <Link className="btn" to="/">
              Voltar às pregações
            </Link>
          </p>
        </div>
      </main>
    );
  }
  return (
    <div className="settings-screen">
      <nav className="snav" aria-label="Seções das configurações">
        <Link className="sn-back" to="/">
          <BackIcon />
          Voltar às pregações
        </Link>
        <ul className="sn-list">
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a className="sn-i" href={`#${section.id}`}>
                {section.title}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <main className="smain">
        <div className="s-wrap">
          <div className="s-head">
            <h1>Configurações</h1>
          </div>
          {SECTIONS.map((section) => (
            <section className="ssec" id={section.id} key={section.id}>
              <h2>{section.title}</h2>
              <p className="note">Em construção.</p>
            </section>
          ))}
        </div>
      </main>
    </div>
  );
}
