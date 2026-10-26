# QA — web-shell — Esqueleto da interface web, lista de pregações e Nova pregação

## Plano de QA — 2026-10-26

**baseline_commit**: a052cd8ddb38006579fd758428c56591592c653b
**Componentes em escopo**: `apps/web` (código e testes); `docs/architecture/README.md` §4 e
`CHANGELOG.md` (passo 5); Python (`packages/core`, `apps/api`, `apps/cli`) só como regressão,
que não pode mudar.
**Suítes que valem como prova**:
- `apps/web`: `npm --prefix apps/web test` (Vitest + Testing Library, jsdom, `fetch` dublê
  com `vi.stubGlobal`); checagem `npm --prefix apps/web run typecheck && npm --prefix apps/web
  run lint && npm --prefix apps/web run build`.
- Regressão Python: `uv run pytest -q`; `uv run ruff check . && uv run ruff format --check .`;
  `uv run mypy`.
- `git diff a052cd8 -- packages apps/api apps/cli` vazio (a issue não toca no servidor).

Fontes da barra: `spec.md`, `plan.md`, "Requisitos gerais de interface" de
`docs/requirements/features.md`, feature 1.1.a, `docs/prototype/wordcut.html` (topbar,
`.crumbs`, `statusbar()`, `level1()`, `modal()`, `:root`), `docs/api.md` §1–§2, ADR-0008,
ADR-0019, ADR-0020, ADR-0021 e o esqueleto em `apps/web/` no baseline.

Regras da barra (valem para todos os passos):
- **Sem rede**: todo teste troca `fetch` por um dublê que responde 404 (ou lança) a URL não
  prevista, para uma chamada esquecida aparecer. Nada de MSW com passthrough, nada de
  `EventSource` real.
- **Corpos reais**: os dublês usam os corpos de `docs/api.md` e da camada de serviço
  (`service/sermons.py::_sermon`/`_listed`, `service/status.py`, `service/tasks.py::shown_task`),
  não formatos inventados. Erros sempre `{"error": {"code", "message", "details"?}}`.
- **Comportamento pela interface**: asserções por papel/texto visível (`getByRole`,
  `findByText`), não por estado interno nem por classe CSS (exceto onde dito).
