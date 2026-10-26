## Plano de QA

baseline_commit 606a0f8db28cd7162ffe418444df564e22698b0c

13:04  📐 BARRA   nenhum módulo do core sem importador de produção
       grep de imports por módulo e por símbolo; ruff e mypy não acham
       código morto entre módulos, então a varredura é o instrumento

13:05  ⚠️ LACUNA  código morto transitivo fora do plan.md
       edit_list.py, plan_timeline, apply_corrections, validate_corrections,
       _retext, download_audio, Transcript.between morrem com short/sermon;
       sem removê-los o passo 3 fica FAIL

13:06  ⚠️ LACUNA  ramo da CLI anterior em contract.execute
       command is None → args.handler(args) e o comentário ficam mortos;
       fora do Contexto de código; sem remover, passo 3 FAIL

13:07  📐 BARRA   o que muda de lugar mantém comportamento
       test_pipeline, test_sermon_download_command e test_render_command
       verdes sem diff contra o baseline

13:08  🧬 EXIGE   LEAD_IN_S 0.3→0.4 e TAIL_S 1.5→1.4 movidos  ·  vermelha
       prova que test_pipeline cobre as bordas movidas de sermon.py

13:09  🧬 EXIGE   folder_name sem tirar caracteres inseguros  ·  vermelha
       prova que o teste de sermon_folder foi movido junto

13:10  ⚠️ LACUNA  destino de folder_name e parâmetro reference sem uso
       nenhum chamador passa reference; recomendado files.py e remover o
       parâmetro com o teste de ":"; mantido sem motivo, passo 2 PARCIAL

13:11  ⚠️ LACUNA  testes da linha do tempo dependem de EditList
       test_timeline e test_timeline_pauses usam plan_timeline; precisam
       passar a plan_segments sem perder caso, senão passo 2 PARCIAL

13:12  🧬 EXIGE   plan_segments sem remove_hesitations  ·  vermelha
       prova que os testes reescritos ainda cobrem a limpeza

13:13  📐 BARRA   wordcut short e os 7 antigos dão invalid_argument
       teste parametrizado com --json: saída 2 e details.choices igual
       aos 9 comandos novos; o plano não decidiu o teste

13:14  🧬 EXIGE   parser short registrado de novo  ·  vermelha
       prova que test_cli e o teste de invalid_argument pegam a volta

13:15  ⚠️ LACUNA  mortos herdados que o plano não cita
       Transcript.text() e CameraPath.max_offset() sem uso nem em teste;
       mantidos sem motivo, passo 3 PARCIAL; output_words, default_levels
       e role_of (só testes ou API planejada) ficam registrados

13:16  📐 BARRA   docs só com comandos que existem
       script extrai "wordcut <grupo> <ação>" de README e skills e roda
       --help; grep dos nomes antigos, --host, roteiro, palavras.json

13:17  ⚠️ LACUNA  README precisa manter a instalação do WhisperX
       LocalTranscriber manda ler "a seção Instalação do README"; sem ela,
       a borda do worker local fica PARCIAL

13:18  ⚠️ LACUNA  CHANGELOG com entradas de transição não lançadas
       cut→cut-sermon e overview com sentences nunca saem; recomendado
       ### Removido e retirar as duas entradas

13:19  📐 BARRA   ajuda dos grupos em 80 colunas
       COLUMNS=80 e main([grupo, "--help"]): nenhuma linha > 80 nos 8
       grupos e o exemplo de member literal em duas linhas

13:20  🧬 EXIGE   descrição com RawDescriptionHelpFormatter  ·  vermelha
       prova que cut --help (102 colunas no baseline) passou a quebrar

13:21  🧬 EXIGE   epílogo com o formatador padrão  ·  vermelha
       prova que o exemplo continua numa linha própria, sem ser re-quebrado

13:22  ⚠️ LACUNA  passo 5 ambíguo e add_command com o mesmo defeito
       o formatador vale para descrição e epílogo juntos; recomendado um
       formatador que quebra a descrição e mantém o epílogo, usado também
       em add_command; add_command não bloqueia

13:23  ⚠️ LACUNA  onde o mapa do passo 1 fica registrado
       o plano não diz; recomendado no tdd.md, entrada do passo 1; sem
       registro, passo 1 PARCIAL

## Rodada 1 · implementador

