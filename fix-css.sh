#!/bin/bash
set -e
echo "=== Fixing CSS transition bug ==="

CSS_FILE="/opt/carbon-helpdesk/frontend/src/index.css"

# Backup
cp "$CSS_FILE" "$CSS_FILE.bak"

# Write the fixed CSS
cat > "$CSS_FILE" << 'CSS_EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ═══════════════════════════════════════════════
   CARBON HELPDESK — Design System Tokens
   Dark + Light theme support
   ═══════════════════════════════════════════════ */

:root[data-theme="dark"], :root:not([data-theme]) {
  /* Palette */
  --carbon-900: #09090b;
  --carbon-800: #111113;
  --carbon-700: #1a1a1f;
  --carbon-600: #232329;
  --carbon-500: #3a3a42;
  --carbon-400: #71717a;
  --carbon-300: #a1a1aa;
  --carbon-200: #d4d4d8;
  --carbon-100: #e4e4e7;
  --carbon-50: #fafafa;

  /* Semantic — backgrounds */
  --bg-primary: #09090b;
  --bg-secondary: #111113;
  --bg-tertiary: #1a1a1f;
  --bg-elevated: #232329;
  --bg-hover: #1f1f26;
  --bg-active: rgba(253, 210, 0, 0.08);
  --bg-input: #141417;

  /* Semantic — text */
  --text-primary: #fafafa;
  --text-secondary: #a1a1aa;
  --text-tertiary: #71717a;
  --text-inverse: #09090b;
  --text-on-accent: #09090b;

  /* Semantic — borders */
  --border-color: #232329;
  --border-hover: #3a3a42;
  --border-focus: #fdd200;

  /* Accent (Carbon Yellow) */
  --accent: #fdd200;
  --accent-hover: #e6c000;
  --accent-muted: #b89400;
  --accent-soft: rgba(253, 210, 0, 0.12);
  --accent-text: #09090b;

  /* Scrollbar */
  --scrollbar-track: #111113;
  --scrollbar-thumb: #2a2a32;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.4);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.5);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.6);

  color-scheme: dark;
}

:root[data-theme="light"] {
  /* Palette */
  --carbon-900: #ffffff;
  --carbon-800: #f8f9fa;
  --carbon-700: #eef0f2;
  --carbon-600: #dee2e6;
  --carbon-500: #adb5bd;
  --carbon-400: #6c757d;
  --carbon-300: #495057;
  --carbon-200: #343a40;
  --carbon-100: #212529;
  --carbon-50: #0d1117;

  /* Semantic — backgrounds */
  --bg-primary: #f8f9fa;
  --bg-secondary: #ffffff;
  --bg-tertiary: #eef0f2;
  --bg-elevated: #ffffff;
  --bg-hover: #e9ecef;
  --bg-active: rgba(180, 130, 0, 0.06);
  --bg-input: #ffffff;

  /* Semantic — text */
  --text-primary: #1a1a2e;
  --text-secondary: #495057;
  --text-tertiary: #868e96;
  --text-inverse: #ffffff;
  --text-on-accent: #09090b;

  /* Semantic — borders */
  --border-color: #dee2e6;
  --border-hover: #ced4da;
  --border-focus: #b89400;

  /* Accent */
  --accent: #c9a600;
  --accent-hover: #b89400;
  --accent-muted: #9a7d00;
  --accent-soft: rgba(180, 130, 0, 0.1);
  --accent-text: #09090b;

  /* Scrollbar */
  --scrollbar-track: #f8f9fa;
  --scrollbar-thumb: #ced4da;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);

  color-scheme: light;
}

/* ═══ Global Reset ═══ */
* {
  scrollbar-width: thin;
  scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--scrollbar-track); }
::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-hover); }

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ═══ Carbon Brand — Indigo → Yellow Override ═══ */

/* Solid backgrounds */
.bg-indigo-600 { background-color: var(--accent) !important; color: var(--accent-text) !important; }
.bg-indigo-500 { background-color: var(--accent-hover) !important; color: var(--accent-text) !important; }
.bg-indigo-700 { background-color: var(--accent-muted) !important; }

