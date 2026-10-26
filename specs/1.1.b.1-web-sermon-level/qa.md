# QA — 1.1.b.1 — Nível 2: prévia 16:9, timeline, delimitar e processar

## Plano de QA — 2026-10-26

**baseline_commit**: 5448fb0ee8adea0c591f948935277fa20df9466e
**Componentes em escopo**: `apps/web` (`src/features/sermon/`, `src/api/client.ts`,
`src/api/types.ts`, `src/app/routes.tsx`, `src/test/`), `docs/architecture/README.md`,
`docs/adr/` (ADR nova do embed do YouTube, ver lacuna L5), `CHANGELOG.md`. Fora: `apps/api`,
`packages/core` (só leitura; nenhuma rota nova), painel de cortes (item 23).
**Suítes que valem como prova**:
`npm --prefix apps/web test` · `npm --prefix apps/web run typecheck` ·
`npm --prefix apps/web run lint` · `npm --prefix apps/web run build`

Fontes da barra: spec.md e plan.md desta pasta; `docs/requirements/features.md` (Requisitos
gerais de interface) e features 1.1.b e 1.1.c; `docs/prototype/wordcut.html` (nível 2:
`bounds`, `mainAction`, `exportMenu`, `transport`, `timeline`, `A.markin/markout/process`,
arrastos `data-trim`); `docs/api.md` §2–§3; ADR-0020 e ADR-0022; código do item 21
(`api/client.ts`, `useResource`, `test/fakeApi.ts`, `test/shellApi.ts`, `ui/Saved.tsx`,
`app/trail.ts`, `LevelPlaceholder`).

### Regras de prova (valem para todos os passos)

- Vitest + Testing Library pela rota real: `renderRoute("/sermons/12")` + `fakeShellApi`.
  Nenhum `fetch` real (rota não prevista dá 404 no `fakeApi` e aparece no teste).
- `EventSource` é dublê (`vi.stubGlobal`), com `emit(tipo, data)` e `close` espionado.
- O player é dublê da porta `PlayerLike` (tempo atual, `seek`, `play/pause`), injetado sem
  carregar a IFrame API: nenhum teste cria `<script>` ou `<iframe>` de `youtube.com`.
- Arraste por `pointerdown/pointermove/pointerup` com `getBoundingClientRect` da timeline
  stubado (jsdom devolve 0); debounce com `vi.useFakeTimers`.
- Asserção por papel/rótulo acessível (`slider` "Início da pregação", `button`
  "Processar"), não por classe CSS. Exceção aceita: o esmaecido, conferido por um atributo
  ou classe de estado documentado no componente.
- Fixtures novas seguem `test/fixtures.ts`: corpo no formato de `_shown`
  (`live_start`, `live_end`, `sermon_start`, `sermon_end`, `processed_at`, `last_task`,
  `cuts`, `suggestion_error`), dados fictícios.

### Decisão registrada: timeline sem miniaturas nem forma de onda

