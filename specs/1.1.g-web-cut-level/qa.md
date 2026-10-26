# QA — 1.1.g (web, item 24) — Nível 3: prévia 9:16, abas Texto e Legenda, grafia na prévia

## Plano de QA — 2026-10-26

**baseline_commit**: d8b0342802f166a759f2dd5f63d2655bc139681b
**Componentes em escopo**: `apps/web` (novo `src/features/cut/`; alterações em
`src/app/routes.tsx`, `src/api/client.ts`, `src/api/types.ts`, testes em `src/test/`);
documentação (`CHANGELOG.md`, `docs/architecture/README.md`). Fora: `apps/api` e
`packages/core` (rotas de cortes já existem, docs/api.md; nenhum arquivo deles deve aparecer
no diff), exportação (item 25), edição de conteúdo pelo administrador (2.1.c).
**Suítes que valem como prova**:
- `apps/web`: `npm --prefix apps/web test` (Vitest + Testing Library, jsdom, `fakeApi` e
  `fakePlayers`; nenhuma rede, nenhum `<video>` real, nenhum script do YouTube).
- Estática: `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build`.
- Regressão: a suíte inteira da web continua verde (níveis 1 e 2, `routes.test.tsx`).

**Fontes da barra**: spec.md e plan.md desta pasta; docs/requirements/features.md
(Requisitos gerais de interface: autosave, "Salvo", regra das abas); features 1.1.g e 1.1.f
(f.2–f.5); docs/prototype/wordcut.html, nível 3 (`capCss`, `checkWord`, `editCapWord`,
`setLegendTab`, `tabLegenda`, pointerdown); docs/api.md (preview, caption, words);
docs/cli.md §8.2, §8.3, §8.5, §8.6; ADR-0022 e ADR-0023.

