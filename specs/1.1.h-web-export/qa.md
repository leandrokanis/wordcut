# QA — 1.1.h (web, item 25) — Caixa de exportação e downloads na web

## Plano de QA — 2026-10-26

**baseline_commit**: ac5446470fa6834fce499fe55f4016b8d5c118ac
**Componentes em escopo**: `apps/web` (novos `src/features/cut/ExportDialog.tsx`,
`RendersList.tsx`, `useEstimate.ts`; alterações em `src/features/cut/CutPage.tsx`,
`src/api/client.ts` e `src/api/types.ts` — ver L1 —, dublês e fixtures em `src/test/`);
documentação (`CHANGELOG.md`, seção "Não lançado"). Fora: `apps/api` e `packages/core` (as
rotas de exportação já existem, docs/api.md §2; nenhum arquivo deles deve aparecer no diff),
painel de cortes do nível 2 (chip "Exportado" e "Baixar exportação" no menu do card do
protótipo — L8) e Configurações (item 26).
**Suítes que valem como prova**:
- `apps/web`: `npm --prefix apps/web test` (Vitest + Testing Library, jsdom; `fakeApi` para
  `fetch` e `fakeEventSource` para o SSE; nenhuma rede, nenhuma renderização real).
- Um arquivo: `npm --prefix apps/web test -- <arquivo>`.
- Estática: `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build`.
- Regressão: a suíte inteira da web continua verde (níveis 1, 2 e 3, `routes.test.tsx`,
  `StatusBar.test.tsx`, `useTaskEvents.test.ts`).

**Fontes da barra**: spec.md e plan.md desta pasta; features 1.1.h (restrições: opções, salvas
no corte, andamento no botão e na barra, resumo em cada exportação) e 1.1.i (histórico no
próprio corte, a última ou uma anterior); docs/prototype/wordcut.html (`XO0`, `xopts`,
`xEstimate`, `xSummary`, `exportDialog`, `exportMenu`, ação `gerar`); docs/api.md §1–§3
(`POST /renders`, `GET /renders/estimate`, `GET /renders`, `GET /renders/{id}/file`, SSE);
docs/cli.md §8.2 (`render_options`, `renders`), §8.7 (opções e padrões) e §9.

**Mapa de opções que a barra cobra** (protótipo → API, docs/cli.md §8.7):

| Grupo | Rótulo | Controle | Campo da API | Valores |
|---|---|---|---|---|
| Limpeza | Remover hesitações | Não/Sim | `fillers` | Sim = `remove`, Não = `keep` |
| | Remover gaguejos | Não/Sim | `stammers` | Sim = `remove`, Não = `keep` |
| | Pausas | Originais/Naturais/Curtas | `pauses` | `original`/`natural`/`short` |
| Edição | Suavizar emendas | Não/Sim | `smooth_joins` | booleano |
| | Fade no início e no fim | Não/Sim | `fade` | booleano |
| Áudio | Normalizar volume (−14 LUFS) | Não/Sim | `normalize` | booleano |
| Vídeo | Legenda | Não/Sim | `caption` | booleano (o mesmo `enabled` da aba Legenda) |
| | Resolução | 1080×1920/720×1280 | `resolution` | `1080x1920`/`720x1280` |
| | Qualidade | Alta/Arquivo menor | `quality` | `high`/`small` |

