# Contributing

## Adding a New Fragment

To add a fragment from a new institution:

### 1. Obtain the source IIIF manifest

Download the institution's IIIF manifest JSON and save it to `source-manifests/`. Use a clear filename, e.g. `institutionname.json` or `institutionname-accession.json`.

- If the manifest is **IIIF v3**, it can be passed through with minimal changes (like Yale and Cleveland).
- If the manifest is **IIIF v2**, it will need conversion (like the OSU manifests). The `osu_canvas_to_v3()` function in `build_manifest.py` is a reference for how to handle this.

### 2. Update `build_manifest.py`

In the Configuration section at the top of the script:

```python
NEW_FILE = "institutionname.json"
```

Then add a canvas-building block (after the existing institution blocks) following the same pattern as Yale or Cleveland for v3, or OSU for v2.

Update the following as appropriate:
- **`summary`** — update the institution count and canvas total
- **`metadata`** — add the new institution's metadata
- **`requiredStatement`** — add the institution name and identifier
- **`provider`** — add a homepage entry for the new institution
- **`items`** — append the new canvases to the list
- **`structures`** — add a new range for the institution and its folios

### 3. Rebuild and verify

```bash
cd source-manifests
python3 ../build_manifest.py
mv iken-psalter-fragments-manifest.json ../
```

Check that:
- The canvas count in the printed summary is correct
- All expected canvas labels appear in the output
- The manifest loads in a IIIF viewer (e.g. [Mirador](https://projectmirador.org/demo/))

### 4. Commit and tag

```bash
git add source-manifests/institutionname.json build_manifest.py iken-psalter-fragments-manifest.json
git commit -m "Add [Institution] fragment ([identifier])"
git push origin main
```

If this is a significant update (new institution, substantial new content), create a new version tag:

```bash
git tag -a v1.x -m "v1.x — Add [Institution] ([identifier])"
git push origin v1.x
```

## Source Manifest Files

| File | Institution | Format | Notes |
|------|-------------|--------|-------|
| `yale-16371296.json` | Yale, Beinecke Library | IIIF v3 | Takamiya MS 136 |
| `osu-1.json` – `osu-9.json` | Ohio State, RBML | IIIF v2 | SPEC.RARE.MS.MR.FRAG.60.1–9 |
| `osu-3.1.json` | Ohio State, RBML | IIIF v2 | SPEC.RARE.MS.MR.FRAG.60.3.1 |
| `osu-7.10.json` | Ohio State, RBML | IIIF v2 | SPEC.RARE.MS.MR.FRAG.60.7.10 |
| `cleveland.json` | Cleveland Museum of Art | IIIF v3 | Acc. 1999.125, via Internet Archive |
