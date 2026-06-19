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
import urllib.parse
import urllib.request
import urllib.error

# ── Configuration ─────────────────────────────────────────────────────────────

MANIFEST_ID = "https://raw.githubusercontent.com/lauraw15/IkenPsalter/main/iken-psalter-fragments-manifest.json"

YALE_FILE = "source-manifests/yale-16371296.json"

CMA_FILE  = "source-manifests/cleveland.json"  # Cleveland Museum of Art — single leaf, already IIIF v3

# OSU source files in desired folio order
OSU_FILES = [
    ("1",    "source-manifests/osu-1.json"),
    ("2",    "source-manifests/osu-2.json"),
    ("3",    "source-manifests/osu-3.json"),
    ("3.1",  "source-manifests/osu-3.1.json"),
    ("4",    "source-manifests/osu-4.json"),
    ("5",    "source-manifests/osu-5.json"),
    ("6",    "source-manifests/osu-6.json"),
    ("7",    "source-manifests/osu-7.json"),
    ("7.10", "source-manifests/osu-7.10.json"),
    ("8",    "source-manifests/osu-8.json"),
    ("9",    "source-manifests/osu-9.json"),
]

MISSING_FRAGMENTS = [
    {
        "slug": "psalm-1-36",
        "label": "Missing Psalter (leaves 1–36) — Psalms 1–36",
        "description": "Large missing opening containing the historiated initial at Psalm 26 (David pointing to his eye).",
    },
    {
        "slug": "cornell-002a-h",
        "label": "Cornell University Library fragment 80.052.002a–h — Psalms 48–65",
        "description": "A reconstructed Cornell quire believed to follow OSU folio 1 and precede Stanford MISC 1989.",
    },
    {
        "slug": "psalm-66-68",
        "label": "Missing Psalter (leaves 66–68) — Psalms 66–68",
        "description": "Historiated initial at Psalm 68 (David praying in the waters).",
    },
    {
        "slug": "stanford-misc-1989",
        "label": "Stanford University Libraries MISC 1989 (not yet digitized) — Psalms 68–69",
        "description": "A fragment held at Stanford University Libraries that is recognized as part of the Iken Psalter.",
    },
    {
        "slug": "psalm-71-85",
        "label": "Missing Psalter (leaves 71–85) — Psalms 71–85",
        "description": "Historiated initial at Psalm 80 (David playing carillon).",
    },
    {
        "slug": "cornell-001a-h",
        "label": "Cornell University Library fragment 80.052.001a–h — Psalms 89–104",
        "description": "A reconstructed Cornell quire believed to follow OSU folio 4 and precede OSU folio 5.",
    },
    {
        "slug": "psalm-107-108",
        "label": "Missing Psalter (leaves 107–108) — Psalms 107–108",
        "description": "A short gap in the reconstructed sequence before the Cleveland leaf (1999.125).",
    },
    {
        "slug": "private-oh-1",
        "label": "Private Ohio collection fragment 1 (not yet digitized) — Psalms 113–117",
        "description": "A private Ohio Iken Psalter fragment believed to follow OSU folio 6.",
    },
    {
        "slug": "psalm-119-128",
        "label": "Missing Psalter (leaves 119–128) — Psalms 119–128",
        "description": "A large lacuna in the reconstructed sequence between OSU folio 7 and OSU folio 7.10.",
    },
    {
        "slug": "psalm-135-145",
        "label": "Missing Psalter (leaves 135–145) — Psalms 135–145",
        "description": "A gap in the reconstructed sequence before the second private Ohio fragment.",
    },
    {
        "slug": "private-oh-2",
        "label": "Private Ohio collection fragment 2 (not yet digitized) — Psalms 146–150",
        "description": "A private Ohio Iken Psalter fragment that is recognized as part of the manuscript.",
    },
    {
        "slug": "stanford-misc-2953",
        "label": "Stanford University Libraries MISC 2953 (not yet digitized)",
        "description": "A fragment held at Stanford University Libraries that is recognized as part of the Iken Psalter.",
    },
    {
        "slug": "osu-3a",
        "label": "OSU additional fragment MS MR.Frag.60.3a (not yet digitized)",
        "description": "An additional OSU Iken Psalter fragment that is known from catalog records but does not yet have an available image manifest.",
    },
]

