# Plan: Corrigir a grafia de uma palavra da legenda (`cut fix-word`)

**Issue**: 1.1.f.2
**Feature**: specs/1.1.f.2-cut-fix-word
**Data**: 2026-10-26

---

## Resumo

Trava de grafia pura no core (núcleo da palavra + Levenshtein + limite), tabela de correções
por corte, serviço `fix_word` e aplicação das correções na montagem (texto, prévia, `show`).
A CLI ganha `cut fix-word`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/cuts/spelling.py` — `word_core(text)`, `levenshtein(a, b)`, `spelling_limit(original)`, `check_spelling(original, proposed)` |
| Criar | `packages/core/src/wordcut/db/migrations/0008_word_fixes.sql` — tabela `word_fixes(cut_id, word_id, text, created_at, PRIMARY KEY(cut_id, word_id))`, as duas FKs com `ON DELETE CASCADE` (D6) |
| Criar | `packages/core/src/wordcut/db/word_fixes.py` — gravar, apagar e ler as correções de um corte (só das palavras pedidas, L9) |
| Alterar | `packages/core/src/wordcut/db/cuts.py` — marcar o corte editado (`edited = 1`, `updated_at`; L1) |
| Alterar | `packages/core/src/wordcut/service/cuts.py` — `fix_word(conn, cut_id, word_id, text, now)`; `list_cuts`, `show_cut` e `preview_cut` passam as correções à montagem (D3, D4) |
| Alterar | `packages/core/src/wordcut/cuts/assembly.py` — `assemble(segments, words, fixes)` com `fixes` obrigatório (D2) |
| Alterar | `apps/cli/src/wordcut_cli/cut.py` — `cut fix-word <id> <word_id> <texto>` |
| Criar | `packages/core/tests/test_spelling.py`, `test_fix_word.py`; `apps/cli/tests/test_cut_fix_word_command.py` |
| Alterar | `CHANGELOG.md`, `docs/cli.md` §8.3 e §8.5, `docs/architecture/README.md` §4 (D5) |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Núcleo | `str.lower()` (L2), remove o que não é letra, número ou hífen (Unicode), depois de NFC | Regra do protótipo (`core`, `toLowerCase`) |
| Limite | `max(1, floor(0.34 * len(núcleo original)))` | Regra do protótipo |
| Uma palavra | texto sem espaço interno (`split()` com 1 elemento); vazio ou só espaços também recusa | "Use uma palavra só" |
| Palavra do corte | `word_id` dentro de algum trecho do corte (não basta a faixa) | Correção é do corte |
| Normalização (L3) | texto recebido passa por `strip()` e NFC antes de comparar, desfazer e gravar | Entrada NFD não grava correção invisível |
| Referência da trava (L4) | sempre o original da transcrição, nunca a correção atual | Protótipo `checkWord(orig, v)`; constituição §I |
| Desfazer (FR-003, L5) | texto igual ao original apaga a correção; sem correção gravada também é sucesso | FR-003 |
| Resposta (D1) | a palavra como `cut show` a dá, mais o corte: `{"cut_id", "word_id", "text" (original), "start", "end", "corrected" (texto ou null)}` | Mesmo nome, mesmo tipo do `words[]` (QA 1.1.e.1 D3) |
| Montagem (D2) | `assemble(segments, words, fixes)`, `fixes: Mapping[int, str]` obrigatório; tempos e duração não mudam | `mypy` acusa chamador esquecido |
| Onde vale (D3) | `cut list`, `cut show` e `cut preview`; no `list`, uma consulta por pregação | Os três usam `assemble` |
| `cut show` (D4) | `words[].text` original, `words[].corrected` texto ou `null`; `text` e `segments[].text` com a correção | docs/cli.md §8.2 |
| Migração (D6) | `0008_word_fixes.sql`, `cut_id` e `word_id` com `ON DELETE CASCADE` | Reprocessar, `sermon suggest` e `sermon delete` apagam cortes e palavras |
| Editado (L1) | sucesso (gravar, trocar ou desfazer) marca `edited = 1` e `updated_at = now`; recusa não escreve | `sermon suggest` preserva os editados |
| Consulta (L9) | a montagem lê só as correções das palavras do corte (ou da pregação, no `list`) | Correção órfã não aparece |
| Trava (L10) | `cut fix-word` não é tarefa e não pega a trava | docs/cli.md §3.5, como `cut choose` |
| Erros (L6) | `spelling_too_different` com `details.distance`, `details.limit`, `details.original`; `invalid_argument` com `details.argument` = `word_id` ou `text`; nenhuma mensagem repete o texto digitado | docs/cli.md §5.3; ADR-0015 |
| Ordem das recusas (L7) | corte inexistente → palavra fora do corte → texto que não é uma palavra → desfazer → trava | Testes determinísticos |
| Saída legível (L8) | uma linha em português com o número da palavra, o original e a correção (ou que foi removida) | docs/cli.md §4.2 |

---

## Ordem de implementação

- [x] **Passo 1 — Trava pura** — `spelling.py` com tabela de casos (acento, maiúscula, troca de palavra, palavras curtas).
- [x] **Passo 2 — Persistência e serviço** — migração, repositório, `fix_word`, desfazer.
- [x] **Passo 3 — Montagem** — correções no texto, na prévia e no `cut show`.
- [x] **Passo 4 — CLI** — `cut fix-word`.
- [x] **Passo 5 — Documentação** — CHANGELOG, docs/cli.md §8.3 e §8.5, arquitetura §4.

---

## Verificação

- [x] "Jesús" → "Jesus" aceito, refletido em `cut show`, texto montado e prévia.
- [x] "não" → "sim" → `spelling_too_different` com distância e limite; nada muda.
- [x] Texto original remove a correção.
- [x] Duas palavras → `invalid_argument`; palavra fora do corte → `invalid_argument` (`word_id`); corte inexistente → `not_found`.
- [x] Correção vale só para o corte.
- [x] Quality gates limpos.
