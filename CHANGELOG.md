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
- `wordcut cut preview <id>` (item 1.1.g.1): a sequência que a prévia toca, sem tocar vídeo,
  sem renderizar e sem esperar a trava. Cada trecho na ordem em que o corte toca, com início
  e fim em tempo da pregação, o texto (sem correção de grafia até o item 1.1.f.2) e
  `out_of_order`, verdadeiro no trecho que começa antes do fim do trecho anterior; mais
  `cut_id` e a duração do `cut show`. Sem `--json`, uma linha por trecho com `↑` no que
  volta no tempo. Corte inexistente dá `not_found`.
- `wordcut cut fix-word <id> <word_id> <texto>` (item 1.1.f.2): corrige a grafia de uma
  palavra da legenda, só naquele corte (tabela `word_fixes`, migração 0008, com as duas
  chaves estrangeiras em `ON DELETE CASCADE`). A trava de grafia (`wordcut.cuts.spelling`,
  item 1.1.f.3) compara sempre com a palavra original o núcleo das duas (minúsculas, só
  letras, números e hífen) e aceita distância de Levenshtein até
  `max(1, floor(0,34 × tamanho do núcleo original))`; acima disso, `spelling_too_different`
  (saída 5) com `details.distance`, `details.limit` e `details.original`, e nada muda. O
  texto original remove a correção. Texto vazio ou com mais de uma palavra e palavra fora
  dos trechos do corte dão `invalid_argument` (`details.argument` `text` ou `word_id`), sem
  repetir o texto digitado. Devolve a palavra como o `cut show` a dá, mais `cut_id`; a
  correção marca o corte como editado, e o `sermon suggest` o mantém. `cut list`, `cut show`
  (`text`, `segments[].text` e `words[].corrected`) e `cut preview` passam a trazer as
  correções; `words[].text` segue com o original.
- `wordcut cut caption <id> [opções]` (item 1.1.f.4): mostra ou altera o estilo da legenda do
  corte, que vale para todas as legendas dele. Opções `--font` (fontes do pacote, pelo nome
  dos metadados do arquivo), `--size` (24–160 px), `--color` e `--border-color`
  (`#RRGGBB`, gravadas em maiúsculas), `--position top|center|bottom` (20, 50 e 78 % da
  altura do quadro, como no protótipo), `--offset` (10–90 %, vence `--position`; sozinho
  mantém o `position`), `--border` (0–12 px), `--shadow none|soft|strong`, `--on`/`--off` e
  `--reset`. O padrão é o estilo da igreja (Open Sans Bold, 60 px, `#FFD600`, centro,
  contorno preto de 3 px, sombra suave). O estilo fica em JSON no corte (`NULL` é o padrão,
  que o `--reset` volta a gravar); um estilo gravado incompleto é completado pelo padrão.
  Alterar ou restaurar marca o corte como editado. Valor fora da faixa ou da forma,
  `--on --off` e `--reset` com outra opção dão `invalid_argument` e nada muda; fonte
  inexistente traz as fontes em `details.choices`.
- Desenho da legenda (`CaptionStyle`/`CaptionRenderer`) com cor do contorno, sombra em três
  níveis (nenhuma, suave com alpha 140, forte com alpha 220), arquivo da fonte e altura do
  quadro; a imagem encosta na borda em vez de sair do quadro. O estilo padrão desenha igual
  ao de antes, pixel a pixel.
- `wordcut cut render <id> [opções] [--estimate] [--wait]` (item 1.1.h.1; ADR-0018): tarefa
  `render`, com trava, que exporta o corte em 9:16 do estado atual (trechos na ordem do corte,
  correções de grafia só na legenda, estilo da legenda). Opções `--fillers` e `--stammers`
  (`remove|keep`), `--pauses original|natural|short` (sem encurtar, 0,15/0,40 s ou
  0,08/0,20 s), `--[no-]smooth-joins` (fade de 15 ms nas emendas), `--[no-]fade` (0,5 s de
  vídeo e áudio no início e no fim, até a metade da duração), `--[no-]normalize` (−14 LUFS),
  `--[no-]caption` (o mesmo estado de `cut caption --on/--off`), `--resolution
  1080x1920|720x1280` (legenda escalada junto) e `--quality high|small` (CRF 18 ou 26). As
  opções ficam salvas no corte ao iniciar, sob a trava, e a omitida usa a última salva.
  `--estimate` devolve a duração estimada e o resumo das opções sem renderizar, sem salvar e
  sem a trava; com `--wait`, é erro de uso. Com `--wait`, devolve a exportação
  `{id, cut_id, path, duration, created_at, options}`; sem ele, a tarefa, e o `task show`
  traz `result.render_id`. A exportação fica na tabela `renders` (migração 0009) e o arquivo
  em `media/cuts/<cut_id>/<render_id>.mp4`; uma falha ou um Ctrl+C não deixam linha nem
  arquivo.
