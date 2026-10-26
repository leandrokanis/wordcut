# QA — 2.1.a.1 — Configurações do LLM, da transcrição e dos segredos (`settings`)

## Plano de QA — 2026-10-26

**baseline_commit**: 9b946d77005e523f5857fcee683a02ab553a6d3f
**Componentes em escopo**: `packages/core` (`wordcut.config`, `wordcut.errors`,
`wordcut.db` com a migração `0005_settings.sql`, `wordcut.service.settings`,
`wordcut.processing`/`wordcut.tasks.process` para o modelo do WhisperX); `apps/cli`
(`wordcut_cli.settings` e o registro em `wordcut_cli/__init__.py`); documentação
(`docs/architecture/README.md` §4, `CHANGELOG.md`, `SECURITY.md`, `docs/cli.md` §5.3).
**Suítes que valem como prova**:
- Python (core + cli), por arquivo:
  `uv run pytest packages/core/tests/test_secrets.py packages/core/tests/test_settings_service.py apps/cli/tests/test_settings_command.py -q`
- Python, suíte completa: `uv run pytest -q`
- Checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`

**Regras da barra**
- Todo teste roda com `WORDCUT_CONFIG` e `WORDCUT_HOME` em `tmp_path`; nenhum teste usa
  nem lê `~/.config/wordcut/`. Segredos de teste são fictícios (ex.: `sk-ficticia-0000abcd`,
  cookie `.example.com`).
- Permissão se prova com `os.stat(...).st_mode & 0o777` e com a umask do teste aberta
  (`os.umask(0o022)` ou `0`), senão a umask do ambiente esconde a mutação de modo.
- Vazamento se prova procurando o valor fictício inteiro em stdout **e** stderr de cada
  comando (sucesso e erro), em `--json` e em texto legível.
- Mutação manual cobrada pelo QA na avaliação está listada em `tdd.md` (🧬 EXIGE).

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Segredos | (a) `write_secret` cria o arquivo com modo exato `0o600` mesmo com umask `0o022`; (b) cria `WORDCUT_CONFIG` ausente com `0o700`; (c) sobrescrever um arquivo existente `0o644` deixa `0o600` e o conteúdo novo; (d) atomicidade: com `os.replace` falhando, o conteúdo anterior fica intacto e nenhum temporário sobra na pasta; um temporário órfão de execução anterior não bloqueia a gravação; (e) `llm_key_file()` = `WORDCUT_CONFIG/openrouter-key`, cookies seguem em `youtube-cookies.txt` (`test_config.py` verde); (f) máscara: `"••••"+key[-4:]` com 8+ caracteres, `"••••"` com 7, `None` sem chave; (g) `has_youtube_cookies()` falso/verdadeiro; (h) pasta sem escrita (`chmod 0o500`, `skipif` root) → `WordcutError("config_not_writable")` saída 5, mensagem sem o conteúdo; `config_not_writable` em `EXIT_CODES` e na tabela de `test_errors.py` | `packages/core/tests/test_secrets.py`, nível unidade pela interface pública de `wordcut.config`; `os.stat`; `monkeypatch` de `os.replace`; mutações: modo padrão no `os.open`, escrita no lugar sem temporário, `>= 8` → `> 8`, remover o `except OSError` |
| 2 — Tabela e serviço | (a) banco novo fica em `user_version` 5 com a tabela `settings`; banco na versão 4 migra sem perder dados (`test_db.py` verde); (b) `show_settings` numa instalação nova devolve exatamente `{llm_model: None, whisper_model: "large-v3", llm_key: None, youtube_cookies: False, default_preset_id: None}`; (c) `update_settings` parcial muda só o campo dado e persiste ao reabrir a conexão; (d) `store_llm_key` grava a chave sem espaços/quebras das pontas; `show_settings` traz só a máscara e nenhum valor do dict contém a chave; a chave não está no arquivo do SQLite (bytes do `.db` e do `-wal`); (e) `store_youtube_cookies`: vazio → `invalid_argument`, texto sem linha Netscape → `invalid_argument`, nos dois casos nada gravado; válido → gravado byte a byte e `youtube_cookies: True`; (f) `whisper_model(conn)` = `"large-v3"` por padrão e o valor gravado depois; `llm_model(conn)` = `None` por padrão | `packages/core/tests/test_settings_service.py`, nível serviço com banco real em `WORDCUT_HOME` temporário; mutações: padrão do WhisperX trocado, chave gravada no banco, `strip()` removido, validação Netscape removida |
| 3 — CLI | (a) `settings show --json` numa instalação nova → saída 0 e o dict exato do cenário 1; (b) `settings set --model x --whisper-model y` → saída 0 e refletido no `show`; (c) `set-key` com stdin redirecionado (`io.StringIO`, `isatty()` falso) → saída 0, arquivo `0o600` em `WORDCUT_CONFIG`, `show` com `"••••abcd"`, chave ausente de stdout/stderr do `set-key` e do `show` (json e texto); (d) `set-key`/`set-cookies` com stdin vazio ou só espaços → saída 2, `invalid_argument`, arquivo inexistente; (e) com terminal (`isatty()` verdadeiro) o `set-key` chama `getpass.getpass` (dublê) e não lê `sys.stdin.read`; (f) `set-cookies < arquivo` → `0o600`, `youtube_cookies: true`; (g) argumento extra (`settings set-key <fictícia>`, `--key <fictícia>`) → saída 2, nada gravado, valor fictício ausente de stdout/stderr; (h) pasta somente leitura → saída 5, `{"error": {"code": "config_not_writable"}}`, sem o conteúdo; (i) `--help` de cada ação diz que é do administrador e traz exemplo; `test_cli.py::COMMANDS` inclui `settings` | `apps/cli/tests/test_settings_command.py` por `wordcut_cli.main(argv)` + `capsys`, como os demais testes da CLI; `monkeypatch` de `sys.stdin` e `getpass.getpass`; mutações: ler sempre `sys.stdin.read()`, aceitar argumento posicional, imprimir a chave no render |
| 4 — Uso | o processamento usa o modelo configurado: com `whisper_model` gravado como `"medium"` o transcritor/fábrica de gateways recebe `"medium"`; sem configuração recebe `"large-v3"`; dublês existentes de `default_gateways` (`conftest.py`, `test_process_task.py`, `test_processing_service.py`, `test_sermon_process_command.py`) ajustados e verdes; docstring de `default_gateways` sem "large-v3" fixo | teste de comportamento em `packages/core/tests/test_process_task.py` (ou `test_processing_service.py`) que captura o argumento do dublê; mutação: valor `"large-v3"` fixo no código → teste do `"medium"` vermelho |
| 5 — Documentação | `docs/architecture/README.md` §4 cita tabela `settings` (migração 0005), `service.settings` e `wordcut settings`; `CHANGELOG.md` em "Não lançado › Adicionado"; `SECURITY.md` nomeia `openrouter-key` e `youtube-cookies.txt` com 600; `docs/cli.md` §5.3 lista `config_not_writable` (saída 5); docstring de `wordcut/config.py` deixa de dizer que o código nunca lê os arquivos; nenhum segredo real nem nome de pessoa nos textos | leitura de `git diff 9b946d7 -- docs CHANGELOG.md SECURITY.md packages/core/src/wordcut/config.py`; sem teste automatizado |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário "ver as configurações" / Verificação 1 — instalação nova → `llm_model: null`, `whisper_model: "large-v3"`, `llm_key: null`, `youtube_cookies: false`, `default_preset_id: null` | Passo 3 (a) no CLI; Passo 2 (b) no serviço |
| Cenário "trocar modelos" / Verificação 2 — `set --model --whisper-model` refletido no `show` | Passo 3 (b); Passo 2 (c) |
| Cenário "gravar a chave pelo stdin" / Verificação 3 — 600 em `WORDCUT_CONFIG`, `"••••abcd"`, ausente de stdout/stderr | Passo 3 (c); Passo 1 (a)(f) |
| Cenário "gravar os cookies pelo stdin" / Verificação 4 — 600, `youtube_cookies: true` | Passo 3 (f); Passo 2 (e) |
| Borda: `set-key` sem stdin → `invalid_argument`, nada gravado / Verificação 5 | Passo 3 (d); Passo 2 (e) para cookies |
| Borda: stdin de terminal → `getpass` sem eco | Passo 3 (e) |
| Borda: chave nunca em saída, erro, log ou progresso | Passo 3 (c)(g)(h) — busca do valor em stdout e stderr, sucesso e erro, json e texto; Passo 2 (d) — fora do banco |
| Borda: nenhuma opção de linha de comando recebe segredo | Passo 3 (g) |
| Borda: pasta somente leitura → erro claro sem conteúdo / Verificação 6 | Passo 1 (h); Passo 3 (h) |
| FR-001 — `show` com modelos, chave mascarada, presença dos cookies e preset padrão | Passo 2 (b)(d); Passo 3 (a)(c) |
| FR-002 — `set` grava no SQLite | Passo 2 (c); Passo 3 (b) |
| FR-003 — só stdin, arquivos 600 em `WORDCUT_CONFIG`, atômico | Passo 1 (a)–(d); Passo 3 (c)(f)(g) |
| FR-004 — segredo em nenhuma saída; chave só mascarada | Passo 1 (f); Passo 2 (d); Passo 3 (c)(g)(h) |
| FR-005 — processamento usa o modelo do WhisperX configurado | Passo 4 |
| Verificação 7 — quality gates limpos | `uv run pytest -q` + `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

