# QA — cli-migration — Remover a CLI anterior e reescrever README e skills

## Plano de QA — 2026-10-26

**baseline_commit**: 606a0f8db28cd7162ffe418444df564e22698b0c
**Componentes em escopo**: `packages/core` (pacote `wordcut`), `apps/cli` (pacote
`wordcut_cli`), documentação (`README.md`, `CONTRIBUTING.md`, `docs/architecture/README.md`,
`CHANGELOG.md`) e `skills/`. Fora: `apps/api`, `apps/web` (o diff contra o baseline NÃO DEVE
tocá-los; se tocar, roda-se também a suíte web de CONTRIBUTING §3.2).
**Suítes que valem como prova**: Python (core, cli), da raiz: `uv run pytest -q`;
`uv run ruff check . && uv run ruff format --check .`; `uv run mypy`. Um arquivo:
`uv run pytest <arquivo> -q`. Varredura de uso (somente leitura):
`grep -rnE "(from|import) +wordcut\.<módulo>( |$)|from wordcut(\.<pai>)? import .*\b<nome>\b" packages apps conftest.py --include=*.py`.
Varredura de documentação: `grep -rnE "wordcut (info|transcribe|transcribe-live|overview|cut-sermon|preview|short)\b|--host|roteiro|palavras\.json|sugerir-cortes|exemplos\.md" README.md CONTRIBUTING.md docs/architecture skills`.

### Mapa de uso no baseline (feito pelo QA, só com leitura e `grep`)

Importadores de produção de cada módulo candidato (fora os próprios testes):

| Módulo | Quem importa (produção) | Depois de remover `legacy.py` |
|---|---|---|
| `wordcut.short` | `legacy.py` | sem uso → remover com o código |
| `wordcut.overview` | `legacy.py` | sem uso → remover com `test_overview.py` |
| `wordcut.asr.remote` | `legacy.py` | sem uso → remover com `test_remote.py` (`--host` sai, cli.md §15) |
| `wordcut.sermon` | `legacy.py`, `processing/pipeline.py` (só `LEAD_IN_S`, `TAIL_S`, `SECTION_MARGIN_S`, `SYNC_SEARCH_S`) | `transcribe_live`, `cut_sermon`, `CutResult`, `RANGE_MARGIN_S` sem uso → remover com `test_sermon.py`; as quatro constantes mudam para `processing/pipeline.py`, único consumidor |
| `wordcut.sermon_folder` | `legacy.py`, `sermon.py`, `short.py`, `service/sermons.py` e `service/renders.py` (só `folder_name`) | `SermonFolder`, `default_root`, `LIVE_*`, `SECTION_VIDEO` sem uso → remover; `folder_name` muda de lugar com seus testes |
| `wordcut.edit.edit_list` | `legacy.py`, `short.py`, `edit/timeline.py` (só para `plan_timeline`) | **sem uso** (transitivo: `plan_timeline` também morre) → remover |
| `wordcut.asr.local`, `wordcut.asr` | `processing/__init__.py` | continuam usados (WhisperX local) |
| `wordcut.asr.worker`, `wordcut.asr.prompt_echo` | `asr/local.py` via `python -m wordcut.asr.worker` | continuam usados |
| `wordcut.media`, `wordcut.sync` | `processing`, `rendering`, `edit/energy` | continuam usados |
| `wordcut.timefmt` | `wordcut_cli/cut.py`, `wordcut_cli/sermon.py` | continua usado |
| `wordcut.youtube`, `wordcut.transcript` | `processing`, `service`, `edit`, `rendering`, `vertical`, `db` | continuam usados |
| `wordcut.edit.{assemble,cleanup,energy,screen,text,timeline}`, `wordcut.vertical.*` | `rendering`, `cuts` | continuam usados |

Símbolos que ficam sem uso em módulos que continuam (morrem junto com a CLI anterior):

