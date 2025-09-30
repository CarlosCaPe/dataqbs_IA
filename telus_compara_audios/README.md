# telus_compara_audios

Automatiza la tarea "Audio Quality Compare" en Multimango usando métricas de red (Chrome DevTools Protocol).

- URL de tarea: https://www.multimango.com/tasks/080825-audio-quality-compare
- Compara archivos .wav A y B contra Reference usando tamaño (kB) y tiempo de carga (ms)
- Soporta modo headed/headless, login manual, contador por iteración y límites con `--max-iters`

## Método de Comparación

El script utiliza **Chrome DevTools Protocol (CDP)** para capturar métricas de red de los archivos .wav:

1. **Captura de métricas**: Intercepta las peticiones de red para los 3 archivos .wav
2. **Extracción de datos**: 
   - Tamaño del archivo (kB) desde Content-Length header
   - Tiempo de carga (ms) desde timestamps de CDP
3. **Mapeo de archivos**: En orden de carga → A, B, Reference
4. **Decisión**: Compara A y B contra Reference usando distancia normalizada:
   - Distancia = 70% × |tamaño - ref_tamaño|/ref_tamaño + 30% × |tiempo - ref_tiempo|/ref_tiempo
   - Elige la versión con menor distancia
   - Declara "Tie" si la diferencia es ≤ 0.001

## Uso rápido

1) Instala dependencias y navegador:

```bash
poetry install
poetry run playwright install chromium
```

2) Ejecutar (headed para revisar):

```bash
poetry run python -m telus_compara_audios.runner --headed --max-iters 3 --manual-login
```

## Parámetros

- `--headed`: Abrir navegador con UI (para debug)
- `--max-iters N`: Límite de iteraciones (0 = ilimitado)
- `--delay-seconds N`: Retardo entre iteraciones (default: 1)
- `--log-file PATH`: Ruta del archivo de log
- `--manual-login`: Esperar login manual (hasta 3 minutos)
- `--iter-timeout N`: Timeout por iteración en segundos (default: 30)
- `--tie-threshold F`: Umbral para declarar Tie (default: 0.001)
- `--audit-csv PATH`: Guardar decisiones en CSV
- `--use-chrome`: Usar canal Chrome del sistema
- `--no-persistent`: No usar perfil persistente

## Ejemplos

### Modo headed con 3 iteraciones:
```bash
poetry run python -m telus_compara_audios.runner --headed --max-iters 3 --manual-login
```

### Modo headless con logs:
```bash
poetry run python -m telus_compara_audios.runner --max-iters 10 --log-file logs/run.log
```

### Con auditoría CSV:
```bash
poetry run python -m telus_compara_audios.runner --max-iters 5 --audit-csv logs/decisions.csv
```

## Salida de Logs

El script muestra logs como:

```
2025-09-30 12:00:00,000 INFO Iteración 1/3
2025-09-30 12:00:03,000 INFO CDP Network -> Reference: 292.0kB/469ms, A: 245.0kB/518ms, B: 254.0kB/550ms
2025-09-30 12:00:03,100 INFO Distancia normalizada -> A: 0.1440, B: 0.1429
2025-09-30 12:00:03,200 INFO Decisión basada en Network: Version B
```

## Notas

- El script requiere acceso a la tarea de Multimango (login puede ser necesario)
- Usa `--manual-login` y `--headed` para sesiones interactivas
- El orden de carga de .wav es: A, B, Reference (según comportamiento observado)
- La decisión se basa únicamente en métricas de red, no en análisis de audio
