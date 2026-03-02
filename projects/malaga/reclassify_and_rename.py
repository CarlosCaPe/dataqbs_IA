#!/usr/bin/env python3
"""
reclassify_and_rename.py — Full pipeline: detect duplicates, classify with CLIP, rename files.

Steps:
  1. Hash all images (perceptual hash) to detect duplicates
  2. Remove duplicate files (keeps the one with earliest name)
  3. Classify all remaining images with CLIP ViT-B-32
  4. Rename files: CATEGORY_NN.jpeg  (e.g., FACHADA_01.jpeg, BAÑO_01.jpeg)
  5. Rebuild ficha_tecnica.json with new filenames and titles

Usage:
    python3 reclassify_and_rename.py ventaCasaBSA
    python3 reclassify_and_rename.py ventaCasaBSA --dry-run   # preview only
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

# ── CLIP categories ───────────────────────────────────────────────────
CATEGORIES = [
    ("FACHADA", "a photo of the front facade of a modern house"),
    ("COCHERA", "a photo of a garage or car parking area"),
    ("JARDIN", "a photo of a backyard garden with plants and grass"),
    ("TERRAZA", "a photo of a terrace or balcony"),
    ("ALBERCA", "a photo of a swimming pool"),
    ("ENTRADA", "a photo of a house entrance or front door"),
    ("SALA", "a photo of a living room with sofa and furniture"),
    ("COMEDOR", "a photo of a dining room with a dining table"),
    ("COCINA", "a photo of a kitchen with cabinets and appliances"),
    ("SALA_COMEDOR", "a photo of an open plan living and dining room"),
    ("RECAMARA_PRINCIPAL", "a photo of a master bedroom with a large bed"),
    ("RECAMARA", "a photo of a bedroom with a bed"),
    ("BAÑO", "a photo of a bathroom with toilet and shower"),
    ("VESTIDOR", "a photo of a walk-in closet or wardrobe"),
    ("OFICINA", "a photo of a home office with a desk"),
    ("AREA_LAVADO", "a photo of a laundry room with washing machine"),
    ("BODEGA", "a photo of a storage room"),
    ("ESCALERAS", "a photo of a staircase inside a house"),
    ("PANELES_SOLARES", "a photo of solar panels on a roof"),
    ("AREA_SOCIAL", "a photo of a family entertainment or TV room"),
    ("ROOF_GARDEN", "a photo of a rooftop garden terrace with pergola"),
    ("COCINA_BARRA", "a photo of a kitchen with a breakfast bar counter"),
    ("CUARTO_SERVICIO", "a photo of a small utility service room"),
    ("PASILLO", "a photo of a hallway or corridor inside an apartment"),
    ("VISTA_EXTERIOR", "a photo of an exterior street view of a neighborhood"),
    ("FACHADA_EDIFICIO", "a photo of the front of an apartment building"),
    ("ESTACIONAMIENTO", "a photo of an open air parking lot or parking space"),
    ("PLANO_DISTRIBUCION", "a photo of a floor plan or architectural blueprint"),
]


# ── Step 1: Detect duplicates via content hash + perceptual resize ────
def compute_image_hash(filepath: str) -> str:
    """Compute a perceptual hash: resize to 64x64 grayscale → SHA256.
    This catches near-identical images even if metadata differs."""
    try:
        img = Image.open(filepath).convert("L").resize((64, 64), Image.LANCZOS)
        pixels = img.tobytes()
        return hashlib.sha256(pixels).hexdigest()
    except Exception:
        # Fallback to file-content hash
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()


def find_duplicates(image_dir: str) -> dict[str, list[str]]:
    """Return dict of hash → [filepaths] where len > 1 means duplicates."""
    files = _list_images(image_dir)
    hash_map: dict[str, list[str]] = defaultdict(list)
    for fp in files:
        h = compute_image_hash(fp)
        hash_map[h].append(fp)
    return {h: paths for h, paths in hash_map.items() if len(paths) > 1}


def remove_duplicates(image_dir: str, dry_run: bool = False) -> list[str]:
    """Detect and remove duplicate images. Keeps the first (alphabetically)."""
    dupes = find_duplicates(image_dir)
    removed = []
    if not dupes:
        print("✅ No duplicate images found.")
        return removed

    print(f"\n🔍 Found {len(dupes)} sets of duplicates:")
    for h, paths in dupes.items():
        paths_sorted = sorted(paths)
        keep = paths_sorted[0]
        to_remove = paths_sorted[1:]
        print(f"  KEEP: {os.path.basename(keep)}")
        for r in to_remove:
            name = os.path.basename(r)
            if dry_run:
                print(f"    🗑️  [DRY-RUN] would remove: {name}")
            else:
                os.remove(r)
                print(f"    🗑️  Removed: {name}")
            removed.append(r)

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Removed {len(removed)} duplicate(s).")
    return removed


# ── Step 2: Classify with CLIP ────────────────────────────────────────
def load_model():
    print("🔄 Loading CLIP model...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()
    print("✅ Model loaded.")
    return model, processor


def classify_all(image_dir: str, model, processor, top_k: int = 3) -> list[dict]:
    text_labels = [c[0] for c in CATEGORIES]
    text_prompts = [c[1] for c in CATEGORIES]

    files = _list_images(image_dir)
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
                text=text_prompts, images=image,
                return_tensors="pt", padding=True,
            )
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits_per_image.squeeze(0)
                probs = logits.softmax(dim=-1)

            values, indices = probs.topk(top_k)
            matches = [
                {"label": text_labels[idx], "confidence": round(val.item() * 100, 1)}
                for val, idx in zip(values, indices)
            ]
            best = matches[0]
            results.append({
                "filepath": filepath,
                "file": filename,
                "classification": best["label"],
                "confidence": best["confidence"],
                "top_matches": matches,
            })

            icon = "🟢" if best["confidence"] > 40 else "🟡" if best["confidence"] > 20 else "🔴"
            match_str = " | ".join(f"{m['label']} ({m['confidence']}%)" for m in matches)
            print(f"  {icon} {filename}")
            print(f"     → {match_str}")

        except Exception as e:
            print(f"  ❌ {filename}: {e}")
            results.append({
                "filepath": filepath, "file": filename,
                "classification": "ERROR", "confidence": 0,
                "top_matches": [], "error": str(e),
            })

    return results


# ── Step 3: Rename files ──────────────────────────────────────────────
def rename_files(results: list[dict], dry_run: bool = False) -> list[dict]:
    """Rename files to CATEGORY_NN.jpeg. Returns updated results with new paths."""
    # Count per category to build sequential names
    cat_counter: Counter = Counter()
    rename_plan = []

    for r in results:
        cat = r["classification"]
        if cat == "ERROR":
            rename_plan.append((r, None))
            continue
        cat_counter[cat] += 1
        seq = cat_counter[cat]
        ext = os.path.splitext(r["file"])[1].lower() or ".jpeg"
        new_name = f"{cat}_{seq:02d}{ext}"
        rename_plan.append((r, new_name))

    print(f"\n📝 Rename plan ({len(rename_plan)} files):\n")
    updated_results = []

    for r, new_name in rename_plan:
        old_path = r["filepath"]
        old_name = r["file"]
        if new_name is None:
            print(f"  ⚠️  {old_name} → SKIP (classification error)")
            updated_results.append(r)
            continue

        new_path = os.path.join(os.path.dirname(old_path), new_name)

        # Avoid overwriting if same name
        if old_path == new_path:
            print(f"  ✓ {old_name} → (already named correctly)")
            r["new_file"] = new_name
            updated_results.append(r)
            continue

        if dry_run:
            print(f"  📄 {old_name} → {new_name}  ({r['confidence']}%)")
        else:
            # Use a temp name first to avoid collisions during batch rename
            tmp_path = old_path + ".tmp_rename"
            os.rename(old_path, tmp_path)
            r["_tmp_path"] = tmp_path
            print(f"  📄 {old_name} → {new_name}  ({r['confidence']}%)")

        r["new_file"] = new_name
        r["new_path"] = new_path
        updated_results.append(r)

    # Second pass: move from tmp to final name (avoids collision if old name = another's new name)
    if not dry_run:
        for r in updated_results:
            tmp = r.pop("_tmp_path", None)
            new_path = r.get("new_path")
            if tmp and new_path:
                os.rename(tmp, new_path)
                r["filepath"] = new_path
                r["file"] = r["new_file"]

    return updated_results


# ── Step 4: Update ficha_tecnica.json ─────────────────────────────────
def rebuild_ficha_json(subtask_dir: str, results: list[dict], dry_run: bool = False):
    """Rebuild the property_images array in ficha_tecnica.json."""
    ficha_path = os.path.join(subtask_dir, "ficha_tecnica.json")
    if not os.path.exists(ficha_path):
        print(f"\n⚠️  {ficha_path} not found. Skipping.")
        return

    with open(ficha_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build new property_images from classification results
    new_images = []
    for i, r in enumerate(results):
        fname = r.get("new_file", r["file"])
        new_images.append({
            "title": r["classification"],
            "url": f"inputImages/{fname}",
            "position": i,
        })

    data["property_images"] = new_images
    data["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat()

    meta = data.get("_malaga_meta", {})
    meta["images_pending_classification"] = False
    meta["total_images"] = len(new_images)
    meta["last_classified_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    data["_malaga_meta"] = meta

    if dry_run:
        print(f"\n📋 [DRY-RUN] Would update ficha_tecnica.json with {len(new_images)} images.")
    else:
        with open(ficha_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ ficha_tecnica.json updated with {len(new_images)} images.")


# ── Helpers ───────────────────────────────────────────────────────────
def _list_images(image_dir: str) -> list[str]:
    exts = ("*.jpeg", "*.jpg", "*.png", "*.webp")
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(image_dir, ext)))
    return sorted(files)


# ── Main ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Dedupe → Classify → Rename → Update JSON"
    )
    parser.add_argument("subtask_dir", help="Subtask folder (e.g., ventaCasaBSA)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    subtask_dir = os.path.abspath(args.subtask_dir)
    input_dir = os.path.join(subtask_dir, "inputImages")
    if not os.path.isdir(input_dir):
        print(f"❌ inputImages/ not found in {subtask_dir}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"  Pipeline: {os.path.basename(subtask_dir)}")
    print(f"  Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"{'='*60}")

    # Step 1 — Duplicates
    print(f"\n{'─'*60}")
    print("STEP 1: Detecting duplicates (perceptual hash)...")
    removed = remove_duplicates(input_dir, dry_run=args.dry_run)

    # Step 2 — Classify
    print(f"\n{'─'*60}")
    print("STEP 2: Classifying images with CLIP...")
    model, processor = load_model()
    results = classify_all(input_dir, model, processor, top_k=args.top_k)

    if not results:
        return

    # Summary
    print(f"\n{'─'*60}")
    counts = Counter(r["classification"] for r in results)
    print(f"📊 Classification Summary ({len(results)} images):")
    for label, count in counts.most_common():
        print(f"   {label}: {count}")

    # Step 3 — Rename
    print(f"\n{'─'*60}")
    print("STEP 3: Renaming files by classification...")
    results = rename_files(results, dry_run=args.dry_run)

    # Step 4 — Update JSON
    print(f"\n{'─'*60}")
    print("STEP 4: Updating ficha_tecnica.json...")
    rebuild_ficha_json(subtask_dir, results, dry_run=args.dry_run)

    # Save report
    report_path = os.path.join(subtask_dir, "classification_report.json")
    report = {
        "classified_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "model": "openai/clip-vit-base-patch32 (HuggingFace transformers)",
        "total_images": len(results),
        "duplicates_removed": len(removed),
        "results": [
            {
                "file": r.get("new_file", r["file"]),
                "original_file": r["file"] if r.get("new_file") and r["new_file"] != r["file"] else None,
                "classification": r["classification"],
                "confidence": r["confidence"],
                "top_matches": r["top_matches"],
            }
            for r in results
        ],
    }
    if not args.dry_run:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📋 Report saved: {report_path}")

    print(f"\n{'='*60}")
    print(f"  ✅ Done! {len(results)} images processed, {len(removed)} duplicates removed.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
