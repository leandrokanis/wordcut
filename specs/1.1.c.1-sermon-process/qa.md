# QA — 1.1.c.1 — Processar a pregação (`sermon process`)

## Plano de QA — 2026-10-26

**baseline_commit**: d5ac68d80b1844baaebb8b0652df93ea3271834f
**Componentes em escopo**: `packages/core` (`wordcut.processing` novo — `__init__`, `pipeline`,
`sentences`; `wordcut.tasks.process` novo e `BUILTIN_KIND_MODULES`; `wordcut.service.processing`
novo; `wordcut.service.sermons`; `wordcut.db.transcripts` novo e migração `0004_transcripts.sql`;
`wordcut.youtube` (`download_audio_window`); `wordcut.overview`; `wordcut.errors`
(`transcription_error`)); `apps/cli` (`wordcut_cli.sermon`); `docs/architecture/README.md`
(§4, §5.1), `docs/cli.md` (§5.1, §5.3, §7.2), `CHANGELOG.md`.
**Suítes que valem como prova**:
- core: `uv run pytest packages/core/tests/test_sentences.py packages/core/tests/test_pipeline.py packages/core/tests/test_process_task.py packages/core/tests/test_processing_service.py -q`
  (+ `test_overview.py`, `test_errors.py`, `test_sermons_service.py`, `test_sermon_trim.py`,
  `test_tasks.py`, `test_task_detached.py`, `test_youtube.py`, `test_db.py` como regressão)
- cli: `uv run pytest apps/cli/tests/test_sermon_process_command.py -q` (+ `test_sermon_command.py`,
  `test_sermon_trim_command.py`, `test_task_command.py`, `test_legacy_commands.py`,
  `test_cli_contract.py` como regressão)
