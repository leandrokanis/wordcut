---
name: video-corte-vertical
description: Gera corte vertical 9:16 (1080x1920) de pregação para Reels/Shorts, com a janela acompanhando o pregador (detecção de rosto + suavização tipo operador de câmera) e legenda queimada. Também sugere, a partir da transcrição, os melhores trechos para corte (cristológicos, aplicação prática, frases marcantes; filtra triunfalismo, alegoria e teologia frágil). Use quando o usuário pedir corte vertical, Reels, Shorts, TikTok, "janela seguindo o pregador", "sugerir cortes" ou "melhores trechos" de um vídeo de culto.
---

# Corte vertical que acompanha o pregador

## Entradas

- **Fonte**: vídeo original do culto (não o corte horizontal da pregação).
- **Trecho**: início e fim com milissegundos (`HH:MM:SS.mmm`).
- **Legenda** (opcional): `.srt` com tempos relativos ao corte (começando em 00:00:00). Se o usuário der o `.srt`/`.txt` do culto inteiro, extraia os blocos do trecho, desloque para 00:00:00, descarte vazios, aplique as correções pedidas e **mostre o texto antes de queimar**.
- **Pasta de saída**: se não informada, `~/Movies/Pregações` (avise).
- **Nome**: o que o usuário pedir; se não pedir, gere sem perguntar `corte - <frase marcante do trecho>.mp4` (curta, com maiúscula inicial). Salve direto, sem confirmar. Se já existir, o script usa `-v2`, `-v3`… automaticamente (nunca sobrescreve); informe o nome final impresso em `pronto:`.

Se faltar a fonte, pergunte. Se faltar o trecho, vá para a etapa 0.

## 0. Sugerir cortes (quando o usuário não informar o trecho)

Siga `sugerir-cortes.md` (critérios e processo) e calibre com `exemplos.md`. Apresente 3–5 opções com tempos, espere o usuário escolher e só então siga para o fluxo abaixo. Registre a decisão em `exemplos.md`.

## Fluxo

1. Confirme a fonte com `ffprobe` (resolução, fps, duração). Se der `Operation not permitted` em `~/Downloads`, é TCC do macOS: o terminal precisa de Acesso Total ao Disco.
2. Rode o script **em background** (detecção leva ~5 s de processamento por segundo de vídeo em 720p):
   ```
   python3 ~/.claude/skills/video-corte-vertical/vertical.py \
     --fonte "<vídeo>" --ini 01:00:51.300 --fim 01:02:22.910 \
     --srt "<legenda.srt>" --saida "<pasta>/<nome>.mp4" \
     --trabalho "<scratchpad>/vertical"
   ```
   Use `--srt-offset -0.3` etc. se a legenda estiver deslocada em relação ao corte.
   Se houver mais de uma pessoa em pé (testemunho, entrevista), olhe um quadro do original e passe `--alvo 0.7` (posição horizontal de quem fala, 0 = esquerda, 1 = direita); sem isso o script segue o maior rosto.
3. Leia o resumo impresso: quadros com detecção, cortes de cena, distância máxima pregador-centro. Se a distância máxima chegar perto da meia janela, aumente `VMAX`/`GAIN` no topo do script e rode de novo (o cache `dets.json` no `--trabalho` evita refazer a detecção; o recorte é refeito).
4. **Verificação visual obrigatória**: extraia 6 quadros espalhados (inclua momentos em que ele anda) e olhe:
   ```
   ffmpeg -i "<saída>" -vf "select='eq(n\,90)+eq(n\,600)+…',scale=270:480,tile=6x1" -frames:v 1 check.png
   ```
   Pregador enquadrado com rosto livre? Legenda legível e abaixo do rosto? Se não, ajuste e refaça.
5. `ffprobe`: vídeo H.264 1080x1920, áudio AAC, duração. Opcional: loudness com `-af ebur128`.
6. Relate: duração final, resolução de origem (e o fator de ampliação; 720p → 2,67×, fica mais suave), estatísticas do rastreamento, caminho do arquivo.

## O que o script faz

- Recorta o trecho reencodando (sem `-c copy`) e trabalha sobre ele.
- Detecção por quadro: Haar (rosto frontal + perfil, OpenCV) com HOG (corpo) como reserva. Corte de cena por histograma HSV.
- Mesma pessoa: inicia no maior rosto na parte de cima do quadro e segue por continuidade (ignora cabeças da plateia na parte inferior); sem detecção mantém a última posição.
- Suavização: mediana → Savitzky-Golay (91 quadros) → zona morta ±45 px + velocidade/aceleração limitadas → Savitzky-Golay leve. Em corte de cena reposiciona de uma vez.
- Janela 9:16 com altura total, presa aos limites do quadro, recorte subpixel (warpAffine Lanczos) escalado para 1080x1920. Sem fundo desfocado.
- Legenda: Arial Bold 76 px, branca, contorno preto, até 2 linhas (quebra equilibrada), topo em y=1370 (terço inferior). Renderizada com Pillow e composta no quadro: o ffmpeg do Homebrew aqui não tem libass/drawtext.
- Codificação: H.264 CRF 18 preset medium, AAC 192k, loudnorm -14 LUFS, `+faststart`. **Sem fades.**

## Regras

- Não apague nem altere o vídeo original.
- Não instale pacotes sem perguntar (opencv, scipy, numpy e Pillow já estão no Python do pyenv).
- Arquivos intermediários no scratchpad, nunca na pasta de saída.
