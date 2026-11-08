# Data access

Production data is published at <https://data.remaju.mejora.me/> as four files:

- [manifest.json](https://data.remaju.mejora.me/manifest.json): dataset version, observation time, counts and SHA-256 hashes of the other files.
- [ids.txt](https://data.remaju.mejora.me/ids.txt): auction numbers, one per line, in the latest complete listing order.
- [available.json](https://data.remaju.mejora.me/available.json): complete auction records whose phase-3 closing date is still valid in Lima time. This file is updated daily and supplies both the site's listings and auction details. Missing/invalid phase-3 dates and cancelled/suspended auctions are excluded.
- [history.json](https://data.remaju.mejora.me/history.json): latest known content of every observed auction, merged by ID over time. Records retain first/last observation, last change, last detail fetch and presence in the latest complete listing. Missing auctions are kept; this is not a release index.

Full auction records have `numero_remate`, `list_data`, `detail` (including `remate_tab`, `inmuebles_tab` and `cronograma_tab`) and `seguimiento`. Properties, coordinates, amounts and schedules are embedded: there are no individual auction files. No CSV/Excel export is currently offered. The viewer derives its filter fields and currency display without modifying the original price strings.

Files are updated in place, with the manifest uploaded last. Check the manifest's SHA-256 hashes and the JSON dataset versions; if they differ, retry after refreshing the manifest. During migration, the old `data/manifest.json` may remain available, but new readers should use the root files above. Old release objects are retained until an owner-approved cleanup.

Daily collection runs at 03:00 Peru time, subject to GitHub scheduling delays. Full listing summaries are checked daily; unchanged auction details may be reused for up to seven days. The detail fetch time is reported as `detail_checked_at`. A valid phase-3 deadline is a display rule, not a real-time guarantee of availability. Absence does not mean sold.

Coordinates outside the Peru boundary are removed. Missing coordinates do not exclude an auction from the list. A point inside Peru does not guarantee parcel-level accuracy. Amounts retain their original currency. Missing information is not zero. Source times are interpreted in Lima. Consult REMAJU and applicable terms before reuse; this is not legal advice or a guarantee of ownership.

Local development uses the bundled sample at [demo/manifest.json](demo/manifest.json). Its legacy detail paths are fixture files, not the production storage layout.
