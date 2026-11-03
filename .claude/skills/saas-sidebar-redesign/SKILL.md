---
name: saas-sidebar-redesign
description: Redesign this inventory-management app's Vue 3 UI into a modern SaaS-style interface - replaces the horizontal top nav in client/src/App.vue with a grouped, collapsible left sidebar (icon rail on desktop, off-canvas drawer on mobile), introduces CSS design tokens for color, spacing, radius and shadow, and normalizes spacing across views and components. Use this skill whenever the user wants to restyle, modernize, polish or "make professional" this app's UI, move or rework the navigation (sidebar, side nav, left menu, nav getting crowded, too many tabs), fix inconsistent spacing or layout, add a mobile/responsive layout, or asks for a SaaS/dashboard look - even if they don't say "sidebar" explicitly.
---

# SaaS sidebar redesign for the inventory-management client

This skill turns the app shell from a top-nav layout into a sidebar layout and makes the visual system consistent. It is written for this repository only, so it names real files and values. Read the whole workflow before editing; the order matters because later steps depend on tokens introduced earlier.

## What exists today (verify quickly, it may have drifted)

- `client/src/App.vue` holds the whole shell: `header.top-nav` with logo, `nav.nav-tabs` router-links, `LanguageSwitcher`, `ProfileMenu`; then `FilterBar`, then `main.main-content > router-view`, then two modals. Its unscoped `<style>` block is the de-facto global stylesheet (`.card`, `.stats-grid`, `.stat-card`, `.badge.*`, `.page-header`, tables, `.loading`, `.error`).
- Colors are hard-coded hex everywhere. There are no CSS variables and no `@media` queries in the codebase.
- `client/src/components/FilterBar.vue` is `position: sticky; top: 70px` - that 70px is the old header height, so it breaks as soon as the header changes.
- z-index layers in use: filter bar 90, header 100, dropdowns (`ProfileMenu`, `LanguageSwitcher`) 1000, `TasksModal` 1000, other modals 2000.
- Routes (from `client/src/main.js`): `/` Overview, `/inventory`, `/orders`, `/spending` (label "Finance"), `/demand` (Demand Forecast), `/restocking`, `/reports`. The Reports link is hard-coded English with no `nav.reports` key. `views/Backlog.vue` exists but is not routed; leave it alone.
- Nav labels come from `t('nav.*')` in `client/src/locales/en.js` and `ja.js`. Every new visible string needs a key in both files.

Run `grep -n "router-link\|path:" client/src/App.vue client/src/main.js` first. If routes were added or renamed, use the current list, not the one above.

## Project rules that still apply

- `CLAUDE.md` requires `.vue` files to be created or substantially modified by the **vue-expert** subagent. In a main session, delegate the shell and component edits to vue-expert and pass it this skill's path so it follows the same plan. If you are already running as a subagent, make the edits yourself.
- No emojis in the UI. Icons are inline SVG (see `references/nav-icons.md`). Do not add an icon library or any new npm dependency.
- Keep the slate palette and blue accent. The goal is polish and consistency, not a rebrand.
- Unique `v-for` keys, no index keys. Comment non-obvious logic (breakpoints, z-index choices, the localStorage key).
- Do not change behavior: same routes, same filters, same API calls, same modals, same i18n. A redesign that breaks a page is a failed redesign.

## Target layout

```
+-----------+--------------------------------------------------+
|  Logo     |  Top bar: [menu btn on mobile]  Page title   Lang  Profile |
|           +--------------------------------------------------+
|  OVERVIEW |  Filter bar (sticky under top bar)                |
|  Overview |--------------------------------------------------|
|           |                                                  |
|  OPERATIONS  main content (router-view), padded, max-width   |
|  Inventory|                                                  |
|  Orders   |                                                  |
|  Restock. |                                                  |
|  Demand   |                                                  |
|           |                                                  |
|  FINANCE  |                                                  |
|  Finance  |                                                  |
|  Reports  |                                                  |
|           |                                                  |
| [<< collapse]                                                |
+-----------+--------------------------------------------------+
```

