# lightshow data

`templates.json.gz` is the bundled lightshow set: one-bar vanilla lighting units (basic events, boosts, event box groups) and colour schemes, per environment. The service uses it when no learned set exists in `/data/lightshow.json`. Format: gzip, UTF-8 JSON, the shape written by `Templates.save`.

Origin: learned with `saber-tooth learn` from the lighting of 98 locally installed community maps (20 environments, 10330 units). Publishing it in a public repository needs a licensing check first; see [ADR 0012](../../../../docs/adr/0012-ship-a-learned-lightshow-set.md).

Regenerate from a levels directory (gzip mtime 0, so equal input gives equal bytes):

```text
task st:learn-bundle -- <levels_dir>
```
