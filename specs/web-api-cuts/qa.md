# QA — web-api-cuts — Rotas da API para cortes, exportações, configurações, presets e equipe

## Plano de QA — 2026-10-26

**baseline_commit**: 7c8f45015d38e76a8ef8679e9f0b0cd8881f1abd
**Componentes em escopo**: `apps/api`: `routes/cuts.py`, `routes/renders.py`,
`routes/settings.py`, `routes/presets.py` e `routes/members.py` novos; `routes/__init__.py`
(lista de routers, L1); `app.py`; `errors.py` se a L7 for adotada; `routes/{sermons,tasks,status}.py`
só para mover a identidade para a inclusão (L1); os testes novos, `tests/conftest.py`
(fixtures de corte e exportação, L9) e `tests/test_auth.py` (varredura, L1). Documentação:
`docs/api.md`, `CHANGELOG.md`, `docs/architecture/README.md` §4 e fluxo 5.3, e uma ADR nova com
entrada no índice e no README (L10). `packages/core` fica fora: só leitura, e mudança nele
exige justificativa no plano. `compose.yaml` também fica fora (L5).
**Suítes que valem como prova**:

| Componente | Comando |
|---|---|
| API (passos 1–4) | `uv run pytest apps/api/tests -q` |
| Um arquivo | `uv run pytest apps/api/tests/<arquivo> -q` |
| Monorepo inteiro (regressão) | `uv run pytest -q` |
| Checagem estática | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

**Fontes da barra**: `spec.md` e `plan.md` desta pasta, inclusive a decisão "Identidade
estrutural"; a tabela de permissões da feature 1.2.a
(`docs/requirements/features/1.2.a-team-and-roles.md`); `docs/cli.md` §5, §8.1–§8.7, §9, §11,
§12 e §16; `docs/api.md`; ADR-0003, ADR-0015, ADR-0017, ADR-0019 e ADR-0020; o código do 20a
(`apps/api/src/wordcut_api/{app,auth,deps,errors}.py`, `routes/*`, `tests/conftest.py`,
`tests/test_auth.py`) e os serviços
`packages/core/src/wordcut/service/{cuts,rendering,renders,settings,presets,members,tasks}.py`.
Sem rastreador: os critérios saem dos cenários do spec e da Verificação do plano.

**Regras da barra** (valem para todos os passos):

- Teste de comportamento por HTTP: `TestClient` sobre `create_app(settings=…)`, com as
  fixtures `assistant` e `admin` do `tests/conftest.py`. Os membros entram por
  `service.members.add_member`, nunca por SQL. E-mails fictícios (`@exemplo.org`).
- "Corpo igual ao JSON da CLI" se prova comparando a resposta com a função de serviço que a
  CLI chama, sobre o mesmo banco e no formato que a CLI imprime. Exemplos desse formato:
  `{"items": …}` em `criteria`, `presets` e `members`; `launched_task` no 202; `show_settings`
  depois de gravar um segredo. Os testes da API não importam `wordcut_cli`. A exceção acordada
  é o `path` das exportações (L3).
- Pregação, transcrição, corte e exportação de teste são criados pelos repositórios
  (`db.sermons`, `db.transcripts`, `db.cuts`, `db.renders`), com o arquivo de vídeo em
  `WORDCUT_HOME`, como em `apps/cli/tests/test_cut_render_command.py` (L9).
- Nada de rede nem de renderização real: `no_network`, `no_real_rendering`,
  `no_real_processing`, `no_real_llm` e `no_real_youtube` continuam autouse. Todo teste que
  espera 202 de `POST /api/cuts/{id}/renders` usa `harmless_tasks` e confere a lista de
  processos. Nenhum teste lança um `render` destacado real com `detached_tasks`: a guarda da
  ADR-0017 não cobre `rendering.default_gateways` no processo filho (L9).
- Segredos fictícios, longos e únicos (ex.: `sk-or-v1-ficticia-…-WXYZ` e um `cookies.txt`
  com valor `valor-ficticio-…`). A procura vai no corpo e nos cabeçalhos de toda resposta e
  no `caplog` em nível DEBUG. Procura-se o valor inteiro, porque a máscara mostra os 4
  últimos caracteres de propósito (feature 2.1.a).
