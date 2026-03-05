# StopPlag

Transcripción automática de entrevistas de usuario (audios en español) usando
[OpenAI Whisper](https://github.com/openai/whisper).

## Setup

```bash
cd projects/stopplag
poetry install
```

> **Requisito**: FFmpeg debe estar instalado en el sistema.
> En Linux: `sudo apt install ffmpeg`

## Uso

```bash
# Transcribir los audios de la entrevista
poetry run stopplag-transcribe

# O directamente:
poetry run python -m stopplag.transcribe
```

Los archivos de transcripción se guardan en `transcripts/`.

## Estructura

```
stopplag/
├── audios/           ← Archivos de audio originales
├── transcripts/      ← Transcripciones generadas (.txt y .md)
├── src/stopplag/
│   ├── __init__.py
│   └── transcribe.py ← Script principal de transcripción
├── pyproject.toml
└── README.md
```