A API não serve miniaturas nem forma de onda (docs/api.md §2). Opção mais conservadora,
sem dado inventado: a timeline mostra a régua de tempo (em tempo da live), a faixa
"Vídeo" com a live inteira esmaecida atrás e o clipe sólido entre as bordas, rotulado
"Live inteira · h:mm:ss" sem bordas ou "Pregação · h:mm:ss" com bordas (protótipo,
`timeline()`), e o cursor. Sem faixa "Áudio" e sem imagem de fundo gerada. FR-001 fica
coberto em parte: miniaturas e forma de onda ficam como pendência de API, não deste item.
Prova: o teste do passo 1 confere a régua, o rótulo e a ausência de `<img>`, `<canvas>` e
de chamada a rota não documentada.

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Player e timeline | (a) `/sermons/:id` mostra o nível 2 no lugar do `LevelPlaceholder`; `not_found` continua "Pregação não encontrada." com o caminho. (b) Antes de processar, o player é o YouTube no trecho; com `status: processed`, é `<video src="/api/sermons/12/video">`. (c) Com `<video>`, o tempo da live vira tempo do vídeo (`t − sermon_start`). (d) Timeline: régua, clipe entre `live_start`/`live_end` (ou a live inteira sem bordas, rótulo "Live inteira"), parte de fora esmaecida, cursor seguindo `PlayerLike` e clique na régua chamando `seek`. (e) Sem miniatura/forma de onda (decisão acima). (f) `live_duration` nulo não quebra a tela. | `features/sermon/SermonPage.test.tsx` e `Timeline.test.tsx` pela rota; `PlayerLike` dublê com tempo controlado; `routes.test.tsx` sem regressão. Tipo `Sermon` estendido conferido pelo `typecheck`. |
| 2 — Bordas | (a) Arrastar a borda inicial e a final muda o clipe e chama `seek` do player na borda a cada movimento (o "quadro da borda"). (b) Soltar gera **um** `PATCH /api/sermons/12` com `{start, end}` numéricos (sem outros campos). (c) I e O trazem a borda ao tempo do cursor e salvam após 500 ms; várias teclas seguidas dão um `PATCH`. (d) Mínimo de 60 s: nem arraste nem I/O deixam a faixa abaixo de 1 min (protótipo: `MINLEN`). (e) "Salvo" (`ui/Saved`) só depois do 200; 409 `sermon_too_short`/`busy` e 400 mostram a mensagem da API junto à timeline, sem "Salvo", e a borda volta ao último valor salvo. (f) I/O e alças indisponíveis com `status: processing`; I/O ignorados com foco em campo de texto. (g) Teclas com `Ctrl/Meta` não marcam. | `ClipEdges.test.tsx`/`SermonPage.test.tsx` com eventos de ponteiro e `userEvent.keyboard`; `vi.useFakeTimers` para o debounce; corpo do `PATCH` lido do `RecordedCall`. Mutações exigidas: PATCH no `pointermove`; mínimo 0; "Salvo" antes da resposta. |
| 3 — Processar/Reprocessar | (a) Processar no lugar de Exportar enquanto não processada; desabilitado sem bordas ("Ajuste as bordas…"). (b) Clique → `POST /api/sermons/12/process` sem `force`; 202 abre `EventSource("/api/tasks/9/events")`. (c) `progress` atualiza o botão ("Processando N%"); `done` fecha o fluxo e recarrega a pregação (novo `GET /api/sermons/12`), que passa a `processed`; `failed` fecha o fluxo e mostra `error.message`, com Processar de volta (1.1.c.3). (d) Ao abrir uma pregação `processing` com `last_task` `running`, o fluxo abre por `last_task.id`. (e) Máquina ocupada: 409 `busy` (e/ou `lock.held` do `GET /api/status`) mostra o que roda, sem lançar tarefa. (f) Live no ar: 409 `live_not_finished` mostra o motivo e deixa Processar indisponível na sessão (ver L4). (g) Pregação `processed` cujas bordas mudaram na sessão mostra Reprocessar com o aviso "as edições dos cortes se perdem"; o clique manda `{"force": true}`. (h) Desmontar a tela fecha o `EventSource`. | `ProcessButton.test.tsx` e `useTaskEvents.test.ts` com `FakeEventSource`; `fakeApi` respondendo 202/409/502; `MachineStatus` por `GET /api/status` do `fakeShellApi`. Mutações exigidas: sem `close()` no `done`; `force: false` no Reprocessar. |
| 4 — Documentação | `CHANGELOG.md` com o nível 2; `docs/architecture/README.md` descreve `features/sermon`, a porta `PlayerLike` e o SSE na tela; ADR nova (ou que substitui a ADR-0022 no ponto "nenhum recurso de outro host") para o embed do YouTube, com entrada no índice `docs/adr/README.md`; README atualizado no mesmo conjunto (CLAUDE.md). | Leitura do diff contra o baseline; ADR-0022 não editada (CONTRIBUTING §3: ADR aceita não é editada). |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| spec · Delimitar: arraste/I-O mudam as bordas | Passo 2 (a)(c), teste de ponteiro e de teclado |
| spec · Delimitar: prévia mostra o quadro da borda durante o arraste | Passo 2 (a): `seek` do `PlayerLike` dublê chamado com a borda em cada `pointermove` |
| spec · Delimitar: parte cortada esmaecida | Passo 1 (d): live inteira esmaecida atrás do clipe |
| spec · Delimitar: salvas sozinhas, "Salvo" | Passo 2 (b)(c)(e): `PATCH` no `RecordedCall` + `role=status` "Salvo" após 200 |
| spec · Processar: bordas ≥ 1 min | Passo 2 (d) e passo 3 (a) |
| spec · Processar: no lugar de Exportar | Passo 3 (a): sem botão Exportar no nível 2 não processado |
| spec · Processar: progresso no botão e na barra de status, por eventos | Passo 3 (c) para o botão (SSE). Barra de status: continua pela consulta de 3 s (ADR-0022); ver L8 |
| spec · Processar: ao fim, processada e lista de cortes | Passo 3 (c): recarga e `processed`. Lista de cortes: ver L7 (item 23) |
| spec · Reprocessar com aviso de perda das edições | Passo 3 (g) |
| spec · Borda: máquina ocupada, aviso com o que roda | Passo 3 (e) |
| spec · Borda: live no ar, Processar indisponível com motivo | Passo 3 (f) |
| spec · Borda: prévia YouTube antes, vídeo da API depois | Passo 1 (b)(c) |
| FR-001 prévia 16:9 e timeline sempre visíveis | Passo 1 (a)(d) em todos os estados (`created`, `trimmed`, `processing`, `processed`, `failed`); miniaturas/onda: decisão acima |
| FR-002 bordas, I/O, `PATCH` automático | Passo 2 |
| FR-003 Processar/Reprocessar com SSE | Passo 3 |
| Verificação · Arrastar e I/O mudam as bordas e salvam sozinhos | Passo 2 (a)–(c) |
| Verificação · Processar mostra progresso e termina com a lista de cortes | Passo 3 (c); parte da lista: L7 |
| Verificação · Reprocessar aparece ao mudar bordas de pregação processada | Passo 3 (g) |
| Verificação · Ocupado e live no ar com motivo | Passo 3 (e)(f) |
| Verificação · typecheck, lint, testes, build limpos | As quatro suítes acima, verdes |
| Req. gerais · valor inválido não é salvo e mostra o motivo | Passo 2 (e) |
| Req. gerais · cada nível só com as opções que valem nele | Passo 1 (a): sem "Nova pregação" no nível 2 |
| docs/api.md §3 · cliente fecha o `EventSource` no `done`/`failed` | Passo 3 (c)(h) |
| ADR-0022 · nenhum recurso de outro host | Passo 1 (b) + passo 4: exceção do YouTube só com ADR nova (L5) |