- Teste que usa `lock_owner` ou `harmless_tasks` já puxa o `time_limit` (20 s).
- Mutação manual, desfeita na hora, nas linhas 🧬 do `tdd.md`. Mutação que sobrevive é
  achado (PARCIAL do passo).
- Um passo que dependa de uma lacuna (L1–L11) não resolvida fica PARCIAL, salvo se o
  `plan.md` registrar outra decisão antes da Rodada 1. Nesse caso, vale a decisão
  registrada.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Cortes | (a) `GET /api/sermons/{id}/cuts[?status=]` devolve `{"items"}` igual a `list_cuts`, com os descartados por último. `?status` fora de `CUT_STATES` → 400 `invalid_argument` com `details.argument` e `details.choices`, sem repetir o valor. Pregação inexistente → 404 com `details.sermon_id`. (b) `GET /api/cuts/{id}` é igual a `show_cut(…, home=deps.home())`, sem o `path` das exportações (L3). Inexistente → 404 com `details.cut_id`. ID não inteiro → 400 sem eco. (c) `GET /api/cuts/{id}/preview` é igual a `preview_cut` e responde 200 com a trava ocupada (`lock_owner`). (d) `POST /api/cuts/{id}/choose`, `/discard` e `/restore` → 200 com o corte de `show_cut`, igual ao `GET` seguinte. Os `segments` não mudam (constituição §I). `restore` de corte não descartado mantém o estado. (e) `PUT /api/cuts/{id}/words/{word_id} {"text"}` → 200 com `{cut_id, word_id, text, start, end, corrected}`, igual a `fix_word`. O texto aparece corrigido no `GET` do corte e na prévia. Grafia distante → 409 `spelling_too_different` com `details` `distance`, `limit` e `original`, sem mudar nada. O texto original remove a correção. Texto vazio ou com duas palavras → 400 com `argument: "text"`. Palavra fora dos trechos → 400 com `argument: "word_id"`. O texto digitado nunca aparece no erro (ADR-0015). (f) `GET /api/cuts/{id}/caption` é igual a `caption_of`. `PATCH` com parte dos campos → 200 com o estilo inteiro, igual a `update_caption`. Valor fora da faixa → 400 com `details.min` e `details.max`, sem gravar nada. Fonte, posição ou sombra fora → 400 com `choices`. `{}` → 400 sem marcar o corte editado (L6). Campo desconhecido → 400 sem eco (L7). Tipo errado (`"size": "72"`) → 400, nunca 500. `DELETE` → 200 com o estilo padrão ligado. (g) Correção, legenda e transições respondem 200 com a trava ocupada. O assistente passa em todas. | `uv run pytest apps/api/tests/test_cuts_routes.py -q`. 🧬 `discard` ligado a `choose_cut`; `?status` ignorado; `PATCH {}` gravando e marcando o corte editado; texto digitado repetido no erro; `DELETE` da legenda sem chamar `reset_caption`; `show_cut` sem o `path` removido (L3). |
