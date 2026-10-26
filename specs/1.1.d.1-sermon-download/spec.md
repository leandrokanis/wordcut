# Spec: Baixar a pregação em 16:9 (`sermon download`)

**Issue**: 1.1.d.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.d-download-sermon.md §1.1.d.1; docs/cli.md §7.5
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O assistente quer o arquivo da pregação recortada em 16:9 para publicá-la inteira. A CLI
copia o vídeo processado para um destino escolhido, ou para a pasta atual com um nome
legível, e devolve o caminho.

---

## Cenários de aceite

**Cenário: baixar com nome legível**
- **Dado** uma pregação `processed` de 2026-10-18 intitulada "Culto de domingo"
- **Quando** o operador roda `wordcut sermon download <id> --json` numa pasta
- **Então** o arquivo `2026-10-18 - Culto de domingo.mp4` aparece na pasta atual, idêntico ao
  vídeo processado, e o JSON traz `path` absoluto e `bytes`

**Cenário: destino escolhido**
- **Dado** uma pregação processada
- **Quando** o operador roda `sermon download <id> -o /tmp/x/pregacao.mp4`
- **Então** o arquivo é gravado nesse caminho (criando a pasta, se preciso)

**Cenário: pregação não processada**
- **Dado** uma pregação `created`, `trimmed`, `processing` ou `failed`
- **Quando** o operador tenta baixar
- **Então** falha com `sermon_not_processed` (saída 5)

### Casos de borda

- `-o` apontando para uma pasta existente → grava dentro dela com o nome legível.
- Arquivo de destino já existe → não sobrescreve; acrescenta ` (2)`, ` (3)`… ao nome.
- Título com caracteres proibidos em nome de arquivo → removidos (regra de `folder_name`).
- ID inexistente → `not_found`.
- Vídeo processado ausente no disco → `internal_error` com mensagem clara, sem caminho
  interno além do da pregação.

---

## Requisitos funcionais

- **FR-001**: `sermon download <id> [-o caminho]` DEVE copiar o vídeo 16:9 da pregação
  processada para o destino e devolver `{path, bytes}`.
- **FR-002**: Sem `-o`, o destino DEVE ser a pasta atual, com nome `AAAA-MM-DD - Título.mp4`.
- **FR-003**: Destino existente NÃO DEVE ser sobrescrito.
- **FR-004**: Pregação não processada DEVE falhar com `sermon_not_processed`.
- **FR-005**: A cópia NÃO DEVE pegar a trava de processamento.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/service/sermons.py` — `sermon_video(conn, home, id)` e a regra de nome.
- `apps/cli/src/wordcut_cli/sermon.py` — `download`.
- Testes com um arquivo de vídeo falso (bytes quaisquer).

### Fora de escopo
- Download pela web (API e interface, fases 2 e 3).

---

## Pressupostos

- O nome legível reaproveita `sermon_folder.folder_name` (sem referência bíblica).
