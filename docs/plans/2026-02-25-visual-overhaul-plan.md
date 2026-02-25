# Visual Overhaul ("Carbon Gold") — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Carbon Helpdesk visual identity from "glass morphism lavanda" to "solid gold premium" — white backgrounds, gold accent, defined borders, zero blur. Light theme optimized for all-day use.

**Architecture:** Pure CSS variable + inline style changes. No component restructuring, no new files, no functional changes. The entire palette lives in index.css `:root` — changing variables propagates everywhere they're referenced. Components with hardcoded colors need surgical edits.

**Tech Stack:** CSS custom properties, Tailwind CSS 3.4, React inline styles

---

### Task 1: Core Palette — index.css CSS Variables

**Files:**
- Modify: `frontend/src/index.css`

**Step 1: Replace `:root` variables**

In `frontend/src/index.css`, replace the entire `:root` block (lines 10-58) with:

```css
:root {
  /* Backgrounds — clean whites */
  --bg-primary: #FFFFFF;
  --bg-secondary: #FFFFFF;
  --bg-tertiary: #F9FAFB;
  --bg-elevated: #FFFFFF;
  --bg-hover: #F3F4F6;
  --bg-active: rgba(229,168,0,0.06);
  --bg-input: #F9FAFB;
  --bg-glass: #FFFFFF;

  /* Text — defined grays */
  --text-primary: #111827;
  --text-secondary: #4B5563;
  --text-tertiary: #9CA3AF;
  --text-inverse: #FFFFFF;
  --text-on-accent: #FFFFFF;

  /* Borders — solid, visible */
  --border-color: #E5E7EB;
  --border-hover: #D1D5DB;
  --border-focus: #E5A800;

  /* Accent — rich gold */
  --accent: #E5A800;
  --accent-hover: #CC9600;
  --accent-muted: #B8860B;
  --accent-soft: rgba(229,168,0,0.08);
  --accent-text: #FFFFFF;

  /* Sidebar */
  --sidebar-bg: #18181B;
  --sidebar-text: #E4E4E7;
  --sidebar-text-secondary: #71717A;
  --sidebar-hover: rgba(255,255,255,0.06);
  --sidebar-active: rgba(229,168,0,0.10);
  --sidebar-border: rgba(255,255,255,0.08);

  /* Scrollbar */
  --scrollbar-track: transparent;
  --scrollbar-thumb: #D1D5DB;

  /* Shadows — Stripe style */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
  --shadow-lg: 0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.04);
  --shadow-glass: 0 1px 2px rgba(0,0,0,0.05);

  color-scheme: light;
}
```

**Step 2: Replace glass utilities**

Replace the `.glass` and `.glass-card` blocks with solid versions:

```css
/* ═══ Solid Card Utilities ═══ */
.glass {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.glass-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
.glass-card:hover {
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
  border-color: #D1D5DB;
}
```

**Step 3: Update scrollbar thumb hover**

Replace the scrollbar `:hover` rule:

```css
::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }
```

**Step 4: Update `.card` utility**

Replace:

```css
.card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
```

**Step 5: Update input border-radius**

In the global input styles, change `border-radius: 10px` to `border-radius: 8px`.

Change the focus ring:
```css
input:focus, textarea:focus, select:focus {
  border-color: #E5A800 !important;
  box-shadow: 0 0 0 3px rgba(229,168,0,0.15);
  outline: none;
}
```

**Step 6: Update sidebar nav CSS**

Replace sidebar nav styles:

```css
.sidebar-nav-item {
  color: #71717A;
  transition: background 0.15s ease, color 0.15s ease;
}
.sidebar-nav-item:not(.sidebar-nav-active):hover {
  background: rgba(255,255,255,0.06);
  color: #E4E4E7;
}
.sidebar-nav-active {
  background: rgba(229,168,0,0.10);
  color: #E5A800;
}
```

**Step 7: Update skeleton shimmer**

Replace:

```css
.skeleton {
  background: linear-gradient(90deg, #F3F4F6 25%, #FFFFFF 50%, #F3F4F6 75%);
  background-size: 800px 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}
```

**Step 8: Update sticky header background**

Replace:

```css
.sticky-header th {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #F9FAFB;
  box-shadow: 0 1px 0 #E5E7EB;
}
```

**Step 9: Verify build**

Run: `cd frontend && npm run build`

**Step 10: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: update core palette to Carbon Gold — solid whites, rich gold, defined borders"
```

---

### Task 2: Sidebar — Gradient + Gold Border

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`

