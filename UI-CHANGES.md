# WebPulse — UI Redesign (v3)

## Why it looked scrambled
1. **Two design systems fighting:** `base.html` had ~600 lines of inline dark-theme CSS, while `static/styles.css` was never linked — and that file was leftover Streamlit CSS (`[data-testid="stSidebar"]`, `.stButton`), with light-theme colours.
2. **Dark vs light clash:** the base defaulted to dark, but every page used light Bootstrap utilities (`bg-white` card headers, `table-light`, `bg-light` inputs, `bg-secondary-subtle` badges). Result: white blocks on a dark page, unreadable text.
3. **Inline styles everywhere:** `style="border-top: 3px solid …"`, `width:36px`, hard-coded hex on almost every card — no spacing, radius, or colour scale, so every page looked different.
4. **Duplicate headings:** the top bar title + a page H1 both said "Dashboard", wasting space and looking unfinished.

## What changed (UI only — no backend, routes, or logic touched)
- **One design system:** all CSS now lives in `static/styles.css` (Inter + JetBrains Mono). `base.html` is ~130 lines, just links it. Streamlit selectors deleted.
- **Light-first, clean SaaS look:** white cards, #f6f7f9 background, 1px #e5e7eb borders, 12px radius, subtle shadow. Indigo #4f46e5 primary. Sidebar is now light/white with an indigo active pill (was dark navy + dark body).
- **Dark mode that actually works:** every component reads CSS variables, so the moon/sun toggle now recolours cards, tables, forms, and charts correctly. Default is now light.
- **One page header per page:** title + one-line subtitle + actions on the right. Top bar is now just a breadcrumb (`WebPulse / Dashboard`) + theme + refresh.
- **Consistent components:** `.panel`, `.kpi-card`, `.status-pill`, `.wp-table`, `.metric` — same KPI cards on Dashboard/Analytics, same pills/tables everywhere, no more `bg-white`/`table-light`.
- **Websites page:** uniform cards, 2×2 metric tiles, pill filters, cleaner Add Website modal.
- **Incidents / Analytics / Settings / Edit:** same panel/table/form language; charts now use theme-aware grid/tick colours; Analytics KPIs reuse the dashboard KPI style instead of centred circles.
- **Small fix:** Settings said `python worker.py` — corrected to the real command `python -m workers.monitor_worker`.
- **Tests pass:** `pytest tests/test_webapp.py` — 7 passed. All pages render 200, CSS serves, no `bg-white`/`table-light` left in templates.

## Files changed
`static/styles.css` (rewritten), `templates/base.html`, `dashboard.html`, `websites.html`, `incidents.html`, `analytics.html`, `settings.html`, `website_edit.html`, `error.html`. Nothing else.

## Not included in this zip (on purpose)
`.env` and `webpulse.db` were in your original zip — they hold your DB password and local data, so I left them out. Copy your own `.env` back in before running. Run: `python webapp.py` → http://127.0.0.1:5000

## If you want a different look
Tell me and I can switch in minutes — e.g. dark as default, a dark sidebar, a different accent colour (teal/green instead of indigo), or a denser table view.

## Update — v3.1 (screenshots)
- Bootstrap, Bootstrap Icons, and Chart.js are now vendored in `static/vendor/` instead of loading from a CDN. The UI now works fully offline, and icons/buttons no longer break if the CDN is slow or blocked. Google Fonts (Inter) still loads from Google when online, with a system-font fallback when offline.
- `base.html` links the local vendor files; no other code changed.

## Update — v3.2 (dark theme default)
- Dark is now the default theme: `base.html` ships with `data-bs-theme="dark"` and the JS fallback is `'dark'`. The sun/moon toggle in the top bar still switches to light, and the choice is remembered in localStorage.
- No new files or backend changes for this: the dark palette already existed as CSS variables in `static/styles.css` (`--wp-bg #0b0f19`, `--wp-surface #111827`, etc.) — this update just makes dark the default and verifies it. All components (sidebar, top bar, KPI cards, tables, forms, modals, status pills, alerts, charts) already read those variables, so dark renders consistently.
- Verified in a headless browser: Dashboard, Websites, Incidents, Analytics, Settings all render cleanly in dark, with readable contrast and green/red/amber status colours standing out. Tests: 7 passed.
