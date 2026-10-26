# QA — 2.1.a.2 — Critérios fixos no código e presets (`criteria list`, `preset`)

## Plano de QA — 2026-10-26

**baseline_commit**: aa687faf634cf2911d54c553d19ea62ad5316687
**Componentes em escopo**: `packages/core` (`wordcut.criteria` com `texts/base.md` e os 11
`texts/<id>.md`; `wordcut.db` com a migração `0006_presets.sql` e `db/presets.py`;
`wordcut.service.presets`; `wordcut.service.settings` para o `default_preset_id`);
`apps/cli` (`wordcut_cli.criteria`, `wordcut_cli.preset` e o registro em
`wordcut_cli/__init__.py`); documentação (`CHANGELOG.md`, `docs/architecture/README.md` §4).
**Suítes que valem como prova**:
- Python (core + cli), por arquivo:
  `uv run pytest packages/core/tests/test_criteria_catalog.py packages/core/tests/test_presets_service.py packages/core/tests/test_prompt.py apps/cli/tests/test_preset_command.py -q`
- Python, suíte completa: `uv run pytest -q` (inclui `test_db.py`, `test_settings_service.py`,
  `test_settings_command.py` e `test_cli.py`, que mudam com este item)
- Checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`

**Regras da barra**
- **Texto teológico tem fonte única.** Todo texto em `criteria/texts/` sai de
  `skills/video-corte-vertical/sugerir-cortes.md` (descrições, tradição, camadas, bônus,
  formato, salvaguardas), e as frases dos níveis saem de `docs/prototype/wordcut.html`
  (`LEVELS_F`, `LEVELS_V`). Não vale: critério novo, critério reescrito com outro sentido,
  exemplo que não está na fonte, nem nada de `skills/video-corte-vertical/exemplos.md`
  (calibração). Os exemplos que já fazem parte da definição na fonte (ex.: "as 5 pedras de
  Davi…", "Deus te deve") ficam como estão. Diferença de redação aceita: só ajuste de
  forma para virar instrução ao LLM (imperativo, pontuação), sem acrescentar nem tirar
  condição.
- O QA verifica **procedência** do texto, não correção teológica. Mesmo com PASS, o texto
  dos critérios exige revisão humana qualificada antes do merge (constituição §I: "só
  mudam por commit revisado"); a rodada registra isso como pendência, nunca como validado.
- Instalação nova: todo teste roda com `WORDCUT_HOME` em `tmp_path` (fixture
  `wordcut_home`); nenhum teste lê o banco real.
- "Sem texto de prompt na saída" se prova procurando, no stdout **e** no stderr de cada
  comando (`--json` e legível, sucesso e erro), a frase de cada nível
  (`LEVELS_F`/`LEVELS_V`) e uma frase-âncora de `base.md` (ex.: "Stone-Campbell").
- CLI pelo contrato: `wordcut_cli.main(argv)` + `capsys`, como os demais testes da CLI;
  stdin com `io.StringIO` (helper `redirect_stdin`).
- Mutações cobradas na avaliação: as linhas `🧬 EXIGE` de `tdd.md`. Mutação manual
  desfeita na hora.
- Decisões que o plano não tomou, fixadas pelo QA na opção mais conservadora (lacunas em
  `tdd.md`): bônus e salvaguardas de colagem de `sugerir-cortes.md` entram no prompt
  (`base.md` ou bloco de edição do `build_prompt`); `base.md` sem números de duração;
  gancho, ideias por pregação e autônomo/fechamento/limpo seguem como texto fixo (não são
  campos do preset); `update` sem campos, arquivo de instruções inexistente e nome vazio →
  `invalid_argument`; `--level` repetido para o mesmo critério → vale o último.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Catálogo | (a) `catalog()` carrega o catálogo **real** do pacote com exatamente 11 critérios: 8 `filter` (`triumphalism`, `fragile_theology`, `allegory`, `graceless_moralism`, `out_of_context`, `sectarianism`, `people_exposure`, `factual_error`) e 3 `value` (`christological`, `practical_application`, `memorable_phrase`), IDs únicos, ordem estável (a de `sugerir-cortes.md`: filtros e depois valores); (b) cada critério tem `name` em português, `type` ∈ {filter, value}, `default_level` ∈ {lenient, moderate, strict} e fragmento não vazio nos três níveis; (c) níveis padrão = os do protótipo: `strict` em triumphalism, fragile_theology, out_of_context, sectarianism, people_exposure e christological; `moderate` nos outros cinco; (d) validação: diretório de textos de teste (em `tmp_path`) com um critério sem `## strict`, com `type` inválido, com `default_level` inválido ou com ID repetido → exceção de programação (não `WordcutError` de usuário), com o nome do arquivo na mensagem; (e) `base.md` existe e não fica vazio; (f) os textos são achados como dados do pacote (mesmo mecanismo das migrações: caminho relativo ao módulo, incluído pelo `packages = ["src/wordcut"]` do hatch) | `packages/core/tests/test_criteria_catalog.py`, unidade pela interface pública de `wordcut.criteria` (carregador que aceita o diretório, como `db.connect(migrations=...)`, para os casos negativos); tabela exata de IDs/tipos/níveis padrão no teste. **Procedência do texto** (verificação do QA, sem teste): para cada `<id>.md`, a descrição de `sugerir-cortes.md` presente com espaços normalizados; a seção de cada nível contém a frase do protótipo do seu tipo (filtro: "Exclui só quando é evidente" / "Exclui quando é provável; o limítrofe vai com alerta" / "Exclui na menor suspeita"; valor: "Basta tocar no tema" / "O valor aparece com clareza" / "O valor é o centro do corte, explicado e não só citado"); `grep -rniE 'exemplos\.md\|calibra' packages/core/src/wordcut/criteria/texts` vazio; nenhuma linha de `exemplos.md` nos textos; nenhum critério além dos 11. `base.md`: objetivo (com "na dúvida, descarte"), referência teológica Stone-Campbell, as três camadas na ordem, bônus, gancho/autônomo/colagem/fechamento/limpo e salvaguardas de colagem; **sem** a seção "Processo" (comandos `wordcut`, `roteiros/*.json`, tabela de apresentação) e **sem** os números 40–75/55–65 fixos (vêm do preset) |
