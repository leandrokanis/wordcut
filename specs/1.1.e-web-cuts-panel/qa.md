# QA — 1.1.e (web) — Nível 2: painel de cortes

## Plano de QA — 2026-10-26

**baseline_commit**: 13ce97aa833e6c81e29f409299a45745e29ecc90
**Componentes em escopo**: `apps/web` (`src/features/sermon/` — `CutsPanel.tsx`,
`CutCard.tsx`, `CutLayers.tsx` novos; `SermonPage.tsx`, `Timeline.tsx` alterados —,
`src/api/client.ts`, `src/api/types.ts`, `src/test/` (fixtures e dublês), `src/ui/app.css`),
`CHANGELOG.md`, `docs/architecture/README.md`. Fora: `apps/api` e `packages/core` (só leitura;
nenhuma rota nova nesta onda, ver L1), nível 3 (item 24), edição de faixa (2.1.c, onda 6).
**Suítes que valem como prova**:
`npm --prefix apps/web test` · `npm --prefix apps/web run typecheck` ·
`npm --prefix apps/web run lint` · `npm --prefix apps/web run build`

Fontes da barra: spec.md e plan.md desta pasta; feature 1.1.e e restrições de camada da 2.1.c
(`docs/requirements/features/`); `docs/prototype/wordcut.html` (`cortesPanel`, `cutCard`,
`A.opencut/discard/restore/cutmenu`, `timeline()` nível 2, `cutColor`); `docs/api.md` §2
(rotas de cortes); `packages/core/src/wordcut/service/cuts.py` (`list_cuts`, `_listed`,
`choose/discard/restore_cut`, `preview_cut`); ADR-0022 e ADR-0023; código do item 22
(`SermonPage`, `Timeline`, `ProcessButton`, `videoPlayer`, `test/fixtures.ts`,
`test/shellApi.ts`, `test/fakeApi.ts`).

### Regras de prova (valem para todos os passos)

- Vitest + Testing Library pela rota real: `renderRoute("/sermons/12")` + `fakeShellApi`;
  rota não prevista dá 404 no `fakeApi` e aparece no teste. Nenhum `fetch` real, nenhum
  `<script>`/`<iframe>` do YouTube (players são os dublês de `test/fakePlayers.ts`).
- Corpo de `GET /api/sermons/{id}/cuts` nas fixtures no formato de `cuts.py::_listed`
  (`id`, `status`, `title`, `segments`, `range_start_word`, `range_end_word`, `source`,
  `preset_id`, `edited`, `sermon_id`, `text`, `duration`), dados fictícios.
- Asserção por papel/rótulo acessível (`article`/`listitem` com o título, `button`
  "Mais ações", `menuitem` "Descartar"/"Restaurar"); estado visual (descartado, cor) por
  atributo de estado documentado no componente, não por classe CSS solta.
- Transições conferidas no `RecordedCall` (método, URL, ordem das chamadas); navegação
  conferida pela rota montada (`/cuts/:id` ainda é o `LevelPlaceholder` do item 21).
- Os testes do item 22 (`SermonPage`, `Timeline`, `ClipEdges`, `ProcessButton`) seguem
  verdes sem alteração de asserção; mudar asserção antiga exige justificativa no tdd.md.

### Divergências do plan.md com o código do item 22 (plano escrito antes dele)