Na query da estimativa os booleanos vão como `true`/`false` (docs/api.md §2). No `POST`, como
booleanos do JSON, nunca texto.

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Caixa e estimativa | (a) No nível 3, Exportar abre `role="dialog"` `aria-modal`, nomeado "Exportar 9:16", com o título do corte, os quatro grupos (Limpeza, Edição, Áudio, Vídeo) e os nove controles da tabela acima, com os rótulos do protótipo; Cancelar e Fechar fecham sem `POST`. (b) Valores iniciais = `render_options` de `GET /api/cuts/{id}` (não os padrões fixos `XO0`): fixture com opções não padrão (ex.: `pauses: "short"`, `fade: false`, `resolution: "720x1280"`) aparece marcada (`aria-pressed`/`checked`). Legenda inicial = estado atual da legenda na sessão (`useCaptionStyle`), não o `render_options.caption` carregado (L4). (c) Ao abrir, um `GET /api/cuts/{id}/renders/estimate?…` e a duração (`duration`) aparece formatada como `formatDuration`. (d) Mudar uma opção → nova estimativa com a query exata do mapa (ex.: `fade=false`, `pauses=short`, `fillers=keep`); a duração exibida passa a ser a da resposta nova. (e) Debounce 300 ms: três mudanças em < 300 ms → um só `GET`, com o último estado. (f) Sem corrida: a resposta de uma estimativa anterior que chega depois da mais nova não sobrescreve a mais nova; a anterior é abortada (`AbortSignal` passado ao `fetch`). (g) Erro da estimativa (400/rede) → motivo na caixa, Exportar continua disponível. (h) Abrir a caixa não grava nada (nenhum `POST`/`PATCH`). | Componente com `openCut` (`src/test/cutLevel.ts`) + `fakeApi`, rotas `GET` da estimativa por URL exata; contar chamadas por prefixo `/renders/estimate`. Debounce com `vi.useFakeTimers` + `userEvent.setup({ advanceTimers })`, `advanceTimersByTime(299)` → 0 chamadas novas, `(1)` → 1. Corrida: rota função que devolve promessa segurada para a 1ª estimativa, liberada depois da 2ª; afirmar texto final = 2ª. Abort: afirmar `init.signal.aborted === true` da 1ª chamada (o `fakeApi` hoje descarta `init.signal` — L5). |
| 2 — Exportar com progresso | (a) Exportar na caixa → `POST /api/cuts/{id}/renders` com corpo JSON contendo as nove opções como estão na caixa (tipos do JSON: booleanos como booleanos), e fecha a caixa. (b) 202 → abre `EventSource("/api/tasks/{task_id}/events")`; `progress` 0.35 → botão do topo do nível desabilitado com "Exportando 35%". (c) `done` → `EventSource.close()`, botão volta a "Exportar", nova leitura de `GET /api/cuts/{id}/renders` (ou do corte) e a exportação nova aparece na lista. (d) `failed` → `close()`, mensagem com `error.message` em `role="alert"`, lista sem exportação nova (nenhuma nova leitura, ou leitura que devolve a mesma lista). (e) Máquina ocupada por outra tarefa (`GET /api/status` com `lock.held` e `resource` ≠ `cut {id}`) → Exportar da caixa desabilitado e aviso "Máquina ocupada: …" (como `ProcessButton`); `POST` recusado com 409 `busy` (corrida com o polling) → mensagem do erro, nenhuma exportação, nenhum `EventSource`. (f) 409 `sermon_not_processed` / 400 → mensagem, sem `EventSource`. (g) Barra de status: com o lock `kind: "render"`, `resource: "cut 34"` e a tarefa em `running_tasks` com `progress`, mostra "exportando o corte 34" e a barra de progresso (componente já existente; prova de regressão). (h) Reabrir o corte com o próprio render rodando (`running_tasks` com `kind: "render"`, `cut_id` = id) → o botão mostra o progresso e não permite exportar de novo (L3). (i) Opções salvas: depois de `done`, reabrir a caixa mostra as opções usadas, não as carregadas antes (L6). | Componente com `openCut` + `fakeEventSource().streams()`; `act(() => stream.emit("progress"|"done"|"failed", task))`; afirmar `stream.close` chamado; `apiError(409, "busy", …)`; status via `fakeShellApi` com `busyMachine`/fixture de lock de render. Corpo do `POST` comparado por igualdade exata. `StatusBar.test.tsx` estendido com lock de render (ou prova de que já cobre `render`). |
| 3 — Lista e download | (a) Lista das exportações do corte, da mais recente para a mais antiga (ordem da API), cada uma com data (`created_at` formatado), duração e resumo das opções em texto humano (L2) — no mínimo resolução, com/sem legenda e o que fugiu do padrão (protótipo `xSummary`). (b) Cada item tem "Baixar": `<a>` com `href="/api/renders/{id}/file"` e atributo `download`; nenhum `fetch` ao clicar. (c) Sem exportações → estado vazio explícito (ou a seção não aparece, como o protótipo), sem erro. (d) Dados vêm de `GET /api/cuts/{id}` (`renders`) ou `GET /api/cuts/{id}/renders`, sem `path` (a web nunca usa `path`). (e) O nome legível `AAAA-MM-DD - Título do corte.mp4` é do servidor (`Content-Disposition`); a web não o monta — se montar no `download`, tem de bater com o do servidor. | Componente com fixture de duas exportações com opções diferentes; asserção sobre `getAllByRole("link", { name: /Baixar/ })` → `href` e `hasAttribute("download")`; ordem do texto; resumo por tabela de casos (função pura, se extraída). |
| 4 — Documentação | `CHANGELOG.md`, "Não lançado": caixa de exportação, estimativa, progresso e downloads na web (item 25). `docs/architecture/README.md` só se descrever a web por feature. Sem ADR nova, salvo decisão de arquitetura nova. | Leitura do diff contra o baseline. |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| spec — Opções e estimativa: a caixa abre com as últimas opções do corte | Passo 1 (a)(b), fixture com `render_options` fora do padrão |
| spec — Opções e estimativa: mudar uma opção atualiza a duração estimada | Passo 1 (c)(d)(e)(f) |
| spec — Exportar: confirmar inicia a tarefa | Passo 2 (a): corpo exato do `POST` |
| spec — Exportar: progresso por eventos | Passo 2 (b)(g); "andamento no botão e na barra" (feature 1.1.h) |
| spec — Exportar: ao fim, a exportação aparece na lista do corte | Passo 2 (c) + Passo 3 (a) |
| spec — Baixar: cada exportação tem Baixar, que entrega o arquivo com nome legível | Passo 3 (b)(e); nome legível só provável no servidor (já coberto pelos testes da API, item 20b); na web, `href` + `download` |
| spec borda — Máquina ocupada: aviso, sem exportar | Passo 2 (e) |
| spec borda — Falha: mensagem com o motivo; nenhuma exportação nova | Passo 2 (d)(f) |
| FR-001 — Caixa sobre `GET …/renders/estimate` e `POST …/renders` | Passo 1 (c)(d) e Passo 2 (a): `fakeApi` registra as duas rotas com query/corpo exatos |
| FR-002 — Lista (`GET /api/cuts/{id}/renders`) com Baixar (`/api/renders/{id}/file`) | Passo 3 (a)(b)(d) |
| feature 1.1.h — as escolhas ficam salvas no corte e aparecem no resumo de cada exportação | Passo 1 (b) + Passo 2 (i) + Passo 3 (a) |
| feature 1.1.i — baixar a última ou uma anterior | Passo 3 (b) com duas exportações, um link por item |
| plan Verificação — caixa abre com as opções do corte; estimativa atualiza | = Passo 1 |
| plan Verificação — exportar mostra progresso e registra; ocupado e falha com mensagem | = Passo 2 |
| plan Verificação — Baixar entrega o arquivo | = Passo 3 (b) |
| plan Verificação — typecheck, lint, testes, build limpos | Suíte e estática acima, mais regressão da web inteira |
| docs/api.md §3 — o cliente MUST fechar o `EventSource` no `done`/`failed` | Passo 2 (c)(d): `close` chamado; reuso de `useTaskEvents` (já testado) aceita como prova se a tela o usar |

