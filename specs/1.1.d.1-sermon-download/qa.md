# QA — 1.1.d.1 — Baixar a pregação em 16:9 (`sermon download`)

## Plano de QA — 2026-10-26

**baseline_commit**: 53fc42b7dd4812ece1a0b251462933971f5584da
**Componentes em escopo**: `packages/core` (`wordcut.files` novo, `wordcut.service.sermons`;
leitura de `wordcut.db.sermons.SermonRow.video_path`, `wordcut.home.Home`,
`wordcut.sermon_folder.folder_name`); `apps/cli` (`wordcut_cli.sermon`); `CHANGELOG.md`.
`wordcut.errors` e as migrações NÃO devem mudar: `sermon_not_processed` (saída 5) já está em
`EXIT_CODES` e a coluna `video_path` já existe (migração 0004, gravada por
`wordcut/tasks/process.py` como caminho relativo a `WORDCUT_HOME`).
**Suítes que valem como prova**:
- core: `uv run pytest packages/core/tests/test_files.py packages/core/tests/test_sermon_video.py -q`
  (+ `test_sermons_service.py`, `test_sermon_folder.py`, `test_errors.py` como regressão)
- cli: `uv run pytest apps/cli/tests/test_sermon_download_command.py -q` (+
  `test_sermon_command.py`, `test_cli_contract.py`, `test_cli.py` como regressão)
