"""
build_manifest.py
-----------------
Combines Yale (IIIF v3) and OSU (IIIF v2) Psalter fragment manifests
into a single IIIF v3 compliant manifest.

Usage:
    python3 build_manifest.py

Output:
    iken-psalter-fragments-manifest.json

Notes:
    - Edit MANIFEST_ID below before hosting the output file.
    - Yale manifest leads, followed by OSU folios in order.
    - OSU sub-variants (3.1, 7.10) follow their parent folio.
"""

import json
import re

# ── Configuration ─────────────────────────────────────────────────────────────

MANIFEST_ID = "https://example.org/iken-psalter-fragments/manifest"  # ← update before hosting

YALE_FILE = "yale-16371296.json"

# OSU files in desired folio order (folio label, filename)
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

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_image_service(service_id):
    """Return a IIIF v3-shaped ImageService2 block."""
    return [{
        "id":      service_id,
        "type":    "ImageService2",
        "profile": "http://iiif.io/api/image/2/level2.json",
    }]


def osu_canvas_to_v3(folio, canvas_v2):
    """Convert a single OSU IIIF v2 canvas dict to a IIIF v3 canvas dict."""
    canvas_id = canvas_v2["@id"]
    label_str = canvas_v2.get("label", f"Folio {folio}")

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

osu_data = []
for folio, path in OSU_FILES:
    with open(path) as f:
        osu_data.append((folio, json.load(f)))

# ── Build Yale canvases (already v3, pass through) ───────────────────────────

yale_canvases = []
for item in yale["items"]:
    canvas = {
        "id":     item["id"],
        "type":   "Canvas",
        "label":  item.get("label", {"none": ["Yale canvas"]}),
        "width":  item["width"],
        "height": item["height"],
        "items":  item["items"],
    }
    if "thumbnail" in item:
        canvas["thumbnail"] = item["thumbnail"]
    yale_canvases.append(canvas)

# ── Build OSU canvases (v2 → v3) ─────────────────────────────────────────────

osu_canvases = []
for folio, manifest in osu_data:
    for seq in manifest.get("sequences", []):
        for canvas_v2 in seq.get("canvases", []):
            osu_canvases.append(osu_canvas_to_v3(folio, canvas_v2))

# ── Merge metadata ────────────────────────────────────────────────────────────

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

# ── Assemble combined manifest ────────────────────────────────────────────────

combined = {
    "@context": "http://iiif.io/api/presentation/3/context.json",
    "id":   MANIFEST_ID,
    "type": "Manifest",
    "label": {"en": ["Iken Psalter Fragments"]},
    "summary": {"en": [
        "A combined presentation of Iken Psalter fragments held at two institutions: "
        "a drawing of King Edmund the Martyr with Middle English verse (Takamiya MS 136, "
        "Beinecke Library, Yale University), and eleven parchment bifolium fragments "
        "(SPEC.RARE.MS.MR.FRAG.60.1–9, Rare Books and Manuscripts Library, "
        "The Ohio State University). "
        "24 canvases total. Latin psalter, circa 1290–1310, possibly written for "
        "the church of St. Botolph in Essex."
    ]},
    "metadata": yale_meta + osu_meta_combined,
    "requiredStatement": {
        "label": {"en": ["Provider"]},
        "value": {"en": [
            "Yale University Library (Takamiya MS 136); "
            "The Ohio State University Libraries, Rare Books and Manuscripts Library "
            "(SPEC.RARE.MS.MR.FRAG.60.1–9)"
        ]},
    },
    "rights": "http://rightsstatements.org/vocab/NoC-US/1.0/",
    "provider": [
        {
            "id":   "https://www.wikidata.org/wiki/Q2583293",
            "type": "Agent",
            "label": {"en": ["Yale University Library"]},
            "homepage": [{
                "id":     "https://library.yale.edu/",
                "type":   "Text",
                "label":  {"en": ["Yale Library homepage"]},
                "format": "text/html",
            }],
        },
        {
            "id":   "https://www.wikidata.org/wiki/Q1065534",
            "type": "Agent",
            "label": {"en": ["The Ohio State University Libraries"]},
            "homepage": [{
                "id":     "https://library.osu.edu/",
                "type":   "Text",
                "label":  {"en": ["OSU Libraries homepage"]},
                "format": "text/html",
            }],
        },
    ],
    "thumbnail": yale.get("thumbnail", []),
    "start": {"id": yale_canvases[0]["id"], "type": "Canvas"},
    "items": yale_canvases + osu_canvases,
    "structures": [],
}

# ── Write output ──────────────────────────────────────────────────────────────

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(combined, f, indent=2, ensure_ascii=False)

total = len(combined["items"])
print(f"Written: {OUTPUT_FILE}")
print(f"Total canvases : {total}  (Yale: {len(yale_canvases)}, OSU: {len(osu_canvases)})")