- **Dados fictícios**, sem nome de pessoa e sem e-mail real (CONTRIBUTING §6, LGPD).
- **Mutação manual** é cobrada onde marcada (🧬): a mutação tem de deixar a suíte vermelha.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Cliente e tipos (`api/client.ts`, `api/types.ts`, erro, 401/403) | (a) sucesso devolve o JSON tipado; (b) resposta não-2xx com `{"error": …}` vira um objeto de erro com `status`, `code`, `message`, `details`; (c) corpo não-JSON (502 HTML do nginx) e `fetch` rejeitado (API fora do ar) viram erro com código próprio (ex.: `network_error`/`unavailable`), nunca exceção crua; (d) 401 `unauthenticated` e 403 `forbidden` são distinguíveis pelo `code`; (e) `POST` envia `Content-Type: application/json` e só os campos declarados (corpos estritos, ADR-0021); (f) `GET /api/me` está no cliente (papel vem dele); (g) os tipos cobrem `SermonListItem` (`id`, `title`, `service_date`, `duration` anulável, `live_duration`, `live_finished`, `status`, `cut_counts`), `SermonCreated` (`_sermon` + `created`, **sem** `duration`/`cut_counts`), `MachineStatus` (`lock.held` + campos do `LockHolder` + `elapsed_seconds`; `running_tasks` de `shown_task`), `Me` (`email`, `role: "assistant" \| "admin"`) | Testes unitários do cliente (`api/client.test.ts`) com `fetch` dublê: um por caso (a)–(f). `typecheck` prova (g). 🧬 trocar `response.ok` por `true` → vermelho; devolver `message` fixa em vez da do corpo → vermelho; remover o `catch` do `fetch` rejeitado → vermelho |
| 2 — Layout e rotas (caminho no topo, rodapé, rotas, tokens, 390 px) | (a) rotas do FR-001 (`/`, `/sermons/:id`, `/cuts/:id`, `/settings`) renderizam o nível certo, com `createMemoryRouter` sobre a mesma tabela de `app/routes.tsx`; (b) `nav` com `aria-label="Caminho"`: em `/` só "Pregações" (atual, `aria-current`); em `/sermons/:id` "Pregações / <título>", com o título de `GET /api/sermons/{id}`; em `/cuts/:id` "Pregações / <pregação> / <corte>", com `GET /api/cuts/{id}` → `sermon_id` → `GET /api/sermons/{sermon_id}`; (c) clicar num item anterior navega ao nível dele; o item atual não é link; (d) a barra de status (rodapé) aparece em todas as rotas, inclusive `/settings`; (e) `tokens.css` declara em `:root` as variáveis do protótipo (`--bg`, `--panel`, `--raised`, `--hover`, `--line`, `--line-2`, `--fg`, `--muted`, `--faint`, `--accent`, `--on-accent`, `--ok`, `--warn`, `--danger`, `--font-ui`, `--font-mono`, `--r`) com os mesmos valores e `color-scheme: dark`; (f) sem fonte nem script de CDN externo; (g) 390 px sem rolagem horizontal | (a)–(d) testes de componente com `MemoryRouter` e `fetch` dublê (`app/Layout.test.tsx`, `app/routes.test.tsx`). (e)–(f) teste que lê `src/ui/tokens.css` como texto (`?raw`) e compara as variáveis com o protótipo; `grep` de `https://` em `index.html`/CSS na revisão. (g) jsdom não mede layout: **verificação manual** em 390 px (DevTools, `vite preview`) registrada na rodada, mais revisão do CSS (sem `width` fixo > 390 px no topo, rodapé e lista; `.crumbs` quebra linha como no `@media (max-width: 860px)` do protótipo). Sem a verificação manual registrada, (g) fica PARCIAL. 🧬 trocar o `to` de "Pregações" por `#` → vermelho |
| 3 — Nível 1 (lista, estado vazio, diálogo com aviso de live no ar) | (a) `GET /api/sermons` → um item por pregação, na ordem da API, com título, data do culto (`service_date` formatada `DD/MM/AAAA`), duração (`duration`, ou indicação "a delimitar" quando `null`) e estado em português; sem prévia, miniatura nem timeline; clicar abre `/sermons/:id`; (b) `{"items": []}` → estado vazio com a ação "Nova pregação"; (c) "Nova pregação" só no nível 1 (ausente em `/sermons/:id`, `/cuts/:id`, `/settings`); (d) diálogo `role="dialog"` com `aria-modal`, título "Nova pregação", campo com rótulo acessível, fecha por botão "Fechar" e por Esc, foco no campo ao abrir; (e) confirmar envia `POST /api/sermons` com corpo exatamente `{"url": "<link>"}`; 201 `created: true` → a pregação aparece na lista (recarregada) com título e data da live; (f) `live_finished: false` → aviso "A live ainda não terminou" visível ao usuário, sem bloquear a criação; (g) 400 `invalid_argument` com `details.argument: "link"` (o código real; o corpo usa `url`) → motivo da API junto ao campo (`aria-describedby`/`aria-invalid`), diálogo aberto, sem duplicar o link digitado na mensagem (ADR-0015); 502 `youtube_error` → mensagem junto ao campo; (h) 200 `created: false` → não duplica a pregação na lista; (i) API fora do ar na lista → mensagem clara, sem tela em branco; (j) botão de confirmar desabilitado durante o envio (sem `POST` duplo) | Testes de componente `features/sermons/SermonList.test.tsx` e `NewSermonDialog.test.tsx` com `userEvent` e `fetch` dublê que registra método, URL e corpo. 🧬 apagar o ramo `live_finished === false` → vermelho; mostrar o erro num toast genérico em vez de junto ao campo → vermelho; trocar `service_date` por `created_at` → vermelho; enviar campo extra no corpo → vermelho |
| 4 — Barra de status e configurações vazias | (a) `lock.held: false` → "Máquina livre"; `lock.held: true` → "Ocupada", o que roda (tipo da tarefa em português, recurso) e há quanto tempo (`elapsed_seconds`), com o progresso (`progress` 0–1 em %) da tarefa de `running_tasks` cujo `id` é o `lock.task_id`; (b) atualiza sozinha: com `vi.useFakeTimers`, avançar 3 s faz nova chamada a `/api/status` e a tela muda de livre para ocupada; (c) o intervalo para ao desmontar (nenhuma chamada após `unmount`); (d) falha de `/api/status` mostra estado "indisponível" e o polling continua (volta a "livre" quando a API volta); (e) `/settings` é tela inteira (sem caminho de níveis e sem lista), com navegação lateral (`nav`) e seções vazias; (f) papel por `GET /api/me`: admin vê a entrada "Configurações" no topo; assistente não vê a entrada e, ao abrir `/settings` direto, recebe tela de acesso negado sem conteúdo; (g) `/api/me` 401 → tela "não identificado" e 403 → tela "fora da equipe", ambas sem dados de pregação (nenhum `GET /api/sermons` disparado ou nenhum dado renderizado) | Testes `features/status/StatusBar.test.tsx` (fake timers) e `features/settings/SettingsPage.test.tsx`, `app/Auth.test.tsx` (ou equivalente) com `fetch` dublê. 🧬 trocar 3000 ms por `Infinity`/remover o `setInterval` → vermelho; remover o `clearInterval` → vermelho; inverter a checagem `role === "admin"` → vermelho; renderizar filhos antes de `/api/me` resolver → vermelho |
| 5 — Documentação | `docs/architecture/README.md` §4, linha "Web", descreve o que existe (rotas, cliente, layout, nível 1, barra de status, configurações vazias) e retira "interface planejada" desta parte; `CHANGELOG.md` em `[Não lançado]` com a entrada; texto em português; sem segredo, e-mail real ou caminho do servidor. Se a implementação tomar decisão de arquitetura nova (ex.: biblioteca de roteamento como dependência de produção), ADR + README no mesmo conjunto (CLAUDE.md) | Leitura do diff de `docs/` e `CHANGELOG.md` contra o código entregue; `git diff a052cd8 -- README.md docs/adr` conferido |

