# Sugerir cortes a partir da transcrição

Objetivo: valorizar as boas partes da pregação. Toda pregação tem trechos fortes e fracos; o corte publica só os fortes. Na dúvida, descarte — um corte a menos custa pouco, um corte ruim publicado custa caro.

Referência teológica: tradição restauracionista Stone-Campbell (Igrejas de Cristo / Igrejas Cristãs). Bíblia como única regra de fé e prática, Cristo no centro, unidade dos cristãos, resposta ao evangelho com fé, arrependimento e batismo, Ceia semanal.

Os critérios são aplicados em três camadas, nesta ordem.

## 1. Filtro — exclui o trecho (basta um)

- **Triunfalismo**: vitória, prosperidade, cura ou "sua hora chegou" prometidos sem cruz; fé como garantia de sucesso; Deus a serviço dos planos do ouvinte.
- **Teologia frágil**: decretar/declarar/profetizar sobre a própria vida, "Deus te deve", fé como força positiva, linguagem de coaching motivacional sem evangelho, homem no centro.
- **Alegoria**: texto bíblico usado como metáfora livre, desconectado do sentido no contexto original ("as 5 pedras de Davi são 5 chaves para sua vida").
- **Moralismo sem graça**: "faça mais, esforce-se, seja melhor" sem Cristo como motivo e poder.
- **Fora de contexto**: frase que, isolada, muda ou inverte o argumento (pregador cita uma ideia para refutá-la; ironia; pergunta retórica sem a resposta). Ler sempre 1 minuto antes e depois do trecho.
- **Sectarismo e polêmica**: ataque a outras igrejas ou cristãos, "só nós somos a igreja", controvérsia intra-cristã que, recortada, gera briga em vez de edificação.
- **Exposição de pessoas**: nome de membro, pedido de oração, testemunho envolvendo saúde, família ou situação de terceiros (LGPD).
- **Erro factual evidente**: citação bíblica errada, dado histórico equivocado, versículo atribuído ao livro errado.

## 2. Valor — o que buscamos (precisa de ao menos um)

- **Cristológico**: Cristo como centro — quem ele é, sua obra (cruz, ressurreição), a graça explicada, não só citada.
- **Aplicação prática**: o que muda na vida concreta (segunda-feira, casa, trabalho), nascida do texto e motivada pelo evangelho.
- **Frase marcante**: síntese curta, memorável, que se sustenta sozinha.

Bônus (somam, não bastam sozinhos):
- Exposição fiel do texto bíblico — mostra o que o texto diz no contexto.
- Chamado ao evangelho: fé, arrependimento, batismo como resposta a Cristo.
- Ceia, comunhão, unidade do corpo de Cristo.
- Consolo pastoral honesto: sofrimento tratado sem promessa fácil.
- Ilustração que esclarece em vez de enfeitar.

## 3. Formato — funciona como corte?

- **Duração** 30–90 s (ideal 45–75 s).
- **Gancho**: os primeiros 3 s prendem — pergunta, afirmação forte, contraste. Nada de "como eu disse antes", "então", "e aí".
- **Autônomo**: entendível sem o que veio antes.
- **Fechamento**: termina numa conclusão natural, não no meio do raciocínio.
- **Limpo**: pouca leitura bíblica longa, sem avisos, sem música, sem interação com a plateia ("vira pro irmão do lado").

## Processo

1. Gere a transcrição com tempos: `python3 -I ~/.claude/skills/video-corte-vertical/transcricao.py "<legenda.vtt>" "<scratchpad>/transcricao.txt"`. Se só houver o vídeo do YouTube, baixe a legenda com `yt-dlp --skip-download --write-auto-subs --sub-langs "pt-orig,pt" --sub-format vtt` (se pedir verificação de bot, `--cookies-from-browser chrome`).
2. Localize início e fim da pregação (ignore louvor, avisos, ofertório, Ceia conduzida por outra pessoa).
3. Leia a pregação inteira antes de escolher — o contexto é o que pega o "fora de contexto".
4. Consulte `exemplos.md` para calibrar com decisões anteriores.
5. Selecione 3–5 candidatos. Tempos: início na primeira palavra do gancho menos ~0,3 s; fim na última palavra do fechamento mais ~0,5 s (tempos por palavra estão na transcrição).
6. Apresente:

| # | Início–fim | Duração | Gancho (primeiras palavras) | Resumo | Valor | Alertas |
|---|---|---|---|---|---|---|

   - **Valor**: qual critério da camada 2 atende.
   - **Alertas**: algo limítrofe (ex.: aplicação boa logo depois de uma alegoria; transcrição automática duvidosa num trecho-chave).
   - Depois da tabela, liste 1–2 **trechos descartados** que pareciam atraentes, com o motivo — mostra o critério em ação.
7. Lembre: a avaliação é sugestão; a decisão teológica e a publicação são do usuário, após assistir ao trecho.
8. Quando o usuário escolher/rejeitar, registre em `exemplos.md` (curto: tempo, gancho resumido, decisão, motivo). Não registre nomes de pessoas.
9. Siga para o fluxo do corte vertical com o trecho escolhido.
