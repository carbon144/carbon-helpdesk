# Visual Overhaul — Design Doc ("Carbon Gold")

**Data:** 2026-02-25
**Abordagem:** Evolucao visual — sai glass morphism lavanda, entra solid gold premium
**Contexto:** Light theme pro uso prolongado com volume alto. Mais personalidade Carbon + estetica moderna (Linear/Stripe). Zero mudanca funcional.

---

## 1. Paleta de Cores

**Backgrounds — brancos limpos:**
- `--bg-primary`: `#FFFFFF` (era #f2f2f7)
- `--bg-secondary`: `#FFFFFF` (era rgba transparente com blur)
- `--bg-tertiary`: `#F9FAFB` (inputs, areas recuadas)
- `--bg-hover`: `#F3F4F6`
- `--bg-active`: `rgba(229,168,0,0.06)`
- `--bg-input`: `#F9FAFB`

**Accent — dourado rico:**
- `--accent`: `#E5A800` (era #fdd200)
- `--accent-hover`: `#CC9600`
- `--accent-soft`: `rgba(229,168,0,0.08)`
- `--accent-text`: `#FFFFFF` (era #1d1d1f — agora branco no dourado)

**Textos — cinzas definidos:**
- `--text-primary`: `#111827`
- `--text-secondary`: `#4B5563`
- `--text-tertiary`: `#9CA3AF`
- `--text-inverse`: `#FFFFFF`
- `--text-on-accent`: `#FFFFFF`

**Bordas — solidas, visiveis:**
- `--border-color`: `#E5E7EB`
- `--border-hover`: `#D1D5DB`
- `--border-focus`: `#E5A800`

**Sidebar:**
- Background: gradiente `#18181B` → `#1F1F23`
- Borda direita: `1px solid rgba(229,168,0,0.3)` (assinatura dourada)
- Nav default: `#71717A`
- Nav hover: `#E4E4E7` + bg `rgba(255,255,255,0.06)`
- Nav active: `#E5A800` + bg `rgba(229,168,0,0.10)`
- Section labels: `#52525B`
- Badge: bg `#E5A800`, texto `#FFFFFF`

**Sombras — Stripe style:**
- `--shadow-sm`: `0 1px 2px rgba(0,0,0,0.05)`
- `--shadow-md`: `0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)`
- `--shadow-lg`: `0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.04)`

**Scrollbars:**
- Thumb: `#D1D5DB`, hover: `#9CA3AF`

---

## 2. Cards e Superficies

- Background: `#FFFFFF` solido
- Borda: `1px solid #E5E7EB`
- Border-radius: `12px` (era 16px)
- Sombra: `--shadow-sm`, hover `--shadow-md`
- **Zero** backdrop-filter, **zero** blur, **zero** rgba backgrounds
- Hover: borda `#D1D5DB` + sombra sobe

**Inputs:**
- Background: `#F9FAFB`
- Borda: `#E5E7EB`, foco `#E5A800` + ring `rgba(229,168,0,0.15)`
- Border-radius: `8px`

**Botoes primarios:**
- Background: `#E5A800` → hover `#CC9600`
- Texto: `#FFFFFF`
- Border-radius: `8px`

**Badges de status:**
- Backgrounds `rgba(..., 0.10)` (mais opacos que antes)
- Textos um tom mais escuro

**Tabelas:**
- Header: `#F9FAFB`, borda bottom `#E5E7EB`
- Rows: branco, hover `#F9FAFB`
- Divisorias: `#F3F4F6`

---

## 3. Sidebar

- Gradiente vertical: `#18181B` → `#1F1F23`
- Borda direita: `1px solid rgba(229,168,0,0.3)`
- Logo borda bottom: `rgba(255,255,255,0.08)`
- Avatar: `#E5A800` + inicial `#FFFFFF`

---

## 4. Tipografia e Espacamento

- Titulos pagina: `24px, weight 700`
- Valores KPI hero: `32px, weight 800`
- Gap entre secoes dashboard: `32px`
- Padding cards: `20px`
- Padding main content: `32px` (p-8)

---

## 5. Modais

- Background: `#FFFFFF` solido
- Borda: `1px solid #E5E7EB`
- Sombra: `0 25px 50px rgba(0,0,0,0.12)`
- Backdrop: `rgba(0,0,0,0.30)` **sem** blur
- Input area: `#F9FAFB`
- Item selecionado: `rgba(229,168,0,0.08)`
- Kbd: `#F3F4F6` bg, `#E5E7EB` borda, `#4B5563` texto

---

## 6. Login Page

- Background: `#FFFFFF`
- Card: borda `#E5E7EB`, sombra `--shadow-lg`
- Logo "C": bg `#E5A800`, texto `#FFFFFF`
- "EXPERT HUB": cor `#E5A800`
- Circulos decorativos: dourado `opacity: 0.04`

---

## 7. Skeleton Loading

- Shimmer: `#F3F4F6` → `#FFFFFF` → `#F3F4F6`

---

## Arquivos Impactados

**Modificados:**
- `frontend/src/index.css` — paleta, remove glass, ajusta overrides
- `frontend/src/pages/LoginPage.jsx` — cores accent
- `frontend/src/components/Sidebar.jsx` — gradiente, borda dourada, cores
- `frontend/src/components/CommandPalette.jsx` — modal solido
- `frontend/src/components/KeyboardShortcutsModal.jsx` — modal solido
- `frontend/src/components/Skeleton.jsx` — shimmer colors
- `frontend/src/pages/DashboardPage.jsx` — espacamento, KPICard cores

**Sem mudancas:** Layout.jsx, App.jsx, TicketsPage.jsx, TicketDetailPage.jsx, routing, API, funcionalidade
