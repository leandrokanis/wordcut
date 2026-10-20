---
name: video-cortar-pregacao
description: Recorta a pregação (ou qualquer trecho) de um vídeo de culto com ffmpeg, com corte preciso no quadro, reencode H.264/AAC e fades de 0,5 s. Use quando o usuário pedir para recortar, cortar ou extrair a pregação/sermão de um vídeo de culto, local ou do YouTube, informando tempos de início e fim.
---

# Recortar pregação de vídeo de culto

## Entradas

- **Fonte**: caminho de arquivo local ou link do YouTube.
- **Trecho**: início e fim (HH:MM:SS). Opcionalmente, frases de referência para início/fim.
- **Nome de saída**: padrão `AAAA-MM-DD - <Título> - <Referência bíblica>.mp4` (ex.: `2026-10-04 - O azeite da viúva - 2 Reis 4.1-7.mp4`). Em nomes de arquivo, troque `:` da referência por `.`.
- **Pasta de saída**: se não informada, use `~/Movies/Pregações` e avise o usuário.

Se faltar fonte ou trecho, pergunte. Não invente tempos.

## Fluxo

1. **Fonte local**: rode `ffprobe` para confirmar que abre, ver resolução, duração e `start_time`. Se der `Operation not permitted` em `~/Downloads`, é TCC do macOS: o terminal precisa de Acesso Total ao Disco (Ajustes → Privacidade e Segurança).
2. **Fonte YouTube**: baixe só o trecho com 30 s de folga:
   ```
   yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" --download-sections "*INI-30s-FIM+30s" --merge-output-format mp4 -o "<pasta>/_trabalho/fonte_trecho.%(ext)s" "<URL>"
   ```
   Os tempos passam a ser relativos ao trecho baixado (início ≈ 30 s).
3. **(Opcional) Confirmar cortes pelo áudio**: só se o usuário der frases de referência. Extraia ~60 s em torno de cada marca, transcreva com faster-whisper (`small`, `language="pt"`, `word_timestamps=True`) num venv no scratchpad, peça permissão antes de instalar pacotes. Início ≈ 1 s antes da frase inicial, fim ≈ 1,5 s depois da última palavra. Se não achar a frase, use o tempo dado e avise.
4. **Cortar**: use o script `cortar.sh` desta skill (rode em background, a codificação demora):
   ```
   ~/.claude/skills/video-cortar-pregacao/cortar.sh "<fonte>" <INI> <FIM> "<saída.mp4>"
   ```
5. **Verificar** com `ffprobe`: faixas de vídeo e áudio presentes, duração = FIM − INI.
6. **Relatar**: tempos usados, duração final, resolução, tamanho, caminho.

## Regras

- Nunca use `-c copy`: o corte tem de ser preciso no quadro.
- `-ss`/`-to` ficam **depois** do `-i` (precisão). Consequência importante: o ffmpeg aplica `-vf`/`-af` **antes** do corte de saída, então os tempos dos fades são **absolutos na fonte** (`st=INI` e `st=FIM-0.5`), não `st=0`. O script já faz isso; somar o `start_time` da fonte se ele não for 0.
- Codificação: `libx264 -crf 18 -preset medium`, `aac -b:a 192k`, `-movflags +faststart`. Fades de 0,5 s de vídeo e áudio na entrada e na saída.
- Use `-n` (nunca sobrescrever). Se o arquivo de saída existir, pergunte.
- Não apague nem altere o vídeo original nem arquivos baixados sem perguntar.