**Lacunas do plano (decisão conservadora registrada; detalhes em `tdd.md`)**
1. `config_not_writable` não existe em `wordcut.errors.EXIT_CODES` (o construtor rejeita
   código desconhecido) nem em `docs/cli.md` §5.3. Barra: código com saída 5 nos dois
   lugares e em `test_errors.py`; sem isso, Passos 1 e 5 ficam PARCIAL.
2. Erro de uso ecoa o argumento: `_usage_error` monta "Argumento não reconhecido:
   {argument}" e `details.argument`, então `wordcut settings set-key <chave>` imprimiria a
   chave. Barra: Passo 3 (g); ecoar o valor é FAIL.
3. `set-cookies` com terminal: `getpass` lê uma linha só e cookies Netscape têm várias.
   Barra conservadora: com terminal, `set-cookies` recusa com `invalid_argument` pedindo o
   redirecionamento do arquivo (ou lê até EOF sem eco); truncar em uma linha é FAIL.
4. `settings set` sem nenhuma opção, ou com valor vazio, não foi decidido. Barra
   conservadora: `invalid_argument` com `details.argument`, nada alterado.
5. Assinatura do ponto de uso do WhisperX não decidida; mudar `default_gateways()` quebra os
   dublês sem argumento existentes. Barra: Passo 4 com os dublês ajustados e suíte verde.
