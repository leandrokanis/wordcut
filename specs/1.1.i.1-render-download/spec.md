# Spec: Consultar e baixar exportações (`render list/show/download`)

**Issue**: 1.1.i.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.i-download-cuts.md §1.1.i.1; docs/cli.md §9
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O assistente consulta o histórico de exportações de um corte e baixa o vídeo de uma delas
para publicar. Cada corte guarda as próprias exportações; não há lista separada de vídeos.

---

## Cenários de aceite

**Cenário: histórico do corte**
- **Dado** um corte com duas exportações
- **Quando** o assistente roda `wordcut render list --cut <id> --json`
- **Então** recebe `{"items": [...]}` com as duas, da mais recente para a mais antiga, cada uma
  com `id`, `cut_id`, `duration`, `created_at` e o resumo das opções

**Cenário: detalhar**
- **Dado** uma exportação
- **Quando** o assistente roda `render show <id> --json`
- **Então** recebe `{id, cut_id, path, duration, created_at, options}` com `path` absoluto local

**Cenário: baixar**
- **Dado** uma exportação do corte "Graça que alcança" da pregação de 2026-10-18
- **Quando** o assistente roda `render download <id>` numa pasta
- **Então** o arquivo `2026-10-18 - Graça que alcança.mp4` aparece ali, idêntico, sem
  sobrescrever, e a saída traz o caminho

### Casos de borda

- Corte ou exportação inexistente → `not_found`.
- Arquivo da exportação ausente no disco → `internal_error` sem caminho interno.
- `-o` com as mesmas regras do `sermon download` (pasta, sufixo ` (2)`).
- Nenhum comando pega a trava.

---

## Requisitos funcionais

- **FR-001**: `render list --cut <id>` DEVE listar as exportações do corte, mais recente primeiro.
- **FR-002**: `render show <id>` DEVE devolver a exportação com caminho absoluto.
- **FR-003**: `render download <id> [-o caminho]` DEVE copiar sem sobrescrever, com nome
  `AAAA-MM-DD - Título do corte.mp4`.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/service/renders.py`.
- `apps/cli/src/wordcut_cli/render.py`.

### Fora de escopo
- Apagar exportações (1.2.b, onda 6).

---

## Pressupostos

- Reaproveita `files.copy_without_overwrite` do item 6.