**Step 1: Update sidebar container styles**

Replace the outer div's style:

```jsx
style={{ background: 'linear-gradient(180deg, #18181B 0%, #1F1F23 100%)', borderRight: '1px solid rgba(229,168,0,0.3)' }}
```

**Step 2: Update section label color**

Replace `style={{ color: '#636366' }}` on the section label `<p>` with:

```jsx
style={{ color: '#52525B' }}
```

**Step 3: Update ticket badge colors**

Replace the ticket count badge:
```jsx
style={{ background: '#E5A800', color: '#FFFFFF' }}
```

**Step 4: Update user avatar**

Replace avatar style:
```jsx
style={{ background: '#E5A800', color: '#FFFFFF' }}
```

**Step 5: Update user name color**

Replace `style={{ color: '#f5f5f7' }}` with:
```jsx
style={{ color: '#E4E4E7' }}
```

**Step 6: Update role label color**

Replace `style={{ color: '#636366' }}` on role label with:
```jsx
style={{ color: '#71717A' }}
```

**Step 7: Update logout button colors**

Replace `style={{ color: '#636366' }}` on the logout button and its mouse handlers:
```jsx
style={{ color: '#71717A' }}
onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
onMouseLeave={e => e.currentTarget.style.color = '#71717A'}
```

**Step 8: Verify build**

Run: `cd frontend && npm run build`

**Step 9: Commit**

```bash
git add frontend/src/components/Sidebar.jsx
git commit -m "feat: sidebar gradient background + gold accent border"
```

---

### Task 3: Modals — Solid Backgrounds, No Blur

**Files:**
- Modify: `frontend/src/components/CommandPalette.jsx`
- Modify: `frontend/src/components/KeyboardShortcutsModal.jsx`

**Step 1: Update CommandPalette backdrop**

Replace the backdrop div:
```jsx
<div className="absolute inset-0 bg-black/30" />
```
(Remove `backdrop-blur-sm`)

**Step 2: Update CommandPalette modal styles**

Replace the modal div's style:
```jsx
style={{
  background: '#FFFFFF',
  border: '1px solid #E5E7EB',
  boxShadow: '0 25px 50px rgba(0,0,0,0.12)',
}}
```
(Remove `backdropFilter`)

**Step 3: Update CommandPalette border colors**

Replace `borderColor: 'rgba(0,0,0,0.06)'` in the search input border-b and footer border-t with:
```jsx
style={{ borderColor: '#E5E7EB' }}
```

**Step 4: Update CommandPalette selected item highlight**

Replace all `rgba(253,210,0,0.08)` with `rgba(229,168,0,0.08)`.

**Step 5: Update CommandPalette kbd styles**

Replace `background: 'rgba(0,0,0,0.05)'` in all kbd elements with:
```jsx
style={{ background: '#F3F4F6', color: '#4B5563' }}
```

And the ESC kbd:
```jsx
style={{ background: '#F3F4F6', color: '#4B5563' }}
```

**Step 6: Update KeyboardShortcutsModal backdrop**

Replace the backdrop div:
```jsx
<div className="absolute inset-0 bg-black/30" />
```

**Step 7: Update KeyboardShortcutsModal modal styles**

Replace the modal div's style:
```jsx
style={{
  background: '#FFFFFF',
  border: '1px solid #E5E7EB',
  boxShadow: '0 25px 50px rgba(0,0,0,0.12)',
}}
```

**Step 8: Update KeyboardShortcutsModal border colors**

Replace `borderColor: 'rgba(0,0,0,0.06)'` with `borderColor: '#E5E7EB'` in header and footer.

**Step 9: Update kbd styling in KeyboardShortcutsModal**

Replace kbd style:
```jsx
style={{
  background: '#F3F4F6',
  color: 'var(--text-primary)',
  border: '1px solid #E5E7EB',
}}
```

And the footer kbd:
```jsx
style={{ background: '#F3F4F6' }}
```

**Step 10: Verify build**

Run: `cd frontend && npm run build`

**Step 11: Commit**

```bash
git add frontend/src/components/CommandPalette.jsx frontend/src/components/KeyboardShortcutsModal.jsx
git commit -m "feat: solid white modals, remove backdrop blur"
```

---

### Task 4: Dashboard — KPI Colors + Spacing

**Files:**
- Modify: `frontend/src/pages/DashboardPage.jsx`

**Step 1: Update KPI_COLORS accent entry**

