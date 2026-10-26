## Plano de QA

baseline_commit afbe8e16606c94b897a70e46e4a7045f6e715687

14:14  📐 BARRA   passo 1 — todo código de EXIT_CODES tem status e corpo
       TestClient parametrizado sobre EXIT_CODES inteiro: um código novo
       sem status quebra o teste, em vez de cair num padrão silencioso

14:14  🧬 EXIGE   unauthenticated→403; saída 5→400; corpo sem details  ·  vermelha
       prova que o status e o objeto de erro da CLI são checados de fato

14:15  📐 BARRA   passo 2 — verify recusa toda forma de token ruim
       test_identity.py com par RSA do teste e KeySource dublê: assinatura,
       exp, aud, kid, malformado, alg none/HS256, sem claim email

14:15  🧬 EXIGE   algorithms aceita HS256/none; sem audience; sem exp  ·  vermelha
       se sobreviver, a API aceita token forjado ou vencido

14:15  🧬 EXIGE   cache sem validade; sem nova busca em kid novo  ·  vermelha
       prova os 10 min e a rotação, com relógio injetado e contador de busca

14:16  🧬 EXIGE   AccessKeys sem refuse_when_forbidden  ·  vermelha
       sem a guarda, um teste que monte AccessKeys real chega à Cloudflare

14:16  📐 BARRA   passo 3 — identidade e papel pela HTTP
       test_auth.py com create_app(settings, keys); membros por add_member
       sobre wordcut_home; rota de admin montada no próprio teste

14:16  🧬 EXIGE   require ignora papel; dev ligado com Access  ·  vermelha
       se sobreviver, assistente vira admin ou o modo dev vaza p/ produção

14:17  🧬 EXIGE   current_member confia no cabeçalho de e-mail  ·  vermelha
       o e-mail só pode vir do JWT verificado (ADR-0009)

14:17  📐 BARRA   passo 4 — compose e docs, sem teste automatizado
       docker compose config, uv lock --check e leitura do diff; DEV_EMAIL
       não pode estar ligado por padrão no compose

14:17  ⚠️ LACUNA  L1 — origem da conexão para role_of não decidida
       barra: db.connect por requisição, fechada; health sem banco; senão
       passo 3 PARCIAL

14:18  ⚠️ LACUNA  L2 — não há rota de admin real nesta issue
       barra: rota de teste com require("admin"); tabela 1.2.a por linha
       fica com 20a/20b

14:18  ⚠️ LACUNA  L3 — TEAM_DOMAIN sem AUD (ou inverso) não decidido
       barra: nunca modo dev; falha ao subir ou 401; aceitar sem aud = FAIL

14:18  ⚠️ LACUNA  L4 — status da falha ao buscar chaves não decidido
       barra: network_error → 502; nunca 200; token fora do corpo

14:19  ⚠️ LACUNA  L5 — interrupted e processing_error sem status
       barra: 500; teste do passo 1 percorre EXIT_CODES inteiro

14:19  ⚠️ LACUNA  L6 — exceção que não é WordcutError não coberta
       recomendado 500 internal_error sem rastro; não bloqueia o PASS

14:19  ⚠️ LACUNA  L7 — iss (emissor) não é verificado pelo FR-001
       recomendado checar https://<team>; não bloqueia o PASS

14:19  ⚠️ LACUNA  L8 — DEV_EMAIL passa ou não por role_of
       barra: passa; dev fora da equipe → 403; não é atalho de admin

## Rodada 1 · implementador

14:16  --- Passo 1: Erros HTTP ---

14:17  🔴 RED    test_every_documented_error_code_maps_to_its_exit_code
       unauthenticated e forbidden existem em EXIT_CODES com saída 1
       passo 1 (a); plano, Contexto de código (core/errors.py)
       E ValueError: unknown error code: unauthenticated

14:17  🟢 GREEN  test_every_documented_error_code_maps_to_its_exit_code  ·  23 passed

14:17  🔴 RED    test_every_error_code_answers_with_its_status_and_the_error_obj…
       WordcutError numa rota vira o status da tabela e {"error": to_dict()},
       parametrizado sobre todo EXIT_CODES
       passo 1 (b)(c); FR-005; decisão Status HTTP; L5
       E json.decoder.JSONDecodeError: Expecting value (500 em texto puro)

