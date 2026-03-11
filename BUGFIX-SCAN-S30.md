# HELPDESK BUGFIX SCAN S30 — Relatório Consolidado

**Data:** 2026-03-11
**Arquivos scaneados:** ~90
**Agentes paralelos:** 10
**Total de bugs encontrados:** 206+

---

## RESUMO POR SEVERIDADE

| Severidade | Qtd | Impacto |
|-----------|-----|---------|
| CRITICAL  | 21  | Crash em produção, perda de dados, falha de segurança |
| HIGH      | 46  | Funcionalidade quebrada, race conditions, bloqueio de event loop |
| MEDIUM    | 72  | Lógica incorreta, UX ruim, performance, falta de validação |
| LOW       | 67+ | Code smell, inconsistências, manutenibilidade |

---

## CRITICAL (21) — Corrigir IMEDIATAMENTE

### Segurança
| # | Arquivo | Bug | Impacto |
|---|---------|-----|---------|
| C1 | core/config.py:11 | JWT_SECRET vazio permite forjar tokens | Qualquer pessoa cria JWT válido |
| C2 | webhooks/whatsapp.py:48 + meta_dm.py:97 | META_APP_SECRET vazio = verificação de webhook DESLIGADA por default | Atacante pode forjar webhooks |
| C3 | api/auth.py:185-187 | Password reset usa header Origin do request | Open redirect — roubo de token de reset |

### Perda de Dados
| # | Arquivo | Bug | Impacto |
|---|---------|-----|---------|
| C4 | api/gmail.py:147-448 | Sem try/except por email no fetch — 1 email ruim mata batch inteiro | Emails perdidos |
| C5 | api/gmail.py:183,232,447 | mark_as_read ANTES do db.commit — crash = email marcado como lido mas nunca salvo | Dados perdidos permanentemente |
| C6 | main.py:720-724 | Rollback no shared session desfaz commits anteriores no chat inactivity loop | Dados de conversas perdidos |
| C7 | voice_service.py:222 | handle_create_ticket faz flush mas nunca commit | Tickets de voz nunca persistidos |

### Crashes em Produção
| # | Arquivo | Bug | Impacto |
|---|---------|-----|---------|
| C8 | SettingsPage.jsx:195 | `isAdmin` usado antes de declarado (const não faz hoist) | ReferenceError — página crasha ao abrir |
| C9 | MetricasPage.jsx:97,118,138 | data.cards/agentes/volume_diario sem guards | White screen se API retorna dados parciais |
| C10 | api/ws.py:227-379 | Exceção no pipeline desconecta visitante permanentemente | Bot morre para o cliente |

### Race Conditions Críticas
| # | Arquivo | Bug | Impacto |
|---|---------|-----|---------|
| C11 | protocol_service.py:14-34 | generate_protocol usa SELECT MAX — sem lock | Protocolos duplicados |
| C12 | voice_service.py:209-211 | Ticket number via SELECT MAX — sem sequence | Números duplicados |
| C13 | webhooks/whatsapp.py:79-82 | scalar_one_or_none com múltiplas conversas abertas | MultipleResultsFound → 500 → retry storm |

### Lógica Quebrada
| # | Arquivo | Bug | Impacto |
|---|---------|-----|---------|
| C14 | message_pipeline.py:1573-1598 | Dead code após return em _escalate_to_agent — NUNCA cria ticket | Escalação não funciona |
| C15 | api/rewards.py:156-169 | Claim não deduz pontos — double-spend ilimitado | Agentes reclamam rewards infinitos |
| C16 | api/triage.py:29-31 | Mass assignment sem validação — request.json() direto | Campos sensíveis sobrescrevíveis |
| C17 | tickets.py:1096-1102 | Path traversal no upload de arquivo | Escrita fora do diretório |
| C18 | core/database.py:6 | DATABASE_URL vazio crasha engine na importação | App não sobe |

### Outros Critical
| # | Arquivo | Bug | Impacto |
|---|---------|-----|---------|
| C19 | Toast.jsx:150 | useCallback com objeto (não função) — violação de hooks | Erro React |
| C20 | csat_service.py:13 | CSAT reusa JWT_SECRET, token nunca expira | Security weakness |
| C21 | security.py:56-59 | Activity tracking commit falha = 500 em TODA request autenticada | Single point of failure |

---

## HIGH (46) — Corrigir esta semana

### Backend — Event Loop Blocking
| # | Arquivo | Bug |
|---|---------|-----|
| H1 | ai_service.py:760-774 | test_ai_connection síncrono bloqueia event loop |
| H2 | api/ai.py:256-260 | copilot_analysis chama Anthropic sync |
| H3 | api/ai.py:373-378 | assistant_chat chama Anthropic sync |
| H4 | tracking_service.py:188-190 | asyncio.sleep(3-8s) durante request de tracking |

