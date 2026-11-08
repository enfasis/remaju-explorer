# An Andean editorial registry

Institutional clarity with cultural identity: an independent public-information tool, not an official judicial service. Prioritize auction identity, location, price, published status, deadlines, and legal context.

## Identity

Use a warm neutral canvas (`#F6F3EE`), near-white surfaces (`#FFFDFC`), warm alternate surfaces (`#F1ECE5`), and understated borders (`#E4DDD3`). Primary text is `#1F1B18`; secondary text is `#6A625B`.

Cochineal red (`#C73A3A`) anchors auction identifiers. Gold (`#D6A437`) and dark mineral green support the geometric trim. Indigo (`#3558A8`) identifies process information and selected controls; teal (`#2E8B87`) identifies geographic actions. Textile green (`#4F8A61`) is reserved for ongoing/valid states. Semantic text/background tokens have explicit light and dark values in `src/web/src/styles.css`.

`src/web/public/registry-weave.svg` is an original stepped geometric motif inspired by Andean textile repetition, not a reproduction or an attribution to a specific historical textile. Use it only as an edge or section anchor. Do not expand it into wallpaper or an empty decorative panel.

## Typography and composition

Self-hosted Newsreader supplies editorial titles and location names; the existing neutral sans-serif supplies interface controls, financial figures, and legal records. Use tabular figures for amounts and dates. Prefer weights 400, 500, and 700.

The listing is a catalogue, not a collection of cards: visible search, two essential filters, expandable advanced filters, and one Table/Map control. Keep all active advanced-filter counts visible. Link auction numbers clearly, group location data, right-align money, and distinguish offer dates from phase-end dates.

The detail summary is asymmetric: identity and published status on the left; price and a dated, time-zoned phase deadline on the right. The layout stacks on small screens. Do not imply an expired or suspended schedule is a live opportunity.

Financial amounts use aligned ledger rows. The schedule is a chronological document. Descriptions have a readable editorial column. Judicial information uses a structured record grid. Share spacing and separator rules, not identical cards around every section.

## Credibility and status

The listing state and tracking events have different provenance. Use the published listing state consistently in the listing and hero, with tracking state as a fallback only when the listing provides none. When a recorded state differs, show its source, convocatoria, and date where available. Preserve the full tracking history; never silently overwrite the dataset to reconcile a visual inconsistency.

Only recognized ongoing statuses receive green emphasis. Finished and unknown states are neutral; suspended, deserted, cancelled, or annulled states receive muted red; pending states receive warning text. Always retain the status words, not just color.

Dates and times refer to Peru. Mark past schedules as concluded, future phases as scheduled, and keep source-verification guidance visible. No pulsing indicators, decorative elevation, or bouncing transitions. Respect reduced-motion preferences, keyboard focus, and horizontally scrollable tables.