6. Nome do temporário com `O_EXCL` não definido: nome fixo falha após queda anterior.
   Barra: Passo 1 (d), temporário órfão não bloqueia.
7. `read_llm_key()` não tem chamador nesta issue (código morto pelo CONTRIBUTING §4).
   Barra: se entrar, teste de ida e volta no Passo 1; senão, fica para 2.1.b.1.
8. Nenhuma fixture global isola `WORDCUT_CONFIG` (só `WORDCUT_HOME` tem `wordcut_home`, e não
   é autouse). Barra: fixture autouse no `conftest.py` raiz apontando `WORDCUT_CONFIG` para
   `tmp_path`; teste que alcance `~/.config/wordcut` é FAIL.
9. Formato Netscape não definido. Barra: aceitar ao menos uma linha não comentada com 7
   campos separados por TAB; o cabeçalho `# Netscape HTTP Cookie File` não é exigido.

---

## Rodada 1 — 2026-10-26 — working tree sobre 9b946d7

**baseline_commit**: 9b946d77005e523f5857fcee683a02ab553a6d3f
**Componentes avaliados**: `packages/core` (config, errors, db/settings + migração 0005,
service/settings, processing, tasks/process), `apps/cli` (settings, contract, registro),
documentação (`docs/architecture/README.md`, `docs/cli.md`, `CHANGELOG.md`, `SECURITY.md`).
**Suítes**: Python (core + cli) ✅ (580 / 0 falhas) · ruff check ✅ · ruff format --check ✅ ·
mypy ✅ (63 arquivos)

Mutações feitas numa cópia em scratchpad, uma por vez, contra `test_secrets.py`,
`test_settings_service.py`, `test_settings_command.py`, `test_process_task.py` e
`test_config.py` (e a suíte inteira nas de `contract.py`): 30 de 34 mortas. Detalhe em
`tdd.md` (Rodada 1 · QA).

