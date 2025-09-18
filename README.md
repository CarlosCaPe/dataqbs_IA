# dataqbs_IA

Este repositorio ahora contiene dos proyectos de Python bajo la misma carpeta:

- email_collector: Colección y clasificación de correos IMAP con exportación .eml.
- easybrokers: Utilidades y scripts para manejar datos de EasyBrokers.

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

## Uso (email_collector)

Con Poetry en la raíz del repo:

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

---

## Uso (easybrokers)

Entra a la carpeta `easybrokers` y usa Poetry para instalar dependencias y ejecutar scripts:

```powershell
cd easybrokers
poetry install
poetry run python test_download.py
```

También puedes usar tareas y configuraciones de VS Code:

- Tareas (Terminal > Run Task):
	- Email Collector: Install deps
	- Precheck run
	- Email Collector: Full run
	- EasyBrokers: Install deps
	- EasyBrokers: Run test_download.py

- Debug (Run and Debug):
	- Email Collector (precheck)
	- Email Collector (run)
	- EasyBrokers: test_download.py
	- EasyBrokers: image_downloader.py

Sugerencia: abre el archivo `dataqbs_IA.code-workspace` para ver ambos proyectos como carpetas del mismo workspace.

### Autenticación OAuth para Hotmail/Outlook

Si el login IMAP básico falla en Hotmail/Outlook, el proyecto soporta fallback a OAuth (XOAUTH2) usando MSAL (device code flow):

1. Registra una app en Entra ID (Azure AD) como Public client/native.
2. Copia el Application (client) ID en tu `.env` como `MSAL_CLIENT_ID`.
3. Agrega el permiso API `IMAP.AccessAsUser.All` (URI: `https://outlook.office.com/IMAP.AccessAsUser.All`) y concédelo.
4. Opcional: `MSAL_TENANT=consumers` (cuentas personales) o `common`/tu tenant.
5. En `.env` define:
	- `HOTMAIL_AUTH=oauth` (o `auto` para intentar basic y luego OAuth)
	- `HOTMAIL_USER=tu_correo@hotmail.com`
	- (Con OAuth, `HOTMAIL_PASS` es opcional.)

En el primer uso se mostrará un mensaje con URL y código para autorizar. El token se cachea en `~/.email_collector/msal_hotmail_token.json`.
