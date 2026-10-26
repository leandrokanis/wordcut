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
| 1 | `internal_error` | erro interno inesperado |
| 2 | `invalid_argument` | uso inválido: argumento faltando, mal formado ou fora da faixa |
| 3 | `not_found` | recurso inexistente |
| 4 | `busy` | máquina ocupada pela trava de processamento |
| 5 | regra violada | a operação contraria uma regra de negócio (§5.3) |
| 6 | falha externa | YouTube, OpenRouter ou rede falharam (§5.3) |
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
| `invalid_argument` | 2 | argumento inválido; `details.argument` diz qual |
| `not_found` | 3 | ID ou e-mail inexistente |
| `busy` | 4 | outra tarefa segura a trava; `details` traz a tarefa |
| `live_not_finished` | 5 | processar uma live que ainda não terminou |
| `sermon_not_trimmed` | 5 | processar sem bordas definidas |
| `sermon_too_short` | 5 | bordas com menos de 1 minuto |
| `sermon_not_processed` | 5 | operação que exige a pregação processada |
| `would_discard_edits` | 5 | reprocessar pregação com cortes editados, sem `--force` |
| `spelling_too_different` | 5 | correção de grafia barrada pela trava; `details` traz a distância e o limite |
| `default_preset` | 5 | apagar o preset padrão |
| `last_admin` | 5 | remover ou rebaixar o último administrador |
| `youtube_error` | 6 | falha ao consultar ou baixar do YouTube |
| `llm_error` | 6 | falha do LLM depois da nova tentativa (constituição §III) |
| `network_error` | 6 | falha de rede genérica |

Códigos novos MAY ser acrescentados; os existentes MUST NOT mudar de saída.

## 6. Tarefas

### 6.1. Modelo

`sermon process`, `sermon suggest` e `cut render` são **tarefas**: rodam em segundo plano,
têm ID e estado gravados no SQLite e podem ser acompanhadas.

| Tipo (`kind`) | Comando | Trava |
|---|---|:-:|
| `process` | `sermon process` | ✅ |
| `render` | `cut render` | ✅ |
| `suggest` | `sermon suggest` | — |

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
  tarefa, marcá-la `failed` e sair com 130.
- Ctrl+C em `task wait` de uma tarefa destacada só para a espera; a tarefa continua.
- Uma tarefa encontrada `running` sem processo vivo (reinício da máquina) MUST ser marcada
  `failed` na próxima leitura (1.1.c).

Não há cancelamento de tarefa nesta versão.

## 7. Pregações (`sermon`)

Estados (`status`): `created` → `trimmed` → `processing` → `processed`, ou `failed`.

### 7.1. `sermon create <link> [--start T --end T] [--process] [--wait]`

Cria a pregação a partir do link da live e devolve título, data do culto e duração (1.1.a).

- O mesmo vídeo duas vezes MUST devolver a pregação existente, com `"created": false` e
  saída 0.
- Live não terminada: cria, avisa no stderr e devolve `"live_finished": false` (1.1.a.2).
- `--start`/`--end`: delimita na criação, como `sermon trim`.
- `--process`: em seguida processa, como `sermon process`; exige `--start` e `--end`.

```
wordcut sermon create https://youtube.com/live/… --start 1:02:10 --end 1:48:30 --process --wait
```

### 7.2. `sermon list [--status S]` · `sermon show <id> [--transcript]`

- `list`: ID, título, data, duração da pregação, estado e quantidade de cortes por estado.
- `show`: os mesmos dados, mais as bordas na live, a última tarefa e os cortes.
- `--transcript`: acrescenta a transcrição, uma frase por linha, com ID da frase, tempo e IDs
  da primeira e da última palavra.

### 7.3. `sermon trim <id> --start T --end T`

Define as bordas da pregação, em tempo da live (1.1.b.2).

- Faixa com menos de 1 minuto: `sermon_too_short`.
- Numa pregação processada, só grava as bordas; reprocessar é `sermon process --force`.

### 7.4. `sermon process <id> [--force] [--wait]`

Tarefa com trava (1.1.c): baixa só a faixa delimitada, transcreve na GPU local, corta em 16:9 e
pede as sugestões ao LLM com o preset padrão (2.1.b.1).

- Exige bordas (`sermon_not_trimmed`) e live terminada (`live_not_finished`).
- Numa pregação já processada, MUST exigir `--force`, porque os cortes e suas edições são
  refeitos (1.1.b.3); sem ele, `would_discard_edits`.
- Uma pregação `failed` é refeita pelo mesmo comando (1.1.c.3).

### 7.5. `sermon download <id> [-o caminho]`

Copia a pregação 16:9 para `caminho`, ou para a pasta atual com um nome legível (data e
título). Devolve o caminho de destino (1.1.d).

### 7.6. `sermon suggest <id> [--preset <id>] [--wait]` — administrador

Tarefa sem trava: pede nova sugestão ao LLM (2.1.b.2), com o preset indicado ou o padrão.

- Os cortes `suggested` não editados são substituídos.
- Os cortes escolhidos, descartados ou editados permanecem.
- Numa pregação não processada, falha com `sermon_not_processed`.

### 7.7. `sermon delete <id>` — administrador

Apaga a pregação, seus cortes, exportações e mídias (1.2.b). Falha com `busy` se uma tarefa
da pregação estiver rodando.

## 8. Cortes (`cut`)