| # | Divergência | Ajuste recomendado ao plan.md |
|---|---|---|
| D1 | `SermonPage` é só `main.work` (barra, prévia, transporte, timeline); não há painel lateral `.side` no app. O plano não diz onde o painel entra nem como fica em 390 px. | Envolver o nível 2 em `.side` (340 px, à esquerda) + `.work`, como o protótipo; painel fixo, sem botão de ocultar nesta onda; em 390 px o painel empilha abaixo da timeline. Acrescentar `ui/app.css` ao Contexto de código. |
| D2 | `Timeline` tem só a faixa "Vídeo" com alças de borda, régua com `seek` e cursor; recebe tudo por props. | `Timeline` ganha uma prop `layers` (vazia por padrão) e desenha, acima de "Vídeo", um `.th` + `.lane` por corte (protótipo `timeline()`), em tempo da live. Sem tocar no arraste das bordas. |
| D3 | `ProcessButton.onEnd` recarrega só `GET /api/sermons/{id}`. | O painel e as camadas recarregam os cortes quando a pregação recarrega (chave do `useResource` com `processed_at`/`status`, ou `reload` conjunto). |
| D4 | `SermonShown.cuts` já traz `{id, status, title}` e `suggestion_error`; `types.ts::Cut` só tem 4 campos; `client.ts` só tem `getCut`. | Contexto de código passa a listar `api/types.ts` (tipo do item de `cut list`), `api/client.ts` (`listCuts`, `chooseCut`, `discardCut`, `restoreCut`) e `test/fixtures.ts`. Painel lê `GET /cuts` (FR-001); `suggestion_error` vem do `GET /api/sermons/{id}`. |
| D5 | O vídeo processado começa em `sermon_start` (`videoPlayer`, ADR-0023); tempos de corte são em tempo da pregação. | Camada em `sermon_start + t`; fixture `processedSermon` já tem `sermon_start: 1801.2`, o que torna o desvio visível. |

### Decisões registradas pelo QA (opção mais conservadora, sem perguntar)

- **Fonte do tempo da camada (L1)**: `GET /api/sermons/{id}/cuts` não traz tempo; a faixa
  (`range_*_word`) só tem ids de palavra, e nenhuma rota dá o tempo dessas palavras. Sem
  mudar a API neste item, a barra aceita a camada como o vão dos trechos — menor `start`
  e maior `end` de `GET /api/cuts/{id}/preview` (não espera a trava) —, convertido com
  `sermon_start`. O tempo exato da faixa fica como pendência de API no roadmap.
- **Abrir** só marca `chosen` quando o corte está `suggested`; `chosen` abre sem `POST`;
  `discarded` não abre (protótipo: sem "Abrir corte" em `off`; restaurar primeiro). A
  navegação acontece depois do 200 do `choose`; erro mostra a mensagem e fica no nível 2.
- **Clique abre** (spec e feature 1.1.e), não o selecionar/expandir + duplo clique do
  protótipo; sem zoom da timeline no corte.
- **Ordem**: a do serviço; depois de descartar/restaurar a lista é pedida de novo, sem
  reordenar no cliente. Lista única; o descartado aparece marcado (sem o grupo
  recolhível "Descartados (N)" do protótipo).