- suíte completa: `uv run pytest -q`
- estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`

Fontes da barra: `spec.md`, `plan.md`, docs/cli.md §3.3, §3.4, §4.5, §5, §6, §7.1, §7.2, §7.4,
§14; ADR-0007, ADR-0013; código no baseline (`sermon.py`, `sync.py`, `media.py`, `youtube.py`,
`overview.py`, `transcript.py`, `asr/`, `tasks/`, `service/{sermons,tasks}.py`, `db/`,
`wordcut_cli/{sermon,tasks_support}.py`, `conftest.py` da raiz). Sem rastreador: os critérios saem
dos cenários do spec e da Verificação do plano. Onde o plano não decidiu, a barra adota a opção
mais conservadora e a registra em **Lacunas** (execução automatizada aprovada pelo
administrador; sem perguntas).

**Prova aceita**: teste de comportamento pela interface pública — `pipeline.process` com dublês de
`ProcessingGateways`; `start_processing`/`show_sermon` com SQLite real em `WORDCUT_HOME`
temporário (fixture `wordcut_home`); `wordcut_cli.main([...])` com `capsys` separando stdout e
stderr. Erros julgados por `code`, saída e `details` (docs/cli.md §5.2), nunca por `message`.
**Não vale**: teste que só verifica que um mock foi chamado; asserção sobre texto de
`message`; teste que alcance YouTube, WhisperX ou vídeo real. **Único `ffmpeg` real permitido**:
clipe sintético curto (≤ 3 s) gerado por `lavfi`, com `skipif` sem `ffmpeg`, como em
`test_sermon.py`. Testes que esperam outro processo usam `time_limit`.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Frases | (a) `processing/sentences.py` quebra em fim de frase (`.`, `?`, `!`), em pausa **> 1,5 s** (1,5 s exatos não quebra; 1,501 quebra) e em **25 palavras** (25ª fecha a frase; 24 não); (b) cada frase traz início (da 1ª palavra), fim (da última), texto (palavras unidas por espaço) e a posição/índice da 1ª e da última palavra; (c) `overview_lines` produz exatamente a mesma saída do baseline: `test_overview.py` verde **sem alteração** (diff vazio no arquivo) e `test_legacy_commands.py` verde; (d) lista vazia → nenhuma frase | pytest em `packages/core/tests/test_sentences.py` com `Word` fictícios; regressão de `test_overview.py` (diff do arquivo contra o baseline = vazio). Mutações: `>` → `>=` na pausa; `>=` → `>` nas 25 palavras |
| 2 — Pipeline | (a) **Download só da faixa**: o dublê registra `download_section(url, live_start − 30, live_end + 30)` e `download_audio_window(url, live_start − 50, live_start + 40)` — uma chamada de cada, nada da live inteira (sem `download_audio`); com `live_start < 50` os inícios ficam em 0 (L4); (b) **sincronia**: `locate` recebe a janela e o vídeo com `expected_start` relativo à janela (20 s no caso geral) e `search = 20`; o início real do vídeo na live = início da janela + offset devolvido — testado com offset ≠ esperado (ex.: keyframe 1,7 s antes do pedido) (L4); (c) **transcrição**: tempos do transcritor (relativos ao vídeo da faixa) convertidos para a live somando o início real; (d) **ajuste às palavras**: primeira palavra com `start ≥ live_start` (palavra exatamente em `live_start` entra; uma que começa 0,01 s antes não) e última com `end ≤ live_end`; `sermon_start = primeira − 0,3`, `sermon_end = última + 1,5`; (e) **corte**: `cut` recebe (`sermon_start − início real`, `sermon_end − início real`) em tempo do arquivo e o destino `…/media/sermons/<id>/sermon.mp4` (L3); (f) **palavras e frases em tempo da pregação** (1ª palavra começa em 0,3 s), só as da primeira à última dentro das bordas (L5), com `score` e `estimated` preservados; (g) corte fora do vídeo baixado ou nenhuma palavra nas bordas → erro claro, sem corte (L6); (h) `YouTubeError` → `youtube_error`; falha do transcritor (`FileNotFoundError` do ambiente ausente, `CalledProcessError`) → `transcription_error`; (i) progresso: mensagens em português por etapa (baixar, sincronizar, transcrever, cortar, gravar) com frações nas faixas do plano e não decrescentes; (j) **integração com `ffmpeg` real**: clipe `lavfi` de 3 s 16:9 (ex.: `testsrc2=size=320x180` + `sine`) como “faixa”, dublês para download/locate/transcrição, `cut` real (`default_gateways().cut` ou `media.cut_with_fades`) → arquivo existe, duração = `sermon_end − sermon_start` (± 1 quadro), geometria 16:9 igual à da fonte, com trilha de áudio | pytest em `packages/core/tests/test_pipeline.py` com dublê de `ProcessingGateways` que grava as chamadas e devolve valores conhecidos; `test_youtube.py` para os argumentos de `download_audio_window` (só áudio, `--download-sections`), sem executar `yt-dlp`. Mutações: `LEAD_IN_S`/`TAIL_S` trocados ou com sinal invertido; `>=` → `>` na 1ª palavra; ignorar o início da janela na sincronia; gravar em tempo da live |
| 3 — Persistência | (a) migração 0004 aplica sobre um banco no estado 0003 com pregações existentes, sem perdê-las (`user_version` = 4); (b) `words` com id, sermon_id, position, text, start, end, score, estimated; `sentences` com id, sermon_id, position, first_word_id, last_word_id, start, end, text; colunas `sermon_start`, `sermon_end`, `video_path`, `processed_at` em `sermons`; (c) gravar e reler devolve os mesmos valores em ordem de `position`; `first_word_id`/`last_word_id` apontam para palavras da mesma pregação; (d) apagar as de uma pregação não toca as de outra; (e) IDs `AUTOINCREMENT`: depois de apagar e regravar, nenhum ID antigo é reaproveitado (docs/cli.md §3.3) (L14) | pytest com SQLite real (`test_db.py` para a migração; repositório testado pelos testes do passo 4 ou arquivo próprio). Mutação: apagar sem `WHERE sermon_id` |
| 4 — Tipo de tarefa e serviço | (a) `start_processing(..., detach=False)` numa pregação `trimmed` de live terminada, com `default_gateways` substituído por dublê (`monkeypatch`) → tarefa `process` `succeeded`, pregação `processed`, `sermon_start`/`sermon_end`/`video_path`/`processed_at` gravados, palavras e frases relidas do banco, `work/` removido, `sermon.mp4` no lugar; (b) durante o `transcribe` do dublê, a pregação relida do banco está `processing` (L2); (c) falha (`youtube_error`, `transcription_error`, exceção inesperada → `internal_error`) → tarefa `failed` com o `code`, pregação `failed`, `WordcutError` com a saída certa (6, 6, 1); (d) pré-condições **sem criar tarefa** (contagem de `tasks` igual antes e depois) e sem mudar a pregação: inexistente → `not_found` (3); sem bordas → `sermon_not_trimmed` (5); live não terminada → `live_not_finished` (5); `processed` sem `force` → `would_discard_edits` (5); `processing` com tarefa viva → `busy` (4); trava ocupada por outro processo (`lock_owner`) → `busy` (4) com `details.task_id`/`kind` quando houver; (e) `failed` → processa de novo e termina `processed`; (f) `force` numa `processed` substitui palavras e frases (contagens novas, IDs antigos ausentes) e funciona com `sermon.mp4` pré-existente (L3); (g) reconciliação: pregação `processing` cuja última tarefa `process` está `running` com PID morto → `show_sermon` devolve `failed` e `last_task` `failed`/`interrupted`; `list --status processing` não a mostra (L9); (h) `last_task` do `show` é a última tarefa da pregação, no formato de `task show` (L9); (i) `transcription_error` em `EXIT_CODES` com saída 6 e em `test_errors.py`; (j) `process` está em `BUILTIN_KIND_MODULES` e `kind("process").needs_lock` é verdadeiro | pytest em `test_process_task.py` e `test_processing_service.py`, SQLite real, dublê de gateways por `monkeypatch` de `default_gateways` em primeiro plano; `lock_owner` para a trava; PID morto = PID de um subprocesso já colhido. Mutações: remover a checagem de `would_discard_edits`; remover o `failed` no erro; remover a reconciliação; apagar palavras sem `force` |
| 5 — CLI | (a) `sermon process <id> --wait --json` (dublês) → saída 0, stdout = um documento JSON com a pregação `processed` (L7), stderr com linhas `[process] <etapa> NN%` em ordem; `--quiet` sem essas linhas; (b) `sermon process <id> --json` sem `--wait` → na hora `{"task_id", "kind": "process", "status": "running", "sermon_id"}` (§6.2), com o filho substituído por processo inofensivo (L1), e `sermon show <id> --json` logo depois mostra `processing` (L2); (c) erros com `code` e saída do contrato: `not_found` 3, `sermon_not_trimmed` 5, `live_not_finished` 5, `would_discard_edits` 5, `busy` 4, `youtube_error` 6, `transcription_error` 6; (d) `--force` aceito e repassado; (e) `create <link> --start … --end … --process --wait --json` faz tudo (pregação criada, delimitada e `processed`, saída 0); `--process` sem bordas → `invalid_argument` (2) com `details.argument` e **nenhuma pregação criada**; demais casos de L12 testados; (f) `show <id> --transcript --json` → frases em ordem, cada uma com ID, início, fim, texto, `first_word_id`, `last_word_id`, em tempo da pregação (L8); sem `--transcript`, o JSON de `show` não traz a transcrição; saída legível com uma frase por linha; (g) `--help` de `process` e opções novas em português | pytest em `apps/cli/tests/test_sermon_process_command.py` via `main([...])`, `FakeLive` para o create e `monkeypatch` de `default_gateways`; `capsys` para stdout/stderr. Mutação: tirar `--force` do repasse |
| 6 — Documentação | `docs/architecture/README.md` §4 (tipo `process`, `wordcut.processing`, tabelas `words`/`sentences`) e §5.1 (fluxo real: faixa + janela, sincronia, transcrição, corte, gravação; sugestão do LLM marcada como item 9); `docs/cli.md` §5.3 com `transcription_error` (6) e §5.1 coerente com ele; §7.2 com o formato de `--transcript` e os campos novos do `show` (L7, L8); `CHANGELOG.md` `[Não lançado]` cita `sermon process`, `create --process`, `show --transcript`, migração 0004 | leitura do diff contra o baseline; `uv run pytest -q` cobre `test_errors.py` |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário “processar uma pregação delimitada” / Verificação 2 (FR-001, FR-003, FR-004, FR-005, FR-008) | CLI 5(a) + serviço 4(a); vídeo 16:9 com fades provado pela integração 2(j) e pelos `test_media.py` existentes (fades) |
| Cenário “processar em segundo plano” / Verificação 3 (FR-001, FR-005) | CLI 5(b) + serviço 4(b) |
| Cenário “transcrição consultável” / Verificação 4 (FR-004, FR-007) | CLI 5(f) + repositório 3(c) |
| Cenário “refazer o que falhou” (1.1.c.3) / Verificação 5 (FR-005) | serviço 4(e) + CLI com pregação `failed` → saída 0 e `processed`; L3 (sem resto de execução anterior) |
| Cenário “reprocessar com novas bordas” (1.1.b.3) / Verificação 6 (FR-006) | serviço 4(d) `would_discard_edits` + 4(f) `force`; CLI 5(c), 5(d) |
| Cenário “pré-condições” / Verificação 7 | serviço 4(d) com contagem de tarefas; CLI 5(c) |
| Borda: máquina ocupada → `busy` (4), pregação inalterada / Verificação 7 | serviço 4(d) com `lock_owner` e com pregação `processing` viva; pregação relida igual |
| Borda: falha do YouTube → tarefa `failed`/`youtube_error`, pregação `failed` / Verificação 8 | pipeline 2(h) + serviço 4(c) + CLI 5(c) |
| Borda: falha da transcrição → `failed`, mensagem clara, `transcription_error` / Verificação 8 | pipeline 2(h) + serviço 4(c) + 4(i) + CLI 5(c) |
| Borda: processo morto → tarefa `failed`/`interrupted` (docs/cli.md §6.5; L13) e pregação `failed` na leitura / Verificação 9 | serviço 4(g) |
| Borda: `create … --process [--wait]` / Verificação 10 | CLI 5(e) |
| FR-002 / Verificação 1 (pipeline com dublês: só faixa e janela, sincroniza, transcreve, ajusta, corta) | pipeline 2(a)–2(g) |
| FR-008 (mídias em `WORDCUT_HOME`, pasta por pregação) | serviço 4(a): caminho sob `WORDCUT_HOME/media/sermons/<id>/`, `work/` apagado no sucesso |
| Progresso no stderr (§4.5, 1.1.c.2) | pipeline 2(i) + CLI 5(a) |
| Verificação 11: quality gates limpos | `uv run pytest -q`, `ruff check`, `ruff format --check`, `mypy` verdes |

### Lacunas (o plano não decidiu, ou decidiu de forma incompleta; barra adotada)

- **L1 — Filho destacado usaria dependências reais.** `default_gateways()` roda no processo do `runner`; `monkeypatch` não atravessa processo, e a fixture `detached_tasks` usa o `Popen` real. Barra: nenhum teste lança `process` destacado com o runner real; o teste “sem `--wait`” troca `wordcut.tasks.execution.Popen` por um filho inofensivo (ex.: `python -c "import time; time.sleep(30)"`, mesma assinatura, sessão própria, colhido no fim). Recomendado: fixture autouse em core e cli que faz `default_gateways` falhar se alcançado (como `NoYouTube`).
- **L2 — `processing` logo após o lançamento.** A tarefa marca `processing` só quando o filho começa; logo após o retorno sem `--wait` (e com o filho falso de L1) a pregação ainda está `trimmed`. Barra: `show`/`list` relatam `processing` enquanto a última tarefa `process` da pregação estiver `running` (simétrico à reconciliação de `failed`), ou o serviço grava `processing` antes do lançamento, dentro da trava. Gravar depois do retorno é recusado (corrida com o fim do filho).
- **L3 — Arquivos de uma execução anterior.** `media.cut_with_fades` nunca sobrescreve (`FileExistsError` → `internal_error`), e o `yt-dlp` pula o download se o arquivo já existe; com `--force`, ou ao refazer um `failed` depois de novas bordas, o pipeline falharia ou usaria a faixa velha. Barra: `work/` limpo no início da tarefa (ou intermediários com as bordas no nome); corte num arquivo temporário trocado por `sermon.mp4` só no sucesso. Testes: `--force` com `sermon.mp4` existente termina `processed`; refazer com `work/` antigo e bordas diferentes pede o download das bordas novas.
- **L4 — Base de tempo da sincronia.** A janela de áudio começa em `live_start − 50`, e `locate_clip` devolve o offset relativo ao arquivo da janela; o plano não diz quem converte, nem o que acontece com `live_start < 50` ou `live_end + 30 > live_duration`. Barra: `expected_start` relativo à janela; início real = início da janela + offset; início da janela e da faixa limitado a 0 e fim limitado à duração da live, quando conhecida; teste com `live_start = 10`.
- **L5 — Quais palavras gravar.** O corte `[primeira − 0,3, última + 1,5]` pode incluir palavras fora das bordas (`Transcript.between` pega tudo que cabe no intervalo). Barra: gravar exatamente da primeira à última palavra dentro das bordas; teste com uma palavra que termina na margem de 0,3 s antes de `live_start` e não pode aparecer.
- **L6 — Sem palavras nas bordas / corte fora do vídeo baixado.** O código de erro não foi decidido. Barra: tarefa e pregação `failed`, nada gravado, sem `sermon.mp4`, com `code` do contrato (`internal_error`, saída 1, ou um código novo documentado em §5.3) e teste explícito. Recomendado decidir e documentar.
- **L7 — Resultado de `--wait`.** §6.3 manda devolver a pregação; o plano não define o `Result` do tipo `process` nem quais campos novos o `show` expõe. Barra: resultado = pregação no formato do `show` (`status: processed`), com `sermon_start`, `sermon_end` (tempo da live) e `processed_at`; o JSON só cresce; documentar em §7.2.
- **L8 — Formato de `--transcript`.** Chave e nomes de campo não decididos. Barra: `"sentences": [{"id", "start", "end", "text", "first_word_id", "last_word_id"}]` em ordem de posição, só com `--transcript`; IDs de palavra existentes na pregação; documentar em §7.2.
- **L9 — `last_task` e reconciliação na leitura.** `show_sermon(connection, id)` não recebe `Home`, que a reconciliação de tarefas precisa (dono da trava), e o plano só reconcilia no `show`. Barra: `show` e `list` reconciliam (tarefa órfã → `failed`/`interrupted`; pregação `processing` → `failed`); `last_task` no formato de `task show`.
- **L10 — Pré-condição fora da trava.** As pré-condições são checadas antes de `tasks.execution.start` adquirir a trava; se outra tarefa terminar `processed` nesse intervalo, um `process` sem `--force` refaria a pregação. Barra: a tarefa revalida `would_discard_edits` (e `sermon_not_trimmed`) ao começar, sob a trava; teste do tipo de tarefa com a pregação já `processed` e `force` falso → `would_discard_edits`.
- **L11 — `live_finished` nunca é atualizado.** A flag vem do `create`; uma pregação criada com a live no ar nunca ficaria processável. Barra: o teste usa a flag gravada; recomendado decidir se o `process` consulta o YouTube (`LiveSource`, dublê nos testes) quando a flag está falsa. Não bloqueia o PASS do item.
- **L12 — `create --process`.** Barra: sem `--start/--end` → `invalid_argument` antes de qualquer criação; pré-condição do processamento falhando depois do `create` → a pregação continua criada/delimitada, saída do erro do processamento; pregação existente `processed` → `would_discard_edits` (o `create` não tem `--force`); sem `--wait` → objeto de §6.2.
- **L13 — Documentos divergentes.** O spec fala em “tarefa `interrupted`”; docs/cli.md §6.1/§6.5 têm só `running`/`succeeded`/`failed`, com o erro `interrupted`; a barra segue o docs/cli.md. `transcription_error` na saída 6 contraria a definição de §5.1 (“YouTube, OpenRouter ou rede”); atualizar §5.1 junto com §5.3. §7.4 e o diagrama §5.1 prometem a sugestão do LLM (item 9); a documentação deve marcá-la como pendente.
- **L14 — IDs e atomicidade.** Barra: `words` e `sentences` com `AUTOINCREMENT` (IDs nunca reaproveitados, §3.3); palavras, frases e o estado `processed` gravados numa transação só, para que um erro na gravação não deixe transcrição parcial com a pregação `processed`.

## Rodada 1 — 2026-10-26 — working tree sobre d5ac68d

**baseline_commit**: d5ac68d80b1844baaebb8b0652df93ea3271834f
**Componentes avaliados**: `packages/core` (`processing/`, `tasks/process.py`, `service/processing.py`,
`service/sermons.py`, `db/transcripts.py`, migração 0004, `youtube.py`, `overview.py`, `errors.py`,
`tasks/execution.py`), `apps/cli` (`sermon.py`), `conftest.py`, docs (`cli.md`, arquitetura, ADR-0014,
CHANGELOG, README)
**Suítes**: completa ✅ (468 / 0 falhas) · `ruff check` ✅ · `ruff format --check` ✅ · `mypy` ✅ ·
mutações 45 de 49 mortas (2 equivalentes, 2 sobreviventes) · nenhum processo `wordcut.tasks.runner` vivo

Mutações e sonda feitas numa cópia em scratchpad; a working tree não foi tocada.

### Divergências relatadas pelo implementador

- **2(e) × L3** — aceita. A própria linha 2(e) remete a L3, e L3 (Decisões técnicas) manda cortar em
  `work/sermon.mp4` e trocar `sermon.mp4` com `os.replace` só no sucesso. O pipeline corta em
  `workdir/sermon.mp4` (`pipeline.py:153-159`); a tarefa move para `media/sermons/<id>/sermon.mp4`
  (`tasks/process.py:84-85`). Provado por `test_media_end_in_the_sermon_folder_and_the_work_files_are_removed`;
  a mutação que tira o `os.replace` morre.
- **6º método `duration`** — aceito. Está nas Decisões técnicas (“Duração da faixa”, para L6), na
  ADR-0014 e em `LocalGateways` (`media.duration_seconds`); as mutações na checagem de L6 morrem.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Frases | PASS | `test_sentences.py` (fim de frase, pausa 1,5/1,501 s, 24/25 palavras, vazio); `test_overview.py` sem diff contra o baseline e verde; mutações `>`→`>=` e `>=`→`>` mortas |
| 2 — Pipeline | PASS | `test_pipeline.py`: só faixa e janela, com limites em 0 e na duração (L4); `locate` com `expected_start` 20/0 e offset ≠ esperado; ajuste às palavras na borda exata; palavras e frases em tempo da pregação (L5); `processing_error` sem corte (L6); `youtube_error`/`transcription_error` 6; progresso. `test_pipeline_cut.py`: `ffmpeg` real em clipe `lavfi` de 3 s (duração ± 1 quadro, 320x180, áudio). 18 de 18 mutações mortas. 2(e) julgado por L3 |
| 3 — Persistência | PASS | `test_transcripts_repository.py`: banco no esquema 3 migra sem perder a pregação; gravar e reler em ordem com `first/last_word_id`; outra pregação intocada; IDs nunca reaproveitados. Mutações sem `WHERE sermon_id` e sem `AUTOINCREMENT` mortas. Atomicidade (L14) conferida na leitura: `tasks/process.py:100-105` |
| 4 — Tipo de tarefa e serviço | PARCIAL | Comportamentos 4(a)–(j) cobertos e verdes, mas duas mutações exigidas sobrevivem: (1) tirar o `failed` da pregação no erro (`tasks/process.py:66`) — a reconciliação de `show`/`list` mascara nos testes, mas `sermon trim` logo após a falha responde `busy` (sonda na cópia: original `trimmed`, mutante `busy`); (2) L10: tirar `check_processable` do `admit` (`service/processing.py:151-154`) sobrevive. A checagem da tarefa (`tasks/process.py:57`) vê `processing`, já gravado pelo `admit`, e nunca recusa no fluxo real. O teste de L10 (`test_the_task_refuses_a_sermon_processed_meanwhile…`) chama a tarefa sem `admit`, então a guarda que vale não tem teste |
| 5 — CLI | PASS | `test_sermon_process_command.py`: `--wait --json` com etapas no stderr e `--quiet`; sem `--wait` → objeto §6.2 e `show` `processing` com filho inofensivo (L1/L2); códigos 3/4/5/6; `--force`; `create --process` (L12, nada criado sem bordas); `--transcript` em JSON e texto (L8); `--help` em português. 7 de 7 mutações mortas |
| 6 — Documentação | PASS | `docs/cli.md` §5.1, §5.3 (`processing_error` 1, `transcription_error` 6), §7.1, §7.2 (campos novos e `sentences`), §7.4 (item 9, etapas, resultado de `--wait`), §14; arquitetura §3, §4 e §5.1 (item 9 marcado); ADR-0014 e índice; CHANGELOG; README |

### Critérios de aceite
- ✅ Processar uma pregação delimitada (Verificação 2) — `test_process_with_wait_prints_the_processed_sermon_and_the_stages_on_stderr`, `test_processing_in_the_foreground_…`, `test_the_cut_sermon_lasts_…_with_audio`
- ✅ Processar em segundo plano (Verificação 3) — `test_process_without_wait_answers_the_running_task_and_the_sermon_is_processing`, `test_a_detached_processing_answers_at_once_…`, `test_the_sermon_is_processing_while_the_task_works`
- ✅ Transcrição consultável (Verificação 4) — `test_show_with_transcript_in_json_…`, `test_show_with_transcript_lists_the_sentences_…`, `test_recorded_words_and_sentences_are_read_back_…`
- ✅ Refazer o que falhou (Verificação 5) — `test_a_failed_sermon_is_processed_again_by_the_same_operation`, `test_a_new_processing_downloads_again_…` (L3)
- ✅ Reprocessar com novas bordas (Verificação 6) — `would_discard_edits` no serviço e na CLI; `test_force_discards_the_old_transcript_…`, `test_force_processes_a_processed_sermon_again`
- ✅ Pré-condições sem criar tarefa (Verificação 7) — `test_a_sermon_that_cannot_be_processed_is_refused_without_a_task_and_unchanged`, `…_exits_with_the_contract_code_and_no_task`
- ✅ Máquina ocupada → `busy`, pregação inalterada — `test_a_busy_machine_refuses_with_the_holder_…`, `test_a_sermon_being_processed_refuses_another_processing_as_busy`, `test_process_while_the_machine_is_busy_exits_4`
- ✅ Falha do YouTube → `failed`/`youtube_error` (Verificação 8) — pipeline, serviço e CLI
- ✅ Falha da transcrição → `transcription_error` (Verificação 8) — pipeline, serviço e CLI; `test_errors.py`
- ✅ Processo morto → tarefa `failed`/`interrupted`, pregação `failed` na leitura (Verificação 9) — `test_a_sermon_whose_task_process_died_…`, `test_listing_processing_sermons_leaves_out_…`
- ✅ `create … --process [--wait]` (Verificação 10) — `test_create_with_borders_and_process_with_wait_…` e demais casos de L12
- ✅ FR-002 / Verificação 1 — `test_only_the_section_around_the_borders_and_the_sync_window_…` e demais testes de `test_pipeline.py`
- ✅ FR-008 — `test_media_end_in_the_sermon_folder_and_the_work_files_are_removed`
- ✅ Progresso no stderr — `test_progress_names_each_stage_…`, `test_the_task_reports_each_stage_up_to_saving`, teste da CLI
- ✅ Quality gates (Verificação 11) — suíte, ruff e mypy verdes

### Observações (fora da barra; não pesam no veredito)
- `sermon trim` não reconcilia: depois de um processo morto (sem gravar `failed`), o `trim` responde `busy` até um `show`/`list`. L9 exige só `show` e `list`.
- `os.replace` roda antes da transação que grava a transcrição (`tasks/process.py:85-87`). Se a gravação falhar, o `sermon.mp4` anterior já foi substituído.
- Numa falha com `--force`, `sermon_start`, `sermon_end`, `video_path` e `processed_at` antigos ficam na pregação `failed`.
- Política de comentários (CONTRIBUTING.md §5): os comentários novos estão em inglês e são de tipos permitidos (intenção, formato, referência). Os `# fmt: skip` sem motivo seguem o padrão do baseline.
- ADR-0014 está coerente com o código, menos no ponto da 2ª pendência do passo 4: a revalidação da tarefa não protege no fluxo real. O status “Aceita” foi gravado por agente e precisa de revisão humana.