| Símbolo | Único uso hoje | Destino |
|---|---|---|
| `edit/timeline.plan_timeline` | `short.py` | remover; os testes de `test_timeline.py` e `test_timeline_pauses.py` passam para `plan_segments` (o algoritmo continua vivo pela exportação) |
| `edit/text.apply_corrections`, `validate_corrections`, `_retext` | `short.py`, `edit_list.py` | remover; `test_text.py` mantém `tidy_joins` e `capitalize` |
| `youtube.YouTube.download_audio` | `sermon.py` | remover |
| `transcript.Transcript.between` | `sermon.py` | remover com o teste de `test_transcript.py` |
| `contract.execute`: ramo `command is None` → `args.handler(args)` e o comentário | comandos de `legacy.py` | remover; `command` deixa de ser opcional |
| parâmetro `reference` de `folder_name` | nenhum chamador o passa (nem `legacy.py`) | remover com o teste de `:` → `.` |

Sem uso nenhum já no baseline, herdados do domínio anterior: `Transcript.text()` e
`CameraPath.max_offset()` (nem testes). Só usados por testes: `Timeline.output_words`
(observável dos testes da linha do tempo), `Catalog.default_levels` (item 8) e
`service.members.role_of` (FR-004 do item 17, consumidor planejado em `1.2.a.2-api-identity`).

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Mapa de uso | (a) Mapa registrado (cada módulo do core → importadores → remover/mover/manter) e decidido antes da remoção. (b) Coincide com o mapa acima, inclusive o transitivo (`edit_list`, `plan_timeline`, `apply_corrections`, `download_audio`, `between`, ramo de `contract.execute`) e o destino de cada item movido; divergência só com motivo escrito | Leitura do registro do implementador (`tdd.md`, entrada do passo 1) contra esta tabela. Sem registro: PARCIAL |
| 2 — Mover o que é usado | (a) `LEAD_IN_S`, `TAIL_S`, `SECTION_MARGIN_S`, `SYNC_SEARCH_S` em `processing/pipeline.py` com os mesmos valores e comentários; nenhum import de `wordcut.sermon`. (b) `folder_name` num módulo que continua (recomendado `wordcut/files.py`, junto da cópia que usa o nome), uma definição só, importada por `service/sermons.py` e `service/renders.py`; teste de caracteres inseguros movido junto. (c) `test_timeline.py` e `test_timeline_pauses.py` passam a exercer `plan_segments` sem perder caso (pausas, energia, ordem, limites); asserções de `EditList.reordered` saem com ele. (d) Comportamento intacto: `test_pipeline.py` (`(999.7, 1101.5)` e as bordas com 0,3/1,5 s), `test_sermon_download_command.py` e `test_render_command.py` (`READABLE_NAME`) verdes **sem alteração** (`git diff 606a0f8 -- <arquivo>` vazio) | pytest dos arquivos citados; diff contra o baseline. Mutações exigidas (vermelhas): `LEAD_IN_S` 0.3→0.4 e `TAIL_S` 1.5→1.4 no novo lugar; `folder_name` sem remover `"`/`?`/`/`; trocar `plan_segments` por uma versão sem `remove_hesitations` (os testes reescritos precisam pegar) |
| 3 — Remover a CLI anterior e o código morto | (a) Apagados: `wordcut_cli/legacy.py`, `apps/cli/tests/test_legacy_commands.py`, `wordcut/{short,overview,sermon,sermon_folder}.py`, `wordcut/asr/remote.py`, `wordcut/edit/edit_list.py` e `test_{overview,sermon,sermon_folder,remote}.py`. (b) `legacy` fora de `wordcut_cli/__init__.py`; ramo `command is None`/`args.handler` e comentário fora de `contract.py`. (c) Símbolos da tabela acima removidos, com seus testes. (d) `test_cli.py` com `COMMANDS = "{criteria,cut,member,preset,render,sermon,settings,status,task}"`. (e) `wordcut short` (e cada um dos 7 antigos) → `invalid_argument`, saída 2, `details.choices` = os 9 novos. (f) Varredura: todo módulo de `packages/core/src/wordcut` tem importador de produção (ou é carregado por `-m`/registro de tipos: `asr.worker`, `tasks.{runner,process,render,suggest,diagnostic}`). (g) `Transcript.text()` e `CameraPath.max_offset()` removidos ou com motivo escrito (sem isso: PARCIAL). (h) Nenhum teste removido além dos de código removido (lista do diff de `tests/` conferida contra (a) e (c)) | `uv run pytest apps/cli/tests/test_cli.py -q` + teste novo de (e) com `main(["--json", nome])`; varredura de uso por módulo e por símbolo (comando no cabeçalho); `git diff --stat 606a0f8 -- '*/tests/*'`. Mutações exigidas (vermelhas): registrar de novo um parser `short` → teste de (d)/(e); restaurar `plan_timeline` sem chamador → a varredura por símbolo acusa (prova do instrumento, não do pytest) |
| 4 — Documentação e skills | (a) README, CONTRIBUTING, `docs/architecture/README.md` (§3 e §4: sem "herdado da CLI anterior", sem "reaproveitadas por `overview`") e skills sem nenhum comando antigo, `--host`, roteiro, `palavras.json`, pasta `~/Videos/Pregações`. (b) Todo `wordcut <grupo> <ação>` citado em README e skills existe: `uv run wordcut <grupo> <ação> --help` sai 0, e cada opção citada aparece nessa ajuda. (c) O fluxo `sermon create … --process`, `cut list`, `cut render`, `render download` aparece no README e nas skills. (d) `skills/video-corte-vertical/{sugerir-cortes,exemplos}.md` apagados e sem referência. (e) Skills como guia curto: pré-requisitos, fluxo com os comandos novos, onde ver o resultado; sem critério teológico próprio, inclusive no `description` do frontmatter (grep `cristológ|triunfalis|alegori|teologia frágil` vazio); critérios remetidos a `criteria list`/presets. (f) README mantém a instalação do ambiente do WhisperX em `~/.local/share/wordcut/venv` (a mensagem de `LocalTranscriber` aponta para "a seção Instalação do README"). (g) CHANGELOG `[Não lançado]` com `### Removido` (os 7 comandos, `--host`, as pastas com `.json`, os módulos e os dois arquivos da skill). (h) Sem nome de pessoa nos textos novos (constituição §VI) | Varredura de documentação (cabeçalho); script que extrai `wordcut \w+ [\w-]+` de README e `skills/**` e roda `--help`; leitura das skills e do diff de `CHANGELOG.md` e `docs/architecture/README.md` |
| 5 — Ajuda dos grupos | (a) Com terminal de 80 colunas, nenhuma linha de `wordcut <grupo> --help` passa de 80, nos 8 grupos (`criteria`, `cut`, `member`, `preset`, `render`, `sermon`, `settings`, `task`); `cut --help` (102 colunas no baseline) quebra. (b) O exemplo do epílogo fica literal: `Exemplo:` numa linha e `  wordcut member add assistente@exemplo.org --role assistant` na seguinte. (c) Teste novo no `apps/cli/tests` | `monkeypatch.setenv("COLUMNS", "80")` (o argparse lê a largura por `shutil.get_terminal_size`) e `main([grupo, "--help"])` com `capsys`. Mutações exigidas (vermelhas): `add_group` volta a `RawDescriptionHelpFormatter` para a descrição → (a); epílogo com o formatador padrão (que junta "Exemplo: wordcut member…" numa linha) → (b) |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Cenário "comandos antigos não existem mais": `--help` só com os novos; `wordcut short` → `invalid_argument` | Passo 3 (d) `test_cli.py` e (e) teste parametrizado com os 7 nomes antigos |
| Cenário "nenhum código morto" | Passo 3 (f), (g) varredura por módulo e por símbolo; passo 1 (b) mapa |
| Cenário "documentação coerente": só comandos que existem, com `sermon create … --process`, `cut list`, `cut render`, `render download` | Passo 4 (a), (b), (c) |
| Borda: constantes e funções usadas migram antes da remoção | Passo 2 (a), (b), (d) e mutações |
| Borda: ambiente do WhisperX e worker local continuam | `asr/{__init__,local,worker,prompt_echo}.py` presentes; `test_local.py`, `test_prompt_echo.py` e o caso `wordcut.asr.worker` de `test_pipeline.py` verdes sem alteração (diff vazio); passo 4 (f) |
| Borda: transcrição por SSH (`--host`) sai | Passo 3 (a) `asr/remote.py` apagado; passo 4 (a) sem `--host` nos docs |
| FR-001 comandos antigos removidos com testes | Passo 3 (a), (b), (d), (e), (h) |
| FR-002 módulos só da CLI anterior removidos; o usado movido sem mudar comportamento | Passos 2 e 3 |
| FR-003 README, CONTRIBUTING, arquitetura e skills só com a CLI nova | Passo 4 (a)–(d), (g) |
| FR-004 skills curtas, sem critérios teológicos próprios | Passo 4 (d), (e) |
| FR-005 quality gates limpos | `uv run pytest -q`, `ruff check`, `ruff format --check`, `mypy` verdes |
| Verificação · `wordcut --help` só com novos; `wordcut short` → `invalid_argument` | = cenário 1 |
| Verificação · nenhum módulo do core sem importador fora dos próprios testes | = cenário 2 |
| Verificação · README e skills só citam comandos existentes | = passo 4 (b) |
| Verificação · quality gates limpos | = FR-005 |