/* Hover */
.hover\:bg-indigo-500:hover { background-color: var(--accent-hover) !important; color: var(--accent-text) !important; }
.hover\:bg-indigo-600:hover { background-color: var(--accent) !important; color: var(--accent-text) !important; }
.hover\:bg-indigo-700:hover { background-color: var(--accent-muted) !important; }

/* Text */
.text-indigo-400, .text-indigo-500, .text-indigo-600 { color: var(--accent) !important; }
.text-indigo-300 { color: #fde047 !important; }

/* Borders */
.border-indigo-500, .border-indigo-600 { border-color: var(--accent) !important; }
.border-indigo-700 { border-color: var(--accent-muted) !important; }
.border-indigo-700\/30 { border-color: rgba(253, 210, 0, 0.2) !important; }
.border-indigo-500\/50 { border-color: var(--accent-soft) !important; }

/* Soft BGs */
.bg-indigo-600\/20, .bg-indigo-600\/10, .bg-indigo-500\/20, .bg-indigo-500\/10 { background-color: var(--accent-soft) !important; }
.bg-indigo-900\/20, .bg-indigo-900\/30 { background-color: var(--accent-soft) !important; }

/* Hover transparent */
.hover\:bg-indigo-600\/30:hover, .hover\:bg-indigo-900\/40:hover { background-color: rgba(253, 210, 0, 0.18) !important; }

/* Focus/ring */
.focus\:ring-indigo-500:focus, .ring-indigo-500 { --tw-ring-color: var(--accent) !important; }
.focus\:border-indigo-500:focus { border-color: var(--accent) !important; }

/* Buttons with accent bg → black text */
.bg-indigo-600 .text-white,
.bg-indigo-600.text-white,
.bg-indigo-500 .text-white,
.bg-indigo-500.text-white { color: var(--accent-text) !important; }

/* Avatar fix */
.bg-indigo-600.flex.items-center.justify-center { background-color: var(--accent-muted) !important; color: #fff !important; }

/* Focus inputs */
.settings-input:focus, .settings-input-sm:focus { border-color: var(--accent) !important; }

/* ═══ Light Theme Overrides ═══ */
[data-theme="light"] .text-white { color: var(--text-primary) !important; }
[data-theme="light"] .bg-black { background-color: var(--bg-primary) !important; }
[data-theme="light"] .bg-\[\#000\], [data-theme="light"] .bg-\[\#0a0a0a\] { background-color: var(--bg-primary) !important; }

/* Light theme — sidebar */
[data-theme="light"] .bg-carbon-900 { background-color: #ffffff !important; }
[data-theme="light"] .border-carbon-700 { border-color: #e5e7eb !important; }
[data-theme="light"] .text-carbon-300 { color: #495057 !important; }
[data-theme="light"] .text-carbon-400 { color: #6c757d !important; }
[data-theme="light"] .text-carbon-500 { color: #868e96 !important; }
[data-theme="light"] .hover\:bg-carbon-700:hover { background-color: #f1f3f5 !important; }
[data-theme="light"] .bg-carbon-700 { background-color: #eef0f2 !important; }
[data-theme="light"] .bg-carbon-600 { background-color: #dee2e6 !important; }
[data-theme="light"] .bg-carbon-700\/50 { background-color: rgba(238, 240, 242, 0.5) !important; }

/* Light theme — cards, modals, panels */
[data-theme="light"] [class*="bg-\[var(--bg-secondary)\]"] { box-shadow: var(--shadow-sm); }

/* ═══ Utility classes ═══ */
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

.card-hover:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-sm);
}

/* Smooth transitions for theme switching — scoped to avoid breaking animations */
body,
.card,
[style*="--bg-"],
nav button,
aside,
header {
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

/* ═══ Better Inputs ═══ */
input[type="text"],
input[type="email"],
input[type="password"],
input[type="search"],
input[type="number"],
input[type="url"],
textarea,
select {
  background: var(--bg-input);
  border-color: var(--border-color);
  color: var(--text-primary);
}

input::placeholder, textarea::placeholder {
  color: var(--text-tertiary);
}

CSS_EOF

echo "CSS updated. Rebuilding..."
cd /opt/carbon-helpdesk
docker compose -f docker-compose.prod.yml up -d --build frontend
echo "=== Done ==="