### Divergências do plan.md com o item 21 e lacunas (recomendação conservadora)

- **L1 — Arquivos que o plano não lista.** O plano foi escrito antes do item 21. Faltam:
  `api/types.ts` (o `Sermon` não tem `live_start`, `live_end`, `sermon_start`,
  `sermon_end`, `processed_at`, `last_task`, `cuts`; `live_duration` pode ser nulo no
  banco), `api/client.ts` (sem `PATCH`, `trimSermon`, `processSermon`), `test/fixtures.ts`
  (corpo de `sermon show`) e um `test/fakeEventSource.ts`. Recomendação: acrescentar esses
  arquivos ao "Contexto de código"; um `SermonShown` em `types.ts` em vez de alargar o
  `Sermon` usado pela lista.
- **L2 — Rota e carga.** O plano diz "Alterar `routes.tsx`", mas a rota `/sermons/:id` já
  existe com `LevelPlaceholder`, e `trail.ts` já busca a pregação sem `reload`.
  Recomendação: trocar só o `element` por `SermonPage`, ler `error` do `Trail` (mantém
  "Pregação não encontrada.") e carregar o corpo completo com `useResource` próprio, com
  `reload` após `done` e após o `PATCH`.
- **L3 — Reprocessar sem sinal da API.** O `PATCH` da API não traz `needs_reprocess`
  (ADR-0020) e `sermon_start`/`sermon_end` são ajustados às palavras, então comparar com
  `live_start`/`live_end` dá falso positivo. Recomendação: Reprocessar aparece quando a
  pregação está `processed` e um `PATCH` deu 200 nesta sessão; após recarregar a página
  ele some. Registrar a limitação no plano e abrir pendência de API (campo de bordas
  processadas) fora deste item.
