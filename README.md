# Iken Psalter Fragments

A combined IIIF presentation of dispersed manuscript fragments from a Latin Psalter (circa 1290–1310), possibly written for the church of St. Botolph, Iken, in Suffolk, England. Fragments are held at three institutions — Yale University's Beinecke Rare Book and Manuscript Library, The Ohio State University's Rare Books and Manuscripts Library, and The Cleveland Museum of Art — and are here united into a single IIIF v3 manifest for viewing and research.

---

## About the Manuscript

The base manuscript is a Latin Psalter produced in England around 1290–1310, written on parchment. Its surviving leaves are now distributed across three collections:

### Yale University — Beinecke Rare Book and Manuscript Library
**Takamiya MS 136**

A bifolium (2 leaves, 267 × 180 mm) that once served as the flyleaf of the psalter. On its blank page a later hand added a full-page pen drawing — in brown ink — of **King Edmund the Martyr** holding an arrow, accompanied by four lines of verse in **Middle English** (15th century, dated 1400–1499). The original text on the bifolium is in Latin.

Purchased from Toshiyuki Takamiya on the Edwin J. Beinecke Book Fund, 2017.

- [Yale Digital Collections record](https://collections.library.yale.edu/catalog/16371296)
- [IIIF Manifest (Yale)](https://collections.library.yale.edu/manifests/16371296)

### The Ohio State University — Rare Books and Manuscripts Library
**SPEC.RARE.MS.MR.FRAG.60.1–9**

Eleven parchment bifolium fragments (22 canvases), catalogued as individual folios. Two fragments (3.1 and 7.10) were scanned at higher resolution (~7600 × 9800 px) and represent bifolia captured intact; the remainder were scanned as individual leaves (~3200 × 4700 px).

| Folio | Identifier | Canvases |
|-------|-----------|----------|
| 1 | SPEC.RARE.MS.MR.FRAG.60.1 | 2 |
| 2 | SPEC.RARE.MS.MR.FRAG.60.2 | 2 |
| 3 | SPEC.RARE.MS.MR.FRAG.60.3 | 2 |
| 3.1 | SPEC.RARE.MS.MR.FRAG.60.3.1 | 2 (bifolium scan) |
| 4 | SPEC.RARE.MS.MR.FRAG.60.4 | 2 |
| 5 | SPEC.RARE.MS.MR.FRAG.60.5 | 2 |
| 6 | SPEC.RARE.MS.MR.FRAG.60.6 | 2 |
| 7 | SPEC.RARE.MS.MR.FRAG.60.7 | 2 |
| 7.10 | SPEC.RARE.MS.MR.FRAG.60.7.10 | 2 (bifolium scan) |
| 8 | SPEC.RARE.MS.MR.FRAG.60.8 | 2 |
| 9 | SPEC.RARE.MS.MR.FRAG.60.9 | 2 |

- [OSU Digital Collections](https://library.osu.edu/dc)

### The Cleveland Museum of Art
**Acc. 1999.125 — Leaf from a Psalter: Historiated Initial D with The Trinity**

A single decorated leaf (26.7 × 17.5 cm), ink, tempera and gold on vellum, attributed to the **Master of the Queen Mary Psalter** (England, East Anglia, c. 1310). The leaf contains a large historiated initial D introducing Psalm 109 (*Dixit dominus domino*), within which the Trinity is depicted. Provenance traces directly to the parish church of St. Botulph at Iken in Suffolk, confirming the connection to the other fragments in this collection.

The Jeanne Miles Blackburn Collection.

- [Cleveland Museum of Art record](https://www.clevelandart.org/art/1999.125)
- [Internet Archive digitization](https://archive.org/details/clevelandart-1999.125-leaf-from-a-psalter)

---

## Repository Contents

```
IkenPsalter/
├── README.md
├── iken-psalter-fragments-manifest.json   # Combined IIIF v3 manifest
├── build_manifest.py                      # Script to regenerate the manifest
└── source-manifests/                      # Original IIIF manifests (optional)
    ├── yale-16371296.json                 # Yale v3 manifest
    ├── osu-1.json … osu-9.json           # OSU v2 manifests
    ├── osu-3_1.json
    ├── osu-7_10.json
    └── cma-1999.125.json                  # Cleveland Museum of Art v3 manifest
```

---

## The Combined Manifest

**`iken-psalter-fragments-manifest.json`** is a single IIIF Presentation API v3 manifest containing all 25 canvases in one sequence:

- Yale canvases (recto + verso) come first
- OSU folios follow in order: 1, 2, 3, 3.1, 4, 5, 6, 7, 7.10, 8, 9
- Cleveland Museum of Art leaf comes last

Canvas labels follow a consistent `institution-folio N, recto/verso` scheme:

```
yale-folio 1, recto
yale-folio 1, verso
osu-folio 1, recto
osu-folio 1, verso
...
osu-folio 9, verso
cma-folio 1, recto
```

The manifest is compatible with IIIF v3 viewers including [Mirador 3](https://projectmirador.org/) and [Universal Viewer](https://universalviewer.io/).

> **Note:** The manifest `id` field is currently set to a placeholder URL. If you host this file, update the `"id"` value at the top of the JSON (and the `MANIFEST_ID` constant in `build_manifest.py`) to match the file's actual served URL.

### View in Mirador

You can load the manifest directly into the hosted Mirador demo:

1. Go to [https://projectmirador.org/demo/](https://projectmirador.org/demo/)
2. Click **Add resource**
3. Paste the raw GitHub URL for the manifest:
   ```
   https://raw.githubusercontent.com/lauraw15/IkenPsalter/main/iken-psalter-fragments-manifest.json
   ```

---

## Regenerating the Manifest

If the source manifests change, the combined manifest can be rebuilt using the included Python script. No third-party dependencies are required — only the Python standard library.

```bash
# Place all source JSON files in the same directory as the script, then:
python3 build_manifest.py
```

The script will write a fresh `iken-psalter-fragments-manifest.json` to the current directory and print a canvas count summary.

---

## Rights

**Yale (Takamiya MS 136):** Use of images may be subject to US copyright law (Title 17) or site license terms. Users are liable for any infringement. See the [Yale Digital Collections record](https://collections.library.yale.edu/catalog/16371296) for full rights information.

**OSU (SPEC.RARE.MS.MR.FRAG.60.1–9):** Images are published under [No Copyright — United States (NoC-US)](http://rightsstatements.org/vocab/NoC-US/1.0/).

**CMA (acc. 1999.125):** Image published under [CC0 1.0 Public Domain Dedication](http://creativecommons.org/publicdomain/zero/1.0/).

---

## Citation

> *Drawing of King Edmund the Martyr* (Takamiya MS 136). General Collection, Beinecke Rare Book and Manuscript Library, Yale University.

> *Psalter fragments* (SPEC.RARE.MS.MR.FRAG.60.1–9). Rare Books and Manuscripts Library, The Ohio State University Libraries.

> *Leaf from a Psalter: Historiated Initial D with The Trinity* (acc. 1999.125). The Jeanne Miles Blackburn Collection, The Cleveland Museum of Art.

---

## Acknowledgements

This project was developed to support the study of dispersed medieval manuscript fragments by bringing together digitized leaves from Yale, OSU, and the Cleveland Museum of Art into a unified viewing experience via the IIIF framework.