- **Sidebar**: fixed to the left, full height, dark slate (`--color-sidebar-bg: #0f172a`) with light text. A dark sidebar against the light `#f8fafc` content is the clearest SaaS cue and keeps the existing palette. Width 248px expanded, 72px collapsed.
- **Groups**: Overview (`/`), Operations (`/inventory`, `/orders`, `/restocking`, `/demand`), Finance (`/spending`, `/reports`). Group labels are small uppercase muted text and are hidden in the collapsed rail. Define the groups as a data array in `App.vue` and render with `v-for` keyed by `path`, so adding a route later is a one-line change.
- **Active state**: use `router-link`'s built-in `active-class`/`exact-active-class` instead of the current manual `$route.path ===` checks. Overview must use exact matching or it will be active on every page. Active item gets a tinted background and a 3px accent bar on the left edge.
- **Collapse toggle** at the bottom of the sidebar. Persist the state in `localStorage` under `sidebar-collapsed`, wrapped in try/catch because storage can throw in private mode. In the collapsed rail, show only icons and expose the label through `title` and `aria-label` so it stays usable.
- **Top bar** inside the content column, sticky, height `--topbar-height` (64px): mobile menu button (hidden on desktop), current page title, then `LanguageSwitcher` and `ProfileMenu` pushed right. Keeping the two dropdown components in the top bar rather than the sidebar means their existing absolute positioning keeps working unchanged.
- **Filter bar**: sticky directly under the top bar using `top: var(--topbar-height)` instead of 70px. Remove its own `max-width: 1600px; margin: 0 auto` centering so it aligns with the content column. Let `.filters-grid` wrap (`flex-wrap: wrap`) so it survives narrow widths.
- **Main content**: `padding: var(--space-8)` on desktop, `var(--space-4)` on mobile, inner `max-width: 1440px`. Drop the old `margin: 0 auto` centering on the shell itself; the content column is offset by the sidebar width via `margin-left`.
- **Mobile (<= 1024px)**: sidebar becomes an off-canvas drawer (`transform: translateX(-100%)`), always shown expanded, opened by the top-bar menu button, closed by a backdrop click, the Escape key, or any route change (watch `$route`). Lock body scroll while open. The collapse toggle is hidden on mobile.
- **Layering** (put these as tokens and comment why): filter bar 80, top bar 90, sidebar 95, drawer backdrop 1090, mobile drawer 1100. Dropdowns stay at 1000 and modals at 2000, so a modal always covers the drawer and a dropdown never hides under the top bar.
- Animate width/transform with `transition: 200ms ease`, and disable transitions under `@media (prefers-reduced-motion: reduce)`.

## Workflow

### 1. Tokens first

Add a `:root` block at the top of the `App.vue` global style using the values in `references/design-tokens.md`. Then convert the App.vue global classes (`.card`, `.stat-card`, `.badge.*`, `.page-header`, tables, `.loading`, `.error`) to use the tokens. This is the foundation: once global classes use tokens, every view that relies on them picks up the new look for free.

Spacing follows a 4px scale (`--space-1` 0.25rem through `--space-12` 3rem). Snap existing paddings, margins and gaps to the nearest step. Odd values like `0.313rem`, `0.813rem`, `1.375rem` are the main source of the "slightly off" feel, so replace them.

### 2. Rebuild the shell in App.vue

Replace the `header.top-nav` markup and its CSS with the sidebar + content column described above. Keep `FilterBar`, `router-view`, both modals and all existing script logic (tasks, profile modals) intact; only add what the layout needs (`navGroups` array, `sidebarCollapsed`, `mobileNavOpen`, the localStorage read/write, the route watcher, an Escape key listener added on mount and removed on unmount, and a computed page title from the current route's nav item).

Icons: copy the SVG markup from `references/nav-icons.md`. Use `stroke="currentColor"` so they inherit the link color, 20x20, `aria-hidden="true"`.

i18n: add to both `en.js` and `ja.js`:
`nav.reports`, `nav.groups.overview`, `nav.groups.operations`, `nav.groups.finance`, `nav.collapse`, `nav.expand`, `nav.openMenu`, `nav.closeMenu`. Replace the hard-coded "Reports" with `t('nav.reports')`.

### 3. FilterBar

Change the sticky offset to the token, remove its own centering, let the grid wrap, and tokenize its colors and spacing. Do not touch its filter logic or option values.

### 4. Spacing and color pass over views and components

Go through `client/src/views/*.vue` and `client/src/components/*.vue` scoped styles and:
- replace the slate/blue hex values that have a token equivalent with `var(--...)` (the mapping table is in `references/design-tokens.md`);
- snap padding/margin/gap to the spacing scale;
- align card radius and shadows to `--radius-lg` / `--shadow-sm`.

Leave semantic chart colors, SVG chart fills and one-off status tints alone unless they map exactly to a token. The point is consistency in chrome and spacing, not repainting charts. `Dashboard.vue` (about 1270 lines) and `Spending.vue` are the largest; work through them section by section rather than rewriting them.

Modals keep their overlay structure and z-index 2000; only tokenize their colors, radius and spacing.

### 5. Verify

All of these, and report results honestly:

1. `cd client && npx vite build` succeeds with no new warnings.
2. With the app running (`./scripts/start.sh`, or the `start` skill; frontend on 3000, API on 8001), use Playwright MCP to check:
   - 1440px wide: sidebar expanded, groups visible, active item highlighted on each of the seven routes, Overview not highlighted on other routes.
   - Collapse toggle: rail is 72px, labels hidden, tooltips present; reload keeps the collapsed state.
   - 390px wide: sidebar hidden, menu button opens the drawer, backdrop click and route change close it, no horizontal page scroll (`document.documentElement.scrollWidth <= window.innerWidth`).
   - Filter bar sticks under the top bar when scrolling a long page (Orders), and changing a filter still reloads data.
   - Open a detail modal (Inventory row) and the profile dropdown; both appear above the sidebar and top bar.
   - Switch to Japanese: all sidebar labels and group names translate.
   - Console shows no new errors (the existing `/api/tasks` 404 is pre-existing and unrelated).
3. Take screenshots of desktop expanded, desktop collapsed and mobile drawer open, and save them where the user asked (default: the scratchpad).

## What to report back

A short summary of the new layout, a list of files changed, the verification results from step 5 (including anything that failed or was skipped), and the screenshot paths. Mention any view whose spacing you left untouched and why.