### Veredito geral: PARCIAL
O passo 4 fica PARCIAL por dois motivos. A guarda de L10 que vale (`admit`) não tem teste, e o `failed` gravado no erro não está fixado por teste, embora tenha efeito observável no `trim`. Os demais passos e os 15 critérios passam.

## Rodada 2 — 2026-10-26 — working tree sobre d5ac68d

**baseline_commit**: d5ac68d80b1844baaebb8b0652df93ea3271834f
**Componentes avaliados**: `packages/core` (`tasks/process.py`, `service/processing.py`, `service/sermons.py`,
`tasks/execution.py` e os demais arquivos do item, como regressão), `apps/cli` (`sermon.py`), `conftest.py`,
docs (ADR-0014, arquitetura §4 e §5.1)
**Suítes**: completa ✅ (470 / 0 falhas) · `ruff check` ✅ · `ruff format --check` ✅ · `mypy` ✅ ·
mutações do passo 4: 6 de 7 mortas (2 equivalentes à parte, 1 sobrevivente) · nenhum processo
`wordcut.tasks.runner` vivo

Barra desta rodada: matriz do topo, decisões L1–L14 do `plan.md` (L10 reescrita pelo orquestrador: o `admit`
revalida sob a trava e a tarefa não repete a checagem) e os dois achados do passo 4 da Rodada 1. Mutações e
sonda feitas numa cópia em scratchpad; a working tree não foi tocada.

