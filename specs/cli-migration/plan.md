# Plan: Remover a CLI anterior e reescrever README e skills

**Issue**: cli-migration
**Feature**: specs/cli-migration
**Data**: 2026-10-26

---

## Resumo

Remove `wordcut_cli/legacy.py`, os comandos antigos e o código do core que só eles usam,
movendo antes o que ainda é usado; reescreve README, skills e documentos para a CLI nova.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Remover | `apps/cli/src/wordcut_cli/legacy.py`, `apps/cli/tests/test_legacy_commands.py` e o registro em `wordcut_cli/__init__.py` |
| Remover | `packages/core/src/wordcut/{short,overview,sermon,sermon_folder}.py`, `asr/remote.py`, `edit/edit_list.py` e `test_{overview,sermon,sermon_folder,remote}.py` |
| Remover (símbolos) | `edit/timeline.plan_timeline`, `edit/text.{apply_corrections,validate_corrections,_retext}`, `youtube.YouTube.download_audio`, `transcript.Transcript.{between,text}`, `vertical/camera.CameraPath.max_offset`, ramo `command is None` de `contract.execute` |
| Mover | `folder_name` (sem `reference`) → `wordcut/files.py`, com o teste de caracteres inseguros em `test_files.py`; `LEAD_IN_S`, `TAIL_S`, `SECTION_MARGIN_S`, `SYNC_SEARCH_S` → `processing/pipeline.py` |
| Migrar testes | `packages/core/tests/test_timeline.py`, `test_timeline_pauses.py` → `plan_segments`, sem perder caso; `test_text.py` só com `tidy_joins` e `capitalize`; `test_transcript.py` sem `between` |
| Alterar | `apps/cli/src/wordcut_cli/contract.py` — `command` obrigatório; formatador que quebra a descrição e mantém o epílogo, em `add_group` e `add_command` |
| Alterar | `apps/cli/tests/test_cli.py` — lista de comandos só com os novos; os 7 antigos → `invalid_argument`; ajuda dos grupos em 80 colunas |
| Reescrever | `skills/video-cortar-pregacao/SKILL.md`, `skills/video-corte-vertical/SKILL.md` — guias curtos sobre a CLI nova; `sugerir-cortes.md` e `exemplos.md` saem (critérios no pacote) |
| Reescrever | `README.md` (instalação, incluindo o venv do WhisperX; uso pela CLI nova; Compose), `CONTRIBUTING.md`, `docs/architecture/README.md` §3 e §4, `CHANGELOG.md` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

Análise de uso: `grep -rn "wordcut\.<módulo>" packages apps --include=*.py`.

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Critério de remoção | módulo sem importador fora dos próprios testes depois de remover a CLI anterior | Clean code, sem código morto |
| O que ainda é usado | movido para o módulo do domínio que o usa, com os testes acompanhando | Sem mudar comportamento |
| Skills | guias de 1 página: pré-requisitos, fluxo com os comandos novos, onde ver o resultado | FR-004 |
| `sugerir-cortes.md`/`exemplos.md` | removidos; o texto vive em `criteria/texts/` (item 8) | Uma fonte só |
| Transcrição remota | removida (`asr/remote.py`), conforme docs/cli.md §15 | Sem uso |
| L1 · código morto indireto | remover `edit_list`, `plan_timeline`, `apply_corrections`/`validate_corrections`/`_retext`, `download_audio`, `Transcript.between`; antes, `test_timeline*.py` passam a `plan_segments` sem perder caso | Recomendação do QA; morrem com `short`/`sermon` |
| L2 · ramo da CLI anterior | sai o ramo `command is None` → `args.handler` de `contract.execute`; `command` passa a obrigatório | Recomendação do QA |
| L3 · `folder_name` | vai para `files.py`; sai o parâmetro `reference` e o teste de `:` | Nenhum chamador passa `reference` |
| L4 · constantes do corte | `LEAD_IN_S`, `TAIL_S`, `SECTION_MARGIN_S`, `SYNC_SEARCH_S` vão para `processing/pipeline.py`; `RANGE_MARGIN_S` sai | Único consumidor |
| L5 · mortos herdados | remover `Transcript.text()` e `CameraPath.max_offset()` | Sem uso nem em teste |
| L6 · comandos antigos | teste parametrizado com os 7 nomes: saída 2 e `details.choices` igual aos novos | Recomendação do QA |
| L7 · README | mantém a instalação do venv do WhisperX | `LocalTranscriber` aponta para a seção Instalação |
| L8 · CHANGELOG | `### Removido`; saem as entradas de transição | Recomendação do QA |
| L9 · ajuda | um formatador que quebra a descrição e preserva o epílogo, em `add_group` e `add_command`; teste com `COLUMNS=80` | Recomendação do QA |
| L10 · mapa do passo 1 | registrado no `tdd.md` | Recomendação do QA |
| L11 · skills | avaliadas pela estrutura: pré-requisitos, fluxo e onde ver o resultado | Recomendação do QA |

---

## Ordem de implementação

- [x] **Passo 1 — Mapa de uso** — listar cada módulo do core e quem o importa; decidir remover ou mover.
- [x] **Passo 2 — Mover o que é usado** — sem mudar comportamento; testes verdes.
- [x] **Passo 3 — Remover a CLI anterior e o código morto** — com os testes.
- [x] **Passo 4 — Documentação e skills** — README, CONTRIBUTING, arquitetura, CHANGELOG, skills.
- [x] **Passo 5 — Ajuda dos grupos** — `add_group` só usa `RawDescriptionHelpFormatter` no epílogo do exemplo; a descrição volta a quebrar linha em 80 colunas (achado do QA do item 17), com teste.

---

## Verificação

- [x] `wordcut --help` só com comandos novos; `wordcut short` → `invalid_argument`.
- [x] Nenhum módulo do core sem importador fora dos próprios testes.
- [x] README e skills só citam comandos existentes.
- [x] Quality gates limpos.