**Fato do implementador (mkstemp)**: confirmado. Com `tempfile.mkstemp` (decisão 6) não há
`os.open` a mutar, e tirar o `fchmod` sobrevive porque o `mkstemp` já cria 0o600. Equivalente
aceita pelo orquestrador; as duas provas exigidas existem e passam:
`test_a_secret_is_written_readable_only_by_its_owner` (umask 0o022 → 0o600) e
`test_rewriting_an_open_secret_leaves_only_the_new_content_private` (644 → 600). A mutação
"fchmod 0o644" morre. O `fchmod` só faz diferença com umask que tira bits do dono, fora da
barra.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Segredos | PASS | `test_secrets.py` (11), `test_config.py::test_llm_key_file_is_in_the_secrets_folder`, `test_errors.py[config_not_writable-5]`; 11 de 12 mutações mortas, a sobrevivente é a equivalente aceita |
| 2 — Tabela e serviço | PASS | `test_settings_service.py` (16); `user_version` 5 com a tabela `settings`; `test_db.py` verde; 10 de 10 mutações mortas |
| 3 — CLI | FAIL | (1) `wordcut settings --key <chave> set-key` (e `wordcut settings <chave>`) ecoa a chave: `Valor inválido para action: '<chave>'` no stderr e no `message` do `--json`, porque o grupo `settings` toma a chave como ação inválida e `contract._usage_error` repete o valor (`contract.py:53-58`, padrão "invalid choice", usado por `_usage_error` em `contract.py:63`); a lacuna 2 da barra diz que ecoar é FAIL e a matriz 3 (g) cobra `--key <fictícia>` sem fixar a posição. (2) Teste frágil: a mutação "comando de segredo ignora a sobra" (`if stray and not command.reads_secret`) deixa a suíte inteira verde, porque `test_a_secret_given_as_argument_is_refused_without_being_echoed` usa stdin vazio e a saída 2 vem do stdin vazio, não da recusa; com stdin cheio a chave seria gravada com saída 0, contra a decisão 2 |
| 4 — Uso | PASS | `test_process_task.py::test_the_task_transcribes_with_the_configured_whisperx_model[default\|set]`; "large-v3" fixo na tarefa → 1 failed; dublês ajustados e verdes. Nota: `LocalTranscriber()` sem o modelo dentro de `default_gateways` sobrevive, mas fica atrás do dublê de `default_gateways` que a barra escolheu como instrumento |
| 5 — Documentação | PASS | §4 cita tabela `settings`/0005, `service.settings`, `wordcut settings`; CHANGELOG em Adicionado e Alterado; SECURITY.md com `openrouter-key`, `youtube-cookies.txt`, 600; `docs/cli.md` §5.3 com `config_not_writable` 5; docstring de `config.py` corrigida. Notas: linha em branco no meio da lista "Alterado" do CHANGELOG; "argumento sobrando recusado sem eco" no §4 vale só depois da ação (ver passo 3) |

**Efeito do `parse_known_args` nos outros comandos**: comparado com o baseline (cópia por
`git archive 9b946d7`), `sermon list extra`, `status extra` e o legado `info u extra` dão a
mesma saída 2 e a mesma mensagem `Argumento não reconhecido: extra.`; a mutação "contrato
ignora sobras" em todo comando quebra 2 testes de `test_cli_contract.py`. Sem regressão.
`settings set --model x <valor>` ecoa o valor sobrando, como os demais comandos sem segredo.
`wordcut --key <chave> settings set-key` ecoa a chave como comando inválido também no
baseline (eco genérico do parser raiz, anterior ao item).

**Política de comentários (CONTRIBUTING §5)**: os comentários novos são de intenção
(`contract.py` `reads_secret`, `config.py` `MIN_KEY_LENGTH_TO_SHOW`, `settings.py` getpass),
referência (`service/settings.py` presets, migração 0005) e restrição externa com fonte
(formato Netscape, link do curl). Nenhum fora dos tipos.