- suíte completa: `uv run pytest -q`
- estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`

Fontes da barra: `spec.md`, `plan.md`, docs/cli.md §5 e §7.5, código no baseline. Sem
rastreador: os critérios saem do spec e da Verificação do plano.

Regras da barra (valem para todos os passos):

- Vídeo falso = bytes arbitrários (não-vazios, não-repetitivos) num arquivo em
  `WORDCUT_HOME/media/sermons/<id>/`; a pregação vai a `processed` com `video_path` relativo
  pelo repositório (`sermons.record_processed`) ou por SQL. Nenhum teste chama YouTube,
  WhisperX ou ffmpeg (os fixtures `no_real_youtube` e `default_gateways` recusam).
- Testes da CLI usam `wordcut_home` e `monkeypatch.chdir(tmp_path/...)`; nunca a pasta real
  de dados nem a pasta atual do processo de teste.
- "Idêntico" = `destino.read_bytes() == origem.read_bytes()`; `bytes` = tamanho do destino.
  Conferir só existência ou só tamanho é teste frágil (PARCIAL).
- Teste de comportamento pela interface pública (`copy_without_overwrite`, `sermon_video`,
  `wordcut_cli.main`); teste que só confere chamada interna conta como frágil (PARCIAL).
- Mutação "exige … vermelha" que sobreviver deixa o passo PARCIAL.

Decisões que o plano deixou abertas, fechadas aqui pela opção mais conservadora (execução
automatizada aprovada pelo administrador; ver lacunas em `tdd.md`):

- D1. O sufixo vai antes da extensão: `2026-10-18 - Culto de domingo (2).mp4`, depois `(3)`…
- D2. A regra de não sobrescrever vale para qualquer destino, inclusive `-o arquivo` explícito.
- D3. Só pasta **existente** recebe o nome legível dentro; caminho inexistente é arquivo.
  Caminho terminado em separador (`-o saida/`) é pasta, criada se preciso.
- D4. Vídeo ausente no disco **ou** `video_path` nulo numa pregação `processed` →
  `internal_error` (saída 1) com mensagem "vídeo da pregação N não encontrado" e, se houver
  `details`, só `{"sermon_id": N}` — nem `WORDCUT_HOME` nem caminho absoluto na saída.
- D5. Saída em texto = o caminho absoluto de destino (docs/cli.md §7.5 "devolve o caminho").
- D6. Nenhum arquivo temporário sobra na pasta de destino, nem em sucesso nem em falha da
  cópia; o temporário não usa o nome final nem um nome que case com `* (N).mp4`.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Cópia segura | (a) `copy_without_overwrite(origem, destino_arquivo)` cria o arquivo com bytes idênticos e devolve o `Path` absoluto; (b) destino em pastas inexistentes → pastas criadas; (c) destino = pasta existente → grava `pasta/<nome sugerido>` (o nome sugerido entra pela assinatura; registrar como chega); (d) destino existente → `Nome (2).ext`, com `(2)` ocupado → `Nome (3).ext`; o original fica com os bytes antigos (D1, D2); (e) falha no meio da cópia (dublê de `shutil.copyfile` que grava parte e lança) → exceção propaga, nome final não existe e a pasta de destino não guarda temporário (D6); (f) após sucesso, a pasta de destino contém só o arquivo final; (g) destino relativo resolvido contra a pasta atual (`monkeypatch.chdir`), retorno absoluto | `packages/core/tests/test_files.py`, arquivos reais em `tmp_path`. Exige mutações: trocar o laço de sufixo por gravação direta no destino → vermelha (original sobrescrito); `mkdir(parents=True)` removido → vermelha; não apagar o temporário no `except` → vermelha; gravar direto no nome final sem temporário → vermelha em (e) |
| 2 — Serviço | (a) `sermon_video(conn, home, id)` de pregação `processed` → `SermonVideo.path == home.root / video_path` (absoluto, existe) e `suggested_name == folder_name(service_date, title) + ".mp4"` (ex.: `2026-10-18 - Culto de domingo.mp4`); (b) título com `/\:*?"<>|` → caracteres removidos no nome sugerido; (c) cada um de `created`, `trimmed`, `processing`, `failed` → `WordcutError` `sermon_not_processed`, `exit_code == 5` (parametrizado nos quatro); (d) ID inexistente → `not_found` (3); (e) arquivo apagado do disco e, separadamente, `video_path` nulo em `processed` → `internal_error` com mensagem contendo o ID, sem `str(home.root)` na mensagem nem em `details` (D4); (f) a função não toma a trava: com `lock_owner` segurando a trava de outro recurso, `sermon_video` responde normalmente (FR-005); (g) serviço sem `argparse`, `print` nem import de `wordcut_cli` (leitura do diff) | `packages/core/tests/test_sermon_video.py` com SQLite real em `wordcut_home`, pregação inserida por `sermons.insert` e levada a cada estado por SQL / `record_processed`. Exige mutações: aceitar qualquer estado (sem checar `processed`) → vermelha; montar o caminho sem `home.root` → vermelha; trocar `folder_name` por `title + ".mp4"` → vermelha em (a)/(b); trocar a checagem de existência por nada → vermelha em (e) (sem ela o erro seria outro código ou `FileNotFoundError` cru) |
| 3 — CLI | (a) `wordcut sermon download <id> --json` com `cwd` numa pasta vazia → saída 0, um único documento JSON `{"path", "bytes"}` com `path` absoluto, `Path(path).name == "2026-10-18 - Culto de domingo.mp4"`, bytes idênticos ao vídeo e `bytes == len(video)`; (b) `-o x/y/pregacao.mp4` (relativo e absoluto, pastas inexistentes) → arquivo nesse caminho, `path` absoluto; (c) `-o <pasta existente>` → `pasta/<nome legível>`; (d) segunda execução igual → `... (2).mp4`, primeiro arquivo intacto; (e) sem `--json` → stdout com o caminho absoluto (D5), stderr vazio; (f) não processada → `{"error": {"code": "sermon_not_processed"}}` e saída 5; `sermon download 999` → `not_found`, saída 3; `sermon download abc` → saída 2; vídeo ausente → `internal_error`, saída 1, mensagem do serviço (não "Erro interno inesperado.") sem caminho de `WORDCUT_HOME`; (g) com a trava segurada por outro processo (`lock_owner`), o download funciona (FR-005); (h) `sermon --help` lista `download`; `sermon download --help` traz exemplo `wordcut sermon download ...`; (i) `--json` antes ou depois da ação dá o mesmo resultado | `apps/cli/tests/test_sermon_download_command.py` via `wordcut_cli.main(argv)` com `capsys`, `wordcut_home`, `monkeypatch.chdir` e fixture de pregação processada (create com `FakeLive` + `record_processed` + arquivo falso). Exige mutações: ignorar `-o` → vermelha; devolver `path` relativo → vermelha; `bytes` do arquivo de origem lido errado/fixo → vermelha; render de texto sem o caminho → vermelha |
| 4 — Documentação | `CHANGELOG.md` em `[Não lançado] / Adicionado` descreve `wordcut sermon download <id> [-o caminho]` (nome legível, sem sobrescrever, `path` e `bytes`); `docs/cli.md` §7.5 só muda se o contrato mudar (se a saída `{path, bytes}` for documentada lá, ok); nenhuma ADR aceita editada; texto em português | Leitura de `git diff 53fc42b -- CHANGELOG.md docs` |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário "baixar com nome legível" (spec) / FR-001 / FR-002 / Verificação 1 | Passo 2a (nome sugerido) + 3a (CLI na pasta atual, `path` absoluto, `bytes`, bytes idênticos) |
| Cenário "destino escolhido" (spec) / FR-001 / Verificação 2 (`-o arquivo`) | Passo 1a/1b + 3b (relativo e absoluto, pastas criadas) |
| Borda "`-o` pasta existente → nome legível dentro" / Verificação 2 (`-o pasta`) | Passo 1c + 3c |
| Borda "destino existente → ` (2)`, ` (3)`" / FR-003 / Verificação 3 | Passo 1d (dois níveis, original intacto) + 3d (CLI, duas execuções) |
| Cenário "pregação não processada" / FR-004 / Verificação 4 (1ª parte) | Passo 2c (os quatro estados, saída 5) + 3f (JSON de erro e código de saída) |
| Borda "ID inexistente → `not_found`" / Verificação 4 (2ª parte) | Passo 2d + 3f |
| Borda "título com caracteres proibidos" | Passo 2b |
| Borda "vídeo ausente no disco → `internal_error` com mensagem clara, sem caminho interno" | Passo 2e + 3f (mensagem do serviço chega à CLI; sem `WORDCUT_HOME`) |
| FR-005 — a cópia não pega a trava | Passo 2f + 3g (trava segurada por outro processo; download sai 0) + leitura do diff: nenhum `ProcessingLock` no caminho do download |
| Decisão "nunca deixa arquivo pela metade com o nome final" (plan) | Passo 1e/1f |
| Verificação 5 — quality gates limpos | `uv run pytest -q` verde; `uv run ruff check . && uv run ruff format --check . && uv run mypy` limpos |

