## Plano de QA

baseline_commit: ac5446470fa6834fce499fe55f4016b8d5c118ac

19:27  📐 BARRA   caixa abre com as opções salvas do corte e a estimativa
       openCut + fakeApi com render_options fora do padrão; query
       exata do GET da estimativa; aria-pressed dos nove controles

19:28  📐 BARRA   estimativa com debounce 300 ms e sem corrida
       vi.useFakeTimers + userEvent(advanceTimers); resposta segurada
       da 1ª estimativa liberada depois da 2ª; signal.aborted

19:29  📐 BARRA   exportar: POST, progresso, done, failed, ocupado
       fakeEventSource.emit + close; corpo exato do POST; apiError
       409 busy; lock de render na barra de status

19:30  📐 BARRA   lista e Baixar
       links com href /api/renders/{id}/file e atributo download;
       nenhum fetch no clique; resumo das opções por tabela

19:31  🧬 EXIGE   mapa Sim/Não invertido em fillers/stammers  ·  vermelha
       prova que "Remover hesitações: Sim" vira fillers=remove

19:31  🧬 EXIGE   booleano como texto no POST ("false")  ·  vermelha
       prova que o corpo é estrito (docs/api.md §1)

19:32  🧬 EXIGE   sem abort da estimativa anterior  ·  vermelha
       prova o AbortController; hoje o fakeApi não o veria

19:32  🧬 EXIGE   sem close() no done/failed  ·  vermelha
       prova docs/api.md §3 (reconexão do navegador)

19:33  🧬 EXIGE   lista não recarregada no done  ·  vermelha
       prova que a exportação nova aparece no corte

19:33  🧬 EXIGE   otherWork ignorando o lock do próprio corte  ·  vermelha
       prova que o corte não exporta duas vezes ao ser reaberto

19:34  ⚠️ LACUNA  types.ts/client.ts fora do Contexto de código
       Cut sem render_options/renders; sem isso, passo 1 não começa

19:34  ⚠️ LACUNA  quem monta o resumo das opções
       API devolve objeto; sem função de resumo, passo 3 fica PARCIAL

19:35  ⚠️ LACUNA  "botão no topo" contra o padrão do item 22
       .top é do Layout; seguir ProcessButton dentro do nível

19:35  ⚠️ LACUNA  legenda com dois donos (item 24 × caption do POST)
       caixa deve partir de useCaptionStyle; senão passo 1 PARCIAL

19:36  ⚠️ LACUNA  fakeApi descarta init.signal
       sem expor o signal, o cancelamento (passo 1 f) fica PARCIAL

19:36  ⚠️ LACUNA  opções antigas após exportar; autosave pendente
       recarregar o corte no done; bloquear Exportar com gravação
       pendente ou registrar limitação

19:37  ⚠️ LACUNA  lista no menu (protótipo) × RendersList solta
       nível 3 segue o menu; card do nível 2 fora deste item

## Rodada 1 · implementador

19:33  🔴 RED    opens Exportar 9:16 with the cut's title and the
       prototype's groups and options
       Exportar → "Exportar 9:16…" abre a caixa modal com o título do
       corte, os quatro grupos e os nove controles do protótipo
       QA passo 1 (a); FR-001; L3 (botão no CutLevel), L8 (menu)
       Unable to find an accessible element with the role "button" and
       name "Exportar"

19:34  🟢 GREEN  opens Exportar 9:16 with the cut's title and the
       prototype's groups and options  ·  1 passed

19:34  🟢 GREEN  closes with Cancelar/Fechar, saving nothing  ·  3 passed
       verde de saída: o fechar veio com o GREEN anterior; sem produção
       nova. QA passo 1 (a)(h)

19:34  🟢 GREEN  opens with the cut's saved options and the caption as
       the Legenda tab has it  ·  4 passed
       verde de saída (L4); mutação manual (render_options.caption no
       lugar de caption.style.enabled) o derruba. QA passo 1 (b)

19:34  🔴 RED    asks the estimate once on opening and shows its duration
       ao abrir, um GET da estimativa com as nove opções na query e a
       duração formatada no rodapé
       QA passo 1 (c); FR-001
       Unable to find an element with the text: 1:01

19:35  🟢 GREEN  asks the estimate once on opening and shows its duration
       ·  5 passed

