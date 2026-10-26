# Plan: Baixar a pregação em 16:9 (`sermon download`)

**Issue**: 1.1.d.1
**Feature**: specs/1.1.d.1-sermon-download
**Data**: 2026-10-26

---

## Resumo

O serviço de pregações ganha a localização do vídeo processado e a regra do nome legível; a
CLI ganha `sermon download`, que copia o arquivo sem sobrescrever e devolve o destino.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core/src/wordcut/service/sermons.py` — `sermon_video(conn, home, id)`.
- `packages/core/src/wordcut/files.py` — cópia sem sobrescrever (reaproveitável pelo `render download`).
- `apps/cli/src/wordcut_cli/sermon.py` — `download`.

---

## Contexto de código

| Situação | Path |
|---|---|
| Alterar | `packages/core/src/wordcut/service/sermons.py` — `sermon_video(conn, home, sermon_id) -> SermonVideo(path, suggested_name)`; `sermon_not_processed` |
| Criar | `packages/core/src/wordcut/files.py` — `copy_without_overwrite(source, destination: str \| PathLike, suggested_name) -> Path` (pasta existente ou caminho terminado em separador → `suggested_name` dentro; existente → ` (2)`, ` (3)`…; cria pastas; sem hard link → queda para `open(final, "x")`) |
| Alterar | `packages/core/src/wordcut/errors.py` — `sermon_not_processed` se ainda não existir |
| Alterar | `apps/cli/src/wordcut_cli/sermon.py` — `sermon download <id> [-o caminho]` |
| Criar | `packages/core/tests/test_files.py`, `packages/core/tests/test_sermon_video.py`, `apps/cli/tests/test_sermon_download_command.py` |
| Alterar | `CHANGELOG.md` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Onde está o vídeo | coluna `video_path` da pregação (relativa a `WORDCUT_HOME`), preenchida pelo item 5; testes a preenchem por SQL ou pelo repositório | Mídia no disco, caminho no banco (constituição) |
| Nome legível | `folder_name(service_date, title) + ".mp4"` | Regra já existente e testada |
| Cópia | `shutil.copyfile` para um temporário na pasta de destino + troca final por `os.link(temp, final)` + `os.unlink(temp)`; `link` falha se o destino existir e então se tenta o próximo sufixo; nunca `os.replace`. Temporário apagado também na falha (D6) | Nunca deixa arquivo pela metade com o nome final nem sobrescreve destino que surja entre checagem e troca (decisão do orquestrador, rodada 1) |
| Queda sem hard link | `os.link` com `OSError` de `errno` `EPERM`, `ENOTSUP`/`EOPNOTSUPP` ou `EXDEV` → `open(final, "x")` + cópia dos bytes do temporário; `FileExistsError` tenta o próximo sufixo; falha no meio apaga o nome final criado ali; temporário apagado no fim; outro `OSError` propaga | Sistemas de arquivos sem hard link (FAT, compartilhamentos de rede) e destino em outro dispositivo; mantém a regra de nunca sobrescrever (decisão do orquestrador, rodada 2). Nesse caminho o nome final existe durante a cópia |
| Sufixo (D1) | ` (2)`, ` (3)`… antes da extensão: `2026-10-18 - Culto de domingo (2).mp4` | qa.md D1; decisão do orquestrador |
| `-o` existente (D2) | `-o arquivo` que já existe também recebe o sufixo | FR-003 sem exceção; qa.md D2 |
| `-o` pasta (D3) | pasta existente ou caminho terminado em separador (`-o saida/`) = pasta, criada na hora; nome legível dentro; caminho inexistente sem separador = arquivo | qa.md D3 |
| `video_path` nulo (D4) | pregação `processed` com `video_path` nulo ou vídeo ausente → `internal_error` "vídeo da pregação N não encontrado", `details: {"sermon_id": N}`, sem caminho de `WORDCUT_HOME` | qa.md D4 |
| Saída em texto (D5) | o caminho absoluto de destino | docs/cli.md §7.5; qa.md D5 |
| Trava (FR-005) | o download não toma a trava; teste explícito com `lock_owner` segurando a trava | Decisão do orquestrador |
| Assinatura | `sermon_video(conn, home, id)`; spec.md alinhado | `home` resolve o `video_path` relativo |
| Destino relativo | resolvido contra a pasta atual; resposta com caminho absoluto | Agentes encadeiam pelo `path` |
| Vídeo ausente no disco | `internal_error` com mensagem "vídeo da pregação N não encontrado" | Estado inconsistente, não erro do usuário |

Se o item 5 ainda não tiver criado a coluna `video_path`, este item cria a migração com ela.

---

## Ordem de implementação

- [x] **Passo 1 — Cópia segura** — `files.copy_without_overwrite` com pasta, sufixo e temporário.
- [x] **Passo 2 — Serviço** — `sermon_video` com `sermon_not_processed`, `not_found` e vídeo ausente.
- [x] **Passo 3 — CLI** — `sermon download` com `-o`, texto e JSON (`path`, `bytes`).
- [x] **Passo 4 — Documentação** — CHANGELOG.

---

## Fora de escopo

- Download pela web.

---

## Verificação

- [x] Pregação `processed` → `sermon download <id> --json` na pasta atual cria
  `AAAA-MM-DD - Título.mp4` idêntico e devolve `path` absoluto e `bytes`.
- [x] `-o arquivo` grava no caminho, criando pastas; `-o pasta` grava dentro com o nome legível.
- [x] Destino existente → ` (2)` no nome, original intacto.
- [x] Pregação não processada → `sermon_not_processed` (saída 5); ID inexistente → `not_found`.
- [x] Quality gates limpos.