14:17  🟢 GREEN  test_every_error_code_answers_with_its_status_and_the_error_obj…  ·  22 passed

14:17  🟢 GREEN  test_an_error_without_details_answers_without_details  ·  passa de
       primeira: o handler usa WordcutError.to_dict, que já omite details;
       fica como prova do passo 1 (b), lado "sem details"

14:17  🔴 RED    test_an_unexpected_failure_answers_internal_error_without_its_text
       exceção que não é WordcutError vira 500 internal_error, sem o texto
       dela (rastro, token, e-mail) no corpo
       L6 (decisão do orquestrador)
       E json.decoder.JSONDecodeError: Expecting value (500 em texto puro)

14:19  🧬 MUTAR  errors.py: STATUS_BY_CODE["unauthenticated"]; STATUS_BY_EXIT_CODE[5];
       {"error": error.to_dict()} no corpo
       test_every_error_code_answers_with_its_status_and_the_error_obj…

14:19  ✅ PASSO 1/4 — Erros HTTP  ·  +26 testes  ·  suíte 1297

14:19  --- Passo 2: Verificação do token ---

14:20  🔴 RED    test_a_valid_access_token_gives_the_verified_email
       JWT RS256 válido, assinado pela chave do kid, com o aud configurado
       e não expirado, devolve o e-mail verificado
       passo 2 (a); FR-001
       E ModuleNotFoundError: No module named 'wordcut_api.identity'

14:21  🟢 GREEN  test_a_valid_access_token_gives_the_verified_email  ·  1 passed

14:21  🔴 RED    test_a_token_access_did_not_sign_for_this_team_is_unauthenticat…
       assinatura de outra chave, exp vencido, aud ou iss errados, kid
       desconhecido, sem e-mail, malformado, alg none e HS256 com a chave
       pública como segredo: unauthenticated, sem o token no erro nem no log
       passo 2 (b)(e); FR-001; L7 (iss)
       E jwt.exceptions.InvalidSignatureError; DID NOT RAISE (iss); KeyError

14:22  🟢 GREEN  test_a_token_access_did_not_sign_for_this_team_is_unauthenticat…  ·  10 passed

14:22  🧬 MUTAR  identity.py: algorithms=[ALGORITHM]; audience=; verify_exp; issuer=
       test_a_token_access_did_not_sign_for_this_team_is_unauthenticat…
       conferido: +HS256, sem audience e verify_exp False ficam vermelhos.
       +"none" é mutante equivalente: o PyJWT recusa chave não nula com
       alg none (InvalidKeyError), e verify nunca decodifica sem chave

14:22  🔴 RED    test_the_keys_are_fetched_once_for_ten_minutes
       duas verificações dentro de 10 min buscam as chaves uma vez só, na
       URL https://<team>/cdn-cgi/access/certs (relógio injetado)
       passo 2 (c); decisão Chaves
       E ImportError: cannot import name 'AccessKeys'

14:22  🟢 GREEN  test_the_keys_are_fetched_once_for_ten_minutes  ·  11 passed

14:22  🟢 GREEN  test_the_keys_are_fetched_again_after_ten_minutes  ·  passa de
       primeira: a validade de 10 min entrou com o teste anterior; fica como
       prova do lado "depois da janela" (mata o cache que nunca expira)

14:22  🔴 RED    test_a_new_key_id_fetches_the_keys_again_to_follow_a_rotation
       kid desconhecido dentro da janela busca as chaves de novo (rotação)
       passo 2 (c); decisão Chaves
       E wordcut.errors.WordcutError: Acesso não identificado

14:23  🟢 GREEN  test_a_new_key_id_fetches_the_keys_again_to_follow_a_rotation  ·  13 passed

14:23  🟢 GREEN  test_a_key_id_unknown_after_fetching_again_is_unauthenticated  ·
       passa de primeira: prova do passo 2 (b) "kid desconhecido mesmo após
       nova busca", com uma só nova busca (sem laço)