- **L4 — Live no ar.** `live_finished` só é atualizado pelo próprio `process`; desabilitar
  Processar pelo campo trava a pregação para sempre. Recomendação: com
  `live_finished: false`, mostrar o aviso mas deixar o clique; indisponível com o motivo
  após 409 `live_not_finished`.
- **L5 — YouTube de outro host.** A IFrame API e o `<iframe>` vêm de `youtube.com`, contra
  a ADR-0022. Recomendação: ADR nova no passo 4 (embed `youtube-nocookie.com`, script da
  IFrame API carregado só no nível 2 de pregação não processada) e o carregador atrás da
  porta, para os testes não o tocarem.
- **L6 — Vídeo processado e bordas.** O vídeo começa em `sermon_start`; borda arrastada
  para fora de `[sermon_start, sermon_end]` não tem quadro no `<video>`. Recomendação:
  converter tempos na implementação `<video>` do `PlayerLike` e, fora do trecho, usar o
  YouTube; testar a conversão.
- **L7 — "Lista de cortes".** Critério do spec e da Verificação contra "Fora: painel de
  cortes (item 23)". Recomendação: reescrever como "ao fim, a pregação recarrega como
  processada e o lugar do painel de cortes fica pronto para o item 23"; a lista em si é
  barra do item 23.
- **L8 — Progresso na barra de status "por eventos".** A barra usa a consulta de 3 s
  (ADR-0022). Recomendação: manter; o SSE vale para o botão. Se a barra precisar do SSE,
  é decisão de arquitetura (ADR).
- **L9 — Tarefa em andamento e falha.** O plano não cobre abrir a tela com tarefa
  `running` nem refazer depois de `failed` (1.1.c.3). Recomendação: incluir no passo 3
  (abrir o fluxo por `last_task.id`; `failed` volta a Processar com a mensagem).
- **L10 — Debounce "ao soltar".** Soltar já é um evento único; o debounce de 500 ms vale
  para I/O repetidos. Recomendação: PATCH imediato no `pointerup`, debounce só no teclado.
- **L11 — Erros do PATCH.** O plano não diz o que acontece em 409/400. Recomendação: motivo
  junto à timeline, sem "Salvo", borda volta ao último valor salvo.
- **L12 — Reprodução do `<video>`.** A rota responde `Content-Disposition: attachment`; o
  `<video>` costuma tocar mesmo assim, mas o seek depende de suporte a `Range`, que a
  suíte não prova. Recomendação: conferência manual fora da suíte, registrada no PR.

## Rodada 1 — 2026-10-26 — working tree sobre 5448fb0

**baseline_commit**: 5448fb0ee8adea0c591f948935277fa20df9466e
**Componentes avaliados**: `apps/web` (`features/sermon`, `api/`, `app/routes.tsx`, `test/`,
`features/status`), docs (ADR-0023, índice de ADRs, arquitetura, README, CHANGELOG, roadmap)
**Suítes**: apps/web test ✅ (122 / 0 falhas) · typecheck ✅ · lint ✅ · build ✅ ·
regressão Python `uv run pytest` ✅ (1506 / 0 falhas) · ruff check/format ✅ · mypy ✅

Decisão do orquestrador aplicada à barra: L5 e L6 valem juntas; o script do YouTube carrega
só no nível 2, quando a prévia precisa da live (antes do processamento ou fora do trecho
processado). A implementação segue: `Preview.tsx` só cria o player do YouTube fora de
`[sermon_start, sermon_end]` de pregação processada, e `youtubePlayer.loadApi` injeta o script
na primeira criação.

