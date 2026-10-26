# Spec: Processar a pregação (`sermon process`)

**Issue**: 1.1.c.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.c-process-sermon.md §1.1.c.1–1.1.c.3;
1.1.b §1.1.b.3; docs/cli.md §6, §7.2 (`--transcript`), §7.4; constituição §IV
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

Com as bordas definidas, o assistente processa a pregação: o sistema baixa só a faixa
marcada, transcreve com tempo por palavra, corta a pregação em 16:9 com fades e guarda as
palavras e as frases no banco. O processamento é uma tarefa pesada, sob a trava, que pode
ser acompanhada, refeita se falhar e repetida (com `--force`) quando as bordas mudam.

---

## Cenários de aceite

**Cenário: processar uma pregação delimitada**
- **Dado** uma pregação `trimmed` de live terminada e a máquina livre
- **Quando** o operador roda `wordcut sermon process <id> --wait`
- **Então** o progresso das etapas (baixar, transcrever, cortar) aparece no stderr, a pregação
  termina `processed` com o vídeo 16:9, as palavras e as frases gravadas, e a saída é 0

**Cenário: processar em segundo plano**
- **Dado** uma pregação `trimmed`
- **Quando** o operador roda `sermon process <id>` sem `--wait`
- **Então** recebe a tarefa `running` na hora e a pregação fica `processing` até a tarefa
  terminar

**Cenário: transcrição consultável**
- **Dado** uma pregação processada
- **Quando** o operador roda `sermon show <id> --transcript --json`
- **Então** recebe as frases em ordem, cada uma com ID, início, fim, texto e IDs da primeira e
  da última palavra, em tempo da pregação

**Cenário: refazer o que falhou (1.1.c.3)**
- **Dado** uma pregação `failed`
- **Quando** o operador roda `sermon process <id>` de novo
- **Então** o processamento recomeça e pode terminar `processed`

**Cenário: reprocessar com novas bordas (1.1.b.3)**
- **Dado** uma pregação `processed` com bordas alteradas
- **Quando** o operador roda `sermon process <id>` sem `--force`
- **Então** falha com `would_discard_edits` (saída 5); com `--force`, refaz tudo e substitui
  palavras, frases e cortes

**Cenário: pré-condições**
- **Dado** uma pregação sem bordas, ou de live não terminada
- **Quando** o operador processa
- **Então** falha com `sermon_not_trimmed` ou `live_not_finished` (saída 5), sem criar tarefa

### Casos de borda

- Máquina ocupada → `busy` (saída 4), pregação inalterada.
- Falha do YouTube na etapa de download → tarefa `failed` com `youtube_error`, pregação
  `failed`.
- Falha da transcrição (sem GPU, ambiente ausente) → tarefa e pregação `failed`, com mensagem
  clara.
- Processo morto no meio → tarefa `interrupted` e pregação `failed` na próxima leitura.
- `sermon create … --start … --end … --process [--wait]` faz tudo num comando.

---

## Requisitos funcionais

- **FR-001**: `sermon process` DEVE ser uma tarefa do tipo `process`, sob a trava, com
  `--wait` e saída de tarefa (item 4).
- **FR-002**: Só a faixa delimitada (com margem pequena) DEVE ser baixada e transcrita.
- **FR-003**: O vídeo da pregação DEVE começar pouco antes da primeira palavra e terminar
  pouco depois da última dentro das bordas, com fades, em 16:9.
- **FR-004**: As palavras DEVEM ser gravadas com ID estável, texto, início, fim, confiança e
  se o tempo foi estimado, em tempo da pregação; as frases DEVEM ser gravadas com ID e as
  palavras de início e fim.
- **FR-005**: A pregação DEVE passar a `processing` no início e a `processed` ou `failed` no
  fim; `failed` DEVE ser reprocessável.
- **FR-006**: Reprocessar uma pregação `processed` DEVE exigir `--force` e substituir palavras,
  frases e cortes.
- **FR-007**: `sermon show --transcript` DEVE listar as frases como em FR-004.
- **FR-008**: As mídias DEVEM ficar em `WORDCUT_HOME`, numa pasta por pregação.

---

## Entidades e dados

- **Palavra (`word`)**: id, sermon_id, position, text, start, end, score, estimated.
- **Frase (`sentence`)**: id, sermon_id, position, first_word_id, last_word_id, start, end, text.
- **Pregação**: ganha `video_path`, `sermon_start`/`sermon_end` reais na live (depois do
  ajuste às palavras) e `processed_at`.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — pipeline de processamento (download da faixa, sincronia,
  transcrição, corte), tipo de tarefa `process`, migração, serviço.
- `apps/cli/src/wordcut_cli/sermon.py` — `process`, `--process` no `create`, `--transcript`.
- Testes com YouTube, transcritor e ffmpeg pesados como dublês.

### Fora de escopo
- Sugestão de cortes pelo LLM ao fim (item 9).
- GPU no contêiner (pendência do administrador).

### Integrações externas
- YouTube (`yt-dlp`) e WhisperX (dublês nos testes).

---

## Pressupostos

- A transcrição usa o `Transcriber` existente (`LocalTranscriber` com o ambiente do WhisperX);
  o modelo vem da configuração quando o item 7 existir, e até lá do padrão `large-v3`.
- O corte com fades e a sincronia reaproveitam `media.cut_with_fades` e `sync.locate_clip`.
