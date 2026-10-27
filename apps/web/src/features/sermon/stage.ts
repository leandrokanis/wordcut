import type { Task } from "../../api/types";

/** The stage of a processing task as the screen names it: the API's message (already in
 * Portuguese) with a capital letter, or "Processando" before the task names one. */
export function stageOf(task: Task | undefined): string {
  const message = task?.progress_message?.trim();
  return message ? message[0].toUpperCase() + message.slice(1) : "Processando";
}

/** "Processando — Baixando 12%", or just "Processando" before the task names its stage. */
export function progressLabel(task: Task | undefined): string {
  if (!task?.progress_message?.trim()) {
    return "Processando";
  }
  return `Processando — ${stageOf(task)} ${Math.round((task.progress ?? 0) * 100)}%`;
}

export interface ProcessStep {
  name: string;
  /** The share of this step that is done, from 0 to 1. */
  progress: number;
  state: "done" | "running" | "pending";
}

// The slices of the task's progress each step takes, as packages/core writes them
// (processing/pipeline.py and tasks/process.py): "sincronizando" falls in the download,
// "gravando" in the cut.
const STEPS: [name: string, from: number, to: number][] = [
  ["Baixar a faixa em 1080p", 0, 0.35],
  ["Transcrever palavra por palavra", 0.35, 0.85],
  ["Cortar a pregação em 16:9", 0.85, 0.96],
  ["Sugerir cortes", 0.96, 1],
];

/** The steps of the processing, as the prototype lists them, at the task's progress. */
export function processSteps(task: Task | undefined): ProcessStep[] {
  const fraction = task?.progress ?? 0;
  return STEPS.map(([name, from, to]) => ({
    name,
    progress: Math.min(1, Math.max(0, (fraction - from) / (to - from))),
    state: fraction >= to ? "done" : fraction >= from ? "running" : "pending",
  }));
}
