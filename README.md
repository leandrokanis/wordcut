# Wordcut

Ferramentas para transformar a transmissão de um culto em:

1. **Pregação** — o trecho da pregação, recortado com precisão de quadro.
2. **Cortes verticais** (Reels/Shorts) — colagens de 40–75 s editadas palavra a palavra:
   sem hesitações nem pausas mortas, com a janela 9:16 acompanhando o pregador e legenda
   sincronizada por palavra.

> Estado: em uso. As duas etapas funcionam de ponta a ponta; a primeira pregação processada
> foi a de 2026-10-18.

## Documentação

- [Constituição](docs/constitution.md): princípios e restrições de arquitetura.
- [Requisitos](docs/requirements/features.md) e [protótipo](docs/prototype/wordcut.html).
- [CLI](docs/cli.md): especificação dos comandos `wordcut`.
- [Arquitetura](docs/architecture/README.md) (C4 e fluxos) e [ADRs](docs/adr/README.md).
- [Como contribuir](CONTRIBUTING.md), [segurança](SECURITY.md) e [changelog](CHANGELOG.md).
- [Roadmap do MVP](specs/roadmap.md).

A aplicação web está em construção como monorepo orquestrado por Docker Compose
(ADR-0002, ADR-0003); a API e a web ainda são esqueletos. As seções de uso descrevem o fluxo
atual, pela CLI anterior.

## Arquitetura atual

O fluxo roda no host com GPU (ex.: "leitao"), conduzido por duas skills do Claude Code em
`skills/`. O Mac só traz os vídeos prontos por `scp`.

```
host com GPU ("leitao")
  live do YouTube ─▶ info ─▶ transcribe-live ─▶ cut ─▶ pasta da pregação
                                                        ├─ <pasta>.mp4
                                                        ├─ palavras.json
                                                        ├─ roteiros/*.json ─▶ preview ─▶ short
                                                        └─ cortes/*.mp4
```

A transcrição (WhisperX large-v3 + alinhamento wav2vec2 pt) também pode ser delegada por SSH
a partir de outra máquina: só o áudio 16 kHz mono trafega, e só pela rede local.

## Estrutura

Monorepo com um projeto por aplicação ([ADR-0002](docs/adr/0002-monorepo.md)), orquestrado por
Docker Compose ([ADR-0003](docs/adr/0003-docker-compose.md)):

```
packages/core/       domínio (pacote Python `wordcut`)
apps/cli/            CLI `wordcut` (pacote `wordcut_cli`)
apps/api/            API HTTP, FastAPI (pacote `wordcut_api`)
apps/web/            interface, React + Vite + TypeScript
docker/python/       imagem das apps Python (alvos `api` e `cli`)
compose.yaml         serviços `api`, `web` e `cli`
```

Os três projetos Python formam um workspace `uv` com um único `uv.lock` na raiz.

## Instalação

Máquina principal, da raiz do repositório:

```sh
uv sync --all-packages
```

Host com GPU (CUDA), uma vez:

```sh
python3 -m venv ~/.local/share/wordcut/venv
~/.local/share/wordcut/venv/bin/pip install whisperx
```

Para baixar do YouTube (na máquina que roda o pipeline):