### Critérios de aceite
- ✅ Ver as configurações / Verificação 1 — `test_show_of_a_new_installation_has_only_the_whisperx_model_set`, `test_a_new_installation_has_only_the_whisperx_model_set`
- ✅ Trocar modelos / Verificação 2 — `test_set_changes_both_models_and_show_reflects_them`, `test_a_changed_model_is_kept_after_reopening_and_the_other_stays`
- ✅ Gravar a chave pelo stdin / Verificação 3 — `test_set_key_reads_the_key_from_redirected_stdin_into_a_private_file`, `test_the_key_appears_in_no_output_of_set_key_nor_of_show[json\|text]`
- ✅ Gravar os cookies pelo stdin / Verificação 4 — `test_set_cookies_reads_the_cookies_from_redirected_stdin_into_a_private_file`, `test_stored_cookies_are_kept_as_they_came_and_shown_only_as_present`
- ✅ Borda: stdin vazio → `invalid_argument`, nada gravado / Verificação 5 — `test_an_empty_stdin_is_refused_and_nothing_is_stored`
- ✅ Borda: stdin de terminal → getpass — `test_set_key_on_a_terminal_reads_the_key_without_echo`
- ❌ Borda: chave nunca em saída ou erro — `wordcut settings --key <chave> set-key` põe a chave no erro (stderr e `--json`); sem teste para argumento antes da ação
- ✅ Borda: nenhuma opção recebe segredo — `test_a_secret_given_as_argument_is_refused_without_being_echoed` (recusa provada só com stdin vazio; ver passo 3)
- ✅ Borda: pasta somente leitura / Verificação 6 — `test_set_key_into_a_read_only_folder_is_a_config_not_writable_error`, `test_the_read_only_folder_error_does_not_carry_the_key`, `test_a_read_only_secrets_folder_is_a_clear_error_without_the_secret`
- ✅ FR-001 — testes de `show` no serviço e na CLI
- ✅ FR-002 — `test_a_changed_model_is_kept_after_reopening_and_the_other_stays`
- ✅ FR-003 — `test_secrets.py` (600, 700, 644 → 600, atomicidade, órfão) e testes de `set-key`/`set-cookies`
- ❌ FR-004 — mesmo caminho do eco acima
- ✅ FR-005 — `test_the_task_transcribes_with_the_configured_whisperx_model`
- ✅ Verificação 7 — pytest, ruff e mypy limpos

### Veredito geral: FAIL
Passo 3 FAIL: a chave passada como `--key` antes de `set-key` aparece no erro, e a recusa do
argumento sobrando não tem prova independente do stdin vazio. Reabrir o passo 3.

---

## Rodada 2 — 2026-10-26 — working tree sobre 9b946d7

**baseline_commit**: 9b946d77005e523f5857fcee683a02ab553a6d3f
**Componentes avaliados**: `apps/cli` (`contract.py`, `settings.py`, testes de contrato e de
`settings`), documentação (ADR-0015 e índice, `README.md`, `docs/cli.md` §5.3,
`docs/architecture/README.md` §4, `CHANGELOG.md`); `packages/core` só pela suíte (sem mudança
desde a Rodada 1).
**Suítes**: Python (core + cli) ✅ (601 / 0 falhas) · ruff check ✅ · ruff format --check ✅ ·
mypy ✅ (63 arquivos)

**Barra desta rodada**: matriz do topo mais a decisão do orquestrador para o passo 3
(`plan.md`, linha "Erro de uso não repete valor digitado", e ADR-0015).

**Sondagem de eco** (`main(argv)` com `WORDCUT_HOME`/`WORDCUT_CONFIG` no scratchpad): 16 272
execuções em todos os comandos, grupos e raiz, com 8 valores fictícios (inclusive com
`(choose from '…')`, aspas, `argument x: …`, quebra de linha, dígitos e `:`), nas formas
posicional, `--x=`, `-valor`, `-k`, `--json=`, `--quiet=`, `-- valor`, abreviação e opção
real, com e sem `--json`, com stdin cheio e vazio. 15 624 saídas 2 e nenhuma com o valor em
stdout ou stderr. Fora da conta: sucessos de `settings set` (o modelo aparece por ser o
resultado) e erros de execução dos comandos legados (traceback com o caminho; não é erro de
uso, anterior ao item). Na sondagem, `--dir <valor>` dos legados criou três pastas vazias na
raiz do repositório; removidas na hora.

