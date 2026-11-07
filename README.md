# remaju^mm

A Python collector for Peru's REMAJU judicial auction listings and a static web explorer for browsing collected data. The collector currently supports non-publishable sample runs; the site can display fixture data. Infrastructure configuration is in `infra/`.

Requires Docker Compose and Make:

```sh
make help       # list commands
make build      # build collector and web images
make test       # run offline tests and build the web app
make run        # serve the explorer at http://localhost:5173
make web-build  # build the static explorer
make sample     # contact REMAJU for a non-publishable sample
```

`make download` is an alias for `make sample`. Collection does not publish data. Existing data and caches are preserved by `make clean`.
