#!/usr/bin/env python3
"""
classify_images.py — CLIP-based image classifier for real estate property photos.

Uses OpenAI CLIP (ViT-B-32) via open_clip to match images against real estate
room/area categories using zero-shot classification in both Spanish and English.

Usage:
    python classify_images.py <subtask_dir>
    python classify_images.py ventaCasaBSA
    python classify_images.py ventaCasaBSA --update-json   # auto-update ficha_tecnica.json

Outputs:
    - Console report with top-3 matches per image
    - Optional: updates property_images[].title in ficha_tecnica.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image


# ── Category labels for zero-shot classification ──────────────────────
# English prompts for CLIP (trained on English data)
CATEGORIES = [
    # Exterior
    ("FACHADA", "a photo of the front facade of a modern house"),
    ("COCHERA", "a photo of a garage or car parking area"),
    ("JARDIN", "a photo of a backyard garden with plants and grass"),
    ("TERRAZA", "a photo of a terrace or balcony"),
    ("ALBERCA", "a photo of a swimming pool"),
    ("ENTRADA", "a photo of a house entrance or front door"),
    # Interior - Common areas
    ("SALA", "a photo of a living room with sofa and furniture"),
    ("COMEDOR", "a photo of a dining room with a dining table"),
    ("COCINA", "a photo of a kitchen with cabinets and appliances"),
    ("SALA_COMEDOR", "a photo of an open plan living and dining room"),
    # Interior - Private areas
    ("RECAMARA_PRINCIPAL", "a photo of a master bedroom with a large bed"),
    ("RECAMARA", "a photo of a bedroom with a bed"),
    ("BAÑO", "a photo of a bathroom with toilet and shower"),
    ("VESTIDOR", "a photo of a walk-in closet or wardrobe"),
    # Interior - Utility
    ("OFICINA", "a photo of a home office with a desk"),
    ("AREA_LAVADO", "a photo of a laundry room with washing machine"),
    ("BODEGA", "a photo of a storage room"),
    ("ESCALERAS", "a photo of a staircase inside a house"),
    # Features
    ("PANELES_SOLARES", "a photo of solar panels on a roof"),
    ("AREA_SOCIAL", "a photo of a family entertainment or TV room"),
    # Views / General
    ("VISTA_EXTERIOR", "a photo of an exterior street view of a neighborhood"),
    ("PLANO_DISTRIBUCION", "a photo of a floor plan or architectural blueprint"),
]


def load_model():
    """Load HuggingFace CLIP model (openai/clip-vit-base-patch32)."""
    print("🔄 Loading CLIP model (openai/clip-vit-base-patch32)...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()
    print("✅ Model loaded.")
    return model, processor


def classify_images(image_dir: str, model, processor, top_k: int = 3):
    """Classify all images in directory using CLIP zero-shot."""
    text_labels = [cat[0] for cat in CATEGORIES]
    text_prompts = [cat[1] for cat in CATEGORIES]

    # Find images
    exts = ('*.jpeg', '*.jpg', '*.png', '*.webp')
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(image_dir, ext)))
    files = sorted(files)

    if not files:
        print("❌ No images found.")
        return []

    print(f"\n📸 Classifying {len(files)} images...\n")
    results = []

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            image = Image.open(filepath).convert("RGB")

            inputs = processor(
                text=text_prompts,
                images=image,
                return_tensors="pt",
                padding=True,
            )

            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits_per_image.squeeze(0)
                probs = logits.softmax(dim=-1)

            values, indices = probs.topk(top_k)

            matches = []
            for val, idx in zip(values, indices):
                matches.append({
                    "label": text_labels[idx],
                    "confidence": round(val.item() * 100, 1),
                })

            best = matches[0]
            results.append({
                "file": filename,
                "classification": best["label"],
                "confidence": best["confidence"],
                "top_matches": matches,
            })

            # Console output
            match_str = " | ".join(
                f"{m['label']} ({m['confidence']}%)" for m in matches
            )
            conf_icon = "🟢" if best["confidence"] > 40 else "🟡" if best["confidence"] > 20 else "🔴"
            print(f"  {conf_icon} {filename}")
            print(f"     → {match_str}")

        except Exception as e:
            print(f"  ❌ {filename}: {e}")
            results.append({
                "file": filename,
                "classification": "ERROR",
                "confidence": 0,
                "top_matches": [],
                "error": str(e),
            })

    return results


def update_ficha_json(subtask_dir: str, results: list[dict]):
    """Update ficha_tecnica.json with classification results."""
    ficha_path = os.path.join(subtask_dir, "ficha_tecnica.json")
    if not os.path.exists(ficha_path):
        print(f"\n⚠️  {ficha_path} not found. Skipping update.")
        return

    with open(ficha_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Build lookup: filename → classification
    lookup = {r["file"]: r["classification"] for r in results if r["classification"] != "ERROR"}

    updated = 0
    for img in data.get("property_images", []):
        url = img.get("url", "")
        basename = os.path.basename(url)
        if basename in lookup:
            old_title = img["title"]
            img["title"] = lookup[basename]
            if old_title != lookup[basename]:
                updated += 1

    # Update meta
    data["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    pending = sum(1 for img in data["property_images"] if img["title"] == "PENDIENTE_CLASIFICAR")
    data["_malaga_meta"]["images_pending_classification"] = pending > 0

    with open(ficha_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Updated {updated} image titles in ficha_tecnica.json ({pending} still pending)")


def save_report(subtask_dir: str, results: list[dict]):
    """Save full classification report as JSON."""
    report_path = os.path.join(subtask_dir, "classification_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "classified_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "model": "ViT-B-32 (laion2b_s34b_b79k)",
            "total_images": len(results),
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"📋 Report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="CLIP image classifier for real estate")
    parser.add_argument("subtask_dir", help="Subtask folder (e.g., ventaCasaBSA)")
    parser.add_argument("--update-json", action="store_true", help="Update ficha_tecnica.json titles")
    parser.add_argument("--top-k", type=int, default=3, help="Show top-K matches per image")
    args = parser.parse_args()

    subtask_dir = os.path.abspath(args.subtask_dir)
    input_dir = os.path.join(subtask_dir, "inputImages")

    if not os.path.isdir(input_dir):
        print(f"❌ inputImages/ not found in {subtask_dir}")
        sys.exit(1)

    model, processor = load_model()
    results = classify_images(input_dir, model, processor, top_k=args.top_k)

    if not results:
        return

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Summary: {len(results)} images classified")
    from collections import Counter
    counts = Counter(r["classification"] for r in results)
    for label, count in counts.most_common():
        print(f"   {label}: {count}")

    # Save report
    save_report(subtask_dir, results)

    # Update JSON if requested
    if args.update_json:
        update_ficha_json(subtask_dir, results)
    else:
        print(f"\n💡 Run with --update-json to update ficha_tecnica.json titles")


if __name__ == "__main__":
    main()