14:23  🔴 RED    test_certs_without_usable_keys_are_a_network_error
       resposta de chaves sem chave utilizável é falha externa, não 401
       L4 (falha ao buscar as chaves → network_error)
       E AssertionError: assert 'unauthenticated' == 'network_error'

14:23  🟢 GREEN  test_certs_without_usable_keys_are_a_network_error  ·  15 passed

14:23  🔴 RED    test_the_real_keys_refuse_before_reaching_access_while_the_netw…
       AccessKeys real, sob a suíte, recusa com network_error e
       details.forbidden_by antes de qualquer rede
       passo 2 (d); ADR-0017
       E TypeError: AccessKeys.__init__() missing … argument: 'fetch'

14:23  🟢 GREEN  test_the_real_keys_refuse_before_reaching_access_while_the_netw…  ·  16 passed

14:23  🧬 MUTAR  identity.py: CACHE_SECONDS no _expired; "kid not in self._keys";
       refuse_when_forbidden em fetch_json; PyJWKSetError → network_error
       test_the_keys_are_fetched_*; test_a_new_key_id_*; test_the_real_keys_*;
       test_certs_without_usable_keys_*

14:23  ✅ PASSO 2/4 — Verificação do token  ·  +16 testes  ·  suíte 1313

14:23  --- Passo 3: Membro e papel ---

14:24  🔴 RED    test_a_member_with_a_valid_token_sees_the_email_and_role
       assistente e admin com token válido: GET /api/me 200 {email, role}
       passo 3 (a); cenário "membro identificado"; FR-002; FR-004
       E ModuleNotFoundError: No module named 'wordcut_api.settings'

14:24  🟢 GREEN  test_a_member_with_a_valid_token_sees_the_email_and_role  ·  43 passed

14:25  🟢 GREEN  test_the_role_comes_from_the_team_not_from_the_token  ·  passa de
       primeira: current_member já pergunta a role_of a cada requisição;
       fica como prova do FR-002 (set_role muda /api/me sem mexer no token)

14:25  🔴 RED    test_a_request_without_the_access_token_is_unauthenticated
       sem Cf-Access-Jwt-Assertion → 401 unauthenticated
       passo 3 (b); cenário "sem token ou token inválido"
       E KeyError: 'Cf-Access-Jwt-Assertion'

14:25  🟢 GREEN  test_a_request_without_the_access_token_is_unauthenticated  ·  45 passed

14:25  🟢 GREEN  test_a_rejected_token_is_unauthenticated_and_never_repeated  ·
       passa de primeira: verify (passo 2) + handler (passo 1); fica como
       prova HTTP do cenário "assinatura errada, expirado, aud errado" e de
       que o token não aparece no corpo nem no log

14:25  🔴 RED    test_an_email_outside_the_team_is_forbidden_without_repeating_it
       token válido de e-mail fora da equipe → 403 forbidden, mensagem clara
       e sem o e-mail no corpo nem no log
       passo 3 (c); cenário "e-mail não liberado"; ADR-0015; LGPD
       E At index 1 diff: … 'message': '' != 'Este e-mail não está na equipe.'

14:26  🟢 GREEN  test_an_email_outside_the_team_is_forbidden_without_repeating_it  ·  49 passed

14:26  🔴 RED    test_an_assistant_is_forbidden_in_a_route_for_administrators
       + test_an_admin_gets_the_answer_of_a_route_for_administrators
       require("admin") numa rota montada no teste: assistente 403
       forbidden; admin recebe a resposta normal da rota
       passo 3 (d); cenário "permissão por papel"; FR-003; L2
       E ImportError: cannot import name 'require' from 'wordcut_api.auth'

14:26  🟢 GREEN  test_an_assistant_is_forbidden_in_a_route_for_administrators  ·  51 passed

14:26  🟢 GREEN  test_the_email_header_without_the_token_is_unauthenticated  ·
       passa de primeira, como o caso sem token na rota de admin: o e-mail
       só sai do JWT verificado (passo 3 (b)(e); ADR-0009)