**Mutações** em cópia no scratchpad, contra `apps/cli/tests`: 13 de 16 mortas. A cobrada pela
barra, "comando de segredo ignora a sobra" com stdin cheio, morre em 12 testes. Detalhe em
`tdd.md` (Rodada 2 · QA). Sobreviventes:
1. **Comando de segredo sem ramo próprio** (`if command.reads_secret` → `if False`): suíte
   verde. A ADR-0015 diz que esse comando recusa "sem nem o nome da opção"; sem o ramo,
   `wordcut settings set-key --sk-or-v1-<chave>` repete a chave inteira, e nenhum teste
   pega. Hoje o código recusa certo (conferido no executável).
2. **Opção longa aceita maiúsculas** (`--[a-zA-Z][a-zA-Z0-9-]*`): suíte verde. A regra de
   minúsculas da decisão não tem teste; `--SK-<VALOR>` passaria a ser repetido.
3. **Fallback "Uso inválido" repete a mensagem do argparse**: suíte verde. Alcançável:
   `wordcut transcribe --h=<valor>` é "ambiguous option" com o valor dentro; hoje sai
   `Uso inválido; veja wordcut --help.`, sem teste que guarde.

**Eco que a regra da barra permite**: `wordcut sermon list --sk-or-v1-<chave>` e
`wordcut settings set --sk-or-v1-<chave>` dão `Argumento não reconhecido: --sk-or-v1-<chave>.`
com `details.argument`, porque o texto casa `^--[a-z][a-z0-9-]*$`. Chave do OpenRouter é
minúscula com hífens e casa a regra. Está dentro da decisão e não é julgado como falha, mas
`docs/cli.md` §5.3 diz que a mensagem "nunca repete o valor digitado".

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Segredos | PASS | sem mudança desde a Rodada 1; `test_secrets.py` verde na suíte |
| 2 — Tabela e serviço | PASS | sem mudança desde a Rodada 1; `test_settings_service.py` verde |
| 3 — CLI | PARCIAL | Os dois achados da Rodada 1 foram resolvidos: `test_a_secret_given_where_the_action_goes_is_refused_without_being_echoed` (6) e `test_a_secret_given_as_argument_is_refused_without_being_echoed` (12, com stdin cheio, "ignora a sobra" vermelha). Os testes de contrato cobrem escolha com lista, tipo, posicional e valor colado ao hífen. Lacuna: o item da ADR-0015 para comando de segredo ("sem nem o nome da opção") e a regra de minúsculas não têm teste (mutações 1 e 2 sobrevivem); `contract.py:99-104` e `contract.py:52` |
| 4 — Uso | PASS | sem mudança desde a Rodada 1; `test_process_task.py` verde |
| 5 — Documentação | PASS | ADR-0015 com índice, `README.md`, §4, `docs/cli.md` §5.3 (`details.choices`), CHANGELOG em "Alterado"; linha em branco removida. Nota: §5.3 diz "nunca repete o valor digitado", mas a regra deixa passar `--<valor>` minúsculo |

### Critérios de aceite
- ✅ Ver as configurações / Verificação 1 — `test_show_of_a_new_installation_has_only_the_whisperx_model_set`
- ✅ Trocar modelos / Verificação 2 — `test_set_changes_both_models_and_show_reflects_them`
- ✅ Gravar a chave pelo stdin / Verificação 3 — `test_set_key_reads_the_key_from_redirected_stdin_into_a_private_file`, `test_the_key_appears_in_no_output_of_set_key_nor_of_show[json|text]`
- ✅ Gravar os cookies pelo stdin / Verificação 4 — `test_set_cookies_reads_the_cookies_from_redirected_stdin_into_a_private_file`
- ✅ Borda: stdin vazio / Verificação 5 — `test_an_empty_stdin_is_refused_and_nothing_is_stored`
- ✅ Borda: stdin de terminal → getpass — `test_set_key_on_a_terminal_reads_the_key_without_echo`
- ✅ Borda: chave nunca em saída ou erro — `test_a_secret_given_where_the_action_goes_is_refused_without_being_echoed`, `test_no_usage_error_repeats_a_value_the_user_typed`, `test_a_value_glued_to_a_dash_is_not_taken_for_an_option_name` (ressalva: `--<chave>` em comando sem segredo, permitido pela regra)
- ✅ Borda: nenhuma opção recebe segredo — `test_a_secret_given_as_argument_is_refused_without_being_echoed` (stdin cheio)
- ✅ Borda: pasta somente leitura / Verificação 6 — `test_set_key_into_a_read_only_folder_is_a_config_not_writable_error`, `test_the_read_only_folder_error_does_not_carry_the_key`
- ✅ FR-001 — testes de `show` no serviço e na CLI
- ✅ FR-002 — `test_a_changed_model_is_kept_after_reopening_and_the_other_stays`
- ✅ FR-003 — `test_secrets.py` e testes de `set-key`/`set-cookies`
- ✅ FR-004 — mesmos testes de eco acima
- ✅ FR-005 — `test_the_task_transcribes_with_the_configured_whisperx_model`
- ✅ Verificação 7 — pytest, ruff e mypy limpos

