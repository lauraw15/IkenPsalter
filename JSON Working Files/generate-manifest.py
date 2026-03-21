#!/usr/bin/env python3
"""
Generate complete IIIF v3 manifest for Iken Psalter project.
Combines OSU and Yale manifest files into a single composite manifest.
"""

import json
import os
from pathlib import Path

def extract_canvas_data(manifest_v2, folio_label_prefix):
    """Extract canvas data from IIIF v2 manifest and convert to v3 format."""
    canvases = []
    
    if 'sequences' not in manifest_v2 or not manifest_v2['sequences']:
        return canvases
    
    sequence = manifest_v2['sequences'][0]
    canvas_list = sequence.get('canvases', [])
    
    for idx, canvas in enumerate(canvas_list):
        # Determine if recto or verso based on index
        side = 'r' if idx == 0 else 'v'
        
        # Extract image service ID
        if 'images' in canvas and canvas['images']:
            image = canvas['images'][0]
            resource = image.get('resource', {})
            service = resource.get('service', {})
            
            if isinstance(service, list):
                service = service[0] if service else {}
            
            service_id = service.get('@id', '')
            
            # Extract dimensions
            width = canvas.get('width', 0)
            height = canvas.get('height', 0)
            
            # Determine image URL and service format
            if 'yale.edu' in service_id:
                image_url = f"{service_id}/full/full/0/default.jpg"
                service_type = "ImageService2"
            else:
                # OSU format
                image_url = f"{service_id}/full/full/0/default.jpg"
                service_type = "ImageService2"
            
            canvas_data = {
                'label': f"{folio_label_prefix}{side}",
                'width': width,
                'height': height,
                'image_url': image_url,
                'service_id': service_id,
                'service_type': service_type
            }
            canvases.append(canvas_data)
    
    return canvases