# Optional mapping of fragment slug -> external IIIF manifest or purl URL.
# If provided, the build script will attempt to fetch the manifest and use
# the canvases from that remote manifest instead of generating a placeholder.
EXTERNAL_MANIFESTS = {
    "stanford-misc-1989": "https://purl.stanford.edu/sz746tg6023",
    "stanford-misc-2953": "https://purl.stanford.edu/vp788xm2948",
}

OUTPUT_FILE = "iken-psalter-fragments-manifest.json"

# Normalize certain fragment labels: use "Missing Psalter Folio" prefix
for frag in MISSING_FRAGMENTS:
    lbl = frag.get("label", "")
    if lbl.startswith("Missing Psalter"):
        frag["label"] = lbl.replace("Missing Psalter", "Missing Psalter Folio", 1)

SIDES = ["recto", "verso"]

BLANK_PAGE_IMAGE = "https://via.placeholder.com/1000x1400.png?text="

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
        # Some v2 manifests provide a resource '@id' that is already a full-image
        # URL (contains '/full/' segments). If so, use it as-is; otherwise, if a
        # service id is available, construct a full image URL from the service.
        src_id = res.get('@id', '')
        if '/full/' in src_id or src_id.endswith('.jpg') or src_id.endswith('.jp2'):
            image_id = src_id
        elif svc_id:
            image_id = svc_id.rstrip('/') + '/full/full/0/default.jpg'
        else:
            image_id = src_id

        body = {
            "id":     image_id,
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


def make_placeholder_canvas(slug, label, description, width=1000, height=1400):
    canvas_id = f"{MANIFEST_ID}/canvas/missing-{slug}"
    # Create a local SVG placeholder file and reference it.
    # Filename: placeholders/missing-<slug>.svg (safe characters only)
    import os
    safe_slug = re.sub(r"[^A-Za-z0-9._-]", "_", f"missing-{slug}")
    os.makedirs("placeholders", exist_ok=True)
    svg_filename = f"{safe_slug}.svg"
    svg_path = os.path.join("placeholders", svg_filename)
    svg_url = svg_path.replace("\\", "/")

    if not os.path.exists(svg_path):
        # Write a simple SVG with centered label text
        svg_label = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        svg_content = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
            f'<rect width="100%" height="100%" fill="#f5f5f5"/>\n'
            f'<text x="50%" y="50%" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="40" fill="#333" text-anchor="middle" dominant-baseline="middle">{svg_label}</text>\n'
            f'</svg>\n'
        )
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(svg_content)

    image_url = svg_url
    return {
        "id":    canvas_id,
        "type":  "Canvas",
        "label": {"none": [label]},
        "width": width,
        "height": height,
        "metadata": [
            {"label": {"en": ["Status"]}, "value": {"en": ["Not yet digitized"]}},
            {"label": {"en": ["Description"]}, "value": {"en": [description]}},
        ],
        "items": [
            {
                "id":    canvas_id + "/page",
                "type":  "AnnotationPage",
                "items": [
                    {
                        "id":         canvas_id + "/annotation",
                        "type":       "Annotation",
                        "motivation": "painting",
                        "target":     canvas_id,
                            "body": {
                            "id":     image_url,
                            "type":   "Image",
                            "format": "image/svg+xml",
                            "width":  width,
                            "height": height,
                        },
                    }
                ],
            }
        ],
        # Provide a thumbnail so viewers (including Mirador) show a preview
        "thumbnail": [
            {
                "id": image_url,
                "type": "Image",
                "format": "image/svg+xml",
                "width": int(width * 0.3),
                "height": int(height * 0.3),
            }
        ],
    }

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