## Rodada 1 — 2026-10-26 — working tree sobre 606a0f8

**baseline_commit**: 606a0f8db28cd7162ffe418444df564e22698b0c
**Componentes avaliados**: `packages/core`, `apps/cli`, documentação (`README.md`,
`CONTRIBUTING.md`, `docs/architecture/README.md`, `CHANGELOG.md`, `docs/requirements`) e
`skills/`. `apps/api` e `apps/web` sem diff contra o baseline.
**Suítes**: Python (core, cli, api) ✅ (1271 / 0 falhas) · `ruff check` ✅ · `ruff format
--check` ✅ · `mypy` ✅ (91 arquivos)

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Mapa de uso | PASS | Mapa registrado no `tdd.md` (Rodada 1 · implementador, 13:09) antes da remoção; coincide com o mapa do QA, transitivos e destinos inclusos. Divergência escrita com motivo: `start`/`duration` de `media.extract_speech_audio` (ver ponto 1) |
| 2 — Mover o que é usado | PASS | `processing/pipeline.py:21-24` com os 4 valores e comentários de `sermon.py`; `files.folder_name` sem `reference`, importado por `service/sermons.py` e `service/renders.py`; `test_files.py::test_folder_name_strips_path_unsafe_characters`; `test_timeline*.py` em `plan_segments` com os 12 casos (saem só os 2 de `EditList.reordered`); `test_pipeline.py`, `test_sermon_download_command.py`, `test_render_command.py` sem diff. Mutações exigidas mortas: `LEAD_IN_S` 0.4 (4), `TAIL_S` 1.4 (2), `PATH_UNSAFE` sem `/ ? "` (1), sem `remove_hesitations` (12); extras `SECTION_MARGIN_S` (3), `SYNC_SEARCH_S` (2), `fillers=False` (1) |
| 3 — Remover a CLI anterior e o código morto | PASS | Os 6 módulos, `legacy.py` e os 5 arquivos de teste apagados; `legacy` fora de `__init__.py`; `contract.execute` sem o ramo `command is None` (`contract.py:213`); símbolos de L1/L5 fora (grep vazio); `test_cli.py::test_help_lists_every_command` e `test_a_command_of_the_previous_cli_is_an_invalid_argument[7]` (saída 2, `details.choices` = os 9). Varredura AST: todo módulo com importador de produção, salvo `asr.worker` (`-m`) e `tasks.{runner,process,render,suggest,diagnostic}` (registro); por símbolo sobram só `output_words`, `default_levels`, `role_of`. Testes removidos = os do código removido. Mutação `short` registrado de novo: 8 vermelhos |
| 4 — Documentação e skills | PARCIAL | (a)–(h) atendidos: varredura vazia; os 28 `wordcut <grupo> <ação>` de README/skills rodam `--help` com saída 0 e cada opção citada aparece; fluxo `sermon create … --process`/`cut list`/`cut render`/`render download` no README e nas skills; os dois arquivos da skill apagados; skills com pré-requisitos, fluxo e onde ver o resultado, sem critério próprio; venv do WhisperX mantido; CHANGELOG com `### Removido`; sem nome de pessoa. **Achado**: `docs/requirements/features/2.1.a-settings.md:14` ainda diz "O conteúdo inicial vem de `skills/video-corte-vertical/sugerir-cortes.md`", arquivo apagado; pela decisão do orquestrador deve dizer que o conteúdo inicial veio desse arquivo, hoje em `packages/core/src/wordcut/criteria/texts/`. `docs/prototype/wordcut.html:536` fica como está (artefato de design) |
| 5 — Ajuda dos grupos | PASS | `contract.HelpFormatter` em `add_group` e `add_command`; com `COLUMNS=80` os 8 grupos ficam em no máximo 78 colunas e o exemplo de `member` sai literal em duas linhas; `test_group_help_fits_an_80_column_terminal[8]`, `test_command_help_fits_an_80_column_terminal`, `test_help_keeps_the_example_on_its_own_line`. Mutações mortas: `add_group` e `add_command` com `RawDescriptionHelpFormatter` (1 cada), epílogo pelo preenchimento padrão (1), usage com `{…}` (1) |