Mutações (cópia de `apps/web` fora do repositório; 23 de 28 mortas): as cinco exigidas pela
matriz morrem (PATCH no `pointermove`, mínimo 0, "Salvo" antes da resposta, sem `close()` no
`done`/`failed`, `force: false` no Reprocessar). Sobreviveram: (1) sem o mínimo de 1 min na
borda **final** arrastada (`ClipEdges.ts` `moved`, ramo `end`); (2) I/O sem reiniciar o
debounce, que salva 300 ms após o O (o teste conta um PATCH, não o momento); (3) o `lock` da
própria pregação contado como ocupada (fora da matriz); (4)–(5) prender as bordas em
`[0, live]` em `moved`, equivalentes porque `liveTimeAt` já prende o ponteiro.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Player e timeline | PASS | `SermonPage.test.tsx` (rota, YouTube antes, `<video src="/api/sermons/12/video">` depois, YouTube fora do trecho, 5 estados), `Timeline.test.tsx` (régua, rótulos, esmaecido por `data-faded`, cursor, clique → `seek`, sem `<img>`/`<canvas>` nem rota extra, `live_duration` nulo), `videoPlayer.test.ts` (`t − sermon_start`), `routes.test.tsx` (`not_found` com o caminho) |
| 2 — Bordas | PARCIAL | 2(a) e 2(d) provados só para a borda inicial: nenhum teste arrasta a borda final, e o mutante sem o mínimo de 1 min nela sobrevive (`ClipEdges.ts:110`). 2(c) "salvam após 500 ms" sem prova do momento: o mutante que não reinicia o debounce sobrevive (`ClipEdges.ts:79-80`). O resto de 2(b)(c)(e)(f)(g) coberto em `ClipEdges.test.tsx` |
| 3 — Processar/Reprocessar | PASS | `ProcessButton.test.tsx` (a)–(g) e `useTaskEvents.test.ts` (close no `done`/`failed` e ao desmontar, h); mutações exigidas mortas |
| 4 — Documentação | PASS | ADR-0023 (substitui a ADR-0022 só no ponto do outro host, registra L5+L6), índice, `docs/architecture/README.md` (C4, tabela de estado, fluxo 5.5), README, CHANGELOG, pendência de API no roadmap; ADR-0022 sem diff |

### Critérios de aceite
- ✅ Delimitar: arraste/I-O mudam as bordas — `ClipEdges.test.tsx` (borda inicial por arraste; as duas por I/O e botões)
- ✅ Delimitar: quadro da borda durante o arraste — "shows the border's frame in the preview while dragging it"
- ✅ Delimitar: parte cortada esmaecida — "draws the clip between the borders, over the whole live faded behind it"
- ✅ Delimitar: salvas sozinhas, "Salvo" — "saves the borders once…", "says Salvo only once the API has saved…"
- ⚠️ Processar: bordas ≥ 1 min — I/O nas duas bordas e arraste da inicial provados; arraste da final sem prova (passo 2)
- ✅ Processar no lugar de Exportar — "offers Processar, not Exportar…"
- ✅ Progresso no botão por SSE; barra de status pela consulta de 3 s (L8) — "shows the progress on the button…"
- ✅ Ao fim, recarrega como processada (L7) — "reloads the sermon, now processed…"
- ✅ Reprocessar com aviso de perda das edições — "offers Reprocessar…", "reprocesses with force…"
- ✅ Máquina ocupada com o que roda — "says what keeps the machine busy…", "keeps Processar off while the machine works on another sermon…"
- ✅ Live no ar com motivo (L4) — "warns that the live may still be on…", "locks Processar with the reason…"
- ✅ Prévia YouTube antes, vídeo da API depois, YouTube fora do trecho (L5+L6) — `SermonPage.test.tsx`, `videoPlayer.test.ts`
- ✅ FR-001 prévia e timeline em todos os estados — `test.each` dos 5 estados
- ✅ FR-002 — `ClipEdges.test.tsx` (com a lacuna do passo 2)
- ✅ FR-003 — `ProcessButton.test.tsx`, `useTaskEvents.test.ts`
- ✅ Tarefa em andamento e falha (L9) — "follows the task already running…", "says why the processing failed…"
- ✅ Valor inválido não salvo, com o motivo (L11) — `test.each` de 409/400
- ✅ Nível só com as opções dele — sem "Nova pregação" no nível 2
- ✅ Cliente fecha o `EventSource` no `done`/`failed` e ao sair — `useTaskEvents.test.ts`
- ✅ ADR-0022 · outro host só com ADR nova — ADR-0023; nenhum teste toca script/iframe do YouTube (`fakePlayers`)
- ✅ typecheck, lint, testes, build limpos
- ✅ L12 `<video>` — conferência manual registrada no tdd.md (17:36), fora da suíte, como a barra pede

