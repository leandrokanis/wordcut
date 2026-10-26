## Plano de QA

baseline_commit: d8b0342802f166a759f2dd5f63d2655bc139681b

18:55  📐 BARRA   prévia toca os trechos na ordem, pulando os intervalos
       controlador puro com tabela de casos + FakePlayer.moveTo como
       relógio falso; asserção nos seeks em segundos da live

18:56  📐 BARRA   legenda acompanha palavra a palavra com o estilo
       moveTo palavra a palavra; palavra atual por aria-current/data-now;
       estilo como valores (captionCss/custom properties), não pixels

18:57  📐 BARRA   abas, autosave com debounce 400 ms, restaurar padrão
       userEvent + vi.useFakeTimers + fakeApi contando PATCH/DELETE

18:58  📐 BARRA   grafia por clique duplo: pausa, Enter/blur/Esc, bloqueio
       fakeApi PUT /words + apiError 409 spelling_too_different

18:59  🧬 EXIGE   controlador que escolhe trecho só pelo tempo  ·  vermelha
       prova que out_of_order (cli.md §8.3) toca na ordem do corte

19:00  🧬 EXIGE   sem sermon_start na conversão de tempo  ·  vermelha
       prova que PlayerLike recebe tempo da live (ADR-0023)

19:01  🧬 EXIGE   Enter+blur mandando dois PUTs; Esc mandando PUT  ·  vermelha
       prova o ciclo do campo de grafia

19:02  ⚠️ LACUNA  plano não converte tempo da pregação em tempo da live
       sem sermon_start, Passo 1 fica PARCIAL

19:03  ⚠️ LACUNA  nextSegment(t) só pelo tempo é ambíguo com out_of_order
       sem índice atual, Passo 1 fica FAIL no caso do cli.md §8.3

19:04  ⚠️ LACUNA  /preview não traz palavras nem word_id
       sem words de GET /api/cuts/{id}, Passos 2 e 4 não fecham

19:05  ⚠️ LACUNA  fonte da legenda: só Open Sans Bold, sem rota de fontes
       e sem host externo (ADR-0022); Fonte fica PARCIAL sem decisão

19:06  ⚠️ LACUNA  -webkit-text-stroke e cqw somem no style do jsdom
       sem captionCss puro ou custom properties, estilo não é provável

19:07  ⚠️ LACUNA  390 px não é provável em jsdom
       sem verificação manual em Chromium headless, fica PARCIAL

## Rodada 1 · implementador

19:01  ▶️ PASSOS   1, 2, 3, 4, 5 (todos os `- [ ]`; qa.md sem rodada anterior)
       decisões do orquestrador 1–11 registradas no plan.md e na spec

19:01  --- Passo 1: Prévia ---

19:01  🔴 RED    sequence: next(segments, index, t), cutTimeOf, pointAt
       ao fim de um trecho pede o início do seguinte na ordem do corte;
       no fim do último, termina; o exemplo fora de ordem do §8.3 não
       volta ao 1º trecho; tempo do corte nos dois sentidos
       barra passo 1 (a)(b); decisão 2 do orquestrador; cli.md §8.3
       Failed to resolve import "./sequence"

19:01  🟢 GREEN  sequence: next(segments, index, t), cutTimeOf, pointAt  ·  18 passed

19:02  🔴 RED    previews the cut on the sermon's processed video, never on
       YouTube
       /cuts/34 monta a tela do corte com só players.video(el,
       sermon_start) e src=/api/sermons/12/video
       barra passo 1 (c)(f); FR-001; ADR-0023; decisões 4 e 5
       Unable to find a label with the text of: Prévia do corte

19:03  🟢 GREEN  previews the cut on the sermon's processed video, never on
       YouTube  ·  1 passed

19:03  🔴 RED    plays the segments in the cut's order, skipping the gaps, in
       time of the live; pauses at the end of the last segment; does
       not go back into the first segment while the third plays
       FakePlayer.moveTo como relógio: seeks em segundos da live
       (sermon_start + t) e playing=false no fim, com o exemplo do §8.3
       spec · Prévia; barra passo 1 (a)(b); mutações sermon_start,
       pausa no fim e escolha só pelo tempo
       Unable to find ... role "button" and name "Reproduzir"

19:04  🟢 GREEN  plays the segments in the cut's order...; pauses at the end
       of the last segment; does not go back into the first  ·  22 passed

19:04  🔴 RED    draws each segment on the cut's timeline in proportion to the
       cut's duration; takes the preview to the right point of the right
       segment from the timeline; plays again from the point clicked
       timeline em tempo do corte: largura por duration, clique leva ao
       trecho certo (pointAt) e ao contador t / duração
       barra passo 1 (d)
       Unable to find ... role "region" and name "Timeline"

19:04  ℹ️ NOTA    loads and plays the preview while the processing lock is held;
       says the cut is missing when the API does not know it
       passam sem produção nova: vieram com o GREEN da rota (a tela não
       lê /api/status; o 404 de /api/cuts/99 dá "Corte não encontrado.")
       barra passo 1 (e)(f); ficam como guarda de regressão