### O que mudou desde a Rodada 1

- `tasks/process.py`: a tarefa não revalida mais as pré-condições; só relê a pregação, apaga a transcrição
  com `force` e confirma `processing`. Em qualquer exceção (`except BaseException`, linhas 42-45) grava `failed`.
- `service/processing.py`: `check_processable` virou `_processable`; o `admit` (linhas 38-41) revalida e grava
  `processing` sob a trava.
- Testes: entram `test_a_sermon_whose_processing_failed_can_be_trimmed_again_at_once`,
  `test_a_sermon_whose_detached_processing_failed_can_be_trimmed_again_at_once` e
  `test_a_sermon_processed_between_the_check_and_the_lock_is_refused_without_a_task`. Sai o teste que chamava a
  tarefa sem `admit`.
- ADR-0014 e o diagrama §5.1 da arquitetura descrevem a revalidação no `admit`, coerentes com o código.

### Mutações do passo 4

| Mutação | Resultado |
|---|---|
| tarefa sem `set_status failed` no erro (exigida) | morta: os 2 testes de `trim` após falha (primeiro plano e destacado) |
| `admit` sem `_processable` (L10, exigida) | morta: `test_a_sermon_processed_between_the_check_and_the_lock_…` |
| `admit` revalida com `force=True` (sem `would_discard_edits` sob a trava) | morta: mesmo teste |
| `_processable` sem `would_discard_edits` (exigida) | morta: 4 testes (serviço e CLI) |
| `show`/`list` sem reconciliação (exigida) | morta: 2 testes |
| `admit` não grava `processing` (L2) | morta: 3 testes |
| apagar a transcrição sem `force` (exigida) | equivalente: uma pregação que não está `processed` nunca tem transcrição, e `transcripts.replace` apaga antes de gravar |
| tarefa sem `set_status processing` | equivalente: o `admit` já gravou |
| `failed` gravado só para `WordcutError` (`except BaseException` → `except WordcutError`) | **sobreviveu**: com exceção inesperada (`internal_error`, 4(c)) a pregação fica `processing` no banco. Sonda na cópia com `BrokenCut`: original → `trim` aceita (`trimmed`); mutante → `trim` responde `busy` |

