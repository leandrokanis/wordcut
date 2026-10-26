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

- **Duração final** (depois da limpeza) 40–75 s, ideal 55–65 s. A limpeza tira ~15–20% do tempo bruto.
- **Gancho**: os primeiros 3 s prendem — pergunta, afirmação forte, contraste. Nada de "como eu disse antes", "então", "e aí".
- **Autônomo**: entendível sem o que veio antes.
- **Colagem**: uma ideia que se desenvolve por vários minutos pode virar um corte juntando trechos dela. Corte sempre entre frases completas quando possível; dentro da frase, só para tirar uma oração intercalada sem mudar o sentido.
- **Fechamento**: termina numa conclusão natural, não no meio do raciocínio.
- **Limpo**: pouca leitura bíblica longa, sem avisos, sem música, sem interação com a plateia ("vira pro irmão do lado").

## Colagem e reordenação — salvaguardas

Reordenar é permitido (ex.: gancho tirado da conclusão), mas é onde mora o risco de distorção:

- Todo trecho fora de ordem leva uma `note` justificando por que o sentido se mantém. O `preview` marca com `↑` e avisa se faltar.
- Nunca emende de forma que mude uma afirmação: nada de juntar sujeito de uma frase com predicado de outra, nem de tirar "não", "mas", "se" ou uma condição.
- Releia o **texto montado** (saída do `preview`) com os filtros da camada 1, especialmente "fora de contexto". O texto montado é o que o público vai ouvir.

## Processo

1. Leia a pregação inteira: `wordcut overview "<pasta>/palavras.json"`. O contexto é o que pega o "fora de contexto".
2. Consulte `exemplos.md` para calibrar com decisões anteriores.
3. Identifique 3–5 **ideias** fortes. Para cada uma, monte um roteiro (trechos que juntos contam a ideia em 55–65 s).
4. Tempos dos trechos: `wordcut overview … --words --start … --end …`. Cada trecho vai do **início** da primeira palavra ao **fim** da última (a ferramenta acrescenta as margens). Uma palavra só entra se estiver inteira dentro do trecho.
5. Grave cada roteiro em `<pasta>/roteiros/<slug>.json`:
   ```json
   {"version": 1, "title": "Frase marcante curta",
    "segments": [{"start": 2440.6, "end": 2444.5, "note": "gancho da conclusão; mesma tese"},
                 {"start": 2414.05, "end": 2439.7, "note": ""}],
    "corrections": {"Esther": "Ester", "Esté": "Ester", "a direita": "à direita"}}
   ```
6. Rode `wordcut preview <roteiro> --dir <pasta>` para cada um e ajuste até não haver avisos. Confira nomes próprios no texto montado e corrija a grafia em `corrections` (nomes bíblicos pela NVI: Ester, Mardoqueu, Hamã…), mesmo número de palavras de cada lado.
7. Apresente uma tabela e, para cada ideia, a saída do `preview` (trechos, cortes `[–hesitação–]`, texto montado):

| # | Ideia | Duração | Gancho | Valor | Trechos | Alertas |
|---|---|---|---|---|---|---|

   - **Valor**: critério da camada 2. **Alertas**: algo limítrofe, transcrição duvidosa num trecho-chave, reordenação.
   - Depois, 1–2 **trechos descartados** que pareciam atraentes, com o motivo.
8. A avaliação é sugestão; a decisão teológica e a publicação são do usuário, após assistir.
9. Registre escolhas/rejeições em `exemplos.md` (curto: tempo, gancho, decisão, motivo). Sem nomes de pessoas.
