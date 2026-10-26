import type { SermonStatus } from "../../api/types";

export const STATUS_LABELS: Record<SermonStatus, { label: string; tone: string }> = {
  created: { label: "A delimitar", tone: "warn" },
  trimmed: { label: "Delimitada", tone: "warn" },
  processing: { label: "Processando", tone: "accent" },
  processed: { label: "Pronta", tone: "ok" },
  failed: { label: "Falhou", tone: "danger" },
};
