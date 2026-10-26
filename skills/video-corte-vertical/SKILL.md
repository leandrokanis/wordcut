---
name: video-corte-vertical
description: Gera cortes verticais 9:16 (1080x1920) de pregação para Reels/Shorts com edição dinâmica palavra a palavra — colagem de trechos de uma ideia, remoção de hesitações e pausas, janela acompanhando o pregador e legenda amarela sincronizada por palavra. Sugere as melhores ideias a partir da transcrição (cristológicas, aplicação prática, frases marcantes; filtra triunfalismo, alegoria e teologia frágil). Use quando o usuário pedir corte vertical, Reels, Shorts, TikTok, "sugerir cortes" ou "melhores trechos" de uma pregação.
---

# Cortes verticais com edição dinâmica

Segunda etapa do fluxo. A primeira é `video-cortar-pregacao`, que gera a pasta da pregação:

```
~/Videos/Pregações/AAAA-MM-DD - Título - Referência/
  <pasta>.mp4      pregação horizontal
  palavras.json    transcrição por palavra (tempos do .mp4)
  roteiros/        um .json por corte
  cortes/          resultado
```

Roda no **leitao**, no repositório `~/cortes-pregacao` (`uv run wordcut …`). Se a pasta não existir ou não tiver `palavras.json`, rode a primeira etapa antes.

## Fluxo

1. **Sugerir ideias e montar roteiros** seguindo `sugerir-cortes.md` (critérios, salvaguardas da colagem e formato do roteiro), calibrado por `exemplos.md`. Cada ideia vira um roteiro em `roteiros/` e passa pelo `wordcut preview` sem avisos.

2. **Aprovação obrigatória do roteiro em texto.** Mostre a saída do `preview` de cada ideia. O usuário pode aprovar várias de uma vez, pedir ajustes (tirar/incluir frase, trocar gancho) ou rejeitar. Ajuste o `.json`, rode `preview` de novo e mostre. Nada é renderizado sem aprovação.

3. **Renderizar** cada roteiro aprovado, em background (≈ 2–4 min por corte):
   ```
   wordcut short "<pasta>/roteiros/<slug>.json" --dir "<pasta>"
   ```
   Com mais de uma pessoa em pé (entrevista, testemunho), olhe um quadro e passe `--alvo 0.7` (posição horizontal de quem fala, 0 = esquerda).

4. **Verificação visual obrigatória** de cada corte: 6 quadros espalhados, incluindo emendas entre trechos:
   ```
   ffmpeg -i "<corte>" -vf "select='eq(n\,90)+eq(n\,600)+…',scale=270:480,tile=6x1" -frames:v 1 check.png
   ```
   Pregador enquadrado com o rosto livre? Legenda legível, sem cobrir o rosto? Se não, ajuste e refaça.

5. **Relatar**: duração, número de emendas, hesitações removidas, caminho, e o comando para trazer o arquivo:
   ```
   scp "leitao:Videos/Pregações/<pasta>/cortes/*.mp4" ~/Movies/Pregações/
   ```
   Lembre o usuário de assistir antes de publicar. Registre a decisão em `exemplos.md`.

## O que a ferramenta faz

- **Limpeza** (conservadora): remove "hã", "hum", "né", "é…"/"então…" arrastados, gaguejo de palavra curta ("o, o Senhor") e de expressão recomeçada ("não teve, não teve sonho"). Repetição retórica ("santo, santo, santo") fica. Se a hesitação removida tinha o ponto final, ele passa para a palavra anterior.
- **Correções de grafia** da legenda vêm do campo `corrections` do roteiro; cada trecho começa com maiúscula.
- **Pausas**: depois de fim de frase ficam até 0,4 s (respiro antes da próxima ideia); demais pausas, 0,15 s.
- **Emendas**: corte seco, no quadro mais silencioso perto da fronteira; fade-out/in de 15 ms no áudio contra estalos. Áudio e vídeo nunca dessincronizam.
- **Enquadramento**: detecção de rosto (Haar) com corpo (HOG) como reserva; segue a mesma pessoa por continuidade, ignora cabeças da plateia; suavização tipo operador de câmera. Em troca de trecho do roteiro a janela reposiciona de uma vez.
- **Legenda**: Open Sans Bold 60 px (fonte incluída no pacote), amarelo saturado (#FFD600), contorno preto e sombra, centralizada na metade do vídeo; blocos de até 2 linhas, cada um entra na primeira palavra e sai na próxima.
- **Codificação**: H.264 CRF 18, AAC 192k, loudnorm −14 LUFS, `+faststart`. Nunca sobrescreve: usa `-v2`, `-v3`…

## Regras

- Não apague nem altere a pregação, `palavras.json` ou roteiros aprovados sem perguntar.
- Intermediários ficam em `<pasta>/trabalho/`.
- Avaliação teológica é sugestão; publicar é decisão do usuário, após assistir.
- Sem nomes de pessoas em `exemplos.md` (LGPD).