| Critério de aceite | O que o cobre |
|---|---|
| Spec — Cenário "lista de pregações": título, data, duração e estado, sem prévia nem timeline; caminho mostra "Pregações" | Passo 3 (a) + passo 2 (b) — `SermonList.test.tsx`, `Layout.test.tsx` |
| Spec — Cenário "Nova pregação": aparece com título, data e duração da live; aviso se a live não terminou; motivo junto ao campo se o link é inválido | Passo 3 (e), (f), (g) — `NewSermonDialog.test.tsx`. "Duração" na criação = `live_duration` (o `POST` não traz `duration`; ver L1) |
| Spec — Cenário "navegação pelo caminho": volta ao nível pelo caminho; "Nova pregação" só no nível 1 | Passo 2 (b), (c) e passo 3 (c) — `Layout.test.tsx` com `MemoryRouter` em `/cuts/:id` |
| Spec — Cenário "barra de status": livre, ou o que roda e o progresso, atualizado sozinho | Passo 4 (a)–(d) — `StatusBar.test.tsx` com fake timers |
| Spec — Cenário "configurações": admin vê tela inteira com navegação própria; assistente não vê a entrada | Passo 4 (e), (f) — `SettingsPage.test.tsx` e teste do topo com `/api/me` dublê nos dois papéis |
| Borda — API fora do ar: mensagem clara, sem tela em branco | Passo 1 (c) + passo 3 (i) + passo 4 (d) — `fetch` rejeitado e 502 HTML |
| Borda — lista vazia com a ação "Nova pregação" | Passo 3 (b) |
| Borda — 401 / 403: tela explicando, sem dados | Passo 1 (d) + passo 4 (g) |
| Borda — 390 px sem rolagem horizontal | Passo 2 (g) — verificação manual registrada + revisão do CSS |
| FR-001 rotas | Passo 2 (a) |
| FR-002 caminho com três níveis e clique | Passo 2 (b), (c) |
| FR-003 lista e diálogo sobre a API (item 20a) | Passo 3 (a), (e)–(h), com corpos de `docs/api.md` |
| FR-004 barra de status por consulta periódica (e eventos quando houver tarefa) | Passo 4 (a)–(d). A parte "pelos eventos" (SSE) não está no plano (ver L8): sem decisão registrada, fica descoberta |
| FR-005 indicador "Salvo" reutilizável | `ui/Saved.tsx` com teste próprio (`ui/Saved.test.tsx`): aparece ao sinalizar salvamento, `role="status"` `aria-live="polite"` como no protótipo, some depois do tempo (fake timers). Nenhum passo do plano o nomeia (ver L12) |
| FR-006 visual do protótipo, tema escuro | Passo 2 (e), (f) |
| Verificação — Lista renderiza os dados da API; vazio mostra a ação | Passo 3 (a), (b) |
| Verificação — Diálogo cria a pregação; aviso de live no ar; erro junto ao campo | Passo 3 (e), (f), (g) |
| Verificação — Caminho navega entre níveis; "Nova pregação" só no nível 1 | Passo 2 (b), (c); passo 3 (c) |
| Verificação — Barra de status mostra livre/ocupado e atualiza | Passo 4 (a), (b) |
| Verificação — Configurações só para admin; 401/403 com tela própria | Passo 4 (f), (g) |
| Verificação — typecheck, lint, testes e build limpos; suíte Python intacta | Suítes acima, todas verdes; `git diff a052cd8 -- packages apps/api apps/cli` vazio |