### Lacunas do plan.md (escrito antes dos itens 22 a 24)

- **L1 — Contexto de código incompleto.** `Cut` (`src/api/types.ts`) não tem `render_options`
  nem `renders`, e `client.ts` não tem as quatro funções de exportação; nenhum dos dois está
  em "Alterar". Recomendação: incluir `types.ts` (tipos `RenderOptions`, `Render` sem `path`),
  `client.ts` (`estimateRender(id, options, signal)`, `startRender`, `listRenders`,
  `renderFileUrl`) e `src/test/fixtures.ts`.
- **L2 — Resumo das opções.** A API devolve `options` como objeto, não texto; o plano não diz
  quem monta o resumo. Recomendação: função pura no front, no espírito de `xSummary`
  (resolução, com/sem legenda, e o que difere do padrão), testada por tabela.
- **L3 — "Botão Exportar no topo".** No item 22 a ação do nível (`ProcessButton`) ficou dentro
  da tela (`.l2-action`), e o cabeçalho `.top` é do `Layout`, sem lugar para ação do nível.
  Recomendação (conservadora): seguir o padrão do item 22 — o botão dentro do `CutLevel`, sem
  mexer no `Layout`; anotar a divergência visual do protótipo. Reaproveitar `useTaskEvents`
  (hoje em `features/sermon/`) em vez de duplicar o SSE, e retomar o acompanhamento ao
  reabrir o corte pela tarefa `render` com `cut_id` em `running_tasks` (o `Cut` não traz
  `last_task`). Atenção: `otherWork` do `ProcessButton` ignora o lock do próprio recurso; o
  equivalente aqui não pode deixar exportar de novo com o lock em `cut {id}`.