**Como a sincronia sem vídeo real é provada (decisão do QA)**: o relógio falso é o
`FakePlayer.moveTo(liveSeconds)` de `src/test/fakePlayers.ts`, que avisa os ouvintes de
`onTime` como o `timeupdate` faria. O teste monta a tela com `PlayerFactoryContext` = dublê,
move o relógio para `sermon_start + word.start + ε` e afirma (a) qual palavra da legenda está
marcada como atual e (b) os `seeks` que o controlador pediu ao cruzar o fim de um trecho. Não
se usa `vi.useFakeTimers` para a sequência (o tempo vem do player); timers falsos só no
debounce do autosave. A fidelidade visual ao render NÃO é provada (é aproximação, FR-002):
o teste prova estado (palavra atual, bloco, estilo como valores), não pixels.

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Prévia (sequência, recorte 9:16, timeline do corte) | (a) Controlador puro: dado `segments` de `GET /api/cuts/{id}/preview`, ao chegar ao `end` do trecho i pede `seek` ao `start` do trecho i+1; no fim do último, pausa. Funciona com `out_of_order` (exemplo do cli.md §8.3: `2.5–3.4`, `0.3–1.2`, `1.35–1.9` toca na ordem dada, não volta ao 1º ao passar por 2.5 no 3º trecho). (b) Conversão de tempo: trechos em tempo da pregação → player em tempo da live (`sermon_start + t`, ADR-0023); tempo do corte (0…`duration`) ↔ (trecho, tempo da pregação) nos dois sentidos. (c) A tela cria só `players.video(el, sermon_start)` com `src=/api/sermons/{sermon_id}/video`; nunca `players.youtube` (ADR-0023: o nível 3 não carrega o YouTube). (d) Timeline do corte em tempo do corte: largura proporcional a `duration`, clique/arrasto leva a prévia ao ponto certo do trecho certo; contador `t / duração`. (e) Prévia não é bloqueada pela trava: com `GET /api/status` com `lock.held=true`, a prévia carrega e toca. (f) Rota `/cuts/:id` monta a tela do corte; 404 continua "Corte não encontrado." | Unitário Vitest do controlador (sem DOM), tabela de casos incluindo `out_of_order`, trecho único e fim. Componente: `fakeApi` (`GET /api/cuts/{id}`, `/preview`, `/api/sermons/{sid}`) + `fakePlayers`; `moveTo` no fim de cada trecho e asserção sobre `current().seeks` (em segundos da live) e `playing=false` no fim; `created.every(p => p.kind === "video")`. `routes.test.tsx` estendido. Recorte 9:16 (`object-fit: cover` centrado): só inspeção do CSS e do build — jsdom não mede layout. |
| 2 — Legenda na prévia | (a) Palavras e tempos vêm de `GET /api/cuts/{id}` (`words`: `word_id`, `text`, `start`, `end`, `corrected`); a legenda mostra `corrected ?? text`. (b) Blocos: nunca misturam duas frases (fim em `.`, `?`, `!`) nem cruzam pausa ≥ 0,6 s (mesmas constantes de `vertical/captions.py`); fora de bloco não há legenda. (c) Palavra atual: no tempo t (sermon) a palavra com `start ≤ t < end` fica marcada (`aria-current` ou `data-now`) e só ela. (d) Estilo do `caption`: `size`/`border` em px no quadro 1080 convertidos para a largura do quadro (proporção `px/1080`), `color`, `border_color`, `offset` → posição vertical %, `shadow` (`none`/`soft`/`strong`), `font`. (e) `enabled=false` → nenhuma legenda no DOM (ou `hidden`), mesmo com relógio sobre uma palavra. | Função pura de blocos testada por tabela (frase, pausa 0,59 vs 0,6 s). Componente com `fakePlayers.moveTo` palavra a palavra: afirmar a palavra marcada antes, dentro e depois de cada palavra, inclusive no salto entre trechos. Estilo testado como VALORES: função pura `captionCss(style)` (objeto) e/ou custom properties (`--cap-size`, `--cap-stroke`, `--cap-top`) — não asserção em `-webkit-text-stroke`/`cqw` no `style` do jsdom, que o `cssstyle` descarta. |
| 3 — Abas e formulário | (a) Abre em Texto; Texto mostra o texto montado (trechos de `/preview`, com correções). (b) Clicar na camada Legenda da timeline abre Legenda; fechar (botão) ou clicar em outra área (vídeo, áudio, prévia) volta a Texto; clicar dentro do painel ou numa palavra da legenda NÃO fecha (protótipo `setLegendTab`/pointerdown). (c) Formulário em linhas (rótulo à esquerda, controle à direita) com: Legenda Sim/Não, Fonte, Tamanho (24–160), Cor, Posição (Topo/Centro/Base), Altura (10–90 %), Borda (0–12), Cor da borda, Sombra (Não/Suave/Forte). (d) Autosave: mudança dispara `PATCH /api/cuts/{id}/caption` só com o campo mudado, após 400 ms; mudanças rápidas no mesmo campo → um só PATCH com o último valor; a resposta (estilo inteiro) vira o estado e a prévia reflete; "Salvo" discreto no sucesso; 400 → motivo junto ao campo, valor não aplicado. (e) Posição leva a Altura ao valor da posição (20/50/78), como a resposta da API devolve. (f) "Restaurar padrão" → `DELETE /api/cuts/{id}/caption`, formulário e prévia com o estilo devolvido (ligado). (g) Sem botão Salvar/Aplicar. | Testing Library + `userEvent` (com `advanceTimers` ligado a `vi.useFakeTimers`) + `fakeApi` gravando chamadas: contar PATCHes e afirmar o corpo exato; `apiError(400, "invalid_argument", …, {min, max})` para o erro junto ao campo; checar que a legenda da prévia muda (valor de estilo) após a resposta. Abas por `role="tab"`/`aria-selected` e cliques (`pointerDown`) nas áreas. |
| 4 — Grafia na prévia | (a) Clique duplo numa palavra da legenda pausa o player (`FakePlayer.playing === false`) e troca a palavra por um campo com o valor atual (`corrected ?? text`), focado. (b) Enter → `PUT /api/cuts/{id}/words/{word_id}` com `{"text"}` (sem espaços nas pontas); sair do campo (blur) → mesmo PUT; valor igual ao atual → nenhum PUT. (c) Sucesso → palavra nova na legenda e na aba Texto, "Salvo". (d) 409 `spelling_too_different` → mensagem de bloqueio no lugar, palavra inalterada; 400 `invalid_argument` (vazio/mais de uma palavra) → motivo, palavra inalterada. A mensagem não repete o texto digitado (ADR-0015). (e) Esc → nenhum PUT, palavra original, campo fechado. (f) Enter seguido do blur que ele provoca não manda dois PUTs. | Componente com `fakeApi` + `fakePlayers` (`play()` antes, `dblClick` na palavra, `type`, `{Enter}`/`{Escape}`/`tab`); contar chamadas `PUT`; `apiError(409, "spelling_too_different", …, {distance, limit, original})`. |
| 5 — Documentação | CHANGELOG em "Não lançado" descreve o nível 3; `docs/architecture/README.md` cita `features/cut/` se descreve a web por feature; `routes` atualizado (Contexto de código). | Leitura do diff contra o baseline. |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| spec — Prévia: tocar percorre os trechos na ordem, pulando os intervalos | Passo 1 (a)(b)(c): controlador puro + componente com `moveTo` e `seeks` em tempo da live, incluindo `out_of_order` |
| spec — Prévia: a legenda acompanha palavra a palavra com o estilo do corte | Passo 2 (c) com relógio falso palavra a palavra; Passo 2 (d) estilo como valores |
| spec — Abas: abre em Texto; camada de legenda abre Legenda; fechar ou clicar em outra área volta para Texto | Passo 3 (a)(b) |
| spec — Estilo: cada um dos 9 controles reflete na prévia e salva sozinho | Passo 3 (c)(d)(e): um caso por campo (pode ser tabela `it.each`), com PATCH e reflexo na prévia |
| spec — Estilo: "Restaurar padrão" volta ao estilo da igreja | Passo 3 (f) |
| spec — Grafia: clique duplo pausa e abre campo; Enter ou sair salva; Esc cancela | Passo 4 (a)(b)(c)(e)(f) |
| spec — Grafia: bloqueio da trava | Passo 4 (d) |
| spec borda — Trava de grafia: mensagem no lugar, sem mudar a palavra | Passo 4 (d) |
| spec borda — Legenda desligada: prévia sem legenda | Passo 2 (e) + Passo 3 (Legenda Não) |
| spec borda — 390 px: layout utilizável | Não provável em jsdom. Prova: regra CSS de 390 px presente + verificação manual em Chromium headless, como o item 21 fez; sem isso fica PARCIAL |
| FR-001 — Prévia sobre `/preview` e o vídeo da pregação | Passo 1: `fakeApi` registra `GET /api/cuts/{id}/preview`; `players.video` com `src=/api/sermons/{sid}/video` e offset `sermon_start` |
| FR-002 — Legenda no navegador com o estilo de `GET /caption` (aproximação) | Passo 2 (d): estilo lido de `caption` (de `GET /api/cuts/{id}` ou `GET /caption`), registrado em `fakeApi` |
| FR-003 — `PATCH/DELETE /caption` com autosave; `PUT /words/{word_id}` | Passo 3 (d)(f); Passo 4 (b) |
| 1.1.g — nunca bloqueada pela trava de processamento | Passo 1 (e) |
| ADR-0023 — nível 3 não carrega o YouTube | Passo 1 (c) |
| Requisitos gerais — "Salvo" discreto; inválido não salva e mostra motivo junto ao campo | Passo 3 (d); Passo 4 (c)(d) |
| plan Verificação — Prévia percorre trechos na ordem; legenda acompanha com o estilo | = critérios de Prévia acima |
| plan Verificação — Abas seguem as regras; formulário salva sozinho e restaura | = Passo 3 |
| plan Verificação — Clique duplo edita a palavra; bloqueio aparece; Esc cancela | = Passo 4 |
| plan Verificação — typecheck, lint, testes, build limpos | Comandos estáticos + suíte inteira da web verdes |