### Lacunas do plan.md (o plano é anterior aos itens 19–20b)

Decisões abaixo tomadas pela opção mais conservadora, em execução automatizada aprovada pelo
administrador. A barra acima já as adota; quem implementa pode registrar outra escolha no
`plan.md`, com justificativa, antes do código.

- **L1 — Duração e formato dos corpos.** `GET /api/sermons` traz `duration` (da pregação,
  `null` antes das bordas) e `live_duration`; o `POST` traz só `_sermon` + `created`, sem
  `duration` nem `cut_counts`. Recomendação: dois tipos (`SermonListItem`, `SermonCreated`);
  na lista, `duration` quando houver e "A delimitar" quando `null`; no resultado da criação,
  `live_duration`.
- **L2 — Argumento do link inválido.** O serviço recusa com `details.argument: "link"`, não
  `"url"` (o nome do campo no corpo). Recomendação: associar ao campo qualquer
  `invalid_argument` do `POST /api/sermons` (`link`, `url` ou sem `details`), e
  `youtube_error` (502) também.
- **L3 — `created: false`.** O plano não diz o que acontece com um vídeo que já tem
  pregação. Recomendação: fechar o diálogo, recarregar a lista sem duplicar e avisar que a
  pregação já existia.
- **L4 — Live no ar: API × protótipo.** O protótipo mostra "A live ainda não terminou" como
  erro e não cria; a API cria com `live_finished: false` (o 409 `live_not_finished` só sai no
  processamento). Recomendação: seguir API + spec (cria e mostra aviso, não erro).
- **L5 — Papel.** O plano exige "configurações só para admin" sem dizer de onde vem o papel.
  Recomendação: `GET /api/me` (item 19) no passo 1 e um contexto de identidade carregado
  antes das telas; a rota `/settings` também recusa o assistente, não só esconde a entrada.
  O seletor "Ver como" do protótipo não entra.
- **L6 — 403 de papel × 403 de equipe.** Com a ADR-0019, o 403 serve para "fora da equipe" e
  para "papel abaixo do da rota". Recomendação: a tela de bloqueio sai do resultado de
  `/api/me`; um 403 numa rota de administração vira mensagem local, não tela de bloqueio.
- **L7 — Formato de `/api/status`.** `{"lock": {"held"} | {held, kind, resource, pid,
  started_at, task_id, elapsed_seconds}, "running_tasks": [...]}`. O "quem" do protótipo
  ("· <pessoa>") não existe na API. Uma tarefa `suggest` roda sem a trava (máquina livre com
  tarefa em andamento). Recomendação: sem "quem"; "livre" segue `lock.held`; `suggest`, se
  houver, aparece como segunda informação, sem marcar a máquina ocupada.
- **L8 — FR-004 × plano.** A spec pede status "pelos eventos quando houver tarefa"; o plano
  adia o SSE para a tela que acompanha a tarefa. Recomendação: registrar no `plan.md` (e na
  spec) que o SSE fica para o item 22, e cumprir FR-004 só com o polling de 3 s. Sem esse
  registro, o critério fica descoberto.
- **L9 — Polling testável.** O plano não pede limpeza do intervalo nem comportamento em
  falha. Recomendação: parar ao desmontar, continuar depois de erro, mostrar "indisponível";
  testes com fake timers.
- **L10 — API fora do ar.** O passo 1 não cobre `fetch` rejeitado nem 502 com corpo HTML do
  nginx. Recomendação: o cliente normaliza os dois num erro com código próprio, e a tela
  mostra mensagem clara.