## Rodada 1 — 2026-10-26 — working tree sobre 53fc42b

**baseline_commit**: 53fc42b7dd4812ece1a0b251462933971f5584da
**Componentes avaliados**: `packages/core` (`wordcut.files`, `wordcut.service.sermons`),
`apps/cli` (`wordcut_cli.sermon`), `CHANGELOG.md`, `docs/cli.md`
**Suítes**: core + cli (arquivos da issue) ✅ (33 / 0 falhas) · suíte completa ✅ (506 / 0
falhas) · ruff check ✅ · ruff format --check ✅ · mypy ✅
**Mutações** (cópia no scratchpad): 15 de 15 mortas, incluindo todas as exigidas pela matriz.

Barra acrescentada pelo orquestrador nesta rodada (passo 1): sem suporte a hard link
(`EPERM`, `ENOTSUP`/`EOPNOTSUPP`, `EXDEV`), a cópia cai para `open(final, "x")` + cópia dos
bytes, com teste que simule o `OSError`; sem isso, o passo 1 fica PARCIAL.

Fatos do implementador, julgados:
1. Assinatura `copy_without_overwrite(source, destination: str | PathLike, suggested_name)`:
   aceita. A matriz 1c já previa o nome sugerido pela assinatura; o `str` é necessário para
   D3, porque `Path("saida/")` perde o separador final (coberto por
   `test_a_missing_destination_ending_in_a_separator_is_a_folder_created_with_the_name_inside`,
   mutação "separador ignorado" morta). O "Contexto de código" do plan.md ficou com a
   assinatura de dois argumentos (desatualizado, sem efeito no veredito).
2. Sem queda quando `os.link` não é suportado: confirmado. Sondagem com dublê de `os.link`
   lançando `EPERM`, `EOPNOTSUPP` e `EXDEV`: o `OSError` propaga (temporário apagado, pasta
   vazia) e o download viraria `internal_error`. Nenhum teste simula o caso.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Cópia segura | PARCIAL | 1a–1g cobertos em `test_files.py` (9 testes) e as 4 mutações exigidas morrem; falta a queda para `open(final, "x")` + cópia dos bytes quando `os.link` falha com `EPERM`/`ENOTSUP`/`EOPNOTSUPP`/`EXDEV` (`files.py:58` só trata `FileExistsError`) e o teste que simule esse `OSError` |