14:26  🔴 RED    test_the_dev_email_identifies_a_member_without_access_and_warns…
       sem Access e com WORDCUT_DEV_EMAIL de um membro: /api/me 200 sem
       token, com aviso no log ao subir
       passo 3 (f); borda "modo de desenvolvimento"; decisão Modo dev
       E AttributeError: 'State' object has no attribute 'identification'

14:27  🟢 GREEN  test_the_dev_email_identifies_a_member_without_access_and_warns…  ·  54 passed

14:27  🟢 GREEN  test_the_dev_email_is_ignored_when_access_is_configured,
       test_without_access_nor_dev_email_nobody_is_identified,
       test_a_dev_email_outside_the_team_is_forbidden  ·  passam de primeira:
       o Access tem precedência e o e-mail dev passa por role_of desde o
       ciclo anterior; ficam como prova do passo 3 (f) e da L8

14:27  🔴 RED    test_access_configured_by_half_refuses_to_start
       só TEAM_DOMAIN ou só AUD: create_app falha ao subir com mensagem
       clara, mesmo com DEV_EMAIL (nunca cai no modo dev)
       L3 (decisão do orquestrador)
       E Failed: DID NOT RAISE WordcutError

14:27  🟢 GREEN  test_access_configured_by_half_refuses_to_start  ·  59 passed

14:27  🟢 GREEN  test_keys_out_of_reach_are_a_bad_gateway_without_the_token,
       test_health_answers_without_a_token_nor_the_database  ·  passam de
       primeira: o AccessKeys real da guarda dá network_error → 502 (L4), e
       /api/health não depende de identificação nem abre o banco (L1, (g))

14:28  🔴 RED    test_the_settings_are_read_from_the_environment
       + test_access_read_from_the_environment_reaches_for_the_team_keys
       create_app() sem argumento lê WORDCUT_DEV_EMAIL, e lê
       WORDCUT_ACCESS_TEAM_DOMAIN/AUD (com Access, DEV_EMAIL não vale e as
       chaves do time são buscadas, recusadas pela guarda)
       passo 3 (h)
       E assert {'error': {'code': 'unauthenticated' …}} == {'email': …}

14:28  🟢 GREEN  test_the_settings_are_read_from_the_environment  ·  63 passed

14:30  🧬 MUTAR  auth.py: "member.role not in (role, ADMIN)" em require; e-mail só do
       TOKEN_HEADER em AccessIdentification; "forbidden" para fora da equipe;
       ordem Access antes de DEV_EMAIL em identification
       conferido: require sem papel, confiar no cabeçalho de e-mail e
       403→401 ficam vermelhos

14:30  ✅ PASSO 3/4 — Membro e papel  ·  +22 testes  ·  suíte 1335

14:30  --- Passo 4: Compose e documentação ---

14:33  📄 DOCS   compose.yaml repassa WORDCUT_ACCESS_TEAM_DOMAIN/AUD à api (vazios
       por padrão; WORDCUT_DEV_EMAIL nunca); docs/cli.md §5.1 e §5.3 com
       unauthenticated e forbidden; ADR-0019 e índice; arquitetura (estado
       da API e fluxo 5.4); README; CHANGELOG. Sem teste automatizado:
       docker compose config -q e uv lock --check limpos

14:33  ✅ PASSO 4/4 — Compose e documentação  ·  +0 testes  ·  suíte 1335

14:33  🏁 FINAL  suíte 1335 passed; ruff check/format e mypy limpos;
       uv lock --check ok; docker compose config -q ok. docker compose
       build não rodado (baixaria pacotes; fora da barra do passo 4)

## Rodada 1 · QA

14:34  📊 SUÍTE  apps/api 63 passed  ·  0 failed
       core test_errors 23 passed; monorepo 1335 passed, 0 failed (offline)

14:35  📊 SUÍTE  ruff check, ruff format --check, mypy limpos
       uv lock --check ok (offline); docker compose config -q ok

14:36  🔎 QA     passo 1/4 — Erros HTTP  ·  ✅ PASS
       EXIT_CODES inteiro parametrizado; status, corpo e L5/L6 provados

