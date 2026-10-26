# Plan: Critérios fixos no código e presets (`criteria list`, `preset`)

**Issue**: 2.1.a.2
**Feature**: specs/2.1.a.2-criteria-presets
**Data**: 2026-10-26

---

## Resumo

Os textos dos critérios viram arquivos do pacote core (um por critério, com os três níveis,
e um prompt base), carregados e validados num catálogo. Presets ficam no SQLite com os níveis
por ID de critério, o formato, as opções de edição e as instruções; o serviço completa
critérios novos, ignora removidos, garante um padrão e monta o prompt. A CLI ganha
`criteria list` e o grupo `preset`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core/src/wordcut/criteria/` — textos e catálogo.
- `packages/core/src/wordcut/` — migração, repositório e serviço de presets, montagem do prompt.
- `apps/cli/src/wordcut_cli/` — `criteria.py`, `preset.py`.

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/criteria/texts/base.md` — prompt base: objetivo, tradição teológica (de `sugerir-cortes.md`), as três camadas, formato da resposta deixado para o item 9 |
| Criar | `packages/core/src/wordcut/criteria/texts/<id>.md` — um por critério (8 filtros, 3 valores): cabeçalho com `name`, `type`, `default_level`; seções `## lenient`, `## moderate`, `## strict` com o trecho de prompt de cada nível |
| Criar | `packages/core/src/wordcut/criteria/__init__.py` — `Criterion(id, name, type, default_level, fragments)`, `catalog()` validado (todo critério com os três níveis, tipos e níveis válidos, IDs únicos) |
| Criar | `packages/core/src/wordcut/db/migrations/<próximo>_presets.sql` — tabela `presets` e o preset "Padrão" semeado como padrão |
| Criar | `packages/core/src/wordcut/db/presets.py` — repositório |
| Criar | `packages/core/src/wordcut/service/presets.py` — `list_presets`, `show_preset`, `create_preset(name, from_id)`, `update_preset(...)`, `set_default`, `delete_preset`, `default_preset`, `build_prompt(preset) -> str` |
| Alterar | `packages/core/src/wordcut/service/settings.py` (se existir) — `default_preset_id` real no `settings show` |
| Criar | `apps/cli/src/wordcut_cli/criteria.py`, `apps/cli/src/wordcut_cli/preset.py` |
| Criar | `packages/core/tests/test_criteria_catalog.py`, `test_presets_service.py`, `test_prompt.py`; `apps/cli/tests/test_preset_command.py` |
| Alterar | `CHANGELOG.md`, `docs/architecture/README.md` §4 |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Formato dos textos | Markdown com cabeçalho simples (`name:`, `type:`, `default_level:`) e seções por nível | Legível para revisão teológica por commit; sem dependência de YAML |
| Conteúdo dos níveis | filtro: brando "exclui só quando é evidente", moderado "exclui quando é provável; limítrofe com alerta", rigoroso "exclui na menor suspeita" + a descrição do filtro; valor: brando "basta tocar no tema", moderado "o valor aparece com clareza", rigoroso "o valor é o centro do corte, explicado e não só citado" + a descrição | Frases já aprovadas no protótipo; descrições de `sugerir-cortes.md` |
| Níveis padrão | os do protótipo (triunfalismo, teologia frágil, fora de contexto, sectarismo, exposição de pessoas e cristológico rigorosos; demais moderados) | Requisito e protótipo |
| Validação do catálogo | ao primeiro uso; falha → exceção de programação; teste carrega o catálogo real | Erro de texto pego no CI |
| Níveis no banco | JSON `{criterio_id: nível}`; leitura completa com o padrão e descarta IDs desconhecidos | FR-006 sem migração por critério |
| Preset padrão | coluna `is_default` com índice único parcial (`WHERE is_default = 1`); `set_default` troca numa transação | Sempre exatamente um padrão |
| Nome único | `UNIQUE(name)`; repetido → `invalid_argument` | Borda da spec |
| Durações | pares `min-max` em segundos inteiros; regras `min ≤ max`, ideal dentro do permitido | Borda da spec |
| Palavras protegidas | lista de strings normalizada (strip, sem vazios, sem repetição); CLI recebe `"a,b"` | docs/cli.md §11.3 |
| Instruções | texto livre até 4000 caracteres, de arquivo ou stdin | Evita prompt gigante |
| `build_prompt` | base + para cada critério o trecho do nível + números do formato + opções de edição + instruções adicionais rotuladas como do administrador | FR-007; ADR-0010 |
| Texto do prompt na CLI | nunca exposto (`criteria list` sem fragmentos; `preset show` sem prompt) | §I |
| Bônus (lacuna do QA) | os bônus de `sugerir-cortes.md` entram no `base.md` como texto fixo, sem alteração do texto original | Decisão do orquestrador, rodada 1; o conteúdo da fonte não some |
| Salvaguardas de colagem (lacuna do QA) | entram no bloco de edição do `build_prompt` quando reordenar está ligado; a regra de não tirar "não", "mas" e "se" fica ligada às palavras protegidas | Decisão do orquestrador, rodada 1 |
| Números do formato (lacuna do QA) | só do preset; `base.md` sem números fixos de duração | Decisão do orquestrador; preset editado não contradiz o base |
| Gancho, autônomo, fechamento, limpo (lacuna do QA) | texto fixo no `base.md`, tirado de `sugerir-cortes.md`; nenhum campo novo no preset | Decisão do orquestrador; segue a entidade da spec |
| Níveis do "Padrão" semeado (lacuna do QA) | migração semeia `levels '{}'`; os níveis padrão vêm do catálogo na leitura (FR-006) | Decisão do orquestrador; uma fonte só para o nível padrão |
| `default_preset_id` (lacuna do QA) | real no `settings show`, no passo 3; testes de 2.1.a.1 que esperavam `None` atualizados | Decisão do orquestrador |
| Carregador do catálogo (lacuna do QA) | `load_catalog(directory)` com diretório injetável; `catalog()` em cache por cima | Decisão do orquestrador; permite o teste negativo |
| JSON do preset (lacuna do QA) | `{"id", "name", "is_default", "levels": {id: nível}, "duration_allowed": {"min", "max"}, "duration_ideal": {"min", "max"}, "reorder", "protected_words": [...], "instructions", "created_at", "updated_at"}`, fixado em teste e em `docs/cli.md` §11.3 | Decisão do orquestrador |
| Bordas do `update` (lacuna do QA) | sem campos, arquivo de instruções inexistente e nome vazio → `invalid_argument` sem repetir o valor (ADR-0015); `--level` repetido para o mesmo critério → vale o último | Decisão do orquestrador |
| Procedência do texto teológico (lacuna do QA) | `texts/*.md` sai literalmente de `sugerir-cortes.md` e das frases de nível do protótipo, sem critério, exemplo ou doutrina inventados. **O texto precisa de revisão humana por pessoa qualificada antes de valer** (constituição §I) | Decisão do orquestrador; o QA prova procedência, não doutrina |
| Layout dos textos (implementação, rodada 1) | critério: cabeçalho `id`, `name`, `type`, `default_level`, `position` (ordem de `sugerir-cortes.md`); `base.md` é `string.Template` com as vagas `${filters}`, `${values}` e as quatro durações; `options/` traz `reorder.md` (salvaguardas, com "nem de tirar uma palavra protegida" no lugar de "não", "mas", "se", pela decisão 2), `no_reorder.md`, `protected_words.md` e `instructions.md` | ID explícito no texto (o ID gravado no preset não depende do nome do arquivo) e repetição detectável; vaga validada ao carregar |

