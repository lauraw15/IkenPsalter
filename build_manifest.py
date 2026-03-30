"""
build_manifest.py
-----------------
Combines Yale (IIIF v3) and OSU (IIIF v2) Psalter fragment manifests
into a single IIIF v3 compliant manifest.

Canvas label scheme
-------------------
Yale:  yale-folio 1, recto / yale-folio 1, verso
       Yale has one folio (bifolium); side is inferred from position (0=recto, 1=verso).

OSU:   osu-folio N, recto / osu-folio N, verso
       Side is inferred from position within the folio sequence (0=recto, 1=verso).

Usage:
    python3 build_manifest.py

    Source JSON files must be in the same directory as this script.

Output:
    iken-psalter-fragments-manifest.json

Notes:
    Update MANIFEST_ID before hosting the output file.
"""

import json
import re

# ── Configuration ─────────────────────────────────────────────────────────────

MANIFEST_ID = "https://example.org/iken-psalter-fragments/manifest"  # ← update before hosting

YALE_FILE = "yale-16371296.json"

CMA_FILE  = "cma-1999.125.json"  # Cleveland Museum of Art — single leaf, already IIIF v3

# OSU source files in desired folio order
OSU_FILES = [
    ("1",    "osu-1.json"),
    ("2",    "osu-2.json"),
    ("3",    "osu-3.json"),
    ("3.1",  "osu-3_1.json"),
    ("4",    "osu-4.json"),
    ("5",    "osu-5.json"),
    ("6",    "osu-6.json"),
    ("7",    "osu-7.json"),
    ("7.10", "osu-7_10.json"),
    ("8",    "osu-8.json"),
    ("9",    "osu-9.json"),
]

OUTPUT_FILE = "iken-psalter-fragments-manifest.json"

