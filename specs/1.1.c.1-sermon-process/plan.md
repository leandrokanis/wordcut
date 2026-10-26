# Plan: Processar a pregação (`sermon process`)

**Issue**: 1.1.c.1
**Feature**: specs/1.1.c.1-sermon-process
**Data**: 2026-10-26

---

## Resumo

Novo tipo de tarefa `process` (com trava) que roda o pipeline: baixar só a faixa (vídeo com
margem e uma janela curta de áudio para sincronia), localizar o vídeo na live, transcrever,
ajustar as bordas às palavras, cortar com fades e gravar palavras e frases no SQLite. O
pipeline recebe as dependências pesadas por uma interface (`ProcessingGateways`), para os
testes usarem dublês. A CLI ganha `sermon process`, `create --process` e `show --transcript`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core/src/wordcut/processing/` — pipeline e dependências.
- `packages/core/src/wordcut/` — migração (palavras, frases, colunas da pregação), repositório,
  tipo de tarefa, serviço, `youtube.py` (áudio de uma janela).
- `apps/cli/src/wordcut_cli/sermon.py`.

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/db/migrations/0004_transcripts.sql` — tabelas `words` e `sentences`; colunas `sermon_start`, `sermon_end`, `video_path`, `processed_at` em `sermons` |
| Criar | `packages/core/src/wordcut/db/transcripts.py` — gravar e ler palavras e frases de uma pregação; apagar as de uma pregação |
| Criar | `packages/core/src/wordcut/processing/__init__.py` — `ProcessingGateways` (protocolo: `download_section`, `download_audio_window`, `locate`, `transcribe`, `cut`) e `default_gateways()` |
| Criar | `packages/core/src/wordcut/processing/pipeline.py` — `process(gateways, workdir, url, live_start, live_end, progress) -> Processed(words, sentences, sermon_start, sermon_end, video)` |
| Criar | `packages/core/src/wordcut/processing/sentences.py` — frases a partir das palavras (fim de frase, pausa > 1,5 s, 25 palavras), mesma regra de `overview.py`, que passa a reaproveitá-la |
| Criar | `packages/core/src/wordcut/tasks/process.py` — tipo `process`: marca `processing`, roda o pipeline, grava, marca `processed` ou `failed`; incluído em `BUILTIN_KIND_MODULES` |
| Criar | `packages/core/src/wordcut/service/processing.py` — `start_processing(home, sermon_id, *, force, detach, on_progress)`: pré-condições e `tasks.execution.start` |
| Alterar | `packages/core/src/wordcut/service/sermons.py` — `last_task` real e reconciliação (`processing` com última tarefa `failed` → `failed`); `show_sermon(..., transcript=True)` |
| Alterar | `packages/core/src/wordcut/youtube.py` — `download_audio_window(url, start, end, output)` (só áudio, `--download-sections`) |
| Alterar | `packages/core/src/wordcut/overview.py` — usa `processing/sentences.py` |
| Alterar | `apps/cli/src/wordcut_cli/sermon.py` — `sermon process <id> [--force] [--wait]`; `create … --process [--wait]`; `show --transcript` |
| Criar | `packages/core/tests/test_sentences.py`, `test_pipeline.py`, `test_process_task.py`, `test_processing_service.py`; `apps/cli/tests/test_sermon_process_command.py` |
| Alterar | `docs/architecture/README.md` (§4, §5.1), `CHANGELOG.md` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

