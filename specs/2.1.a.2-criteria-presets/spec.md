# Spec: Critérios fixos no código e presets (`criteria list`, `preset`)

**Issue**: 2.1.a.2 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/2.1.a-settings.md §2.1.a.2, §2.1.a.3; docs/cli.md
§11.2, §11.3; constituição §I; ADR-0010
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O administrador calibra as sugestões sem reescrever os critérios teológicos: escolhe, por
preset, o nível de rigidez (brando, moderado, rigoroso) de cada filtro e valor, os números
do formato, as opções de edição e instruções adicionais. Os textos dos critérios ficam no
código, revisados por commit, e nunca aparecem para edição.

---

## Cenários de aceite

**Cenário: listar critérios**
- **Dado** a instalação
- **Quando** o administrador roda `wordcut criteria list --json`
- **Então** recebe os 8 filtros e os 3 valores, cada um com `id`, `name`, `type`
  (`filter` | `value`) e `default_level`, sem nenhum texto de prompt

**Cenário: preset padrão de fábrica**
- **Dado** uma instalação nova
- **Quando** o administrador roda `preset list --json`
- **Então** existe um preset "Padrão", marcado como padrão, com os níveis padrão dos
  critérios, duração permitida 40–75 s, ideal 55–65 s, reordenar ligado, palavras protegidas
  "não, mas, se" e instruções vazias

**Cenário: criar e editar**
- **Dado** o preset padrão
- **Quando** o administrador roda `preset create "Estudo bíblico"` e depois
  `preset update <id> --level allegory=strict --duration-ideal 60-75 --instructions-file -`
- **Então** o preset novo começa como cópia do padrão e passa a ter os valores alterados

**Cenário: escolher o padrão e proteger o padrão**
- **Dado** dois presets
- **Quando** o administrador roda `preset set-default <id>` e tenta `preset delete` do padrão
- **Então** o padrão muda e apagar o padrão falha com `default_preset` (saída 5)

**Cenário: critério novo ou removido no código**
- **Dado** um preset gravado antes de um critério novo existir
- **Quando** o preset é lido
- **Então** o critério novo aparece com o nível padrão dele, e um critério removido do código
  é ignorado

### Casos de borda

- `--level` com critério inexistente ou nível inválido → `invalid_argument`.
- Durações com mínimo maior que máximo, ou ideal fora do permitido → `invalid_argument`.
- Nome de preset repetido → `invalid_argument`.
- Instruções adicionais lidas de arquivo ou stdin, até um limite de tamanho.
- Os textos dos critérios são validados ao carregar: todo critério tem os três níveis; falta
  de nível é erro de programação, pego por teste.

---

## Requisitos funcionais

- **FR-001**: Os critérios (prompt base e um trecho por critério e nível) DEVEM ficar em
  arquivos do pacote core, um por critério, com conteúdo inicial tirado de
  `skills/video-corte-vertical/sugerir-cortes.md`, sem exemplos de calibração.
- **FR-002**: `criteria list` DEVE listar id, nome, tipo e nível padrão, sem texto de prompt.
- **FR-003**: Presets DEVEM guardar nome, nível por ID de critério, duração permitida, duração
  ideal, reordenar, palavras protegidas e instruções adicionais.
- **FR-004**: `preset list/show/create/update/set-default/delete` DEVEM existir conforme
  docs/cli.md §11.3.
- **FR-005**: Deve haver sempre exatamente um preset padrão, que não pode ser apagado.
- **FR-006**: A leitura de um preset DEVE completar critérios novos com o nível padrão e
  ignorar critérios removidos.
- **FR-007**: O serviço DEVE oferecer a montagem do prompt de um preset (base + trechos dos
  níveis + formato + instruções), para o item 9.

---

## Entidades e dados

- **Preset**: id, name (único), is_default, levels (JSON id → nível), duration_allowed
  (min, max), duration_ideal (min, max), reorder, protected_words, instructions, created_at,
  updated_at.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/criteria/` — textos e carregamento validado.
- `packages/core/src/wordcut/` — migração e serviço de presets, montagem do prompt.
- `apps/cli/src/wordcut_cli/` — `criteria` e `preset`.

### Fora de escopo
- Chamada ao LLM (item 9).
- Tela de configurações (fase 3).

---

## Pressupostos

- IDs dos critérios em inglês: filtros `triumphalism`, `fragile_theology`, `allegory`,
  `graceless_moralism`, `out_of_context`, `sectarianism`, `people_exposure`, `factual_error`;
  valores `christological`, `practical_application`, `memorable_phrase`. Nomes em português.
- Níveis na CLI e no JSON: `lenient`, `moderate`, `strict`.
