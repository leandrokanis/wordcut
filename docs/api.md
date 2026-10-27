# API HTTP do Wordcut

A API (`apps/api`, FastAPI) expõe à web as mesmas operações da CLI, sobre a mesma camada de
serviço ([ADR-0004](adr/0004-camada-de-servico-no-core.md)). Este documento lista as rotas,
os corpos, os status e os eventos de progresso. As decisões estão na
[ADR-0019](adr/0019-identidade-e-erros-na-api.md), na
[ADR-0020](adr/0020-rotas-e-progresso-por-sse-na-api.md), na
[ADR-0021](adr/0021-rotas-de-cortes-e-administracao-na-api.md) e, para a mídia da timeline,
na [ADR-0025](adr/0025-midia-da-timeline-por-storyboards-e-audio-minimo.md).

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
- Um campo do corpo ou um parâmetro da query que a rota não declara dá 400
  `invalid_argument` com a mensagem "Argumento não reconhecido; veja docs/api.md.", sem
  `details` e sem o nome enviado.
- Os corpos são estritos: número e chave (`true`/`false`) vão como número e booleano do
  JSON, nunca como texto, e um campo opcional enviado não pode ser `null`. Num `PATCH`, só
  os campos enviados mudam. Um campo de escolha fora das escolhas dá 400 com
  `details.choices`.
- Uma rota que não existe dá 404 `not_found`.
- As exportações saem sem `path`, o caminho local que a CLI mostra: a web baixa o arquivo
  por `GET /api/renders/{id}/file`.
