# Changelog — Carbon Expert Hub (Helpdesk)

Todas as alterações relevantes do projeto documentadas por data.

---

## [2026-02-26] — Permissões e Roles

### Corrigido
- Agentes agora têm acesso a **todos os tickets** (antes só viam os atribuídos a eles)
- Removido filtro restritivo `assigned_to == user.id` no endpoint `GET /tickets`

### Alterado
- **Pedro** e **Lyvia** promovidos a `super_admin`
- **Victor** e **Tauane** promovidos a `supervisor`
- Luana e Reinan permanecem como `agent`

---

## [2026-02-25] — Análise de Equipe + Overhaul Visual do Frontend

### Adicionado — Análise de Agentes (`/agent-analysis`)
- Página exclusiva para super_admin com análise profunda da equipe
- Métricas quantitativas por agente: tickets resolvidos, tempo médio de resposta, SLA, CSAT
- Análise qualitativa com IA (Claude) das mensagens dos agentes
- Scores de qualidade: empatia, clareza, resolução, tom profissional
- Relatórios semanais automáticos gerados todo domingo 23h UTC
- Histórico de relatórios por período
- Service: `agent_analysis_service.py`
- Model: `agent_report.py`
- API: `agent_analysis.py` (7 endpoints, super_admin only)

### Adicionado — Overhaul Visual do Frontend
- Design system completo com paleta dark + dourado Carbon (#E5A800)
- Sidebar redesenhada com gradiente e navegação por grupos
- Layout responsivo com skeleton loading states
- Componente `CommandPalette.jsx` — busca rápida com atalho `Ctrl+K`
- Componente `KeyboardShortcutsModal.jsx` — modal de atalhos
- Componente `NotificationBell.jsx` — sino de notificações real-time
- Componente `Toast.jsx` — notificações toast
- Componente `Skeleton.jsx` — loading placeholders
- Componente `MetaBadge.jsx` — badge de plataforma Meta
- Todas as páginas redesenhadas com novo design system

### Adicionado — Performance do Frontend
- Leaderboard com gamificação: pontos, ranking, streaks
- Sistema de recompensas (rewards) com resgate por pontos
- API de gamificação: `gamification.py`
- API de recompensas: `rewards.py`

---

## [2026-02-24] — Helpdesk 100% + Otimização de Performance

### Adicionado — Features Completas do Helpdesk
- **Protocolo automático** — número único por ticket (formato CARBON-YYYYMMDD-XXXX)
- **Notas internas** (sticky notes) — campo separado das mensagens
- **Notas do fornecedor** — campo para comunicação com fornecedores
- **Merge de tickets** — unificação de tickets duplicados do mesmo cliente
- **CC/BCC em emails** — suporte a cópia e cópia oculta
- **Agendamento de envio** — agendar email para envio futuro
- **Busca ampla** — pesquisa por assunto, número, nome, email, tracking, conteúdo
- **Blacklist de clientes** — flag de clientes problemáticos com motivo
- **Customer notes/tags** — anotações e tags por cliente
- **Tracking integrado** — código de rastreio com status no ticket

### Adicionado — Otimização de Performance
- Índices compostos para queries frequentes (status+created, agent+created, source+created)
- Índice parcial para SLA não-breached
- Índices para mensagens por tipo
- Ordenação por `received_at` (data real do email) em vez de `created_at`

### Adicionado — Módulos de Rastreamento
- Integração **LinkeTrack** para rastreio Correios
- Integração **17Track** para rastreio internacional
- Service: `tracking_service.py`
- API: `tracking.py`
- Página: `TrackingPage.jsx`

---

## [2026-02-23] — Canais Meta (WhatsApp/Instagram/Facebook) + Correções

### Adicionado — Integração Meta
- **WhatsApp Business** — receber e responder mensagens via API
- **Instagram DM** — receber e responder mensagens diretas
- **Facebook Messenger** — receber e responder mensagens
- **Moderação de comentários** com IA — análise automática de comentários do Instagram/Facebook
- Auto-resposta por IA nos canais Meta com toggle on/off por ticket
- Webhook unificado para todas as plataformas Meta
- Service: `meta_service.py`
- API: `meta.py`
- Página: `CanaisIAPage.jsx` — painel de canais com IA
- Página: `ModerationPage.jsx` — moderação de comentários sociais
- Model: `social_comment.py`
- Tabela `moderation_settings` para configurações de auto-moderação

### Corrigido — Diagnóstico e Fixes
- Fix de CSS em múltiplas páginas
- Fix de configurações do backend
- Correções gerais de estabilidade
- Scripts de correção: `fix-all.sh`, `fix-backend.sh`, `fix-css.sh`, `fix-settings.sh`

---

## [2026-02-22] — Integração E-Commerce + Deploy Inicial

### Adicionado — Integração E-Commerce
- Service **Yampi** — busca de pedidos, detalhes, rastreio
- Service **Appmax** — busca de vendas, detalhes, transações
- API unificada: `GET /api/ecommerce/orders?email=X`
- Normalização de status entre plataformas (pago, enviado, entregue, etc.)
- Mascaramento de credenciais nas respostas
- Configuração por env vars, JSON ou banco

### Adicionado — Integração Shopify
- Service: `shopify_service.py`
- API: `shopify.py`

### Adicionado — Deploy e Infraestrutura
- Docker Compose para produção (PostgreSQL 16, Redis 7, Backend, Frontend, Nginx)
- Scripts de deploy automatizado com backup prévio do banco
- Configuração Nginx com proxy reverso
- Health check com monitoramento de email fetch e créditos IA
- SSL/domínio: `helpdesk.brutodeverdade.com.br`
- Servidor: DigitalOcean `143.198.20.6`

---

## [Base] — Sistema Core

### Atendimento
- **Tickets** — CRUD completo com 11 status, 4 prioridades, categorias, tags
- **Caixa de entrada** — listagem com filtros avançados, paginação, ordenação
- **Inboxes** — caixas de entrada configuráveis
- **Atribuição** — manual e em massa (bulk assign/update)
- **Lock de ticket** — evita edição simultânea
- **SLA** — deadlines de resposta e resolução com cálculo automático por categoria/prioridade
- **Escalação automática** — verificação a cada 5 min, escala tickets vencidos

### Comunicação
- **Gmail** — integração bidirecional (receber/enviar), fetch automático a cada 60s
- **Slack** — integração para notificações e alertas
- **WebSocket** — notificações real-time (novo ticket, atribuição, atualização)
- **Emails enviados** — histórico de mensagens outbound

### IA (Claude)
- **Triagem automática** — categorização, prioridade, sentimento, risco jurídico
- **Resumo automático** — AI summary por ticket
- **Tags automáticas** — sugestão de tags por IA
- **Assistente IA** — página dedicada para consultas (`AssistantPage.jsx`)
- **Auto-resposta** nos canais Meta

### Gestão
- **Dashboard** — métricas em tempo real (abertos, meus, equipe, SLA, etc.)
- **Relatórios** — exportação e análise por período
- **Export** — exportação de dados
- **CSAT** — pesquisa de satisfação por email (link público, sem auth)
- **Clientes** — gestão com histórico, blacklist, merge, notes

### Ferramentas
- **Base de Conhecimento (KB)** — artigos internos para consulta
- **Biblioteca de Mídia** — arquivos do Google Drive integrados
- **Catálogo de Produtos** — referência rápida de produtos

### Segurança
- JWT com expiração configurável
- Roles: `super_admin`, `admin`, `supervisor`, `agent`
- Permissões por role na sidebar e endpoints
- Audit log para ações críticas
- CORS configurado por ambiente

### Stack Técnica
- **Backend:** Python 3.11 + FastAPI + SQLAlchemy (async) + PostgreSQL 16 + Redis 7
- **Frontend:** React + Vite + Tailwind CSS
- **IA:** Claude (Anthropic API)
- **Email:** Gmail API
- **Deploy:** Docker Compose + Nginx + DigitalOcean