| 2 — Serviço | PASS | `test_sermon_video.py` (10 testes): 2a–2f; D4 com `details` só `{sermon_id}`; FR-005 com `lock_owner`; 2g pela leitura do diff (sem `argparse`, `print` nem `wordcut_cli`); 5 mutações mortas |
| 3 — CLI | PASS | `test_sermon_download_command.py` (14 testes) + `download` no parametrize de help de `test_sermon_command.py`: 3a–3i; 4 mutações exigidas mortas |
| 4 — Documentação | PASS | `CHANGELOG.md` [Não lançado] / Adicionado; `docs/cli.md` §7.5 documenta pasta, sufixo, `{path, bytes}` e trava; nenhuma ADR alterada; texto em português |

Política de comentários (CONTRIBUTING.md §5): conforme. Comentários novos são de intenção
(`_linked`, `_download`, `_video_file`, bytes não repetitivos nos testes), formato
(`FIRST_COPY_NUMBER`) ou contrato público (docstring de `copy_without_overwrite`), em inglês.

### Critérios de aceite
- ✅ Baixar com nome legível / FR-001 / FR-002 — `test_video_of_a_processed_sermon_is_its_file_with_the_readable_name`, `test_download_with_json_copies_the_video_to_the_current_folder_with_the_readable_name`
- ✅ Destino escolhido (`-o arquivo`, pastas criadas) — `test_copy_creates_the_missing_folders_of_the_destination`, `test_download_to_a_file_path_creates_its_folders_and_answers_the_absolute_path[relative|absolute]`
- ✅ `-o` pasta existente → nome legível dentro — `test_copy_to_an_existing_folder_writes_the_suggested_name_inside_it`, `test_download_to_an_existing_folder_writes_the_readable_name_inside_it`
- ✅ Destino existente → ` (2)`, ` (3)` / FR-003 — `test_existing_destination_is_kept_and_the_copy_gets_2_before_the_extension`, `test_with_2_taken_too_the_copy_gets_3_and_both_earlier_files_are_kept`, `test_a_second_download_gets_2_in_the_name_and_keeps_the_first_file`
- ✅ Não processada → `sermon_not_processed` (5) / FR-004 — `test_a_sermon_not_processed_has_no_video_to_download[4 estados]`, `test_download_of_a_sermon_not_processed_fails_with_sermon_not_processed_and_exit_5`
- ✅ ID inexistente → `not_found` — `test_video_of_a_missing_sermon_is_not_found`, `test_download_of_a_missing_sermon_fails_with_not_found_and_exit_3`
- ✅ Título com caracteres proibidos — `test_characters_forbidden_in_file_names_are_left_out_of_the_readable_name`
- ✅ Vídeo ausente → `internal_error` sem caminho interno — `test_a_processed_sermon_whose_video_left_the_disk_is_an_internal_error_without_the_data_folder`, `test_a_processed_sermon_without_a_video_path_is_the_same_internal_error`, `test_download_of_a_sermon_whose_video_left_the_disk_is_the_service_internal_error`
- ✅ FR-005 — `test_video_is_found_while_another_process_holds_the_processing_lock`, `test_download_works_while_another_process_holds_the_processing_lock`; nenhum `ProcessingLock` no caminho do download
- ✅ Nunca arquivo pela metade com o nome final — `test_a_copy_that_fails_midway_leaves_neither_the_final_name_nor_a_temporary_file`, `test_after_a_copy_the_destination_folder_holds_only_the_copied_file`
- ❌ Queda sem hard link (`EPERM`/`ENOTSUP`/`EXDEV` → `open(final, "x")`, decisão do orquestrador) — sem implementação e sem cobertura
- ✅ Verificação 5 — quality gates limpos (506 passed; ruff e mypy limpos)

### Veredito geral: PARCIAL
Sem FAIL; o passo 1 reabre só pela queda sem hard link e pelo teste que simule o `OSError`.

## Rodada 2 — 2026-10-26 — working tree sobre 53fc42b

**baseline_commit**: 53fc42b7dd4812ece1a0b251462933971f5584da
**Componentes avaliados**: `packages/core` (`wordcut.files`), regressão de `wordcut.service.sermons`,
`apps/cli` (`wordcut_cli.sermon`), `CHANGELOG.md`, `docs/cli.md`
**Suítes**: core + cli (arquivos da issue) ✅ (43 / 0 falhas) · suíte completa ✅ (516 / 0
falhas) · ruff check ✅ · ruff format --check ✅ · mypy ✅
**Mutações** (cópia no scratchpad): 15 de 15 mortas: 11 na queda sem hard link e as 4 exigidas
pela matriz do passo 1, rodadas de novo como regressão.

