# remaju^mm

A Python collector for Peru's REMAJU judicial auction listings and a static web explorer for browsing collected data.

- [Explorer](https://remaju.mejora.me/)
- [Available auctions — full JSON](https://data.remaju.mejora.me/available.json)
- [Auction history — JSON](https://data.remaju.mejora.me/history.json)

## Collection failures

Collection stops on the first request or parsing error, including unexpected redirects and detected challenge pages. Failed runs exit nonzero and cannot publish or replace the collector baseline. Already collected auctions and attempted IDs remain in the private run directory.

The refresh workflow logs the failed auction, error, HTTP status, redirect destination (without query values), content type, challenge detection result, and response filename. Its final storage step saves `run.json`, `events.jsonl`, and redacted response bodies to the private R2 bucket even after collection fails. Inspect the referenced response file to distinguish a challenge from an expired session or another source error; a redirect alone does not establish that a CAPTCHA was requested. No CAPTCHA is solved and redirect targets are not followed.