19:35  🟢 GREEN  asks the estimate again when <opção> changes (10 casos)
       ·  15 passed
       verde de saída: a estimativa já seguia as opções; mutação manual
       (Sim/Não invertido em fillers/stammers) derruba 3 casos.
       QA passo 1 (d) e mapa de opções

19:35  🔴 RED    waits 300 ms after the last change to ask the estimate,
       with the last options
       três mudanças em menos de 300 ms dão um só GET, com o último
       estado, e nenhum antes dos 300 ms
       QA passo 1 (e); Decisão técnica "Estimativa"
       expected { early: 4, asked: [ …(3) ] } to deeply equal
       { early: 1, …(1) }

19:35  🟢 GREEN  waits 300 ms after the last change to ask the estimate,
       with the last options  ·  16 passed

19:36  🔴 RED    cancels the estimate a newer one replaces, and never shows
       its late answer
       a 1ª estimativa segurada e liberada depois da 2ª não sobrescreve
       a 2ª; o fetch da 1ª recebeu um signal abortado
       QA passo 1 (f); L5; Decisão técnica "Estimativa"
       received { olderAborted: undefined, shown: "Duração estimada 1:39" }

19:36  🟢 GREEN  cancels the estimate a newer one replaces, and never shows
       its late answer  ·  17 passed

19:36  🔴 RED    says why the estimate failed on a refusal / no network,
       keeping Exportar
       erro 400 ou de rede na estimativa mostra o motivo na caixa e
       Exportar continua disponível
       QA passo 1 (g)
       Unable to find an element with the text: Valor inválido para
       pauses.

19:37  🟢 GREEN  says why the estimate failed on a refusal / no network,
       keeping Exportar  ·  19 passed

19:37  ✅ PASSO 1/4 — Caixa e estimativa  ·  +19 testes  ·  suíte 260

19:37  🔴 RED    launches the export with the dialog's nine options as
       JSON, and closes it
       Exportar na caixa faz o POST com as nove opções da caixa, os
       booleanos como booleanos do JSON, e fecha a caixa
       QA passo 2 (a); FR-001; docs/api.md §1 (corpo estrito)
       expected <div class="modal xmodal" …(3)>…(3)</div> to be null

19:38  🟢 GREEN  launches the export with the dialog's nine options as
       JSON, and closes it  ·  1 passed

19:38  🔴 RED    follows the export's events, its progress on the level's
       button
       o 202 abre o EventSource da tarefa; progress 0.35 deixa o botão
       do nível desabilitado com "Exportando 35%"
       QA passo 2 (b); spec "progresso por eventos"; L3
       expected [] to have a length of 1 but got +0

19:38  🟢 GREEN  follows the export's events, its progress on the level's
       button  ·  2 passed

19:38  🔴 RED    closes the events on done, offers Exportar again and reads
       the cut and its exports
       no done o EventSource fecha, o botão volta a "Exportar" e a tela
       relê o corte (opções salvas) e GET /api/cuts/34/renders
       QA passo 2 (c); L6; docs/api.md §3
       expected +0 to be 1 // Object.is equality

19:39  🟢 GREEN  closes the events on done, offers Exportar again and reads
       the cut and its exports  ·  3 passed

19:39  🔴 RED    says why the export failed, closing the events and
       registering nothing
       failed fecha o EventSource, mostra o motivo em role="alert" e não
       relê a lista
       QA passo 2 (d); spec borda "Falha"
       Unable to find role="alert"

19:39  🟢 GREEN  says why the export failed, closing the events and
       registering nothing  ·  4 passed

19:39  🔴 RED    keeps Exportar off while the machine works for another
       resource, saying so
       lock de outro recurso: Exportar da caixa desabilitado e aviso
       "Máquina ocupada: …", como o ProcessButton
       QA passo 2 (e); spec borda "Máquina ocupada"
       Unable to find an element with the text: /^Máquina ocupada/

19:39  🟢 GREEN  keeps Exportar off while the machine works for another
       resource, saying so  ·  5 passed
       refactor: otherWork(lock, resource) sai do ProcessButton para
       status/StatusBar.tsx, usado pelos dois; ProcessButton verde

