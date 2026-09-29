# Publish the standalone Card Atlas

This repository owns its website. The `site/` directory is ready to commit and contains
the runnable Card Atlas, 48 selected English records and all 48 pictures. It has no
runtime dependency on a blog checkout, a local image archive, an API or a server.
Open `site/index.html` directly to browse it offline.

The prepared project URL is **https://type-null.github.io/PTCG-database/**.
These local changes do not deploy that address; publishing requires committing
and pushing them to this repository and enabling Pages below. GitHub Pages is
available for public repositories on GitHub Free.

## Enable GitHub Pages once

1. Commit `site/`, `.github/workflows/pages.yml`, the builder/exporter/checker, tests and
   documentation to this repository. Include `site/images/`; those files are
   deliberately tracked even though the much larger root image archive is not.
2. Push to `main`.
3. In **Settings → Pages → Build and deployment → Source**, select
   **GitHub Actions**.
4. Open **Actions → Publish Card Atlas → Run workflow**. Every later push to `main` builds and deploys automatically, including
   viewer, code, data and site changes. The `github-pages` environment can enforce
   the repository's normal deployment approval rules.
5. After that workflow succeeds, open the URL shown by its deployment step.

The workflow runs `python3 code/buildSite.py`, validates the result, and uploads
only `site/`. The builder renders the committed card edition with the latest
`docs/index.html`, so an interface/source change is visible after the next
successful deployment. It never scrapes data, downloads artwork, reads an
external archive or checks out another repository. A fresh checkout is enough.

The published **data edition stays explicit**: ordinary CI builds retain the
committed 48-card records, their printing links, selection date and local artwork.
Changes under `data_*` trigger a build but do not silently choose new cards or
claim that the sample now contains the full updated database. Choose a new data
edition using the separate export command below and commit that snapshot. The
report retains the data fingerprint/date and records the current viewer hash.

To preview a viewer/source edit locally without an archive:

```sh
python3 code/buildSite.py
python3 code/checkSite.py
```

The official [GitHub Pages workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
describes the Actions used here.

## Refresh the selected cards separately

From this repository:

```sh
python3 code/exportSite.py
python3 code/checkSite.py
```

The default output is `site/`, with 48 English cards. The exporter reads saved
JSON, selects familiar names, printing pairs, card and energy types, then sets,
and copies artwork already present in the local archive. It does not download
anything. The page and `site/export-report.json` state the included count,
source count, export date and exact image coverage. Inspect the resulting site,
then commit and push `site/` when you want to publish that new snapshot.

The initial committed snapshot has every picture. If refreshing on another
machine, first obtain the corresponding artwork archive or pass `--images`.
Missing pictures produce a record-based card face and an honest coverage count;
the exporter never substitutes a remote image. Keep the previous checked-in
snapshot if that reduced coverage is not what you want to publish.

```sh
# Use an archive at a different location
python3 code/exportSite.py --images /path/to/PTCG-card-images

# A focused set; use its exact saved set_name
python3 code/exportSite.py --set MEW --limit 48

# Several languages, with at most 48 cards per language
python3 code/exportSite.py --language en jp --limit 48

# Prepare an alternate version without replacing the published selection
python3 code/exportSite.py --output dist/alternate --language en --limit 24
```

Repeat `--set` for multiple sets; `--limit 0` includes every matching card.
Images use the source path's nested structure under the archive, such as
`en/<series>/<set>/<card>.jpg`. The default search locations are the ignored
root `images` link and the sibling `../PTCG-card-images` directory. These are
**refresh inputs only**; the published files contain copied local artwork and
work after those locations are removed.

Refresh replaces only its own unchanged output. File hashes in the report
protect manually edited files and extra authored files from being overwritten;
use a fresh `dist/` output when the checker reports a conflict. Edit
`docs/index.html`, then run `buildSite.py` for a viewer change; use
`exportSite.py` when deliberately refreshing the card edition.

## Link to the app from an article

Keep the app in this repository. An article in another repository needs only a
local screenshot or cover, a description, the project URL above and the source
link **https://github.com/type-null/PTCG-database**. An article can embed the independently hosted project URL and provide an
“Open in new tab” link to the same address. The article and its local preview
remain readable offline; a hosted iframe and outbound links need internet.
For card dialogs, the app optionally posts `{type: "type-null:focus-embed"}` to
its parent so the article can align the iframe. A parent should verify that
`event.source` is its actual rendered iframe before handling that notice.
No app folder needs to be copied into the blog, and publishing either repository
does not rebuild the other.

## Verify before publishing

```sh
python3 code/checkSite.py
python3 -m unittest discover -s tests -p 'test_export_site.py'
```

`checkSite.py` checks the manifest hashes, bundled records, artwork coverage and
relative asset paths without reading any archive or source card JSON. Optional
browser regressions require Playwright and Chromium in your test environment:

```sh
python3 -m unittest discover -s tests -p 'test_export_browser.py'
```

Those test the committed `site/` with real search, printing links, artwork,
relocation and narrow layouts. Set `PTCG_EXPORT_DIR` to inspect another export.
The full-data `docs/index.html` retains its ordinary index-loading behavior;
the published selection uses the same viewer with bundled data.