---

## Ordem de implementação

- [x] **Passo 1 — Catálogo** — textos (base + 11 critérios) e `criteria.catalog()` validado.
- [x] **Passo 2 — Presets no banco** — migração com o "Padrão" semeado, repositório.
- [x] **Passo 3 — Serviço** — CRUD, padrão único, proteção do padrão, completar/descartar
  critérios, validações, `build_prompt`.
- [x] **Passo 4 — CLI** — `criteria list`, `preset list/show/create/update/set-default/delete`.
- [x] **Passo 5 — Documentação** — CHANGELOG, arquitetura §4.

---

## Fora de escopo

- Chamada ao LLM e validação da resposta (item 9).

---

## Verificação

- [x] `criteria list --json` → 11 critérios (8 `filter`, 3 `value`) com id, nome, tipo, nível
  padrão e nenhum texto de prompt.
- [x] Instalação nova → um preset "Padrão" padrão com os valores da spec.
- [x] `preset create` copia do padrão (ou de `--from`); `preset update` muda nível, durações,
  reordenar, palavras e instruções.
- [x] `set-default` troca o padrão; `delete` do padrão → `default_preset` (saída 5).
- [x] Critério novo no catálogo aparece com o nível padrão; ID desconhecido gravado é ignorado.
- [x] Nível, critério, durações ou nome inválidos → `invalid_argument`.
- [x] `build_prompt` contém o trecho do nível escolhido de cada critério e as instruções.
- [x] Quality gates limpos.
