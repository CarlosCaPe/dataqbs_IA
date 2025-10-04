# telus_compara_imagenes

Automatiza la tarea "Image Quality Compare" (Side by Side) en Multimango.

- Abre Chrome/Chromium con Playwright (reutiliza sesión si existe)
- Navega a https://www.multimango.com/tasks/081925-image-quality-compare
- Selecciona "Side by Side"
- En cada iteración: compara A vs B mediante una métrica de nitidez (Laplaciano) y decide A/B/Tie
- Aplica un retardo humano (~30s por foto, configurable)
- Envía la evaluación y avanza hasta que el sitio no responda
- Muestra un contador en pantalla por iteración ("Iteración X/Y"; Y es '?' si no se definió `--max-iters`)
- Lleva contador de iteraciones y tiempo total en un log y en stdout

## Uso rápido

1) Instalar dependencias y navegador:

```
poetry install
poetry run playwright install chromium
```

2) Ejecutar (headed, para revisar):

```
poetry run telus-compare --headed --delay-seconds 30
```

3) Headless (cuando ya funcione):

```
poetry run telus-compare --delay-seconds 30
```

Parámetros útiles:
- `--max-iters N` para limitar iteraciones
- `--delay-seconds S` para simular ritmo humano (default 30)
- `--log-file ruta.log` para guardar logs

Nota: Si el sitio requiere login, inicia una vez en modo `--headed`. La sesión se guardará automáticamente.