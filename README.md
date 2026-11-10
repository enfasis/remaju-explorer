# remaju^mm

A Python collector for Peru's REMAJU judicial auction listings and a static web explorer for browsing collected data.

- [Explorer](https://remaju.mejora.me/)
- [Available auctions — full JSON](https://data.remaju.mejora.me/available.json)
- [Auction history — JSON](https://data.remaju.mejora.me/history.json)

## Collection failures

Collection stops on the first request or parsing error, including unexpected redirects and detected challenge pages. Failed runs exit nonzero and cannot publish or replace the collector baseline. Already collected auctions and attempted IDs remain in the run directory and its trace artifact.

Requests are sequential with a 1–2-second pause between them. Returning from details or tracking reloads the listing, restores its page position and size, and selects the auction by number using its refreshed controls and JSF ViewState. Navigation responses must redirect to the expected page; a source error redirect stops collection immediately rather than requesting another page and masking the original failure.

The refresh workflow logs the failed auction, error, HTTP status, redirect destination (without query values), content type, challenge detection result, and response filename. Its last step uploads `run.json`, `events.jsonl`, and redacted response bodies as the public workflow artifact `trace-<run id>` (kept 30 days) even after collection fails; download it with `make trace` or `gh run download <actions run id> -p 'trace-*'`. Geocoding, exchange-rate and collector caches are kept in the GitHub Actions cache, not in R2. Inspect the referenced response file to distinguish a challenge from an expired session or another source error; a redirect alone does not establish that a CAPTCHA was requested. No CAPTCHA is solved and redirect targets are not followed.
