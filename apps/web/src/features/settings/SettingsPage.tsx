import { useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useMe } from "../../app/Identity";
import { BackIcon } from "../../ui/icons";
import { Saved } from "../../ui/Saved";
import { ModelSection } from "./ModelSection";
import { PresetSections } from "./PresetSections";
import { TeamSection } from "./TeamSection";
import { useScrollSpy } from "./useScrollSpy";

// docs/prototype/wordcut.html SPAGES, without Processamentos (item 26, L1).
const SECTIONS = [
  { id: "modelo", title: "Modelo" },
  { id: "presets", title: "Presets" },
  { id: "filtros", title: "Filtros" },
  { id: "valor", title: "Valor" },
  { id: "formato", title: "Formato" },
  { id: "pessoas", title: "Pessoas" },
];
const SECTION_IDS = SECTIONS.map((section) => section.id);

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
  return <AdminSettings />;
}

function AdminSettings() {
  const bottom = useRef<HTMLDivElement>(null);
  const spy = useScrollSpy(SECTION_IDS, bottom);
  const [savedAt, setSavedAt] = useState(0);
  // One Salvo for the whole screen, as the prototype's .s-saved (L11).
  const onSaved = () => setSavedAt((count) => count + 1);
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
              <a
                className="sn-i"
                href={`#${section.id}`}
                aria-current={spy.current === section.id ? "true" : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  spy.jump(section.id);
                }}
              >
                {section.title}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <main className="smain">
        <div className="s-saved">
          <Saved savedAt={savedAt} />
        </div>
        <div className="s-wrap">
          <div className="s-head">
            <h1>Configurações</h1>
          </div>
          <ModelSection onSaved={onSaved} />
          <PresetSections onSaved={onSaved} />
          <TeamSection onSaved={onSaved} />
          <div className="s-end" ref={bottom} />
        </div>
      </main>
    </div>
  );
}