- **L4 — Legenda tem dois donos.** Desde o item 24, `useCaptionStyle` guarda `enabled` na
  sessão e o `POST` com `caption` muda o mesmo estado no servidor. Recomendação: o controle
  Legenda da caixa parte de `caption.style.enabled` (como o protótipo, que usa `capStyle(r).on`)
  e, depois do `POST`, a aba Legenda e a prévia refletem o valor enviado.
- **L5 — Cancelamento sem prova.** O `fakeApi` ignora `init.signal`; um `AbortController` que
  não aborta passaria. Recomendação: o teste afirma `signal.aborted` na chamada anterior
  (o `RecordedCall` precisa expor o `signal`) e prova a corrida com resposta segurada.
- **L6 — Opções após exportar.** O corte é carregado uma vez (`useResource`); sem nova leitura,
  a caixa reabre com as opções antigas. Recomendação: recarregar o corte (ou suas opções e a
  lista) no `done`.
- **L7 — Autosave pendente.** O `PATCH` da legenda e o `PUT` de grafia têm debounce/blur; um
  Exportar logo depois pode renderizar o estado anterior. Recomendação: desabilitar Exportar
  enquanto houver gravação pendente, ou esperar a gravação antes do `POST`; no mínimo,
  registrar como limitação.
- **L8 — Lista: onde.** O protótipo põe as exportações no menu do botão Exportar ("Exportar
  9:16…" + "Exportações") e também no menu do card do nível 2; o plano só diz
  `RendersList`. Recomendação: no nível 3, seguir o menu do protótipo (fidelidade, Decisões
  técnicas); o card do nível 2 fica fora deste item e vai para o Registro do roadmap.
- **L9 — Estimativa fora da meta.** O protótipo pinta a duração de verde (40–75 s) ou
  amarelo. Não está no spec; não é barra. Recomendação: seguir o protótipo se for barato e
  testar a classe, ou registrar como fora.

## Rodada 1 — 2026-10-26 — working tree sobre ac54464

**baseline_commit**: ac5446470fa6834fce499fe55f4016b8d5c118ac
**Componentes avaliados**: `apps/web`; documentação (`CHANGELOG.md`,
`docs/architecture/README.md`). Diff sem arquivos de `apps/api` nem `packages/core`.
**Suítes**: web ✅ (291 / 0 falhas, 27 arquivos) · typecheck ✅ · lint ✅ · build ✅ ·
regressão Python ✅ (1510 / 0 falhas)
**Mutações** (cópia de `apps/web` no scratchpad, repositório intocado): 21 de 22 mortas — as
seis exigidas no plano de QA (Sim/Não invertido, booleano como texto no `POST`, sem abort,
sem `close()`, lista não relida no `done`, lock do próprio corte ignorado) morreram; também
L4, L6, L7, debounce, `download`, ordem, resumo, recusa e erro da estimativa. Sobreviveu:
remover o filtro `ended` do `ExportButton` (a tarefa encerrada pelos eventos voltaria a ser
seguida enquanto o `GET /api/status` atrasado ainda a lista) — fora da matriz, achado leve.
**Comentários**: dentro da política, com uma ressalva leve — `useEstimate.ts:6` aponta para
`plan.md` (em `specs/`, não ADR nem `docs/`, CONTRIBUTING §5.5); o texto em si é intenção.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Caixa e estimativa | PASS | `ExportDialog.test.tsx`: (a) diálogo modal, título, 4 grupos e 9 controles; Cancelar/Fechar sem escrita (h); (b) `render_options` fora do padrão marcados e Legenda de `useCaptionStyle` (L4); (c) estimativa ao abrir com query exata e "1:01"; (d) 10 casos de query por opção; (e) 3 mudanças → 1 `GET` após 300 ms (299 ms → nenhum); (f) resposta segurada não sobrescreve e `signal.aborted` (L5, `fakeApi.signal`); (g) 400 e rede → `alert`, Exportar ativo |
| 2 — Exportar com progresso | PASS | `ExportButton.test.tsx`: (a) corpo do `POST` por igualdade exata e caixa fechada; (b) "Exportando 35%" desabilitado, SSE `/api/tasks/10/events`; (c) `close`, Exportar de volta, relê corte e `/renders`; (d) `failed` → `alert`, `close`, nenhuma releitura; (e) lock alheio → "Máquina ocupada…" e Exportar desabilitado; 409 `busy` sem `EventSource`; (f) 409 `sermon_not_processed` e 400; (g) `StatusBar.test.tsx` "exportando o corte 34 · … 60%"; (h) retoma por `running_tasks` e bloqueia com lock `cut 34` sem tarefa seguível (L3, botão em `.l2-bar` dentro do `CutLevel`, `CutPage.tsx:137`); (i) reabre com as opções usadas (L6); L4 aba Legenda adota o `POST`; L7 "Salvando…" com `PATCH`, `PUT` de grafia e `DELETE` pendentes |
| 3 — Lista e download | PASS | `RendersList.test.tsx`: lista no menu do Exportar (L8), mais recente primeiro (inverte `cut.renders`, que vem do mais antigo, `db/renders.py:60`), data, 9:16, duração e resumo; `<a href="/api/renders/{id}/file" download>` sem `fetch` no clique; sem exportações → nada; exportação nova após `done`; `exportSummary.test.ts` por tabela (L2, 11 casos); `Render` sem `path`; nome do arquivo não montado na web |
| 4 — Documentação | PASS | `CHANGELOG.md` "Não lançado" com o item 25; `docs/architecture/README.md` (linha Web por feature e §5.3 com releitura no `done` e Baixar); sem ADR nova, nenhuma decisão de arquitetura nova |

### Critérios de aceite
- ✅ spec — caixa abre com as últimas opções do corte — "opens with the cut's saved options and the caption as the Legenda tab has it"
- ✅ spec — mudar uma opção atualiza a duração estimada — "asks the estimate again when …" (10 casos), debounce e corrida
- ✅ spec — confirmar inicia a tarefa — "launches the export with the dialog's nine options as JSON, and closes it"
- ✅ spec — progresso por eventos (botão e barra) — "follows the export's events…", `StatusBar` "says which cut the machine exports…"
- ✅ spec — ao fim, a exportação aparece na lista — "lists the new export once the export is done"
- ✅ spec — Baixar entrega o arquivo com nome legível — `href` + `download` na web; o nome é do servidor (testes da API, item 20b)
- ✅ borda — máquina ocupada: aviso, sem exportar — "keeps Exportar off while the machine works for another resource…", 409 `busy`
- ✅ borda — falha: motivo e nenhuma exportação nova — "says why the export failed…", "says why the API refused the export (…)"
- ✅ FR-001 — estimativa e `POST` com query/corpo exatos
- ✅ FR-002 — lista (`GET /api/cuts/{id}/renders`) com Baixar (`/api/renders/{id}/file`)
- ✅ feature 1.1.h — escolhas salvas no corte e resumo em cada exportação — passo 1 (b), passo 2 (i), `exportSummary`
- ✅ feature 1.1.i — baixar a última ou uma anterior — um link por item, duas exportações
- ✅ docs/api.md §3 — `close()` no `done`/`failed` — testes do botão + `useTaskEvents.test.ts` (mutação morta)
- ✅ plan Verificação — typecheck, lint, testes e build limpos

### Veredito geral: PASS
Todos os passos `[x]` em PASS contra a matriz, critérios cobertos, suítes e estática verdes.
Achados leves sem efeito no veredito: filtro `ended` sem teste (mutação sobrevivente) e a
referência a `plan.md` em `useEstimate.ts:6`.