- **Camadas sem alça nem arraste para nenhum papel**, inclusive admin (constituição §I e
  2.1.c na onda 6; o protótipo desenha alças para admin).

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Painel e cards | (a) Pregação `processed`: um card por item de `GET /api/sermons/12/cuts`, com título, texto montado, duração formatada (`formatDuration`) e estado legível (sugerido/escolhido/descartado). (b) Ordem do serviço: o descartado da resposta aparece por último, sem reordenar no cliente. (c) Menu "Mais ações": `menuitem` "Descartar" num corte não descartado, "Restaurar" num descartado; Escape e clique fora fecham; um menu aberto por vez. (d) `suggestion_error` com zero cortes: mostra a `message` da API (ex.: `llm_not_configured`), nunca segredo. (e) Zero cortes sem erro: "Nenhum corte nesta pregação.". (f) Não processada: "Os cortes aparecem depois do processamento." e nenhuma chamada a `GET /cuts`. (g) `GET /cuts` 404/502: mensagem, sem tela branca. | `CutsPanel.test.tsx`/`CutCard.test.tsx` pela rota com `processedSermon` e corpo de `_listed`; `userEvent` para o menu e Escape; `calls` conferindo ausência de `GET /cuts` antes de processar. Mutações exigidas: esconder `suggestion_error`; inverter Descartar/Restaurar no menu; pedir `GET /cuts` com pregação `trimmed`. |
| 2 — Abrir, descartar, restaurar | (a) Clique num card `suggested` → `POST /api/cuts/34/choose` e, depois do 200, rota `/cuts/34`. (b) Card `chosen` → navega sem `POST`. (c) Card `discarded` não abre. (d) `choose` com erro → mensagem no painel, sem navegar. (e) "Descartar" → `POST /api/cuts/34/discard` e novo `GET /cuts`; o card passa a descartado e vai para o fim conforme a resposta. (f) "Restaurar" → `POST .../restore` e novo `GET /cuts`; volta a sugerido. (g) Falha de discard/restore: mensagem, estado anterior mantido. (h) Nenhuma rota de edição de conteúdo chamada (`PUT words`, `PATCH caption`, etc.). | Testes de rota com `fakeApi` que segura a resposta (promessa) para provar a ordem `choose` → navegação; `calls` com método/URL; asserção da rota `/cuts/34` pelo `LevelPlaceholder`. Mutações exigidas: remover o `POST choose`; navegar antes do 200 (ou mesmo com erro); mandar `choose` para `chosen`/`discarded`; não pedir a lista de novo após discard. |
| 3 — Camadas na timeline | (a) Pregação `processed` com cortes: uma camada por corte (cabeçalho com número/título + faixa), acima de "Vídeo", na ordem do painel. (b) Posição/largura em tempo da live: `sermon_start + min(start)` a `sermon_start + max(end)` dos trechos (decisão L1), conferidas no `style` contra a fixture com `sermon_start: 1801.2`. (c) Descartado marcado (atributo de estado), mesma cor do card (L9). (d) Sem alça (`slider`) nem arraste nas camadas, como assistente e como admin; `pointerdown` na camada não chama `PATCH`. (e) Não processada: nenhuma camada. (f) Após `done` do processamento, camadas e painel recarregam. (g) Régua, bordas, I/O e cursor do item 22 intactos. | `Timeline.test.tsx`/`CutLayers.test.tsx` e `SermonPage.test.tsx`; `fakeApi` com `GET /api/cuts/{id}/preview`; `FakeEventSource` para o `done`. Mutações exigidas: omitir `sermon_start`; desenhar camada com `trimmed`; renderizar alça para admin; não recarregar cortes no `done`. |
| 4 — Documentação | `CHANGELOG.md` com o painel e as camadas; `docs/architecture/README.md` descrevendo `CutsPanel`/`CutCard`/`CutLayers` em `features/sermon`; pendência de API do tempo da faixa (L1) anotada em `specs/roadmap.md`. Sem ADR nova, salvo se entrar biblioteca (cache, menu) — aí ADR + índice. | Leitura do diff contra o baseline; ADR-0022/0023 não editadas (CONTRIBUTING §3). |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Spec · Listar: cards com título, texto, duração e estado; descartados por último | Passo 1 (a)(b) |
| Spec · Abrir: clicar no card abre o nível 3 e marca escolhido | Passo 2 (a)(b)(c)(d) |
| Spec · Descartar/restaurar pelo menu; card vai para o fim ou volta | Passo 1 (c) + Passo 2 (e)(f)(g) |
| Spec · Camadas: cada corte como faixa contínua na timeline do nível 2, só leitura | Passo 3 (a)–(e) |
| Borda · sem cortes com `suggestion_error`: mensagem com o motivo | Passo 1 (d) |
| Borda · nenhuma edição de conteúdo nesta onda | Passo 2 (h) + Passo 3 (d) |
| FR-001 · painel sobre `GET /api/sermons/{id}/cuts` | Passo 1 (a)(f)(g) |
| FR-002 · `choose` ao abrir; `discard`/`restore` no menu | Passo 2 (a)–(g) |
| FR-003 · camadas sem edição | Passo 3 (a)–(d) |
| Verificação · cards com título, texto, duração e estado; descartados por último | Passo 1 (a)(b) |
| Verificação · abrir marca escolhido e navega; menu descarta e restaura | Passo 2 |
| Verificação · camadas na timeline; mensagem de `suggestion_error` | Passo 3 + Passo 1 (d) |
| Verificação · typecheck, lint, testes, build limpos | as quatro suítes acima, verdes; testes do item 22 sem regressão |

### Lacunas do plan.md