def expand_fragment_canvases(fragment):
    """Return a list of placeholder canvases for the given fragment.

    - If the fragment label or slug contains a numeric range (e.g. "leaves 1–36" or "119-128"),
      create one leaf placeholder per number and one canvas per side (recto, verso).
    - If it contains an alpha range after a base number (e.g. "001a–h"), expand a..h.
    - Otherwise return a single placeholder canvas for the fragment.
    """
    slug = fragment["slug"]
    label = fragment.get("label", slug)
    desc = fragment.get("description", "")
    canvases = []

    # If an external IIIF manifest or purl has been provided for this fragment,
    # attempt to fetch it and use its canvases.
    if slug in EXTERNAL_MANIFESTS:
        base = EXTERNAL_MANIFESTS[slug]
        # Candidate suffixes to try for IIIF manifest endpoints
        candidates = ["/iiif/manifest.json", "/iiif/2/manifest.json", "/manifest.json", ""]
        for suf in candidates:
            url = urllib.parse.urljoin(base.rstrip('/') + '/', suf.lstrip('/'))
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    data = resp.read().decode('utf-8')
                manifest = json.loads(data)
            except (urllib.error.URLError, ValueError):
                manifest = None
            if manifest:
                # If this is IIIF Presentation API v3, assume canvases live in manifest['items']
                if isinstance(manifest, dict) and manifest.get('@context') and 'presentation/3' in manifest.get('@context'):
                    items = manifest.get('items', [])
                    # Adopt canvases as-is (ensure ids are absolute)
                    for it in items:
                        canvases.append(it)
                    if canvases:
                        return canvases
                # If this is a v2 manifest, convert its canvases to v3 format
                if isinstance(manifest, dict) and manifest.get('@context') and 'presentation/2' in manifest.get('@context'):
                    for seq in manifest.get('sequences', []):
                        for idx, canvas_v2 in enumerate(seq.get('canvases', [])):
                            # remote v2 manifests may contain long canvas lists; use parity
                            # to assign recto/verso labels (0=recto, 1=verso)
                            canvases.append(osu_canvas_to_v3(slug, canvas_v2, idx % 2))
                    if canvases:
                        return canvases
        # If remote fetch failed, fall back to placeholder behaviour

    # Special-case: use a single placeholder canvas for Psalms 1-36
    if slug == "psalm-1-36":
        # Use concise label without leaf counts
        single_label = "Missing Psalter, Psalms 1-36"
        return [make_placeholder_canvas(slug, single_label, desc)]

    # Search for explicit 'leaves N–M' in label or description
    m = re.search(r"leaves?\s+(\d+)[–-](\d+)", (label + " " + desc))
    if m:
        start = int(m.group(1))
        end = int(m.group(2))
        for leaf in range(start, end + 1):
            canvases.append(make_placeholder_canvas(f"{slug}-leaf{leaf}", f"{label} — leaf {leaf}", desc))
        return canvases

    # Search for numeric ranges in slug (e.g. psalm-119-128)
    m2 = re.search(r"(\d+)[-–](\d+)", slug)
    if m2:
        start = int(m2.group(1))
        end = int(m2.group(2))
        for leaf in range(start, end + 1):
            canvases.append(make_placeholder_canvas(f"{slug}-leaf{leaf}", f"{label} — leaf {leaf}", desc))
        return canvases

    # Search for letter ranges after a base number (e.g. 001a–h or 001a-h)
    m3 = re.search(r"(\d+)([a-zA-Z])[–-]([a-zA-Z])", slug)
    if m3:
        base = m3.group(1)
        start_ch = m3.group(2).lower()
        end_ch = m3.group(3).lower()
        for code in range(ord(start_ch), ord(end_ch) + 1):
            suffix = chr(code)
            canvases.append(make_placeholder_canvas(f"{slug}-{base}{suffix}", f"{label} — {base}{suffix}", desc))
        return canvases

    # Fallback: single placeholder canvas per fragment/folio
    return [make_placeholder_canvas(slug, label, desc)]


placeholder_canvases_map = {fragment["slug"]: expand_fragment_canvases(fragment) for fragment in MISSING_FRAGMENTS}
placeholder_canvases = [c for canv_list in placeholder_canvases_map.values() for c in canv_list]