13:09  📋 MAPA   passo 1 — importadores de produção de cada módulo do core
       instrumento: varredura AST de imports e de nomes de módulo em
       string (registro de tarefas, `-m`) sobre packages/core/src,
       apps/cli/src e apps/api/src, sem os testes; bate com o mapa do QA
       remover: wordcut.short, wordcut.overview, wordcut.asr.remote ←
       só legacy.py; wordcut.sermon ← legacy.py e processing/pipeline.py
       (só as 4 constantes); wordcut.sermon_folder ← legacy.py, sermon.py,
       short.py, service/{sermons,renders}.py (só folder_name);
       wordcut.edit.edit_list ← legacy.py, short.py e edit/timeline.py
       (só plan_timeline, que morre com short.py)
       mover: LEAD_IN_S, TAIL_S, SECTION_MARGIN_S, SYNC_SEARCH_S →
       processing/pipeline.py (único consumidor); folder_name, sem
       reference, → files.py (service/sermons.py e service/renders.py);
       RANGE_MARGIN_S, transcribe_live, cut_sermon, CutResult saem
       remover símbolos: edit/timeline.plan_timeline; edit/text.
       apply_corrections, validate_corrections, _retext; youtube.YouTube.
       download_audio; Transcript.between; Transcript.text e
       CameraPath.max_offset (mortos já no baseline); ramo
       `command is None` de contract.execute
       divergência: os parâmetros start/duration de media.
       extract_speech_audio só eram passados por sermon.transcribe_live;
       ficam sem chamador e saem junto (mesmo motivo de reference)
       manter: asr, asr.local, asr.worker (-m), asr.prompt_echo, media,
       sync, timefmt, youtube, transcript, edit.{assemble,cleanup,energy,
       screen,text,timeline}, vertical.*, tasks.* (registro por nome);
       Timeline.output_words, Catalog.default_levels e
       service.members.role_of ficam (observável de teste, item 8 e
       FR-004 do item 17)

13:09  ✅ PASSO 1/5 — Mapa de uso  ·  +0 testes  ·  suíte 1275

13:10  🔴 RED    test_folder_name_strips_path_unsafe_characters (test_files)
       o nome legível sem caracteres inseguros vem de wordcut.files
       decisão L3 do plano; passo 2 (b) da barra
       E   ImportError: cannot import name 'folder_name' from
       'wordcut.files'

13:10  🟢 GREEN  test_folder_name_strips_path_unsafe_characters  ·  20 passed
       service/sermons.py, service/renders.py e legacy.py importam de
       wordcut.files; sai de sermon_folder.py com o teste de ":";
       mutação sem " ? / em PATH_UNSAFE: 1 failed (vermelha)

13:11  🔵 REFACTOR  LEAD_IN_S, TAIL_S, SECTION_MARGIN_S, SYNC_SEARCH_S
       movidos para processing/pipeline.py, mesmos valores e
       comentários; test_pipeline.py sem alteração, 18 passed
       mutação LEAD_IN_S 0.3→0.4: 4 failed; TAIL_S 1.5→1.4: 2 failed

13:11  🔵 REFACTOR  test_timeline.py e test_timeline_pauses.py → plan_segments
       os 12 casos de pausa, energia, ordem, limites e hesitação passam a
       dar os segmentos por palavras; saem só os 2 de EditList.reordered
       (hook e cronológico), que morre com edit_list.py · 12 passed
       mutação plan_segments sem remove_hesitations: 1 failed (vermelha)

13:12  ✅ PASSO 2/5 — Mover o que é usado  ·  +1 teste  ·  suíte 1271
       test_pipeline, test_sermon_download_command e test_render_command
       sem diff contra 606a0f8

13:13  🔴 RED    test_help_lists_every_command; test_a_command_of_the_
       previous_cli_is_an_invalid_argument[info…short]
       --help só com os 9 novos; cada um dos 7 antigos → invalid_argument,
       saída 2 e details.choices igual aos novos
       cenário "comandos antigos não existem mais"; FR-001; decisão L6
       E  assert (0, False) == (0, True) · E  KeyError: 'choices'
       · 8 failed

13:14  🟢 GREEN  test_cli.py  ·  8 passed (44 com test_cli_contract)
       git rm legacy.py e test_legacy_commands.py; legacy fora do
       __init__; contract.execute sem o ramo command is None e o
       comentário, _run recebe args.contract (obrigatório)

