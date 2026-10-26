# Changelog

Formato de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões em
[SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado

- Especificação da CLI `wordcut` (`docs/cli.md`).
- ADRs (`docs/adr/`), documentos de arquitetura (`docs/architecture/`), `CONTRIBUTING.md`.
- Esqueleto da API (`apps/api`, FastAPI) com `GET /api/health`.
- Esqueleto da web (`apps/web`, React + Vite + TypeScript) que mostra o estado da API.
- `compose.yaml` com os serviços `api`, `web` e `cli`, portas só em `127.0.0.1`, dados em
  `WORDCUT_HOME` e segredos montados só para leitura.
- Base da CLI nova: contrato de saída e erros (`--json`, `--quiet`, códigos de saída;
  ADR-0012), banco SQLite com migrações em `WORDCUT_HOME`, trava global de processamento e
  `wordcut status`.
- `wordcut sermon create <link>`, `sermon list [--status]` e `sermon show <id>`: a pregação
  passa a existir no banco (tabela `sermons`, migração 0002) a partir do link da live, com o
  mesmo vídeo devolvendo a pregação existente e aviso no stderr para live ainda no ar.
- `wordcut sermon trim <id> --start T --end T` e `--start/--end` no `sermon create`: grava as
  bordas da pregação em tempo da live (mínimo de 1 minuto, dentro da live), leva a pregação a
  `delimitada` e, numa pregação já processada, mantém o estado e avisa que reprocessar exige
  `sermon process --force`. `sermon list` e `sermon show` passam a trazer a duração da
  pregação.
- Tarefas (`docs/cli.md` §6; ADR-0013): tabela `tasks` (migração 0003), execução em primeiro
  plano ou em processo destacado em sessão própria que herda a trava, progresso no banco e
  saída do processo em `tasks/<id>.log`. `wordcut task list [--status] [--kind]`,
  `task show <id>` e `task wait <id>` (progresso no stderr, resultado no stdout, saída da
  tarefa; Ctrl+C só para a espera). Os comandos que lançam tarefa ganham `--wait`, que roda
  em primeiro plano e sai com 130 no Ctrl+C. `wordcut status` traz o `task_id` do dono da
  trava e as tarefas em andamento, e o `busy` traz o `task_id` nos `details`.
- Código de erro `interrupted` (saída 1): tarefa interrompida por Ctrl+C ou cujo processo
  morreu; uma tarefa `running` sem processo vivo vira `failed` na próxima leitura.
- `wordcut sermon process <id> [--force] [--wait]` (tarefa `process`, com trava; ADR-0014):
  baixa só a faixa delimitada (com 30 s de margem) e uma janela curta de áudio para a
  sincronia, transcreve, ajusta as bordas à primeira e à última palavra, corta em 16:9 com
  fades em `media/sermons/<id>/sermon.mp4` e grava palavras e frases em tempo da pregação
  (migração 0004: tabelas `words` e `sentences`; `sermon_start`, `sermon_end`, `video_path` e
  `processed_at` na pregação). A pregação fica `processing` desde o lançamento e termina
  `processed` ou `failed`; `failed` é refeita pelo mesmo comando, e uma pregação processada
  exige `--force` (`would_discard_edits`). Progresso no stderr por etapa.
- `sermon create … --start T --end T --process [--wait]`: cria, delimita e processa num
  comando.
- `sermon show <id> --transcript`: as frases da pregação, com ID, tempo e IDs da primeira e
  da última palavra. `sermon show` passa a trazer `sermon_start`, `sermon_end`,
  `processed_at` e a última tarefa (`last_task`); `show` e `list` deixam `failed` a pregação
  `processing` cujo processo morreu.
- Códigos de erro `transcription_error` (saída 6) e `processing_error` (saída 1).
- `wordcut sermon download <id> [-o caminho]`: copia o vídeo 16:9 da pregação processada
  para o caminho indicado ou, sem `-o`, para a pasta atual com o nome legível
  `AAAA-MM-DD - Título.mp4`; `-o` com uma pasta existente (ou terminado em `/`) grava o
  nome legível dentro dela. Nunca sobrescreve: um destino ocupado ganha ` (2)`, ` (3)`…
  antes da extensão, e o nome final só aparece com a cópia completa. Devolve `path`
  (absoluto) e `bytes`; não toma a trava de processamento. Pregação não processada falha
  com `sermon_not_processed`.
- `wordcut settings show`, `settings set [--model] [--whisper-model]`, `settings set-key` e
  `settings set-cookies` (administrador): modelos do LLM e do WhisperX no banco (tabela
  `settings`, migração 0005; o do LLM começa sem valor, o do WhisperX em `large-v3`); a chave
  do LLM e os cookies do YouTube lidos só do stdin (a chave sem eco no terminal; os cookies,
  só redirecionados, no formato Netscape) e gravados de uma vez em `WORDCUT_CONFIG` com
  permissão 600. O `show` traz a chave só mascarada (`••••` e os 4 últimos caracteres) e os
  cookies só como presentes ou ausentes; argumento a mais nesses comandos é recusado sem
  ecoar o valor. Código de erro `config_not_writable` (saída 5) para a pasta sem escrita.
- `wordcut criteria list` (administrador): os 8 filtros e os 3 valores da sugestão, com ID,
  nome, tipo e nível padrão, sem o texto do prompt. Os textos ficam em
  `packages/core/src/wordcut/criteria/texts/` (prompt base, um arquivo por critério com os
  três níveis e os textos das opções de edição), carregados e validados por
  `wordcut.criteria`. O conteúdo foi tirado literalmente de
  `skills/video-corte-vertical/sugerir-cortes.md` e das frases de nível do protótipo, e
  **precisa de revisão humana por pessoa qualificada antes de valer** (constituição §I).
- `wordcut preset list`, `show`, `create <nome> [--from]`, `update`, `set-default` e
  `delete` (administrador): presets no banco (tabela `presets`, migração 0006) com o nível
  de cada critério, as durações permitida e ideal, reordenar, palavras protegidas e
  instruções adicionais (até 4000 caracteres, de arquivo ou do stdin). Instalação nova traz
  o preset "Padrão"; sempre há exatamente um padrão, que não pode ser apagado
  (`default_preset`, saída 5). Critério novo no código entra com o nível padrão e critério
  removido é ignorado na leitura. O serviço monta o prompt de um preset para a sugestão
  (item 9).
- Sugestão de cortes pelo LLM ao fim do `sermon process` (item 2.1.b.1; ADR-0016): uma
  chamada ao OpenRouter com o prompt do preset padrão e as frases numeradas, sem tempos;
  resposta validada por esquema JSON, com uma nova tentativa só quando fora do esquema; os
  cortes válidos ficam `suggested`, com título, trechos, faixa contínua e o preset usado
  (tabela `cuts`, migração 0007). Corte cuja duração estimada (soma dos trechos ×0,82) sai
  da duração permitida do preset é descartado, com aviso em `suggestion_warnings` no
  resultado da tarefa. A falha da sugestão não desfaz o processamento: a tarefa termina
  `succeeded`, a pregação `processed`, e o erro fica em `suggestion_error` no
  `sermon show` (e numa linha do `show` legível). Nova etapa `sugerindo` no progresso.
  Código de erro `llm_not_configured` (saída 5) para modelo ou chave ausentes, sem chamar o
  LLM; toda falha do OpenRouter vira `llm_error`, sem a chave, o prompt nem o corpo da
  resposta.
- `wordcut sermon suggest <id> [--preset <id>] [--wait]` (administrador; tarefa `suggest`,
  sem a trava de processamento; item 2.1.b.2): pede nova sugestão de cortes de uma pregação
  processada, com o preset indicado ou o padrão, e, só no sucesso e numa transação, troca os
  cortes `suggested` não editados pelos novos; escolhidos, descartados e editados ficam. O
  resultado traz `sermon_id`, `preset_id`, `suggested_cuts` (como no `sermon show`) e
  `suggestion_warnings`; etapa `sugerindo` no progresso. Recusa sem criar tarefa a pregação
  inexistente ou o preset inexistente (`not_found`), a não processada
  (`sermon_not_processed`), o LLM sem modelo ou chave (`llm_not_configured`, sem tocar em
  `suggestion_error`) e uma segunda sugestão da mesma pregação enquanto outra roda (`busy`,
  com a tarefa nos `details`). A falha do LLM deixa a tarefa `failed` com `llm_error`, os
  cortes como estavam e o erro em `suggestion_error`; uma pregação reprocessada durante a
  sugestão faz a tarefa falhar com `sermon_not_processed`, sem gravar nada.
- Guarda da suíte de testes contra a rede real (ADR-0017): com `WORDCUT_FORBID_NETWORK`
  definida, que o `conftest.py` da raiz define e a tarefa destacada herda, a montagem do LLM
  real e do processamento real recusa com `network_error`.
- `wordcut cut list --sermon <id> [--status S]`, `cut show <id>`, `cut choose <id>`,
  `cut discard <id>` e `cut restore <id>` (item 1.1.e.1): o `list` traz cada corte com o
  texto montado (as palavras de cada trecho, na ordem em que o corte toca) e a duração (soma
  das faixas dos trechos, sem a estimativa de limpeza), com os descartados por último; o
  `show` traz também os trechos com tempos e texto, as palavras (`word_id`, texto, tempos e
  `corrected`, sempre `null` até a correção de grafia), `caption` e `render_options` (`{}`
  enquanto valem os padrões) e `renders: []`. `choose`, `discard` e `restore` mudam só o
  estado e devolvem o corte como o `show`; `restore` só tira um corte de `discarded`, e
  repetir uma transição não grava nada. Corte ou pregação inexistente dá `not_found`.

### Alterado

- O comando `cut` da CLI anterior passa a se chamar `cut-sermon`, com os mesmos argumentos e
  a mesma saída, porque `cut` é agora o grupo dos cortes; sai junto com a CLI anterior
  (roadmap, item 18).
- `sermon process` transcreve com o modelo do WhisperX das configurações
  (`settings set --whisper-model`), não mais com `large-v3` fixo.
- `settings show` traz o ID do preset padrão em `default_preset_id` (antes sempre `null`).
- `sermon list` e `sermon show` trazem as contagens de cortes por estado reais, e o `show`, os
  cortes e `suggestion_error`. `sermon process --force` apaga os cortes da pregação junto
  com as palavras e as frases.
- Erro de uso da CLI não repete o valor digitado (ADR-0015): escolha inválida lista as
  opções válidas (`details.choices`), argumento não reconhecido nunca é repetido, nem como
  nome de opção (a mensagem aponta para o `--help` do comando), e valor de tipo inválido
  nomeia só a opção, como o parser a define.
- `overview` passa a quebrar as frases com o mesmo módulo do processamento
  (`wordcut.processing.sentences`), sem mudar a saída.
- Tempos (`T`) aceitam só dígitos: minutos e segundos depois do primeiro componente ficam
  abaixo de 60, e valores como `inf`, `nan`, `1e3` ou negativos são recusados.
- O projeto passa a se chamar Wordcut; executável `wordcut`, pacote `wordcut`.
- Organização em monorepo orquestrado por Docker Compose (ADR-0002, ADR-0003): domínio em
  `packages/core`, CLI em `apps/cli`, workspace `uv` com lock único na raiz.
- Os cookies do YouTube vêm da pasta de segredos (`WORDCUT_CONFIG`, ou `~/.config/wordcut`),
  resolvida a cada uso; falhas do YouTube (inclusive cookies ausentes) viram `youtube_error`
  (saída 6), com mensagem sem o comando do `yt-dlp` nem o caminho dos cookies.