### Mutações que serão cobradas (cada uma deve deixar um teste vermelho)

- Controlador que escolhe o trecho só pelo tempo (sem índice atual) → caso `out_of_order` vermelho.
- Remover a soma de `sermon_start` na conversão → `seeks` errados.
- Não pausar no fim do último trecho → vermelho.
- Palavra atual com `<=` no `end` (duas palavras marcadas na fronteira) → vermelho.
- Ignorar `corrected` na legenda → vermelho.
- Debounce removido (PATCH a cada tecla) ou PATCH com o estilo inteiro → vermelho.
- Clique dentro do painel fechando a aba Legenda → vermelho.
- Duplo clique sem `pause()` → vermelho.
- Esc mandando PUT, ou Enter+blur mandando dois PUTs → vermelho.
- 409 aplicando a palavra mesmo assim → vermelho.
- `enabled=false` ainda desenhando legenda → vermelho.

### Divergências do plan.md (escrito antes dos itens 22 e 23) e ajuste recomendado

1. **Tempo da live × tempo da pregação**: `PlayerLike` fala em segundos da live
   (`Player.tsx`, ADR-0023) e `videoPlayer(el, offset)` usa `offset = sermon_start`; os trechos
   e as palavras do corte estão em tempo da pregação (cli.md §8.3, `CutLayers.tsx`). O plano
   não diz de onde vem `sermon_start` nem onde se converte. Ajuste: a tela do corte carrega a
   pregação (`GET /api/sermons/{sermon_id}`, já pedida pelo `useTrail`) e converte num só
   lugar (`live = sermon_start + t`).