13:15  🔵 REFACTOR  código morto do core removido com git rm e com os testes
       módulos: short, overview, sermon, sermon_folder, asr/remote,
       edit/edit_list e test_{overview,sermon,sermon_folder,remote}.py
       símbolos: plan_timeline, apply_corrections, validate_corrections,
       _retext, YouTube.download_audio, Transcript.between,
       Transcript.text, CameraPath.max_offset, os parâmetros start e
       duration de extract_speech_audio; casos de test_text (3) e
       test_transcript (1) que só cobriam o removido saem
       docstrings de edit/, timeline e camera sem "edit list"
       varredura: todo módulo com importador de produção (cuts, service e
       vertical são pacotes dos submódulos usados; asr.worker por -m;
       tasks.* por registro); por símbolo, sobram só output_words,
       default_levels e role_of, como no mapa
       mutação parser short registrado de novo: 8 failed (vermelha)

13:16  ✅ PASSO 3/5 — Remover a CLI anterior e o código morto  ·  +8 testes
       ·  suíte 1261 (ruff e mypy limpos)

13:52  📝 DOCS   passo 4 — documentação, sem TDD (texto, não comportamento)
       README: sai a arquitetura anterior (host por SSH, pastas .json),
       entra "Como funciona" e o uso por sermon create … --process,
       sermon show/trim/process/download, cut list/preview/choose/
       fix-word/render, render list/download; Instalação mantém o venv do
       WhisperX em ~/.local/share/wordcut/venv (L7); cookies e LLM por
       settings; o uvicorn de dev perde o --host redundante
       skills: as duas reescritas em pré-requisitos, fluxo e onde ver o
       resultado (L11), sem critério próprio (remetem a criteria list e
       presets); git rm sugerir-cortes.md e exemplos.md; comentários do
       código que citavam sugerir-cortes.md apontam para base.md e o
       protótipo
       CONTRIBUTING: skills/ na árvore; arquitetura §4 sem "herdado da
       CLI anterior" e sem overview; CHANGELOG com ### Removido e sem as
       duas entradas de transição (L8)
       verificação: os 26 "wordcut <grupo> <ação>" de README e skills
       rodam --help com saída 0 e cada opção citada aparece na ajuda;
       varredura de comandos antigos, --host, roteiro, palavras.json,
       sugerir-cortes, exemplos.md e termos teológicos vazia

13:52  ✅ PASSO 4/5 — Documentação e skills  ·  +0 testes  ·  suíte 1261

13:53  🔴 RED    test_group_help_fits_an_80_column_terminal[8 grupos];
       test_command_help_fits_an_80_column_terminal;
       test_help_keeps_the_example_on_its_own_line
       com COLUMNS=80, nenhuma linha da ajuda passa de 80 e o exemplo do
       epílogo fica literal em duas linhas
       passo 5 do plano; decisão L9
       E  assert 102 <= 80 (cut) · E  assert 85 <= 80 (sermon download)
       · 2 failed, 16 passed

13:54  🟢 GREEN  test_cli.py  ·  18 passed
       HelpFormatter em add_group e add_command: quebra a descrição,
       preserva o texto que começa por "Exemplo:" e nomeia as ações do
       grupo como <ação> no usage (o {…} de 66 colunas do cut não quebra);
       o nome do argumento nos erros (details.argument "action") não muda
       mutação add_group com RawDescriptionHelpFormatter: 1 failed (cut);
       epílogo pelo preenchimento padrão: 1 failed (exemplo); vermelhas

13:56  🔵 REFACTOR  <ação> só na linha de usage (_format_args), não na lista
       de ações: test_cut_help_lists_its_actions e
       test_sermon_help_lists_its_actions seguem com o {…} sem alteração
       a descrição quebrada pode separar "—" de "administrador":
       test_member_command compara o texto da ajuda com os espaços
       normalizados (o comportamento, dizer que é do administrador, não
       muda) · apps/cli 444 passed

13:59  ✅ PASSO 5/5 — Ajuda dos grupos  ·  +10 testes  ·  suíte 1271
       verificação final: wordcut --help só com os 9 novos; wordcut short
       → invalid_argument, saída 2; pytest 1271 passed, ruff check,
       ruff format --check e mypy limpos; apps/api e apps/web intocados

## Rodada 1 · QA

14:01  📊 SUÍTE  1271 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos; diff contra 606a0f8
       não toca apps/api nem apps/web