- `wordcut render list --cut <id>`, `render show <id>` e `render download <id> [-o caminho]`
  (item 1.1.i.1): o `list` traz `{"items": [...]}` com as exportações do corte, da mais
  recente para a mais antiga (no mesmo segundo, a gravada por último primeiro), cada uma como
  o `show` a dá: `{id, cut_id, path, duration, created_at, options}`, com `path` absoluto e as
  opções como foram gravadas. O `show` não abre o arquivo. O `download` copia o vídeo da
  exportação com as regras do `sermon download` (`-o` com arquivo ou pasta, sem
  sobrescrever, ` (2)`, ` (3)`…) e o nome legível `AAAA-MM-DD - Título do corte.mp4`, com a
  data do culto da pregação do corte; devolve `path` (absoluto) e `bytes`. Corte ou
  exportação inexistente dá `not_found`; arquivo da exportação ausente no disco,
  `internal_error` com `details.render_id`, sem caminho interno. Nenhum dos três toma a trava
  de processamento.
- `wordcut member list`, `member add <email> --role assistant|admin`,
  `member set-role <email> assistant|admin` e `member remove <email>` (administrador; item
  1.2.a.1): a equipe na tabela `members` (migração 0010), que guarda, de dado pessoal, só o
  e-mail, em minúsculas e sem os espaços das pontas, com o papel e as datas de inclusão e de
  alteração (LGPD). O `list` traz `{"items": [...]}` em ordem de e-mail, cada membro como
  `{email, role, created_at, updated_at}`; `add` e `set-role` devolvem o membro; `remove`
  devolve `{"email", "removed": true}`. Remover ou rebaixar o último administrador dá
  `last_admin` (saída 5), com a checagem e a gravação na mesma transação de escrita, para a
  CLI e a API não zerarem os administradores ao mesmo tempo; `set-role` para o papel que o
  membro já tem não muda nada. E-mail inválido ou já na equipe e papel fora de
  `assistant|admin` dão `invalid_argument`; e-mail fora da equipe, `not_found`; nenhum erro
  repete o e-mail. `service.members.role_of` dá o papel de um e-mail, ou `None`, para a API.
- Identidade e papéis na API (item 1.2.a.2; ADR-0019): a API valida o JWT do Cloudflare
  Access (`Cf-Access-Jwt-Assertion`, RS256, `aud`, `iss`, `exp` e `email`) contra as chaves
  do time, em cache de 10 minutos e buscadas de novo em `kid` desconhecido, e dá o papel por
  `members.role_of`. `GET /api/me` devolve `{"email", "role"}`. Configuração por
  `WORDCUT_ACCESS_TEAM_DOMAIN` e `WORDCUT_ACCESS_AUD`, repassadas à `api` pelo Compose;
  `WORDCUT_DEV_EMAIL` fixa o e-mail só sem o Access e avisa no log; Access configurado pela
  metade recusa subir. Os erros da API usam o objeto de erro da CLI com o status da saída
  (400, 404, 409, 502, 500), `unauthenticated` 401 e `forbidden` 403, códigos novos com
  saída 1 que só a API produz; erro inesperado dá 500 `internal_error` sem o texto da
  exceção. Nenhum token ou e-mail aparece em erro ou log. Dependência nova: `pyjwt[crypto]`.