| 2 — Exportações | (a) `POST /api/cuts/{id}/renders` com corpo opcional → 202 com exatamente `{"task_id", "kind": "render", "status": "running", "cut_id"}` (`launched_task`), um processo em `harmless_tasks` e a tarefa achada em `GET /api/tasks/{task_id}`. As opções ficam no corte (`render_options` do `GET` do corte). `"caption": false` desliga a legenda e marca o corte editado. Corpo vazio repete as últimas opções salvas. (b) Opção fora das escolhas → 400 com `details.argument` e `choices`, sem tarefa e sem gravar nada. Campo desconhecido → 400 sem eco (L7). (c) Máquina ocupada → 409 `busy` com `details` da dona. Nenhuma tarefa gravada, nenhum processo novo, opções e legenda do corte sem mudança. (d) Pregação não processada → 409 `sermon_not_processed`. Corte inexistente → 404. (e) `GET /api/cuts/{id}/renders/estimate?…` é igual a `estimate_render` com as mesmas opções (`fade=false`, `pauses=short`). `GET /api/tasks` continua vazio, o `render_options` do corte não muda e a rota responde 200 com a trava ocupada. Opção fora na query → 400 com `choices`. Parâmetro desconhecido → 400 sem eco (L7). (f) `GET /api/cuts/{id}/renders` é igual a `list_renders`, da mais recente para a mais antiga. `GET /api/renders/{id}` é igual a `show_render`. Os dois vêm sem `path` (L3). Inexistente → 404 com `details.render_id` ou `details.cut_id`. (g) `GET /api/renders/{id}/file` → 200, bytes iguais aos do arquivo, `video/mp4` e `Content-Disposition: attachment` com `AAAA-MM-DD - Título do corte.mp4`. Título acentuado sai em `filename*=utf-8''…`. Arquivo ausente → 500 `internal_error` com `details.render_id`, sem caminho. Responde 200 com a trava ocupada. | `uv run pytest apps/api/tests/test_renders_routes.py -q`. 🧬 `detach=False` (a tarefa roda na requisição e bate em `no_real_rendering`); 202→200; corpo de opções descartado antes de `start_render`; estimativa chamando `start_render`; `filename` trocado pelo caminho interno; `path` vazando na resposta. |
| 3 — Administração | (a) `GET /api/settings` é igual a `show_settings`. `PATCH {"llm_model"?, "whisper_model"?}` é igual a `update_settings`. `{}` ou modelo em branco → 400 do serviço. (b) `PUT /api/settings/llm-key {"value"}` → 200 com `show_settings`, e `llm_key` é `"••••"` com os 4 últimos caracteres. O valor fictício inteiro não aparece em corpo, cabeçalho nem log. O arquivo da chave guarda o valor sem os brancos, com permissão 600. Valor vazio → 400 com `argument: "value"` (L5), sem eco. Pasta de configuração só leitura → 409 `config_not_writable`, sem o valor (L5). (c) `PUT /api/settings/youtube-cookies {"value"}` → 200 com `youtube_cookies: true`. Nenhuma linha nem valor de cookie aparece em resposta ou log. Formato fora do Netscape → 400 sem eco. (d) `GET /api/criteria` → `{"items": list_criteria()}`, cada item só com `id`, `name`, `type` e `default_level`, sem texto de prompt. (e) Presets: `GET /api/presets` → `{"items"}`. `GET /api/presets/{id}` é igual a `show_preset`. `POST /api/presets {"name", "from_id"?}` → 201 com a cópia, que não é padrão; `from_id` inexistente → 404 com `details.preset_id`. `PATCH /api/presets/{id}` com os campos no formato da saída (`levels`, `duration_*` como `{"min", "max"}`, `reorder`, `protected_words`, `instructions`) é igual a `update_preset`. `{}`, nome repetido, critério inexistente e duração ideal fora da permitida → 400 sem eco. `POST /api/presets/{id}/set-default` → 200, e o padrão anterior deixa de ser. `DELETE /api/presets/{id}` → 200 `{"id", "deleted": true}`; apagar o padrão → 409 `default_preset`. (f) Membros (L4): `GET /api/members` → `{"items"}` em ordem de e-mail. Incluir → 201 com o e-mail em minúsculas. E-mail repetido → 400. E-mail malformado → 400 sem eco. Papel fora → 400 com `choices`. Trocar o papel → 200. Remover → `{"email", "removed": true}`. Rebaixar ou remover o último administrador → 409 `last_admin`. E-mail fora da equipe → 404 sem eco. O e-mail nunca vai na URL. | `uv run pytest apps/api/tests/test_settings_routes.py apps/api/tests/test_presets_routes.py apps/api/tests/test_members_routes.py -q`. Pasta só leitura: `chmod` em `wordcut_config`, como em `apps/cli/tests/test_settings_command.py`. 🧬 o corpo do `PUT` devolvido ou logado; `store_llm_key` não chamado (o teste lê o arquivo); `from_id` ignorado; `set-default` sem efeito; `whisper_model` ignorado no `PATCH`. |
| 4 — Permissões | (a) `test_permissions.py` tem uma tabela `(método, caminho) → papel mínimo`. O conjunto da tabela é **igual** ao das rotas de `routes.ROUTERS` mais `/api/me`: nenhuma rota fica fora e nenhuma linha sobra. Isso também prova que não existe rota de edição de conteúdo (`segments`, `range`, `move`, criar ou apagar corte). (b) Sem identidade (`ApiSettings()`) → 401 em toda rota da tabela, inclusive nas que estiverem fora do OpenAPI (L1). (c) O assistente recebe 403 `forbidden` em toda rota de administrador, também com ID inexistente, sem efeito colateral: nada de arquivo de segredo, preset, membro ou configuração novos. (d) O assistente passa (nem 401 nem 403) nas rotas de assistente, e o administrador passa em todas. (e) O app não inclui router fora de `ROUTERS`: as entradas de `app.routes` que não são `APIRoute` somam `len(ROUTERS)` (L1). | `uv run pytest apps/api/tests/test_permissions.py apps/api/tests/test_auth.py -q`. 🧬 tirar a identidade da inclusão (401 vira outro status); tirar `require("admin")` de members, presets ou settings; criar uma rota `include_in_schema=False` sem identidade num router fora de `ROUTERS`; criar uma rota num router de admin sem linha na tabela. As quatro devem ficar vermelhas. |
| 5 — Documentação | `docs/api.md` lista cada rota deste item com método, caminho, corpo, status de sucesso, erros próprios e papel mínimo. Registra também: segredos só pelo corpo e nunca devolvidos; exportação sem `path` (L3); e-mail fora da URL (L4); `config_not_writable` no Compose (L5); campo desconhecido → 400 (L7). `CHANGELOG.md` em `[Não lançado] › Adicionado`. `docs/architecture/README.md` §4, linha API, com as rotas novas e sem "planejadas (item 20b)"; o fluxo 5.3 segue coerente. ADR nova para as decisões L1, L3, L4 e L7, com entrada no índice e no README (L10). ADR-0019 e ADR-0020 intocadas. Nenhum nome nem e-mail real. | Leitura de `git diff 7c8f450 -- docs CHANGELOG.md README.md`. |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário: escolher e ajustar um corte (assistente: `choose`, `PUT …/words/{word_id}`, `PATCH …/caption`; 409 `spelling_too_different`) | Passo 1 (d), (e), (f) com o cliente `assistant` |
| Cenário: exportar (202 com a tarefa; estimativa sem tarefa) | Passo 2 (a), (e) |
| Cenário: baixar exportação com nome legível | Passo 2 (g) |
| Cenário: configurações e equipe só para administrador (403 para o assistente; o administrador recebe o JSON da CLI) | Passo 4 (c), (d); passo 3 (a)–(f), comparando com o serviço |
| Borda: `llm-key` e `youtube-cookies` pelo corpo, resposta só com máscara ou presença | Passo 3 (b), (c); passo 4 (c), que mostra que o 403 não grava |
| Borda: sem edição de conteúdo nesta onda | Passo 4 (a): a tabela é igual às rotas do app. `PUT /api/cuts/{id}/segments` → 404 `not_found` |
| Borda: testes sem rede e sem renderização real | Guardas autouse da raiz e `no_real_youtube`; todo 202 de exportação com `harmless_tasks`; nenhum `detached_tasks` de `render` (leitura dos testes) |
| FR-001 — rotas de cortes | Passos 1 e 2 (a)–(e) |
| FR-002 — rotas de exportações | Passo 2 (f), (g) |
| FR-003 — rotas de administração | Passo 3 |
| FR-004 — corpos iguais ao JSON da CLI; segredos nunca devolvidos | Comparação com o serviço em todos os arquivos de rotas; passo 3 (b), (c); exceção do `path` documentada (L3) |
| FR-005 — permissões da 1.2.a | Passo 4 |
| Verificação: cada rota devolve o JSON da CLI; erros com o status do item 19 | Passos 1–3 (comparação com o serviço; 400, 404, 409 e 500 conferidos pelo `code` e pelo status) |
| Verificação: exportar → 202; estimativa sem tarefa; arquivo com nome legível | Passo 2 (a), (e), (g) |
| Verificação: segredos nunca devolvidos (procura do valor fictício nas respostas) | Passo 3 (b), (c), com a procura nos corpos, cabeçalhos e `caplog`; erros 400 e 409 incluídos |
| Verificação: assistente recebe 403 em toda rota de admin; admin passa | Passo 4 (c), (d) |
| Verificação: sem rede, sem renderização real; quality gates limpos | `uv run pytest -q`, `ruff check`, `ruff format --check` e `mypy` verdes; regras da barra |