### Observações (não mudam o veredito)
- Comentários (CONTRIBUTING §5): todos classificáveis (intenção, referência, restrição externa,
  formato, contrato). Ressalva: a docstring de `apps/web/src/test/fakePlayers.ts:3` diz que
  ``play`` move o player a um tempo; quem move é ``moveTo``.
- `ClipEdges.test.tsx` deixa avisos de `act(...)` no stderr (sem falha).

### Veredito geral: PARCIAL
Passos 1, 3 e 4 PASS; passo 2 PARCIAL: falta teste que arraste a borda final (mínimo de 1 min)
e que prove o momento do salvamento por I/O (500 ms após a última tecla).

## Rodada 2 — 2026-10-26 — working tree sobre 5448fb0

**baseline_commit**: 5448fb0ee8adea0c591f948935277fa20df9466e
**Componentes avaliados**: `apps/web` (passo 2 reaberto: `features/sermon/ClipEdges*`,
`test/fakePlayers.ts`); regressão dos demais passos pela suíte completa
**Suítes**: apps/web test ✅ (124 / 0 falhas) · typecheck ✅ · lint ✅ · build ✅ ·
regressão Python `uv run pytest` ✅ (1506 / 0 falhas) · ruff check/format ✅

Mutações (cópia de `apps/web` no scratchpad, original conferido com `cmp`; 8 de 8 mortas):
sem o mínimo de 1 min na borda final arrastada; I/O sem `clearTimeout`; I/O com
`??= setTimeout`; debounce de 300 ms; debounce de 700 ms; mínimo 0; PATCH no
`pointermove`; "Salvo" antes da resposta. Os dois mutantes vivos da Rodada 1 no passo 2
morrem agora.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Player e timeline | PASS | Sem mudança desde a Rodada 1; suíte verde |
| 2 — Bordas | PASS | `ClipEdges.test.tsx`: "stops the dragged end border a minute after the start" (2(a)(d) na borda final; mata o mutante de `ClipEdges.ts:110`), "saves half a second after the last press, not the first" (2(c): nada aos 400 ms após a 2ª tecla, um PATCH aos 500 ms com a borda dela; mata `clearTimeout` ausente, `??=`, 300 e 700 ms). Docstring de `test/fakePlayers.ts:3` corrigida (`moveTo`) |
| 3 — Processar/Reprocessar | PASS | Sem mudança desde a Rodada 1; suíte verde |
| 4 — Documentação | PASS | Sem mudança desde a Rodada 1 |

### Critérios de aceite
- ✅ Processar: bordas ≥ 1 min — agora também no arraste da borda final ("stops the dragged end border a minute after the start")
- ✅ FR-002 — `ClipEdges.test.tsx`, sem lacuna
- ✅ Demais critérios — como na Rodada 1, suítes verdes

### Veredito geral: PASS
Os dois achados da Rodada 1 no passo 2 foram fechados com teste e mutante morto; nenhum
passo pendente. Observação mantida: avisos de `act(...)` no stderr de `ClipEdges.test.tsx`.