### Pontos fora da barra relatados pelo implementador

1. **`start`/`duration` de `extract_speech_audio` removidos** — aceito. O único chamador
   (`processing/__init__.py:62`) não os passa; é o mesmo critério de L3 e da decisão "Critério
   de remoção". O comando perde só um `-ss 0.000` de entrada, sem efeito. O comando do ffmpeg
   não tem teste, nem no baseline.
2. **Usage dos grupos com `<ação> ...`** — aceito. Sem isso o `{…}` de `cut` (66 colunas) não
   quebra e a linha de usage passa de 80 colunas, contra o passo 5 (a); `docs/cli.md` §3.1 usa
   `<ação>`. A lista de ações segue com `{…}` (`test_cut_help_lists_its_actions` sem
   alteração) e `wordcut --json cut` dá `details.argument: "action"`, como antes.
3. **`2.1.a-settings.md` e o protótipo citam `sugerir-cortes.md`** — o requisito não foi
   ajustado: achado do passo 4 (acima). O protótipo fica como está, conforme a decisão.

### Observações (não bloqueiam)

- Mutação `stammers=False` em `plan_segments` sobrevive à suíte inteira. Fora da barra e
  anterior a esta issue (os casos de `test_timeline*.py` são os mesmos do baseline).
- Fora da barra do passo 5 (`add_command` não bloqueia): `sermon list --help` chega a 83
  colunas (as `choices` de `--status` no usage) e o exemplo de `preset update`, mantido
  literal, a 107.

