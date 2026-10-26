# QA — 1.1.h.1 — Exportar o corte 9:16 (`cut render`)

## Plano de QA — 2026-10-26

**baseline_commit**: 80e64ff34df99cb5f4389d5888672e852536f2f0
**Componentes em escopo**: `packages/core` (`wordcut/rendering/` novo com `options.py`,
`estimate.py` e `pipeline.py`; `wordcut/edit/cleanup.py`, `edit/timeline.py`,
`edit/assemble.py`; `wordcut/vertical/render.py`; `wordcut/cuts/caption.py` (escala da
legenda, ver divergências); `wordcut/db/migrations/0009_renders.sql`, `db/renders.py` novo e
`db/cuts.py` (gravar `render_options`); `wordcut/tasks/render.py` novo e
`tasks/__init__.py`; `wordcut/service/rendering.py` novo e `service/cuts.py`; `conftest.py`
da raiz (fixture `no_real_rendering`)); `apps/cli` (`wordcut_cli/cut.py`); documentação
(`docs/architecture/README.md`, `CHANGELOG.md`, `docs/cli.md` §8.2, §8.7 e §10, ADR se houver
porta nova)
**Suítes que valem como prova**:
- Python (core e cli): `uv run pytest -q` na raiz; um arquivo: `uv run pytest <arquivo> -q`.
- Integração com ffmpeg real: `uv run pytest packages/core/tests/test_render_integration.py
  -q -rs`. Com o ffmpeg instalado (está em `~/.local/bin`), o teste **não pode** sair como
  `skipped`; se sair, o passo 3 fica PARCIAL.
- Checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`.

Diff de cada rodada: `git diff 80e64ff34df99cb5f4389d5888672e852536f2f0` mais os arquivos
novos de `git status --short`. Nenhum vídeo real é renderizado. Detecção e codificação são
dublês. O único ffmpeg real é o do clipe sintético `lavfi` de 2 s em baixa resolução.

### Decisões que o QA tomou no lugar do plano

O plan.md não decidiu estes pontos. A execução automatizada não admite perguntas, então o QA
adotou a opção mais conservadora. Cada uma vale como barra até o plano ser corrigido:

1. **Correções de grafia por palavra**: as correções do corte (`word_fixes`, por `word_id`)
   entram só no texto da legenda e nunca por `EditList.corrections`, que troca por padrão de
   texto. Corrigir uma palavra não muda outra palavra do corte com o mesmo texto original. A
   limpeza (hesitações e gaguejos) e a timeline usam o texto original.
2. **Quando as opções são salvas**: no gancho `admit`, sob a trava, depois de revalidar o
   corte e a pregação. `busy`, `not_found`, `sermon_not_processed`, `invalid_argument` e
   `--estimate` não gravam nada: `render_options`, `caption`, `edited` e `updated_at` do corte
   ficam iguais.
3. **Legenda**: `--caption`/`--no-caption` gravam pelo mesmo caminho de `cut caption
   --on/--off` (estilo completo gravado e corte marcado `edited`). O `caption` não é guardado
   em `render_options`, para não haver duas fontes da verdade. Omitido, vale o `enabled` atual
   do corte. As `options` da exportação registram o `caption` efetivo.
4. **`cut show`**: `render_options` são as opções efetivas, isto é, os padrões de §8.7 mais
   as salvas, com o `caption` igual ao `enabled` do corte. Chaves desconhecidas são ignoradas,
   e um valor salvo inválido volta ao padrão, como em `stored_caption`. `renders` lista as
   exportações do corte, da mais antiga para a mais nova, no formato de §9. As asserções de
   `test_cuts_service.py:149` (`{}`) e `:167` (`{"quality": "high"}` cru) mudam com este item.
   O QA aceita a mudança se ela só trocar o marcador provisório pelas opções efetivas.
5. **`path`**: é gravado relativo a `WORDCUT_HOME` (spec, Entidades) e sai absoluto no JSON,
   porque o §9 diz que `path` é o caminho local, para encadear (1.1.h.2). O arquivo existe
   em `path` quando a exportação é devolvida.
6. **`render_id`**: `task show <id> --json` de uma tarefa `render` terminada traz
   `result.render_id`, igual ao `id` da exportação. `--wait` devolve a exportação de §9, com
   as seis chaves.
7. **Falha**: uma exceção do pipeline deixa a tarefa `failed` com `internal_error` (saída 1),
   sem código novo. Ctrl+C deixa `interrupted` (saída 130). Nos dois casos, nenhuma linha em
   `renders`, nenhum arquivo em `media/cuts/<cut_id>/` (nem temporário) e nenhuma pasta de
   trabalho sobrando.
8. **Pregação não processada**: o estado diferente de `processed` dá `sermon_not_processed`
   (saída 5). Pregação `processed` sem o arquivo de vídeo dá `internal_error`, como
   `sermon download` (`service.sermons._video_file`). Recomenda-se ajustar a frase do spec.
9. **Estimativa**: não abre mídia, nem ffprobe, nem ffmpeg. Usa as palavras do banco, as
   opções efetivas mescladas às informadas, `energy=None` e uma taxa de quadros nominal
   (constante nomeada). Funciona com a trava ocupada por outro processo e sem o arquivo de
   vídeo. Devolve `duration` e o resumo das opções (`options`) e não cria tarefa.
10. **Ordem das recusas**: argumento inválido (2), depois corte inexistente (3), depois
    pregação não processada (5) e por último `busy` (4). As pré-condições são conferidas
    antes da trava e de novo no `admit`, como em `service.processing`.
11. **Estado do corte**: qualquer estado (`suggested`, `chosen`, `discarded`) pode ser
    exportado, porque nenhum documento proíbe. O QA não cobra recusa.
12. **Dublês e processo destacado**: `rendering.default_gateways` é trocado por uma fixture
    autouse (`no_real_rendering`) no `conftest.py` da raiz, que falha se o real for alcançado.
    O teste de integração monta os seus gateways e não passa pela fábrica. Teste sem `--wait`
    usa `harmless_tasks`. Nenhum teste lança um runner `render` real com `detached_tasks`,
    porque a guarda da ADR-0017 cobre só a rede e não impede ffmpeg e OpenCV no filho.
13. **Fade**: 0,5 s de vídeo e áudio no início e no fim. Num corte com menos de 1 s, o fade
    é limitado à metade da duração, sem `st` negativo.
14. **Normalização desligada**: tira só o `loudnorm`; o `aresample=48000` continua.
15. **720×1280**: a geometria da saída é 720×1280. A legenda escala por 720/1080 (tamanho,
    contorno, deslocamento da sombra, `max_width`), e a altura sai do `offset` em %. A câmera
    não muda, porque os centros estão em pixels da fonte.
16. **Arquivo**: renderiza num temporário da mesma pasta e faz `os.replace` para
    `<render_id>.mp4` só no sucesso. Nunca sobrescreve. Se a gravação da linha falhar, o
    arquivo é apagado.

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Opções | `RenderOptions()` tem os padrões de §8.7: `fillers=remove`, `stammers=remove`, `pauses=natural`, `smooth_joins`, `fade` e `normalize` ligados, `resolution=1080x1920`, `quality=high`, e o `caption` vem do corte (decisão 3). `merged(saved, changes)`: o informado vence o salvo, e o salvo vence o padrão; chave desconhecida é ignorada; valor salvo inválido volta ao padrão (decisão 4). A validação recusa valor fora das escolhas de cada campo com `invalid_argument`, `details.argument` e `details.choices`, sem repetir o valor digitado (ADR-0015). `summary()` traz as nove escolhas. | `packages/core/tests/test_render_options.py`, unitário, pela interface pública de `wordcut.rendering.options`. Mutações cobradas: padrão `pauses` trocado para `short`; mescla com o salvo vencendo o informado; validação de `resolution` removida. As três precisam ser mortas. |
| 2 — Limpeza e pausas | `remove_hesitations(words, fillers, stammers)`: com `fillers=False`, "hã" e "né" ficam e os gaguejos saem; com `stammers=False`, "o, o Senhor" e "não teve, não teve" ficam e "hã" sai; com os dois `False`, nada sai. A chamada sem argumentos é idêntica à atual (`test_cleanup.py` sem alteração). `plan_timeline` com pausas: `original` mantém uma pausa longa entre palavras do mesmo trecho (gap de saída igual ao de entrada, ±1 quadro, num clipe só); `short` reduz para 0,08 s no meio da frase e 0,20 s depois de ponto (±2 quadros); `natural` mantém 0,15 e 0,40 (`test_timeline.py` sem alteração). Regressão: `plan_timeline` com as opções padrão explícitas dá uma `Timeline` igual (`==`) à da chamada sem opções, em pelo menos um caso com hesitação, gaguejo, pausa longa e dois trechos fora de ordem. `estimate`: a duração é a de `plan_timeline(..., energy=None)` com as opções e a taxa nominal (decisão 9), e ela muda com `pauses` e com `fillers`. | `packages/core/tests/test_cleanup_options.py` e `test_timeline_pauses.py` com `Word` sintéticos, sem mídia. A estimativa é testada sem arquivo de vídeo no `WORDCUT_HOME`. Mutações cobradas: a flag `fillers` ignorada, a flag `stammers` ignorada e `original` caindo em `natural`. As três precisam ser mortas. |
| 3 — Montagem e codificação | `montage_command(..., smooth_joins=False)` não tem `afade`; ligado, tem os dois `afade` de 15 ms por clipe; o padrão é ligado (`test_assemble.py` sem alteração). Comando do codificador: `-s 720x1280` ou `1080x1920` conforme a resolução; `-crf 18` para `high` e `-crf 26` para `small`; `loudnorm=I=-14` só com `normalize` (decisão 14); `fade=t=in`, `fade=t=out`, `afade=t=in` e `afade=t=out` de 0,5 s só com `fade`, com o início do fade de saída em `duração − 0,5` e limite em cortes curtos (decisão 13). O reenquadramento devolve quadros na geometria escolhida. Integração: clipe `lavfi` (`testsrc2` 16:9 em baixa resolução com `sine`, 2 s, 30 fps), montagem real e codificação real com detecção dublê, `resolution=720x1280`, `quality=small`. O `ffprobe` do arquivo dá 720×1280 com áudio, e a duração bate com a da timeline (±1 quadro mais a folga do AAC, constante nomeada). | Unitário sobre os comandos gerados (lista de argumentos e filtro), sem rodar ffmpeg, em `test_render_pipeline.py` ou num arquivo próprio. `packages/core/tests/test_render_integration.py` com o mesmo `skipif` de `test_pipeline_cut.py`. Mutações cobradas: o CRF fixo em 18; a resolução fixa em 1080×1920 (precisa avermelhar a integração); o `loudnorm` sempre aplicado; o fade nunca aplicado. As quatro precisam ser mortas. |
| 4 — Pipeline do corte | `render_cut(gateways, ...)` monta a timeline a partir dos trechos do corte na ordem em que o corte toca, chama `assemble`, `detect` e `render` dos gateways nessa ordem e devolve o arquivo e a duração. As legendas passadas ao `render` trazem as correções de grafia por `word_id` (decisão 1), com o estilo do corte (`to_style`, escalado em 720, decisão 15). Com `caption` desligado, nenhuma legenda chega ao `render`. As opções chegam a cada gateway (`smooth_joins` à montagem; `resolution`, `quality`, `normalize` e `fade` ao `render`). O progresso passa pelas etapas (montando, detectando, legendas e renderizando) em ordem, com fração crescente. Uma falha de qualquer gateway propaga e não deixa arquivo em `output` nem pasta de trabalho (decisões 7 e 16). | `packages/core/tests/test_render_pipeline.py` com gateways dublês que registram as chamadas e escrevem um arquivo falso. Fixture autouse `no_real_rendering` no `conftest.py` da raiz (decisão 12). Mutações cobradas: as correções ignoradas na legenda; o `caption` desligado ignorado; o `output` escrito direto, sem temporário (falha deixa arquivo). As três precisam ser mortas. Uma correção numa palavra repetida tem de mudar só a palavra corrigida. |
| 5 — Persistência e tarefa | A migração `0009_renders.sql` cria `renders` com `id`, `cut_id` (FK com `ON DELETE CASCADE`), `path`, `duration`, `options` (JSON) e `created_at`; `test_db.py` continua verde. O repositório grava e lista por corte. `wordcut.tasks.render` está em `BUILTIN_KIND_MODULES`, com `needs_lock=True`. `start_render(home, cut_id, changes, detach, on_progress)`: com a máquina livre, grava as opções no `admit` (decisão 2) e cria a tarefa `render` com o recurso `cut`. Em primeiro plano, registra a exportação, deixa o arquivo em `media/cuts/<cut_id>/<render_id>.mp4` e põe `render_id` no resultado (decisões 5 e 6). Com a trava ocupada (`lock_owner`), dá `busy` sem tarefa e sem gravar opções. Corte inexistente dá `not_found`; pregação não processada dá `sermon_not_processed` (decisão 8). Uma falha do pipeline deixa a tarefa `failed`, sem linha e sem arquivo (decisão 7). Uma segunda exportação reaproveita as opções salvas quando omitidas. `estimate_render(conn, cut_id, changes)` não grava nada e funciona com a trava ocupada. `cut show` traz `render_options` efetivas e `renders` (decisão 4). | `packages/core/tests/test_render_task.py`, com SQLite real em `wordcut_home`, `rendering.default_gateways` dublê e `lock_owner` do `conftest.py`. Repositório em `test_renders_repository.py` ou no mesmo arquivo. `test_cuts_service.py` só troca as duas asserções da decisão 4. Mutações cobradas: as opções gravadas antes da trava (o caso `busy` tem de avermelhar); a linha inserida antes do sucesso do render (o caso de falha tem de avermelhar); o `estimate` gravando opções. As três precisam ser mortas. |
| 6 — CLI | `cut render <id> --wait --json` com dublês: saída 0, JSON com `{id, cut_id, path, duration, created_at, options}`, `path` absoluto e existente, e progresso `[render] …` no stderr (nada no stdout além do JSON). Com `--pauses short --no-fade --resolution 720x1280`, a exportação seguinte, sem opções, traz as mesmas `options`. Com `--estimate --json`: `duration` e `options`, nenhuma tarefa em `task list`, `render_options` do corte intacto, e funciona com a trava ocupada. Sem `--wait` (`harmless_tasks`): `{task_id, kind: "render", status: "running", cut_id}`. `--wait` seguido de `task show <task_id> --json` traz `result.render_id`. `--no-caption` muda o `enabled` de `cut caption` e o deixa assim; com `--estimate`, não muda. Recusas: `--resolution 640x480`, `--quality max`, `--pauses long` e `--fillers drop` saem com 2, com `details.argument` e `choices`, sem eco; `--fade --no-fade` sai com 2; corte inexistente sai com 3; trava ocupada sai com 4 sem tarefa; pregação não processada sai com 5. Sem `--json`, uma saída legível com saída 0. `--help` com `example`. | `apps/cli/tests/test_cut_render_command.py` chamando `wordcut_cli.main(argv)` com `wordcut_home`, `capsys`, `lock_owner` e `harmless_tasks`, no padrão de `test_sermon_process_command.py` e `test_cut_caption_command.py`. `test_cut_command.py` só ganha `render` na lista de ações. `test_cli_contract.py` continua verde. |
| 7 — Documentação | `docs/architecture/README.md` §4: a linha de Tarefas deixa de dizer que o `render` "chega com a operação"; a camada de serviço e uma peça de exportação citam `service.rendering`, `wordcut.rendering`, `RenderGateways` e a tabela `renders` (migração 0009). Há um fluxo da exportação pela CLI ou o 5.2 é ajustado. `CHANGELOG.md` em "Não lançado": `cut render` com as opções, `--estimate` e o registro da exportação. `docs/cli.md`: §8.2 diz que `render_options` são as efetivas; §8.7 e §10 dizem onde fica o `render_id` (decisão 6); o caso de vídeo ausente segue a decisão 8. Se `RenderGateways` for porta nova, há ADR com entrada no índice e README atualizado (CLAUDE.md). Os valores dos documentos batem com o código. | Leitura do diff dos documentos, conferida contra as constantes do código (CRF, pausas, fade, LUFS). Não há teste. |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Spec · Cenário "exportar com as opções padrão" (`--wait --json`, progresso no stderr, exportação registrada, seis chaves, saída 0) | Passo 6: CLI com dublês, stdout com JSON exato nas seis chaves e stderr com `[render]`. Passo 5: a linha em `renders` e o arquivo em `media/cuts/<cut_id>/`. |
| Spec · Cenário "opções salvas no corte" (`--pauses short --no-fade --resolution 720x1280` e depois sem opções) | Passo 6: as duas exportações seguidas com `options` iguais. Passo 5: o `admit` grava. Passo 1: a mescla. |
| Spec · Cenário "estimativa sem renderizar" (duração e resumo, sem tarefa, sem trava, sem salvar) | Passo 6: `--estimate --json` com `lock_owner` segurando a trava, `task list` vazio e `render_options` intacto. Passo 2: `estimate` sem mídia. Passo 5: `estimate_render` não grava. |
| Spec · Cenário "em segundo plano" (tarefa `render` `running`; `task show` traz `render_id`) | Passo 6: sem `--wait` com `harmless_tasks`, e `render_id` por `task show` de tarefa terminada em primeiro plano (decisões 6 e 12). |
| Spec · Borda: máquina ocupada → `busy` (4), sem tarefa | Passo 5 (serviço, sem tarefa e sem opções gravadas) e passo 6 (saída 4 e `task list` vazio). |
| Spec · Borda: pregação não processada → `sermon_not_processed` | Passo 5 e passo 6 (saída 5). O vídeo ausente em pregação `processed` segue a decisão 8. |
| Spec · Borda: `--caption`/`--no-caption` mudam o estado de `cut caption --on/--off` | Passo 6: `cut render --no-caption --wait` e depois `cut caption <id> --json` com `enabled: false`. Passo 4: nenhuma legenda chega ao render. |
| Spec · Borda: falha da renderização → `failed`, sem exportação, sem arquivo parcial | Passo 5: gateway dublê que escreve um arquivo parcial e levanta exceção; tarefa `failed` (`internal_error`), nenhuma linha e a pasta do corte vazia. Passo 4: o mesmo no `render_cut`. |
| Spec · Borda: corte inexistente → `not_found` | Passos 5 e 6 (saída 3), também com `--estimate`. |
| FR-001: tarefa `render` sob a trava, do estado atual do corte | Passo 5: `needs_lock`, `busy` com a trava ocupada e trechos, correções e estilo lidos na hora. Passo 4: os trechos na ordem do corte. |
| FR-002: opções de §8.7 com os padrões, salvas e reutilizadas | Passo 1 (padrões e mescla), passo 5 (gravação no `admit`) e passo 6 (reuso pela CLI). |
| FR-003: hesitações e gaguejos separados; pausas `original`, `natural` e `short` | Passo 2. |
| FR-004: emendas suavizadas ou não; fade no início e no fim ou não | Passo 3 (comandos gerados) e passo 4 (a opção chega ao gateway). |
| FR-005: áudio a −14 LUFS ou não | Passo 3: `loudnorm=I=-14` presente ou ausente. |
| FR-006: legenda com o estilo e as correções do corte, ou sem legenda | Passo 4 (correções por `word_id`, estilo, desligada) e passo 6 (o estado de `cut caption`). |
| FR-007: 1080×1920 ou 720×1280; qualidade alta ou arquivo menor | Passo 3: comando com `-s` e `-crf`, e integração real em 720×1280. |
| FR-008: exportação registrada com caminho, duração, data e opções; `cut show` lista | Passo 5 (repositório e `cut show`) e passo 6 (JSON da exportação). |
| FR-009: `--estimate` calcula a duração da timeline limpa sem renderizar | Passo 2 (`estimate`) e passo 6 (sem tarefa, sem trava e sem chamar gateway; a fixture `no_real_rendering` falharia). |
| Verificação · `cut render <id> --wait --json` (dublês) → exportação com as seis chaves | Passo 6. |
| Verificação · opções salvas e reutilizadas quando omitidas | Passos 5 e 6. |
| Verificação · `--estimate` → duração e resumo, sem tarefa, sem trava, sem salvar | Passos 2, 5 e 6. |
| Verificação · sem `--wait` → tarefa `render`; `task show` traz `render_id` | Passo 6 (decisões 6 e 12). |
| Verificação · cada opção altera o que deve (limpeza, pausas, emendas, fade, normalização, legenda, resolução, qualidade), provado por comando gerado ou timeline | Limpeza e pausas no passo 2; emendas, fade, normalização, resolução e qualidade no passo 3; legenda no passo 4. Cada opção precisa de um teste que avermelhe com a mutação dela. |
| Verificação · integração ffmpeg real (clipe sintético) → arquivo 720×1280 com a duração esperada | Passo 3: `test_render_integration.py`, sem `skipped` com o ffmpeg presente. |
| Verificação · `busy`, `sermon_not_processed`, `not_found`; falha → sem exportação e sem arquivo parcial | Passos 5 e 6, e decisões 7, 8 e 10. |
| Verificação · opções padrão → timeline idêntica à do pipeline atual | Passo 2: igualdade de `Timeline` mais `test_timeline.py`, `test_cleanup.py` e `test_assemble.py` sem alteração. `test_legacy_commands.py` continua verde (o `short` antigo usa os mesmos módulos). |
| Verificação · quality gates limpos | `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run mypy` (strict), todos verdes. |
| Decisões 1 a 16 do QA (não estão no spec) | Passos 1 a 7, como na matriz. Um teste que faltar deixa o passo PARCIAL, não FAIL, até o plano ser corrigido. |

### Divergências do plan.md com o código atual (escrito antes dos itens 11 a 14)

| Plano | Código no baseline | Ajuste recomendado |
|---|---|---|
| `render_cut` "monta o `EditList` a partir do corte", com as correções | `EditList.corrections` troca por padrão de texto (`edit/text.apply_corrections`), e `short.caption_words` a usa. As correções do item 13 são por `word_id` (`word_fixes`, `cuts.assembly`). `EditList.Segment` exige `start < end`, e `plan_timeline` escolhe as palavras pela janela de tempo. | Montar os trechos com `cuts.assembly.assemble` (posição das palavras) e aplicar as correções só ao texto da legenda, por `word_id` ou por `(start, end)` (decisão 1). Tratar o trecho de uma palavra com `start == end`. Não reaproveitar `short.caption_words` com `corrections`. |
| Legenda "liga/desliga o mesmo `enabled`" e "legendas escaladas pela largura" | O item 14 já tem `CaptionSettings.enabled`, `stored_caption` e `to_style(settings, frame_height)`, mas `to_style` só converte o `centre_y`: `size`, `outline`, `shadow_offset` e `max_width` ficam em px do quadro 1080. | Acrescentar `wordcut/cuts/caption.py` ao Contexto de código e escalar no `to_style` (decisão 15). Gravar `--caption`/`--no-caption` reaproveitando `service.cuts.update_caption` (estilo completo e `mark_edited`, decisão 3). |
| `service/cuts.py`: "`render_options` efetivas e `renders`" | `show_cut(connection, cut_id)` devolve `row.render_options or {}` e `renders: []`. `test_cuts_service.py:149/167` cravam esse comportamento provisório. `show_cut` não recebe `Home`, mas o `path` absoluto precisa dele. | Trocar pelas opções efetivas e atualizar as duas asserções (decisão 4). Montar o `path` absoluto com `Home.from_environment()` ou passar `home`, como `show_sermon(..., home=)`. |
| `db/cuts.py` não aparece no plano | `CutRow.render_options` já é lido, e `cuts.render_options` já existe na migração 0007. Não há função que grave. | Acrescentar `set_render_options(conn, cut_id, options, updated_at)` em `db/cuts.py`, sem migração para a coluna. |
| Migração `<próximo>_renders.sql` | A última é `0008_word_fixes.sql`. | `0009_renders.sql`, com `cut_id` em `ON DELETE CASCADE` (o `sermon suggest` e o reprocessamento apagam cortes). Registrar que o arquivo fica órfão nesses casos, ou apagá-lo junto (o `cut delete` é do item de administrador). |
| Estimativa "sem mídia" | `plan_timeline` precisa de `fps`, que hoje sai de `video_geometry` (ffprobe no vídeo). O banco não guarda a taxa de quadros. | Taxa nominal como constante nomeada (decisão 9) ou um `probe` em `RenderGateways`. A estimativa não pode abrir mídia. |
| `sermon_not_processed` "(vídeo ausente)" | `service.sermons.sermon_video` dá `sermon_not_processed` para o estado e `internal_error` para o arquivo ausente. | Reaproveitar `processed_row` e `sermon_video` (decisão 8) e corrigir a frase do spec. |
| "`task show` traz `render_id`" | `shown_task` expõe só `<recurso>_id` (aqui `cut_id`) e `result`. Nada no código define `render_id`. | Pôr `render_id` no `result` da tarefa (decisão 6) e dizer isso em §10. |
| Fixture autouse "como o item 5" | `no_real_processing` e `no_real_llm` ficam no `conftest.py` da raiz. A guarda da ADR-0017 só cobre a rede, e um runner `render` destacado rodaria ffmpeg e OpenCV de verdade. | Criar `no_real_rendering` no `conftest.py` da raiz. Testes sem `--wait` com `harmless_tasks` (decisão 12). |
| Passo 7 sem ADR | `RenderGateways` é uma porta nova, e o arquivo vai para o temporário e depois é movido. CLAUDE.md pede ADR para decisão de arquitetura nova. | Escrever a ADR-0018 (exportação por portas, arquivo sem parcial) ou dizer no plano por que a ADR-0014 já cobre. Atualizar o README junto. |
| Falha da renderização | `tasks.execution._execute` converte exceção inesperada em `internal_error`, e Ctrl+C em `interrupted`. Nada apaga arquivo parcial. | Limpar o temporário e a pasta de trabalho em `finally`/`BaseException` dentro do tipo `render` (decisão 7). Não criar código de erro novo sem atualizar §5.3. |

## Rodada 1 — 2026-10-26 — working tree sobre 80e64ff

**baseline_commit**: 80e64ff34df99cb5f4389d5888672e852536f2f0
**Componentes avaliados**: `packages/core`, `apps/cli`, documentação (ADR-0018, arquitetura,
README, CONTRIBUTING, CHANGELOG, docs/cli.md)
**Suítes**: Python core+cli ✅ (1168 / 0 falhas) · integração ffmpeg real
`test_render_integration.py -rs` ✅ (1 passed, 0 skipped) · `ruff check` ✅ · `ruff format
--check` ✅ (317 arquivos) · `mypy` strict ✅ (93 arquivos)
**Mutações** (cópia no scratchpad, restaurada; árvore de trabalho intocada): 18 de 20 mortas.
As 16 da matriz (incluindo as 11 do diário) morreram, e a resolução fixa avermelha a
integração tanto no pipeline quanto no reenquadramento. Sobreviveram as duas extras do QA:
D16 (`tasks/render.py:_recorded` sem o `moved.unlink`) e D8 (`_exportable` sem conferir o
arquivo do vídeo).
**Processos**: nenhum `ffmpeg`, runner ou `lock_owner` sobrando.

### Pontos do implementador

1. **`RenderGateways` com 5 métodos** (`geometry`, `energy`, `assemble`, `detect`,
   `render`): aceito. Bate com a decisão "Porta" do plan.md (orquestrador, decisão 10), com a
   ADR-0018 e com a divergência "taxa nominal ou probe" do plano de QA. O teste de ordem
   (`test_the_cut_is_assembled_then_detected_then_rendered_into_the_output`) cobra só os três
   que a matriz cita, e isso basta. Observação: o plan.md ainda traz, nas linhas 50–65, a tabela
   antiga do Contexto de código (com `RenderGateways (assemble, detect, render)` e uma linha
   `---|---|` solta), o que contradiz a linha 33 e a decisão "Porta".
2. **`--estimate --wait` → `invalid_argument` (2)**: aceito pela decisão do orquestrador.
   Está documentado em docs/cli.md §8.7 ("Com `--wait`, é `invalid_argument`.") e no
   CHANGELOG, e é coberto por `test_an_estimate_does_not_wait_for_anything_so_wait_with_it_is_refused`.
3. **Commit que falha depois do `os.replace`, sem teste**: a barra exige teste. A decisão 16
   diz "Se a gravação da linha falhar, o arquivo é apagado", e a linha "Decisões 1 a 16" da
   matriz diz que um teste que falte deixa o passo PARCIAL. A mutação D16 sobreviveu a toda a
   suíte do item (133 testes). O passo 5 fica PARCIAL. Um dublê simples cabe no próprio teste:
   trocar `wordcut.tasks.render.connect` por uma conexão cuja `commit` levante exceção, ou
   trocar `os.replace` por um que mova e depois levante. Depois, conferir que `media/cuts/<id>/`
   ficou vazia e que `renders` não tem linha.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Opções | PASS | `test_render_options.py` (5). Mutações mortas: padrão `pauses`→`short`, mescla invertida, validação de `resolution` removida. Os padrões batem com §8.7. `invalid_argument` sai com `argument` e `choices`, sem eco. `summary` tem as nove escolhas. |
| 2 — Limpeza e pausas | PASS | `test_cleanup_options.py`, `test_timeline_pauses.py` e `test_render_estimate.py`. `test_timeline.py`, `test_cleanup.py` e `test_assemble.py` não mudaram. A regressão `Timeline ==` cobre hesitação, gaguejo, pausa longa e trechos fora de ordem. Mutações mortas: `fillers` ignorada, `stammers` ignorada, `original`→`natural` e `Cleanup` com padrão `short`. A estimativa não abre mídia (30 q/s, `energy=None`). |
| 3 — Montagem e codificação | PASS | `test_render_encoding.py` (8) e `test_caption_render_style.py::test_on_a_720_by_1280_frame_the_style_shrinks_by_two_thirds`. A integração real passou (720×1280, com áudio e com a duração da timeline ±1 quadro mais a folga do AAC), sem `skipped`. Mutações mortas: CRF fixo em 18, `loudnorm` sempre ligado, fade nunca aplicado, resolução fixa no pipeline (unitário e integração) e no reenquadramento (integração). |
| 4 — Pipeline do corte | PASS | `test_render_pipeline.py` (10): ordem assemble→detect→render, correção por `word_id` só na palavra corrigida, legenda desligada, opções em cada gateway, legenda em 720 na altura do corte, progresso em ordem, câmera no salto do trecho e falha sem `output` nem pasta de trabalho. Mutações mortas: correções ignoradas, `caption` ignorado e `output` direto. A falha está provada só para o gateway `render`. Para os outros, o mesmo `finally` cobre. |
| 5 — Persistência e tarefa | PARCIAL | Decisão 16 sem teste: o ramo de `tasks/render.py:_recorded` que apaga o arquivo movido quando o commit falha não tem teste, e a mutação D16 sobrevive. O resto está verde em `test_render_task.py` (12), `test_renders_repository.py` (3) e `test_cuts_repository.py::…set_render_options…`. Mutações mortas: opções antes da trava, linha antes do render e estimate gravando. Lacuna menor, da decisão 8: não há teste de `cut render` com pregação `processed` sem o arquivo do vídeo. O código reaproveita `sermon_video`, testado em `sermon download`. A mutação D8 sobrevive, mas o código de saída continuaria `internal_error`. |
| 6 — CLI | PASS | `apps/cli/tests/test_cut_render_command.py` (20) e `test_cut_command.py` (só `render` na lista). Cobertos: seis chaves com `path` absoluto e existente, `[render]` só no stderr, reuso das opções, `--estimate` com a trava ocupada sem tarefa e sem gravar (inclusive `--no-caption`), tarefa `running` com `harmless_tasks`, `result.render_id` no `task show`, `--no-caption` persistente, recusas 2, 3, 4 e 5 sem eco, saída legível e `--help` com exemplo. |
| 7 — Documentação | PASS | ADR-0018 está no índice, no README, no CONTRIBUTING e na arquitetura (§4: Tarefas com `render`, camada de serviço, linha "Exportação do corte", fluxo 5.2 pela CLI). CHANGELOG atualizado. docs/cli.md atualizado em §8.2, §8.7 (pausas, CRF, fade, normalização, `render_id`, vídeo ausente, `--estimate --wait`), §10 e §14. A frase do spec foi corrigida. Os valores conferem com o código: CRF 18/26, pausas 0,15/0,40 e 0,08/0,20, fade 0,5 s, −14 LUFS e 30 q/s. |

### Política de comentários (CONTRIBUTING §5)

- ❌ `packages/core/src/wordcut/cuts/caption.py:20–23`: a constante nova
  `REFERENCE_FRAME_HEIGHT`, com o comentário dela, entrou entre o comentário "The height of
  each position…" e `POSITIONS`. Agora esse comentário descreve a linha errada.
- ⚠️ `packages/core/src/wordcut/rendering/pipeline.py:26`: a referência aponta para
  `specs/1.1.h.1-cut-render`. O §5.5 pede uma ADR ou `docs/`, e docs/cli.md §8.7 já traz
  "`high` é CRF 18, `small` é CRF 26".
- Os demais comentários novos estão nos tipos da política: intenção, referência, formato e
  contrato. Os dois marcadores provisórios de `service/cuts.py` foram removidos.

Esses desvios não fazem parte da matriz por passo e não mudam o veredito de nenhum passo. Eles
ficam como checagem pendente, junto com a reabertura do passo 5.

### Critérios de aceite

- ✅ Cenário: exportar com as opções padrão. `test_render_with_wait_prints_the_export_and_the_stages_on_stderr` e `test_an_export_in_the_foreground_is_recorded_with_its_file_named_after_it`.
- ✅ Cenário: opções salvas no corte. `test_options_given_once_are_saved_and_the_next_render_without_options_repeats_them` e `test_a_second_export_without_options_repeats_the_options_of_the_first`.
- ✅ Cenário: estimativa sem renderizar. `test_an_estimate_saves_nothing_creates_no_task_and_does_not_wait_for_the_lock` e `test_an_estimate_gives_duration_and_options_saving_nothing_even_busy_and_without_video`.
- ✅ Cenário: em segundo plano. `test_render_without_wait_answers_the_running_render_task` e `test_task_show_of_a_finished_render_carries_the_render_id`.
- ✅ Borda `busy` (4), sem tarefa. `test_with_the_machine_busy_render_exits_4_and_creates_no_task` e `test_with_the_machine_busy_the_export_is_refused_without_a_task_and_saves_nothing`.
- ✅ Borda `sermon_not_processed`. `test_a_cut_of_a_sermon_not_processed_exits_5` e `test_a_cut_of_a_sermon_being_processed_again_is_refused_as_not_processed`. O vídeo ausente, que dá `internal_error`, não tem teste de render (passo 5).
- ✅ Borda `--caption`/`--no-caption`. `test_render_without_caption_leaves_the_cut_caption_off` e `test_an_export_without_caption_turns_the_cut_s_caption_off_as_cut_caption_off_does`.
- ✅ Borda: falha sem exportação e sem arquivo parcial. `test_a_failed_export_fails_the_task_and_leaves_no_export_and_no_file`, `test_an_interrupted_export_is_failed_as_interrupted_and_leaves_no_file` e `test_a_failed_render_raises_and_leaves_neither_the_output_nor_the_work_folder`. Falta o caminho do commit que falha (decisão 16).
- ✅ Borda `not_found`. `test_a_cut_that_does_not_exist_exits_3[render|estimate]` e `test_a_cut_that_does_not_exist_is_not_found_even_with_the_machine_busy`.
- ✅ FR-001. `test_render_is_a_builtin_kind_that_holds_the_processing_lock`, os testes de `busy` e `test_the_camera_jumps_where_the_next_segment_starts_and_plays_in_the_cut_s_order`.
- ✅ FR-002. `test_render_options.py` e os testes de reuso das opções.
- ✅ FR-003. `test_cleanup_options.py` e `test_timeline_pauses.py`.
- ✅ FR-004. `test_joins_without_smoothing_have_no_audio_fade`, `test_a_fade_takes_half_a_second_in_and_out_of_video_and_audio` e `test_the_options_reach_the_montage_and_the_encode`.
- ✅ FR-005. `test_without_normalization_the_audio_is_only_resampled` e `test_normalization_brings_the_audio_to_minus_14_lufs`.
- ✅ FR-006. `test_the_captions_carry_the_fix_of_one_word_and_not_of_another_spelled_the_same` e `test_with_the_caption_off_no_caption_reaches_the_render`.
- ✅ FR-007. `test_the_encoder_takes_frames_in_the_chosen_resolution`, `test_a_smaller_file_is_encoded_with_a_higher_crf` e a integração em 720×1280.
- ✅ FR-008. `test_renders_repository.py` e `test_cut_show_lists_the_exports_and_the_options_the_next_one_uses`.
- ✅ FR-009. `test_render_estimate.py` e o `--estimate` da CLI com a trava ocupada.
- ✅ Verificação: opções padrão dão a timeline atual. `test_the_default_cleanup_plans_the_same_timeline_as_before_the_options`. Os testes de timeline, limpeza e montagem não mudaram, e `short.caption_words` delega a `edit.screen`.
- ✅ Verificação: quality gates limpos (pytest, ruff, format e mypy).
- ❌ Decisão 16 do QA (commit que falha depois do `os.replace`, arquivo apagado): sem cobertura. A mutação D16 sobrevive.

### Veredito geral: PARCIAL

O passo 5 está PARCIAL: o ramo da decisão 16 não tem teste. Os outros seis passos passam, as
suítes e as checagens estão verdes e as 16 mutações da matriz morreram. Ficam pendentes dois
desvios da política de comentários (`cuts/caption.py:20–23` e `rendering/pipeline.py:26`).

## Rodada 2 — 2026-10-26 — working tree sobre 80e64ff

**baseline_commit**: 80e64ff34df99cb5f4389d5888672e852536f2f0
**Componentes avaliados**: `packages/core`, `apps/cli`, `specs/1.1.h.1-cut-render/plan.md`
**Suítes**: Python core+cli ✅ (1170 / 0 falhas) · integração ffmpeg real
`test_render_integration.py -rs` ✅ (1 passed, 0 skipped) · `ruff check` ✅ · `ruff format
--check` ✅ (317 arquivos) · `mypy` strict ✅ (93 arquivos)
**Mutações** (cópia no scratchpad, restaurada e apagada; árvore de trabalho intocada): 5 de 5
mortas. D16 (`tasks/render.py:_recorded` sem o `moved.unlink`) avermelha
`test_an_export_whose_record_is_not_committed_leaves_no_file`. D8
(`service/rendering.py:_exportable` só com `processed_row`) avermelha
`test_a_cut_whose_processed_sermon_lost_its_video_is_refused_as_an_internal_error`. As três da
matriz do passo 5 continuam vermelhas: opções antes da trava (1 teste), `estimate` gravando
(2) e linha antes do render (3).
**Processos**: nenhum `ffmpeg`, runner, `pytest` ou `lock_owner` sobrando.

### Escopo desta rodada

O passo 5 foi reaberto na Rodada 1. Os passos 1, 2, 3, 4, 6 e 7 mantêm o PASS da Rodada 1.
A suíte inteira e as checagens estáticas continuam verdes, e o diff desses passos não mudou.
Esta rodada também confere os dois comentários fora da política e a tabela antiga do plan.md.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Opções | PASS | Mantido da Rodada 1. Suíte verde. |
| 2 — Limpeza e pausas | PASS | Mantido da Rodada 1. Suíte verde. |
| 3 — Montagem e codificação | PASS | Mantido da Rodada 1. A integração real passou sem `skipped`. |
| 4 — Pipeline do corte | PASS | Mantido da Rodada 1. Suíte verde. |
| 5 — Persistência e tarefa | PASS | `test_render_task.py` tem 14 testes. D16: `test_an_export_whose_record_is_not_committed_leaves_no_file` usa uma conexão cujo `__exit__` desfaz a transação e levanta `OperationalError` depois do `os.replace`. Ele confere `internal_error`, nenhuma linha em `renders` e `media/cuts/<id>/` vazia. D8: `test_a_cut_whose_processed_sermon_lost_its_video_is_refused_as_an_internal_error` confere `internal_error`, nenhuma tarefa, nenhuma linha e nenhum arquivo. As duas mutações ficaram vermelhas. |
| 6 — CLI | PASS | Mantido da Rodada 1. Suíte verde. |
| 7 — Documentação | PASS | Mantido da Rodada 1. Suíte verde. |

### Política de comentários e plan.md

- ✅ `packages/core/src/wordcut/cuts/caption.py:18–22`: `REFERENCE_FRAME_HEIGHT` fica acima do
  comentário "The height of each position…", e esse comentário volta a descrever
  `POSITIONS`. A referência a docs/cli.md §8.6 confere, porque a linha 537 diz "no quadro
  1080×1920".
- ✅ `packages/core/src/wordcut/rendering/pipeline.py:26`: `QUALITY_CRF` cita docs/cli.md §8.7.
  Nenhum comentário de `packages/*/src` ou `apps/*/src` aponta para `specs/`.
- ✅ `plan.md`: a tabela antiga saiu, e a linha `---|---|` solta também. O Contexto de código
  tem uma tabela só, e ela traz `RenderGateways (geometry, energy, assemble, detect,
  render)`, de acordo com a decisão "Porta".

### Critérios de aceite

- ✅ Os critérios da Rodada 1 continuam cobertos pelos mesmos testes, todos verdes.
- ✅ Borda `sermon_not_processed`, vídeo ausente (decisão 8):
  `test_a_cut_whose_processed_sermon_lost_its_video_is_refused_as_an_internal_error`.
- ✅ Borda: falha sem exportação e sem arquivo parcial, no commit depois do `os.replace`
  (decisão 16): `test_an_export_whose_record_is_not_committed_leaves_no_file`.
- ✅ Decisão 16 do QA, que estava descoberta na Rodada 1, agora tem cobertura. A mutação D16
  morre.

### Veredito geral: PASS

Os sete passos passam. Os critérios e as decisões 1 a 16 têm cobertura. As suítes, a
integração sem `skipped` e as checagens estáticas estão verdes. As 16 mutações da matriz e
as extras D16 e D8 morrem. Os dois desvios de comentário e a tabela antiga do plan.md foram
corrigidos.
