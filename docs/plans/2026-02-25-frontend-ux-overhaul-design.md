# Frontend UX Overhaul — Design Doc

**Data:** 2026-02-25
**Abordagem:** Cirurgica (melhorias de alto impacto sem reescrita)
**Contexto:** Time de 4-10 agentes + supervisores, volume muito alto, helpdesk novo em fase de adocao, deploy meio a meio (staging/prod). Manter estetica atual (light theme, amarelo Carbon, glass morphism) e refinar.

---

## 1. URL Routing com React Router

**Problema:** Navegacao via useState — sem URLs, sem back/forward, refresh perde contexto, nao compartilha links.

**Solucao:**
- Usar react-router-dom (ja no package.json, nao utilizado)
- App.jsx wrappa com BrowserRouter
- Layout.jsx troca switch(page) por Routes/Route
- Sidebar.jsx troca onClick/setPage por NavLink
- onOpenTicket(id) vira navigate(/tickets/:id)
- onBack() vira navigate(-1) ou navigate('/tickets')

**Rotas:**
- `/dashboard` — DashboardPage
- `/tickets` — TicketsPage
- `/tickets/:id` — TicketDetailPage
- `/kb` — KBPage
- `/assistant` — AssistantPage
- `/media` — MediaPage
- `/catalog` — CatalogPage
- `/leaderboard` — LeaderboardPage
- `/tracking` — TrackingPage
- `/canais-ia` — CanaisIAPage
- `/moderation` — ModerationPage
- `/reports` — ReportsPage
- `/integrations` — IntegrationsPage
- `/settings` — SettingsPage

**Redirect:** `/` redireciona pra `/dashboard`. Rota 404 redireciona pra `/dashboard`.

**Ticket counts:** Continuam via polling no Layout (30s interval), passados via context ou props.

---

## 2. Command Palette (Cmd+K)

**Problema:** Nao existe busca global ou navegacao rapida por atalhos.

**Solucao:** Componente CommandPalette.jsx montado no Layout, escuta Cmd+K/Ctrl+K global.

**Funcionalidades:**
- Input de busca com debounce 200ms
- Navegacao por setas, Enter seleciona, Esc fecha
- 3 categorias de resultados:
  1. Tickets — busca por #numero, nome cliente, assunto. Mostra status + agente
  2. Paginas — Dashboard, KB, Configuracoes, etc.
  3. Acoes — Novo ticket, Exportar CSV, Atribuicao automatica

**Visual:**
- Overlay escuro semi-transparente
- Modal centralizado no topo (estilo Spotlight/Linear)
- Fundo glass com blur, borda sutil, shadow-lg
- Input grande no topo, resultados abaixo agrupados
- Item selecionado com highlight amarelo Carbon sutil
- Icones por tipo (ticket, pagina, acao)

**API:** Usa endpoint existente getTickets({search}) para busca de tickets.

---

## 3. Sidebar com Agrupamento

**Problema:** 13 itens numa lista flat — dificil de escanear.

**Solucao:** Agrupar em 3 secoes com labels discretos.

**Estrutura:**
```
ATENDIMENTO
  Dashboard
  Caixa de Entrada    [badge count]
  Canais IA           [badge count]
  Rastreamento

FERRAMENTAS
  Assistente IA
  Base de Conhecimento
  Biblioteca de Midia
  Catalogo
  Moderacao Social

GESTAO
  Performance
  Relatorios
  Integracoes          (so super_admin)
  Configuracoes
```