19:40  🔴 RED    says why the API refused the export (busy /
       sermon_not_processed / invalid_argument), following nothing
       recusa do POST (409 busy na corrida com o polling, 409, 400)
       mostra a mensagem na caixa, sem EventSource
       QA passo 2 (e)(f)
       Unable to find role="alert"

19:40  🟢 GREEN  says why the API refused the export (3 casos), following
       nothing  ·  8 passed

19:40  🟢 GREEN  says which cut the machine exports and how far it got
       ·  StatusBar 1 passed
       prova de regressão (QA passo 2 g): passa sem produção; a
       fixture busyMachine passa a pôr o lock em "cut {id}" no render

19:40  🔴 RED    follows its own export, running when the cut is opened,
       without exporting again
       ao reabrir o corte com o próprio render em running_tasks, o
       botão segue a tarefa pelo SSE e mostra o progresso, desabilitado
       QA passo 2 (h); L3
       Unable to find role="button" and name "Exportando 35%"

19:41  🟢 GREEN  follows its own export, running when the cut is opened,
       without exporting again  ·  9 passed

19:41  🔴 RED    keeps Exportar off while the cut's own lock is held by an
       export it cannot follow
       lock em "cut 34" sem tarefa em running_tasks (ex.: CLI com
       --wait): a caixa não deixa exportar de novo
       QA mutação "otherWork ignorando o lock do próprio corte"; L3
       Unable to find an element with the text: /^Máquina ocupada/

19:41  🟢 GREEN  keeps Exportar off while the cut's own lock is held by an
       export it cannot follow  ·  10 passed

19:41  🟢 GREEN  reopens the dialog with the options the finished export
       used  ·  11 passed
       verde de saída (L6, QA passo 2 i): o refresh do done já relia o
       corte; mutação manual (sem setOptions no refresh) o derruba

19:42  🔴 RED    shows on the Legenda tab the caption switch the accepted
       export saved
       aceito o POST com caption=false, a aba Legenda passa a "Não"
       sem PATCH (o POST já gravou o mesmo estado de cut caption)
       L4; docs/api.md §2 (caption liga/desliga a legenda)
       expected { legenda: 'Sim', patches: +0 } to deeply equal
       { legenda: 'Não', patches: +0 }

19:42  🟢 GREEN  shows on the Legenda tab the caption switch the accepted
       export saved  ·  12 passed

19:43  🔴 RED    waits for the caption's pending save before exporting,
       saying Salvando…
       com o autosave da legenda pendente (PATCH segurado), o Exportar
       da caixa fica desabilitado como "Salvando…"; gravado, volta
       L7
       Unable to find an accessible element with the role "button" and
       name "Salvando…"

19:43  🟢 GREEN  waits for the caption's pending save before exporting,
       saying Salvando…  ·  13 passed

19:43  🔴 RED    waits for a spelling fix being saved before exporting,
       saying Salvando…
       com o PUT de grafia segurado, o Exportar da caixa fica
       "Salvando…" desabilitado; gravado, volta
       L7
       Unable to find an accessible element with the role "button" and
       name "Salvando…"

19:44  🟢 GREEN  waits for a spelling fix being saved before exporting,
       saying Salvando…  ·  14 passed

19:44  ✅ PASSO 2/4 — Exportar com progresso  ·  +15 testes  ·  suíte 275

19:44  🔴 RED    sums up <opções> as “<resumo>” (11 casos)
       resumo humano das opções de uma exportação: resolução, com/sem
       legenda e o que foge do padrão de docs/cli.md §8.7
       QA passo 3 (a); L2 (função pura, por tabela); xSummary
       Failed to resolve import "./exportSummary"

19:44  🟢 GREEN  sums up <opções> as “<resumo>” (11 casos)  ·  11 passed

19:44  🔴 RED    lists the cut's exports in the Exportar menu, newest
       first, with date, duration and options
       o menu do Exportar lista as exportações da mais recente para a
       mais antiga, com data, 9:16, duração e resumo
       QA passo 3 (a)(d); FR-002; L8; feature 1.1.i
       Unable to find an accessible element with the role "list" and
       name "Exportações"

19:45  🟢 GREEN  lists the cut's exports in the Exportar menu, newest
       first, with date, duration and options  ·  1 passed

