import { useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useMe } from "../../app/Identity";
import { deleteSermon, listSermons, type ApiError } from "../../api/client";
import type { SermonCreated, SermonListItem } from "../../api/types";
import { useResource } from "../../api/useResource";
import { formatDate, formatDuration } from "../../ui/format";
import { DotsIcon } from "../../ui/icons";
import { useDismiss } from "../../ui/useDismiss";
import { useMachineStatus } from "../status/MachineStatus";
import { NewSermonDialog } from "./NewSermonDialog";
import { STATUS_LABELS } from "./sermonStatus";

export function SermonList() {
  const sermons = useResource(listSermons, "sermons");
  const admin = useMe().role === "admin";
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<SermonCreated>();

  function showCreated(sermon: SermonCreated) {
    setCreating(false);
    setCreated(sermon);
    sermons.reload();
  }

  const empty = sermons.data?.length === 0;
  const listed = Boolean(sermons.data?.length || sermons.error);
  const newSermon = (
    <button
      className="btn primary"
      type="button"
      onClick={() => setCreating(true)}
    >
      Nova pregação
    </button>
  );
  return (
    <main className="l1">
      <div className="l1-wrap">
        <div className="l1-head">
          <h1>Pregações</h1>
          <span className="spacer" />
          {listed && newSermon}
        </div>
        {created && <CreatedNotice sermon={created} />}
        {sermons.error && (
          <div className="banner err" role="alert">
            <div>
              <strong>Não foi possível carregar as pregações.</strong>{" "}
              {sermons.error.message}
            </div>
            <button className="btn" type="button" onClick={sermons.reload}>
              Tentar de novo
            </button>
          </div>
        )}
        {empty && (
          <div className="emptyp">
            <p>Nenhuma pregação ainda.</p>
            {newSermon}
          </div>
        )}
        {sermons.data && !empty && (
          <ul className="pgrid">
            {sermons.data.map((sermon) => (
              <SermonCard
                key={sermon.id}
                sermon={sermon}
                admin={admin}
                onDeleted={sermons.reload}
              />
            ))}
          </ul>
        )}
      </div>
      {creating && (
        <NewSermonDialog
          onClose={() => setCreating(false)}
          onCreated={showCreated}
        />
      )}
    </main>
  );
}

function CreatedNotice({ sermon }: { sermon: SermonCreated }) {
  if (!sermon.created) {
    return (
      <div className="banner" role="status">
        <div>Esta live já tinha uma pregação: {sermon.title}.</div>
      </div>
    );
  }
  return (
    <div
      className={sermon.live_finished ? "banner ok" : "banner"}
      role="status"
    >
      <div>
        Pregação criada: {sermon.title}, culto de{" "}
        {formatDate(sermon.service_date)}, live de{" "}
        {formatDuration(sermon.live_duration)}.
        {!sermon.live_finished && (
          <>
            {" "}
            <strong>A live ainda não terminou.</strong> Processe a pregação
            depois do fim da transmissão.
          </>
        )}
      </div>
    </div>
  );
}

interface SermonCardProps {
  sermon: SermonListItem;
  /** Only the administrator deletes sermons (1.2.b.1). */
  admin: boolean;
  onDeleted: () => void;
}

function SermonCard({ sermon, admin, onDeleted }: SermonCardProps) {
  const status = STATUS_LABELS[sermon.status];
  const progress = useProcessProgress(sermon);
  return (
    <li className="pcard">
      <Link className="pc-main" to={`/sermons/${sermon.id}`}>
        <span className="pdate mono">{formatDate(sermon.service_date)}</span>
        <span className="pt">{sermon.title}</span>
        <span className="pmeta">
          <span className={`chip ${status.tone}`}>
            {progress === undefined
              ? status.label
              : `${status.label} ${progress}%`}
          </span>
          {sermon.duration === null ? (
            <span>Duração a delimitar</span>
          ) : (
            <span className="mono">{formatDuration(sermon.duration)}</span>
          )}
        </span>
      </Link>
      {admin && <SermonActions sermon={sermon} onDeleted={onDeleted} />}
    </li>
  );
}

/** The card's "Mais ações" menu, with Apagar and its confirmation, after the prototype. */
function SermonActions({ sermon, onDeleted }: Omit<SermonCardProps, "admin">) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [failure, setFailure] = useState<ApiError>();
  const area = useRef<HTMLDivElement>(null);
  useDismiss(area, menuOpen, () => setMenuOpen(false));

  function askToDelete() {
    setMenuOpen(false);
    setFailure(undefined);
    setConfirming(true);
  }

  function remove() {
    deleteSermon(sermon.id).then(onDeleted, (error: ApiError) => {
      setConfirming(false);
      setFailure(error);
    });
  }

  return (
    <div ref={area}>
      <button
        className="ibtn sm pc-more"
        type="button"
        aria-label="Mais ações"
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen(!menuOpen)}
      >
        <DotsIcon />
      </button>
      {menuOpen && (
        <div className="cmenu pc-menu" role="menu">
          <button
            className="mi danger"
            type="button"
            role="menuitem"
            onClick={askToDelete}
          >
            <b>Apagar</b>
          </button>
        </div>
      )}
      {confirming && (
        <div className="pc-confirm">
          <span>Apagar a pregação e {cutsLabel(sermon)}?</span>
          <div className="row">
            <button className="btn sm danger" type="button" onClick={remove}>
              Apagar
            </button>
            <button
              className="btn sm ghost"
              type="button"
              onClick={() => setConfirming(false)}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
      {failure && (
        <p className="ferr pc-err" role="alert">
          {failure.message}
        </p>
      )}
    </div>
  );
}

/** "1 corte" or "N cortes": every cut of the sermon, since all of them go with it. */
function cutsLabel(sermon: SermonListItem): string {
  const { suggested, chosen, discarded } = sermon.cut_counts;
  const count = suggested + chosen + discarded;
  return `${count} ${count === 1 ? "corte" : "cortes"}`;
}

/** The percentage of the sermon's running process task, while the machine status has it. */
function useProcessProgress(sermon: SermonListItem): number | undefined {
  const { status } = useMachineStatus();
  if (sermon.status !== "processing") {
    return undefined;
  }
  const task = status?.running_tasks.find(
    (running) => running.kind === "process" && running.sermon_id === sermon.id,
  );
  return task?.progress == null ? undefined : Math.round(task.progress * 100);
}