- Rotas da API para pregações, tarefas e estado (item 20a; ADR-0020; `docs/api.md`):
  `POST /api/sermons {"url"}` (201, ou 200 com `created: false`), `GET /api/sermons
  [?status=]`, `GET /api/sermons/{id}[?transcript=true]`, `PATCH /api/sermons/{id}
  {"start", "end"}`, `POST /api/sermons/{id}/process {"force"}` e
  `POST /api/sermons/{id}/suggest {"preset_id"}` (só administrador), as duas com 202 e a
  tarefa lançada em processo destacado, `GET /api/sermons/{id}/video` (anexo com o nome
  `AAAA-MM-DD - Título.mp4`), `GET /api/tasks[?status=&kind=]`, `GET /api/tasks/{id}` e
  `GET /api/status`, com o mesmo JSON da CLI. `GET /api/tasks/{id}/events` acompanha a
  tarefa por SSE (`progress`, `done`, `failed`, com a tarefa no `data`, e `: ping` a cada
  15 s), lendo o banco a cada 0,5 s. Requisição malformada dá 400 `invalid_argument` sem
  repetir o valor enviado, com `details.choices` nos filtros; rota inexistente, 404
  `not_found`. O esquema OpenAPI fica em `/api/docs` só em desenvolvimento.
- Rotas da API para cortes, exportações, configurações, critérios, presets e equipe (item 20b,
  ADR-0021; `docs/api.md`): listar, detalhar, prever, escolher, descartar e restaurar cortes,
  corrigir a grafia de uma palavra, ver, alterar e restaurar o estilo da legenda, exportar
  (202) e estimar a exportação, listar, detalhar e baixar exportações com nome legível; ver e
  trocar os modelos, gravar a chave do LLM e os cookies pelo corpo, sem nunca devolvê-los;
  critérios, presets e equipe, só para o administrador, com o e-mail só no corpo. Toda rota de
  negócio passa pela identidade num só lugar (`routes.ROUTERS`), as exportações saem sem o
  caminho local, os corpos são estritos e um campo desconhecido dá 400 sem repetir o nome.
- Interface web (item 21, ADR-0022): rotas dos três níveis e das configurações pelo React
  Router, cliente da API tipado com erro único (inclusive API fora do ar), identidade por
  `GET /api/me` com tela própria para 401 e 403, caminho no topo com navegação por clique,
  lista de pregações com data, título, estado e duração, estado vazio, diálogo "Nova
  pregação" com aviso de live no ar e motivo junto ao campo, barra de status atualizada a
  cada 3 s, configurações em tela inteira só para o administrador e indicador "Salvo". O
  visual segue o protótipo, com as fontes Geist empacotadas no build.
- Nível 2 da web (item 22, ADR-0023): prévia 16:9 e timeline sempre visíveis numa pregação.
  A prévia é o embed do YouTube (`youtube-nocookie.com`) antes do processamento e fora do
  trecho processado, e o vídeo da API dentro dele, com o tempo da live convertido. A timeline
  mostra a régua em tempo da live, a live esmaecida e o clipe entre as bordas, sem miniaturas
  nem forma de onda (a API ainda não as serve). As bordas mudam por arraste, com o quadro da
  borda na prévia, e por I e O no cursor, com mínimo de 1 min; o arraste salva ao soltar e
  I/O depois de 500 ms, com "Salvo" só depois da resposta e o motivo do erro junto à
  timeline. Processar fica no lugar de Exportar, com o progresso no botão pelos eventos SSE
  (o fluxo fecha no fim e ao sair da tela), a tarefa em andamento retomada ao abrir a página,
  o motivo da falha, a máquina ocupada e a live no ar. Reprocessar aparece numa pregação
  processada depois de salvar bordas novas na sessão, com o aviso de que as edições dos cortes
  se perdem.
- Painel de cortes no nível 2 da web (item 23): painel lateral com um card por corte (número,
  título, texto montado, duração e estado), na ordem do serviço, com os descartados por
  último. Um clique abre o corte: o sugerido é marcado escolhido e o nível 3 abre depois da
  resposta da API; o descartado não abre. "Mais ações" descarta ou restaura e pede a lista de
  novo. O painel diz por que a pregação não tem cortes (`suggestion_error`) e que os cortes
  aparecem depois do processamento, e recarrega quando o processamento termina. Cada corte
  vira uma camada da timeline, acima de "Vídeo", em tempo da live e só para leitura, com a
  mesma cor do card. Em telas estreitas o painel fica abaixo da timeline.