O teste de L10 prova a guarda pelo fluxo real. `start_processing` passa pela checagem de fora da trava, e,
durante a consulta ao YouTube (`LiveSource`), outro processamento termina `processed`. O `admit` recusa com
`would_discard_edits`, sem segunda tarefa.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Frases | PASS | sem mudança desde a Rodada 1; `test_sentences.py` e `test_overview.py` verdes |
| 2 — Pipeline | PASS | sem mudança desde a Rodada 1; `test_pipeline.py` e `test_pipeline_cut.py` verdes |
| 3 — Persistência | PASS | sem mudança desde a Rodada 1; `test_transcripts_repository.py` verde |
| 4 — Tipo de tarefa e serviço | PARCIAL | Os dois achados da Rodada 1 foram resolvidos: as mutações exigidas (sem `failed` no erro; `admit` sem revalidação) ficam vermelhas pelo fluxo real, e o `trim` logo após uma falha de `youtube_error` responde `trimmed`. Resta uma lacuna na mesma linha 4(c). O `failed` gravado só está fixado para `WordcutError`. Com a mutação `except WordcutError` (`tasks/process.py:42`), uma exceção inesperada (`internal_error`) deixa a pregação `processing`, e o `trim` logo depois responde `busy`. Nenhum teste vê isso, porque `test_a_failure_leaves_the_task_and_the_sermon_failed_with_its_error[BrokenCut…]` lê pelo `show`, que reconcilia. Basta estender o teste de `trim` após falha aos três casos de 4(c) |
| 5 — CLI | PASS | sem mudança desde a Rodada 1; `test_sermon_process_command.py` verde; mutação `would_discard_edits` mata 2 testes da CLI |
| 6 — Documentação | PASS | ADR-0014 (linhas 27-30) e §5.1 da arquitetura atualizados para a L10 reescrita; demais docs inalterados |