| # | Lacuna | O que fica PARCIAL sem ela | Recomendação |
|---|---|---|---|
| L1 | Camada exige tempo; `cut list` não traz tempo e a faixa só tem ids de palavra. | Passo 3, FR-003 | Adotar a decisão acima (vão dos trechos via `GET /cuts/{id}/preview` + `sermon_start`) e anotar pendência de API: tempo da faixa em `cut list`. |
| L2 | Onde fica o painel e como reflui em 390 px (D1). | Passo 1 | Adotar D1. |
| L3 | Como as camadas entram na `Timeline` sem quebrar o item 22 (D2). | Passo 3 (g) | Prop `layers`; testes antigos sem alteração. |
| L4 | Recarga dos cortes após processar (D3). | Passo 3 (f) | Adotar D3. |
| L5 | Tipos e cliente fora do Contexto de código (D4). | Passos 1–2 (typecheck) | Adotar D4. |
| L6 | `choose` para `chosen`/`discarded`, ordem `choose`→navegação e erro. | Passo 2 | Adotar a decisão "Abrir" acima. |
| L7 | Atualização após discard/restore (reordenar local ou pedir de novo). | Passo 2 (e)(f) | Pedir `GET /cuts` de novo (decisão "Ordem: a do serviço"). |
| L8 | Estados do painel por status da pregação (não processada, processando, vazio, erro de rede). | Passo 1 (e)(f)(g) | Textos do protótipo `cortesPanel`/`emptyP`; não chamar `GET /cuts` antes de `processed`. |
| L9 | Cor da camada: plano diz "por estado", protótipo usa cor por índice (`cutColor`) com descartado esmaecido. | Passo 3 (c) | Ajustar o plano ao protótipo: cor por índice, a mesma no card e na camada; estado por marcação de descartado. |
| L10 | Clique abre (spec) × selecionar/expandir + duplo clique (protótipo); grupo "Descartados (N)" do protótipo. | — (registro) | Manter a spec; registrar a divergência no plan.md. |
| L11 | Acessibilidade do menu (papel, Escape, clique fora, um por vez). | Passo 1 (c) | `button` "Mais ações" com `aria-haspopup`, `role="menu"`/`menuitem`, como `exportMenu`/`cmenu` do protótipo. |
| L12 | Passo 4 cita só CHANGELOG. | Passo 4 | Incluir `docs/architecture/README.md` e a pendência L1 no roadmap. |

## Rodada 1 — 2026-10-26 — working tree sobre 13ce97a

**baseline_commit**: 13ce97aa833e6c81e29f409299a45745e29ecc90
**Componentes avaliados**: `apps/web`; `packages/core` (`list_cuts`), `apps/cli` e `apps/api`
(testes de `cut list`), pela decisão L1 do orquestrador no plan.md; docs.
**Suítes**: web ✅ (152 / 0 falhas) · typecheck ✅ · lint ✅ · build ✅ · pytest ✅ (1510 / 0
falhas) · ruff check ✅ · ruff format --check ✅ · mypy ✅

