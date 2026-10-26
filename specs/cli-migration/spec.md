# Spec: Remover a CLI anterior e reescrever README e skills sobre a nova

**Issue**: cli-migration (sem rastreador; item 18 de specs/roadmap.md)
**Requisito**: docs/cli.md §15; constituição §V (sem retrocompatibilidade)
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

A CLI nova cobre o fluxo inteiro da live às exportações. Os comandos da CLI anterior
(`info`, `transcribe`, `transcribe-live`, `overview`, `cut-sermon`, `preview`, `short`), o
formato em pastas com `.json` e o código que só eles usam saem. O README e as skills do
Claude Code passam a descrever só a CLI nova, como guias curtos de uso.

---

## Cenários de aceite

**Cenário: comandos antigos não existem mais**
- **Dado** a CLI depois da migração
- **Quando** o operador roda `wordcut --help`
- **Então** só aparecem os comandos de docs/cli.md (`sermon`, `cut`, `render`, `task`,
  `status`, `settings`, `criteria`, `preset`, `member`, conforme existirem), e `wordcut short`
  dá `invalid_argument`

**Cenário: nenhum código morto**
- **Dado** o repositório depois da migração
- **Quando** se procura quem importa cada módulo do core
- **Então** todo módulo do core é usado pela camada de serviço, por outro módulo usado, ou
  pelos testes de um módulo usado; o que só a CLI anterior usava foi removido com os testes

**Cenário: documentação coerente**
- **Dado** o README e as skills
- **Quando** alguém segue os passos descritos
- **Então** só encontra comandos que existem, com o fluxo `sermon create … --process`,
  `cut list`, `cut render` e `render download`

### Casos de borda

- Constantes e funções ainda usadas por módulos novos (ex.: nome legível de arquivo, margens
  do corte) migram para o módulo certo antes de remover o antigo.
- O ambiente do WhisperX e o worker local continuam funcionando.
- A transcrição remota por SSH (`--host`) sai, conforme docs/cli.md §15.

---

## Requisitos funcionais

- **FR-001**: Os comandos da CLI anterior DEVEM ser removidos, com seus testes.
- **FR-002**: Módulos do core usados só por eles DEVEM ser removidos; o que ainda é usado DEVE
  ser movido para onde pertence, sem mudar comportamento.
- **FR-003**: README, CONTRIBUTING, docs/architecture e as skills DEVEM descrever só a CLI nova.
- **FR-004**: As skills DEVEM ser guias curtos (fluxo e comandos), sem critérios teológicos
  próprios (que estão no pacote, item 8).
- **FR-005**: Quality gates limpos.

---

## Escopo

### Componentes em escopo
- `apps/cli/src/wordcut_cli/legacy.py` e testes.
- `packages/core/src/wordcut/` — módulos usados só pela CLI anterior (provavelmente
  `short.py`, `overview.py`, `sermon_folder.py`, `sermon.py`, `asr/remote.py`), conforme a
  análise de uso.
- `README.md`, `CONTRIBUTING.md`, `docs/architecture/README.md`, `CHANGELOG.md`, `skills/`.

### Fora de escopo
- Servidor e interface (fases 2 e 3).