- Nível 3 da web (item 24): a tela do corte. A prévia 9:16 sem renderizar toca o vídeo
  processado da pregação (nunca o YouTube; ADR-0023) de trecho em trecho, na ordem do corte e
  pulando os intervalos, inclusive com trechos fora de ordem, recortada ao centro do quadro, e
  não espera a trava de processamento. A legenda é desenhada pelo navegador por cima, em
  blocos como os da exportação, com a palavra falada marcada e o estilo do corte (fonte Open
  Sans 700 empacotada no build). A timeline mostra só o corte, em tempo do corte, com as
  camadas Legenda e Vídeo. O painel tem as abas Texto (o texto montado, com as correções) e
  Legenda (formulário em linhas: Legenda, Fonte, Tamanho, Cor, Posição, Altura, Borda, Cor da
  borda e Sombra), que abre pela camada Legenda e volta a Texto ao fechar ou clicar fora;
  cada campo salva sozinho 400 ms depois da mudança, só com o campo mudado, com "Salvo" e o
  motivo junto ao campo, e "Restaurar padrão" volta ao estilo da igreja. Clique duplo numa
  palavra da legenda pausa e abre a correção de grafia no lugar: Enter ou sair salva, Esc
  cancela, e o bloqueio da trava aparece junto à legenda sem repetir o texto digitado. A aba
  Legenda lista as correções de grafia, cada uma com Desfazer.

### Alterado

- `cut list` e `GET /api/sermons/{id}/cuts` trazem em cada corte `start` e `end`: o menor
  início e o maior fim dos trechos, em tempo da pregação, ao milissegundo.

- A web deixa de ser o esqueleto que mostrava só o estado da API (`fetchHealth`) e passa a
  ser a interface do item 21.
- `cut show` traz em `render_options` as opções efetivas da próxima exportação (padrões mais
  as salvas, com `caption` igual ao estado da legenda), não mais o JSON gravado ou `{}`, e em
  `renders` as exportações do corte, da mais antiga para a mais nova, com `path` absoluto.
- O `path` das exportações (`cut show`, `cut render --wait`, `render list` e `render show`) é
  absoluto mesmo com `WORDCUT_HOME` relativo.
- `cut show` traz em `caption` o estilo efetivo da legenda (o padrão completo quando o corte
  não tem estilo), não mais `{}`.
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
- Tempos (`T`) aceitam só dígitos: minutos e segundos depois do primeiro componente ficam
  abaixo de 60, e valores como `inf`, `nan`, `1e3` ou negativos são recusados.
- O projeto passa a se chamar Wordcut; executável `wordcut`, pacote `wordcut`.
- Organização em monorepo orquestrado por Docker Compose (ADR-0002, ADR-0003): domínio em
  `packages/core`, CLI em `apps/cli`, workspace `uv` com lock único na raiz.
- Os cookies do YouTube vêm da pasta de segredos (`WORDCUT_CONFIG`, ou `~/.config/wordcut`),
  resolvida a cada uso; falhas do YouTube (inclusive cookies ausentes) viram `youtube_error`
  (saída 6), com mensagem sem o comando do `yt-dlp` nem o caminho dos cookies.

### Removido

- Os comandos da CLI anterior: `info`, `transcribe`, `transcribe-live`, `overview`,
  `cut-sermon`, `preview` e `short`. O fluxo inteiro passa por `sermon`, `cut` e `render`, e
  um nome antigo dá `invalid_argument` (saída 2).
- A transcrição por SSH em outra máquina (`--host`); o WhisperX roda na máquina da CLI.
- O formato em pastas com `.json` (`palavras.json`, `roteiros/`, `cortes/`, `trabalho/`): a
  pregação, os cortes e as exportações ficam no banco e em `media/` na pasta de dados.
- Os módulos do core que só a CLI anterior usava: `wordcut.short`, `wordcut.overview`,
  `wordcut.sermon`, `wordcut.sermon_folder`, `wordcut.asr.remote` e `wordcut.edit.edit_list`,
  com o código que só eles chamavam. O nome legível dos arquivos baixados passa a
  `wordcut.files` e as margens do corte, a `wordcut.processing.pipeline`, sem mudar o
  comportamento.
- `skills/video-corte-vertical/sugerir-cortes.md` e `exemplos.md`: os critérios da sugestão
  vivem no pacote (`criteria list`, presets).