19:05  🟢 GREEN  draws each segment on the cut's timeline...; takes the
       preview to the right point...; plays again from the point
       clicked  ·  27 passed

19:05  🔧 REFAC  rulerMarks exportado de sermon/Timeline e reaproveitado;
       LevelPlaceholder removido (sem uso); CutsPanel.test e routes.test
       passam a reconhecer o nível 3 pela "Prévia do corte", com
       shownCut/cutPreview das fixtures; + plays the sequence the API's
       preview gives (FR-001)  ·  suíte 181 passed

19:05  ✅ PASSO 1/5 — Prévia  ·  +29 testes  ·  suíte 182

19:05  --- Passo 2: Legenda na prévia ---

19:06  🔴 RED    captions: timedWords, captionBlocks, currentWord, captionCss
       palavras em tempo do corte com corrected ?? text; blocos sem
       misturar frases nem cruzar pausa > 0,6 s (vertical/captions.py
       usa ">"); permanência de 0,4 s; palavra atual com start ≤ t < end;
       estilo como valores (px/1080 → cqw, cores, fonte, sombra)
       barra passo 2 (a)(b)(c)(d); decisões 3, 6, 7 e 8
       Failed to resolve import "./captions"

19:07  🟢 GREEN  captions: timedWords, captionBlocks, currentWord, captionCss
       ·  18 passed

19:07  🔴 RED    follows the speech word by word, across the jump between
       segments; shows the cut's spelling fix in the caption; draws the
       caption with the cut's style
       moveTo palavra a palavra: bloco e palavra atual (aria-current),
       inclusive no salto entre trechos e na fronteira graça|paz.;
       corrected na legenda; custom properties do estilo
       spec · legenda acompanha com o estilo; barra passo 2 (a)(c)(d);
       FR-002; mutações "<=" no end e "ignorar corrected"
       expected [ [ null, [] ], ... ] to deeply equal [ …(6) ]

19:07  ℹ️ NOTA    draws no caption while the cut's caption is off passa sem
       produção (ainda não há legenda); fica como guarda da barra 2 (e)

19:08  🟢 GREEN  follows the speech word by word...; shows the cut's spelling
       fix in the caption; draws the caption with the cut's style  ·
       14 passed

19:08  🔧 REFAC  CutPage carrega e trata erro; CutLevel guarda o estado da
       tela; CSS da legenda lê as custom properties de captionCss();
       --font-cap e Open Sans 700 (@fontsource/open-sans) no build

19:08  ✅ PASSO 2/5 — Legenda na prévia  ·  +22 testes  ·  suíte 204

19:08  --- Passo 3: Abas e formulário ---

19:10  🔧 REFAC  openCut/live/SERMON_START movidos para src/test/cutLevel.ts,
       usados por CutPage.test e pelos testes novos  ·  50 passed

19:10  🔴 RED    opens on Texto, with the cut's assembled text; opens Legenda
       from the caption layer; goes back to Texto when Legenda is closed
       or on a click on the preview, the video track or the transport;
       keeps Legenda on a click inside the panel or on a caption word;
       switches between the tabs by their names
       regra das abas do protótipo (setLegendTab/pointerdown)
       spec · Abas; barra passo 3 (a)(b); mutação "clique no painel
       fecha a Legenda"
       Unable to find an accessible element with the role "tablist"

19:10  🟢 GREEN  tabs: Texto ao abrir, camada Legenda abre, fechar/clique fora
       volta a Texto, painel e palavra da legenda não fecham  ·  8 passed

19:12  🔴 RED    CaptionTab: rows with every control and no save button; each
       field saved by itself after 400 ms (PATCH só com o campo) and shown
       in the preview; font among the API's fonts; off takes the caption
       out; position takes the height; one PATCH for quick changes;
       "Salvo"; 400 next to the field keeping the saved value; Restaurar
       padrão (DELETE) and dropping a pending change
       userEvent/fireEvent + vi.useFakeTimers + fakeApi contando PATCH
       spec · Estilo; FR-003; barra passo 3 (c)(d)(e)(f)(g); decisão 11;
       mutações "sem debounce" e "PATCH com o estilo inteiro"
       Unable to find ... role "slider" and name "Tamanho" (18 failed)

19:13  🟢 GREEN  CaptionTab: form rows, autosave por campo com 400 ms,
       resposta vira o estado, "Salvo", erro junto ao campo, Restaurar
       padrão  ·  18 passed

19:13  🔧 REFAC  legenda da prévia renomeada "Legenda na prévia" (o grupo
       "Legenda" do formulário tem o mesmo nome); wordsOf compartilhado
       entre captions e TextTab; CSS do painel, abas e formulário como no
       protótipo; tsc e lint limpos  ·  suíte 230

19:13  ✅ PASSO 3/5 — Abas e formulário  ·  +26 testes  ·  suíte 230

19:13  --- Passo 4: Grafia na prévia ---