### Critérios de aceite
- ✅ Processar uma pregação delimitada (Verificação 2) — mesmos testes da Rodada 1, verdes
- ✅ Processar em segundo plano (Verificação 3) — `test_a_detached_processing_answers_at_once_…`, `test_process_without_wait_…`
- ✅ Transcrição consultável (Verificação 4) — mesmos testes da Rodada 1
- ✅ Refazer o que falhou (Verificação 5) — `test_a_failed_sermon_is_processed_again_…`, `test_a_new_processing_downloads_again_…`
- ✅ Reprocessar com novas bordas (Verificação 6) — `would_discard_edits` (fora e sob a trava) e `--force`
- ✅ Pré-condições sem criar tarefa (Verificação 7) — `test_a_sermon_that_cannot_be_processed_…`, `test_a_sermon_processed_between_the_check_and_the_lock_…`
- ✅ Máquina ocupada → `busy`, pregação inalterada — mesmos testes da Rodada 1
- ✅ Falha do YouTube → `failed`/`youtube_error` (Verificação 8) — inclui `failed` gravado e `trim` após a falha, em primeiro plano e destacado
- ✅ Falha da transcrição → `transcription_error` (Verificação 8) — pipeline, serviço e CLI. O estado gravado no banco só é visto pelo `show`, que reconcilia. A mutação que sobreviveu não afeta este caso, porque `transcription_error` é `WordcutError`
- ✅ Processo morto → tarefa `failed`/`interrupted`, pregação `failed` na leitura (Verificação 9)
- ✅ `create … --process [--wait]` (Verificação 10)
- ✅ FR-002 / Verificação 1
- ✅ FR-008
- ✅ Progresso no stderr
- ✅ Quality gates (Verificação 11) — 470 testes, ruff e mypy verdes