Os testes usam dublês de `ProcessingGateways`; um teste de integração do corte usa o
`ffmpeg` real num clipe sintético de 3 s gerado por `lavfi`. Nada de YouTube, WhisperX nem
vídeo real.

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| O que baixar | vídeo da faixa `[live_start − 30 s, live_end + 30 s]` e áudio de uma janela `[live_start − 50 s, live_start + 40 s]` | FR-002: só a faixa; o áudio curto e exato serve de régua para a sincronia |
| Sincronia | `sync.locate_clip(janela de áudio, vídeo da faixa, expected_start, search=20)` → início real do vídeo na live | O `--download-sections` do vídeo começa num keyframe, não no ponto pedido (ver docstring de `download_section`) |
| Transcrição | áudio 16 kHz do vídeo da faixa inteira; tempos da faixa convertidos para a live | Uma transcrição só, com margem para achar a primeira e a última palavra |
| Ajuste às palavras | primeira palavra que começa em `≥ live_start` e última que termina em `≤ live_end`; corte em `[primeira − 0,3 s, última + 1,5 s]` (`LEAD_IN_S`, `TAIL_S` de `sermon.py`) | Regra já usada no corte atual |
| Tempos gravados | palavras e frases em tempo da pregação (t = 0 em `sermon_start`); `sermon_start`/`sermon_end` em tempo da live | docs/cli.md §3.4 |
| Frases | módulo próprio reaproveitado por `overview.py`; IDs estáveis (linha no banco) e `position` | FR-004; o LLM recebe frases numeradas (item 9) |
| Mídias | `WORDCUT_HOME/media/sermons/<id>/sermon.mp4`; intermediários em `…/<id>/work/`, apagados no sucesso | FR-008; disco |
| Estado da pregação | a tarefa marca `processing` ao começar; `processed` no sucesso; `failed` em erro; morte do processo → `failed` na leitura, pela última tarefa | FR-005; sem daemon |
| Pré-condições | antes da tarefa: `not_found`, `sermon_not_trimmed`, `live_not_finished`, `would_discard_edits` (estado `processed` sem `--force`); `processing` → `busy` | Falha rápida, sem criar tarefa |
| `--force` | apaga palavras, frases (e cortes, quando existirem) no início da tarefa | FR-006 |
| Dependências no processo destacado | `default_gateways()` monta YouTube, `LocalTranscriber` e `media` reais; testes de pipeline injetam dublês direto; testes do tipo de tarefa rodam em primeiro plano com `monkeypatch` de `default_gateways` | O filho não recebe objetos Python |
| Modelo do WhisperX | `large-v3` até o item 7 ligar a configuração | Pressuposto da spec |
| Erros do pipeline | `YouTubeError` → `youtube_error`; falha da transcrição → `transcription_error` (saída 6, novo código); outras → `internal_error` | Mensagem clara, contrato estável |
| Progresso | baixar 0–0,3; sincronizar 0,3–0,35; transcrever 0,35–0,85; cortar 0,85–0,95; gravar 0,95–1 | Linha `[process] …` legível |
| L1 — Filho destacado nos testes | testes sem `--wait` trocam o `Popen` de `tasks.execution` por um filho inofensivo; fixture autouse (raiz) faz `processing.default_gateways` falhar se chamada | `monkeypatch` não atravessa processo; nunca alcançar YouTube/WhisperX |
| L2 — `processing` no lançamento | o serviço grava `processing` dentro da trava, antes de criar a tarefa (gancho `admit` de `tasks.execution.start`); a tarefa só confirma o estado | Sem corrida logo após o retorno sem `--wait` |
| L3 — Restos de execução anterior | `work/` limpo no início; o corte vai para `work/sermon.mp4` e substitui `sermon.mp4` com `os.replace` só no sucesso | `cut_with_fades` não sobrescreve; `yt-dlp` reaproveita arquivo existente |
| L4 — Base de tempo e limites | `expected_start` relativo à janela; início real = início da janela + offset; inícios limitados a 0 e fins à duração da live, quando conhecida | `live_start < 50` e faixa no fim da live |
| L5 — Palavras gravadas | só da primeira à última palavra dentro das bordas | A margem de 0,3 s não traz palavra de fora |
| L6 — Sem palavras / corte fora do vídeo | novo código `processing_error` (saída 1, docs/cli.md §5.3), nada gravado | Erro claro e estável |
| L7 — Resultado de `--wait` | a pregação no formato do `show`, com `sermon_start`, `sermon_end` e `processed_at` (§7.2); o resultado gravado na tarefa é o mesmo objeto sem `last_task` | §6.3 |
| L8 — `--transcript` | acrescenta `sentences: [{id, start, end, text, first_word_id, last_word_id}]` (§7.2) | FR-007 |
| L9 — Reconciliação na leitura | `show` e `list` recebem `home` e reconciliam: tarefa órfã → `failed`/`interrupted`; pregação `processing` sem trava da pregação e sem tarefa `process` viva → `failed`; `last_task` no formato de `task show` | FR-005 sem daemon |
| L10 — Revalidação sob a trava | o `admit` do serviço revalida `would_discard_edits` e `sermon_not_trimmed` sob a trava, antes de criar a tarefa; a tarefa não repete a checagem (decisão do orquestrador na rodada 2, substitui "a tarefa revalida ao começar") | Pré-condição fora da trava pode envelhecer; a trava é da tarefa do `admit` até o fim |
| L11 — `live_finished` desatualizado | com `live_finished` falso, o `process` consulta o YouTube uma vez (`LiveSource`, dublê nos testes) e atualiza a pregação antes de recusar com `live_not_finished` | Live criada no ar continua processável |
| L12 — `create --process` | sem bordas → `invalid_argument` sem criar nada; falha de pré-condição mantém a pregação criada; pregação `processed` → `would_discard_edits`; `--wait` sem `--process` → `invalid_argument` | docs/cli.md §7.1 |
| L13 — Documentos | segue docs/cli.md §6.5 (tarefa `failed` com `interrupted`); §5.1 inclui a transcrição na saída 6; §7.4 e diagrama §5.1 marcam a sugestão do LLM como item 9 | Coerência dos contratos |
| L14 — IDs e atomicidade | `words` e `sentences` com `AUTOINCREMENT`; palavras, frases e estado `processed` numa única transação | §3.3; sem transcrição parcial |
| Mídia gravada | `video_path` relativo à pasta de dados (`media/sermons/<id>/sermon.mp4`) | A pasta de dados muda de lugar entre host e contêiner |
| Duração da faixa | `ProcessingGateways.duration(media)` para conferir que o corte cabe no vídeo baixado | L6 |