# Build the reconstruction item sequence programmatically so placeholders expand into
# one or more canvases depending on the fragment definition.
sequence_tokens = [
    ("yale", 0),
    ("yale", 1),
    ("placeholder", "psalm-1-36"),
    ("osu", 0),
    ("osu", 1),
    ("placeholder", "cornell-002a-h"),
    ("placeholder", "psalm-66-68"),
    ("placeholder", "stanford-misc-1989"),
    ("osu", 2),
    ("osu", 3),
    ("placeholder", "psalm-71-85"),
    ("osu", 4),
    ("osu", 5),
    ("osu", 6),
    ("osu", 7),
    ("osu", 8),
    ("osu", 9),
    ("placeholder", "cornell-001a-h"),
    ("osu", 10),
    ("osu", 11),
    ("placeholder", "psalm-107-108"),
    ("cma", 0),
    ("osu", 12),
    ("osu", 13),
    ("placeholder", "private-oh-1"),
    ("osu", 14),
    ("osu", 15),
    ("placeholder", "psalm-119-128"),
    ("osu", 16),
    ("osu", 17),
    ("placeholder", "psalm-135-145"),
    ("placeholder", "private-oh-2"),
    ("osu", 18),
    ("osu", 19),
    ("osu", 20),
    ("osu", 21),
    ("placeholder", "stanford-misc-2953"),
]

reconstruction_items = []
for kind, idx in sequence_tokens:
    if kind == "yale":
        reconstruction_items.append(yale_canvases[idx])
    elif kind == "osu":
        reconstruction_items.append(osu_canvases[idx])
    elif kind == "cma":
        reconstruction_items.append(cma_canvases[idx])
    elif kind == "placeholder":
        for c in placeholder_canvases_map[idx]:
            reconstruction_items.append(c)

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
        "This manifest uses the reconstruction order from the Iken Psalter worksheet, "
        "including placeholder canvases for missing folios and fragments that are not yet digitized."
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
    "items": reconstruction_items,
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
    ("1",    osu_canvases[0:2]),
    ("2",    osu_canvases[2:4]),
    ("3",    osu_canvases[4:6]),
    ("3.1",  osu_canvases[6:8]),
    ("4",    osu_canvases[8:10]),
    ("5",    osu_canvases[10:12]),
    ("6",    osu_canvases[12:14]),
    ("7",    osu_canvases[14:16]),
    ("7.10", osu_canvases[16:18]),
    ("8",    osu_canvases[18:20]),
    ("9",    osu_canvases[20:22]),
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
            "items": [canvas_ref(canvas) for canvas in canvases],
        }
        for folio, canvases in osu_folio_defs
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
        "items": [canvas_ref(cma_canvases[0])],
    }],
}

placeholder_range = {
    "id":    range_id("missing"),
    "type":  "Range",
    "label": {"en": ["Not yet digitized / missing fragments"]},
    "items": [
        {
            "id":    range_id(f"missing-{fragment['slug']}"),
            "type":  "Range",
            "label": {"en": [fragment["label"]]},
            "items": [canvas_ref(c) for c in placeholder_canvases_map[fragment["slug"]]],
        }
        for fragment in MISSING_FRAGMENTS
    ],
}

top_range = {
    "id":          range_id("top"),
    "type":        "Range",
    "label":       {"en": ["Iken Psalter Fragments"]},
    "viewingHint": "top",
    "items":       [yale_range, osu_range, cma_range, placeholder_range],
}

combined["structures"] = collect_ranges(top_range)

# ── Write output ──────────────────────────────────────────────────────────────

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(combined, f, indent=2, ensure_ascii=False)

total = len(combined["items"])
print(f"Written: {OUTPUT_FILE}")
print(f"Total canvases: {total}  (Yale: {len(yale_canvases)}, OSU: {len(osu_canvases)}, CMA: {len(cma_canvases)}, placeholders: {len(placeholder_canvases)})")
print("\nCanvas labels:")
for c in combined["items"]:
    print(f"  {list(c['label'].values())[0][0]}")