### Lacunas do plano (escrito antes dos itens 19 e 20a)

- **L1 — Identidade estrutural contra o padrão do 20a.** O plano manda incluir cada router com
  `dependencies=[Depends(current_member)]` e varrer também as rotas fora do OpenAPI. O 20a
  declara a identidade no `APIRouter(...)` de cada módulo. No FastAPI 0.162,
  `app.routes` traz `_IncludedRouter` (API privada) no lugar das rotas incluídas, e a
  varredura de `test_auth.py` lê o OpenAPI. Por isso uma rota com `include_in_schema=False`
  escapa, e foi esse o risco que o roadmap passou para o 20b. **Recomendação**:
  - `routes/__init__.py` exporta `ROUTERS`, com os oito routers;
  - `app.py` inclui todos num laço com `dependencies=[Depends(current_member)]`;
  - a identidade sai dos construtores do 20a e fica num lugar só, para a mutação que a tira
    da inclusão morrer;
  - os routers de administrador declaram `require("admin")` no próprio `APIRouter`;
  - a varredura percorre as `APIRoute` de cada router de `ROUTERS`, que já trazem o prefixo,
    em vez do OpenAPI;
  - um teste exige que as entradas de `app.routes` que não são `APIRoute` somem
    `len(ROUTERS)`, para nenhum router ser incluído fora do laço.