### Observações (fora da barra; não pesam no veredito)
- Também não há teste do Ctrl+C (`KeyboardInterrupt`) na tarefa `process`. O `except BaseException` grava `failed`, mas não foi provado.
- Seguem as observações da Rodada 1: o `trim` não reconcilia; o `os.replace` roda antes da transação; os campos antigos ficam numa falha com `--force`.
- ADR-0014 continua “Aceita” gravada por agente e precisa de revisão humana.

### Veredito geral: PARCIAL
Houve progresso: os dois achados da Rodada 1 estão fechados pelo fluxo real. O passo 4 segue PARCIAL por uma lacuna menor na mesma linha 4(c). Não há teste de que o `failed` fica gravado após uma exceção inesperada (`internal_error`). Os demais passos e os 15 critérios passam.

## Rodada 3 — 2026-10-26 — working tree sobre d5ac68d

**baseline_commit**: d5ac68d80b1844baaebb8b0652df93ea3271834f
**Componentes avaliados**: `packages/core` (`tasks/process.py`, `tests/test_processing_service.py`; demais
arquivos do item como regressão), `apps/cli`, docs
**Suítes**: completa ✅ (472 / 0 falhas) · `ruff check` ✅ · `ruff format --check` ✅ · `mypy` ✅ ·
mutações do passo 4: 2 de 2 exigidas mortas · nenhum processo `wordcut.tasks.runner` vivo