- O e-mail de um membro vai só no corpo, nunca no caminho, que os proxies registram.
- Um segredo (chave do LLM, cookies do YouTube) só entra, no corpo `{"value"}`. A resposta
  traz a chave mascarada (`"••••"` e os 4 últimos caracteres) e os cookies só como presentes;
  o valor nunca volta em resposta, erro ou log.
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
| `POST /api/sermons/{id}/prepare` | — | 202 a tarefa `prepare` lançada, que refaz as miniaturas e a forma de onda | 404; 409 `busy` com outra `prepare` da pregação em andamento | assistente |
| `GET /api/sermons/{id}/thumbnails` | — | 200 a faixa de miniaturas (`image/jpeg`), lado a lado na ordem do tempo | 404 pregação inexistente ou miniaturas indisponíveis | assistente |
| `GET /api/sermons/{id}/thumbnails.json` | — | 200 `{"width", "height", "times"}`: tamanho de uma miniatura da faixa e o segundo da live de cada uma | 404 como `thumbnails` | assistente |
| `GET /api/sermons/{id}/waveform` | — | 200 `{"buckets", "peaks"}`: os picos da live inteira, de 0 a 1, na ordem do tempo | 404 pregação inexistente ou forma de onda indisponível | assistente |
| `GET /api/sermons/{id}/video` | — | 200 o vídeo 16:9 (`video/mp4`), `Content-Disposition: attachment` com o nome `AAAA-MM-DD - Título.mp4` | 404; 409 `sermon_not_processed` | assistente |
| `GET /api/tasks[?status=&kind=]` | — | 200 `{"items"}` de `task list` | 400 `status` fora de `running`, `succeeded`, `failed`; `kind` fora de `process`, `render`, `suggest`, `prepare` | assistente |
| `GET /api/tasks/{id}` | — | 200 a tarefa de `task show` | 404 | assistente |
| `GET /api/tasks/{id}/events` | — | 200 `text/event-stream` (§3) | 404 em JSON, antes de abrir o fluxo | assistente |
| `GET /api/status` | — | 200 `{"lock", "running_tasks"}` de `wordcut status` | — | assistente |
| `GET /api/sermons/{id}/cuts[?status=]` | — | 200 `{"items"}` de `cut list`, os descartados por último, cada corte com `start` e `end` (vão dos trechos) e `range_start` e `range_end` (a faixa), em tempo da pregação | 400 `status` fora de `suggested`, `chosen`, `discarded`; 404 | assistente |
| `POST /api/sermons/{id}/cuts` | `{"start", "end", "title"?}`, em segundos da pregação | 201 o corte criado, como o `GET /api/cuts/{id}` o mostra: `chosen`, `source` `admin` | 400 campo desconhecido ou faltando, valor que não é número (título que não é texto), regra de `cut create` (menos de 10 s depois de encostar, fim antes do início, fora da pregação); 404; 409 `sermon_not_processed` | administrador |
| `GET /api/cuts/{id}` | — | 200 o corte de `cut show`, com as exportações sem `path` | 404 | assistente |
| `GET /api/cuts/{id}/preview` | — | 200 a sequência de `cut preview`; nunca espera a trava | 404 | assistente |
| `POST /api/cuts/{id}/choose` | — | 200 o corte como o `GET` o mostra | 404 | assistente |
| `POST /api/cuts/{id}/discard` | — | 200 o corte como o `GET` o mostra | 404 | assistente |
| `POST /api/cuts/{id}/restore` | — | 200 o corte como o `GET` o mostra; um corte não descartado fica como está | 404 | assistente |
| `PUT /api/cuts/{id}/words/{word_id}` | `{"text"}` | 200 `{"cut_id", "word_id", "text", "start", "end", "corrected"}` de `cut fix-word`; o texto original remove a correção | 400 `text` vazio ou com mais de uma palavra, `word_id` fora dos trechos; 404; 409 `spelling_too_different` com `distance`, `limit` e `original` | assistente |
| `PUT /api/cuts/{id}/segments` | `{"segments": [{"from_word", "to_word"}]}` | 200 o corte como o `GET` o mostra, editado | 400 corpo fora do formato ou regra de `cut segments` (lista vazia, palavra fora da faixa ou de outra pregação, trecho invertido, sobreposição); 404 | administrador |
| `PATCH /api/cuts/{id}/range` | `{"start"?, "end"?}` ou `{"by"}` | 200 o corte como o `GET` o mostra, editado | 400 corpo vazio, `by` junto com `start` ou `end`, campo desconhecido, valor que não é número, regra de `cut range`/`cut move` (menos de 10 s depois de encostar, fim antes do início, corte vazio); 404 | administrador |
| `GET /api/cuts/{id}/caption` | — | 200 o estilo da legenda de `cut caption` | 404 | assistente |
| `PATCH /api/cuts/{id}/caption` | campos do estilo | 200 o estilo inteiro | 400 sem campo, valor fora da faixa (`min`, `max`), escolha fora (`choices`), cor fora de `#RRGGBB`; 404 | assistente |
| `DELETE /api/cuts/{id}/caption` | — | 200 o estilo padrão, ligado | 404 | assistente |
| `POST /api/cuts/{id}/renders` | opções da exportação, opcional | 202 a tarefa `render` lançada | 400 opção fora das escolhas; 404; 409 `sermon_not_processed`, `busy` | assistente |
| `GET /api/cuts/{id}/renders/estimate[?opções]` | — | 200 `{"duration", "options"}` de `cut render --estimate`, sem tarefa, sem salvar e sem a trava | 400 opção fora das escolhas; 404 | assistente |
| `GET /api/cuts/{id}/renders` | — | 200 `{"items"}` de `render list`, da mais recente para a mais antiga, sem `path` | 404 | assistente |
| `GET /api/renders/{id}` | — | 200 a exportação de `render show`, sem `path` | 404 | assistente |
| `GET /api/renders/{id}/file` | — | 200 o vídeo 9:16 (`video/mp4`), `Content-Disposition: attachment` com o nome `AAAA-MM-DD - Título do corte.mp4` | 404; 500 `internal_error` se o arquivo sumiu | assistente |
| `GET /api/settings` | — | 200 as configurações de `settings show` | — | administrador |
| `PATCH /api/settings` | `{"llm_model"?, "whisper_model"?}` | 200 as configurações | 400 sem modelo ou modelo em branco | administrador |
| `PUT /api/settings/llm-key` | `{"value"}` | 200 as configurações, com `llm_key` mascarada | 400 `value` vazio; 409 `config_not_writable` | administrador |
| `PUT /api/settings/youtube-cookies` | `{"value"}` | 200 as configurações, com `youtube_cookies: true` | 400 `value` fora do formato Netscape; 409 `config_not_writable` | administrador |
| `GET /api/criteria` | — | 200 `{"items"}` de `criteria list`, sem texto de prompt | — | administrador |
| `GET /api/presets` | — | 200 `{"items"}` de `preset list` | — | administrador |
| `POST /api/presets` | `{"name", "from_id"?}` | 201 o preset criado, cópia de `from_id` ou do padrão, não padrão | 400 nome vazio ou repetido; 404 `from_id` | administrador |
| `GET /api/presets/{id}` | — | 200 o preset de `preset show` | 404 | administrador |
| `PATCH /api/presets/{id}` | campos do preset | 200 o preset | 400 sem campo, nome repetido, critério ou nível inválido (`levels`), duração inválida; 404 | administrador |
| `POST /api/presets/{id}/set-default` | — | 200 o preset, agora o padrão | 404 | administrador |
| `DELETE /api/presets/{id}` | — | 200 `{"id", "deleted": true}` | 404; 409 `default_preset` | administrador |
| `GET /api/members` | — | 200 `{"items"}` de `member list`, por e-mail | — | administrador |
| `POST /api/members` | `{"email", "role"}` | 201 o membro, com o e-mail em minúsculas | 400 e-mail inválido ou já na equipe, `role` fora de `assistant`, `admin` | administrador |
| `POST /api/members/set-role` | `{"email", "role"}` | 200 o membro com o papel novo | 400; 404 e-mail fora da equipe; 409 `last_admin` | administrador |
| `POST /api/members/remove` | `{"email"}` | 200 `{"email", "removed": true}` | 400; 404 e-mail fora da equipe; 409 `last_admin` | administrador |