- **L2 — Papel das leituras de presets e critérios.** O spec diz `/api/presets` (escrita) para
  o 403, e isso deixa a leitura ambígua. A tabela da 1.2.a ("Configurações e equipe") e
  `docs/cli.md` §11 ("Todos os comandos desta seção são do administrador") dizem
  administrador. O assistente não usa preset, porque `suggest` é só do administrador.
  **Recomendação** (a mais conservadora): todas as rotas de `/api/settings`, `/api/criteria`,
  `/api/presets` e `/api/members` são de administrador, leitura incluída.
- **L3 — `path` absoluto nas exportações.** `shown_render` devolve o caminho local absoluto
  (`/data/media/…` no contêiner) em `render show`, `render list` e em `renders` de
  `cut show`. As transições devolvem o corte com esse mesmo `renders`. Na CLI o caminho faz
  sentido, porque ela roda no servidor (§9). Na web é estrutura interna: os specs 1.1.d.1 e
  1.1.i.1 tiram esse caminho até das mensagens, e o JSON de pregação não o expõe.
  **Recomendação**: a API tira `path` de todo objeto de exportação, como o 20a tirou
  `needs_reprocess`. A web baixa por `GET /api/renders/{id}/file`. Barra: nenhuma resposta
  contém `str(wordcut_home)`.
- **L4 — E-mail na URL.** "CRUD" de `/api/members` levaria a `PATCH` e `DELETE
  /api/members/{email}`. O uvicorn do contêiner registra o caminho no log de acesso
  (`docker/python/Dockerfile` sem `--no-access-log`), e o nginx e o Cloudflare também
  registram. É dado pessoal em log (LGPD, constituição §VI). **Recomendação**: o e-mail vai só
  no corpo:
  - `POST /api/members {"email", "role"}` → 201;
  - `POST /api/members/set-role {"email", "role"}` → 200;
  - `POST /api/members/remove {"email"}` → 200.

  Isso segue os verbos da CLI e a regra do plano de `POST` para ação, como no `set-default`.
- **L5 — Segredo numa pasta só leitura.** A ADR-0003 e o `compose.yaml`
  (`${HOME}/.config/wordcut:/config:ro`) montam os segredos só para leitura na `api`. Assim,
  `PUT /api/settings/llm-key` e `PUT /api/settings/youtube-cookies` dão sempre 409
  `config_not_writable` no deploy. O plano não trata disso. **Recomendação**:
  - não mudar a montagem neste item, porque isso muda a postura de segurança e pede ADR e
    decisão humana;
  - a rota existe, devolve o 409 sem o segredo, e um teste prova isso com a pasta sem
    escrita;
  - o `docs/api.md` registra que, no Compose, o segredo se grava pela CLI no host.

  Ponto menor da mesma rota: o serviço dá `details.argument` `"key"` ou `"cookies"`, mas o
  corpo tem `value`. A rota deve renomear para `value`, como a CLI renomeia os argumentos do
  preset. A resposta de sucesso é `show_settings`, a mesma de `settings set-key --json`.
