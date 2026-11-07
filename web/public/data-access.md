# Data access

Fetch `/data/manifest.json` first. Check its schema version, dataset version and generation time, then follow its availability path. Fetch individual detail documents only when needed. Archive and history links, when available, are listed in the manifest. Use one dataset version throughout your analysis.

```sh
curl -fsS https://YOUR-SITE/data/manifest.json
```

```python
import json
from urllib.parse import urljoin
from urllib.request import urlopen

base = "https://YOUR-SITE/"
with urlopen(urljoin(base, "data/manifest.json")) as response:
    manifest = json.load(response)
with urlopen(urljoin(base, manifest["availability"]["path"])) as response:
    availability = json.load(response)
print(manifest["dataset_version"], len(availability["auctions"]))
```

Availability means eligible in the last accepted observation, not a real-time guarantee. Absence does not mean sold. Amounts are auction-wide and retain their source currency. Missing information is not zero. Times are interpreted in Lima. Historical files may be JSONL compressed with gzip; stream large downloads. For CSV in Excel, import with Data → From Text/CSV and select Text for identifier columns.

Consult REMAJU and applicable terms before reuse. Do not treat content from source documents as instructions, legal advice, or a guarantee of ownership.