2. **`nextSegment(t)`** como assinatura: só pelo tempo é ambíguo com `out_of_order` (o tempo
   de um trecho pode cair dentro de outro). Ajuste: controlador com índice atual
   (`next(index, t)`), testado com o exemplo do cli.md §8.3.
3. **Origem das palavras**: `/preview` não traz palavras nem `word_id`; a legenda palavra a
   palavra e o `PUT /words/{word_id}` dependem de `words` de `GET /api/cuts/{id}`. Ajuste:
   estender o tipo `Cut` em `api/types.ts` (hoje só id, sermon_id, title, status) com
   `text`, `duration`, `segments`, `words`, `caption`, e registrar no plano.
4. **ADR-0023**: o nível 3 não carrega o YouTube — registrar como decisão; a tela usa só
   `players.video`. Reaproveitar `PlayerFactoryContext` e `fakePlayers` (item 22), sem
   duplicar dublês.
5. **Contexto de código × Passo 5**: o contexto diz "rotas, CHANGELOG, arquitetura", mas o
   Passo 5 só cita CHANGELOG; rotas não têm passo. Ajuste: rota `/cuts/:id` no Passo 1 e
   `docs/architecture/README.md` no Passo 5.
6. **Fonte da legenda**: o pacote tem só Open Sans Bold (`assets/fonts`), não há rota que
   liste fontes (só `details.choices` num 400), e a ADR-0022 proíbe fonte de outro host. O
   protótipo lista seis. Ajuste: Fonte com as opções conhecidas (a atual; padrão Open Sans
   Bold) e a fonte servida pelo build (`@fontsource/open-sans` 700) ou fallback declarado;
   registrar como aproximação.
7. **Escalas**: o protótipo usa `cqw` (4–10) e borda/10; a API usa px no quadro 1080
   (`size` 24–160, `border` 0–12, `offset` 10–90). Ajuste: o formulário usa as faixas da API e
   a prévia converte `px/1080`; registrar a fórmula.
8. **Itens do protótipo sem decisão no plano**: (a) botão olho na camada Legenda da timeline
   (liga/desliga, protótipo l.1221); (b) seção "Correções de grafia" com Desfazer na aba
   Legenda (PUT com o original remove a correção, api.md); (c) alternância 9:16/16:9 do nível
   3. A spec não pede nenhum. Opção conservadora do QA: fora da barra; o plano deve dizer
   "fora" (ou incluir com passo próprio). (c) fica fora (spec diz só 9:16).
9. **Bloqueio ao sair do campo**: o protótipo fecha o campo e mostra aviso; a spec diz
   "mensagem de bloqueio no lugar". Barra adotada: em Enter e em blur a palavra fica
   inalterada e a mensagem aparece junto à legenda; o plano deve dizer se o campo fica aberto.
   A mensagem não repete o texto digitado (ADR-0015; o `checkWord` do protótipo repete).
10. **"Salvo"** (Requisitos gerais) não aparece no plano; entra na barra dos Passos 3 e 4.

## Rodada 1 — 2026-10-26 — working tree sobre d8b0342