14:37  🧬 MUTAÇÕES · passo 1 (errors.py da API e do core)  ·  5 de 5 mortas
       ☠️  unauthenticated→403                          1 teste
       ☠️  saída 5→400                                  1 teste
       ☠️  corpo sem details                            1 teste
       ☠️  exceção inesperada repete o texto            1 teste
       ☠️  core: unauthenticated com saída 2            1 teste

14:38  🧬 MUTAÇÕES · passo 2 (identity.py)  ·  15 de 19 mortas
       ☠️  +HS256; sem audience; verify_aud False       1 teste cada
       ☠️  verify_exp False; sem issuer; sem assinatura 1 teste cada
       ☠️  cache sem validade; cache sempre vencido     1 teste cada
       ☠️  sem nova busca em kid; sem guarda de rede    1 teste cada
       ☠️  JWKS vazio→401; token no erro; sem email     1 teste cada
       ☠️  sem a guarda key None (só e com +none)       1 teste
       🚨  REQUIRED_CLAIMS sem "exp"      SOBREVIVEU — token sem exp
       (assinado pelo Access) passaria para sempre; fora da lista da barra
       🚨  _key_id sem checar tipo        SOBREVIVEU — equivalente: kid
       não-str vira chave inexistente → 401
       🚨  chave não-RSA mantida          SOBREVIVEU — equivalente: RS256
       com chave EC dá InvalidKeyError → 401
       🚨  algorithms +"none"             SOBREVIVEU — equivalente,
       confirmado: NoneAlgorithm.prepare_key recusa chave não nula
       (PyJWT 2.15.1) e a guarda key None está presa pelo teste de kid
       desconhecido

14:39  🔎 QA     passo 2/4 — Verificação do token  ·  ✅ PASS
       (a)–(e) provados; todas as mutações exigidas pela barra morrem

14:40  🧬 MUTAÇÕES · passo 3 (auth.py, settings.py, app.py)  ·  14 de 17 mortas
       ☠️  require ignora papel; dev antes do Access    1 teste cada
       ☠️  confiar no cabeçalho de e-mail; 403→401      1 teste cada
       ☠️  e-mail no details do 403; e-mail no log      1 teste cada
       ☠️  sem guarda de meia config; meia config→dev   1 teste cada
       ☠️  e-mail dev pula role_of; sem aviso dev       1 teste cada
       ☠️  NoIdentification deixa entrar; DEV_EMAIL     1 teste cada
       ☠️  health exige membro                          1 teste
       🚨  require: admin deixa de passar em tudo  SOBREVIVEU — nenhuma
       rota com require("assistant") no teste; fora da barra (d)
       🚨  AUD lido de TEAM_DOMAIN        SOBREVIVEU — o teste do ambiente
       prova que as variáveis são lidas, não que o valor chega à
       verificação; falha fechada (401), fora das 🧬 do passo
       🚨  TEAM_DOMAIN lido de AUD        SOBREVIVEU — idem

14:41  🔎 QA     passo 3/4 — Membro e papel  ·  ✅ PASS
       (a)–(h) provados por HTTP; mutações exigidas morrem; L1, L3, L8 ok

14:41  🔎 QA     passo 4/4 — Compose e documentação  ·  ✅ PASS
       compose repassa TEAM_DOMAIN/AUD vazios e nunca DEV_EMAIL (mesmo
       com DEV_EMAIL no shell); cli.md, arquitetura, CHANGELOG, uv.lock ok

## Rodada 2 · implementador

14:42  ↩️ REABERTO  passo 2/4 — Verificação do token
       decisão do orquestrador: token sem exp → 401; a mutação "exp
       ausente aceito" tem que ficar vermelha; atalho de admin do require

14:42  --- Passo 2: Verificação do token ---

14:42  🟢 GREEN  test_a_token_access_did_not_sign_…[without an expiry]  ·
       passa de primeira: REQUIRED_CLAIMS já tinha "exp". Token válido em
       tudo, sem exp, dá unauthenticated
       orquestrador, rodada 2 (L9); achado da Rodada 1 do QA
       11 passed (test_identity, tokens ruins)

14:43  🧬 MUTAR  identity.py: REQUIRED_CLAIMS sem "exp"  ·  ☠️ morta
       E Failed: DID NOT RAISE WordcutError
       test_a_token_access_did_not_sign_…[without an expiry]