### Critérios de aceite
- ✅ Cenário "comandos antigos não existem mais" — `test_help_lists_every_command`, `test_a_command_of_the_previous_cli_is_an_invalid_argument[short…]`
- ✅ Cenário "nenhum código morto" — varredura AST por módulo e por símbolo; mapa do passo 1
- ✅ Cenário "documentação coerente" — 28 comandos de README/skills com `--help` 0 e opções presentes; varredura vazia
- ✅ Borda: constantes e funções usadas migram antes — passo 2, mutações vermelhas
- ✅ Borda: WhisperX e worker local continuam — `asr/{__init__,local,worker,prompt_echo}.py` sem diff; `test_local.py`, `test_prompt_echo.py`, `test_pipeline.py` sem diff e verdes; README §Instalação com o venv
- ✅ Borda: `--host` sai — `asr/remote.py` apagado; sem `--host` nos docs
- ✅ FR-001 — passo 3 (a), (b), (d), (e), (h)
- ✅ FR-002 — passos 2 e 3
- ✅ FR-003 — README, CONTRIBUTING, arquitetura (§4 sem "herdado da CLI anterior" e sem `overview`) e skills só com a CLI nova
- ✅ FR-004 — skills curtas, sem critério próprio (grep teológico vazio)
- ✅ FR-005 — pytest, ruff check, ruff format --check, mypy verdes
- ✅ Verificação · `wordcut --help`/`wordcut short` — = cenário 1
- ✅ Verificação · nenhum módulo sem importador — = cenário 2
- ✅ Verificação · README e skills só com comandos existentes — = passo 4 (b)
- ✅ Verificação · quality gates — = FR-005