Barra desta rodada (passo 1, reaberto): sem hard link (`EPERM`, `ENOTSUP`/`EOPNOTSUPP`,
`EXDEV`), a cópia usa `open(final, "x")` + cópia, sem sobrescrever, com sufixo se o destino
existir, sem temporário no fim e com teste para cada `errno`; outros `OSError` propagam; o
"Contexto de código" do plan.md traz a assinatura real.

Fato do implementador, julgado: no caminho de queda, o nome final existe pela metade durante a
cópia e é apagado se a cópia falhar. Confirmado (`files.py:79-92`) e aceito, como decidiu o
orquestrador. A divergência está registrada no plan.md (Decisões técnicas, "Queda sem hard
link") e na docstring de `copy_without_overwrite`. Só um processo morto durante a cópia
(`SIGKILL`) deixa esse arquivo pela metade. Fora da queda, o mesmo caso deixa só um `.part`.
Nota: no Linux, `ENOTSUP == EOPNOTSUPP == 95`, então os dois ids do parametrize exercitam o
mesmo valor. Isso não é falha: o conjunto `NO_HARD_LINK` traz os dois nomes.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Cópia segura | PASS | `files.py:71-92`: `os.link` com `errno` em `NO_HARD_LINK` vai para `_copy_exclusive` (`open("xb")` + `copyfileobj`). O `FileExistsError` do `open` fica fora do `try` e leva ao próximo sufixo sem apagar o existente. O temporário sai no `finally`. Testes: `test_without_hard_links_the_copy_still_lands_with_identical_bytes_and_no_temporary_file[EPERM\|ENOTSUP\|EOPNOTSUPP\|EXDEV]`, `test_without_hard_links_an_existing_destination_is_kept_and_the_copy_gets_2[4 errno]`, `test_another_link_error_propagates_and_leaves_the_destination_folder_empty` (EIO) e `test_without_hard_links_a_failed_copy_leaves_no_final_name_and_no_temporary_file`. 1a–1g seguem cobertos. O plan.md "Contexto de código" traz `copy_without_overwrite(source, destination: str \| PathLike, suggested_name) -> Path`, a assinatura real. 15 mutações mortas |
| 2 — Serviço | PASS | Sem mudança desde a Rodada 1; `test_sermon_video.py` verde |
| 3 — CLI | PASS | Sem mudança desde a Rodada 1; `test_sermon_download_command.py` verde |
| 4 — Documentação | PASS | Sem mudança desde a Rodada 1 |

Política de comentários (CONTRIBUTING.md §5): conforme. Os comentários novos explicam intenção
(`NO_HARD_LINK`, docstrings de `_placed` e `_copy_exclusive`) e estão em inglês.

### Critérios de aceite
- ✅ Baixar com nome legível / FR-001 / FR-002: os mesmos testes da Rodada 1
- ✅ Destino escolhido (`-o arquivo`, pastas criadas): os mesmos testes da Rodada 1
- ✅ `-o` pasta existente → nome legível dentro: os mesmos testes da Rodada 1
- ✅ Destino existente → ` (2)`, ` (3)` / FR-003: os mesmos testes da Rodada 1, mais `test_without_hard_links_an_existing_destination_is_kept_and_the_copy_gets_2`
- ✅ Não processada → `sermon_not_processed` (5) / FR-004: os mesmos testes da Rodada 1
- ✅ ID inexistente → `not_found`: os mesmos testes da Rodada 1
- ✅ Título com caracteres proibidos: os mesmos testes da Rodada 1
- ✅ Vídeo ausente → `internal_error` sem caminho interno: os mesmos testes da Rodada 1
- ✅ FR-005: os mesmos testes da Rodada 1
- ✅ Nunca arquivo pela metade com o nome final: vale no caminho com hard link (testes da Rodada 1). Sem hard link, o nome final é apagado na falha (`test_without_hard_links_a_failed_copy_leaves_no_final_name_and_no_temporary_file`), com a divergência aceita acima
- ✅ Queda sem hard link (`EPERM`/`ENOTSUP`/`EOPNOTSUPP`/`EXDEV` → `open(final, "x")`; outros `OSError` propagam): os quatro testes do passo 1 acima
- ✅ Verificação 5, quality gates limpos: 516 passed; ruff e mypy limpos

### Veredito geral: PASS
O passo 1 fechou a lacuna da Rodada 1. Todos os passos estão `[x]` e PASS, todos os critérios
estão cobertos, e as suítes e as checagens estão verdes.