**baseline_commit**: d8b0342802f166a759f2dd5f63d2655bc139681b
**Componentes avaliados**: `apps/web` (`src/features/cut/`, `app/routes.tsx`, `api/`, `test/`,
`ui/app.css`, `main.tsx`); `CHANGELOG.md`; `docs/architecture/README.md`. Nenhum arquivo de
`apps/api` nem de `packages` no diff.
**Suítes**: web ✅ (241 / 0 falhas) · typecheck ✅ · lint ✅ · build ✅ · Python (regressão,
`uv run pytest`) ✅ (1510 / 0 falhas)
**Mutações** (cópia no scratchpad): 21 de 21 mortas, incluindo as 11 cobradas no plano de QA,
mais `>=` na pausa, sem quebra por frase, sem trim, valor igual com PUT, Desfazer com a
correção, bloqueio repetindo o texto digitado, YouTube no nível 3, sem escala px/1080.
**390 px**: verificação própria em Chromium headless sobre o build (porta 8797, `/api` pelas
fixtures): abas Texto e Legenda com `scrollWidth` 390, nenhum elemento fora da tela, quadro
9:16 243×432, sem erro de página.
**Barra ajustada pelo orquestrador**: Passo 2 (b) julgado com "> 0,6 s" (o render
`vertical/captions.py:97` usa `>`); o teste "a pause of 0.6 s keeps" fixa isso e a mutação
`>=` morre.
**Comentários**: todos de tipo da política (contrato público em JSDoc, como no baseline;
intenção, referência a ADR/docs, alerta em `WordEditor.tsx:32`); nenhuma diretiva de
ferramenta, nenhum TODO.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Prévia | PASS | `sequence.test.ts` (18, exemplo `out_of_order` do cli.md §8.3, trecho único, fim, `pointAt`/`cutTimeOf`); `CutPage.test.tsx`: só `players.video` com `/api/sermons/12/video`, `seeks` em tempo da live, pausa no fim, não volta ao 1º trecho, timeline proporcional e clique, trava `held` não bloqueia, 404 "Corte não encontrado."; `routes.test.tsx` |
| 2 — Legenda na prévia | PASS | `captions.test.ts` (frase, pausa 0,59/0,6/>0,6, `currentWord` na fronteira, `captionCss` por valor, px/1080 → cqw, sombra); `CutPage.test.tsx` palavra a palavra com `moveTo` inclusive no salto entre trechos, `corrected`, `enabled=false` sem legenda |
| 3 — Abas e formulário | PASS | `CutTabs.test.tsx` (8: abre em Texto, camada abre Legenda, fechar/prévia/vídeo/transporte voltam, painel e palavra não fecham); `CaptionTab.test.tsx` (18: 9 controles em linhas sem Salvar, PATCH só do campo após 400 ms, um PATCH para mudanças rápidas, Posição → Altura, "Salvo", 400 junto ao campo, Restaurar padrão por DELETE) |
| 4 — Grafia na prévia | PASS | `WordEditor.test.tsx` (11: clique duplo pausa e foca, Enter/blur com trim, valor igual sem PUT, Esc, Enter+blur um PUT, 409 junto à legenda sem o texto digitado e campo aberto, 400, Correções de grafia, Desfazer com o original) |
| 5 — Documentação | PASS | `CHANGELOG.md` ("Não lançado", item 24); `docs/architecture/README.md` (`features/cut`, Open Sans 700); rota `/cuts/:id` → `CutPage` |

### Critérios de aceite
- ✅ Prévia: trechos na ordem, pulando intervalos — `CutPage.test` "plays the segments in the cut's order…", "does not go back into the first segment…"; `sequence.test`
- ✅ Prévia: legenda palavra a palavra com o estilo — `CutPage.test` "follows the speech word by word…", "draws the caption with the cut's style"
- ✅ Abas: abre em Texto; camada abre Legenda; fechar/clique fora volta — `CutTabs.test`
- ✅ Estilo: 9 controles refletem e salvam sozinhos — `CaptionTab.test` (`test.each` por campo, fonte, Legenda Não)
- ✅ Estilo: Restaurar padrão — `CaptionTab.test` "restores the church's style…"
- ✅ Grafia: clique duplo pausa e abre; Enter/sair salva; Esc cancela — `WordEditor.test`
- ✅ Correções de grafia com Desfazer — `WordEditor.test` "lists the cut's fixes…", "undoes a fix…"
- ✅ Borda — trava de grafia: mensagem no lugar, palavra inalterada, campo aberto — `WordEditor.test` "shows the spelling lock's block…", "does not send the blocked text again…"
- ✅ Borda — legenda desligada — `CutPage.test` "draws no caption…", `CaptionTab.test` "turns the caption off…"
- ✅ Borda — 390 px — regra `@media (max-width: 860px)` com `.l3` em uma coluna + verificação própria em Chromium headless
- ✅ FR-001 — `CutPage.test` "plays the sequence the API's preview gives", "previews … never on YouTube"
- ✅ FR-002 — `captions.test` `captionCss`; `CutPage.test` estilo da legenda
- ✅ FR-003 — `CaptionTab.test` (PATCH/DELETE); `WordEditor.test` (PUT)
- ✅ 1.1.g — não bloqueada pela trava — `CutPage.test` "loads and plays the preview while the processing lock is held"
- ✅ ADR-0023 — sem YouTube no nível 3 — `CutPage.test` (mutação morta)
- ✅ Requisitos gerais — "Salvo" e motivo junto ao campo — `CaptionTab.test`, `WordEditor.test`
- ✅ plan Verificação — typecheck, lint, testes e build limpos

### Veredito geral: PASS
Os 5 passos `[x]` PASS, 17/17 critérios cobertos, suítes web e Python verdes, 21/21 mutações
mortas. Fora da barra, como decidido: botão olho da camada e alternância 9:16/16:9.
