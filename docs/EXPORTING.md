# Build or refresh the standalone website

Run `python3 code/buildSite.py` to render the current viewer with the committed
card edition and artwork. This is the automatic Pages build on every main push;
it needs no external image archive or source-data refresh.

Run `python3 code/exportSite.py` separately to choose a new card/data edition in
`site/`. `python3 code/checkSite.py` verifies either result.

See [Publishing the Card Atlas](PUBLISHING.md) for complete commands, Pages setup,
image archive options and verification. An article can embed and link to the
independently hosted app without copying it into the blog.