### Veredito geral: PARCIAL
O FAIL da Rodada 1 foi resolvido, com progresso. O passo 3 fica PARCIAL porque dois itens da
decisão não têm teste: a recusa própria do comando de segredo e a regra de minúsculas. Basta
reabrir o passo 3 só para esses testes.

---

## Rodada 3 — 2026-10-26 — working tree sobre 9b946d7

**baseline_commit**: 9b946d77005e523f5857fcee683a02ab553a6d3f
**Componentes avaliados**: `apps/cli` (`contract.py`, `settings.py`, `test_cli_contract.py`,
`test_settings_command.py`), documentação (ADR-0015, `docs/cli.md` §5.3, `CHANGELOG.md`);
`packages/core` só pela suíte (sem mudança desde a Rodada 1).
**Suítes**: Python (core + cli) ✅ (613 / 0 falhas) · ruff check ✅ · ruff format --check ✅ ·
mypy ✅ (63 arquivos)

**Barra desta rodada**: matriz do topo mais a decisão final do orquestrador para o passo 3
(`plan.md`, linha "Erro de uso não repete valor digitado", e ADR-0015): argumento não
reconhecido nunca é repetido, nem como nome de opção, com mensagem genérica e sem
`details.argument`; nome de opção só quando a opção existe no parser, pela definição dele.

**Sondagem de eco** (`main(argv)` com `WORDCUT_HOME`/`WORDCUT_CONFIG` no scratchpad, `_run`
e handlers do legado trocados por dublê para não haver efeito colateral): 14 700 execuções em
todos os comandos, grupos e raiz, com 3 valores fictícios (minúsculo com hífens, maiúsculo,
curto) em 49 formas (`--valor`, `-valor`, `---valor`, `--VALOR`, `--valor=x`, `--x=valor`,
`-k valor`, `-- valor`, `--json=`, `--h=`, `--help=`, `--version=`, imitação de
`(choose from …)` e de `argument x:`, quebra de linha, valor em `--status`/`--stat`/`--kind`/
`--start`), antes e depois do comando, com e sem `--json`, stdin cheio. 14 598 saídas 2 e
nenhuma com o valor (em qualquer caixa) em stdout ou stderr. Conferidos à parte:
`wordcut --sk-or-v1-<fictícia>` sai `Argumento obrigatório ausente: command.` com
`details.argument: "command"` (o argparse reclama do comando ausente antes da sobra; nome do
parser, sem o valor); `settings set-key --SK-…` e `settings --sk-or-v1-… set-key` saem
`Argumento não reconhecido; veja wordcut settings set-key --help.` sem `details`, nada
gravado; `sermon list --stat <valor>` sai `Valor inválido para --status; use um de: …`.
Fora da conta: sucesso de `settings set --whisper-model <valor>` (o modelo é o resultado).