SIDES = ["recto", "verso"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_image_service(service_id):
    """Return a IIIF v3-shaped ImageService2 block."""
    return [{
        "id":      service_id,
        "type":    "ImageService2",
        "profile": "http://iiif.io/api/image/2/level2.json",
    }]


def osu_canvas_to_v3(folio, canvas_v2, canvas_idx):
    """
    Convert a single OSU IIIF v2 canvas to IIIF v3.

    Label format: osu-<fileset-id> · folio N, recto|verso
    canvas_idx: 0-based position within the folio (0=recto, 1=verso)
    """
    canvas_id = canvas_v2["@id"]
    side = SIDES[canvas_idx]
    label_str = f"osu-folio {folio}, {side}"

    anno_list = []
    for img in canvas_v2.get("images", []):
        res = img["resource"]
        svc = res.get("service", {})
        svc_id = svc.get("@id", "")
        body = {
            "id":     res["@id"] + "/full/full/0/default.jpg",
            "type":   "Image",
            "format": res.get("format", "image/jpeg"),
            "width":  res.get("width", canvas_v2["width"]),
            "height": res.get("height", canvas_v2["height"]),
        }
        if svc_id:
            body["service"] = make_image_service(svc_id)
        anno_list.append({
            "id":         img["@id"],
            "type":       "Annotation",
            "motivation": "painting",
            "target":     canvas_id,
            "body":       body,
        })

    return {
        "id":     canvas_id,
        "type":   "Canvas",
        "label":  {"none": [label_str]},
        "width":  canvas_v2["width"],
        "height": canvas_v2["height"],
        "items": [{
            "id":    canvas_id + "/page",
            "type":  "AnnotationPage",
            "items": anno_list,
        }],
    }


def osu_metadata_to_v3(meta_list):
    """Convert OSU v2 metadata array to IIIF v3 metadata format."""
    out = []
    for entry in meta_list:
        label = entry.get("label", "")
        value = entry.get("value", "")
        if isinstance(value, list):
            vals = value
        elif isinstance(value, str):
            vals = [re.sub(r"<[^>]+>", "", value).strip()]
        else:
            vals = [str(value)]
        vals = [v for v in vals if v]
        if vals:
            out.append({"label": {"en": [label]}, "value": {"none": vals}})
    return out

# ── Load sources ──────────────────────────────────────────────────────────────

with open(YALE_FILE) as f:
    yale = json.load(f)

with open(CMA_FILE) as f:
    cma = json.load(f)

osu_data = []
for folio, path in OSU_FILES:
    with open(path) as f:
        osu_data.append((folio, json.load(f)))

# ── Yale canvases — already v3, pass through with normalised labels ───────────

yale_canvases = []
for idx, item in enumerate(yale["items"]):
    side = SIDES[idx]  # Yale has one bifolium: index 0=recto, 1=verso
    label_str = f"yale-folio 1, {side}"

    canvas = {
        "id":     item["id"],
        "type":   "Canvas",
        "label":  {"none": [label_str]},
        "width":  item["width"],
        "height": item["height"],
        "items":  item["items"],
    }
    if "thumbnail" in item:
        canvas["thumbnail"] = item["thumbnail"]
    yale_canvases.append(canvas)

# ── OSU canvases — v2 → v3, normalised labels ────────────────────────────────

osu_canvases = []
for folio, manifest in osu_data:
    for seq in manifest.get("sequences", []):
        for canvas_idx, canvas_v2 in enumerate(seq.get("canvases", [])):
            osu_canvases.append(osu_canvas_to_v3(folio, canvas_v2, canvas_idx))

# ── CMA canvas — already v3, pass through with normalised label ───────────────
# Single-sided leaf: labelled cma-folio 1, recto

cma_canvas_src = cma["items"][0]
cma_canvases = [{
    "id":     cma_canvas_src["id"],
    "type":   "Canvas",
    "label":  {"none": ["cma-folio 1, recto"]},
    "width":  cma_canvas_src["width"],
    "height": cma_canvas_src["height"],
    "items":  cma_canvas_src["items"],
}]

# ── Metadata ──────────────────────────────────────────────────────────────────

yale_meta = yale.get("metadata", [])

# OSU folios share the same collection metadata; de-duplicate across files
osu_meta_combined = []
seen = set()
for folio, manifest in osu_data:
    for entry in osu_metadata_to_v3(manifest.get("metadata", [])):
        label_key = list(entry["label"].values())[0][0]
        val_key   = str(list(entry["value"].values())[0])
        key = (label_key, val_key)
        if key not in seen:
            seen.add(key)
            osu_meta_combined.append(entry)

# CMA metadata — de-duplicate against yale + osu keys
cma_meta_combined = []
for entry in cma.get("metadata", []):
    label_key = list(entry["label"].values())[0][0]
    val_key   = str(list(entry["value"].values())[0])
    key = (label_key, val_key)
    if key not in seen:
        seen.add(key)
        cma_meta_combined.append(entry)

# ── seeAlso / homepage links on canvases ─────────────────────────────────────

# Yale — both canvases share the same record
yale_see_also = [{
    "id":      "https://collections.library.yale.edu/catalog/oai?verb=GetRecord&metadataPrefix=oai_mods&identifier=oai:collections.library.yale.edu:16371296",
    "type":    "Dataset",
    "format":  "application/mods+xml",
    "profile": "http://www.loc.gov/mods/v3",
    "label":   {"en": ["MODS metadata record (Yale)"]},
}]
yale_homepage = [{
    "id":     "https://collections.library.yale.edu/catalog/16371296",
    "type":   "Text",
    "format": "text/html",
    "label":  {"en": ["Yale Digital Collections record"]},
}]
for canvas in yale_canvases:
    canvas["seeAlso"]  = yale_see_also
    canvas["homepage"] = yale_homepage

# OSU — unique permanent link and source manifest per folio
osu_folio_links = [
    ("1",    "wm1181815", "731b4b11-93a9-4711-9239-d2ac91a50b6d"),
    ("2",    "1c18dt69z", "97b83279-4db4-4574-8a6f-6718c2431a8a"),
    ("3",    "mk61rv69f", "d9df8395-c575-463a-97d0-82cb55fd9919"),
    ("3.1",  "d504rz60b", "5307b371-49c2-44ad-a8cb-24a841535e8b"),
    ("4",    "2z10x3125", "33e2f13b-934c-4b23-b792-69bc2234204b"),
    ("5",    "rb68xq45h", "d4ce2422-766e-4d49-9785-f43fce1051a3"),
    ("6",    "np193p133", "fa05bd08-7201-4ddd-aa01-7a2eea18187a"),
    ("7",    "m039kh79c", "6e91d9ef-9be2-434b-ade1-0af3c0b8c1b4"),
    ("7.10", "44558s88w", "0a0db418-50e1-4128-8ba1-49a523a16e12"),
    ("8",    "t148fw28q", "dba989ac-622a-4f5d-8182-8f1d98e12d52"),
    ("9",    "m900p677j", "70e5a37e-6cdf-41bf-9186-e294b77b0200"),
]

osu_canvas_iter = iter(osu_canvases)
for (folio, work_id, hdl_uuid), (_, manifest) in zip(osu_folio_links, osu_data):
    ident        = f"SPEC.RARE.MS.MR.FRAG.60.{folio}"
    manifest_url = f"https://library.osu.edu/dc/dc/concern/generic_works/{work_id}/manifest"
    hdl_url      = f"https://hdl.handle.net/1811/{hdl_uuid}"
    see_also = [{
        "id":     manifest_url,
        "type":   "Dataset",
        "format": "application/ld+json",
        "profile":"http://iiif.io/api/presentation/2/context.json",
        "label":  {"en": [f"IIIF manifest (OSU, {ident})"]},
    }]
    homepage = [{
        "id":     hdl_url,
        "type":   "Text",
        "format": "text/html",
        "label":  {"en": [f"OSU Libraries permanent link ({ident})"]},
    }]
    # apply to both canvases in this folio (recto + verso)
    for _ in range(2):
        canvas = next(osu_canvas_iter)
        canvas["seeAlso"]  = see_also
        canvas["homepage"] = homepage

# CMA — single canvas
cma_canvases[0]["seeAlso"] = [{
    "id":     "https://archive.org/metadata/clevelandart-1999.125-leaf-from-a-psalter",
    "type":   "Dataset",
    "format": "application/json",
    "label":  {"en": ["Internet Archive item metadata (CMA acc. 1999.125)"]},
}]
cma_canvases[0]["homepage"] = [
    {
        "id":     "https://www.clevelandart.org/art/1999.125",
        "type":   "Text",
        "format": "text/html",
        "label":  {"en": ["Cleveland Museum of Art collection record"]},
    },
    {
        "id":     "https://archive.org/details/clevelandart-1999.125-leaf-from-a-psalter",
        "type":   "Text",
        "format": "text/html",
        "label":  {"en": ["Internet Archive digitization page"]},
    },
]



combined = {
    "@context": "http://iiif.io/api/presentation/3/context.json",
    "id":   MANIFEST_ID,
    "type": "Manifest",
    "label": {"en": ["Iken Psalter Fragments"]},
    "summary": {"en": [
        "A combined presentation of Iken Psalter fragments held at three institutions: "
        "a drawing of King Edmund the Martyr with Middle English verse (Takamiya MS 136, "
        "Beinecke Library, Yale University); eleven parchment bifolium fragments "
        "(SPEC.RARE.MS.MR.FRAG.60.1–9, Rare Books and Manuscripts Library, "
        "The Ohio State University); and a single decorated leaf with a historiated initial "
        "attributed to the Master of the Queen Mary Psalter (acc. 1999.125, "
        "The Cleveland Museum of Art). "
        "25 canvases total. Latin psalter, circa 1290–1310, East Anglia, England, "
        "possibly written for the church of St. Botolph at Iken in Suffolk."
    ]},
    "metadata": yale_meta + osu_meta_combined + cma_meta_combined,
    "requiredStatement": {
        "label": {"en": ["Provider"]},
        "value": {"en": [
            "Yale University Library (Takamiya MS 136); "
            "The Ohio State University Libraries, Rare Books and Manuscripts Library "
            "(SPEC.RARE.MS.MR.FRAG.60.1–9); "
            "The Cleveland Museum of Art (acc. 1999.125, The Jeanne Miles Blackburn Collection)"
        ]},
    },
    "rights": "http://creativecommons.org/publicdomain/zero/1.0/",
    "provider": [
        {
            "id":   "https://github.com/lauraw15/IkenPsalter",
            "type": "Agent",
            "label": {"en": ["Yale University Library; The Ohio State University Libraries; The Cleveland Museum of Art"]},
            "homepage": [
                {"id": "https://library.yale.edu/",     "type": "Text",
                 "label": {"en": ["Yale Library"]},     "format": "text/html"},
                {"id": "https://library.osu.edu/",      "type": "Text",
                 "label": {"en": ["OSU Libraries"]},    "format": "text/html"},
                {"id": "https://www.clevelandart.org/", "type": "Text",
                 "label": {"en": ["Cleveland Museum of Art"]}, "format": "text/html"},
            ],
        },
    ],
    "thumbnail": yale.get("thumbnail", []),
    "start": {"id": yale_canvases[0]["id"], "type": "Canvas"},
    "items": yale_canvases + osu_canvases + cma_canvases,
    "structures": [],  # populated below
}

# ── Build structures (table of contents) ─────────────────────────────────────

def range_id(slug):
    return f"{MANIFEST_ID}#range-{slug}"

def canvas_ref(canvas):
    return {"id": canvas["id"], "type": "Canvas"}

def collect_ranges(r):
    """Recursively flatten all nested ranges into a list for structures[]."""
    result = [r]
    for item in r.get("items", []):
        if item.get("type") == "Range":
            result.extend(collect_ranges(item))
    return result

all_canvases = combined["items"]

yale_range = {
    "id":    range_id("yale"),
    "type":  "Range",
    "label": {"en": ["Yale University, Beinecke Library"]},
    "items": [{
        "id":    range_id("yale-folio-1"),
        "type":  "Range",
        "label": {"en": ["Folio 1 (Takamiya MS 136)"]},
        "items": [canvas_ref(all_canvases[0]), canvas_ref(all_canvases[1])],
    }],
}

osu_folio_defs = [
    ("1",    [2,  3]),
    ("2",    [4,  5]),
    ("3",    [6,  7]),
    ("3.1",  [8,  9]),
    ("4",    [10, 11]),
    ("5",    [12, 13]),
    ("6",    [14, 15]),
    ("7",    [16, 17]),
    ("7.10", [18, 19]),
    ("8",    [20, 21]),
    ("9",    [22, 23]),
]

osu_range = {
    "id":    range_id("osu"),
    "type":  "Range",
    "label": {"en": ["The Ohio State University, Rare Books and Manuscripts Library"]},
    "items": [
        {
            "id":    range_id(f"osu-folio-{folio.replace('.', '-')}"),
            "type":  "Range",
            "label": {"en": [f"Folio {folio} (SPEC.RARE.MS.MR.FRAG.60.{folio})"]},
            "items": [canvas_ref(all_canvases[i]) for i in idxs],
        }
        for folio, idxs in osu_folio_defs
    ],
}

cma_range = {
    "id":    range_id("cma"),
    "type":  "Range",
    "label": {"en": ["The Cleveland Museum of Art"]},
    "items": [{
        "id":    range_id("cma-folio-1"),
        "type":  "Range",
        "label": {"en": ["Leaf from a Psalter: Historiated Initial D with The Trinity (acc. 1999.125)"]},
        "items": [canvas_ref(all_canvases[24])],
    }],
}

top_range = {
    "id":          range_id("top"),
    "type":        "Range",
    "label":       {"en": ["Iken Psalter Fragments"]},
    "viewingHint": "top",
    "items":       [yale_range, osu_range, cma_range],
}

combined["structures"] = collect_ranges(top_range)

# ── Write output ──────────────────────────────────────────────────────────────

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(combined, f, indent=2, ensure_ascii=False)

total = len(combined["items"])
print(f"Written: {OUTPUT_FILE}")
print(f"Total canvases: {total}  (Yale: {len(yale_canvases)}, OSU: {len(osu_canvases)}, CMA: {len(cma_canvases)})")
print("\nCanvas labels:")
for c in combined["items"]:
    print(f"  {list(c['label'].values())[0][0]}")
