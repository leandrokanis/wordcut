```
Wordcut                                                    Administrador
Especificação de interface                                 2026-10-26
Situação: aprovado


                    Interface de linha de comando do Wordcut
```

## Resumo

Este documento especifica a interface de linha de comando (CLI) `wordcut`: a gramática dos
comandos, o contrato de saída e de erros, o modelo de tarefas em segundo plano e cada comando
por recurso. A CLI executa o fluxo inteiro do Wordcut, da live do culto às exportações dos
cortes, e é operável por pessoas e por agentes.

## Situação deste documento

Aprovado pelo administrador do projeto em 2026-10-26.
Em funcionalidade, prevalecem os requisitos (`docs/requirements/`); em princípios e
arquitetura, a constituição (`docs/constitution.md`). Este documento detalha como os dois se
traduzem em comandos.

## Sumário

1. [Introdução](#1-introdução)
2. [Convenções](#2-convenções)
3. [Visão geral](#3-visão-geral)
4. [Contrato de saída](#4-contrato-de-saída)
5. [Erros e códigos de saída](#5-erros-e-códigos-de-saída)
6. [Tarefas](#6-tarefas)
7. [Pregações (`sermon`)](#7-pregações-sermon)
8. [Cortes (`cut`)](#8-cortes-cut)
9. [Exportações (`render`)](#9-exportações-render)
10. [Tarefas (`task`) e estado (`status`)](#10-tarefas-task-e-estado-status)
11. [Configurações, critérios e presets](#11-configurações-critérios-e-presets)
12. [Equipe (`member`)](#12-equipe-member)
13. [Servidor](#13-servidor)
14. [Armazenamento](#14-armazenamento)
15. [Migração da CLI anterior](#15-migração-da-cli-anterior)
16. [Considerações de segurança](#16-considerações-de-segurança)
17. [Considerações de privacidade (LGPD)](#17-considerações-de-privacidade-lgpd)
18. [Referências](#18-referências)

---

## 1. Introdução

O Wordcut transforma a live de um culto no YouTube na pregação recortada e em cortes
verticais 9:16 editados palavra a palavra. A aplicação tem uma interface web para a equipe e
esta CLI, que cobre o mesmo fluxo de ponta a ponta (constituição §II).

A web e a CLI chamam a mesma camada de serviço. A CLI chama essa camada diretamente, sem
depender do servidor no ar, e, na máquina do servidor, age como administrador.

## 2. Convenções

As palavras-chave "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY" e "OPTIONAL" neste documento devem ser
interpretadas como descrito no BCP 14 [RFC2119] [RFC8174] quando, e somente quando, aparecem
em maiúsculas, como aqui.

Notação de sintaxe:

- `<valor>`: argumento obrigatório; `[opção]`: opcional; `a|b`: uma das alternativas.
- `T`: tempo em `HH:MM:SS[.mmm]`, `MM:SS[.mmm]` ou segundos (`754.2`).
- `<id>`: inteiro positivo (§3.3).

Vocabulário, conforme os requisitos:

| Requisitos | CLI | Significado |
|---|---|---|
| pregação | `sermon` | o trecho da live delimitado e processado |
| corte | `cut` | unidade editável: sugerido, escolhido ou descartado |
| exportação | `render` | vídeo renderizado de um corte, registrado nele |
| preset | `preset` | conjunto nomeado de níveis de rigidez, formato e instruções |
| equipe | `member` | e-mail liberado, com papel |
| tarefa | `task` | processamento em segundo plano |

## 3. Visão geral

### 3.1. Gramática

```
wordcut [opções globais] <recurso> <ação> [argumentos] [opções]
```

Comandos e opções MUST estar em inglês. Ajuda, mensagens e documentação MUST estar em
português.

### 3.2. Opções globais

| Opção | Efeito |
|---|---|
| `--json` | saída em JSON (§4); aceita antes ou depois do subcomando |
| `--quiet` | suprime o progresso no stderr |
| `--version` | mostra a versão e sai |
| `--help` | ajuda do comando, com ao menos um exemplo pronto para copiar |

A CLI MUST NOT pedir confirmação nem abrir prompt interativo quando chamada com argumentos.
Comandos destrutivos (`delete`, `sermon process --force`) executam direto. A única leitura
interativa permitida é a digitação sem eco de segredo em `settings set-key` e
`settings set-cookies`, e só quando o stdin é um terminal.

### 3.3. Identificadores

- Cada recurso tem ID inteiro, gerado pelo SQLite, único na sua tabela e estável.
- Os IDs são globais: `wordcut cut show 34` dispensa o ID da pregação.
- Palavras da transcrição têm ID próprio (`word_id`), estável enquanto a pregação não for
  reprocessada.
- Membros da equipe são identificados pelo e-mail.

### 3.4. Tempos

- `sermon trim` usa o **tempo da live**.
- Todos os demais comandos usam o **tempo da pregação**, com t = 0 no início dela.

### 3.5. Mapa de comandos

| Comando | Feature | Papel | Tarefa |
|---|---|---|:-:|
| `sermon create` | 1.1.a | assistente | — |
| `sermon list` · `show` | 1.1.a | assistente | — |
| `sermon trim` | 1.1.b | assistente | — |
| `sermon process` | 1.1.c | assistente | ✅ com trava |
| `sermon download` | 1.1.d | assistente | — |
| `sermon suggest` | 2.1.b | admin | ✅ sem trava |
| `sermon prepare` | 1.1.b | assistente | ✅ sem trava |
| `sermon delete` | 1.2.b | admin | — |
| `cut list` · `show` · `preview` | 1.1.e, 1.1.g | assistente | — |
| `cut choose` · `discard` · `restore` | 1.1.e | assistente | — |
| `cut fix-word` · `caption` | 1.1.f | assistente | — |
| `cut render` | 1.1.h | assistente | ✅ com trava |
| `cut create` · `range` · `move` · `segments` | 2.1.c | admin | — |
| `cut delete` | 1.2.b | admin | — |
| `render list` · `show` · `download` | 1.1.i | assistente | — |
| `task list` · `show` · `wait` | 3.1.a | assistente | — |
| `status` | 3.1.a | assistente | — |
| `settings` · `criteria` · `preset` | 2.1.a | admin | — |
| `member` | 1.2.a | admin | — |

A coluna "Papel" segue a tabela de permissões da feature 1.2.a. Na máquina do servidor, a CLI
age como administrador e pode executar todos os comandos. O `--help` dos comandos de
administrador MUST dizer que são do administrador.

## 4. Contrato de saída

### 4.1. Canais

- O **stdout** MUST conter só o resultado do comando.
- O **stderr** MUST conter só progresso, avisos e logs; nunca o resultado.

### 4.2. Saída legível

Sem `--json`, o stdout traz texto legível em português. Seu formato pode mudar a qualquer
versão e MUST NOT ser usado por programas.

### 4.3. Saída JSON

Com `--json`, o stdout MUST conter exatamente um documento JSON:

- comandos de um item: um objeto;
- listagens: `{"items": [ … ]}`;
- erro: `{"error": { … }}` (§5).

Convenções:

- Nomes de campo e valores de enumeração em inglês, `snake_case` (`"status": "chosen"`).
- Tempos em segundos, como número (`12.48`).
- Datas em ISO 8601 com fuso [RFC3339] (`"2026-10-26T19:40:00-03:00"`).
- Referências entre recursos por `<recurso>_id` (`"sermon_id": 12`).
- Textos de conteúdo (título, transcrição) e `message` de erro em português.

### 4.4. Estabilidade

- Antes da versão 1.0, o formato pode mudar (constituição §V).
- A partir da 1.0, o JSON só cresce: campos novos MAY entrar; campos existentes MUST NOT
  mudar de nome, tipo ou significado. Uma quebra MUST vir numa versão MAJOR do `wordcut`.
- Programas SHOULD ignorar campos que não conhecem.

### 4.5. Progresso

Comandos longos escrevem o progresso no stderr, uma linha por etapa ou atualização
(`[process] transcrevendo 42%`). `--quiet` suprime essas linhas; avisos e erros continuam.

## 5. Erros e códigos de saída

### 5.1. Códigos de saída

| Saída | Nome | Significado |
|:-:|---|---|
| 0 | — | sucesso |
| 1 | `internal_error`, `interrupted`, `processing_error`, `unauthenticated`, `forbidden` | erro interno inesperado; tarefa interrompida; processamento sem resultado; quem chama a API não foi identificado ou não tem permissão (§5.3) |
| 2 | `invalid_argument` | uso inválido: argumento faltando, mal formado ou fora da faixa |
| 3 | `not_found` | recurso inexistente |
| 4 | `busy` | máquina ocupada pela trava de processamento |
| 5 | regra violada | a operação contraria uma regra de negócio (§5.3) |
| 6 | falha externa | YouTube, OpenRouter, rede ou transcrição falharam (§5.3) |
| 130 | — | interrompido pelo usuário (Ctrl+C) |

### 5.2. Objeto de erro

Com `--json`, um erro MUST produzir no stdout:

```json
{
  "error": {
    "code": "busy",
    "message": "A máquina está processando a pregação 12 há 4 min.",
    "details": { "task_id": 9, "kind": "process", "started_at": "2026-10-26T19:40:00-03:00" }
  }
}
```

- `code`: estável, em inglês. Programas MUST decidir pelo `code` e pela saída, nunca pelo
  `message`.
- `message`: em português, para pessoas.
- `details`: OPTIONAL; dados que ajudam a reagir ao erro.

Sem `--json`, o `message` vai para o stderr.

### 5.3. Códigos de erro

| `code` | Saída | Quando |
|---|:-:|---|
| `internal_error` | 1 | falha não prevista |
| `interrupted` | 1 | a tarefa parou antes do fim: Ctrl+C durante `--wait` ou processo da tarefa morto (§6.5) |
| `processing_error` | 1 | o processamento não achou palavra dentro das bordas, ou o vídeo baixado não cobre a pregação; nada é gravado |
| `unauthenticated` | 1 | só na API (HTTP 401): requisição sem o token do Cloudflare Access, com token inválido (assinatura, validade, `aud` ou emissor) ou sem Access configurado nem e-mail de desenvolvimento; a mensagem nunca traz o token (ADR-0019) |
| `forbidden` | 1 | só na API (HTTP 403): e-mail fora da equipe, ou papel sem permissão para a rota; a mensagem nunca traz o e-mail (ADR-0015, ADR-0019) |
| `invalid_argument` | 2 | argumento inválido; `details.argument` diz qual opção do comando, quando identificável, com o nome que o parser define, e `details.choices` lista as opções válidas de uma escolha; argumento não reconhecido não traz `details`; a mensagem nunca repete o que foi digitado, nem como nome de opção (ADR-0015) |
| `not_found` | 3 | ID ou e-mail inexistente |
| `busy` | 4 | outra tarefa segura a trava, ou já há uma sugestão (§7.6) ou uma preparação da timeline (§7.7) da mesma pregação em andamento; `details` traz a tarefa (`task_id`, `kind`, `started_at`) |
| `live_not_finished` | 5 | processar uma live que ainda não terminou |
| `sermon_not_trimmed` | 5 | processar sem bordas definidas |
| `sermon_too_short` | 5 | bordas com menos de 1 minuto |
| `sermon_not_processed` | 5 | operação que exige a pregação processada |
| `would_discard_edits` | 5 | reprocessar pregação com cortes editados, sem `--force` |
| `spelling_too_different` | 5 | correção de grafia barrada pela trava; `details` traz a distância e o limite |
| `default_preset` | 5 | apagar o preset padrão |
| `last_admin` | 5 | remover ou rebaixar o último administrador |
| `config_not_writable` | 5 | gravar um segredo numa pasta de configuração sem escrita (montada só para leitura no contêiner); a mensagem não traz o segredo |
| `llm_not_configured` | 5 | sugerir cortes sem o modelo do LLM ou sem a chave; `details.missing` lista o que falta (`llm_model`, `llm_key`); a mensagem não traz a chave |
| `youtube_error` | 6 | falha ao consultar ou baixar do YouTube |
| `llm_error` | 6 | falha do LLM depois da nova tentativa (constituição §III) |
| `network_error` | 6 | falha de rede genérica; também a rede proibida por `WORDCUT_FORBID_NETWORK`, que a suíte de testes define (`details.forbidden_by`, ADR-0017) |
| `transcription_error` | 6 | falha da transcrição: ambiente do WhisperX ausente, GPU ou processo de transcrição |

Códigos novos MAY ser acrescentados; os existentes MUST NOT mudar de saída.

## 6. Tarefas

### 6.1. Modelo

`sermon process`, `sermon suggest`, `sermon prepare` e `cut render` são **tarefas**: rodam
em segundo plano, têm ID e estado gravados no SQLite e podem ser acompanhadas. `sermon
create` também lança uma, a preparação da timeline da pregação nova (§7.7).

| Tipo (`kind`) | Comando | Trava |
|---|---|:-:|
| `process` | `sermon process` | ✅ |
| `render` | `cut render` | ✅ |
| `suggest` | `sermon suggest` | — |
| `prepare` | `sermon prepare`, e `sermon create` numa pregação nova | — |

Estados: `running`, `succeeded`, `failed`.

### 6.2. Sem `--wait`

O comando MUST lançar um processo destacado (sessão própria), que executa a tarefa e segura a
trava, e MUST voltar em seguida com a tarefa:

```json
{ "task_id": 9, "kind": "process", "status": "running", "sermon_id": 12 }
```

### 6.3. Com `--wait`

O comando MUST executar a tarefa em primeiro plano, com o progresso no stderr, e devolver o
resultado final (a pregação, a exportação ou as sugestões). A saída reflete o resultado: 0
em sucesso, o código do erro em falha.

`task wait <id>` MUST se comportar como `--wait` para uma tarefa já lançada.

### 6.4. Trava

- Tarefas com trava MUST adquirir a trava do sistema operacional (`flock`) compartilhada pela
  web e pela CLI (constituição §IV).
- Se a trava estiver ocupada, o comando MUST falhar na hora com `busy` (saída 4), sem fila e
  sem lançar processo.
- A trava se libera sozinha quando o processo da tarefa morre.

### 6.5. Interrupção

- Ctrl+C durante `--wait` ou `task wait` de uma tarefa em primeiro plano MUST interromper a
  tarefa, marcá-la `failed` com o erro `interrupted` e sair com 130.
- Ctrl+C em `task wait` de uma tarefa destacada só para a espera; a tarefa continua.
- Uma tarefa encontrada `running` sem processo vivo (reinício da máquina) MUST ser marcada
  `failed`, com o erro `interrupted`, na próxima leitura (1.1.c).

Não há cancelamento de tarefa nesta versão.

## 7. Pregações (`sermon`)

Estados (`status`): `created` → `trimmed` → `processing` → `processed`, ou `failed`.

### 7.1. `sermon create <link> [--start T --end T] [--process] [--wait]`

Cria a pregação a partir do link da live e devolve título, data do culto e duração (1.1.a).

- O mesmo vídeo duas vezes MUST devolver a pregação existente, com `"created": false` e
  saída 0.
- Uma pregação nova MUST ter a timeline preparada em segundo plano (§7.7): a criação lança a
  tarefa `prepare`, destacada, e volta sem esperá-la. O mesmo vídeo de novo não prepara outra
  vez. Se o lançamento falhar, a pregação continua criada e a timeline aparece como não
  preparada.
- Live não terminada: cria, avisa no stderr e devolve `"live_finished": false` (1.1.a.2).
- `--start`/`--end`: delimita na criação, como `sermon trim`; os dois juntos ou nenhum. Bordas
  recusadas MUST NOT deixar pregação criada. Para um vídeo que já tem pregação, delimita a
  existente, com as mesmas regras e aviso de `sermon trim`, e devolve `"created": false`.
- `--process`: em seguida processa, como `sermon process`; exige `--start` e `--end`
  (`invalid_argument` sem criar nada). Sem `--wait`, devolve a tarefa (§6.2); com ele, a
  pregação processada. Se o processamento for recusado (live no ar, pregação já processada),
  a pregação criada e delimitada permanece. `--wait` sem `--process` é `invalid_argument`.

```
wordcut sermon create https://youtube.com/live/… --start 1:02:10 --end 1:48:30 --process --wait
```

### 7.2. `sermon list [--status S]` · `sermon show <id> [--transcript]`

- `list`: ID, título, data, duração da pregação, estado, quantidade de cortes por estado e
  `borders_changed`.
- `show`: os mesmos dados, mais as bordas na live (`live_start`, `live_end`), as bordas
  ajustadas às palavras pelo processamento (`sermon_start`, `sermon_end`, em tempo da live;
  `null` antes de processar), `processed_at`, a última tarefa da pregação (`last_task`, no
  formato de `task show`, ou `null`; a preparação da timeline não conta), os cortes
  (`cuts`), o erro da última sugestão (`suggestion_error`) e o estado da timeline
  (`timeline`, §7.7).
- Cada corte em `cuts`, na ordem em que foi criado: `id`, `status`, `title`, `segments` (no
  formato de `cut segments`, §8.10, na ordem em que o corte toca), `range_start_word` e
  `range_end_word` (primeira e última palavra da faixa contínua, na ordem da pregação),
  `source` (`llm` ou `admin`), `preset_id` (o preset da sugestão; `null` se o preset foi
  apagado ou o corte não veio do LLM) e `edited`.
- `borders_changed` (em `list` e `show`): `true` quando a pregação está `processed` e as
  bordas na live (`live_start`, `live_end`) diferem, ao milissegundo, das usadas no último
  processamento bem-sucedido (1.1.b.3); `false` nos demais casos, inclusive para pregações
  processadas antes de as bordas processadas serem guardadas, até a próxima mudança. Sem
  `--json`, o `show` traz a linha
  `Bordas mudaram desde o processamento: reprocesse com wordcut sermon process --force.`
- `suggestion_error`: `{"code", "message"}` da última sugestão que falhou, ou `null` quando
  ela deu certo ou nunca rodou. Sem `--json`, o `show` termina com a linha
  `Sugestão de cortes falhou: <mensagem>`.
- `timeline`: `{"status", "error", "task_id"}` da preparação das miniaturas e da forma de
  onda (§7.7). Sem `--json`, o `show` traz a linha `Timeline: preparando`, `Timeline: pronta`
  ou `Timeline: falhou (<mensagem>)`.

```json
{ "cuts": [ { "id": 34, "status": "suggested", "title": "Graça que alcança",
              "segments": [ { "from_word": 1201, "to_word": 1230 } ],
              "range_start_word": 1201, "range_end_word": 1230, "source": "llm",
              "preset_id": 1, "edited": false } ],
  "borders_changed": false,
  "suggestion_error": null }
```
- `--transcript`: acrescenta a transcrição, uma frase por linha, com ID da frase, tempo e IDs
  da primeira e da última palavra. No JSON, `sentences`, em ordem e em tempo da pregação:

```json
{ "sentences": [ { "id": 41, "start": 0.3, "end": 1.3, "text": "Irmãos, graça e paz.",
                   "first_word_id": 803, "last_word_id": 806 } ] }
```

- `list` e `show` conferem o estado: uma pregação `processing` cuja tarefa morreu (§6.5) é
  mostrada e gravada `failed`.

### 7.3. `sermon trim <id> --start T --end T`

Define as bordas da pregação, em tempo da live (1.1.b.2).

- Faixa com menos de 1 minuto: `sermon_too_short`.
- Bordas fora de `[0, duração da live]` ou com o início no fim ou depois dele:
  `invalid_argument`. Com a duração da live desconhecida (live no ar), vale só a ordem.
- Numa pregação processada, só grava as bordas; reprocessar é `sermon process --force`. A
  resposta traz `borders_changed` (§7.2), que volta a `false` quando as bordas voltam às
  processadas.

### 7.4. `sermon process <id> [--force] [--wait]`

Tarefa com trava (1.1.c): baixa só a faixa delimitada, transcreve na GPU local, corta em 16:9 e
pede as sugestões ao LLM com o preset padrão (2.1.b.1).

- Exige bordas (`sermon_not_trimmed`) e live terminada (`live_not_finished`). Uma pregação
  criada com a live no ar é consultada de novo no YouTube antes da recusa.
- Numa pregação já processada, MUST exigir `--force`, porque os cortes e suas edições são
  refeitos (1.1.b.3); sem ele, `would_discard_edits`. Com `--force`, os cortes da pregação
  são apagados junto com as palavras e as frases.
- Uma pregação `failed` é refeita pelo mesmo comando (1.1.c.3).
- A pregação fica `processing` desde o lançamento e termina `processed` ou `failed`. O
  sucesso guarda as bordas na live usadas como as processadas, e `borders_changed` (§7.2)
  volta a `false`; a falha não as muda.
- Depois de gravar palavras e frases, a tarefa pede os cortes ao LLM uma vez (constituição
  §III), com o prompt do preset padrão e as frases numeradas de 1 em diante, sem tempos. A
  resposta é validada por esquema; fora dele, uma nova tentativa; fora de novo, `llm_error`.
  Os cortes válidos ficam `suggested`, com o `preset_id` do padrão. Um corte cuja duração
  estimada (soma dos trechos, menos 18% de limpeza) sai da duração permitida do preset é
  descartado com aviso.
- A falha da sugestão (`llm_not_configured`, `llm_error`) MUST NOT desfazer o processamento:
  a tarefa termina `succeeded`, a pregação `processed`, sem cortes, e o erro fica em
  `suggestion_error` (§7.2). Sem o modelo ou sem a chave, o LLM não é chamado.
- Etapas no progresso: `baixando`, `sincronizando`, `transcrevendo`, `cortando`, `gravando`,
  `sugerindo`.
- Com `--wait`, devolve a pregação como `sermon show`. O resultado gravado na tarefa, que
  `task wait` devolve, é o mesmo objeto sem `last_task`, mais `suggestion_warnings`: um item
  `{"title", "estimated_duration", "message"}` por corte descartado pela duração (lista vazia
  quando nenhum foi descartado ou a sugestão falhou).

### 7.5. `sermon download <id> [-o caminho]`

Copia a pregação 16:9 para `caminho`, ou para a pasta atual com um nome legível (data e
título). Devolve o caminho de destino (1.1.d).

- `caminho` que é pasta existente, ou que termina em `/`, recebe o nome legível dentro.
- Destino existente não é sobrescrito: o nome ganha ` (2)`, ` (3)`… antes da extensão.
- Saída: `{"path": "<caminho absoluto>", "bytes": N}`; em texto, só o caminho.
- Não toma a trava de processamento. Numa pregação não processada, falha com
  `sermon_not_processed`.

### 7.6. `sermon suggest <id> [--preset <id>] [--wait]` — administrador

Tarefa sem trava: pede nova sugestão ao LLM (2.1.b.2), com o preset indicado ou o padrão.
O pedido e a validação da resposta são os do `sermon process` (§7.4).

- Os cortes `suggested` não editados são substituídos, só no sucesso e numa transação.
- Os cortes escolhidos, descartados ou editados permanecem.
- Recusas antes de criar a tarefa: pregação inexistente ou preset inexistente (`not_found`,
  com `details.sermon_id` ou `details.preset_id`); pregação não processada
  (`sermon_not_processed`); sem o modelo do LLM ou sem a chave (`llm_not_configured`, que não
  muda a pregação nem o `suggestion_error`); outra tarefa `suggest` da mesma pregação em
  andamento (`busy`, com `task_id`, `kind` e `started_at` dela). A tarefa órfã (§6.5) não
  conta. A conferência e a criação da tarefa não são atômicas: dois pedidos no mesmo instante
  podem passar os dois; cada substituição continua inteira.
- A tarefa guarda o preset resolvido (o padrão de quando foi lançada, sem `--preset`). Um
  preset apagado antes da execução faz a tarefa terminar `failed` com `not_found`.
- A falha do LLM (`llm_error`, ou `llm_not_configured` se a configuração mudou depois do
  lançamento) deixa a tarefa `failed`, os cortes como estavam e o erro em `suggestion_error`
  (§7.2); o sucesso limpa `suggestion_error`.
- Resposta no esquema, mas sem corte dentro da duração permitida, é sucesso: os sugeridos não
  editados saem, `suggested_cuts` vem vazio e `suggestion_warnings` traz os descartados.
- Se a pregação for processada de novo (ou estiver processando) quando a resposta chega, a
  tarefa falha com `sermon_not_processed` e nada é gravado.
- Etapa no progresso: `sugerindo`.
- Resultado (com `--wait`, e o que `task wait` devolve):

```json
{
  "sermon_id": 12,
  "preset_id": 3,
  "suggested_cuts": [ { "id": 41, "status": "suggested", "title": "…", "preset_id": 3, "…": "…" } ],
  "suggestion_warnings": [ { "title": "…", "estimated_duration": 92.3, "message": "…" } ]
}
```

  `suggested_cuts` traz os cortes novos no formato do `sermon show`; `suggestion_warnings`,
  os descartados pela duração, como no §7.4.

### 7.7. `sermon prepare <id> [--wait]`

Tarefa sem trava (1.1.b.1, ADR-0025): prepara as miniaturas e a forma de onda da timeline da
pregação. Baixa só as imagens de navegação da live (storyboards do YouTube, do maior
tamanho) e o áudio da live inteira na menor qualidade; calcula os picos da forma de onda e
apaga o áudio. `sermon create` lança a mesma tarefa numa pregação nova (§7.1); este comando
a pede de novo.

- Não toma a trava de processamento: roda junto com um `process` ou um `render`. Outra
  `prepare` da mesma pregação em andamento: `busy`, com `task_id`, `kind` e `started_at`
  dela. A tarefa órfã (§6.5) não conta. A conferência e a criação da tarefa não são
  atômicas.
- Roda em qualquer estado da timeline, pronta inclusive: refaz tudo. Mostrar a pregação
  (`sermon show`, web) nunca prepara.
- Live sem storyboards: a timeline fica pronta só com a forma de onda, sem erro. A falha das
  miniaturas também deixa só a forma de onda; a falha do áudio deixa a timeline `failed`.
- `timeline.status` (§7.2): `pending` enquanto a tarefa roda (`task_id` é a tarefa),
  `ready` ou `failed`. Uma pregação sem preparação em andamento nem terminada (criada antes
  desta versão, ou com a tarefa morta) aparece `failed` com o erro `interrupted`.
- `timeline.error`: `{"code", "message"}` da falha, com uma mensagem genérica que nunca traz
  caminho, URL, cookies nem a saída do yt-dlp; o código é o da falha (`youtube_error`,
  `network_error`, `internal_error`). A tarefa falha com o mesmo erro.
- A falha da preparação MUST NOT impedir `sermon trim` nem `sermon process`.
- Etapas no progresso: `miniaturas`, `áudio`, `forma de onda`.
- Sem `--wait`, devolve a tarefa (§6.2). Com `--wait`, devolve
  `{"sermon_id": 12, "timeline": {"status": "ready", "error": null, "task_id": null}}`; o
  resultado gravado na tarefa é `{"sermon_id", "status": "ready", "thumbnails"}`, com
  `thumbnails` falso quando a live não tem storyboards.

```
wordcut sermon prepare 12 --wait --json
```

### 7.8. `sermon delete <id>` — administrador

Apaga a pregação, seus cortes, exportações e mídias (1.2.b). Falha com `busy` se uma tarefa
da pregação estiver rodando.

## 8. Cortes (`cut`)

Estados (`status`): `suggested`, `chosen`, `discarded`.

### 8.1. `cut list --sermon <id> [--status S]`

Lista os cortes da pregação com texto montado, duração e estado (1.1.e.1). Descartados vêm
por último. Cada corte traz também `start` e `end`: o menor início e o maior fim dos seus
trechos, em tempo da pregação, arredondados ao milissegundo; com trechos fora de ordem esse
vão vai além do que o corte toca. E traz `range_start` e `range_end`: o início e o fim da
faixa do corte (§8.9), no mesmo tempo e arredondamento. A camada do corte na timeline do
nível 2 desenha a faixa.

### 8.2. `cut show <id>`

Devolve o corte completo:

- texto montado, duração, estado e faixa na pregação;
- `segments`: trechos em ordem, no formato de `cut segments` (§8.10), com tempos e texto;
- `range_sentences`: as frases da faixa do corte, na ordem da pregação, cada uma com `id`,
  `start` e `end` (tempo da pregação), `text` (com as correções de grafia do corte),
  `first_word` e `last_word` e `included`: `all` quando o corte toca todas as suas palavras,
  `part` quando toca algumas e `none` quando não toca nenhuma. A frase que cruza a borda da
  faixa vem recortada a ela: `first_word`, `last_word`, tempos e texto são os da parte dentro
  da faixa. Sem `--json`, não aparece;
- `words`: palavras do corte com `word_id`, `text` (o original), tempos e `corrected` (a
  correção de grafia do corte, §8.5, ou `null`);
- `caption`: estilo efetivo da legenda, no formato de `cut caption` (§8.6); o padrão completo
  quando o corte não tem estilo gravado;
- `render_options`: as opções efetivas da próxima exportação (§8.7), com as nove escolhas: os
  padrões mais as últimas salvas, com `caption` igual ao `enabled` da legenda; uma opção salva
  que deixou de valer volta ao padrão;
- `renders`: histórico de exportações, da mais antiga para a mais nova, no formato de §9.

### 8.3. `cut preview <id>`

Devolve a sequência que a prévia toca (1.1.g): cada trecho com início e fim na pregação e o
texto. Não toca vídeo nem renderiza; nunca é bloqueado pela trava.

- `segments`: os trechos na ordem em que o corte toca, cada um com `start` e `end` (início da
  primeira palavra e fim da última, em tempo da pregação), `text` (as palavras do trecho
  unidas por espaço, com as correções de grafia do corte, §8.5) e `out_of_order`.
- `out_of_order` é `true` no trecho que começa antes do fim do trecho tocado logo antes dele,
  e só esse anterior conta; o primeiro trecho é sempre `false`. Um trecho que começa
  exatamente no fim do anterior não está fora de ordem. Exemplo: um corte que toca
  `2.5–3.4`, depois `0.3–1.2` e depois `1.35–1.9` marca `false`, `true`, `false`; o terceiro
  ainda vem antes do primeiro na pregação, mas segue o segundo.
- `duration`: a mesma do `cut show` (§8.2), a soma das faixas dos trechos.
- Sem `--json`, uma linha por trecho com os tempos e o texto, com `↑` nos fora de ordem:
  `[00:00:00.300 → 00:00:01.200] ↑ Irmãos, graça`.
- Corte inexistente: `not_found`.

```json
{ "cut_id": 34, "duration": 2.35,
  "segments": [ { "start": 2.5, "end": 3.4, "text": "Deus governa.", "out_of_order": false },
                { "start": 0.3, "end": 1.2, "text": "Irmãos, graça", "out_of_order": true },
                { "start": 1.35, "end": 1.9, "text": "paz.", "out_of_order": false } ] }
```

### 8.4. `cut choose <id>` · `cut discard <id>` · `cut restore <id>`

Mudam o estado (1.1.e). `restore` devolve um corte descartado a `suggested`. Nenhum deles
altera o conteúdo (constituição §I).

### 8.5. `cut fix-word <id> <word_id> <texto>`

Corrige a grafia de uma palavra da legenda, só neste corte (1.1.f.2). `<word_id>` é o de
`cut show` (§8.2). A correção aparece no texto de `cut list`, `cut show` e `cut preview`; em
`words`, `text` continua o original e `corrected` traz a correção.

- A correção MUST passar pela trava de grafia por distância de edição (1.1.f.3): a distância
  de Levenshtein entre o núcleo da palavra original e o da correção (minúsculas, só letras,
  números e hífen) não pode passar de `max(1, floor(0,34 × tamanho do núcleo original))`. A
  comparação é sempre com a palavra original, nunca com a correção atual. Se não passar,
  `spelling_too_different`, com `details.distance`, `details.limit` e `details.original`, e
  nada muda.
- `<texto>` igual ao original remove a correção; sem correção gravada, não é erro.
- `<texto>` vazio ou com mais de uma palavra: `invalid_argument` com
  `details.argument = "text"`. Palavra fora dos trechos do corte (não basta estar na faixa):
  `invalid_argument` com `details.argument = "word_id"`. Nenhuma mensagem repete o texto
  digitado (ADR-0015). Corte inexistente: `not_found`.
- Os espaços das pontas são ignorados, e o texto é comparado e gravado em NFC.
- Corrigir marca o corte como editado (`edited`), e `sermon suggest` o mantém (§7.6). Não é
  tarefa nem toma a trava.
- Sem `--json`, uma linha com a palavra, o original e a correção.

```json
{ "cut_id": 34, "word_id": 1204, "text": "Jesús", "start": 512.31, "end": 512.7,
  "corrected": "Jesus" }
```

### 8.6. `cut caption <id> [opções]`

Sem opções, mostra o estilo atual e não grava nada. Com opções, altera só o informado, e o
estilo vale para todas as legendas do corte (1.1.f.4, 1.1.f.5).

| Opção | Valores |
|---|---|
| `--on` · `--off` | liga ou desliga a legenda |
| `--font <nome>` | fontes incluídas no pacote, pelo nome dos metadados do arquivo (`Open Sans Bold`) |
| `--size <px>` | tamanho em pixels, no quadro 1080×1920, de 24 a 160 |
| `--color <#RRGGBB>` | cor do texto |
| `--position top\|center\|bottom` | posição: 20, 50 e 78 % da altura do quadro, como no protótipo |
| `--offset <%>` | altura do centro da legenda, de 10 a 90 % do quadro |
| `--border <px>` · `--border-color <#RRGGBB>` | contorno, de 0 a 12 px |
| `--shadow none\|soft\|strong` | sombra |
| `--reset` | volta ao estilo da igreja |

- O estilo da igreja é o padrão: Open Sans Bold, 60 px, `#FFD600`, centro (altura 50 %),
  contorno preto de 3 px e sombra suave.
- `--position` leva a altura (`offset`) à da posição. `--offset` junto com `--position`
  vence; `--offset` sozinho mantém o `position`.
- As cores são aceitas em maiúsculas ou minúsculas e gravadas em maiúsculas.
- O estilo fica gravado no corte; `--reset` apaga o gravado, e o corte volta a seguir o
  padrão, ligado. Um estilo gravado incompleto é completado pelo padrão, e campos
  desconhecidos são ignorados.
- Alterar, ligar, desligar ou restaurar marca o corte como editado (`edited`), e
  `sermon suggest` o mantém (§7.6). Não é tarefa nem toma a trava.
- `invalid_argument`, sem mudar nada: valor fora da faixa (`details.min` e `details.max`),
  cor fora de `#RRGGBB`, posição ou sombra fora dos valores, fonte que não está no pacote
  (`details.choices` com as fontes), `--on` com `--off` e `--reset` com outra opção. Corte
  inexistente: `not_found`.
- No desenho, a legenda nunca sai do quadro: perto da borda, encosta nela.
- Saída: o estilo inteiro, o mesmo `caption` de `cut show`. Sem `--json`, uma linha por
  campo.

```json
{ "enabled": true, "font": "Open Sans Bold", "size": 60, "color": "#FFD600",
  "position": "center", "offset": 50, "border": 3, "border_color": "#000000",
  "shadow": "soft" }
```

### 8.7. `cut render <id> [opções] [--estimate] [--wait]`

Tarefa com trava: cria uma exportação 9:16 do estado atual do corte (1.1.h).

| Grupo | Opção | Padrão |
|---|---|---|
| Limpeza | `--fillers remove\|keep` | `remove` |
| | `--stammers remove\|keep` | `remove` |
| | `--pauses original\|natural\|short` | `natural` |
| Edição | `--smooth-joins` · `--no-smooth-joins` | ligado |
| | `--fade` · `--no-fade` | ligado |
| Áudio | `--normalize` · `--no-normalize` | ligado (−14 LUFS) |
| Legenda | `--caption` · `--no-caption` | estado do corte |
| Vídeo | `--resolution 1080x1920\|720x1280` | `1080x1920` |
| | `--quality high\|small` | `high` |

- As opções MUST ficar salvas no corte, como na interface; opção omitida usa a última salva.
  `wordcut cut render 34` repete a exportação anterior. Elas são gravadas quando a tarefa é
  aceita, sob a trava; uma recusa (`busy`, `not_found`, `sermon_not_processed`,
  `invalid_argument`) não grava nada.
- `--caption`/`--no-caption` alteram o mesmo estado de `cut caption --on/--off` (e marcam o
  corte como editado).
- Pausas: `original` não encurta as pausas entre palavras do mesmo trecho; `natural` deixa
  até 0,15 s no meio da frase e 0,40 s depois de ponto; `short`, até 0,08 s e 0,20 s.
  Qualidade: `high` é CRF 18, `small` é CRF 26. O fade dura 0,5 s, ou metade do corte se ele
  for mais curto que 1 s. Sem normalização, o áudio só é reamostrado a 48 kHz. Em 720×1280,
  a legenda escala na mesma proporção.
- `--estimate` devolve `{duration, options}`: a duração estimada e o resumo das opções, sem
  renderizar, sem salvar as opções, sem pegar a trava e sem abrir o vídeo (a timeline é
  calculada sem a energia do áudio, a 30 quadros/s). Com `--wait`, é `invalid_argument`.
- Com `--wait`, devolve a exportação (§9). Sem `--wait`, devolve a tarefa; ao terminar,
  `task show` traz `render_id` em `result` (§10).
- Pregação não processada dá `sermon_not_processed`; pregação processada sem o arquivo do
  vídeo dá `internal_error`, como `sermon download`.
- Uma falha da renderização deixa a tarefa `failed` (`internal_error`) e um Ctrl+C a deixa
  `interrupted`; nos dois casos nenhuma exportação é registrada e nenhum arquivo fica.

### 8.8. `cut create --sermon <id> --start T --end T` — administrador

Cria um corte do zero com as frases da faixa, já `chosen` (2.1.c.4).

### 8.9. `cut range <id> [--start T] [--end T]` · `cut move <id> --by ±S` — administrador

Ajustam a faixa contínua do corte (2.1.c.3). Os tempos são da pregação (0 no início dela).

- `range`: redimensiona. `T` aceita `SS`, `MM:SS` ou `HH:MM:SS`, como em `sermon trim`; a
  borda omitida fica onde estava, e sem nenhuma das duas é `invalid_argument`. O início
  encosta no início de frase mais próximo e o fim, no fim de frase mais próximo; as palavras
  dos trechos que ficam fora da faixa saem do corte (um trecho que cruza a borda é cortado
  nela). Ampliar a faixa só oferece as frases novas em `range_sentences` (§8.2), com
  `included` `none`; elas não entram sozinhas no corte.
- `move`: desloca a faixa inteira em `S` segundos (`--by -12.5` ou `--by=-12.5` volta). O
  deslocamento para no início e no fim da pregação (a primeira e a última frase da
  transcrição), e a faixa deslocada encosta em frases como em `range`. Cada frase escolhida
  (com ao menos uma palavra no corte, mesmo que só em parte) vai inteira para a frase da faixa
  nova cujo início fica mais perto do seu início deslocado, sem repetir destino; as que ficam
  sem destino livre saem. Os trechos novos seguem a ordem em que o corte tocava as frases, e
  destinos vizinhos tocados em seguida viram um trecho só.
- `invalid_argument`, sem gravar nada (`details.argument` é `range`): faixa com menos de
  10 s depois de encostar nas frases; fim antes do início ou igual a ele; fim que, ao
  encostar, cai antes do início; faixa que deixaria o corte sem nenhuma palavra; tempo que não é número. Em `move`,
  um `--by` que não é número finito dá `invalid_argument` com `details.argument` `by`. Corte
  inexistente: `not_found`.
- Gravar marca o corte como editado (`edited`), e `sermon suggest` o mantém (§7.6). As
  correções de grafia ficam gravadas, como em `cut segments` (§8.10). Vale em qualquer estado
  do corte, inclusive descartado (a web é que não arrasta o descartado); não é tarefa nem toma
  a trava.
- A CLI roda no host e não confere papel, como `cut segments`; pela API, só o administrador
  (§5.3).
- Saída: o corte como `cut show` (§8.2), em JSON ou em texto.

```
wordcut cut range 34 --start 1:02:10 --end 1:03:05 --json
wordcut cut move 34 --by -12.5 --json
```

### 8.10. `cut segments <id> --file <arquivo|->` — administrador

Define o que entra no corte e em que ordem (2.1.c.1, 2.1.c.2). Lê, do arquivo ou do stdin,
uma lista ordenada de faixas de palavras:

```json
[
  { "from_word": 1201, "to_word": 1230 },
  { "from_word": 1188, "to_word": 1199 }
]
```

- A lista cobre escolher frases, reordenar trechos e dividir uma frase. Ela substitui a
  anterior inteira, na ordem dada.
- `invalid_argument`, sem gravar nada: lista vazia; elemento que não é um objeto com
  `from_word` e `to_word` inteiros; palavra que não é da pregação do corte; trecho que
  termina antes de começar; palavra fora da faixa do corte (as bordas da faixa valem);
  trechos que se sobrepõem, inclusive repetidos. Arquivo ilegível, que não é JSON ou não é
  uma lista também dá `invalid_argument`. Em todos os casos, `details.argument` é `file` e
  nenhuma mensagem repete o caminho nem o conteúdo (ADR-0015). Corte inexistente:
  `not_found`.
- Gravar marca o corte como editado (`edited`), e `sermon suggest` o mantém (§7.6). As
  correções de grafia ficam gravadas, inclusive as das palavras que saem do corte, que
  voltam se a frase voltar; as exportações já feitas não mudam. Vale em qualquer estado do
  corte; não é tarefa nem toma a trava.
- A CLI roda no host e não confere papel, como `preset`; pela API, só o administrador
  (§5.3).
- Saída: o corte como `cut show` (§8.2), em JSON ou em texto.
- `cut show --json` devolve `segments` no mesmo formato, para editar e devolver.

```
wordcut cut segments 34 --file - --json < trechos.json
```

### 8.11. `cut delete <id>` — administrador

Apaga o corte e suas exportações (1.2.b).

## 9. Exportações (`render`)

Uma exportação é o arquivo renderizado de um corte, registrado nele com data, duração e
opções (1.1.i).

- `render list --cut <id>`: histórico de exportações do corte, `{"items": [...]}`, da mais
  recente para a mais antiga (no mesmo segundo, a gravada por último primeiro); cada item no
  formato de `render show`.
- `render show <id>`: `{id, cut_id, path, duration, created_at, options}`. `path` é o caminho
  local absoluto, já que a CLI roda no servidor (1.1.h.2); `options` é o resumo gravado na
  exportação (§8.7). Não abre o arquivo.
- `render download <id> [-o caminho]`: copia o arquivo para `caminho`, ou para a pasta atual
  com o nome legível `AAAA-MM-DD - Título do corte.mp4` (data do culto da pregação do corte),
  com as regras de `caminho` e de não sobrescrever do `sermon download` (§7.5). Saída:
  `{"path": "<caminho absoluto>", "bytes": N}`; em texto, só o caminho. Arquivo da
  exportação ausente no disco dá `internal_error` com `details.render_id`, sem caminho
  interno.
- Corte ou exportação inexistente dá `not_found`. Nenhum dos três toma a trava de
  processamento.

## 10. Tarefas (`task`) e estado (`status`)

- `task list [--status S] [--kind K]`: tarefas, da mais recente para a mais antiga.
- `task show <id>`: tipo, estado, recurso (`<recurso>_id`, como em §6.2), início, fim,
  progresso, erro e resultado. O `result` de um `process` é a pregação processada; o de um
  `render` é `{"render_id": …}`, o `id` da exportação (§9).
- `task wait <id>`: espera o fim, como `--wait` (§6.3).
- `status`: estado da máquina (3.1.a.3): se a trava está livre ou quem a segura (tarefa, tipo,
  recurso, há quanto tempo) e as tarefas em andamento.

## 11. Configurações, critérios e presets

Todos os comandos desta seção são do administrador (2.1.a).

### 11.1. `settings`

- `settings show`: modelo do LLM, chave mascarada (últimos 4 caracteres), modelo do WhisperX e
  preset padrão.
- `settings set [--model <id>] [--whisper-model <nome>]`.
- `settings set-key`: grava a chave do LLM, lida **só** do stdin.
- `settings set-cookies`: grava os cookies do YouTube, lidos **só** do stdin.

```
wordcut settings set-key < chave.txt
```

### 11.2. `criteria list`

Lista os filtros e valores definidos no código: ID, nome, tipo (filtro ou valor) e nível
padrão. O texto dos prompts MUST NOT aparecer (constituição §I; 2.1.a).

```json
{"items": [{"id": "triumphalism", "name": "Triunfalismo", "type": "filter", "default_level": "strict"}]}
```

### 11.3. `preset`

- `preset list` · `preset show <id>`.
- `preset create <nome> [--from <id>]`: copia do preset indicado ou do padrão.
- `preset update <id> [opções]`:

| Opção | Efeito |
|---|---|
| `--name <nome>` | renomeia |
| `--level <criterio>=lenient\|moderate\|strict` | nível de um filtro ou valor; repetível |
| `--duration-ideal <min>-<max>` | duração ideal, em segundos |
| `--duration-allowed <min>-<max>` | duração permitida, em segundos |
| `--reorder` · `--no-reorder` | permite reordenar trechos |
| `--protected-words "<a,b>"` | palavras protegidas |
| `--instructions-file <arquivo\|->` | instruções adicionais (texto livre, até 4000 caracteres sem os brancos das pontas) |

- `preset update` sem nenhuma opção, nome vazio ou repetido, critério ou nível inexistente,
  duração fora do formato `<min>-<max>` em segundos inteiros, mínimo maior que o máximo,
  duração ideal fora da permitida (mesmo quando só uma das faixas muda) e arquivo de
  instruções que não pode ser lido dão `invalid_argument`, sem repetir o valor digitado
  (ADR-0015). `--level` repetido para o mesmo critério: vale o último.
- `preset set-default <id>`.
- `preset delete <id>`: o preset padrão não pode ser apagado (`default_preset`). Devolve
  `{"id": 2, "deleted": true}`.

`show`, `create`, `update` e `set-default` devolvem o preset; `list` devolve
`{"items": [ … ]}` com os presets. O preset nunca traz texto de prompt; `levels` traz todos
os critérios do código, com o nível padrão para os que o preset não gravou:

```json
{
  "id": 1, "name": "Padrão", "is_default": true,
  "levels": {"triumphalism": "strict", "allegory": "moderate", "…": "…"},
  "duration_allowed": {"min": 40, "max": 75},
  "duration_ideal": {"min": 55, "max": 65},
  "reorder": true,
  "protected_words": ["não", "mas", "se"],
  "instructions": "",
  "created_at": "2026-10-26T19:40:00+00:00",
  "updated_at": "2026-10-26T19:40:00+00:00"
}
```

## 12. Equipe (`member`)

Comandos do administrador (1.2.a). Membros são identificados pelo e-mail, gravado e
comparado em minúsculas, sem os espaços das pontas: `Admin@Exemplo.org` e `admin@exemplo.org`
são o mesmo membro em todos os comandos.

- `member list`: `{"items": [ … ]}` com os membros em ordem de e-mail.
- `member add <email> --role assistant|admin`: `--role` é obrigatório. Devolve o membro.
- `member set-role <email> assistant|admin`: devolve o membro. O papel que o membro já tem
  não muda nada e não é erro.
- `member remove <email>`: devolve `{"email": "assistente@exemplo.org", "removed": true}`.

O membro:

```json
{
  "email": "assistente@exemplo.org",
  "role": "assistant",
  "created_at": "2026-10-26T19:40:00-03:00",
  "updated_at": "2026-10-26T19:40:00-03:00"
}
```

Remover ou rebaixar o último administrador falha com `last_admin`, também quando a CLI e a API
mudam a equipe ao mesmo tempo. Antes do primeiro administrador, qualquer papel pode ser
incluído. E-mail fora da forma de endereço (parte local, `@` e domínio com ponto), e-mail já
na equipe e papel fora de `assistant|admin` dão `invalid_argument` (papel com
`details.choices`); e-mail fora da equipe dá `not_found`. Nenhum erro repete o e-mail digitado (ADR-0015).

## 13. Servidor

A CLI não sobe o servidor. A API (`apps/api`) e a interface (`apps/web`) são aplicações
próprias, iniciadas pelo Docker Compose (ADR-0002, ADR-0003, ADR-0008). Elas compartilham com
a CLI o mesmo `WORDCUT_HOME` e a mesma trava. As portas publicadas MUST escutar só em
`127.0.0.1`; o acesso externo é pelo Cloudflare Tunnel (constituição §VI).

A CLI também roda no contêiner: `docker compose run --rm cli <comando>`.

## 14. Armazenamento

| O quê | Onde | Observação |
|---|---|---|
| Banco (SQLite) e mídias | `~/.local/share/wordcut/` | sobrescrito por `WORDCUT_HOME`; nos contêineres, o volume de dados |
| Mídias de uma pregação | `media/sermons/<id>/` na pasta de dados | `sermon.mp4`; intermediários em `work/`, apagados no sucesso |
| Mídias da timeline | `media/sermons/<id>/timeline/` na pasta de dados | `thumbnails.jpg`, `thumbnails.json`, `waveform.json`; intermediários em `timeline-work/`, apagados no fim |
| Exportações de um corte | `media/cuts/<id>/` na pasta de dados | `<render_id>.mp4`; intermediários em `work/`, apagados no fim |
| Saída dos processos de tarefa | `tasks/<id>.log` na pasta de dados | traz o rastreio de um erro interno; permissão 600 |
| Segredos (chave do LLM, cookies) | `~/.config/wordcut/` | permissão 600 |
| Demais configurações, presets e equipe | no SQLite | — |

O esquema do banco MUST ser criado e migrado automaticamente na primeira chamada; não há
`wordcut init`.

## 15. Migração da CLI anterior

O executável `cortes` e seus comandos são removidos, sem retrocompatibilidade
(constituição §V).

| Antes | Depois |
|---|---|
| `cortes info <link>` | `sermon create` |
| `cortes live` | `sermon create … --start --end --process` |
| `cortes cut` | `sermon trim` + `sermon process` |
| `cortes transcribe` (`--host`, `--model`) | etapa de `sermon process`, na GPU local; `--host` sai; o modelo vai para `settings set --whisper-model` |
| `cortes overview` | `sermon show --transcript` |
| `cortes preview` | `cut preview` |
| `cortes short` | `cut render` |
| pastas com `.json` e "roteiro" | SQLite e mídias no disco |

As skills do Claude Code passam a ser guias curtos de uso da CLI, sem lógica própria; o
critério teológico vai para o pacote (2.1.a).

## 16. Considerações de segurança

- Segredos MUST NOT ser aceitos como argumento de linha de comando, porque ficariam no
  histórico do shell e visíveis na lista de processos. `settings set-key` e
  `settings set-cookies` leem só do stdin.
- Segredos MUST NOT aparecer em saída, log, progresso ou mensagem de erro; a chave aparece só
  pelos últimos 4 caracteres (constituição §VI).
- Os arquivos de segredo MUST ter permissão 600.
- As portas publicadas pelo Compose MUST escutar só em localhost.
- A CLI age como administrador porque roda na máquina do servidor; o acesso a essa máquina é,
  portanto, acesso de administrador.
- Comandos destrutivos não pedem confirmação (§3.2); agentes SHOULD ser autorizados com isso
  em vista.

## 17. Considerações de privacidade (LGPD)

- Da equipe, de dado pessoal, a CLI guarda e mostra só o e-mail; além dele, o papel e as
  datas de inclusão e de alteração. Mensagens de erro não repetem o e-mail.
- Textos livres (instruções adicionais dos presets) e relatórios MUST NOT conter nomes de
  pessoas (constituição §VI).
- Exemplos no `--help` e neste documento usam dados fictícios.

## 18. Referências

### 18.1. Normativas

- [RFC2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels",
  BCP 14, RFC 2119, março de 1997.
- [RFC8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14,
  RFC 8174, maio de 2017.
- [RFC3339] Klyne, G. e Newman, C., "Date and Time on the Internet: Timestamps", RFC 3339,
  julho de 2002.
- Constituição do projeto: [docs/constitution.md](constitution.md).
- Requisitos: [docs/requirements/features.md](requirements/features.md).

### 18.2. Informativas

- [RFC7322] Flanagan, H. e Ginoza, S., "RFC Style Guide", RFC 7322, setembro de 2014. Modelo
  de estrutura deste documento.