### Backend — Race Conditions
| # | Arquivo | Bug |
|---|---------|-----|
| H5 | main.py:269-274 | Duplicate tickets — sem unique constraint em gmail_message_id |
| H6 | chat_routing_service.py:52-55 | auto_assign sem lock — agent assignment duplicado |
| H7 | meta_dm.py:259 | scalar_one_or_none crash com múltiplas conversas (mesmo C13) |
| H8 | webhooks/whatsapp.py:130-135 | Debounce dict unbounded — memory leak |

### Backend — Dados Incorretos
| # | Arquivo | Bug |
|---|---------|-----|
| H9 | api/gmail.py:695-763 | send_gmail_reply NUNCA salva Message no DB |
| H10 | api/gmail.py:727 | Lazy load ticket.customer em async = crash |
| H11 | tickets.py:1575-1584 | Unmerge query usa JSON path errado — nunca restaura mensagens |
| H12 | tickets.py:659-662 | SLA recalculado a partir de "agora" em vez de created_at |
| H13 | tickets.py:641-644 | setattr sem whitelist — campos sensíveis editáveis |
| H14 | shopify_service.py:238-241 | get_order_by_number retorna pedido ERRADO |
| H15 | ai_service.py:729 | Chat auto-reply regex falha com JSON nested — raw JSON vai pro cliente |
| H16 | ai_service.py:132-141 vs api/ai.py:94-96 | SLA usa prioridade da IA, não a final do ticket |
| H17 | triage_service.py:57-59 | Triage rules podem REBAIXAR prioridade set pela IA |
| H18 | gmail.py:229,286 | first_response_at resetado quando cliente responde — SLA corrompido |
| H19 | main.py:342 | first_response_at = None ao reabrir ticket — métrica perdida |
| H20 | main.py:361-373 | sla_response_deadline não setado em tickets novos |
| H21 | webhooks/whatsapp.py:83-85 | Missing db.flush antes de usar conversation.id |

### Backend — Segurança
| # | Arquivo | Bug |
|---|---------|-----|
| H22 | api/gmail.py:96-101 | OAuth callback expõe refresh_token sem auth |
| H23 | meta_dm.py:103-121 | print() com payload completo do webhook (PII) |
| H24 | meta_service.py:18-19 | verify_signature retorna True quando sem secret |
| H25 | troque_service.py:9 | API token hardcoded no source code |
| H26 | appmax_service.py:37-41 | API key em query parameter (visível em logs) |
| H27 | api/auth.py:132-134 | update_user permite admin desativar outros admins |
| H28 | api/triage.py:23-36 | Sem validação de input (Pydantic) nos CRUD de rules |
| H29 | api/auth.py:70 | list_users expõe todos os usuários a qualquer role |

### Backend — Outros
| # | Arquivo | Bug |
|---|---------|-----|
| H30 | escalation_service.py:35 | Datetime naive vs aware — crash na subtração |
| H31 | message_pipeline.py:1457 | asyncio.get_event_loop() deprecated |
| H32 | message_pipeline.py:1452-1454 | Observation timeout não cancelado quando cliente responde |
| H33 | voice_ws_manager.py:13-15 | Transcript lines crescem ilimitado — memory leak |
| H34 | voice_calls.py:64-76 | Carrega TODOS customers pra matching de telefone |
| H35 | main.py:282-285 | Thread match pode retornar ticket errado |
| H36 | main.py:1098 | Token NF PDF hardcoded |
| H37 | api/gmail.py:490-689 | fetch_email_history sem try/except por email |
| H38 | duplicate triage (main.py:389-430) | Triage duplicada sem recalcular SLA |
| H39 | ws.py:88 | Dict mutation during iteration no broadcast |

### Frontend — High
| # | Arquivo | Bug |
|---|---------|-----|
| H40 | ChatView.jsx:33-49 | Race condition: fetch A resolve depois de B → mensagens trocadas |
| H41 | ChatView.jsx:102-111 | Poll 30s faz setMessages([]) — flash de tela vazia |
| H42 | useWebSocket.js:14-76 | WS singleton nunca desconecta no logout |
| H43 | chat_ws_manager.py:18 | Single WS per agent — 2ª aba sobrescreve 1ª |
| H44 | VoiceCallsPage.jsx:404-408 | WebSocket nunca reconecta após close |
| H45 | ChatbotFlowsPage.jsx:430-438 | Sem error handling em toggle/delete |
| H46 | ComposeEmailModal.jsx:5-17 | Stale state quando modal reabre |