- `yt-dlp[default]` e [Deno](https://deno.land) (resolve o desafio JavaScript do YouTube);
- no Linux, o [build estático de ffmpeg do yt-dlp](https://github.com/yt-dlp/FFmpeg-Builds)
  extraído em `~/.local/share/wordcut/ffmpeg/` — o ffmpeg 6.1 do Ubuntu trava
  ao baixar trechos;
- cookies de uma sessão logada no YouTube em
  `~/.config/wordcut/youtube-cookies.txt` (permissão `600`, nunca no repositório).

Para usar as skills, ligue-as ao Claude Code:

```sh
ln -s ~/cortes-pregacao/skills/video-cortar-pregacao ~/.claude/skills/
ln -s ~/cortes-pregacao/skills/video-corte-vertical ~/.claude/skills/
```

## Uso

O caminho normal é pelas skills: `video-cortar-pregacao` com o link da live e, depois,
`video-corte-vertical` na pasta gerada. Elas chamam os comandos abaixo e pedem aprovação
antes de cortar e de renderizar.

### Estado da máquina (CLI nova)

A CLI nova ([docs/cli.md](docs/cli.md), [ADR-0012](docs/adr/0012-contrato-da-cli.md)) convive
com os comandos abaixo até a migração. Para o estado da máquina e as tarefas, ela tem `status`
e `task`:

```sh
uv run wordcut status          # máquina livre ou qual tarefa segura a trava, e as em andamento
uv run wordcut status --json   # o mesmo em JSON; --json vale antes ou depois do comando
uv run wordcut task list [--status running]   # tarefas, da mais recente para a mais antiga
uv run wordcut task wait <id>  # espera a tarefa: progresso no stderr, resultado no stdout
uv run wordcut sermon process <id> [--force] [--wait]   # baixa a faixa, transcreve e corta
uv run wordcut sermon show <id> --transcript            # a pregação e suas frases
```

As operações pesadas rodam como tarefas: sem `--wait`, voltam na hora com o `task_id` e
seguem num processo destacado que segura a trava (saída em `tasks/<id>.log`); com `--wait`,
rodam em primeiro plano ([ADR-0013](docs/adr/0013-trava-herdada-pelo-processo-da-tarefa.md)).
O processamento (`sermon process`) usa o mundo externo por uma porta e deixa a pregação
`failed` na leitura se o processo morrer
([ADR-0014](docs/adr/0014-processamento-por-portas-e-estado-na-leitura.md)); as mídias ficam
em `media/sermons/<id>/` na pasta de dados.

Os dados (banco SQLite, criado e migrado na primeira chamada, e a trava `processing.lock`)
ficam em `~/.local/share/wordcut/`, ou em `WORDCUT_HOME` quando definida. Essa pasta deve
estar em disco local: a trava usa `flock`, que não é garantido em sistema de arquivos de rede.
Com `--json`, um erro sai no stdout como `{"error": {"code": …}}`; o código de saída diz o
tipo (2 uso inválido, 4 máquina ocupada; tabela em `docs/cli.md` §5).

### 1. Pregação

```sh
uv run wordcut info <link>                    # título, data do culto, duração, se terminou
uv run wordcut transcribe-live <link> --dir "<pasta>" [--start HH:MM:SS --end HH:MM:SS]
uv run wordcut overview "<pasta>/trabalho/live-palavras.json" [--words --start … --end …]
uv run wordcut cut <link> --dir "<pasta>" --first-word <início> --last-word <fim>
```

A pasta segue o padrão `~/Videos/Pregações/AAAA-MM-DD - Título - Referência/`. O `cut` grava
`<pasta>.mp4` e `palavras.json`, com tempos relativos ao vídeo; os intermediários ficam em
`trabalho/`.

### 2. Cortes verticais

Cada corte é um roteiro em `<pasta>/roteiros/<slug>.json`: título, trechos (`start`/`end` em
segundos do `.mp4`) e correções de grafia da legenda. Critérios e formato estão em
`skills/video-corte-vertical/sugerir-cortes.md`.

```sh
uv run wordcut overview "<pasta>/palavras.json"              # pregação, uma frase por linha
uv run wordcut preview "<pasta>/roteiros/<slug>.json" --dir "<pasta>"   # texto montado
uv run wordcut short "<pasta>/roteiros/<slug>.json" --dir "<pasta>" [--alvo 0.7]
```

O `short` grava `cortes/corte - <título>.mp4` em 1080x1920 e nunca sobrescreve (cria `-v2`,
`-v3`…). Use `--alvo` quando houver mais de uma pessoa em quadro (0 = esquerda).

### Transcrição avulsa

```sh
uv run wordcut transcribe pregacao.mp4 -o palavras.json                # nesta máquina
uv run wordcut transcribe pregacao.mp4 -o palavras.json --host leitao  # por SSH
```

## Desenvolvimento

Python, da raiz (testes de `packages/core`, `apps/cli` e `apps/api`):

```sh
uv sync --all-packages
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

Web:

```sh
npm --prefix apps/web ci
npm --prefix apps/web test
npm --prefix apps/web run typecheck && npm --prefix apps/web run lint
npm --prefix apps/web run build
```

Em desenvolvimento, `npm --prefix apps/web run dev` serve a web e repassa `/api` para a API
local em `127.0.0.1:8781`:

```sh
uv run uvicorn wordcut_api.app:create_app --factory --host 127.0.0.1 --port 8781
```

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
  imagem nem no contexto de build (`.dockerignore`).

Crie os dois diretórios antes do primeiro `up`; se não existirem, o Docker os cria como
`root`. Portas e usuário mudam por variável de ambiente: `WORDCUT_WEB_PORT`,
`WORDCUT_API_PORT`, `UID`, `GID`. A imagem sai sem WhisperX; o argumento de build `WITH_ASR`
(`WORDCUT_WITH_ASR=1`) fica para o item de processamento do roadmap, junto com a GPU.

## Licença

MIT. A fonte Open Sans incluída em `packages/core/src/wordcut/assets/fonts/` é distribuída sob a
SIL Open Font License 1.1 (`OFL.txt`).
