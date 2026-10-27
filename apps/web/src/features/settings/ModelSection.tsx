import { useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";

import {
  getSettings,
  patchSettings,
  putLlmKey,
  putYoutubeCookies,
  type ApiError,
} from "../../api/client";
import type { Settings, SettingsModels } from "../../api/types";
import { useResource } from "../../api/useResource";
import { FormRow } from "../../ui/FormRow";
import { CommitInput } from "./CommitInput";
import { Loading, Section } from "./Section";

/** Modelo: the models of the suggestion and of the transcription and the two secrets. */
export function ModelSection({ onSaved }: { onSaved: () => void }) {
  const loaded = useResource(getSettings, "settings");
  return (
    <Section id="modelo" title="Modelo">
      {loaded.data ? <ModelForm initial={loaded.data} onSaved={onSaved} /> : <Loading error={loaded.error} />}
    </Section>
  );
}

function ModelForm({ initial, onSaved }: { initial: Settings; onSaved: () => void }) {
  const [current, setCurrent] = useState(initial);

  async function saveModels(models: SettingsModels) {
    setCurrent(await patchSettings(models));
    onSaved();
  }

  async function storeSecret(store: () => Promise<Settings>) {
    setCurrent(await store());
    onSaved();
  }

  return (
    <div className="scard">
      <FormRow label="Modelo" description="Usado na sugestão automática." controlId="llm-model">
        <CommitInput
          className="input mono"
          id="llm-model"
          value={current.llm_model ?? ""}
          save={(text) => saveModels({ llm_model: text })}
        />
      </FormRow>
      <FormRow label="Modelo do WhisperX" controlId="whisper-model">
        <CommitInput
          className="input mono"
          id="whisper-model"
          value={current.whisper_model}
          save={(text) => saveModels({ whisper_model: text })}
        />
      </FormRow>
      <FormRow
        label="Chave da API"
        description={current.llm_key ? `Atual: ${current.llm_key}` : "Nenhuma chave gravada"}
        controlId="llm-key"
      >
        <KeyForm store={(key) => storeSecret(() => putLlmKey(key))} />
      </FormRow>
      <FormRow
        label="Cookies do YouTube"
        description={current.youtube_cookies ? "Presentes" : "Ausentes"}
      >
        <CookiesForm store={(text) => storeSecret(() => putYoutubeCookies(text))} />
      </FormRow>
    </div>
  );
}

// docs/api.md §2: in the Docker Compose the secrets are read-only for the API.
const NOT_WRITABLE = "config_not_writable";

/** Why a secret was refused; when the API cannot write it, how to store it on the host. */
function secretRefusal(refusal: ApiError, hostCommand: string): ReactNode {
  if (refusal.code !== NOT_WRITABLE) {
    return refusal.message;
  }
  return (
    <>
      {refusal.message} Grave pela CLI no host: <code>{hostCommand}</code>
    </>
  );
}

/** The LLM key, written and never read back: the field is emptied as soon as it is sent and
 * holds the key only in the DOM input, never in React state. */
function KeyForm({ store }: { store: (key: string) => Promise<void> }) {
  const field = useRef<HTMLInputElement>(null);
  const sending = useRef(false);
  const [error, setError] = useState<ReactNode>();

  function submit(event: FormEvent) {
    event.preventDefault();
    send();
  }

  function send() {
    const input = field.current;
    // Checked before the field is read: a key typed meanwhile stays there for the next send.
    if (!input || sending.current) {
      return;
    }
    const key = input.value;
    input.value = "";
    if (!key.trim()) {
      return;
    }
    sending.current = true;
    setError(undefined);
    store(key)
      .catch((refusal: ApiError) =>
        setError(secretRefusal(refusal, "wordcut settings set-key < chave.txt")),
      )
      .finally(() => (sending.current = false));
  }

  return (
    <form className="field" onSubmit={submit}>
      <input
        ref={field}
        className="input mono"
        id="llm-key"
        type="password"
        autoComplete="off"
        placeholder="Cole a nova chave"
        aria-label="Nova chave"
        aria-invalid={error ? true : undefined}
        onBlur={send}
      />
      {error && (
        <p className="ferr" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}

/** The YouTube cookies, sent as the chosen ``cookies.txt`` file and never shown. */
function CookiesForm({ store }: { store: (text: string) => Promise<void> }) {
  const [error, setError] = useState<ReactNode>();

  function send(event: ChangeEvent<HTMLInputElement>) {
    const input = event.target;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    setError(undefined);
    readText(file)
      .then(store)
      .catch((refusal: ApiError) =>
        setError(secretRefusal(refusal, "wordcut settings set-cookies < cookies.txt")),
      )
      .finally(() => (input.value = ""));
  }

  return (
    <div className="field">
      <input
        className="input"
        type="file"
        accept=".txt,text/plain"
        aria-label="Arquivo de cookies"
        aria-invalid={error ? true : undefined}
        onChange={send}
      />
      {error && (
        <p className="ferr" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

// FileReader rather than Blob.text(): jsdom, where the tests run, has no Blob.text().
function readText(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}
