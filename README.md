# dataqbs_IA / email_collector

Colección y clasificación de correos IMAP con exportación .eml.

## Configuración de entorno

1) Crea un archivo `.env` en la raíz (ya agregado) con credenciales:

```
# === GMAIL cacp18 ===
GMAIL1_USER=cacp18@gmail.com
GMAIL1_PASS=APP_PASSWORD_GMAIL_CACP18

# === HOTMAIL cacp18 ===
HOTMAIL_USER=cacp18@hotmail.com
HOTMAIL_PASS=PASSWORD_HOTMAIL

# === GMAIL dataqbs (Carlos) ===
GMAIL2_USER=carlos.carrillo@dataqbs.com
GMAIL2_PASS=APP_PASSWORD_GMAIL_DATAQBS

# Opcional: seleccionar cuenta por defecto
# EMAIL_ACCOUNT=gmail1
```

2) Ajusta `config.yaml` para reglas de clasificación/validación. IMAP host/port/carpeta se pueden sobreescribir por variables de entorno `IMAP_HOST`, `IMAP_PORT`, `IMAP_FOLDER`.

## Uso

Con Poetry:

```powershell
poetry install
poetry run email-collect --precheck --account gmail1
poetry run email-collect --account hotmail
```

También puedes fijar la cuenta vía variable:

```powershell
$env:EMAIL_ACCOUNT = "gmail2"
poetry run email-collect --precheck
```

Resultados:
- EML y reportes JSON en la carpeta configurada (`emails_out` por defecto).

## Notas
- Gmail requiere contraseña de aplicación si 2FA está habilitado.
- Para Hotmail/Outlook se usa `outlook.office365.com` con IMAPS (993).
