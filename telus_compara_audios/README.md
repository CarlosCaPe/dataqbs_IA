# telus_compara_audios

Automatiza la tarea "Audio Quality Compare" en Multimango.

- URL de tarea: https://www.multimango.com/tasks/080825-audio-quality-compare
- Interactúa con los botones "Audio A", "Audio B" y "Reference" y envía la elección (Version A/B/Tie)
- Soporta modo headed/headless, login manual, contador por iteración y límites con `--max-iters`

## Uso rápido

1) Instala dependencias y navegador:

```
poetry install
poetry run playwright install chromium
```

2) Ejecutar (headed para revisar):

```
poetry run telus-compare-audio --headed --delay-seconds 1 --strict
```

Parámetros comunes: `--max-iters`, `--delay-seconds`, `--log-file`, `--manual-login`, `--iter-timeout`.