Corpos de entrada:

- `start` e `end` do `PATCH` são obrigatórios, em segundos da live e como número
  (`3730.5`); texto como `"1:02:10"` dá 400. A resposta não traz `needs_reprocess`: numa
  pregação já processada, o estado continua `processed` e as bordas novas valem depois de
  processar de novo com `force`. Ela traz `borders_changed`, como o `GET`.
- `borders_changed` (booleano, no `GET /api/sermons`, no `GET /api/sermons/{id}` e na
  resposta do `PATCH`): `true` quando a pregação está processada e as bordas atuais diferem
  das usadas no último processamento bem-sucedido ([docs/cli.md](cli.md) §7.2). A web
  oferece Reprocessar no menu Exportar a partir dele.
- A pregação nasce sem bordas no `POST /api/sermons`; as bordas vão no `PATCH`. Uma
  pregação nova já sai com a preparação da timeline lançada ([docs/cli.md](cli.md) §7.7).
- `timeline` (no `GET /api/sermons/{id}` e na resposta do `PATCH`): `{"status", "error",
  "task_id"}`, com `status` `pending` (a tarefa `prepare` em `task_id` roda), `ready` ou
  `failed` (com `error`, mensagem genérica) ([docs/cli.md](cli.md) §7.7). A web acompanha a
  tarefa pelos eventos (§3) e, no fim, lê a pregação de novo e busca as mídias.
- As três rotas de mídia da timeline dão 404 `not_found` enquanto a preparação não terminou,
  quando ela falhou ou, nas miniaturas, quando a live não tem storyboards; nunca 500. As
  respostas não trazem caminho do servidor. A faixa muda quando a timeline é preparada de
  novo: a web acrescenta `?v=` à URL para não reaproveitar a imagem antiga.
