#!/usr/bin/env python3
"""
generate_ficha.py — Generate a ficha_tecnica.json skeleton from inputImages/ + text description.

Reusable across all malaga subtasks.

Usage:
    python generate_ficha.py <subtask_dir> [--title "..."] [--price 6700000] [--currency MXN]

Example:
    python generate_ficha.py ventaCasaBSA --title "Casa Moderna BSA" --price 6700000

If ficha_tecnica.json already exists, it will:
  - Add any NEW images from inputImages/ that aren't already in the JSON
  - Print a summary of what was added
  - NOT overwrite existing data (title, description, features, etc.)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone


def discover_images(input_dir: str) -> list[str]:
    """Find all image files in inputImages/."""
    exts = ('*.jpeg', '*.jpg', '*.png', '*.webp', '*.heic')
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(input_dir, ext)))
    return sorted(files)


def make_image_entry(filepath: str, sort_order: int) -> dict:
    """Create a property_images entry from a local file."""
    return {
        "title": "PENDIENTE_CLASIFICAR",
        "url": os.path.join("inputImages", os.path.basename(filepath)),
        "sort_order": sort_order,
    }


def make_skeleton(
    public_id: str,
    title: str,
    images: list[dict],
    price: float | None = None,
    currency: str = "MXN",
    operation_type: str = "sale",
) -> dict:
    """Create a blank ficha_tecnica.json skeleton in EasyBroker-compatible format."""
    now = datetime.now(timezone.utc).astimezone().isoformat()
    operations = []
    if price:
        operations.append({
            "type": operation_type,
            "amount": price,
            "currency": currency,
            "formatted_amount": f"${price:,.0f}",
            "commission": {"type": "percentage"},
            "unit": "total",
        })

    return {
        "public_id": public_id,
        "title": title,
        "description": "",
        "bedrooms": None,
        "bathrooms": None,
        "half_bathrooms": None,
        "parking_spaces": None,
        "lot_size": None,
        "lot_size_unit": "m²",
        "construction_size": None,
        "lot_length": None,
        "lot_width": None,
        "floors": None,
        "floor": None,
        "age": None,
        "internal_id": None,
        "expenses": None,
        "location": {
            "name": "",
            "latitude": None,
            "longitude": None,
            "street": None,
            "postal_code": None,
            "show_exact_location": False,
            "hide_exact_location": True,
            "exterior_number": None,
            "interior_number": None,
        },
        "property_type": "Casa",
        "created_at": now,
        "updated_at": now,
        "published_at": None,
        "operations": operations,
        "property_files": [],
        "videos": [],
        "virtual_tour": None,
        "collaboration_notes": None,
        "public_url": None,
        "shared_commission_percentage": None,
        "exclusive": None,
        "foreclosure": False,
        "tags": [],
        "private_description": "",
        "show_prices": True,
        "share_commission": False,
        "property_images": images,
        "agent": None,
        "features": [],
        "_malaga_meta": {
            "project": "",
            "source": "manual",
            "images_pending_classification": True,
            "images_total": len(images),
            "notes": "",
        },
    }


def update_existing(ficha_path: str, input_dir: str) -> None:
    """Add new images to an existing ficha_tecnica.json."""
    with open(ficha_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_urls = {img["url"] for img in data.get("property_images", [])}
    all_images = discover_images(input_dir)
    max_order = max((img.get("sort_order", 0) for img in data.get("property_images", [])), default=0)

    added = 0
    for filepath in all_images:
        rel_url = os.path.join("inputImages", os.path.basename(filepath))
        if rel_url not in existing_urls:
            max_order += 1
            data["property_images"].append(make_image_entry(filepath, max_order))
            added += 1

    if added > 0:
        data["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat()
        data["_malaga_meta"]["images_total"] = len(data["property_images"])
        data["_malaga_meta"]["images_pending_classification"] = any(
            img["title"] == "PENDIENTE_CLASIFICAR" for img in data["property_images"]
        )
        with open(ficha_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Added {added} new image(s). Total: {len(data['property_images'])}")
    else:
        print("ℹ️  No new images to add.")


def create_new(subtask_dir: str, title: str, price: float | None, currency: str, op_type: str) -> None:
    """Create a fresh ficha_tecnica.json."""
    input_dir = os.path.join(subtask_dir, "inputImages")
    ficha_path = os.path.join(subtask_dir, "ficha_tecnica.json")

    all_images = discover_images(input_dir)
    entries = [make_image_entry(f, i + 1) for i, f in enumerate(all_images)]

    folder_name = os.path.basename(os.path.abspath(subtask_dir))
    public_id = f"MLG-{folder_name[:8].upper()}-001"

    data = make_skeleton(public_id, title, entries, price, currency, op_type)
    data["_malaga_meta"]["project"] = folder_name

    with open(ficha_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Created {ficha_path} with {len(entries)} image(s).")
    print(f"   ID: {public_id}")
    print(f"   Edit the JSON to fill in description, features, location, etc.")


def main():
    parser = argparse.ArgumentParser(description="Generate or update ficha_tecnica.json")
    parser.add_argument("subtask_dir", help="Path to the subtask folder (e.g., ventaCasaBSA)")
    parser.add_argument("--title", default="Propiedad sin título", help="Property title")
    parser.add_argument("--price", type=float, default=None, help="Price amount")
    parser.add_argument("--currency", default="MXN", help="Currency code (default: MXN)")
    parser.add_argument("--op-type", default="sale", choices=["sale", "rental"], help="Operation type")
    args = parser.parse_args()

    subtask_dir = os.path.abspath(args.subtask_dir)
    input_dir = os.path.join(subtask_dir, "inputImages")
    ficha_path = os.path.join(subtask_dir, "ficha_tecnica.json")

    if not os.path.isdir(input_dir):
        print(f"❌ inputImages/ not found in {subtask_dir}")
        sys.exit(1)

    if os.path.exists(ficha_path):
        print(f"📋 Updating existing {ficha_path} ...")
        update_existing(ficha_path, input_dir)
    else:
        print(f"📋 Creating new ficha_tecnica.json ...")
        create_new(subtask_dir, args.title, args.price, args.currency, args.op_type)


if __name__ == "__main__":
    main()
