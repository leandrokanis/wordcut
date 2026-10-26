# API HTTP do Wordcut

A API (`apps/api`, FastAPI) expõe à web as mesmas operações da CLI, sobre a mesma camada de
serviço ([ADR-0004](adr/0004-camada-de-servico-no-core.md)). Este documento lista as rotas,
os corpos, os status e os eventos de progresso. As decisões estão na
[ADR-0019](adr/0019-identidade-e-erros-na-api.md) e na
[ADR-0020](adr/0020-rotas-e-progresso-por-sse-na-api.md).

As palavras-chave DEVE, NÃO DEVE e PODE seguem o BCP 14
([RFC 2119](https://www.rfc-editor.org/rfc/rfc2119),
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)).

## 1. Convenções

- Os corpos de resposta são o JSON da CLI com `--json` ([docs/cli.md](cli.md) §4.3): objeto
  para um item, `{"items": […]}` para listagens, tempos em segundos como número, datas em
  ISO 8601 com fuso.
- Um erro é `{"error": {"code", "message", "details"?}}`, o objeto da CLI (§5), com o status
  da tabela da ADR-0019: `invalid_argument` 400, `unauthenticated` 401, `forbidden` 403,
  `not_found` 404, `busy` e as regras (saída 5) 409, falha externa (saída 6) 502, falha
  interna 500.
- Um corpo, um parâmetro de caminho ou um filtro que a rota não aceita dá 400
  `invalid_argument`, com o nome do argumento em `details.argument` e, num filtro com
  escolhas, a lista em `details.choices`. A resposta nunca repete o valor enviado
  ([ADR-0015](adr/0015-erro-de-uso-nao-repete-valor-digitado.md)).
- Uma rota que não existe dá 404 `not_found`.
- Toda rota, menos `GET /api/health`, exige um membro da equipe identificado pelo Cloudflare
  Access. Sem identificação, 401 `unauthenticated`; e-mail fora da equipe ou papel abaixo do
  da rota, 403 `forbidden`. O papel mínimo de cada rota está na tabela; o administrador
  passa em todas.
- Uma rota que lança tarefa responde 202 com a tarefa lançada, como a CLI sem `--wait`
  (§6.2), e a tarefa roda em processo destacado
  ([ADR-0007](adr/0007-tarefas-em-processo-destacado.md)).

## 2. Rotas

| Método e caminho | Corpo | Sucesso | Erros próprios | Papel |
|---|---|---|---|---|
| `GET /api/health` | — | 200 `{"status": "ok"}` | — | nenhum |
| `GET /api/me` | — | 200 `{"email", "role"}` | — | assistente |
| `POST /api/sermons` | `{"url"}` | 201 a pregação com `created: true`; 200 com `created: false` se o vídeo já tem pregação | 400 link inválido; 502 `youtube_error` | assistente |
| `GET /api/sermons[?status=]` | — | 200 `{"items"}`, da mais recente para a mais antiga | 400 `status` fora de `created`, `trimmed`, `processing`, `processed`, `failed` | assistente |
| `GET /api/sermons/{id}[?transcript=true]` | — | 200 a pregação de `sermon show`; com `transcript`, também `sentences` | 404 | assistente |
| `PATCH /api/sermons/{id}` | `{"start", "end"}` | 200 a pregação como o `GET` a mostra | 400 bordas fora da live; 404; 409 `sermon_too_short`, `busy` | assistente |
| `POST /api/sermons/{id}/process` | `{"force": false}`, opcional | 202 a tarefa lançada | 404; 409 `sermon_not_trimmed`, `would_discard_edits`, `live_not_finished`, `busy`; 502 `youtube_error` | assistente |
| `POST /api/sermons/{id}/suggest` | `{"preset_id": null}`, opcional | 202 a tarefa lançada | 404 pregação ou preset; 409 `sermon_not_processed`, `llm_not_configured`, `busy` | administrador |
| `GET /api/sermons/{id}/video` | — | 200 o vídeo 16:9 (`video/mp4`), `Content-Disposition: attachment` com o nome `AAAA-MM-DD - Título.mp4` | 404; 409 `sermon_not_processed` | assistente |
| `GET /api/tasks[?status=&kind=]` | — | 200 `{"items"}` de `task list` | 400 `status` fora de `running`, `succeeded`, `failed`; `kind` fora de `process`, `render`, `suggest` | assistente |
| `GET /api/tasks/{id}` | — | 200 a tarefa de `task show` | 404 | assistente |
| `GET /api/tasks/{id}/events` | — | 200 `text/event-stream` (§3) | 404 em JSON, antes de abrir o fluxo | assistente |
| `GET /api/status` | — | 200 `{"lock", "running_tasks"}` de `wordcut status` | — | assistente |

Corpos de entrada:

- `start` e `end` do `PATCH` são obrigatórios, em segundos da live e como número
  (`3730.5`); texto como `"1:02:10"` dá 400. A resposta não traz `needs_reprocess`: numa
  pregação já processada, o estado continua `processed` e as bordas novas valem depois de
  processar de novo com `force`.
- A pregação nasce sem bordas no `POST /api/sermons`; as bordas vão no `PATCH`.

A tarefa lançada (202):

```json
{ "task_id": 9, "kind": "process", "status": "running", "sermon_id": 12 }
```

## 3. Eventos de uma tarefa (SSE)

`GET /api/tasks/{id}/events` é um fluxo [Server-Sent
Events](https://html.spec.whatwg.org/multipage/server-sent-events.html) que acompanha a
tarefa até o fim. O `data` de todo evento é a tarefa em JSON, igual ao corpo de
`GET /api/tasks/{id}`.

| Evento | Quando | O que o `data` traz de útil |
|---|---|---|
| `progress` | a tarefa está `running` e o par `progress`/`progress_message` mudou desde o último evento | `progress` (0 a 1) e `progress_message` |
| `done` | a tarefa terminou `succeeded`; último evento | `result` (por exemplo, `render_id`) |
| `failed` | a tarefa terminou `failed`; último evento | `error`, o objeto de erro da CLI |

```text
event: progress
data: {"id": 9, "kind": "process", "status": "running", "progress": 0.35, "progress_message": "transcrevendo", …}

event: done
data: {"id": 9, "kind": "process", "status": "succeeded", "progress": 1.0, "result": {…}, …}
```

- O servidor fecha o fluxo logo depois do `done` ou do `failed`. Uma tarefa já terminada dá
  o evento final na hora.
- Uma tarefa cujo processo morreu sem gravar o fim termina em `failed` com
  `interrupted`, como na leitura pela CLI (§6.5).
- Sem mudança de progresso, o servidor envia a cada 15 s o comentário `: ping`, que o
  `EventSource` ignora e que mantém o proxy com a conexão aberta.
- O cliente DEVE fechar o `EventSource` ao receber `done` ou `failed`. Sem isso, o
  navegador reconecta sozinho quando o servidor fecha o fluxo e recebe o evento final de
  novo.
- Fechar o fluxo só para o acompanhamento; a tarefa continua no processo dela.

## 4. Esquema OpenAPI

Em desenvolvimento (`WORDCUT_DEV_EMAIL`, sem o Access), o esquema fica em
`/api/openapi.json` e a página dele em `/api/docs`. Com o Access configurado, esses
caminhos dão 404.