Estados (`status`): `suggested`, `chosen`, `discarded`.

### 8.1. `cut list --sermon <id> [--status S]`

Lista os cortes da pregação com texto montado, duração e estado (1.1.e.1). Descartados vêm
por último.

### 8.2. `cut show <id>`

Devolve o corte completo:

- texto montado, duração, estado e faixa na pregação;
- `segments`: trechos em ordem, no formato de `cut segments` (§8.10), com tempos e texto;
- `words`: palavras do corte com `word_id`, texto, tempos e correção aplicada, se houver;
- `caption`: estilo da legenda;
- `render_options`: últimas opções de exportação;
- `renders`: histórico de exportações.

### 8.3. `cut preview <id>`

Devolve a sequência que a prévia toca (1.1.g): cada trecho com início e fim na pregação e o
texto. Não toca vídeo nem renderiza; nunca é bloqueado pela trava.

### 8.4. `cut choose <id>` · `cut discard <id>` · `cut restore <id>`

Mudam o estado (1.1.e). `restore` devolve um corte descartado a `suggested`. Nenhum deles
altera o conteúdo (constituição §I).

### 8.5. `cut fix-word <id> <word_id> <texto>`

Corrige a grafia de uma palavra da legenda, só neste corte (1.1.f.2).

- A correção MUST passar pela trava de grafia por distância de edição (1.1.f.3); se não
  passar, `spelling_too_different`, com `details.distance` e `details.limit`.
- `<texto>` igual ao original remove a correção.

### 8.6. `cut caption <id> [opções]`

Sem opções, mostra o estilo atual. Com opções, altera o estilo, que vale para todas as legendas
do corte (1.1.f.4, 1.1.f.5).

| Opção | Valores |
|---|---|
| `--on` · `--off` | liga ou desliga a legenda |
| `--font <nome>` | fontes oferecidas pela interface |
| `--size <px>` | tamanho em pixels, no quadro 1080×1920 |
| `--color <#RRGGBB>` | cor do texto |
| `--position top\|center\|bottom` | posição |
| `--offset <%>` | ajuste fino da altura |
| `--border <px>` · `--border-color <#RRGGBB>` | contorno |
| `--shadow none\|soft\|strong` | sombra |
| `--reset` | volta ao estilo da igreja (Open Sans Bold, #FFD600, contorno preto, centro) |

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
  `wordcut cut render 34` repete a exportação anterior.
- `--caption`/`--no-caption` alteram o mesmo estado de `cut caption --on/--off`.
- `--estimate` devolve a duração estimada e o resumo das opções, sem renderizar, sem salvar as
  opções e sem pegar a trava.
- Com `--wait`, devolve a exportação (§9). Sem `--wait`, devolve a tarefa; ao terminar,
  `task show` traz `render_id`.

### 8.8. `cut create --sermon <id> --start T --end T` — administrador

Cria um corte do zero com as frases da faixa, já `chosen` (2.1.c.4).

### 8.9. `cut range <id> [--start T] [--end T]` · `cut move <id> --by ±S` — administrador

Ajustam a faixa contínua do corte (2.1.c.3).

- `range`: redimensiona; as frases que ficam de fora saem do corte.
- `move`: desloca a faixa inteira em `S` segundos; as frases escolhidas acompanham e encostam
  na frase mais próxima.

### 8.10. `cut segments <id> --file <arquivo|->` — administrador

Define o que entra no corte e em que ordem (2.1.c.1, 2.1.c.2). Lê, do arquivo ou do stdin,
uma lista ordenada de faixas de palavras:

```json
[
  { "from_word": 1201, "to_word": 1230 },
  { "from_word": 1188, "to_word": 1199 }
]
```

- A lista cobre escolher frases, reordenar trechos e dividir uma frase.
- As palavras MUST estar dentro da faixa do corte; senão, `invalid_argument`.
- `cut show --json` devolve `segments` no mesmo formato, para editar e devolver.

### 8.11. `cut delete <id>` — administrador

Apaga o corte e suas exportações (1.2.b).

## 9. Exportações (`render`)

Uma exportação é o arquivo renderizado de um corte, registrado nele com data, duração e
opções (1.1.i).

- `render list --cut <id>`: histórico de exportações do corte.
- `render show <id>`: `{id, cut_id, path, duration, created_at, options}`. `path` é o caminho
  local, já que a CLI roda no servidor (1.1.h.2).
- `render download <id> [-o caminho]`: copia o arquivo para `caminho`, ou para a pasta atual
  com um nome legível. Devolve o destino.

## 10. Tarefas (`task`) e estado (`status`)

- `task list [--status S] [--kind K]`: tarefas recentes.
- `task show <id>`: tipo, estado, recurso, início, fim, progresso, erro e resultado
  (`sermon_id`, `render_id`).
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
| `--instructions-file <arquivo\|->` | instruções adicionais (texto livre) |

- `preset set-default <id>`.
- `preset delete <id>`: o preset padrão não pode ser apagado (`default_preset`).

## 12. Equipe (`member`)

Comandos do administrador (1.2.a). Membros são identificados pelo e-mail.

- `member list`
- `member add <email> --role assistant|admin`
- `member set-role <email> assistant|admin`
- `member remove <email>`

Remover ou rebaixar o último administrador falha com `last_admin`.

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

- Da equipe, a CLI guarda e mostra só o e-mail e o papel.
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