- **L11 — Esqueleto atual.** `src/api.ts` (`fetchHealth`) e `App.test.tsx` existem no
  baseline. O roadmap registra que uma mutação (`setStatus("ok")` fixo) sobreviveu no item 0
  e devia ser coberta na fase 3. Recomendação: apagar `api.ts` e os testes de saúde, ou
  migrá-los para o cliente novo, sem deixar código morto, e cobrir "API indisponível" nos
  testes novos.
- **L12 — Indicador "Salvo" (FR-005).** Está no Contexto de código (`ui/Saved.tsx`), mas em
  nenhum passo. Recomendação: incluí-lo no passo 2, com teste (`role="status"`,
  `aria-live="polite"`, some sozinho).
- **L13 — Miniatura.** Os cards do protótipo têm miniatura; o requisito diz "sem prévia" e a
  API não tem rota de miniatura. Recomendação: sem miniatura.
- **L14 — Confirmação do link.** O protótipo carrega ao colar, sem botão; a spec diz "cola o
  link e confirma". Recomendação: envio por Enter/submit do formulário (com botão visível),
  sem envio automático no `paste`.
- **L15 — Depois de criar.** O protótipo vai direto ao nível 2; a spec diz que a pregação
  aparece na lista. Recomendação: seguir a spec (fechar, recarregar a lista); a ida ao nível
  2 fica para o item 22.
- **L16 — Títulos no caminho.** Os níveis 2 e 3 estão fora de escopo, mas o caminho precisa
  dos títulos. Recomendação: `GET /api/sermons/{id}` e `GET /api/cuts/{id}` → `sermon_id`,
  com páginas-esboço nas rotas; 404 mostra "não encontrada" sem quebrar o layout.
- **L17 — 390 px.** jsdom não mede layout. Recomendação: verificação manual registrada na
  rodada (DevTools a 390 px), mais revisão do CSS; sem ela, o critério fica PARCIAL.
- **L18 — Fontes.** O protótipo usa Geist. Recomendação: sem Google Fonts nem CDN (nenhuma
  chamada a terceiros); a pilha de fallback do `--font-ui`, ou a fonte empacotada no build.
- **L19 — Rótulos de estado.** O plano não mapeia `created`, `trimmed`, `processing`,
  `processed` e `failed`. Recomendação: "A delimitar" (`created`), "Delimitada" (`trimmed`),
  "Processando N%" (`processing`, com o progresso de `/api/status` quando houver), "Pronta"
  (`processed`) e "Falhou" (`failed`), com o tom do protótipo (`warn`/`accent`/`ok`/`danger`).
- **L20 — Documentação.** O passo 5 cita o §4 e o CHANGELOG. Recomendação: se o React Router
  entrar como decisão de arquitetura, a ADR e o README vão no mesmo conjunto (CLAUDE.md); se
  não entrar, registrar no `plan.md` que não há ADR.

## Rodada 1 — 2026-10-26 — working tree sobre a052cd8

**baseline_commit**: a052cd8ddb38006579fd758428c56591592c653b
**Componentes avaliados**: `apps/web`, `docs/` (arquitetura §4, ADR-0022, índice), `README.md`,
`CHANGELOG.md`; Python só como regressão.
**Suítes**: web ✅ (63 / 0 falhas) · typecheck ✅ · lint ✅ · build ✅ · Python pytest ✅
(1506 / 0 falhas) · ruff check e format ✅ · mypy ✅ · `git diff a052cd8 -- packages apps/api
apps/cli` vazio ✅

Roteamento revisto (decisão do orquestrador): `App.tsx` monta `BrowserRouter` + `AppRoutes`
e `test/renderRoute.tsx` monta `MemoryRouter` + o mesmo `AppRoutes` (`useRoutes(routes)` de
`app/routes.tsx`). App e testes usam a mesma tabela, então a condição está cumprida. A linha
(a) do passo 2 ("`createMemoryRouter`") é julgada por essa condição.

Mutações: 36, todas numa cópia no scratchpad, uma por vez, com o arquivo restaurado depois.
33 deixaram a suíte vermelha, entre elas todas as 🧬 da matriz. 3 sobreviveram, todas no item
3(j) (ver o passo 3).

