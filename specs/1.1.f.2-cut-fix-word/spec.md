# Spec: Corrigir a grafia de uma palavra da legenda (`cut fix-word`)

**Issue**: 1.1.f.2 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.f-adjust-form.md §1.1.f.2, §1.1.f.3;
docs/cli.md §8.5; constituição §I
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O assistente corrige a grafia de uma palavra da legenda de um corte ("Jesús" → "Jesus") sem
mudar o que foi dito. Uma trava por distância de edição aceita só correções parecidas com a
original e bloqueia a troca de uma palavra por outra ("não" → "sim").

---

## Cenários de aceite

**Cenário: correção aceita**
- **Dado** um corte com a palavra 1204 "Jesús"
- **Quando** o assistente roda `wordcut cut fix-word <id> 1204 Jesus --json`
- **Então** a correção fica gravada no corte, aparece em `cut show` (`corrected`) e no texto
  montado, e a saída é 0

**Cenário: troca bloqueada (1.1.f.3)**
- **Dado** a palavra "não"
- **Quando** o assistente tenta corrigir para "sim"
- **Então** falha com `spelling_too_different` (saída 5), com `details.distance` e
  `details.limit`, e nada muda

**Cenário: desfazer**
- **Dado** uma palavra corrigida
- **Quando** o assistente corrige para o texto original
- **Então** a correção é removida

### Casos de borda

- Mais de uma palavra no texto → `invalid_argument`.
- Palavra fora do corte → `invalid_argument` com `details.argument = "word_id"`.
- Corte inexistente → `not_found`.
- Diferença só de maiúsculas, acentos ou pontuação conta pouco (comparação no núcleo da
  palavra: minúsculas, só letras, números e hífen).
- A correção vale só para aquele corte.

---

## Requisitos funcionais

- **FR-001**: `cut fix-word <id> <word_id> <texto>` DEVE gravar a correção no corte.
- **FR-002**: A correção DEVE ser aceita só se a distância de Levenshtein entre os núcleos for
  ≤ `max(1, floor(0,34 × tamanho do núcleo original))`.
- **FR-003**: Texto igual ao original DEVE remover a correção.
- **FR-004**: Texto montado, prévia e `cut show` DEVEM refletir a correção.

---

## Entidades e dados

- **Correção (`word_fix`)**: cut_id, word_id, text, created_at (única por corte e palavra).

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — trava de grafia, migração, serviço.
- `apps/cli/src/wordcut_cli/cut.py` — `fix-word`.

### Fora de escopo
- Edição por clique duplo na prévia (fase 3).

---

## Pressupostos

- A regra do limite é a do protótipo (`checkWord`): núcleo em minúsculas com letras, números e
  hífen; limite `max(1, floor(0,34 × len))`.
- Na CLI a trava vale sempre, mesmo agindo como administrador: mudar conteúdo é pelos comandos
  de conteúdo (`cut segments`), não pela grafia.
