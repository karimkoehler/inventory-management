# Design tokens

Paste this `:root` block at the top of the global (unscoped) `<style>` in `client/src/App.vue`. Values keep the existing slate palette and blue accent; they only give names to colors the app already uses and add a spacing scale.

```css
:root {
  /* Surfaces and text (slate) */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-surface-muted: #f1f5f9;
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #64748b;
  --color-text-subtle: #94a3b8;

  /* Accent (blue) */
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-soft: #eff6ff;
  --color-focus-ring: rgba(37, 99, 235, 0.25);

  /* Status */
  --color-success: #10b981;
  --color-success-soft: #d1fae5;
  --color-success-text: #065f46;
  --color-warning: #f59e0b;
  --color-warning-soft: #fed7aa;
  --color-warning-text: #92400e;
  --color-danger: #ef4444;
  --color-danger-soft: #fecaca;
  --color-danger-text: #991b1b;
  --color-info-soft: #dbeafe;
  --color-info-text: #1e40af;

  /* Sidebar (dark slate) */
  --color-sidebar-bg: #0f172a;
  --color-sidebar-text: #cbd5e1;
  --color-sidebar-text-muted: #64748b;
  --color-sidebar-hover: #1e293b;
  --color-sidebar-active-bg: rgba(37, 99, 235, 0.16);
  --color-sidebar-active-text: #ffffff;
  --color-sidebar-accent: #3b82f6;

  /* Spacing: 4px scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;

  /* Type scale */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;

  /* Radius and elevation */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);
  --shadow-lg: 0 12px 32px rgba(15, 23, 42, 0.16);

  /* Layout */
  --sidebar-width: 248px;
  --sidebar-width-collapsed: 72px;
  --topbar-height: 64px;
  --content-max-width: 1440px;

  /* Layering. Dropdowns (1000) and modals (2000) keep their existing values,
     so a modal always covers the mobile drawer. */
  --z-filterbar: 80;
  --z-topbar: 90;
  --z-sidebar: 95;
  --z-drawer-backdrop: 1090;
  --z-drawer: 1100;

  --transition-base: 200ms ease;
}
```

## Hex to token mapping for the spacing and color pass

| Hex in the code | Token |
|---|---|
| `#f8fafc` | `--color-bg` |
| `#ffffff`, `white` (as a surface) | `--color-surface` |
| `#f1f5f9` | `--color-surface-muted` |
| `#e2e8f0` | `--color-border` |
| `#cbd5e1` | `--color-border-strong` |
| `#0f172a`, `#1e293b` (body text) | `--color-text` |
| `#334155`, `#475569` | `--color-text-secondary` |
| `#64748b` | `--color-text-muted` |
| `#94a3b8` | `--color-text-subtle` |
| `#2563eb`, `#3b82f6` (accent, links, focus) | `--color-primary` |
| `#eff6ff` | `--color-primary-soft` |
| `#d1fae5` / `#065f46` | `--color-success-soft` / `--color-success-text` |
| `#fed7aa` / `#92400e` | `--color-warning-soft` / `--color-warning-text` |
| `#fecaca` / `#991b1b` | `--color-danger-soft` / `--color-danger-text` |
| `#dbeafe` / `#1e40af` | `--color-info-soft` / `--color-info-text` |

Leave chart series colors, gradients (for example `#667eea`) and any color used inside SVG chart markup as they are.

## Spacing snapping

Snap to the nearest step: `0.313rem` to `--space-1`, `0.375rem`/`0.4rem` to `--space-2`, `0.625rem` to `--space-3`, `0.813rem` font sizes to `--font-size-sm`, `0.938rem` to `--font-size-sm` or `--font-size-base` depending on role, `1.375rem` to `--font-size-xl`. Cards use `--space-6` internal padding, grids use `--space-6` gaps, page header margin-bottom `--space-6`.