390 px: medido pelo QA com Chromium sem interface (`playwright-core` só como biblioteca)
sobre `vite preview` do build em 127.0.0.1, viewport 390×844. `/api` foi respondida pelo
dublê do script, e pedidos a outro host seriam abortados (nenhum ocorreu). Em `/`,
`/sermons/12`, `/cuts/34`, `/settings` e com o diálogo aberto, `scrollWidth = clientWidth =
390`, com títulos longos. A Geist carrega do build, e o build não tem referência a CDN. Em
`/settings`, a lista de seções rola dentro da própria faixa (`overflow-x: auto`, como no
protótipo), sem rolar a página. O servidor foi encerrado.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Cliente e tipos | PASS | `api/client.test.ts` cobre (a)–(f), e o typecheck cobre (g). As mutações `ok → true`, `message` fixa, sem `catch`, sem `Content-Type` e `unavailable` trocado ficam vermelhas |
| 2 — Layout e rotas | PASS | `app/routes.test.tsx` e `app/Identity.test.tsx` (rodapé nas 4 rotas) usam a tabela única. `ui/tokens.test.ts` cobre (e)–(f), e `ui/Saved.test.tsx` cobre L12. 390 px medido nesta rodada. As mutações `to="#"`, item atual como link, corte sem buscar a pregação, rodapé fora do `Shell`, token alterado, `Saved` que não some e `not_found` genérico ficam vermelhas |
| 3 — Nível 1 | PARCIAL | (a)–(i) cobertos em `SermonList.test.tsx` e `NewSermonDialog.test.tsx`, e as 🧬 da matriz ficam vermelhas. **(j) sem prova**: "blocks a second submission while the first is on its way" (`NewSermonDialog.test.tsx:160`) passa sem `disabled={sending …}` (`NewSermonDialog.tsx:70`), sem a guarda `if (sending)` (`:28`) e sem as duas juntas. O dublê responde antes do 2º clique e o diálogo já fechou. Falta um teste com o `POST` pendente (resposta segurada) que verifique o botão desabilitado e um só `POST` |
| 4 — Barra de status e configurações vazias | PASS | `StatusBar.test.tsx` (fake timers: 3 s, 2999 ms, `unmount`, indisponível e retorno), `SettingsPage.test.tsx` e `Identity.test.tsx` (401/403 só com `/api/me`). As mutações `Infinity`, sem `setInterval`, sem `clearInterval`, polling que para no erro, progresso de outra tarefa, `suggest` como ocupada, papel invertido (topo e rota), `/settings` sem recusa, filhos antes de `/api/me` e 401 = 403 ficam vermelhas |
| 5 — Documentação | PASS | §4 "Web" descreve o que existe, e "interface planejada" saiu. O `CHANGELOG` tem a entrada em `[Não lançado]`. A ADR-0022 bate com o código (roteador declarativo, tabela única, `ApiError`, `IdentityGate`, polling, tokens, Geist pelo npm) e está no índice e no README. O texto está em português, sem segredo e sem e-mail real |

### Critérios de aceite
- ✅ Cenário "lista de pregações" — `SermonList.test.tsx` (texto exato do item, sem prévia) e `routes.test.tsx` ("Pregações" atual)
- ✅ Cenário "Nova pregação" (título, data, duração da live; aviso de live no ar; motivo junto ao campo) — `NewSermonDialog.test.tsx`
- ✅ Cenário "navegação pelo caminho" e "Nova pregação" só no nível 1 — `routes.test.tsx` e `SermonList.test.tsx` (3 rotas)
- ✅ Cenário "barra de status" — `StatusBar.test.tsx`
- ✅ Cenário "configurações" — `SettingsPage.test.tsx` e `Identity.test.tsx`
- ✅ Borda API fora do ar — `client.test.ts`, `SermonList.test.tsx` (alerta), `Identity.test.tsx` (502 HTML), `StatusBar.test.tsx` (indisponível)
- ✅ Borda lista vazia — `SermonList.test.tsx`
- ✅ Borda 401/403 — `client.test.ts` e `Identity.test.tsx` (só `/api/me` chamado)
- ✅ Borda 390 px — medição registrada nesta rodada e revisão do CSS (`.crumbs` vai para linha própria, como no `@media` do protótipo)
- ✅ FR-001 — `routes.test.tsx`
- ✅ FR-002 — `routes.test.tsx`
- ✅ FR-003 — `SermonList.test.tsx` e `NewSermonDialog.test.tsx`, com corpos de `service/sermons.py`
- ✅ FR-004 — polling de 3 s em `StatusBar.test.tsx`. O SSE ficou para o item 22, registrado no `plan.md` e na spec (L8)
- ✅ FR-005 — `ui/Saved.test.tsx`
- ✅ FR-006 — `ui/tokens.test.ts`
- ✅ Verificação — as 6 linhas, pelos testes acima e pelas suítes verdes

