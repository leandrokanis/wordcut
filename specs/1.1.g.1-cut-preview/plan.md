# Plan: Sequência da prévia de um corte (`cut preview`)

**Issue**: 1.1.g.1
**Feature**: specs/1.1.g.1-cut-preview
**Data**: 2026-10-26

---

## Resumo

`preview_cut` no serviço de cortes reaproveita a montagem do item 11 (trechos com tempos e
texto) e marca os trechos fora de ordem; a CLI ganha `cut preview`. O texto sai sem correção
de grafia: a montagem ainda não aplica correção, e o item 13 (1.1.f.2) estende a prévia (e o
`cut show`) para usá-la.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Alterar | `packages/core/src/wordcut/service/cuts.py` — `preview_cut(conn, cut_id)` |
| Alterar | `packages/core/src/wordcut/cuts/assembly.py` — `AssembledCut.out_of_order` (um por trecho: começa antes do fim do anterior); o `AssembledSegment` não conhece o vizinho |
| Alterar | `apps/cli/src/wordcut_cli/cut.py` — `cut preview` |
| Criar | `packages/core/tests/test_cut_preview.py`, `apps/cli/tests/test_cut_preview_command.py` |
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
| Fora de ordem | `segment.start < previous.end`, comparando só com o trecho imediatamente anterior; o primeiro nunca é marcado | Critério novo, alinhado à spec ("o trecho que volta no tempo"); difere do `EditList.reordered()` antigo, que marca o trecho antes de um trecho mais cedo e compara inícios (QA D2/L3) |
| Onde mora a marca | `AssembledCut.out_of_order -> tuple[bool, ...]`, um por trecho, testada por `preview_cut` | O trecho isolado não conhece o anterior; só o corte tem a sequência (QA D1/L1) |
| Tempos | `AssembledSegment.start/end` (início da primeira palavra e fim da última), já em tempo da pregação | docs/cli.md §3.4 (QA D4) |
| Texto | `AssembledSegment.text`, palavras unidas por espaço, **sem** correção de grafia; nenhum gancho de correção criado aqui | Não há correção no baseline; o item 13 (1.1.f.2) estende a prévia e o `show` (QA D3/L6) |
| Duração | `AssembledCut.duration` (soma das faixas, ao ms) | Igual ao `cut show` (QA D5) |
| Inexistente | `_existing` do serviço: `not_found` com `details.cut_id` | Igual ao `cut show` (QA D6) |
| Chaves do JSON | só `cut_id`, `duration`, `segments[start, end, text, out_of_order]` | As da spec; sem extras (QA L5) |
| Texto legível | uma linha por trecho com os dois tempos em `format_timestamp`, o texto e `↑` só no fora de ordem | Spec; §4.2 deixa o espaçamento livre (QA L8) |
| Corte sem trechos | sem teste; `AssembledCut.out_of_order` devolve `()` e a prévia sai com `segments: []` | `cuts.insert_many` sempre grava trechos (QA L9) |
| Testes | arquivos novos `test_cut_preview.py` (core) e `test_cut_preview_command.py` (cli); o cenário usa três trechos | Com dois trechos as mutações do critério antigo e do vizinho sobrevivem (QA D7/L7) |
| Documentação | docs/cli.md §8.3 ganha o formato JSON, a regra da marca com exemplo e a duração | QA L4 |
| Trava | nenhuma leitura de trava | §IV |

---

## Ordem de implementação

- [x] **Passo 1 — Serviço** — `preview_cut` com `out_of_order` e texto (sem correção até o item 13).
- [x] **Passo 2 — CLI** — `cut preview` com texto (`↑`) e JSON.
- [x] **Passo 3 — Documentação** — CHANGELOG; docs/cli.md §8.3 com formato, regra da marca (com exemplo) e duração.

---

## Verificação

- [x] Corte com trecho fora de ordem → JSON na ordem de montagem com `out_of_order` certo e duração.
- [x] Com `lock_owner` segurando a trava → sai normalmente.
- [x] Inexistente → `not_found`; texto legível com `↑`.
- [x] Quality gates limpos.