- O `GET /api/cuts/{id}` traz `range_sentences`, as frases da faixa com quanto delas o corte
  toca (`included`: `all`, `part`, `none`), como `cut show` ([docs/cli.md](cli.md) §8.2). O
  `PUT .../segments` troca a lista inteira de trechos, com as regras de `cut segments`
  (§8.10); a recusa não grava nada. A aba Texto da web, para o administrador, mostra essas
  frases com uma caixa cada e grava por essa rota.
- O `POST /api/sermons/{id}/cuts` cria um corte do zero com as regras de `cut create`
  ([docs/cli.md](cli.md) §8.8): a faixa encosta em frases, o corte toca todas elas, nasce
  `chosen` com `source` `admin` e a nova sugestão nunca o substitui; a recusa não grava nada.
  No painel de cortes do nível 2, o administrador tem "Novo corte", que cria a faixa de 60 s a
  partir do cursor (em tempo da pregação), terminando no fim da pregação quando faltam menos
  de 60 s e recuando o início para manter 10 s; com a resposta, a web abre o nível do corte.
  O assistente não vê o botão.
- O `PATCH .../range` redimensiona a faixa com `start` e `end` (um deles basta; o outro fica)
  ou a move com `by`, em segundos da pregação e como número, com as regras de `cut range` e
  `cut move` ([docs/cli.md](cli.md) §8.9); a recusa não grava nada. Na timeline do nível 2, o
  administrador arrasta as bordas (`start` e `end`) ou o meio (`by`) da camada de um corte
  não descartado, com prévia local; grava ao soltar e, se a API recusar, a camada volta e o
  erro aparece. Um toque sem arrastar (até 3 px) abre o corte não descartado, para qualquer
  papel; a camada de um corte descartado não abre, como o cartão do painel.
- O `PATCH` da legenda aceita `enabled` (booleano), `font`, `color` e `border_color`
  (`#RRGGBB`), `position` (`top`, `center`, `bottom`), `shadow` (`none`, `soft`, `strong`)
  e `size`, `offset` e `border` (inteiros), com os nomes e as faixas de `cut caption`
  ([docs/cli.md](cli.md) §8.6). Sem nenhum campo, dá 400 e não grava nada.
- As opções da exportação são `fillers`, `stammers`, `pauses`, `resolution` e `quality`
  (texto) e `smooth_joins`, `fade`, `normalize` e `caption` (booleanos), com as escolhas de
  `cut render` (§8.7). No `POST`, a opção omitida repete a última salva no corte, e
  `caption` liga ou desliga a legenda como `cut caption --on/--off`. Na estimativa, as
  mesmas opções vão na query, com os booleanos como `true` ou `false`
  (`?fade=false&pauses=short`).
- O `PATCH` do preset aceita `name`, `levels` (objeto `{"<critério>": "<nível>"}`, que muda
  só os critérios citados), `duration_allowed` e `duration_ideal` (`{"min", "max"}` em
  segundos inteiros), `reorder`, `protected_words` (lista) e `instructions`, no formato do
  `GET`.
- Os segredos vão em `{"value"}`: a chave do LLM sem os brancos em volta e os cookies no
  formato Netscape (`cookies.txt`), inteiros. No Docker Compose, a pasta de segredos é
  montada só para leitura na `api` ([ADR-0003](adr/0003-docker-compose.md)), e essas duas
  rotas dão 409 `config_not_writable`, com mensagem genérica e sem `details`: a API não mostra
  caminho do servidor. Nesse caso, grave o segredo pela CLI no host
  (`wordcut settings set-key < chave.txt`, `wordcut settings set-cookies < cookies.txt`).

A tarefa lançada (202):

```json
{ "task_id": 9, "kind": "process", "status": "running", "sermon_id": 12 }
{ "task_id": 10, "kind": "render", "status": "running", "cut_id": 34 }
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
