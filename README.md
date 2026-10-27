# Wordcut

Ferramentas para transformar a transmissão de um culto em:

1. **Pregação** — o trecho da pregação, recortado com precisão de quadro.
2. **Cortes verticais** (Reels/Shorts) — colagens de 40–75 s editadas palavra a palavra:
   sem hesitações nem pausas mortas, com a janela 9:16 acompanhando o pregador e legenda
   sincronizada por palavra.

> Estado: em uso pela CLI `wordcut`, da live às exportações. A API já tem as rotas de
> pregações, tarefas e estado; o restante da API e a web estão em construção (roadmap, fases
> 2 e 3).

## Documentação

- [Constituição](docs/constitution.md): princípios e restrições de arquitetura.
- [Requisitos](docs/requirements/features.md) e [protótipo](docs/prototype/wordcut.html).
- [CLI](docs/cli.md): especificação dos comandos `wordcut`.
- [API](docs/api.md): rotas HTTP, corpos, status e eventos de progresso.
- [Arquitetura](docs/architecture/README.md) (C4 e fluxos) e [ADRs](docs/adr/README.md).
- [Como contribuir](CONTRIBUTING.md), [segurança](SECURITY.md) e [changelog](CHANGELOG.md).
- [Issues](https://github.com/leandrokanis/wordcut/issues): bugs e histórias em andamento.

## Como funciona

A pregação nasce do link da live e das suas bordas em tempo da live. O processamento baixa
só essa faixa, transcreve com o WhisperX (tempo por palavra), ajusta as bordas à primeira e
à última palavra e corta o vídeo 16:9 com fades. Em seguida, um LLM sugere cortes com os
critérios do preset padrão. Cada corte é revisado em texto e exportado em 9:16, com
hesitações e pausas removidas, a janela acompanhando o pregador e legenda por palavra.

```
live do YouTube ─▶ sermon create ─▶ sermon process ─▶ pregação 16:9 + transcrição
                                                    └▶ cortes sugeridos ─▶ cut render ─▶ 9:16
```

Tudo fica no banco SQLite e em `media/` na pasta de dados; o operador baixa o resultado com
`sermon download` e `render download`.

## Estrutura

Monorepo com um projeto por aplicação ([ADR-0002](docs/adr/0002-monorepo.md)), orquestrado por
Docker Compose ([ADR-0003](docs/adr/0003-docker-compose.md)):

```
packages/core/       domínio e camada de serviço (pacote Python `wordcut`)
apps/cli/            CLI `wordcut` (pacote `wordcut_cli`)
apps/api/            API HTTP, FastAPI (pacote `wordcut_api`)
apps/web/            interface, React + Vite + TypeScript
docker/python/       imagem das apps Python (alvos `api` e `cli`)
skills/              guias do Claude Code para usar a CLI
compose.yaml         serviços `api`, `web` e `cli`
```

Os três projetos Python formam um workspace `uv` com um único `uv.lock` na raiz.

## Instalação

Da raiz do repositório:

```sh
uv sync --all-packages
```

A transcrição roda nesta máquina, com GPU (CUDA), num ambiente próprio do WhisperX. Uma vez:

```sh
python3 -m venv ~/.local/share/wordcut/venv
~/.local/share/wordcut/venv/bin/pip install whisperx
```

Para baixar do YouTube:

- `yt-dlp[default]` e [Deno](https://deno.land) (resolve o desafio JavaScript do YouTube);
- no Linux, o [build estático de ffmpeg do yt-dlp](https://github.com/yt-dlp/FFmpeg-Builds)
  extraído em `~/.local/share/wordcut/ffmpeg/` — o ffmpeg 6.1 do Ubuntu trava
  ao baixar trechos;
- cookies de uma sessão logada no YouTube, em formato Netscape, gravados pela CLI na pasta de
  segredos (`~/.config/wordcut`, ou `WORDCUT_CONFIG`), nunca no repositório.

Configuração do administrador, uma vez (os segredos só entram pelo stdin):

```sh
uv run wordcut settings set-cookies < cookies.txt
uv run wordcut settings set --model <id do OpenRouter> --whisper-model large-v3
uv run wordcut settings set-key < chave.txt
uv run wordcut settings show
```

Sem modelo ou chave do LLM, a pregação é processada sem cortes sugeridos.

Para usar as skills, ligue-as ao Claude Code:

```sh
ln -s ~/cortes-pregacao/skills/video-cortar-pregacao ~/.claude/skills/
ln -s ~/cortes-pregacao/skills/video-corte-vertical ~/.claude/skills/
```

## Uso

A especificação completa está em [docs/cli.md](docs/cli.md)
([ADR-0012](docs/adr/0012-contrato-da-cli.md)). Todo comando aceita `--json` e mostra um
exemplo no `--help`. As skills `video-cortar-pregacao` e `video-corte-vertical` conduzem o
mesmo fluxo pelo Claude Code.

### 1. Pregação

```sh
uv run wordcut sermon create <link> --start 1:02:10 --end 1:48:30 --process --wait
uv run wordcut sermon show <id> --transcript   # bordas, frases e cortes sugeridos
uv run wordcut sermon trim <id> --start <T> --end <T>   # corrige as bordas, em tempo da live
uv run wordcut sermon process <id> --force --wait       # e processa de novo
uv run wordcut sermon download <id> -o ~/Vídeos/        # copia a pregação 16:9
```

Sem `--start` e `--end`, o `sermon create` só cria a pregação e mostra título, data do culto
e duração da live; as bordas vêm depois, por `sermon trim`, e o processamento, por
`sermon process <id> --wait`.

### 2. Cortes verticais

```sh
uv run wordcut cut list --sermon <id>          # cortes com texto montado, duração e estado
uv run wordcut cut preview <corte>             # a sequência de trechos que o corte toca
uv run wordcut cut choose <corte>              # ou discard / restore
uv run wordcut cut fix-word <corte> <word_id> <texto>   # grafia de uma palavra da legenda
uv run wordcut cut render <corte> --estimate   # só a duração, sem exportar
uv run wordcut cut render <corte> --pauses short --wait   # exporta em 9:16
uv run wordcut render list --cut <corte>
uv run wordcut render download <exportação> -o ~/Vídeos/
```

As opções da exportação (hesitações, gaguejos, pausas, resolução, qualidade, emendas, fade,
normalização e legenda) ficam salvas no corte, e a omitida usa a última salva. Uma nova
sugestão de cortes, com outro preset, sai de `sermon suggest <id> --preset <preset>`; os
critérios estão em `criteria list` e nos presets (`preset list`, `preset show`).

### Tarefas e estado da máquina

```sh
uv run wordcut status                          # máquina livre ou qual tarefa segura a trava
uv run wordcut task list --status running      # tarefas, da mais recente para a mais antiga
uv run wordcut task wait <id>                  # progresso no stderr, resultado no stdout
```

As operações pesadas rodam como tarefas: sem `--wait`, voltam na hora com o `task_id` e
seguem num processo destacado que segura a trava (saída em `tasks/<id>.log`); com `--wait`,
rodam em primeiro plano ([ADR-0013](docs/adr/0013-trava-herdada-pelo-processo-da-tarefa.md)).
O processamento (`sermon process`) usa o mundo externo por uma porta e deixa a pregação
`failed` na leitura se o processo morrer
([ADR-0014](docs/adr/0014-processamento-por-portas-e-estado-na-leitura.md)); as mídias ficam
em `media/sermons/<id>/` na pasta de dados. O progresso sobe também dentro do download e da
transcrição, sem nunca voltar, gravado no máximo uma vez por segundo
([ADR-0024](docs/adr/0024-progresso-dentro-das-etapas.md)). Ao fim, ele pede os cortes ao LLM com o preset
padrão; sem modelo ou chave configurados, ou com o OpenRouter falhando, a pregação fica
processada sem cortes e o erro aparece no `sermon show`
([ADR-0016](docs/adr/0016-sugestao-por-porta-com-falha-na-pregacao.md)). A exportação
(`cut render`) também usa uma porta, grava as opções no corte e só deixa o arquivo em
`media/cuts/<corte>/<exportação>.mp4` quando termina bem
([ADR-0018](docs/adr/0018-exportacao-por-portas-sem-arquivo-parcial.md)).

Os dados (banco SQLite, criado e migrado na primeira chamada, mídias e a trava
`processing.lock`) ficam em `~/.local/share/wordcut/`, ou em `WORDCUT_HOME` quando definida.
Essa pasta deve estar em disco local: a trava usa `flock`, que não é garantido em sistema de
arquivos de rede. Com `--json`, um erro sai no stdout como `{"error": {"code": …}}`; o código
de saída diz o tipo (2 uso inválido, 4 máquina ocupada; tabela em `docs/cli.md` §5). Erro de
uso nunca repete o valor digitado
([ADR-0015](docs/adr/0015-erro-de-uso-nao-repete-valor-digitado.md)).

## Desenvolvimento

Python, da raiz (testes de `packages/core`, `apps/cli` e `apps/api`):

```sh
uv sync --all-packages
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

A suíte não usa a rede real: ela define `WORDCUT_FORBID_NETWORK`, e com essa variável o
OpenRouter e o YouTube recusam com `network_error`, até numa tarefa destacada
([ADR-0017](docs/adr/0017-testes-sem-rede-real.md)).

Web:

```sh
npm --prefix apps/web ci
npm --prefix apps/web test
npm --prefix apps/web run typecheck && npm --prefix apps/web run lint
npm --prefix apps/web run build
```

Em desenvolvimento, `npm --prefix apps/web run dev` serve a web e repassa `/api` para a API
local em `127.0.0.1:8781` (o uvicorn escuta só em `127.0.0.1` por padrão):

```sh
WORDCUT_DEV_EMAIL=admin@exemplo.org uv run uvicorn wordcut_api.app:create_app --factory --port 8781
```

A API identifica quem chama pelo token do Cloudflare Access (`WORDCUT_ACCESS_TEAM_DOMAIN` e
`WORDCUT_ACCESS_AUD`). Sem o Access, `WORDCUT_DEV_EMAIL` fixa o e-mail de um membro da equipe,
só em desenvolvimento; sem nenhum dos dois, toda rota menos `/api/health` dá 401
([ADR-0019](docs/adr/0019-identidade-e-erros-na-api.md)). Configurações, critérios, presets e
equipe são só do administrador; o e-mail de um membro e os segredos vão só no corpo, e os
segredos nunca voltam ([ADR-0021](docs/adr/0021-rotas-de-cortes-e-administracao-na-api.md)).
As rotas estão em [docs/api.md](docs/api.md); em desenvolvimento, o esquema OpenAPI fica em
`/api/docs`.

A web navega pelos três níveis (`/`, `/sermons/:id`, `/cuts/:id`) e pelas configurações
(`/settings`, só do administrador) com o React Router, fala com a API por um cliente próprio
e mostra a tela só depois de `GET /api/me`. O visual segue o protótipo
(`docs/prototype/wordcut.html`), com as fontes Geist empacotadas no build e nenhum recurso de
outro host ([ADR-0022](docs/adr/0022-arquitetura-do-cliente-web.md)), salvo a prévia da live.

Dentro de uma pregação (nível 2), a prévia 16:9 e a timeline ficam sempre visíveis: o
assistente puxa as bordas do clipe ou as traz ao cursor com I e O, e elas são salvas sozinhas.
Antes do processamento, e fora do trecho processado, a prévia é o embed do YouTube
(`youtube-nocookie.com`); dentro dele, o vídeo processado servido pela API
([ADR-0023](docs/adr/0023-previa-da-live-pelo-embed-do-youtube.md)). Processar e Reprocessar
acompanham a tarefa pelos eventos SSE.

## Docker Compose

O projeto Compose se chama `wordcut`. A `web` responde em `http://127.0.0.1:8780/` e repassa
`/api` para a `api`, que também fica em `127.0.0.1:8781`; nenhuma porta escuta fora do
`localhost`.

```sh
docker compose up -d --build api web
curl http://127.0.0.1:8780/api/health          # {"status":"ok"}
docker compose run --rm cli --help             # a CLI, sem subir com `up`
docker compose down
```

Os contêineres Python rodam com o usuário do host (`UID`/`GID`, padrão `1000`) e montam:

- `${WORDCUT_DATA:-~/.local/share/wordcut}` em `/data` (`WORDCUT_HOME`), o estado compartilhado
  com a CLI do host;
- `~/.config/wordcut` em `/config` (`WORDCUT_CONFIG`), só leitura. Segredos nunca entram na
  imagem nem no contexto de build (`.dockerignore`). Por isso, gravar a chave do LLM ou os
  cookies pela web dá 409 `config_not_writable`; grave-os pela CLI no host
  (`wordcut settings set-key`, `set-cookies`).

Crie os dois diretórios antes do primeiro `up`; se não existirem, o Docker os cria como
`root`. Portas e usuário mudam por variável de ambiente: `WORDCUT_WEB_PORT`,
`WORDCUT_API_PORT`, `UID`, `GID`. O Access do time chega à `api` por `WORDCUT_ACCESS_TEAM_DOMAIN`
e `WORDCUT_ACCESS_AUD`; o Compose nunca repassa `WORDCUT_DEV_EMAIL`. A imagem sai sem WhisperX; o argumento de build `WITH_ASR`
(`WORDCUT_WITH_ASR=1`) fica para o item de processamento do roadmap, junto com a GPU.

## Licença

MIT. A fonte Open Sans incluída em `packages/core/src/wordcut/assets/fonts/` é distribuída sob a
SIL Open Font License 1.1 (`OFL.txt`).
