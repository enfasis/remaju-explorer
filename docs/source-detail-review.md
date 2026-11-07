# Detail coverage review

The existing `download.py` is still the legacy scraper; the new collector is a sample adapter, not a completed refactor. Do not confuse a successful sample run with full collector parity.

## Saved three-page sample

The 2026-11-07 run contains 12 unique auctions with Remate, Inmuebles, Cronograma and seguimiento. The static sample now includes the saved description, case and financial terms, property addresses, registry references, encumbrances, percentages, area, schedule and tracking. Source-provided personal names and meaningless parsed `archivo: Inicio` values are omitted. The schedule is displayed as extracted, in Lima civil time, without deriving the current phase from the last schedule row.

No property in this run has coordinates: geocoding was explicitly disabled. Its absence is not evidence that geocoding is broken. Do not substitute city centers for property locations or call paid services without approval. The optional map shows only verified coordinates when supplied; unmatched records remain in the list. Browser location is requested only by pressing the location button and is not persisted or sent to our server. Map tiles go to OpenStreetMap and must comply with its tile policy; the exchange lookup goes to ExchangeRate-API. Both expose the visitor's IP to their respective providers. Conversion is indicative, uses the provider's actual date and falls back to original money on failure. Authoritative source money is retained as strings; converted comparison uses integer decimal arithmetic.

## Files and images

In `test_data/detail_base.html`, `resolucion.pdf` has `href="#"` and an `onclick` JSF form submission. It is not a stable public URL. Similarly, the generic detail page URL does not select an auction. Documents therefore link users to the source search with the auction number until session-independent URLs are proven. No documents are mirrored or downloaded.

List fixtures contain inline base64 JPEGs. This makes local thumbnail generation possible without hotlinking or storing private tokens, but the prior run did not retain the original list bodies/images. One property (25940) reports an image count of one; the count itself is not a URL. `source_media.thumbnail_from_card` decodes a bounded inline JPEG/PNG and writes a reduced WebP; it must be called only with an auction-matched card known to contain a real image, not the source placeholder. A subsequent approved capture can connect that helper to the full collector. The current sample does not misrepresent an unrelated fixture image as that property.

## Remaining collection work

Fix and characterize field mapping for district and phase; preserve correlated source captures; discover actual image and file controls per auction; verify any permitted public links in a new session; retain thumbnail provenance and privacy/reuse review. Reusing saved JSF ViewState or row indices as public links is invalid. Production completeness validation, all-phase coverage and durable cloud publication remain incomplete.