def create_canvas_v3(canvas_id, canvas_data, base_url):
    """Create a IIIF v3 Canvas object."""
    label = canvas_data['label']
    
    return {
        "id": f"{base_url}/canvas/{canvas_id}",
        "type": "Canvas",
        "label": {"en": [f"Folio {label}"]},
        "height": canvas_data['height'],
        "width": canvas_data['width'],
        "items": [
            {
                "id": f"{base_url}/page/{canvas_id}/1",
                "type": "AnnotationPage",
                "items": [
                    {
                        "id": f"{base_url}/annotation/{canvas_id}/1",
                        "type": "Annotation",
                        "motivation": "painting",
                        "target": f"{base_url}/canvas/{canvas_id}",
                        "body": {
                            "id": canvas_data['image_url'],
                            "type": "Image",
                            "format": "image/jpeg",
                            "height": canvas_data['height'],
                            "width": canvas_data['width'],
                            "service": [
                                {
                                    "id": canvas_data['service_id'],
                                    "type": canvas_data['service_type'],
                                    "profile": "http://iiif.io/api/image/2/level2.json"
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

def create_range_v3(range_id, folio_label, canvas_ids, base_url):
    """Create a IIIF v3 Range object for grouping recto/verso."""
    return {
        "id": f"{base_url}/range/{range_id}",
        "type": "Range",
        "label": {"en": [f"Folio {folio_label}"]},
        "items": [
            {"id": f"{base_url}/canvas/{cid}", "type": "Canvas"}
            for cid in canvas_ids
        ]
    }

def main():
    base_url = "https://lauraw15.github.io/IkenPsalter"
    
    # Define the folio structure
    folio_structure = [
        # Yale folios
        ('yale-16371296.json', 'Y1'),
        
        # OSU folios
        ('osu-1.json', '1'),
        ('osu-2.json', '2'),
        ('osu-3.1.json', '3.1'),
        ('osu-3.json', '3'),
        ('osu-4.json', '4'),
        ('osu-5.json', '5'),
        ('osu-6.json', '6'),
        ('osu-7.json', '7'),
        ('osu-7.10.json', '7.10'),
        ('osu-8.json', '8'),
        ('osu-9.json', '9'),
    ]
    
    all_canvases = []
    all_ranges = []
    
    print("Processing manifest files...")
    
    for filename, folio_label in folio_structure:
        if not os.path.exists(filename):
            print(f"Warning: {filename} not found, skipping...")
            continue
        
        print(f"  Processing {filename} (Folio {folio_label})...")
        
        with open(filename, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Handle IIIF v3 format (Yale)
        if manifest.get('@context') and 'presentation/3' in str(manifest.get('@context')):
            # Yale v3 format
            items = manifest.get('items', [])
            canvases_data = []
            
            for idx, canvas in enumerate(items):
                side = 'r' if idx == 0 else 'v'
                
                # Extract image info
                annotation_page = canvas.get('items', [{}])[0]
                annotation = annotation_page.get('items', [{}])[0]
                body = annotation.get('body', {})
                
                service = body.get('service', [{}])
                if isinstance(service, list):
                    service = service[0] if service else {}
                
                canvas_data = {
                    'label': f"{folio_label}{side}",
                    'width': canvas.get('width', 0),
                    'height': canvas.get('height', 0),
                    'image_url': body.get('id', ''),
                    'service_id': service.get('@id', ''),
                    'service_type': service.get('@type', 'ImageService2')
                }
                canvases_data.append(canvas_data)
        else:
            # IIIF v2 format (OSU)
            canvases_data = extract_canvas_data(manifest, folio_label)
        
        # Create v3 canvases
        folio_canvas_ids = []
        for canvas_data in canvases_data:
            canvas_id = f"folio-{canvas_data['label'].lower()}"
            canvas_v3 = create_canvas_v3(canvas_id, canvas_data, base_url)
            all_canvases.append(canvas_v3)
            folio_canvas_ids.append(canvas_id)
        
        # Create range for this folio
        if folio_canvas_ids:
            range_id = f"folio-{folio_label.lower()}"
            range_v3 = create_range_v3(range_id, folio_label, folio_canvas_ids, base_url)
            all_ranges.append(range_v3)
    
    # Create the complete manifest
    manifest_v3 = {
        "@context": "http://iiif.io/api/presentation/3/context.json",
        "id": f"{base_url}/manifests/iken-psalter.json",
        "type": "Manifest",
        "label": {"en": ["Iken Psalter (composite manifest)"]},
        
        "requiredStatement": {
            "label": {"en": ["Attribution"]},
            "value": {
                "en": [
                    "Images courtesy of The Ohio State University Libraries and Yale University Library. "
                    "Manifest assembled for the Iken Psalter project."
                ]
            }
        },
        
        "metadata": [
            {"label": {"en": ["Project"]}, "value": {"en": ["Iken Psalter"]}},
            {"label": {"en": ["Description"]}, "value": {"en": [
                f"Complete manifest with {len(all_canvases)} canvases ({len(all_ranges)} folios) "
                "grouped using IIIF v3 structures."
            ]}},
            {"label": {"en": ["Total Folios"]}, "value": {"en": [
                f"{len(all_ranges)} folios (1 from Yale, {len(all_ranges)-1} from OSU)"
            ]}}
        ],
        
        "items": all_canvases,
        "structures": all_ranges
    }
    
    # Write the output file
    output_file = "iken-psalter-complete.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(manifest_v3, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Complete manifest created: {output_file}")
    print(f"  Total canvases: {len(all_canvases)}")
    print(f"  Total folios: {len(all_ranges)}")
    print(f"  Total ranges: {len(all_ranges)}")
    
    # Print summary
    print("\nFolio summary:")
    for range_obj in all_ranges:
        folio_label = range_obj['label']['en'][0]
        num_canvases = len(range_obj['items'])
        print(f"  - {folio_label}: {num_canvases} canvases")

if __name__ == "__main__":
    main()