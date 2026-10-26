# ADR-0009: Identidade pelo Cloudflare Access

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

O princípio VI proíbe autenticação própria; o acesso externo é só pelo Cloudflare Tunnel
com o Cloudflare Access.

## Decisão

A API confia no e-mail verificado que o Cloudflare Access envia e valida o JWT do
Access (`Cf-Access-Jwt-Assertion`) contra as chaves públicas da equipe. O papel vem da
tabela de membros. A CLI na máquina do servidor age como administrador.

## Consequências

- A API não guarda senha nem sessão.
- Em desenvolvimento local, uma variável de ambiente define o e-mail fixo, nunca ligada em
  produção.