19:45  🟢 GREEN  downloads each export from the API's file route, without a
       call of its own  ·  3 passed
       verde de saída (QA passo 3 b): veio com a lista; mutação manual
       (sem o atributo download) o derruba

19:45  🟢 GREEN  shows no Exportações in the menu while the cut has none
       ·  3 passed
       verde de saída (QA passo 3 c), como o protótipo

19:46  🟢 GREEN  lists the new export once the export is done  ·  4 passed
       verde de saída (QA passo 2 c + 3 a): o refresh do done já relia
       a lista; mutação manual (sem setRenders) o derruba

19:46  ✅ PASSO 3/4 — Lista e download  ·  +15 testes  ·  suíte 290

19:47  ✅ PASSO 4/4 — Documentação  ·  +0 testes  ·  suíte 290
       CHANGELOG (Não lançado, item 25); docs/architecture/README.md:
       web por feature e §5.3 (relê corte e lista no done; Baixar)

19:47  🏁 FINAL  suíte web 290 passed (27 arquivos)  ·  typecheck, lint e
       build limpos

19:48  🔴 RED    waits for the church's caption style being restored before
       exporting
       "Restaurar padrão" com o DELETE segurado também é gravação
       pendente da legenda: Exportar fica "Salvando…"
       L7
       Unable to find an accessible element with the role "button" and
       name "Salvando…"

19:48  🟢 GREEN  waits for the church's caption style being restored before
       exporting  ·  15 passed

19:48  🏁 FINAL  suíte web 291 passed (27 arquivos)  ·  typecheck, lint e
       build limpos

## Rodada 1 · QA

19:50  📊 SUÍTE  web 291 passed  ·  0 failed (27 arquivos)
       typecheck, lint e build limpos; regressão Python 1510 passed

19:51  🔎 QA     passo 1/4 — Caixa e estimativa  ·  ✅ PASS
       (a)–(h) da matriz cobertos em ExportDialog.test.tsx: nove
       controles, opções salvas, query exata, debounce, abort e corrida

19:51  🔎 QA     passo 2/4 — Exportar com progresso  ·  ✅ PASS
       POST com corpo exato, progresso, done/failed com close, 409/400,
       lock próprio e alheio, L4, L6 e L7 (Salvando…) em ExportButton

19:52  🔎 QA     passo 3/4 — Lista e download  ·  ✅ PASS
       lista no menu do Exportar (L8), ordem da API, resumo por tabela,
       <a href download> sem fetch, estado vazio

19:52  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       CHANGELOG "Não lançado" (item 25); architecture §4 e §5.3; sem
       arquivo de apps/api nem packages/core no diff

19:56  🧬 MUTAÇÕES · cópia de apps/web no scratchpad  ·  21 de 22 mortas
       ☠️  Sim/Não invertido em fillers/stammers              5 testes
       ☠️  booleano como texto no POST                        2 testes
       ☠️  estimativa sem signal / sem abort                  1 teste
       ☠️  lista não relida no done                           3 testes
       ☠️  lock do próprio corte ignorado                     1 teste
       ☠️  sem close() no evento final (useTaskEvents)        2 testes
       ☠️  debounce 0                                          1 teste
       ☠️  Exportar sem esperar gravação pendente (L7)        3 testes
       ☠️  legenda inicial de render_options (L4)             1 teste
       ☠️  sem atributo download                               1 teste
       ☠️  corte não relido no done (L6)                      2 testes
       ☠️  aba Legenda não adota o POST (L4)                  1 teste
       ☠️  lista sem inverter cut.renders                     2 testes
       ☠️  grafia / restaurar padrão nunca pendentes          1+1
       ☠️  resumo sem "sem fade"                               1 teste
       ☠️  relê a lista no failed                              1 teste
       ☠️  recusa da API não exibida                           3 testes
       ☠️  erro da estimativa desliga Exportar                 2 testes
       🚨  ended (tarefa já encerrada) removido   SOBREVIVEU — com o
           status atrasado listando o render em running_tasks, o botão
           voltaria a seguir a tarefa; fora da matriz, achado leve

19:57  🔎 QA     política de comentários  ·  ⚠️ leve
       useEstimate.ts:6 cita plan.md (specs/), não ADR nem docs/ (§5.5);
       o conteúdo é intenção, os demais comentários se enquadram