---

## TOP 20 FIXES — Prioridade de Execução

### Wave 1 — Crashes e Segurança (HOJE)
1. **C8** SettingsPage isAdmin ReferenceError — mover declaração
2. **C9** MetricasPage guards — adicionar `?.` e `|| []`
3. **C1** JWT_SECRET — raise RuntimeError se vazio
4. **C2** META_APP_SECRET — raise se vazio ou log WARNING gigante
5. **C5** mark_as_read após db.commit (não antes)
6. **C4** try/except por email individual no fetch_emails

### Wave 2 — Funcionalidade Quebrada (AMANHÃ)
7. **H9** send_gmail_reply salvar Message no DB
8. **C14** _escalate_to_agent dead code — implementar criação de ticket
9. **C13/H7** scalar_one_or_none → .scalars().first() nas conversas
10. **C11** Protocol generation → usar sequence PostgreSQL
11. **H16** SLA usar ticket.priority final, não AI priority
12. **H15** Chat auto-reply regex → JSON extraction correto

### Wave 3 — Race Conditions (ESTA SEMANA)
13. **H5** Unique constraint em Message.gmail_message_id + index
14. **H6** auto_assign com SELECT FOR UPDATE
15. **C10** Pipeline error → try/except + continuar (não desconectar)
16. **H21** db.flush() antes de usar conversation.id

### Wave 4 — Security Hardening
17. **C3** Password reset — usar URL do settings, não Origin header
18. **C17** File upload — sanitizar filename
19. **H22** OAuth callback — requerer auth
20. **H25** Mover tokens hardcoded pra env vars

---

## MEDIUM (72) — Lista Resumida

### Backend (45)
- Triage rules downgrade priority sem guard
- N+1 queries em triage_service e tickets.py
- Sync calls in async context (send_email, Gmail API)
- flag_modified faltando em metadata_ JSONB mutations (5+ locais)
- Batch auto-reply race condition (duplicatas)
- Rollback faltando em batch operations
- Activity tracking commit pode falhar
- Customer.total_tickets off-by-one
- Spam filter substring matching muito agressivo
- Redis connection sem reconnect
- Auto-close sem notificar cliente
- Export CSV com DB session que pode fechar
- Login attempts dict cresce forever
- CSAT submit via query params (PII em logs)
- Ticket autoincrement=True mas assigned manually
- Tags inconsistentes (JSONB vs ARRAY) entre models
- Profile fetch do Graph API em toda mensagem
- Webhook retry storm por falta de exception handling
- Debounce salva mensagem mas pula pipeline

### Frontend (27)
- Toast api object recriado todo render
- AudioContext never closed (leak após ~6 toasts)
- WS reconnect loop quando token é null
- Ping interval leak em reconnects rápidos
- Transfer dropdown sem click-outside handler
- handleResolve usa conversation stale
- ScrollIntoView dispara em todo poll (puxa scroll)
- Duplicate messages (API + WS)
- No error feedback ao usuário em ações falhadas
- No role-based route guards (URL direto funciona)
- TriagemPage agents list nunca atualiza
- Token no WebSocket URL query param
- api.js 401 causa full page reload
- Charts usam light-mode styles (theme === 'dark' sempre false)
- Muitas páginas mortas sem rotas (10+ arquivos)
- LoginPage logo preto em fundo escuro

---

## Arquivos com Mais Bugs

| Arquivo | Bugs | Mais Grave |
|---------|------|-----------|
| api/gmail.py | 17 | 2 CRITICAL |
| message_pipeline.py | 10 | 1 CRITICAL |
| main.py | 12 | 1 CRITICAL |
| api/ws.py | 8 | 1 CRITICAL |
| webhooks/whatsapp.py | 9 | 1 CRITICAL |
| TicketDetailPage.jsx | 11 | 1 CRITICAL |
| tickets.py | 15 | 1 CRITICAL |
| ai_service.py | 9 | 0 CRITICAL, 3 HIGH |
| ChatView.jsx | 8 | 1 CRITICAL |
| SettingsPage.jsx | 3 | 1 CRITICAL |

---

## Notas para Próxima Sessão

1. **Prioridade absoluta:** Waves 1-2 (items 1-12) — crashes e funcionalidade quebrada
2. **Antes de deployar:** Rodar migrations se adicionar index/constraint
3. **Commits atômicos:** Um commit por wave, testando entre cada
4. **Não quebrar:** Cada fix deve ser minimal e isolado
5. **Verificar:** Testar cada fix em prod após deploy
