"""
StopPlag – Transcripción de entrevistas de usuario con OpenAI Whisper.

Transcribe archivos de audio (OGG/MP3/WAV/M4A) en español usando el modelo
Whisper de OpenAI (local, sin API key) y genera transcripciones en texto plano
y un documento Markdown consolidado.
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent  # projects/stopplag
AUDIOS_DIR = PROJECT_DIR / "audios"
TRANSCRIPTS_DIR = PROJECT_DIR / "transcripts"

# Whisper model sizes: tiny, base, small, medium, large
DEFAULT_MODEL = "medium"


def transcribe_audio(audio_path: Path, model_name: str = DEFAULT_MODEL) -> dict:
    """Transcribe a single audio file and return the Whisper result dict."""
    import whisper  # lazy import so help/--version work fast

    print(f"\n{'='*60}")
    print(f"  Transcribiendo: {audio_path.name}")
    print(f"  Modelo: {model_name}")
    print(f"{'='*60}")

    model = whisper.load_model(model_name)
    result = model.transcribe(
        str(audio_path),
        language="es",
        verbose=True,
    )
    return result


def save_individual_transcript(result: dict, output_path: Path) -> None:
    """Save a single transcript as plain text."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result["text"].strip(), encoding="utf-8")
    print(f"  ✓ Guardado: {output_path}")


def save_consolidated_markdown(
    results: list[tuple[str, dict]],
    output_path: Path,
) -> None:
    """
    Save all transcripts in a single Markdown document, in sequence,
    preserving the order of the interview.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = [
        "# StopPlag – Transcripción de Entrevista de Usuario",
        "",
        f"> Generado automáticamente el {now} con OpenAI Whisper.",
        "",
        "---",
        "",
    ]

    for idx, (filename, result) in enumerate(results, start=1):
        text = result["text"].strip()
        lines.append(f"## Parte {idx} — `{filename}`")
        lines.append("")
        # Wrap long paragraphs for readability
        for paragraph in text.split("\n"):
            wrapped = textwrap.fill(paragraph, width=100)
            lines.append(wrapped)
            lines.append("")
        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  ✓ Documento consolidado guardado: {output_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe entrevistas de usuario en español con OpenAI Whisper."
    )
    parser.add_argument(
        "--audios-dir",
        type=Path,
        default=AUDIOS_DIR,
        help="Directorio con los archivos de audio (default: audios/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=TRANSCRIPTS_DIR,
        help="Directorio de salida para transcripciones (default: transcripts/)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=["tiny", "base", "small", "medium", "large"],
        help="Tamaño del modelo Whisper (default: medium)",
    )
    args = parser.parse_args(argv)

    audio_extensions = {".ogg", ".mp3", ".wav", ".m4a", ".flac", ".webm"}
    audio_files = sorted(
        f for f in args.audios_dir.iterdir() if f.suffix.lower() in audio_extensions
    )

    if not audio_files:
        print(f"No se encontraron archivos de audio en {args.audios_dir}")
        sys.exit(1)

    print(f"\nSe encontraron {len(audio_files)} archivo(s) de audio:")
    for f in audio_files:
        print(f"  • {f.name}")

    results: list[tuple[str, dict]] = []

    for audio_file in audio_files:
        result = transcribe_audio(audio_file, model_name=args.model)
        results.append((audio_file.name, result))

        # Save individual .txt
        txt_path = args.output_dir / f"{audio_file.stem}.txt"
        save_individual_transcript(result, txt_path)

    # Save consolidated Markdown
    md_path = args.output_dir / "entrevista_completa.md"
    save_consolidated_markdown(results, md_path)

    print("\n✅ Transcripción completada exitosamente.")


if __name__ == "__main__":
    main()
