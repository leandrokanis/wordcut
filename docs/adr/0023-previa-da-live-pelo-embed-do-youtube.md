# ADR-0023: Prévia da live pelo embed do YouTube

**Status**: Aceita · **Data**: 2026-10-26

Substitui a [ADR-0022](0022-arquitetura-do-cliente-web.md) só no ponto "Nenhum recurso vem de
outro host"; o resto da ADR-0022 continua valendo. Esta ADR diz de onde vem a prévia 16:9 do
nível 2 da web (item 22 do roadmap).

## Contexto

No nível 2, o assistente delimita a pregação puxando as bordas do clipe sobre a live inteira
e vê na prévia o quadro de cada borda (features 1.1.b e 1.1.c). Antes do processamento, a
máquina não tem a live: o processamento baixa só a faixa delimitada
([ADR-0014](0014-processamento-por-portas-e-estado-na-leitura.md)). Depois dele, a API serve
o vídeo 16:9 processado em `GET /api/sermons/{id}/video`, que começa em `sermon_start` e
termina em `sermon_end`, e uma borda puxada para fora desse trecho não tem quadro nele.

Baixar a live inteira só para a prévia ocupa a máquina e a trava por minutos a cada
pregação, contra o motivo de baixar só a faixa. A ADR-0022 diz que a web não pede nada a
terceiros, e a única fonte da live sem baixá-la é o próprio YouTube.

## Decisão

- **A prévia é uma porta, `PlayerLike`** (`features/sermon/Player.tsx`): posição, `seek`,
  `play`, `pause` e aviso de mudança de posição, sempre em segundos da live. A tela recebe as
  implementações por contexto (`PlayerFactoryContext`), e os testes trocam as duas por dublês;
  nenhum teste carrega script, iframe ou mídia do YouTube.
- **Antes do processamento, e fora do trecho processado, a prévia é o embed do YouTube**
  (`youtubePlayer.ts`): o script da IFrame API vem de `https://www.youtube.com/iframe_api` e o
  player usa o host `https://www.youtube-nocookie.com`, o modo de privacidade aprimorada do
  YouTube. O script é carregado uma vez, só quando uma tela do nível 2 precisa da live; a
  lista, o nível 3 e as configurações não o carregam.
- **Dentro do trecho processado, a prévia é o `<video>` da API** (`videoPlayer.ts`), que
  converte o tempo da live em tempo do vídeo (`t − sermon_start`) e de volta.
- Fora disso, a regra da ADR-0022 continua: fonte, script e estilo da aplicação saem do
  próprio contêiner.

## Consequências

- O assistente delimita sem esperar download nenhum, e a máquina fica livre para outras
  tarefas.
- O navegador de quem delimita fala com o YouTube: a página precisa de acesso a
  `youtube.com` e `youtube-nocookie.com`, e uma live privada ou removida deixa a prévia
  vazia, sem mudar a timeline nem o salvamento das bordas.
- O YouTube não dá evento de tempo pela IFrame API; o adaptador lê a posição a cada 250 ms.
- Uma política de segurança de conteúdo (CSP) no nginx, se vier, precisa liberar esses dois
  hosts para script e frame.
- Trocar a fonte da prévia (por exemplo, para uma cópia baixada) muda só as implementações da
  porta, não a tela.