Replace the accent entry in KPI_COLORS:
```jsx
accent: { bg: 'rgba(229,168,0,0.08)', text: '#E5A800' },
```

**Step 2: Update KPICard border-radius**

In the KPICard component, change `rounded-xl` to `rounded-lg` (12px → 8px equivalent — actually `rounded-xl` is 12px in Tailwind, which matches our design. Keep `rounded-xl`).

Actually, keep as-is — `rounded-xl` = 12px which is correct per the design.

**Step 3: Update KPICard hero value font-weight**

Change the hero value class:
```jsx
<p className={`${isHero ? 'text-[32px] font-extrabold' : 'text-2xl font-bold'}`} style={{ color: 'var(--text-primary)' }}>{value}</p>
```

**Step 4: Update ChartCard border-radius**

In ChartCard, change `rounded-xl` to `rounded-xl` (keep — 12px is correct).

**Step 5: Update main page padding**

In the main DashboardPage return, change `className="p-6"` to `className="p-8"`.

**Step 6: Update section gaps**

Change `mb-6` to `mb-8` on the hero KPI grid and the main charts grid in AdminDashboard (the gaps between major sections).

**Step 7: Verify build**

Run: `cd frontend && npm run build`

**Step 8: Commit**

```bash
git add frontend/src/pages/DashboardPage.jsx
git commit -m "feat: dashboard gold accent colors, larger spacing"
```

---

### Task 5: Login Page — Gold Accent

**Files:**
- Modify: `frontend/src/pages/LoginPage.jsx`

**Step 1: Update decorative circle opacity**

Change `opacity-[0.03]` to `opacity-[0.04]` on both decorative circles (lines 30, 32).

**Step 2: Update login card border-radius**

Change `rounded-2xl` to `rounded-xl` on the card div (line 37).

Correction: keep `rounded-2xl` for login — it's the hero card, deserves more radius.

Actually no — design says 12px border-radius for cards. `rounded-xl` = 12px. Change `rounded-2xl` (16px) to `rounded-xl` (12px).

**Step 3: Update input border-radius**

Change `rounded-lg` to `rounded-lg` on both inputs — `rounded-lg` = 8px, matches design. Keep as-is.

**Step 4: Verify build**

The LoginPage uses CSS variables extensively (`var(--accent)`, `var(--bg-primary)`, etc.), so most color changes are already handled by Task 1's CSS variable update. The only hardcoded values to check are the decorative circle opacities.

Run: `cd frontend && npm run build`

**Step 5: Commit**

```bash
git add frontend/src/pages/LoginPage.jsx
git commit -m "feat: login page refined — gold circles, tighter radius"
```

---

### Task 6: Skeleton — Updated Colors

**Files:**
- Modify: `frontend/src/components/Skeleton.jsx`

**Step 1: Update SkeletonCard border-radius**

Change `rounded-xl` to `rounded-xl` in SkeletonCard — keep, 12px is correct.

**Step 2: Update SkeletonDashboard padding**

Change `className="p-6"` to `className="p-8"` in SkeletonDashboard to match the new dashboard padding.

**Step 3: Verify build**

Run: `cd frontend && npm run build`

**Step 4: Commit**

```bash
git add frontend/src/components/Skeleton.jsx
git commit -m "feat: skeleton padding matches new dashboard spacing"
```

---

### Task 7: Final Build Verification

**Step 1: Full build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 2: Review all color references**

Search for any remaining hardcoded old colors that should have changed:
- `#fdd200` — old yellow accent (should be `#E5A800` or `var(--accent)`)
- `#1d1d1f` — old sidebar text-on-accent (should be `#FFFFFF` or `var(--accent-text)`)
- `#f2f2f7` — old bg-primary (should be `#FFFFFF` or `var(--bg-primary)`)
- `rgba(255,255,255,0.72)` — old glass bg (should be `#FFFFFF`)
- `backdrop-filter` — should be removed everywhere except maybe 0 places

Fix any remaining references.

**Step 3: Commit if any fixes needed**

```bash
git add -A
git commit -m "chore: clean up remaining old color references"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Core palette CSS variables | index.css |
| 2 | Sidebar gradient + gold border | Sidebar.jsx |
| 3 | Modals solid, no blur | CommandPalette.jsx, KeyboardShortcutsModal.jsx |
| 4 | Dashboard KPI colors + spacing | DashboardPage.jsx |
| 5 | Login page gold accent | LoginPage.jsx |
| 6 | Skeleton updated padding | Skeleton.jsx |
| 7 | Final build + cleanup old colors | any remaining |