**Mutações** em cópia no scratchpad, contra `apps/cli/tests`: 10 de 13 mortas. As duas
sobreviventes cobradas na Rodada 2 morrem: "comando de segredo deixa passar a sobra" (14
testes) e "nome da opção com maiúsculas é repetido" (1 teste, caso `--BOGUS`). Detalhe em
`tdd.md` (Rodada 3 · QA). Sobreviventes, nenhuma com eco hoje e nenhuma cobrada pela barra:
1. `<comando>` do `--help` sem a ação (`veja wordcut settings --help`): ainda vem do parser.
2. Legado ignora a sobra (`info u extra` rodaria): sem eco; guarda de comportamento anterior.
3. Fallback `Uso inválido` repete a mensagem do argparse: o mesmo da Rodada 2
   (`transcribe --h=<valor>`); o código atual sai genérico, conferido na sondagem.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Segredos | PASS | sem mudança desde a Rodada 1; `test_secrets.py` verde na suíte |
| 2 — Tabela e serviço | PASS | sem mudança desde a Rodada 1; `test_settings_service.py` verde |
| 3 — CLI | PASS | `test_a_secret_shaped_like_an_option_is_refused_without_being_repeated` (8: `sermon list`, `settings set`, `settings set-key` e raiz, json e texto, stdin cheio, nada gravado); `test_an_unrecognized_argument_is_refused_in_portuguese_without_naming_it` (5, com `--BOGUS`); `test_an_invalid_value_for_an_existing_option_names_it_as_the_parser_defines_it` (`--stat` → `--status`); `contract.py:89-97` sempre genérico, `reads_secret` e a regra do nome removidos; sondagem sem eco; as duas mutações da Rodada 2 mortas |
| 4 — Uso | PASS | sem mudança desde a Rodada 1; `test_process_task.py` verde |
| 5 — Documentação | PASS | ADR-0015 com a regra final (sem ramo próprio para segredo, nome só do parser), `docs/cli.md` §5.3 ("argumento não reconhecido não traz `details`"), CHANGELOG em "Alterado"; nenhum resto de `Argumento não reconhecido: <x>` fora do Contexto da ADR |

### Critérios de aceite
- ✅ Ver as configurações / Verificação 1 — `test_show_of_a_new_installation_has_only_the_whisperx_model_set`
- ✅ Trocar modelos / Verificação 2 — `test_set_changes_both_models_and_show_reflects_them`
- ✅ Gravar a chave pelo stdin / Verificação 3 — `test_set_key_reads_the_key_from_redirected_stdin_into_a_private_file`, `test_the_key_appears_in_no_output_of_set_key_nor_of_show[json|text]`
- ✅ Gravar os cookies pelo stdin / Verificação 4 — `test_set_cookies_reads_the_cookies_from_redirected_stdin_into_a_private_file`
- ✅ Borda: stdin vazio / Verificação 5 — `test_an_empty_stdin_is_refused_and_nothing_is_stored`
- ✅ Borda: stdin de terminal → getpass — `test_set_key_on_a_terminal_reads_the_key_without_echo`
- ✅ Borda: chave nunca em saída ou erro — `test_a_secret_shaped_like_an_option_is_refused_without_being_repeated`, `test_a_secret_given_where_the_action_goes_is_refused_without_being_echoed`, `test_no_usage_error_repeats_a_value_the_user_typed`, `test_a_value_glued_to_a_dash_is_not_taken_for_an_option_name` (a ressalva da Rodada 2 sobre `--<chave>` caiu)
- ✅ Borda: nenhuma opção recebe segredo — `test_a_secret_given_as_argument_is_refused_without_being_echoed` (stdin cheio)
- ✅ Borda: pasta somente leitura / Verificação 6 — `test_set_key_into_a_read_only_folder_is_a_config_not_writable_error`, `test_the_read_only_folder_error_does_not_carry_the_key`
- ✅ FR-001 — testes de `show` no serviço e na CLI
- ✅ FR-002 — `test_a_changed_model_is_kept_after_reopening_and_the_other_stays`
- ✅ FR-003 — `test_secrets.py` e testes de `set-key`/`set-cookies`
- ✅ FR-004 — mesmos testes de eco acima
- ✅ FR-005 — `test_the_task_transcribes_with_the_configured_whisperx_model`
- ✅ Verificação 7 — pytest, ruff e mypy limpos

### Veredito geral: PASS
O PARCIAL da Rodada 2 foi resolvido: segredo em forma de opção não é repetido em nenhum
comando nem na raiz, e as duas mutações cobradas morrem. As três sobreviventes restantes não
têm eco hoje e ficam fora da barra; entram como notas para quem revisar.
