# Navigation icons

Inline SVG, 24x24 viewBox rendered at 20x20, stroke-based so they inherit `currentColor`. Hand-drawn simple shapes in the style of common open stroke icon sets; no library dependency. Always add `aria-hidden="true"` and `focusable="false"`; the link text or `aria-label` carries the meaning.

Shared attributes for every icon:

```html
<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
     aria-hidden="true" focusable="false"> ...paths... </svg>
```

The cleanest approach is to store only the inner path markup per route in the `navGroups` data and render it with a tiny inline `NavIcon` pattern (`<svg ...><g v-html="item.icon" /></svg>`). `v-html` is safe here because the strings are static constants in the source, never user input; add a comment saying so.

| Route | Icon | Inner markup |
|---|---|---|
| `/` Overview | grid | `<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>` |
| `/inventory` | box | `<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>` |
| `/orders` | clipboard list | `<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1"/><path d="M9 10h6M9 14h6M9 18h4"/>` |
| `/restocking` | truck | `<path d="M3 6h11v10H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>` |
| `/demand` | trend line | `<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>` |
| `/spending` Finance | wallet | `<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><path d="M16 15h2"/>` |
| `/reports` | bar chart | `<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>` |

Utility icons:

| Use | Inner markup |
|---|---|
| Collapse (chevrons left) | `<path d="M11 17l-5-5 5-5M18 17l-5-5 5-5"/>` |
| Expand (chevrons right) | `<path d="M13 17l5-5-5-5M6 17l5-5-5-5"/>` |
| Menu (hamburger) | `<path d="M4 6h16M4 12h16M4 18h16"/>` |
| Close | `<path d="M6 6l12 12M18 6L6 18"/>` |

If a new route appears that has no icon here, pick a simple geometric stroke shape in the same style rather than leaving it blank.