Barra desta rodada: matriz do topo, decisões do `plan.md` e o achado do passo 4 na Rodada 2. O teste de `trim`
logo após a falha precisa cobrir `youtube_error`, `transcription_error` e exceção inesperada (`internal_error`),
e falhar com a mutação `except BaseException` → `except WordcutError` em `tasks/process.py`. As mutações
foram feitas numa cópia em scratchpad, e a working tree não foi tocada.

### O que mudou desde a Rodada 2

- `test_processing_service.py`: `test_a_sermon_whose_processing_failed_can_be_trimmed_again_at_once` agora é
  parametrizado com `RefusingYouTube`, `MissingWhisperX` e `BrokenCut`. O código de cada dublê está fixado em
  `test_a_failure_leaves_the_task_and_the_sermon_failed_with_its_error`.
- Produção: nenhuma mudança. `tasks/process.py` mantém `except BaseException` (linha 42). O arquivo foi tocado
  pela mutação do implementador e restaurado igual.

### Mutações do passo 4

| Mutação | Resultado |
|---|---|
| `except BaseException` → `except WordcutError` (`tasks/process.py:42`, exigida) | morta: `…trimmed_again_at_once[BrokenCut]` (1 falha, 471 passam) |
| tarefa sem `set_status failed` no erro (exigida desde a Rodada 1) | morta: os 3 casos parametrizados e a variante destacada (4 falhas) |
| `except BaseException` → `except Exception` | sobreviveu. Está fora da barra, porque 4(c) não pede `KeyboardInterrupt` (ver Observações) |

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Frases | PASS | sem mudança desde a Rodada 1; `test_sentences.py` e `test_overview.py` verdes |
| 2 — Pipeline | PASS | sem mudança desde a Rodada 1; `test_pipeline.py` e `test_pipeline_cut.py` verdes |
| 3 — Persistência | PASS | sem mudança desde a Rodada 1; `test_transcripts_repository.py` verde |
| 4 — Tipo de tarefa e serviço | PASS | O achado da Rodada 2 está fechado. `test_a_sermon_whose_processing_failed_can_be_trimmed_again_at_once[RefusingYouTube\|MissingWhisperX\|BrokenCut]` prova pelo `trim` que o `failed` fica gravado nos três casos de 4(c), sem passar pela reconciliação do `show`. A mutação `except WordcutError` fica vermelha. As mutações das Rodadas 1 e 2 seguem mortas |
| 5 — CLI | PASS | sem mudança desde a Rodada 1; `test_sermon_process_command.py` verde |
| 6 — Documentação | PASS | sem mudança desde a Rodada 2 |

### Critérios de aceite
- ✅ Processar uma pregação delimitada (Verificação 2) — mesmos testes da Rodada 1, verdes
- ✅ Processar em segundo plano (Verificação 3) — mesmos testes da Rodada 2
- ✅ Transcrição consultável (Verificação 4) — mesmos testes da Rodada 1
- ✅ Refazer o que falhou (Verificação 5) — `test_a_failed_sermon_is_processed_again_…`, `test_a_new_processing_downloads_again_…`
- ✅ Reprocessar com novas bordas (Verificação 6) — `would_discard_edits` (fora e sob a trava) e `--force`
- ✅ Pré-condições sem criar tarefa (Verificação 7) — mesmos testes da Rodada 2
- ✅ Máquina ocupada → `busy`, pregação inalterada — mesmos testes da Rodada 1
- ✅ Falha do YouTube → `failed`/`youtube_error` (Verificação 8) — `failed` gravado e provado pelo `trim`, em primeiro plano e destacado
- ✅ Falha da transcrição → `transcription_error` (Verificação 8) — pipeline, serviço e CLI. O `failed` gravado agora é provado pelo `trim` (`[MissingWhisperX]`)
- ✅ Processo morto → tarefa `failed`/`interrupted`, pregação `failed` na leitura (Verificação 9)
- ✅ `create … --process [--wait]` (Verificação 10)
- ✅ FR-002 / Verificação 1
- ✅ FR-008
- ✅ Progresso no stderr
- ✅ Quality gates (Verificação 11) — 472 testes, ruff e mypy verdes. O único aviso da suíte é de terceiros (`starlette.testclient`)

### Observações (fora da barra; não pesam no veredito)
- Não há teste do Ctrl+C (`KeyboardInterrupt`) na tarefa `process`. Por isso a mutação `except Exception` sobrevive. O `except BaseException` cobre o caso no código, mas nenhum teste o prova.
- Seguem as observações da Rodada 1: o `trim` não reconcilia; o `os.replace` roda antes da transação; os campos antigos ficam numa falha com `--force`.
- ADR-0014 continua com o status “Aceita” gravado por agente e precisa de revisão humana. Pelo SGQ, o item também precisa de revisão humana qualificada antes do merge. Este veredito não é aprovação.

### Veredito geral: PASS
O único achado da Rodada 2 está fechado: o `failed` gravado após `internal_error` tem teste, e a mutação exigida fica vermelha. Os 6 passos estão PASS, os 15 critérios estão cobertos, e a suíte e as checagens estáticas estão verdes.
