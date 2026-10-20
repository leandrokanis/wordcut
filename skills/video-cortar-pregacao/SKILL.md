---
name: video-cortar-pregacao
description: Extrai a pregação de uma live de culto no YouTube — baixa, transcreve com tempo por palavra (WhisperX), localiza início e fim da pregação, corta com precisão de quadro e fades, e gera a pasta da pregação com palavras.json para os cortes verticais. Use quando o usuário passar o link de uma live/culto e pedir para recortar, cortar ou extrair a pregação/sermão, com ou sem minutagem.
---

# Extrair a pregação de uma live

Primeira etapa do fluxo. A segunda é a skill `video-corte-vertical`, que usa a pasta gerada aqui.

Roda no **leitao** (GPU), no repositório `~/cortes-pregacao`. Todos os comandos abaixo são `uv run cortes …` a partir dele. Se a sessão não estiver no leitao, avise o usuário e pare.

## Entradas

- **Link da live** (obrigatório).
- **Minutagem aproximada** da pregação (opcional). Acelera muito: só a faixa é transcrita.
- **Título e referência bíblica** (opcionais). Sem eles, proponha a partir da pregação.

## Fluxo

1. **Info**: `cortes info <link>`. Se `terminada` for `false`, avise que a live ainda está no ar ou sendo processada pelo YouTube e pare. Use `data_culto` (fuso de Brasília), nunca a data de upload.

2. **Transcrever** em background, na pasta provisória `pasta_sugerida`:
   ```
   cortes transcribe-live <link> --dir "<pasta>" [--start HH:MM:SS --end HH:MM:SS]
   ```
   Leva ~0,3× a duração transcrita (live de 2 h ≈ 40 min; faixa de 45 min ≈ 15 min). Avise o usuário da estimativa.

3. **Localizar a pregação** lendo `cortes overview "<pasta>/trabalho/live-palavras.json"` (use `--start/--end` para focar).
   - Início: primeira palavra do pregador (saudação, "graça e paz"), depois da oração de apresentação feita por outra pessoa.
   - Fim: última frase da pregação (normalmente "amém" após a conclusão). Fica de fora: apelo ou oração conduzidos por outra pessoa, Ceia, avisos, louvor.
   - Leitura bíblica feita pelo pregador faz parte.
   - Tempos exatos: `cortes overview … --words --start … --end …`. Use o **início** da primeira palavra e o **fim** da última.
   - Trechos durante música podem ter texto alucinado; ignore-os.

4. **Confirmar com o usuário** antes de cortar: início e fim (tempo + frase), duração, leitura bíblica, título proposto (frase-tema da pregação) e nome da pasta `AAAA-MM-DD - Título - Referência` (`:` vira `.`). Não corte sem o "ok".

5. **Renomear a pasta** provisória para o nome confirmado (`mv`).

6. **Cortar** em background:
   ```
   cortes cut <link> --dir "<pasta>" --first-word <início> --last-word <fim>
   ```
   Baixa o trecho (1080p, 30 s de folga), sincroniza pelo áudio, codifica com fades de 0,5 s (~17 min para 40 min de pregação) e grava `palavras.json` com tempos relativos ao vídeo.

7. **Verificar**: `ffprobe` com vídeo H.264 + áudio AAC e duração igual à informada. Desvio do download acima de 1 s merece menção.

8. **Relatar**: tempos na live, duração, caminho, e o comando para o usuário trazer o vídeo:
   ```
   scp "leitao:Videos/Pregações/<pasta>/*.mp4" ~/Movies/Pregações/
   ```
   Lembre que ele deve assistir início e fim antes de publicar. Sugira seguir para os cortes verticais.

## Regras

- **Cookies do YouTube** ficam em `~/.config/cortes-pregacao/youtube-cookies.txt`. Nunca exiba, copie ou registre o conteúdo. Se o yt-dlp pedir verificação anti-robô, peça ao usuário para exportar de novo.
- Nunca sobrescreva arquivos. Não apague nada (nem `trabalho/`) sem perguntar.
- O resultado é sugestão: a decisão de publicar é do usuário, após assistir.
- Não registre nomes de pessoas em arquivos de calibração ou relatórios (LGPD).