19:15  🔴 RED    WordEditor: double click pauses and opens the focused field;
       Enter/blur save trimmed (legenda, Texto, "Salvo"); unchanged sends
       nothing; Esc cancels; Enter+blur send one PUT; 409 block by the
       caption without the typed text, field open; blocked text not sent
       again on blur; 400 reason; fixes listed on Legenda; Desfazer sends
       the original
       fakeApi PUT /words + fakePlayers (pause) + userEvent
       spec · Grafia e Correções de grafia; FR-003; barra passo 4
       (a)–(f); decisões 9, 10 e 11; mutações "sem pause", "Esc com PUT",
       "Enter+blur com dois PUTs", "409 aplica a palavra"
       Unable to find ... role "textbox" and name "Corrigir “Deus”"

19:16  🟢 GREEN  WordEditor: grafia por clique duplo, Enter/blur/Esc,
       bloqueio junto à legenda, "Salvo", Correções de grafia com
       Desfazer  ·  11 passed

19:16  🔧 REFAC  useWordFixes (PUT /words) separado de CutLevel; arquivos
       novos de features/cut formatados (largura 100, como o vizinho);
       CSS do aviso junto à legenda e da lista de correções  ·  suíte 241

19:16  ✅ PASSO 4/5 — Grafia na prévia  ·  +11 testes  ·  suíte 241

19:16  --- Passo 5: Documentação ---

19:17  📝 DOCS   CHANGELOG ("Não lançado": nível 3 da web, item 24) e
       docs/architecture/README.md (features/cut, Open Sans 700 pelo npm)

19:17  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 241

19:18  🖥️ 390 PX  Chromium headless (playwright-core 1.58.2 como biblioteca)
       sobre o build (dist), /api por dublê local na porta 8794
       /cuts/34 nas abas Texto e Legenda e com o campo de grafia aberto:
       scrollWidth 390 = largura, nenhum elemento fora da tela fora da
       timeline (que rola), sem erro de página; quadro 9:16 243×432;
       legenda em Open Sans 700 carregada do build, 13,49 px = 243 × 60
       / 1080, contorno 1,35 px, #FFD600; formulário em linhas cabe em
       390 px. Prints só no scratchpad. A barra de status fixa no rodapé
       cobre uma linha no print de página inteira, como no nível 2.

19:18  📊 FINAL   web 241 passed · typecheck, lint e build limpos

## Rodada 1 · QA

19:19  📊 SUÍTE  web 241 passed  ·  0 failed (23 arquivos)

19:19  📊 SUÍTE  typecheck, lint e build limpos; Python 1510 passed
       nenhum arquivo de apps/api nem de packages no diff do baseline

19:22  🧬 MUTAÇÕES · cópia no scratchpad, src/features e src/app
       ·  21 de 21 mortas
       ☠️  next() só pelo tempo (sem índice)              3 testes
       ☠️  toLive sem sermon_start                        4 testes
       ☠️  sem pause() no fim do último trecho            2 testes
       ☠️  palavra atual com <= no end                    3 testes
       ☠️  legenda ignora corrected                       4 testes
       ☠️  pausa com >= 0,6 (o render usa >)              1 teste
       ☠️  sem quebra por frase                           8 testes
       ☠️  PATCH sem debounce                             3 testes
       ☠️  PATCH com o estilo inteiro                    13 testes
       ☠️  clique no painel fecha a Legenda               2 testes
       ☠️  clique duplo sem pause()                       1 teste
       ☠️  Esc manda PUT                                  3 testes
       ☠️  Enter+blur manda dois PUTs                     1 teste
       ☠️  409 aplica a palavra                           2 testes
       ☠️  enabled=false ainda desenha                    2 testes
       ☠️  sem trim / valor igual manda PUT           1 + 1 testes
       ☠️  Desfazer manda a correção                      1 teste
       ☠️  bloqueio repete o texto digitado               2 testes
       ☠️  player do YouTube no nível 3                   1 teste
       ☠️  sem a escala px/1080                           9 testes

19:23  🔎 QA     390 px  ·  Chromium headless próprio, porta 8797
       build no scratchpad, /api por fixtures; abas Texto e Legenda:
       scrollWidth 390, nada fora da tela, quadro 243×432, sem erro

19:24  🔎 QA     passo 1/5 — Prévia  ·  ✅ PASS
       sequence.test + CutPage.test; out_of_order, seeks na live, lock

19:24  🔎 QA     passo 2/5 — Legenda na prévia  ·  ✅ PASS
       captions.test + CutPage.test; pausa "> 0,6" pela decisão

19:24  🔎 QA     passo 3/5 — Abas e formulário  ·  ✅ PASS
       CutTabs.test + CaptionTab.test (18)

19:24  🔎 QA     passo 4/5 — Grafia na prévia  ·  ✅ PASS
       WordEditor.test (11), Correções de grafia com Desfazer

19:24  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       CHANGELOG "Não lançado" e docs/architecture (features/cut)
