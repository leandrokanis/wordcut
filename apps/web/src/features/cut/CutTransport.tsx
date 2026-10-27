import type { ReactNode } from "react";

import { formatDuration } from "../../ui/format";
import {
  LeftIcon,
  PauseIcon,
  PlayIcon,
  RedoIcon,
  RightIcon,
  ScissorsIcon,
  TrashIcon,
  UndoIcon,
} from "../../ui/icons";

// docs/prototype/wordcut.html: a vertical cut is meant to last from 40 to 75 s, both included.
const GOAL_MIN = 40;
const GOAL_MAX = 75;

function onGoal(seconds: number): boolean {
  return GOAL_MIN <= seconds && seconds <= GOAL_MAX;
}

function goalSays(seconds: number): string {
  if (seconds < GOAL_MIN) {
    return "Abaixo";
  }
  return seconds > GOAL_MAX ? "Acima" : "Dentro";
}

/** The tools that change the cut's segments. An action left undefined is not available now. */
export interface SegmentTools {
  /** Only the administrator changes what the cut plays; anyone else sees the tools off. */
  admin: boolean;
  onUndo?: () => void;
  onRedo?: () => void;
  onSplit?: () => void;
  onMoveLeft?: () => void;
  onMoveRight?: () => void;
  onRemove?: () => void;
  /** Why the last change was not saved. */
  error?: string;
}

interface CutTransportProps {
  playing: boolean;
  onToggle: () => void;
  /** The cursor and the cut's length, in seconds of the cut. */
  cursor: number;
  duration: number;
  tools: SegmentTools;
}

/** The segment tools, play/pause, the cursor's time in the cut and the cut's duration against
 * the goal (docs/prototype/wordcut.html ``transport``, level 3). */
export function CutTransport({ playing, onToggle, cursor, duration, tools }: CutTransportProps) {
  const tool = (
    label: string,
    title: string,
    action: (() => void) | undefined,
    icon: ReactNode,
  ) => (
    <button
      className="ibtn"
      type="button"
      title={tools.admin ? title : "Só o administrador muda o conteúdo"}
      aria-label={tools.admin ? label : `${label} (só o administrador)`}
      disabled={!tools.admin || !action}
      onClick={action}
    >
      {icon}
    </button>
  );
  const edit = (label: string, action: (() => void) | undefined, icon: ReactNode) =>
    tool(label, label, action, icon);

  return (
    <div className="transport">
      <div className="tools">
        {tool("Desfazer", "Desfazer (Ctrl+Z)", tools.onUndo, <UndoIcon />)}
        {tool("Refazer", "Refazer (Ctrl+Shift+Z)", tools.onRedo, <RedoIcon />)}
        <span className="tsep" />
        {edit("Dividir o trecho no cursor, entre frases", tools.onSplit, <ScissorsIcon />)}
        {edit("Mover o trecho para a esquerda", tools.onMoveLeft, <LeftIcon />)}
        {edit("Mover o trecho para a direita", tools.onMoveRight, <RightIcon />)}
        {edit("Remover o trecho", tools.onRemove, <TrashIcon />)}
        {tools.error && (
          <p className="ferr" role="alert">
            {tools.error}
          </p>
        )}
      </div>
      <div className="tools c">
        <button
          className="play"
          type="button"
          aria-label={playing ? "Pausar" : "Reproduzir"}
          onClick={onToggle}
        >
          {playing ? <PauseIcon /> : <PlayIcon />}
        </button>
        <span className="tc" aria-label="Tempo do corte">
          <b>{formatDuration(cursor)}</b> / {formatDuration(duration)}
        </span>
      </div>
      <div className="tools r">
        <span
          className={`chip mono ${onGoal(duration) ? "ok" : "warn"}`}
          aria-label="Duração do corte"
          title={`${goalSays(duration)} da meta de ${GOAL_MIN} a ${GOAL_MAX} s`}
        >
          {formatDuration(duration)}
        </span>
      </div>
    </div>
  );
}
