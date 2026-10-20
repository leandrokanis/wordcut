# cortes-pregacao

Ferramentas para transformar a transmissão de um culto em:

1. **Pregação** — o trecho da pregação, recortado com precisão de quadro.
2. **Cortes verticais** (Reels/Shorts) — colagens de 40–75 s editadas palavra a palavra:
   sem hesitações nem pausas mortas, com a janela 9:16 acompanhando o pregador e legenda
   sincronizada por palavra.

> Estado: em desenvolvimento. Fase 1 (transcrição por palavra) implementada.

## Arquitetura

```
Mac (orquestra, edita, renderiza)          host com GPU (ex.: "leitao")
  extrai áudio 16 kHz mono  ── scp ──▶       WhisperX large-v3 + alinhamento wav2vec2 pt
  palavras.json             ◀── scp ──       (venv em ~/.local/share/cortes-pregacao)
```

Só o áudio trafega, e só pela rede local.

## Instalação

Máquina principal:

```sh
uv sync
```

Host com GPU (CUDA), uma vez:

```sh
python3 -m venv ~/.local/share/cortes-pregacao/venv
~/.local/share/cortes-pregacao/venv/bin/pip install whisperx
```

Para baixar do YouTube (na máquina que roda o pipeline):

- `yt-dlp[default]` e [Deno](https://deno.land) (resolve o desafio JavaScript do YouTube);
- no Linux, o [build estático de ffmpeg do yt-dlp](https://github.com/yt-dlp/FFmpeg-Builds)
  extraído em `~/.local/share/cortes-pregacao/ffmpeg/` — o ffmpeg 6.1 do Ubuntu trava
  ao baixar trechos;
- cookies de uma sessão logada no YouTube em
  `~/.config/cortes-pregacao/youtube-cookies.txt` (permissão `600`, nunca no repositório).

## Uso

Na própria máquina com GPU:

```sh
uv run cortes transcribe pregacao.mp4 -o palavras.json
```

De outra máquina, delegando a transcrição por SSH (só o áudio trafega):

```sh
uv run cortes transcribe pregacao.mp4 -o palavras.json --host leitao
```

## Desenvolvimento

```sh
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

## Licença

MIT. A fonte Open Sans incluída em `src/cortes_pregacao/assets/fonts/` é distribuída sob a
SIL Open Font License 1.1 (`OFL.txt`).
