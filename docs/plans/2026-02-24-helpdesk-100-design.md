# Carbon Helpdesk — "100%" Design Document

**Data:** 2026-02-24
**Objetivo:** Deixar o helpdesk 100% funcional, com merge de tickets/clientes, fixes diagnósticos e pronto pra produção.

---

## Bloco 1: Merge de Tickets e Clientes

### 1.1 Extração de Dados (Email Novo)

**Regex primeiro:**
- CPF: `\d{3}\.?\d{3}\.?\d{3}-?\d{2}`
- Telefone: `\(?\d{2}\)?\s?\d{4,5}-?\d{4}`
- Nº pedido Shopify: `#\d{4,}`
- Email secundário: pattern de email no corpo

**IA como fallback:**
- Se regex não extraiu nada, adicionar campos no prompt de triagem IA que já existe
- Prompt adicional: "Extraia CPF, telefone, nome completo e número de pedido se presentes"
- Sem custo extra (já faz triagem)

### 1.2 Match Automático por Thread

- Usar headers `In-Reply-To` e `References` do email
- Se o Message-ID bate com um email já associado a um ticket → adiciona mensagem ao ticket existente
- Não cria ticket novo

### 1.3 Match Automático por Dados do Cliente

- Email chega → extrai dados → busca no banco:
  - CPF igual → mesmo cliente
  - Telefone igual → mesmo cliente
  - Nº pedido Shopify igual → mesmo cliente
- Se achou cliente existente:
  - Linka email ao cliente
  - Se cliente tem ticket aberto → adiciona nota ao agente sugerindo merge (não faz automático)

### 1.4 Merge Manual (API + UI)

**Merge de tickets:**
- Endpoint: `POST /api/tickets/merge`
- Body: `{ source_ticket_id, target_ticket_id }`
- Comportamento:
  - Move todas as mensagens do source pro target (ordem cronológica)
  - Marca source como `status=merged`, `merged_into_id=target_id`
  - Copia notas internas
  - Audit log

**Merge de clientes:**
- Endpoint: `POST /api/customers/merge`
- Body: `{ source_customer_id, target_customer_id }`
- Comportamento:
  - Transfere todos os tickets do source pro target
  - Merge dados (preenche campos vazios do target com dados do source)
  - Marca source como `merged_into_id=target_id`
  - Audit log

**UI:**
- Botão "Mesclar" na tela de detalhe do ticket
- Modal de seleção do ticket destino (busca por ID, cliente, assunto)
- Botão "Mesclar clientes" na sidebar de informações do cliente
- Badge visual em tickets merged indicando origem

### 1.5 Modelo de Dados

**Customer (campos novos):**
- `cpf: String, nullable, indexed`
- `phone: String, nullable, indexed`
- `shopify_order_ids: JSON (lista), nullable`
- `merged_into_id: Integer, FK(customers.id), nullable`
- `alternate_emails: JSON (lista), nullable`

**Ticket (campos novos):**
- `merged_into_id: Integer, FK(tickets.id), nullable`
- `email_message_id: String, nullable` (Message-ID do header do email)

**Message (campos novos):**
- `email_message_id: String, nullable` (pra tracking de thread)
- `email_references: String, nullable` (References header)

---

## Bloco 2: Fixes Diagnósticos (29 tasks)

Implementar todas as 29 tasks do plano `2026-02-23-diagnostic-fixes.md`:

- **Phase 1 (Critical):** Tasks 1-7 — segurança, crashes, error handling
- **Phase 2 (High):** Tasks 8-19 — SLA, RBAC, WebSocket, frontend
- **Phase 3 (Medium):** Tasks 20-26 — lazy loading, debounce, config
- **Phase 4 (Low):** Tasks 27-29 — magic numbers, logging, inline styles

---

## Bloco 3: Produção

### 3.1 Segurança
- Remover credenciais hardcoded
- Remover demo credentials do login
- Validar JWT_SECRET como obrigatório (sem default)
- RBAC em endpoints sensíveis

### 3.2 Deploy
- Nginx com SSL (certificado auto-assinado ou Let's Encrypt pro IP)
- docker-compose.prod.yml atualizado
- Health checks adequados
- Script de backup PostgreSQL

### 3.3 Configuração
- Separar .env.prod de .env.dev
- Extrair Claude model pra config
- Guard seed data em produção

---

## Decisões de Design

1. **Regex + IA fallback** — 90% regex resolve, IA só quando necessário, sem custo extra
2. **Merge manual por default** — sistema sugere, agente confirma (evita erros)
3. **Thread matching automático** — respostas de email são caso seguro
4. **Soft delete em merges** — tickets/clientes merged ficam marcados, não deletados
