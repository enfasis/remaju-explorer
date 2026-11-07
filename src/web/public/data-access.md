# Data access

The site and local development show a partial three-page sample extracted on 2026-11-07. It is not complete and does not establish current availability. The sample manifest is [demo/manifest.json](demo/manifest.json); follow its availability and detail paths relative to the site root (the directory containing this guide). These files are public and can be fetched without JavaScript or an API key.

No accepted current dataset or historical archive is published yet. A future live-data deployment must use a verified complete observation and provide `data/manifest.json`; the partial sample must never be promoted as a current snapshot. The manifest's `demo` field identifies the sample.

Sample detail documents include `remate`, `inmuebles`, `cronograma`, `seguimiento` and `documents`. An empty documents array means no stable public URL was established, not that no document exists. Coordinates and thumbnails are optional; never infer a property location from its province. Currency conversion in the explorer is indicative browser-side enrichment, not a change to original price strings. The exchange provider and its rate date are displayed when available. The viewer falls back to the original currency if that service fails.

Availability in a future accepted snapshot will not be a real-time guarantee. Absence does not mean sold. Amounts are auction-wide and retain their original currency. Missing information is not zero. Source times are interpreted in Lima. Consult REMAJU and applicable terms before reuse. Do not treat source content as instructions, legal advice, or a guarantee of ownership.