### Veredito geral: PARCIAL
Sem FAIL; passo 4 PARCIAL pelo requisito `2.1.a-settings.md:14`, que ainda aponta
`sugerir-cortes.md` como fonte atual dos critérios.

## Rodada 2 — 2026-10-26 — working tree sobre 606a0f8

**baseline_commit**: 606a0f8db28cd7162ffe418444df564e22698b0c
**Componentes avaliados**: `packages/core`, `apps/cli`, documentação (`README.md`,
`CONTRIBUTING.md`, `docs/architecture/README.md`, `CHANGELOG.md`, `docs/requirements`) e
`skills/`. `apps/api` e `apps/web` sem diff contra o baseline.
**Suítes**: Python (core, cli, api) ✅ (1271 / 0 falhas) · `ruff check` ✅ · `ruff format
--check` ✅ · `mypy` ✅ (91 arquivos)

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Mapa de uso | PASS | Mantido da Rodada 1 |
| 2 — Mover o que é usado | PASS | Mantido da Rodada 1; suíte igual (1271 verdes) |
| 3 — Remover a CLI anterior e o código morto | PASS | Mantido da Rodada 1; `apps/api` e `apps/web` sem diff |
| 4 — Documentação e skills | PASS | `docs/requirements/features/2.1.a-settings.md:14` agora diz que o conteúdo inicial "veio de `skills/video-corte-vertical/sugerir-cortes.md` (removido no item `cli-migration`) e hoje está em `packages/core/src/wordcut/criteria/texts/`" (pasta existe, com `base.md` e os 11 critérios). Varredura de `docs/` por arquivos e módulos removidos (fora `docs/prototype/` e `inception.md`): só essa menção, histórica. `docs/cli.md:798` cita `--host` apenas na tabela de migração (§15), dizendo que sai. Varredura do cabeçalho em README, CONTRIBUTING, arquitetura e skills vazia; os `wordcut <grupo> <ação>` de README/skills seguem com `--help` saída 0 |
| 5 — Ajuda dos grupos | PASS | Mantido da Rodada 1 |

### Critérios de aceite
- ✅ Cenário "comandos antigos não existem mais" — `test_help_lists_every_command`, `test_a_command_of_the_previous_cli_is_an_invalid_argument[short…]`
- ✅ Cenário "nenhum código morto" — varredura da Rodada 1; a Rodada 2 só registra edição de documento e a suíte segue verde
- ✅ Cenário "documentação coerente" — varreduras vazias; comandos citados com `--help` 0
- ✅ Borda: constantes e funções usadas migram antes — passo 2
- ✅ Borda: WhisperX e worker local continuam — `test_local.py`, `test_prompt_echo.py`, `test_pipeline.py` verdes
- ✅ Borda: `--host` sai — `asr/remote.py` apagado; `--host` só na tabela de migração de `docs/cli.md`
- ✅ FR-001 — passo 3
- ✅ FR-002 — passos 2 e 3
- ✅ FR-003 — passo 4, incluindo `docs/requirements` coerente
- ✅ FR-004 — skills curtas, sem critério próprio
- ✅ FR-005 — pytest, ruff check, ruff format --check, mypy verdes
- ✅ Verificação · `wordcut --help`/`wordcut short` — = cenário 1
- ✅ Verificação · nenhum módulo sem importador — = cenário 2
- ✅ Verificação · README e skills só com comandos existentes — = passo 4 (b)
- ✅ Verificação · quality gates — = FR-005

### Veredito geral: PASS
O achado da Rodada 1 (passo 4, `2.1.a-settings.md:14`) foi resolvido; os demais passos seguem
PASS com a suíte e as checagens verdes.
