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

MANIFEST_ID = "https://raw.githubusercontent.com/lauraw15/IkenPsalter/main/iken-psalter-fragments-manifest.json"

YALE_FILE = "yale-16371296.json"
CLEVELAND_FILE = "cleveland.json"

# OSU source files in desired folio order
OSU_FILES = [
    ("1",    "osu-1.json"),
    ("2",    "osu-2.json"),
    ("3",    "osu-3.json"),
    ("3.1",  "osu-3.1.json"),
    ("4",    "osu-4.json"),
    ("5",    "osu-5.json"),
    ("6",    "osu-6.json"),
    ("7",    "osu-7.json"),
    ("7.10", "osu-7.10.json"),
    ("8",    "osu-8.json"),
    ("9",    "osu-9.json"),
]

OUTPUT_FILE = "iken-psalter-fragments-manifest.json"

SIDES = ["recto", "verso"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_service(svc):
    """Convert v2-style @id/@type service properties to v3 id/type."""
    if isinstance(svc, list):
        return [normalize_service(s) for s in svc]
    out = dict(svc)
    if "@id" in out:
        out["id"] = out.pop("@id")
    if "@type" in out:
        out["type"] = out.pop("@type")
    return out


def normalize_annotation_pages(pages):
    """Recursively normalize service properties in annotation pages."""
    result = []
    for page in pages:
        new_page = dict(page)
        new_items = []
        for anno in page.get("items", []):
            new_anno = dict(anno)
            body = dict(anno.get("body", {}))
            if "service" in body:
                body["service"] = normalize_service(body["service"])
            new_anno["body"] = body
            new_items.append(new_anno)
        new_page["items"] = new_items
        result.append(new_page)
    return result


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
            "id":     svc_id + "/full/full/0/default.jpg",
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

with open(CLEVELAND_FILE) as f:
    cleveland = json.load(f)

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
        "items":  normalize_annotation_pages(item["items"]),
    }
    if "thumbnail" in item:
        canvas["thumbnail"] = item["thumbnail"]
    yale_canvases.append(canvas)

# ── Cleveland canvases — already v3, pass through with normalised labels ─────

cleveland_canvases = []
for idx, item in enumerate(cleveland["items"]):
    canvas = {
        "id":     item["id"],
        "type":   "Canvas",
        "label":  {"none": [f"cleveland-folio {idx + 1}, recto"]},
        "width":  item["width"],
        "height": item["height"],
        "items":  item["items"],
    }
    if "thumbnail" in item:
        canvas["thumbnail"] = item["thumbnail"]
    cleveland_canvases.append(canvas)

# ── OSU canvases — v2 → v3, normalised labels ────────────────────────────────

osu_canvases = []
osu_folio_ids = {}  # folio label -> [canvas_id, ...]
for folio, manifest in osu_data:
    folio_canvas_ids = []
    for seq in manifest.get("sequences", []):
        for canvas_idx, canvas_v2 in enumerate(seq.get("canvases", [])):
            canvas = osu_canvas_to_v3(folio, canvas_v2, canvas_idx)
            osu_canvases.append(canvas)
            folio_canvas_ids.append(canvas["id"])
    osu_folio_ids[folio] = folio_canvas_ids

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

# ── Structures (ranges for viewer navigation) ─────────────────────────────────

RANGE_BASE = MANIFEST_ID + "/range"

def make_range(slug, label, items):
    return {
        "id":    f"{RANGE_BASE}/{slug}",
        "type":  "Range",
        "label": {"none": [label]},
        "items": items,
    }

leaf_ranges = []

# Yale — one bifolium
leaf_ranges.append(make_range(
    "yale-1",
    "Yale, folio 1 (Takamiya MS 136)",
    [{"id": c["id"], "type": "Canvas"} for c in yale_canvases],
))

# OSU — one range per folio, preserving order from OSU_FILES
for folio, _ in OSU_FILES:
    slug = "osu-" + folio.replace(".", "-")
    identifier = f"SPEC.RARE.MS.MR.FRAG.60.{folio}"
    leaf_ranges.append(make_range(
        slug,
        f"OSU, folio {folio} ({identifier})",
        [{"id": cid, "type": "Canvas"} for cid in osu_folio_ids[folio]],
    ))

# Cleveland — single leaf
leaf_ranges.append(make_range(
    "cleveland-1",
    "Cleveland, folio 1 (CMA 1999.125)",
    [{"id": c["id"], "type": "Canvas"} for c in cleveland_canvases],
))

# Top-level range referencing all leaf ranges
top_range = {
    "id":    f"{RANGE_BASE}/top",
    "type":  "Range",
    "label": {"en": ["Iken Psalter Fragments"]},
    "items": [{"id": r["id"], "type": "Range"} for r in leaf_ranges],
}

structures = [top_range] + leaf_ranges

# ── Assemble combined manifest ────────────────────────────────────────────────

combined = {
    "@context": "http://iiif.io/api/presentation/3/context.json",
    "id":   MANIFEST_ID,
    "type": "Manifest",
    "label": {"en": ["Iken Psalter Fragments"]},
    "summary": {"en": [
        "A combined presentation of Iken Psalter fragments held at three institutions: "
        "a drawing of King Edmund the Martyr with Middle English verse (Takamiya MS 136, "
        "Beinecke Library, Yale University), eleven parchment bifolium fragments "
        "(SPEC.RARE.MS.MR.FRAG.60.1–9, Rare Books and Manuscripts Library, "
        "The Ohio State University), and a leaf with historiated initial "
        "(1999.125, Cleveland Museum of Art). "
        "25 canvases total. Latin psalter, circa 1290–1310, possibly written for "
        "the church of St. Botolph in Essex."
    ]},
    "metadata": yale_meta + osu_meta_combined + cleveland.get("metadata", []),
    "requiredStatement": {
        "label": {"en": ["Provider"]},
        "value": {"en": [
            "Yale University Library (Takamiya MS 136); "
            "The Ohio State University Libraries, Rare Books and Manuscripts Library "
            "(SPEC.RARE.MS.MR.FRAG.60.1–9); "
            "Cleveland Museum of Art (1999.125)"
        ]},
    },
    "rights": "http://rightsstatements.org/vocab/NoC-US/1.0/",
    "provider": [
        {
            "id":   "https://github.com/lauraw15/IkenPsalter",
            "type": "Agent",
            "label": {"en": ["Yale University Library; The Ohio State University Libraries"]},
            "homepage": [
                {"id": "https://library.yale.edu/", "type": "Text",
                 "label": {"en": ["Yale Library"]}, "format": "text/html"},
                {"id": "https://library.osu.edu/", "type": "Text",
                 "label": {"en": ["OSU Libraries"]}, "format": "text/html"},
                {"id": "https://www.clevelandart.org/", "type": "Text",
                 "label": {"en": ["Cleveland Museum of Art"]}, "format": "text/html"},
            ],
        },
    ],
    "thumbnail": yale.get("thumbnail", []),
    "start": {"id": yale_canvases[0]["id"], "type": "Canvas"},
    "items": yale_canvases + osu_canvases + cleveland_canvases,
    "structures": structures,
}

# ── Write output ──────────────────────────────────────────────────────────────

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(combined, f, indent=2, ensure_ascii=False)

total = len(combined["items"])
print(f"Written: {OUTPUT_FILE}")
print(f"Total canvases: {total}  (Yale: {len(yale_canvases)}, OSU: {len(osu_canvases)}, Cleveland: {len(cleveland_canvases)})")
print("\nCanvas labels:")
for c in combined["items"]:
    print(f"  {list(c['label'].values())[0][0]}")
