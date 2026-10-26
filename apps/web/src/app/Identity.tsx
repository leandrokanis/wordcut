import { createContext, useContext, type ReactNode } from "react";

import { getMe, type ApiError } from "../api/client";
import type { Me } from "../api/types";
import { useResource } from "../api/useResource";

const MeContext = createContext<Me | undefined>(undefined);

const BLOCKED: Record<string, { title: string; hint: string }> = {
  unauthenticated: {
    title: "Você não está identificado.",
    hint: "Entre pelo acesso da equipe e recarregue a página.",
  },
  forbidden: {
    title: "Seu e-mail não faz parte da equipe.",
    hint: "Peça a um administrador que libere o seu acesso.",
  },
};

/** Renders ``children`` only for a team member, known from GET /api/me (ADR-0019). */
export function IdentityGate({ children }: { children: ReactNode }) {
  const me = useResource(getMe, "me");
  if (me.error) {
    return <Blocked error={me.error} retry={me.reload} />;
  }
  if (!me.data) {
    return (
      <div className="gate" aria-busy="true">
        <p className="note">Carregando…</p>
      </div>
    );
  }
  return <MeContext.Provider value={me.data}>{children}</MeContext.Provider>;
}

/** The member using the application; only valid below ``IdentityGate``. */
export function useMe(): Me {
  const me = useContext(MeContext);
  if (!me) {
    throw new Error("useMe must be used below IdentityGate");
  }
  return me;
}

function Blocked({ error, retry }: { error: ApiError; retry: () => void }) {
  const blocked = BLOCKED[error.code];
  return (
    <main className="gate">
      <div>
        <h1>{blocked ? blocked.title : "A API não respondeu."}</h1>
        <p className="note">{blocked ? blocked.hint : error.message}</p>
        {!blocked && (
          <p>
            <button className="btn" type="button" onClick={retry}>
              Tentar de novo
            </button>
          </p>
        )}
      </div>
    </main>
  );
}