14:43  🟢 GREEN  test_a_rejected_token_is_unauthenticated_…[without an expiry]
       mesmo caso por HTTP: /api/me com token sem exp → 401
       passa de primeira, pelo mesmo motivo; 4 passed

14:43  🧬 MUTAR  identity.py: REQUIRED_CLAIMS sem "exp"  ·  ☠️ morta
       primeiro deu 403 (o e-mail assinado não era membro), o que esconde
       o efeito do mutante; o teste agora cadastra o e-mail assinado como
       admin, e o mutante dá 200
       E KeyError: 'error'

14:43  🟢 GREEN  test_an_admin_gets_the_answer_of_a_route_for_assistants  ·
       24 passed. Rota montada no teste com require("assistant"); o admin
       recebe a resposta normal
       ADR-0019 ("o administrador passa em todas"); L10. Passa de
       primeira: o atalho já existia; o mutante muda comportamento
       público, então não é equivalente

14:43  🧬 MUTAR  auth.py: require com member.role != role  ·  ☠️ morta
       E assert (403, …) == (200, {'done_by': 'admin@exemplo.org'})

14:44  ⚖️ EQUIVALENTE  "email" fora do require do PyJWT
       _email recusa claim ausente, não texto ou vazio; pôr "email" no
       require só duplicaria a checagem (L9, "ou equivalente")

14:44  ✅ PASSO 2/4 — Verificação do token  ·  +3 testes  ·  suíte 1338
       ruff check, ruff format --check e mypy limpos; ADR-0019 diz "exp
       presente e no futuro"

## Rodada 2 · QA

14:45  📊 SUÍTE  API 66 passed · 0 failed  ·  monorepo 1338 · 0
       core test_errors 23; ruff, format, mypy, uv lock --check e
       docker compose config limpos; tudo com UV_OFFLINE=1

14:46  🧬 MUTAÇÕES · barra da rodada 2 (identity.py, auth.py)  ·  4 de 4
       mortas
       ☠️  REQUIRED_CLAIMS sem "exp"                    2 testes
       ☠️  REQUIRED_CLAIMS vazio                        1+ teste
       ☠️  options sem "require"                        1+ teste
       ☠️  require sem atalho de admin (!= role)        1 teste

14:47  🧬 MUTAÇÕES · regressão das 🧬 da rodada 1  ·  13 de 13 mortas
       ☠️  +HS256; sem audience; verify_exp False       1+ teste cada
       ☠️  cache sem validade; sem nova busca em kid    1 teste cada
       ☠️  sem refuse_when_forbidden                    1+ teste
       ☠️  require ignora papel; dev antes do Access    1 teste cada
       ☠️  confiar no cabeçalho; 403→401                1 teste cada
       ☠️  unauthenticated→403; saída 5→400; sem details  1+ teste cada

14:48  🧬 MUTAÇÕES · fora da barra  ·  0 de 2 mortas
       🚨  AUD lido de TEAM_DOMAIN        SOBREVIVEU — o mesmo da rodada
       1; falha fechada (401); recomendação não aplicada
       🚨  require: só admin passa (!= ADMIN)  SOBREVIVEU — nenhum
       assistente numa rota require("assistant"); o mutante tranca o
       assistente em toda rota de assistente das issues 20a/20b

14:48  🔎 QA     passo 1/4 — Erros HTTP  ·  ✅ PASS
       sem mudança desde a rodada 1; mutações exigidas continuam mortas

14:48  🔎 QA     passo 2/4 — Verificação do token  ·  ✅ PASS
       token sem exp → 401 em verify e por HTTP; mutante "exp ausente
       aceito" vermelho nos dois níveis; L9 no plan.md

14:49  🔎 QA     passo 3/4 — Membro e papel  ·  ✅ PASS
       atalho de admin coberto por require("assistant") no teste;
       mutante != role vermelho; L10 no plan.md

14:49  🔎 QA     passo 4/4 — Compose e documentação  ·  ✅ PASS
       sem mudança; ADR-0019 já diz "exp presente e no futuro" e "o
       administrador passa em todas"