- **L6 — Corpos de entrada não fixados.** O plano decide só `{"value"}` dos segredos.
  **Recomendação**:
  - a entrada tem o formato da saída e os nomes do serviço: legenda (`enabled`, `font`,
    `size`, `color`, `position`, `offset`, `border`, `border_color`, `shadow`); opções da
    exportação (`fillers`, …, `caption`); preset (`levels` como objeto, `duration_*` como
    `{"min", "max"}`, `protected_words` como lista, `instructions`); `{"name", "from_id"?}`
    na criação; `{"text"}` na correção; `{"llm_model"?, "whisper_model"?}` nas
    configurações;
  - os modelos usam `extra="forbid"` e tipos estritos (`StrictInt`, `StrictBool`). Sem
    isso, um `"size": "72"` repassado como veio, ou um campo desconhecido, chega a
    `caption.validated` e dá `TypeError`, ou seja, 500;
  - um campo de escolha no corpo (`role`, `position`, `fillers`…) é tipado `str`, para o erro
    vir do serviço com `details.choices`. O `errors._choices` do 20a só lê `Literal` de query
    e de caminho;
  - `model_dump(exclude_unset=True)` e `null` recusado;
  - `PATCH` de legenda `{}` dá 400. Hoje `update_caption(…, {})` grava e marca o corte
    editado;
  - no preset, `details.argument` `level` vira `levels`.