| 2 — Presets no banco | (a) banco novo fica em `user_version` 6 com a tabela `presets` (`test_db.py` verde: a migração mais nova é aplicada); banco na versão 5 migra sem perder `settings`/`sermons`; (b) instalação nova tem exatamente um preset, "Padrão", `is_default = 1`, durações 40–75 e 55–65, `reorder = 1`, palavras protegidas `não, mas, se`, instruções vazias; (c) `UNIQUE(name)` e índice único parcial `WHERE is_default = 1`: inserir um segundo `is_default = 1` direto pelo repositório falha no SQLite; (d) repositório grava e relê todos os campos da entidade da spec (id, name, is_default, levels JSON, durações min/max, reorder, protected_words, instructions, created_at, updated_at) sem regra de negócio (a regra fica no serviço, ADR-0004); (e) migração sem `BEGIN`/`COMMIT` (regra de `db.connect`) | `packages/core/tests/test_presets_service.py` (ou um `test_presets_repository.py`, no padrão de `test_sermons_repository.py`) com SQLite real em `tmp_path`; `test_db.py` existente; leitura do `.sql`. Os níveis do "Padrão" de fábrica se provam pelo serviço (passo 3 b), não pelo JSON semeado |
| 3 — Serviço | (a) `list_presets`/`show_preset` devolvem `levels` **completo** (11 IDs) e sem texto de prompt; (b) instalação nova: `default_preset()` = "Padrão" com `levels` igual ao `default_level` de cada critério do catálogo; (c) `create_preset(name)` copia o preset **padrão atual** (não os valores de fábrica): mudar o padrão antes e conferir a cópia; `from_id` copia o indicado; a cópia nasce `is_default = false`; (d) `update_preset` muda nome, nível (um ou vários), durações, reorder, palavras protegidas e instruções, só os campos dados, e atualiza `updated_at`; persiste ao reabrir a conexão; (e) `set_default` troca o padrão: depois dele `SELECT count(*) WHERE is_default = 1` = 1 e é o novo; (f) `delete_preset` do padrão → `WordcutError("default_preset")` saída 5, nada apagado; apagar outro funciona; (g) FR-006: linha com `levels` sem um ID do catálogo → lido com o `default_level` dele; linha com ID desconhecido (ex.: `"removed_criterion"`) → ausente de `show`, de `list` e de `build_prompt`; (h) bordas → `invalid_argument` com `details.argument`: critério inexistente, nível fora de {lenient, moderate, strict}, nome repetido, nome vazio/só espaços, duração mal formada (`"60"`, `"a-b"`, negativa), `min > max` (com `min == max` aceito), ideal fora do permitido — inclusive quando só uma das duas faixas é alterada e a outra, gravada, deixa de caber; instruções acima de 4000 caracteres (4000 aceito, 4001 recusado); `update_preset` sem nenhum campo; (i) `not_found` para ID inexistente em show/update/set-default/delete e no `from_id`; (j) palavras protegidas normalizadas (`" não, mas,, se, não "` → `["não", "mas", "se"]`); (k) `show_settings(conn)["default_preset_id"]` = ID do padrão (antes `None`), e muda após `set_default` | `packages/core/tests/test_presets_service.py`, nível serviço com banco real em `WORDCUT_HOME` temporário; linhas com `levels` antigos inseridas por SQL direto para (g). `test_settings_service.py` e `test_settings_command.py` atualizados de `None` para o ID semeado (ajuste justificado, não regressão) |
| 3 — Serviço · `build_prompt` | (a) contém o texto de `base.md`; (b) para cada um dos 11 critérios, contém o fragmento do nível **do preset** e **não** contém os fragmentos dos outros dois níveis desse critério; (c) contém as durações do preset (ex.: com ideal 60–75, "60" e "75" aparecem e "55–65" não); (d) contém as palavras protegidas e o estado de reordenar (texto diferente com `reorder` ligado e desligado); (e) com instruções, elas aparecem rotuladas como do administrador e depois dos critérios; sem instruções, nenhum rótulo vazio; (f) ID desconhecido gravado não gera trecho; critério novo entra com o nível padrão; (g) não chama rede nem LLM | `packages/core/tests/test_prompt.py`, unidade pela interface pública (`build_prompt(preset)`), comparando com os fragmentos lidos de `catalog()` (não com strings copiadas) |
| 4 — CLI | (a) `criteria list --json` → saída 0, `{"items": [...]}` com 11 itens, cada um com exatamente `id`, `name`, `type`, `default_level` (nenhum campo com fragmento); legível também sem texto de prompt; (b) `preset list --json` → `{"items": [...]}` com o "Padrão" e `is_default: true`; `preset show <id> --json` → objeto com os campos da entidade, `levels` completo, sem prompt; (c) `preset create "Estudo bíblico"` → saída 0, cópia do padrão; `--from <id>` copia o indicado; (d) `preset update <id> --level allegory=strict --level christological=lenient --duration-ideal 60-75 --duration-allowed 45-80 --no-reorder --protected-words "não,mas" --name X` → refletido no `show`; `--instructions-file -` lê do stdin redirecionado; `--instructions-file <arquivo>` lê do arquivo; (e) `preset set-default <id>` → `settings show --json` traz o novo `default_preset_id`; (f) `preset delete <padrão> --json` → saída 5, `{"error": {"code": "default_preset"}}`; (g) erros de uso → saída 2, `invalid_argument`, `details.argument` com o nome do parser (`level`, `duration_ideal`…), `details.choices` em nível inválido, e a mensagem não repete o valor digitado (ADR-0015); ID inexistente → saída 3; (h) `--help` de `criteria` e de cada ação de `preset` diz que é do administrador e traz exemplo; `test_cli.py::COMMANDS` inclui `criteria` e `preset`; (i) nenhum comando imprime fragmento ou `base.md` (regra da barra) | `apps/cli/tests/test_preset_command.py` (e `criteria list` no mesmo arquivo ou em `test_criteria_command.py`) por `main(argv)` + `capsys`; `redirect_stdin` para `-`; arquivo de instruções em `tmp_path`; `test_cli.py` atualizado |
| 5 — Documentação | `CHANGELOG.md` em "Não lançado" cita `criteria list` e `preset`; `docs/architecture/README.md` §4 cita `wordcut.criteria`, a tabela `presets` (migração 0006), `service.presets` e os comandos; `docs/cli.md` §11.2–§11.3 continua verdadeiro (se o JSON ou uma regra nova — limite de 4000 caracteres, `update` sem campos — divergir, §11.3 atualizado); nenhum nome de pessoa nem segredo nos textos | `git diff aa687fa -- CHANGELOG.md docs/`; leitura; sem teste automatizado |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário "listar critérios" / Verificação 1 — `criteria list --json` → 8 `filter` + 3 `value` com `id`, `name`, `type`, `default_level`, sem texto de prompt | Passo 4 (a)(i); Passo 1 (a)(c) |
| Cenário "preset padrão de fábrica" / Verificação 2 — "Padrão" marcado padrão, níveis padrão, 40–75, 55–65, reordenar ligado, "não, mas, se", instruções vazias | Passo 4 (b); Passo 3 (b); Passo 2 (b) |
| Cenário "criar e editar" / Verificação 3 — `create` copia do padrão (ou `--from`); `update --level allegory=strict --duration-ideal 60-75 --instructions-file -` muda os valores | Passo 4 (c)(d); Passo 3 (c)(d) |
| Cenário "escolher o padrão e proteger o padrão" / Verificação 4 — `set-default` troca; `delete` do padrão → `default_preset`, saída 5 | Passo 4 (e)(f); Passo 3 (e)(f) |
| Cenário "critério novo ou removido no código" / Verificação 5 — novo com o nível padrão; ID desconhecido ignorado | Passo 3 (g); `build_prompt` (f) |
| Borda — `--level` com critério inexistente ou nível inválido → `invalid_argument` / Verificação 6 | Passo 3 (h); Passo 4 (g) |
| Borda — durações com mínimo > máximo, ou ideal fora do permitido → `invalid_argument` / Verificação 6 | Passo 3 (h), inclusive a validação cruzada com a faixa gravada |
| Borda — nome repetido → `invalid_argument` / Verificação 6 | Passo 3 (h); Passo 4 (g) |
| Borda — instruções de arquivo ou stdin, até um limite | Passo 4 (d); Passo 3 (h) com 4000/4001 |
| Borda — textos validados ao carregar; falta de nível pega por teste | Passo 1 (a)(b)(d) |
| FR-001 — critérios em arquivos do core, um por critério, conteúdo de `sugerir-cortes.md`, sem calibração | Passo 1 + verificação de procedência (regra da barra); revisão humana do texto pendente fora do QA |
| FR-002 — `criteria list` sem texto de prompt | Passo 4 (a)(i) |
| FR-003 — preset guarda nome, níveis por ID, duração permitida e ideal, reordenar, palavras protegidas, instruções | Passo 2 (d); Passo 3 (d) |
| FR-004 — `preset list/show/create/update/set-default/delete` conforme §11.3 | Passo 4 (b)–(h) |
| FR-005 — sempre exatamente um padrão, que não pode ser apagado | Passo 2 (c); Passo 3 (e)(f) |
| FR-006 — completar critérios novos e ignorar removidos | Passo 3 (g) |
| FR-007 / Verificação 7 — `build_prompt` com base + trecho do nível de cada critério + formato + instruções | Passo 3 `build_prompt` (a)–(f) |
| Constituição §I — texto do prompt nunca exposto nem editável | Passo 4 (i); nenhuma opção da CLI aceita texto de critério (só nível) |
| Verificação 8 — quality gates limpos | `uv run pytest -q`; `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

## Rodada 1 — 2026-10-26 — working tree sobre aa687fa

**baseline_commit**: aa687faf634cf2911d54c553d19ea62ad5316687
**Componentes avaliados**: `packages/core` (`wordcut.criteria` e textos, migração 0006,
`db.presets`, `service.presets`, `service.settings`); `apps/cli` (`criteria`, `preset`,
`settings`, registro); documentação
**Suítes**: Python ✅ (749 / 0 falhas) · `ruff check` ✅ · `ruff format --check` ✅ ·
`mypy` ✅ (68 arquivos)

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Catálogo | PASS | `test_criteria_catalog.py` (11 verdes): catálogo real com os 11 IDs, tipos e níveis padrão na ordem da fonte; casos negativos por `load_catalog(tmp)` com o nome do arquivo; textos no pacote. Procedência abaixo |
| 2 — Presets no banco | PASS | `test_presets_repository.py` (8): "Padrão" de fábrica, releitura de todos os campos, segundo padrão e nome repetido recusados pelo SQLite, 5 → 6 sem perder `settings`; `0006_presets.sql` sem `BEGIN`/`COMMIT`. A migração 5 → 6 confere `settings`, não `sermons`; a 0006 só cria e semeia `presets` |
| 3 — Serviço | PASS | `test_presets_service.py`, `test_settings_service.py`: (a)–(k) cobertos; mutações EXIGE de create, set_default, delete, FR-006, ideal, min ≤ max e 4000 mortas |
| 3 — Serviço · `build_prompt` | PASS | `test_prompt.py` (10): nível do preset entra e os outros dois não (fragmentos de `catalog()`), durações do preset, reorder ligado/desligado, palavras, instruções rotuladas depois dos critérios, FR-006, sem rede |
| 4 — CLI | PARCIAL | `test_preset_command.py` e `test_cli.py` cobrem (a)–(i), mas há duas lacunas. (1) O limite de 4000 pela CLI devolve `details.argument: "instructions"`, e a lista do `update` sem campos traz o mesmo nome (`service/presets.py:27-29`, `:278`). O parser chama a opção de `instructions_file`, e a matriz 4(g) e `docs/cli.md` §5 pedem esse nome; a própria opção dá `instructions_file` quando o arquivo não pode ser lido. (2) `--level` repetido, o último vale (decisão 9, `docs/cli.md` §11.3): está implementado e foi conferido à mão, mas não tem teste, e a mutação "vale o primeiro" sobrevive com 61 testes verdes |
| 5 — Documentação | PASS | `CHANGELOG.md` (criteria list, preset, `default_preset_id`, revisão humana pendente); arquitetura §4; `docs/cli.md` §11.2–§11.3 com o JSON da decisão 8, o limite de 4000 e as bordas do `update`; sem nome de pessoa nem segredo |

**Procedência do texto teológico** (linha a linha, script no scratchpad; o QA prova
procedência, não doutrina):
- As 11 descrições estão em `sugerir-cortes.md`, literais. Cada nível acrescenta só a frase
  `LEVELS_F`/`LEVELS_V` do protótipo do seu tipo.
- `base.md` repete a fonte linha a linha: objetivo, tradição Stone-Campbell, camadas, bônus e
  formato. Só a linha da duração tem vagas, e com 40/75/55/65 volta a ser idêntica à fonte. O
  arquivo não tem a seção "Processo", `exemplos.md`, calibração nem os números 40–75/55–65
  fixos.
- O prompt do "Padrão" montado por `build_prompt` é idêntico à fonte sem "Processo", tirando
  as frases de nível. Sobram duas diferenças:
  - a linha das salvaguardas da decisão 2;
  - o bloco "Palavras protegidas" (frase do protótipo) com `"não", "mas", "se"`.
- **Fato 1 (decisão 2)**: aceito. A linha bate com a decisão registrada no plan.md, e no
  "Padrão" a condição continua no prompt pelo bloco de palavras protegidas. Consequência que
  fica para a revisão humana: com `--protected-words ""` e reordenar ligado, nenhuma palavra
  fica nomeada.
- **Linha não literal que o implementador não citou**: `options/no_reorder.md:3` ("Reordenar
  não é permitido: os trechos do corte seguem a ordem da pregação."). Não é texto teológico.
  A matriz pede um texto diferente com reordenar desligado (`build_prompt` (d)), e a fonte
  não tem esse texto, então a regra de procedência não serve para julgar esta linha. Fica
  registrada para a revisão humana, sem mudar o veredito. Os rótulos "Palavras protegidas" e
  "Instruções adicionais do administrador" vêm do protótipo e da matriz (e).
- **Pendência, não validação**: o texto dos critérios exige revisão humana por pessoa
  qualificada antes do merge (constituição §I).

**Fato 2**: o precedente de `settings` existe (`--model` devolve `llm_model`), mas não muda
a barra. A matriz 4(g) pede o nome do parser, por isso o passo 4 fica PARCIAL.

**Mutações** (cópia no scratchpad, código da worktree intacto):
- As 12 `🧬 EXIGE` morreram.
- 10 mutações extras também morreram: `update` sem campos, dedup das palavras, nome repetido,
  ideal cruzado só quando muda, nível e critério inexistentes, `default_preset_id`, rótulo
  antes dos critérios, reorder ignorado e ordem do catálogo.
- Sobreviveu só "`--level` repetido: vale o primeiro".

**Comentários (CONTRIBUTING §5)**: os 9 comentários novos estão em inglês e cada um tem tipo:
referência (ADR-0015, FR-005, docs/cli.md, protótipo), intenção, formato ou alerta. Não há
comentário que sobre.

### Critérios de aceite
- ✅ Listar critérios / Verificação 1 — `test_criteria_list_gives_the_eight_filters_and_three_values_with_id_name_type_and_level`
- ✅ Preset padrão de fábrica / Verificação 2 — `test_a_new_installation_lists_the_factory_preset_with_every_criterion_at_its_default`, `test_preset_list_of_a_new_installation_gives_the_factory_default`
- ✅ Criar e editar / Verificação 3 — `test_preset_create_copies_the_default`, `test_preset_update_changes_the_fields_given_and_show_reflects_them`
- ✅ Escolher e proteger o padrão / Verificação 4 — `test_preset_set_default_changes_the_default_preset_of_settings_show`, `test_preset_delete_of_the_default_is_a_default_preset_error_with_exit_5`
- ✅ Critério novo ou removido / Verificação 5 — `test_a_criterion_the_stored_preset_lacks_is_read_with_its_default_level`, `test_a_criterion_removed_from_the_code_is_left_out_of_show_and_list`, `test_the_prompt_takes_a_missing_criterion_at_its_default_and_ignores_a_removed_one`
- ✅ Borda `--level` inválido / Verificação 6 — `test_an_invalid_update_is_refused_naming_the_argument_and_changes_nothing`, `test_an_invalid_update_is_a_usage_error_naming_the_option_without_the_typed_value`
- ✅ Borda durações (inclusive a faixa gravada) — mesmos testes, casos `allowed above/below stored ideal`
- ✅ Borda nome repetido — `test_renaming_to_the_name_of_another_preset_is_a_usage_error`, `test_a_preset_created_with_a_repeated_or_blank_name_is_refused`
- ✅ Borda instruções de arquivo/stdin até um limite — `test_preset_update_reads_the_instructions_from_a_file`, stdin no teste de update, `test_an_update_at_the_boundary_is_accepted` (4000) e caso 4001
- ✅ Borda textos validados ao carregar — `test_a_criterion_without_the_strict_level_is_a_programming_error_naming_its_file` e afins
- ✅ FR-001 — procedência provada acima; a revisão humana do texto fica pendente, fora do QA
- ✅ FR-002 — teste do `criteria list` e `test_no_criteria_or_preset_output_carries_prompt_text`
- ✅ FR-003 — `test_an_inserted_preset_is_read_back_by_its_id_with_every_field`, `test_an_update_changes_every_field_given_and_is_kept_after_reopening`
- ✅ FR-004 — `test_preset_command.py` (as seis ações)
- ✅ FR-005 — `test_the_database_refuses_a_second_default_preset`, `test_set_default_makes_the_preset_the_only_default`, `test_deleting_the_default_preset_is_refused_and_deletes_nothing`
- ✅ FR-006 — os testes de leitura e de prompt já citados na Verificação 5
- ✅ FR-007 / Verificação 7 — `test_prompt.py`
- ✅ Constituição §I — `test_no_criteria_or_preset_output_carries_prompt_text` (stdout e stderr, json e texto, sucesso e erro); a CLI só aceita nível, nenhum texto de critério
- ✅ Verificação 8 — pytest, ruff e mypy verdes

### Veredito geral: PARCIAL
O passo 4 fica PARCIAL por duas lacunas: `details.argument` "instructions" em vez do nome do
parser, `instructions_file`, e a decisão 9 (`--level` repetido) sem teste. Os outros passos e
os 19 critérios estão cobertos. O texto dos critérios continua pendente de revisão humana
qualificada.

## Rodada 2 — 2026-10-26 — working tree sobre aa687fa

**baseline_commit**: aa687faf634cf2911d54c553d19ea62ad5316687
**Componentes avaliados**: `apps/cli` (`wordcut_cli.preset`, reaberto); suíte completa e
checagens estáticas para o resto
**Suítes**: Python ✅ (751 / 0 falhas) · `ruff check` ✅ · `ruff format --check` ✅ ·
`mypy` ✅ (68 arquivos)

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Catálogo | PASS | sem mudança desde a Rodada 1; suíte verde |
| 2 — Presets no banco | PASS | sem mudança desde a Rodada 1; suíte verde |
| 3 — Serviço | PASS | sem mudança desde a Rodada 1 (`service/presets.py` continua devolvendo `instructions`; quem traduz é a CLI) |
| 3 — Serviço · `build_prompt` | PASS | sem mudança desde a Rodada 1 |
| 4 — CLI | PASS | (1) `wordcut_cli/preset.py:32-33,152-162`: a CLI troca `instructions` por `instructions_file` em `details.argument`, nome único ou lista. `test_instructions_above_the_limit_are_refused_naming_the_option_of_the_parser` (4001 pelo stdin) e o caso `no field` de `test_an_invalid_update_is_a_usage_error_naming_the_option_without_the_typed_value` fixam o nome do parser. (2) `test_a_level_repeated_for_the_same_criterion_keeps_the_last` mata "vale o primeiro". As outras chaves de `details` (`choices`) e o `not_found` do `update` continuam iguais |
| 5 — Documentação | PASS | sem mudança desde a Rodada 1; `docs/cli.md` §11.3 já dizia "vale o último" e o limite de 4000 |

**Mutações** (cópia em scratchpad com o `conftest.py` da raiz, worktree intacta): 5 de 5
mortas.
- "`--level` repetido: vale o primeiro" (`reversed`): 1 teste.
- Sem a tradução `instructions` → `instructions_file`: 2 testes.
- Tradução só de nome único, sem tratar a lista do `update` sem campos: 1 teste.
- Tradução que descarta as outras chaves de `details` (`choices`): 1 teste.
- Tradução sem o guarda de `argument`, que faria o `not_found` virar `internal_error`: 1 teste.

**Pendência, não validação** (vem da Rodada 1): o texto dos critérios exige revisão humana
por pessoa qualificada antes do merge (constituição §I). A linha `options/no_reorder.md:3` e a
consequência da decisão 2 com `--protected-words ""` também ficam para essa revisão.

### Critérios de aceite
- ✅ Os 19 critérios da Rodada 1 continuam cobertos pelos mesmos testes, todos verdes.
- ✅ Borda `--level` inválido / Verificação 6 — mais
  `test_instructions_above_the_limit_are_refused_naming_the_option_of_the_parser` para o
  limite pela CLI.
- ✅ Criar e editar / Verificação 3 — mais `test_a_level_repeated_for_the_same_criterion_keeps_the_last`
  (decisão 9).

### Veredito geral: PASS
As duas lacunas do passo 4 foram fechadas e as mutações que as cobram morrem. O texto dos
critérios continua pendente de revisão humana qualificada antes do merge.