Barra: matriz do topo com as decisões do orquestrador no plan.md. A L1 mudou: a camada usa
`start`/`end` de `cut list` (não mais o vão de `GET /cuts/{id}/preview`), e a pendência de
API do roadmap (passo 4) deixou de existir. A linha 3 (b) é julgada pela posição
`sermon_start + start` … `sermon_start + end`, o que a decisão nova fixou.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Painel e cards | PASS | `CutsPanel.test.tsx` cobre (a)–(g): cards, ordem do serviço com `data-discarded`, menu acessível (Escape, clique fora, um por vez), `suggestion_error`, vazio, não processada sem `GET /cuts`, erro 502. Mutações exigidas vermelhas (esconder `suggestion_error`, inverter o menu, `GET /cuts` com `trimmed`) e mais: ordenar no cliente, Escape/clique fora, texto vazio, erro da lista. |
| 2 — Abrir, descartar, restaurar | PASS | `CutsPanel.test.tsx`: `choose` só em sugerido e navegação depois do 200, escolhido sem `POST`, descartado não abre, erro no painel, discard/restore com novo `GET /cuts`, falha mantém o card, nenhuma rota de conteúdo. Mutações vermelhas: sem `choose`, navegar antes do 200 ou com erro, `choose` em qualquer estado, abrir descartado, sem nova lista, restaurar chamando discard, engolir o erro. |
| 3 — Camadas na timeline | PASS | `CutLayers.test.tsx` (ordem acima de "Vídeo", posição contra `sermon_start` 1801.2, cor por índice igual ao card, `data-discarded`, sem alça como admin e assistente, nenhuma camada antes de processar, recarga no `done`); core `test_listed_cut_spans_…`, `…_kept_to_the_millisecond`, CLI `test_list_with_json_gives_each_cut_its_span_…`, API `test_listing_gives_each_cut_its_span_…`. Mutações vermelhas: sem `sermon_start`, largura errada, alça, recarga no `done`, ordem das camadas, cor e marca; no core: sem `round`, início do primeiro trecho, sem span. Sobreviveu só remover o portão de status de `cutLayers` (equivalente: `useSermonCuts` já devolve `[]` fora de `processed`). Testes do item 22 sem alteração. |
| 4 — Documentação | PASS | `CHANGELOG.md` (Adicionado: painel; Alterado: `start`/`end`), `docs/architecture/README.md` (`CutsPanel`, `CutCard`, `CutLayers`), `docs/cli.md` §8.1, `docs/api.md`; sem ADR nova nem edição de ADR-0022/0023; pendência do roadmap extinta pela L1. |

**Asserção antiga ajustada** (`packages/core/tests/test_cuts_service.py::test_listed_cut_has_the_sermon_cut_fields_plus_its_text_duration_and_span_without_words`):
legítima. O teste fixa o dict exato do item listado; o contrato mudou por decisão do
orquestrador (L1). O ajuste só acrescenta `start: 2.5` e `end: 3.4`, sem afrouxar nenhuma
outra chave, renomeia o teste para o contrato novo e está justificado no tdd.md (18:08).

**Política de comentários (CONTRIBUTING §5)**: comentários e docstrings novos estão em
inglês e são de intenção, referência ou contrato. Dois desvios leves, que não mudam
veredito: `CutsPanel.tsx`, comentário de `open` ("a discarded one is restored first")
descreve algo que o código não faz, porque o descartado não abre; `test/fixtures.ts`
`listedCut` cita `_listed`, mas o item agora sai de `_spanned`. No `CHANGELOG.md` sobrou
uma linha em branco entre os dois itens de "Alterado".

### Critérios de aceite
- ✅ Spec · Listar (cards, ordem, descartados por último): `shows one card per cut…`, `keeps the service's order…`
- ✅ Spec · Abrir marca escolhido e abre o nível 3: `opens a suggested cut by choosing it…`, `opens a chosen cut…`, `does not open a discarded cut`, `stays on the sermon… when choosing the cut fails`
- ✅ Spec · Descartar/restaurar pelo menu: `offers Descartar… Restaurar…`, `discards from the menu…`, `restores from the menu…`, `keeps the card as it was…`
- ✅ Spec · Camadas só leitura: `CutLayers.test.tsx` (ordem, posição, cor, sem alça)
- ✅ Borda · `suggestion_error`: `says why a processed sermon has no cuts…`
- ✅ Borda · nenhuma edição de conteúdo: `never asks the API to change a cut's content` + camadas sem alça e sem `PATCH`
- ✅ FR-001 · painel sobre `GET /cuts`: testes de rota com `fakeApi` + estados (f)(g)
- ✅ FR-002 · `choose`/`discard`/`restore`: passo 2
- ✅ FR-003 · camadas sem edição: passo 3 (a)–(d)
- ✅ Verificação · cards com título, texto, duração e estado: passo 1
- ✅ Verificação · abrir e menu: passo 2
- ✅ Verificação · camadas e `suggestion_error`: passo 3 + passo 1 (d)
- ✅ Verificação · typecheck, lint, testes, build: as quatro suítes web verdes; Python verde

### Veredito geral: PASS
Quatro passos PASS, 13/13 critérios cobertos, suítes e checagens verdes. O refluxo em 390 px
(D1) está só no CSS (`@media`, painel com `order: 3`), sem verificação visual nesta rodada.