- **L7 — Campo desconhecido repetido no erro.** Com `extra="forbid"`, o pydantic devolve
  `extra_forbidden` com o nome do campo em `loc`, e `errors.invalid_argument` o põe em
  `details.argument`. Isso repete um nome digitado, o que a ADR-0015 proíbe ("nem como nome de
  opção"). Conferido no baseline: `{"a": 1, "segredo-digitado": 1}` num modelo com
  `extra="forbid"` responde `Valor inválido para segredo-digitado.`, com
  `details.argument: "segredo-digitado"`. O mesmo vale para um parâmetro desconhecido na query
  da estimativa.
  **Recomendação**: `errors.py` trata `extra_forbidden` como argumento não reconhecido
  (`invalid_argument`, "Argumento não reconhecido; veja docs/api.md.", sem `details`). A
  estimativa lê a query por um modelo com `extra="forbid"`.
- **L8 — Status de sucesso não fixados.** **Recomendação**:
  - 201 em `POST /api/presets` e na inclusão de membro, como em `POST /api/sermons`;
  - 200 com corpo em `DELETE /api/cuts/{id}/caption` (o estilo padrão) e em
    `DELETE /api/presets/{id}` (`{"id", "deleted": true}`), nunca 204;
  - 200 com `show_cut` nas transições;
  - 202 só na exportação.
- **L9 — Fixtures e renderização real.** A guarda da ADR-0017 cobre só as fábricas de
  processamento e de sugestão. Um `render` destacado real (`detached_tasks`) montaria
  `rendering.default_gateways` de verdade no processo filho, e rodaria ffmpeg e OpenCV.
  **Recomendação**:
  - toda exportação 202 nos testes usa `harmless_tasks`;
  - nenhum teste usa `detached_tasks` com `render`;
  - o `tests/conftest.py` da API ganha fixtures de pregação processada, transcrição, corte e
    exportação, criados pelos repositórios, sem importar os testes da CLI.
- **L10 — ADR ausente no passo 5.** As decisões L1, L3, L4, L5 e L7 são de arquitetura e mudam
  o que a ADR-0020 diz das respostas e da identidade. ADR aceita não se edita
  (CONTRIBUTING). **Recomendação**: uma ADR-0021 com entrada no índice e atualização de
  `docs/architecture/README.md` e do README no mesmo commit (CLAUDE.md).
- **L11 — Contexto de código incompleto.** O plano lista só arquivos novos, `app.py` e docs.
  **Recomendação**: incluir `routes/__init__.py` (L1), `errors.py` (L7), `tests/conftest.py`
  (L9), `tests/test_auth.py` (a varredura atual pelo OpenAPI passa para `ROUTERS` ou fica
  como redundante) e `routes/{sermons,tasks,status}.py` (L1).
- **Nota (não é lacuna)**: o FastAPI resolve as dependências antes de validar o corpo
  (conferido no baseline com FastAPI 0.162: 403 com corpo inválido no esquema, 400 com JSON
  malformado). Assim
  o 401/403 vem antes do 400 de um corpo válido em JSON e inválido no esquema. Um JSON
  malformado dá 400 antes da identidade, sem revelar nada. Nos testes de permissão, o corpo
  deve ser JSON válido.

## Rodada 1 — 2026-10-26 — working tree sobre 7c8f450

**baseline_commit**: 7c8f45015d38e76a8ef8679e9f0b0cd8881f1abd
**Componentes avaliados**: `apps/api` (routes `cuts`, `renders`, `settings`, `presets`,
`members`, `__init__`; `app.py`, `bodies.py`, `errors.py`; testes novos, `conftest.py`,
`test_auth.py`); documentação (`docs/api.md`, `CHANGELOG.md`, `README.md`,
`docs/architecture/README.md`, ADR-0021 e índice).
**Suítes**: monorepo ✅ (1504 / 0 falhas) · API ✅ (232 / 0 falhas) · ruff check ✅ ·
ruff format --check ✅ · mypy ✅
**Mutações** (cópia no scratchpad, desfeitas): 15 de 15 mortas, inclusive identidade fora
da inclusão, `require("admin")` fora de presets e settings, L7 desligada, `path` mantido
nas transições e na lista de exportações, `null` aceito nos corpos e `StrictInt` afrouxado.
A mutação `detach=False` não foi repetida pelo QA (renderização real proibida nesta rodada);
vale o registro do implementador no `tdd.md`.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Cortes | PASS | `test_cuts_routes.py`; comparação com `list_cuts`, `show_cut`, `preview_cut`, `fix_word`, `caption_of`, `update_caption`; `PATCH {}` 400 sem marcar editado; `str(home.root)` ausente; mutações de status, restore, `path` e `StrictInt` mortas |
| 2 — Exportações | PASS | `test_renders_routes.py`; todo `POST …/renders` com `harmless_tasks`; nenhum `detached_tasks` de `render`; estimativa sem tarefa e com a trava ocupada; download com `filename*`; `path` ausente (mutação morta) |
| 3 — Administração | PASS | `test_settings_routes.py`, `test_presets_routes.py`, `test_members_routes.py`; valor fictício procurado em corpo, cabeçalhos e `caplog`; `value` em `details.argument`; e-mail só no corpo. Achado fora da matriz: ver Observação |
| 4 — Permissões | PASS | `test_permissions.py`: tabela igual às `APIRoute` de `ROUTERS` + `/api/me`; 401 em toda linha; assistente 403 sem efeito com ID existente e inexistente; contagem de `app.routes` igual a `len(ROUTERS)`; mutações de identidade e de `require("admin")` mortas |
| 5 — Documentação | PASS | `git diff 7c8f450 -- docs CHANGELOG.md README.md`: rotas com corpo, status, erros e papel; L3, L4, L5 e L7 registradas; ADR-0021 no índice; ADR-0019 e ADR-0020 sem diff; só `@exemplo.org` |

### Critérios de aceite
- ✅ Escolher e ajustar um corte (assistente; 409 `spelling_too_different`) — `test_cuts_routes.py`
- ✅ Exportar (202 com a tarefa; estimativa sem tarefa) — `test_renders_routes.py`
- ✅ Baixar exportação com nome legível — `test_the_file_of_an_export_downloads_with_the_readable_name_even_with_the_lock_held`
- ✅ Configurações e equipe só para administrador — `test_permissions.py` e testes de admin comparando com o serviço
- ✅ Segredos pelo corpo, resposta só com máscara ou presença — `test_settings_routes.py`; 403 sem gravar em `test_permissions.py`
- ✅ Sem edição de conteúdo nesta onda — tabela igual às rotas; `PUT /api/cuts/1/segments` → 404
- ✅ Testes sem rede e sem renderização real — guardas autouse; `harmless_tasks` em todo 202
- ✅ FR-001 a FR-005 — passos 1 a 4
- ✅ Verificação do plano (JSON da CLI, 202, segredos, 403, quality gates) — suítes e checagens verdes

### Observação (fora da matriz; não muda o veredito)
`PUT /api/settings/llm-key` e `/youtube-cookies` com a pasta só leitura respondem 409
`config_not_writable` com o caminho absoluto da pasta de configuração na mensagem e em
`details.path` (vem de `packages/core/src/wordcut/config.py:81-84`; conferido por sonda na
cópia do scratchpad). Só o administrador alcança a rota, e no Compose o valor é `/config`.
A matriz do passo 3 (b) exige só "sem o valor", então o passo fica PASS; mas a ADR-0021
(Consequências: "A web nunca vê a estrutura de pastas do servidor") e o espírito da L3
ficam desmentidos. Decisão humana: tirar o caminho na rota ou ajustar a ADR.

### Veredito geral: PASS
Todos os passos PASS pela matriz, critérios cobertos, suítes e checagens verdes; um achado
de caminho interno no 409 de segredo fica para decisão (fora da barra).

## Rodada 2 — 2026-10-26 — working tree sobre 7c8f450

**baseline_commit**: 7c8f45015d38e76a8ef8679e9f0b0cd8881f1abd
**Componentes avaliados**: `apps/api` (`routes/settings.py`, `tests/test_settings_routes.py`);
documentação (`docs/api.md`, ADR-0021); regressão no restante.
**Barra adicional**: decisão L5b do orquestrador (`plan.md`, Decisões técnicas). O 409
`config_not_writable` sai com mensagem genérica, sem `details` e sem caminho do servidor, e a
mutação que repassa o erro do serviço tem que ficar vermelha.
**Suítes**: monorepo ✅ (1506 / 0 falhas) · API ✅ (234 / 0 falhas) · ruff check ✅ ·
ruff format --check ✅ · mypy ✅
**Mutações** (cópia no scratchpad, desfeitas): 4 de 4 mortas em `settings._stored`. Erro do
serviço repassado, `details` do serviço anexado, mensagem do serviço (com o caminho) sem
`details`, e `code` trocado.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Cortes | PASS | sem mudança desde a Rodada 1; suíte verde |
| 2 — Exportações | PASS | sem mudança desde a Rodada 1; suíte verde |
| 3 — Administração | PASS | `routes/settings.py:66-80` troca o 409 pela mensagem da L5b, sem `details`; `test_a_secret_into_a_read_only_folder_never_shows_the_configuration_folder` (llm-key e youtube-cookies) procura `str(wordcut_config)` e `/config` no corpo e nos cabeçalhos, e exige a ausência de `details`; as 4 mutações morreram |
| 4 — Permissões | PASS | sem mudança desde a Rodada 1; suíte verde |
| 5 — Documentação | PASS | `docs/api.md:121` e ADR-0021:44 registram o 409 sem caminho e sem `details` |

### Varredura de caminho do servidor (pedida nesta rodada)
Em `packages/core`, só `config.py:80-84` põe caminho num erro, e a rota agora o limpa. Vídeo
e exportação ausentes respondem sem caminho (`service/sermons.py:199`, `service/renders.py:56`).
O `path` sai de cortes, transições e exportações (`routes/cuts.py:135-143`). Exceção não
prevista vira `UNEXPECTED` genérico (`errors.py:57-59`). Tarefas mostram só `code`, `message`
e `details` gravados pelo serviço, sem caminho. Nenhuma outra resposta com caminho foi
encontrada.

Ponto menor, que não muda o veredito: o teste não fixa o texto exato da mensagem. Uma
mensagem genérica diferente passaria, mas qualquer mensagem com caminho fica vermelha.

### Critérios de aceite
- ✅ Todos os da Rodada 1, com as mesmas evidências; suíte inteira verde
- ✅ Segredos e pastas: 409 sem valor (teste da Rodada 1) e sem caminho (teste novo)

### Veredito geral: PASS
A Observação da Rodada 1 foi resolvida pela L5b, com teste e mutação vermelha. Suítes e
checagens estão verdes.