---

## Ordem de implementação

- [x] **Passo 1 — Frases** — `processing/sentences.py` com a regra de `overview.py`; `overview`
  passa a usá-lo sem mudar a saída.
- [x] **Passo 2 — Pipeline** — `ProcessingGateways`, `download_audio_window`, `pipeline.process`
  com sincronia, transcrição, ajuste às palavras e corte; testes com dublês e um de integração
  do corte com `ffmpeg` real em clipe sintético.
- [x] **Passo 3 — Persistência** — migração 0004, `db/transcripts.py`.
- [x] **Passo 4 — Tipo de tarefa e serviço** — `tasks/process.py`, `service/processing.py`,
  estados, `--force`, reconciliação e `last_task` no `show`, `transcription_error`.
- [x] **Passo 5 — CLI** — `sermon process`, `create --process`, `show --transcript`.
- [x] **Passo 6 — Documentação** — arquitetura (§4, §5.1), docs/cli.md (§5.3 com
  `transcription_error`), CHANGELOG.

---

## Riscos

- **Sincronia falhar em áudio ruim**: `locate_clip` devolve o melhor casamento; se o ajuste
  levar o corte para fora do vídeo baixado, a tarefa falha com mensagem clara.
- **Imagem Docker sem WhisperX/GPU**: o processamento real roda pela CLI no host até o NVIDIA
  Container Toolkit existir (pendência do administrador).

---

## Fora de escopo

- Sugestão de cortes pelo LLM (item 9).
- Modelo do WhisperX configurável (item 7).

---

## Verificação

- [x] Pipeline com dublês: baixa só a faixa e a janela, sincroniza, transcreve, ajusta às
  palavras e corta com os tempos esperados.
- [x] `sermon process <id> --wait` (dublês, primeiro plano) → progresso no stderr, pregação
  `processed`, palavras e frases gravadas em tempo da pregação, vídeo no lugar, saída 0.
- [x] Sem `--wait` → tarefa `running` na hora; pregação `processing` enquanto roda.
- [x] `sermon show <id> --transcript --json` → frases com ID, início, fim, texto, primeira e
  última palavra.
- [x] Pregação `failed` → `process` de novo funciona.
- [x] `processed` sem `--force` → `would_discard_edits`; com `--force` substitui palavras e frases.
- [x] Sem bordas → `sermon_not_trimmed`; live no ar → `live_not_finished`; máquina ocupada →
  `busy`; sem criar tarefa.
- [x] Falha do YouTube → tarefa `failed`/`youtube_error`, pregação `failed`; falha da
  transcrição → `transcription_error`.
- [x] Processo morto → pregação `failed` na leitura.
- [x] `create … --start … --end … --process --wait` faz tudo.
- [x] Quality gates limpos.