14:02  🔎 QA     passo 1/5 — Mapa de uso  ·  ✅ PASS
       mapa no tdd.md bate com o do QA, transitivos e destinos inclusos;
       a divergência (start/duration) vem com motivo escrito

14:03  🔎 QA     ponto 1 · start/duration de extract_speech_audio  ·  aceito
       único chamador (processing) não os passa; mesmo critério de L3;
       sai só um -ss 0.000 de entrada, sem efeito; o comando do ffmpeg não
       tinha teste nem no baseline

14:04  🧬 MUTAÇÕES · passo 2 (cópia no scratchpad)  ·  7 de 8 mortas
       ☠️  LEAD_IN_S 0.3→0.4                             4 testes
       ☠️  TAIL_S 1.5→1.4                                2 testes
       ☠️  SECTION_MARGIN_S 30→29                        3 testes
       ☠️  SYNC_SEARCH_S 20→19                           2 testes
       ☠️  PATH_UNSAFE sem / ? "                         1 teste
       ☠️  plan_segments sem remove_hesitations          12 testes
       ☠️  plan_segments com fillers=False               1 teste
       🚨  plan_segments com stammers=False   SOBREVIVEU — fora da barra;
           sobrevive à suíte inteira, e os casos migrados são os mesmos
           do baseline: lacuna anterior a esta issue, não regressão

14:05  🔎 QA     passo 2/5 — Mover o que é usado  ·  ✅ PASS
       constantes e folder_name movidos com valores e teste; test_pipeline,
       sermon_download e render_command sem diff contra o baseline

14:06  🧬 MUTAÇÕES · passos 3 e 5  ·  5 de 5 mortas
       ☠️  parser short registrado de novo               8 testes
       ☠️  add_group com RawDescriptionHelpFormatter     1 teste
       ☠️  add_command com RawDescriptionHelpFormatter   1 teste
       ☠️  epílogo pelo preenchimento padrão             1 teste
       ☠️  usage com {…} em vez de <ação> ...            1 teste

14:07  🔎 QA     passo 3/5 — Remover a CLI anterior e o código morto  ·  ✅ PASS
       arquivos e símbolos fora; varredura AST: só asr.worker e tasks.*
       sem import (carregados por -m/registro); sobram output_words,
       default_levels e role_of, como no mapa

14:08  🔎 QA     ponto 2 · usage com <ação> ...  ·  aceito
       sem isso o {…} do cut passa de 80 colunas; docs/cli.md §3.1 usa
       <ação>; lista de ações e details.argument "action" intactos

14:09  🔎 QA     passo 4/5 — Documentação e skills  ·  ⚠️ PARCIAL
       28 comandos citados rodam --help e cada opção aparece; varredura
       vazia; mas 2.1.a-settings.md:14 ainda diz "O conteúdo inicial vem
       de skills/video-corte-vertical/sugerir-cortes.md" (decisão do
       orquestrador: dizer que veio dele e hoje está em criteria/texts/)

14:10  🔎 QA     passo 5/5 — Ajuda dos grupos  ·  ✅ PASS
       8 grupos a 80 colunas com no máximo 78; exemplo literal; fora da
       barra: sermon list --help 83 (choices no usage) e o exemplo de
       preset update 107, ambos de add_command

## Rodada 2 · orquestrador

- Achado da Rodada 1 (passo 4): `docs/requirements/features/2.1.a-settings.md:14` citava como atual o
  arquivo removido. Corrigido para dizer que o conteúdo inicial veio de `sugerir-cortes.md`
  (removido neste item) e hoje está em `packages/core/src/wordcut/criteria/texts/`. Edição só de
  documento, sem código; feita pelo orquestrador.

## Rodada 2 · QA

14:09  📊 SUÍTE  1271 passed  ·  0 failed
       ruff check, ruff format --check e mypy (91 arquivos) verdes

14:11  🔎 QA     passo 4/5 — Documentação e skills  ·  ✅ PASS
       2.1.a-settings.md:14 diz que o conteúdo inicial veio de
       sugerir-cortes.md (removido) e hoje está em criteria/texts/

14:11  🔎 QA     varredura de docs/ (fora prototype/ e inception.md)
       única menção a arquivo removido é a histórica de 2.1.a:14;
       cli.md:798 cita --host só na tabela de migração (§15)

14:12  🔎 QA     passos 1, 2, 3 e 5  ·  ✅ PASS (mantidos)
       a Rodada 2 só registra edição de documento; suíte 1271 verdes
