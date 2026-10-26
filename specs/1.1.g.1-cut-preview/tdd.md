## Plano de QA

baseline_commit: 8e972fc2ce7357ac96bed728b8cc09ac6a214cb1

09:35  📐 BARRA   preview_cut devolve trechos na ordem de montagem, com
       tempos da pregação, texto, out_of_order e a duração do show
       teste no core com corte de três trechos e valores à mão

09:35  🧬 EXIGE   critério antigo (marcar o trecho antes do mais cedo)  ·
       vermelha
       prova que a marca vai no trecho que volta no tempo (spec)

09:35  🧬 EXIGE   comparar com qualquer anterior, não o imediato  ·  vermelha
       prova a regra literal do plano: start < previous.end

09:35  🧬 EXIGE   < trocado por <=  ·  vermelha
       trecho que começa no fim exato do anterior não é fora de ordem

09:35  🧬 EXIGE   duração = fim do último − início do primeiro  ·  vermelha
       prova que é a soma das faixas, igual ao cut show

09:35  📐 BARRA   cut preview nunca bloqueado pela trava (§IV)
       CLI com lock_owner segurando a trava: saída 0 e resultado

09:35  🧬 EXIGE   envolver o preview em ProcessingLock.acquire  ·  vermelha
       se sobreviver, o teste da trava não prova nada

09:35  📐 BARRA   contrato da CLI: JSON, not_found → 3, texto com ↑
       main(argv) + capsys, no padrão de test_cut_command.py

09:35  ⚠️ LACUNA  plano manda marcar out_of_order em assembly.py
       AssembledSegment não conhece o vizinho; a marca vem do corte
       (AssembledCut ou serviço)

09:35  ⚠️ LACUNA  "mesmo critério do preview antigo" é falso
       EditList.reordered marca o trecho antes do mais cedo; barra
       segue a spec e a regra start < previous.end

09:35  ⚠️ LACUNA  "texto corrigido" sem correção no baseline
       texto original até o item 13; nenhum gancho criado aqui

09:35  ⚠️ LACUNA  docs/cli.md §8.3 sem formato do JSON nem regra da marca
       atualizar §8.3; sem isso, passo 3 fica PARCIAL

09:35  ⚠️ LACUNA  fixture da CLI com só dois trechos
       com dois, as mutações do critério antigo e do vizinho sobrevivem;
       o cenário pede três

## Rodada 1 · implementador

09:35  📝 PLANO  decisões D1–D7 e L1–L9 do QA registradas no plan.md
       marca em AssembledCut, texto sem correção (item 13 estende),
       três trechos no cenário, §8.3 com formato, regra e duração

09:36  🔴 RED    test_preview_plays_the_segments_in_cut_order_and_marks_
       the_one_that_goes_back_in_time
       três trechos A(tarde) → B(cedo) → C(entre B e A): ordem de
       montagem, tempos da pregação, texto, [false, true, false], 2,35 s
       spec, cenário "sequência da prévia"; FR-001; plano "Fora de ordem"
       ImportError: cannot import name 'preview_cut' from
       'wordcut.service.cuts'

09:36  🟢 GREEN  test_preview_plays_the_segments_in_cut_order_and_marks_
       the_one_that_goes_back_in_time  ·  1 passed

09:36  🛡️ GUARDA test_a_segment_that_starts_exactly_where_the_previous_
       one_ends_is_not_out_of_order
       trecho que começa no fim exato do anterior não volta no tempo
       plano "Fora de ordem" (start < previous.end); QA mutação c
       passou de primeira (o GREEN anterior já usa <); com < → <= fica
       vermelho: assert [False, True] == [False, False]; revertido

09:40  🛡️ GUARDA test_preview_lasts_as_long_as_the_shown_cut
       a duração da prévia é a do cut show do mesmo corte
       plano "Duração"; QA D5, mutação d
       passou de primeira (AssembledCut.duration já vinha do GREEN)

09:40  🛡️ GUARDA test_preview_of_a_cut_that_does_not_exist_is_not_found
       corte inexistente → WordcutError not_found, details.cut_id
       spec, borda "corte inexistente"; QA D6
       passou de primeira (_existing já levanta not_found)

09:40  🧬 MUTA   core: a (critério antigo), b (qualquer anterior),
       c (<=), d (fim − início), e (ordenar por start), f (sempre
       false): todas vermelhas no test_cut_preview.py; revertidas

09:40  ♻️ REFAC  out_of_order por pares (anterior, atual) com zip;
       strict=True no zip do serviço (ruff B905)  ·  28 passed

09:40  ✅ PASSO 1/3 — Serviço  ·  +4 testes  ·  suíte 28 (arquivos do
       passo)

