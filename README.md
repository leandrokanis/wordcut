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
(ADR-0002, ADR-0003). As seções abaixo descrevem o fluxo atual, pela CLI anterior.

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

## Instalação

Máquina principal:

```sh
uv sync
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

```sh
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

## Licença

MIT. A fonte Open Sans incluída em `src/wordcut/assets/fonts/` é distribuída sob a
SIL Open Font License 1.1 (`OFL.txt`).
