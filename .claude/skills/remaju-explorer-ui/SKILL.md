---
name: remaju-explorer-ui
description: Build RemaJu's static auction explorer, accessible custom design system, filtering, lazy details and archive downloads.
---

# Explorer workflow

1. Read `AGENTS.md` and `docs/implementation-plan.md`, especially sections 5, 10 and 13. Inspect the actual frontend before assuming planned tooling exists.
2. Keep the app static: no backend, no live scraper calls, no secret keys in browser bundles.
3. Confirmed stack: Vite/TypeScript/React, selected Nyxhora UI components, Tailwind tokens, `@generouted/react-router` file routes and nuqs URL state with the matching React Router adapter. Do not substitute Preact/Base UI or copy Nyxhora's Next.js showcase app. Pin selected upstream files/dependencies and preserve license notices.
4. No Bootstrap or generic dashboard theme. Use a quiet civic-data aesthetic: warm canvas, navy hierarchy, restrained crimson accents, clear numerical typography and the existing logo.
5. Fetch only manifest/current summaries initially, details on demand and archives only after an explicit action. Enforce measured payload budgets.
6. Spanish-first labels, Lima dates, original currencies, honest unknown/stale/partial states, clear auction-wide price labeling and multi-property support.
7. Layout is top filters then content, with no sidebar/rail/drawer. Order results by source offer date descending, with missing dates last and deterministic ties; never substitute collection time. Use semantic controls, keyboard navigation, focus management and non-color-only statuses.
8. Do not render scraped HTML directly or promise generic JSF detail URLs are permanent auction links. Explain source navigation truthfully.
9. URL-owned filters must restore on initial load and Back/Forward, update without reload, batch dependent changes, reset cleanly and support copying a shareable link. Test routed direct loads, query roundtrips, date-only/null sort cases, mobile and accessibility.
10. Provide current JSON/CSV, labeled filtered exports and clearly distinguished latest-known/history downloads with schema, sizes and spreadsheet instructions. Plan public `/llms.txt` and `/data-access.md` linking manifests/schemas and explaining data retrieval without JavaScript; these differ from repository developer skills.

Use fixtures for development until an accepted dataset exists. Never accidentally replace production data with fixture data during a frontend-only deployment.