**Visual:**
- Labels de secao: text-[10px] uppercase tracking-wider, cor cinza (#636366)
- mt-5 entre secoes (espacamento, nao linha)
- Itens mantém estilo atual (hover, active com amarelo)
- Role-based filtering continua funcionando

---

## 4. Dashboard Simplificado

**Problema:** Admin view tem 16 KPI cards em 3 fileiras + 6 graficos. Tudo tem o mesmo peso visual.

**Solucao:** Hierarquia clara com hero row + secoes colapsaveis.

**Layout Admin:**
1. Hero Row (4 cards grandes): Abertos, SLA %, Tempo Resposta, Risco Juridico
   - Cards maiores com contexto extra (delta vs ontem, meta)
2. Secondary KPIs: colapsavel com toggle "Ver mais metricas", fechado por padrao
   - Trocas, Escalados, FCR, Resolvidos Hoje, Respondidos Hoje, Nao Atribuidos, etc.
3. Graficos principais: so 2 (Volume Diario + Por Categoria)
4. Graficos secundarios: colapsavel "Mais graficos"
   - Status, Prioridade, Canal, Sentimento
5. Acesso rapido por categoria: mantém, mais compacto

**Views Gestao/Agente:** mesma logica — hero row + colapsaveis.

---

## 5. Skeleton Loading

**Problema:** Loading states sao apenas spinners (fa-spinner). Conteudo "pula" ao carregar.

**Solucao:** Componente Skeleton reutilizavel com variantes.

**Onde aplica:**
1. Lista de tickets — 8 linhas skeleton pulsantes
2. Ticket detail — skeleton header + mensagens + sidebar
3. Dashboard KPIs — cards com retangulo pulsante

**Implementacao:**
- Componente Skeleton com variantes: line, card, circle
- CSS puro com @keyframes e gradiente animado (shimmer)
- Nao adiciona dependencia externa

---

## 6. Preview na Lista de Tickets

**Problema:** Time precisa abrir cada ticket pra saber do que se trata. Com volume alto, isso desperdiceca muito tempo.

**Solucao:** Adicionar informacoes na row da tabela.

**Adicoes:**
- Abaixo do assunto: snippet da ultima mensagem (60-80 chars, cinza, truncado)
- Ao lado do SLA: tempo desde ultima resposta ("ha 2h", "ha 15min")
- Indicador visual se ultimo quem respondeu foi o cliente (bolinha azul = precisa de acao)

**Dados:** Backend ja retorna messages no ticket. Usar last_message_preview ou calcular no frontend.

---

## 7. Sticky Table Headers

**Problema:** Ao rolar lista de tickets, perde referencia das colunas.

**Solucao:**
- position: sticky; top: 0; z-index: 10 no thead
- Background solido (nao transparente) no header
- Sombra sutil embaixo quando ha scroll
- Aplica em: tickets, enviados, spam

---

## 8. Refinamento Tipografico

**Problema:** Inter eh funcional mas generica. Hierarquia visual fraca.

**Solucao:**
- Trocar Inter por DM Sans (Google Fonts, gratis)
- Adicionar JetBrains Mono para elementos monospace
- Hierarquia:
  - Titulos de pagina: DM Sans 600, 24px
  - Labels de secao: DM Sans 500, 10px uppercase tracking-wider
  - Corpo/tabela: DM Sans 400, 13px
  - Numeros/metricas: DM Sans 700, 28px
  - Monospace (SLA, ticket number): JetBrains Mono 500, 12px
- Espacamento vertical mais generoso entre secoes
- Line-height do corpo de mensagens: leading-[1.7]

---

## 9. Keyboard Shortcuts Overlay

**Problema:** Atalhos existem mas sao invisiveis.

**Solucao:** Pressionar ? (fora de inputs) abre modal com todos os atalhos.

**Layout:** 2 colunas, agrupado por contexto.

**Atalhos existentes:**
- Alt+R: Resolver ticket
- Alt+E: Escalar ticket
- Alt+W: Aguardando
- Alt+N: Proximo ticket
- Alt+S: Sugestao IA
- Alt+F: Focar reply
- Cmd+Enter: Enviar mensagem
- /: Macros (slash commands)

**Novos atalhos:**
- Cmd+K: Command palette
- ?: Overlay de atalhos
- G D: Go to Dashboard
- G T: Go to Tickets
- G K: Go to KB
- J/K: Navegar tickets na lista (estilo Gmail)
- X: Selecionar ticket na lista
- Enter: Abrir ticket selecionado
- Esc: Fechar modal/overlay

**Componente:** KeyboardShortcutsModal.jsx + hook useKeyboardShortcuts.js

---

## Arquivos Impactados

**Novos:**
- src/components/CommandPalette.jsx
- src/components/Skeleton.jsx
- src/components/KeyboardShortcutsModal.jsx
- src/hooks/useKeyboardShortcuts.js

**Modificados:**
- src/App.jsx (BrowserRouter)
- src/components/Layout.jsx (Routes, CommandPalette, shortcuts)
- src/components/Sidebar.jsx (NavLink, agrupamento)
- src/pages/DashboardPage.jsx (hierarquia, colapsaveis)
- src/pages/TicketsPage.jsx (preview, sticky, skeleton, J/K nav)
- src/pages/TicketDetailPage.jsx (skeleton, navigate)
- src/index.css (tipografia, skeleton keyframes, sticky)
- index.html (Google Fonts link)

**Sem mudancas:** LoginPage, KBPage, IntegrationsPage, ReportsPage, SettingsPage, TrackingPage, AssistantPage, MediaPage, CatalogPage, LeaderboardPage, ModerationPage, CanaisIAPage, Toast, api.js
