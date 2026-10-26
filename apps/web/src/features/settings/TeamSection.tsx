import { useState, type FormEvent } from "react";

import {
  addMember,
  listMembers,
  removeMember,
  setMemberRole,
  type ApiError,
} from "../../api/client";
import type { Member, Role } from "../../api/types";
import { useResource } from "../../api/useResource";
import { useMe, useReloadMe } from "../../app/Identity";
import { Loading, Section } from "./Section";

/** Pessoas: who is on the team and with which role; of a person, only the e-mail. */
export function TeamSection({ onSaved }: { onSaved: () => void }) {
  const loaded = useResource(listMembers, "members");
  return (
    <Section id="pessoas" title="Pessoas">
      {loaded.data ? (
        <Team initial={loaded.data} onSaved={onSaved} />
      ) : (
        <Loading error={loaded.error} />
      )}
    </Section>
  );
}

const ROLES: [Role, string][] = [
  ["assistant", "Assistente"],
  ["admin", "Administrador"],
];

function Team({ initial, onSaved }: { initial: Member[]; onSaved: () => void }) {
  const [team, setTeam] = useState(initial);
  const me = useMe();
  const reloadMe = useReloadMe();
  const [error, setError] = useState<string>();

  /** Runs a change of the team; a refusal leaves the list as the API has it. */
  async function run(change: () => Promise<void>) {
    setError(undefined);
    try {
      await change();
      onSaved();
    } catch (refusal) {
      setError((refusal as ApiError).message);
    }
  }

  function changeRole(email: string, role: Role) {
    return run(async () => {
      const changed = await setMemberRole(email, role);
      setTeam((current) =>
        current.map((candidate) => (candidate.email === changed.email ? changed : candidate)),
      );
      if (changed.email === me.email) {
        reloadMe();
      }
    });
  }

  function remove(email: string) {
    return run(async () => {
      await removeMember(email);
      setTeam((current) => current.filter((candidate) => candidate.email !== email));
    });
  }

  return (
    <>
      <div className="scard">
        <div className="team">
          {team.map((member) => (
            <div key={member.email}>
              <span className="mono">{member.email}</span>
              <select
                className="input"
                aria-label={`Papel de ${member.email}`}
                value={member.role}
                onChange={(event) => changeRole(member.email, event.target.value as Role)}
              >
                {ROLES.map(([role, label]) => (
                  <option key={role} value={role}>
                    {label}
                  </option>
                ))}
              </select>
              <button
                className="btn sm ghost danger"
                type="button"
                aria-label={`Remover ${member.email}`}
                onClick={() => remove(member.email)}
              >
                Remover
              </button>
            </div>
          ))}
        </div>
        {error && (
          <p className="ferr" role="alert">
            {error}
          </p>
        )}
      </div>
      <NewMember
        onAdded={(added) => {
          setTeam((current) =>
            [...current, added].sort((a, b) => a.email.localeCompare(b.email)),
          );
          onSaved();
        }}
      />
    </>
  );
}

/** Liberar acesso: an e-mail and its role, sent with Enter. */
function NewMember({ onAdded }: { onAdded: (member: Member) => void }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("assistant");
  const [error, setError] = useState<string>();

  function send(event: FormEvent) {
    event.preventDefault();
    setError(undefined);
    addMember(email, role).then(
      (added) => {
        setEmail("");
        onAdded(added);
      },
      (refusal: ApiError) => setError(refusal.message),
    );
  }

  return (
    <div className="scard">
      <h3>Liberar acesso</h3>
      {/* noValidate: the API checks the e-mail and tells why, as everywhere else. */}
      <form className="team-add" noValidate onSubmit={send}>
        <input
          className="input mono"
          type="email"
          placeholder="email@exemplo.org"
          aria-label="E-mail"
          aria-invalid={error ? true : undefined}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <select
          className="input"
          aria-label="Papel do novo membro"
          value={role}
          onChange={(event) => setRole(event.target.value as Role)}
        >
          {ROLES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <button className="btn" type="submit">
          Liberar
        </button>
      </form>
      {error && (
        <p className="ferr" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