09:40  🔴 RED    test_preview_with_json_prints_the_segments_in_cut_order_
       marking_the_one_that_goes_back
       cut preview <id> --json de um corte de três trechos: saída 0 e o
       objeto do passo 1 inteiro, com cut_id e duração
       spec, cenário "sequência da prévia"; FR-001; QA L7 (três trechos)
       assert (2, {'error': ... invalid_argument (ação preview não existe)

09:40  🟢 GREEN  test_preview_with_json_prints_the_segments_in_cut_order_
       marking_the_one_that_goes_back  ·  1 passed

09:41  🔴 RED    test_preview_without_json_prints_one_line_per_segment_
       with_an_arrow_only_on_the_jump_back
       sem --json: uma linha por trecho com os dois tempos, o texto e ↑
       só no trecho que volta no tempo
       spec, borda "sem --json … ↑ nos fora de ordem"; QA L8, mutação h
       At index 1 diff: ... 'Irmãos, graça', False) != ... True)

09:41  🟢 GREEN  test_preview_without_json_prints_one_line_per_segment_
       with_an_arrow_only_on_the_jump_back  ·  2 passed

09:42  🛡️ GUARDA test_preview_is_never_blocked_by_a_lock_held_elsewhere
       com lock_owner("render", "cut 34") segurando a trava, a prévia
       sai 0 com o resultado
       spec, cenário "nunca bloqueada"; FR-002; constituição §IV
       passou de primeira (a ação não toca a trava); QA mutação g
       (acquire em volta do run) deixa só este teste vermelho

09:42  🛡️ GUARDA not_found → 3, erro sem --json só no stderr, id mal
       formado → invalid_argument 2, --json antes/no meio/depois
       contrato da CLI, docs/cli.md §4–§5; QA matriz passo 2
       passaram de primeira (o contrato comum já cobre); QA mutação i
       (not_found → saída 1) deixa dois vermelhos

09:42  🧬 MUTA   cli: g (trava), h (↑ em todas / em nenhuma), i (código
       do not_found): todas vermelhas; revertidas

09:42  🔧 AJUSTE test_cut_command.py: --help do grupo lista preview e o
       teste de exemplo por ação inclui preview (wordcut cut preview 34
       --json); falhava porque a lista de ações mudou de propósito

09:42  ✅ PASSO 2/3 — CLI  ·  +9 testes (+1 parâmetro no teste de
       exemplo)  ·  suíte 41 (arquivos do passo)

09:43  📄 DOC    CHANGELOG [Não lançado]/Adicionado com wordcut cut preview
       <id>; docs/cli.md §8.3 com formato JSON, regra da marca (só o
       anterior imediato, fronteira, exemplo de três trechos), duração do
       cut show, linha legível e not_found  ·  sem TDD (documentação)

09:43  ✅ PASSO 3/3 — Documentação  ·  +0 testes

09:44  🏁 FINAL  suíte completa 941 passed (1 aviso do starlette, alheio)
       ruff check, ruff format --check e mypy limpos
       Verificação do plan.md marcada

## Rodada 1 · QA

09:48  📊 SUÍTE  941 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos

09:48  🧬 MUTAÇÕES · a–i da barra, numa cópia no scratchpad  ·  10 de 10
       mortas
       ☠️  a critério antigo (marca o que precede o mais cedo)   3 testes
       ☠️  b qualquer anterior em vez do imediato                3 testes
       ☠️  c < trocado por <=                                    1 teste
       ☠️  d duração = fim do último − início do primeiro        3 testes
       ☠️  e trechos ordenados por start                         3 testes
       ☠️  f out_of_order sempre false                           3 testes
       ☠️  g ProcessingLock.acquire em volta do _preview         1 teste
       ☠️  h ↑ em todas as linhas                                1 teste
       ☠️  h ↑ em nenhuma linha                                  1 teste
       ☠️  i not_found → saída 1                                 2 testes

09:48  🧬 MUTAÇÕES · guarda do not_found no core, sem mutação no diário
       ·  1 de 1 morta
       ☠️  preview_cut engole not_found e devolve prévia vazia   3 testes

09:48  🔎 QA     passo 1/3 — Serviço  ·  ✅ PASS
       preview_cut e AssembledCut.out_of_order seguem D1–D6; três trechos
       com valores à mão; a–f vermelhas

09:48  🔎 QA     passo 2/3 — CLI  ·  ✅ PASS
       JSON, texto com ↑, not_found 3, invalid_argument 2, --json em três
       posições, trava (lock_owner), --help com exemplo; g–i vermelhas

09:48  🔎 QA     passo 3/3 — Documentação  ·  ✅ PASS
       CHANGELOG [Não lançado]/Adicionado; §8.3 com formato, regra da
       marca com exemplo de três trechos, duração do cut show (L4)
