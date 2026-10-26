import { useState, type FormEvent, type KeyboardEvent } from "react";

import { createSermon, type ApiError } from "../../api/client";
import type { SermonCreated } from "../../api/types";
import { CloseIcon } from "../../ui/icons";

interface Props {
  onClose: () => void;
  onCreated: (sermon: SermonCreated) => void;
}

const REASON_ID = "new-sermon-reason";

/** Creates a sermon from the live's link; every refusal shows next to the field. */
export function NewSermonDialog({ onClose, onCreated }: Props) {
  const [url, setUrl] = useState("");
  const [sending, setSending] = useState(false);
  const [reason, setReason] = useState<string>();

  function closeOnEscape(event: KeyboardEvent) {
    if (event.key === "Escape") {
      onClose();
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (sending) {
      return;
    }
    setSending(true);
    setReason(undefined);
    createSermon(url.trim()).then(onCreated, (error: ApiError) => {
      setReason(error.message);
      setSending(false);
    });
  }

  return (
    <div className="modal-bg" onKeyDown={closeOnEscape}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="new-sermon-title">
        <div className="row">
          <h2 id="new-sermon-title">Nova pregação</h2>
          <span className="spacer" />
          <button className="ibtn sm" type="button" aria-label="Fechar" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <form onSubmit={submit}>
          <div>
            <input
              className="input mono"
              name="url"
              aria-label="Link da live no YouTube"
              placeholder="Link da live no YouTube"
              autoComplete="off"
              autoFocus
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              aria-invalid={reason ? true : undefined}
              aria-describedby={reason ? REASON_ID : undefined}
            />
            {reason && (
              <p className="ferr" id={REASON_ID}>
                {reason}
              </p>
            )}
          </div>
          <div className="actions">
            <button className="btn primary" type="submit" disabled={sending || !url.trim()}>
              Carregar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