Política de comentários (CONTRIBUTING.md §5): conforme. Os comentários novos estão em inglês
e são de referência (protótipo, ADR-0019, ADR-0022, `docs/api.md`, item 22/26), de intenção
(`vite.config.ts`, `fakeApi`) ou de contrato (docstrings, na prática das rodadas anteriores).
Não há diretiva de ferramenta nova.

Fora da barra, sem efeito no veredito:
- Há 5 arquivos `shot-*.png` não rastreados na raiz do repositório, de 16:48, que são a
  medição de 390 px do implementador. Removê-los antes do commit.
- A 390 px, a barra de status corta o texto longo ("… a pregação 12 · há 3 min").
- A ADR-0022 foi gravada como "Aceita" por agente e precisa de revisão humana.

### Veredito geral: PARCIAL
Passos 1, 2, 4 e 5 PASS. O passo 3 é PARCIAL porque falta prova do item (j): o teste de envio
duplo não distingue o código atual de um código sem proteção. Os 16 critérios estão cobertos,
e as suítes e checagens estão verdes.

## Rodada 2 — 2026-10-26 — working tree sobre a052cd8

**baseline_commit**: a052cd8ddb38006579fd758428c56591592c653b
**Componentes avaliados**: `apps/web` (reaberto: passo 3, item (j)); Python só como regressão.
**Suítes**: web ✅ (65 / 0 falhas) · typecheck ✅ · lint ✅ · build ✅ · Python pytest ✅
(1506 / 0 falhas) · ruff check e format ✅ · mypy ✅ · `git diff a052cd8 -- packages apps/api
apps/cli` vazio ✅

Item (j), decisão do orquestrador: a guarda `if (sending)` só é alcançável por
`fireEvent.submit` direto, porque o botão desabilitado já impede o clique e o Enter. A guarda
é defesa em profundidade, e o submit direto é a prova adequada. O passo é julgado com essa
condição.

Mutações: 5, numa cópia de `apps/web` no scratchpad, uma por vez, com o arquivo restaurado
depois. As 5 deixaram a suíte vermelha, entre elas as três que sobreviveram na Rodada 1:
`disabled={!url.trim()}` (1 teste), sem a guarda `if (sending)` (1), sem as duas proteções
(3), `setSending(true)` removido (3) e botão sempre desabilitado (8).

Raiz do repositório: nenhum arquivo solto novo. Os `shot-*.png` da Rodada 1 foram removidos, e
só há os caches ignorados pelo `.gitignore`.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Cliente e tipos | PASS | Sem mudança desde a Rodada 1. Suíte verde |
| 2 — Layout e rotas | PASS | Sem mudança desde a Rodada 1. Suíte verde |
| 3 — Nível 1 | PASS | (j) provado em `NewSermonDialog.test.tsx` com o `POST` segurado (`heldCreation`, `fakeApi` aceita resposta em promessa). "disables Carregar while the link is on its way" verifica o botão desabilitado. "sends the link once however many times it is confirmed" verifica um único `POST` após clique, Enter e submit direto. "follows the normal flow once the held reply arrives" verifica o fluxo depois de soltar o `POST`. As três mutações da Rodada 1 ficam vermelhas. (a)–(i) seguem como na Rodada 1 |
| 4 — Barra de status e configurações vazias | PASS | Sem mudança desde a Rodada 1. Suíte verde |
| 5 — Documentação | PASS | Sem mudança desde a Rodada 1 |

### Critérios de aceite
- ✅ Os 16 critérios da Rodada 1 continuam cobertos, pelos mesmos testes, com a suíte verde.
  "Diálogo cria a pregação" agora também tem a prova do envio único.

Fora da barra, sem efeito no veredito (da Rodada 1, ainda válidos):
- A 390 px, a barra de status corta o texto longo.
- A ADR-0022 foi gravada como "Aceita" por agente e precisa de revisão humana antes da
  aprovação.

### Veredito geral: PASS
Os 5 passos têm PASS. O item (j), PARCIAL na Rodada 1, está provado, e as três mutações que
sobreviveram agora ficam vermelhas. Os 16 critérios estão cobertos, e as suítes e checagens
estão verdes. Este resultado é sugestão de QA automatizado e precisa de revisão humana.
