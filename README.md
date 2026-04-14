# FlowCast

Self-hosted audiogram generator para podcasts. Convierte episodios en videos 16:9 con forma de onda animada y los publica automáticamente en YouTube.

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.12 |
| Web framework | FastAPI |
| Templates HTML | Jinja2 + Design System Adwaita (theme.css — CSS custom properties) + APIs nativas del browser |
| Base de datos | SQLite (SQLAlchemy async + aiosqlite) |
| Tareas programadas | APScheduler |
| Procesamiento de video | FFmpeg |
| Análisis de audio / waveform | numpy + Pillow |
| Autenticación | itsdangerous (sesión) + pyotp (2FA TOTP) |
| YouTube API | google-api-python-client (OAuth2) |
| Deploy | Docker + Docker Compose + Caddy (HTTPS) |

### Arquitectura

```
Browser
  │
  ├── GET /episodes, /podcasts, /templates …
  │     └── FastAPI → Jinja2 renderiza HTML completo → respuesta al browser
  │
  └── fetch() /api/episodes/24/render, /api/podcasts …
        └── FastAPI → JSON response → JS actualiza la UI
```

Las páginas cargan con datos del servidor (server-rendered). Las interacciones dinámicas (crear, editar, borrar, renderizar) usan `fetch()` a la API REST `/api/*` sin recargar la página. No hay framework JS — todo es vanilla JS dentro de los templates Jinja2.

---

## Características

- **Multi-podcast**: gestiona varios podcasts, cada uno con su feed RSS y playlist de YouTube
- **Audiogramas 1920×1080** con forma de onda animada (FFmpeg)
- **Plantillas personalizables**: fondo, colores, posición de onda y título por podcast
- **Modo manual**: procesa episodios existentes uno a uno
- **Modo automático**: detecta nuevos episodios via RSS → descarga → renderiza → publica
- **Publicación en YouTube** con OAuth2 — asigna automáticamente la playlist del podcast
- **Autenticación**: login con usuario/contraseña + 2FA TOTP (Google Authenticator, Authy, 1Password)
- **Progreso en tiempo real**: barras de progreso para descarga, render (waveform + FFmpeg) y publicación en YouTube — persisten al recargar la página
- **Self-hosted**: corre en tu VPS con Docker

---

## Seguridad

FlowCast ha pasado por 4 rondas de auditoría externa activa. Score final: **92/100**.

| Área | Implementación |
|------|---------------|
| Autenticación | Usuario + contraseña + TOTP 2FA obligatorio |
| CSRF | Double-submit cookie con token firmado (itsdangerous); token reutilizado si válido (evita invalidación por favicon) |
| Sesión | Cookie httponly, SameSite=Lax, Secure (en HTTPS), firmada con itsdangerous |
| Headers HTTP | HSTS 2 años, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, COOP, CORP — aplicados a **todas** las respuestas |
| CSP | Nonce único por request; sin `unsafe-inline` en ninguna directiva; Bootstrap JS eliminado |
| Sin CDN externo | Phosphor Icons y Cantarell servidos localmente — `style-src` y `font-src` solo desde `'self'` |
| JS sin `innerHTML` | Todo el código JS usa `textContent` + DOM methods — sin superficie de XSS DOM-based |
| Sanitización HTML | Descripciones RSS sanitizadas con `nh3` (ammonia) antes de guardar en DB — allowlist estricto de tags seguros; `html_to_text()` convierte a texto estructurado para YouTube |
| Archivos estáticos | `/static/img/` requiere autenticación. `/static/css/` y `/static/js/` son públicos (solo contienen el design system visual, no lógica de negocio) |
| Rate limiting | 5 req/minuto en `/login` (por IP); `/health` requiere autenticación |
| SSRF | Validación de URLs externas (IP privadas bloqueadas) antes de fetch RSS y descarga de MP3 |
| Proxy de imágenes | `/api/img` descarga imágenes externas server-side con allowlist de content-types y límite 5 MB |
| Tokens YouTube | Cifrados en disco con Fernet (AES-128-CBC) derivando clave del `SECRET_KEY` |
| Credenciales | La app no arranca si `SECRET_KEY` o `ADMIN_PASSWORD` usan valores por defecto |
| Robots | `robots.txt` con `Disallow: /` — ningún bot indexa nada |
| Divulgación responsable | `/.well-known/security.txt` (RFC 9116) con contacto, expiración y scope |
| Sin JS externo | Bootstrap JS eliminado; modales con `<dialog>` nativo, acordeón con `<details>` — cero dependencias JS de CDN |

---

## Deploy en VPS (Ubuntu 24.04 x86)

### 1. Instalar Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Agregar SSH key del VPS a GitHub

```bash
ssh-keygen -t ed25519 -C "flowcast-vps"
cat ~/.ssh/id_ed25519.pub
```

Copiá la clave pública y agrégala en GitHub: **Settings → SSH and GPG keys → New SSH key**.

### 3. Clonar el repositorio

```bash
git clone git@github.com:lookingforways/flowcast.git
cd flowcast
```

### 4. Apuntar el dominio al VPS

En tu registrador de dominio, crea un registro DNS tipo `A`:
```
tu-dominio.com  →  IP-DE-TU-VPS
```

Esperá a que propague (generalmente 1-5 minutos con TTL bajo).

### 5. Configurar variables de entorno

```bash
cp .env.example .env
nano .env
```

Completá como mínimo:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
APP_BASE_URL=https://tu-dominio.com
SECRET_KEY=una-clave-aleatoria-larga
ADMIN_USERNAME=tu-usuario
ADMIN_PASSWORD=una-contraseña-segura
```

### 6. Arrancar

```bash
docker compose up -d
```

Caddy obtiene el certificado TLS automáticamente en el primer arranque.
Accedé a `https://tu-dominio.com` (HTTP redirige a HTTPS automáticamente).

> **Nota**: los puertos 80 y 443 deben estar abiertos en el firewall del VPS.

Para ver los logs:
```bash
docker compose logs -f flowcast
docker compose logs -f caddy     # logs de Caddy / TLS
```

Para actualizar cuando haya cambios:
```bash
git pull && docker compose up -d --build
```

---

## Inicio rápido (desarrollo local)

### 1. Clonar y configurar

```bash
git clone <tu-repo> flowcast
cd flowcast
cp .env.example .env
```

Edita `.env` con tus valores:

```env
RSS_FEED_URL=https://tu-podcast.com/feed.xml
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret
APP_BASE_URL=https://tu-dominio.com   # o http://localhost:8000 para desarrollo
```

### 2. Levantar con Docker

```bash
docker compose up -d
```

Accede a `http://localhost:8000` (o tu dominio).

---

## Autenticación y 2FA

FlowCast protege toda la interfaz con usuario/contraseña + TOTP (autenticación de dos factores).

### Primer acceso

1. Accedé a la app — serás redirigido a `/login`
2. Ingresá el usuario y contraseña definidos en `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`)
3. En el primer login verás un **código QR** — escanealo con tu app de autenticación (Google Authenticator, Authy, 1Password, etc.)
4. Ingresá el código de 6 dígitos que aparece en la app
5. A partir de ese momento cada login pedirá usuario/contraseña + código TOTP

> El secreto TOTP se guarda en `data/tokens/totp_secret.txt`. Si perdés el acceso al autenticador, eliminá ese archivo y volvé a escanear el QR en el próximo login.

---

## Configurar YouTube

### Paso 1: Crear proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto nuevo (p.ej. "FlowCast")
3. En el menú izquierdo: **APIs y servicios → Biblioteca**
4. Busca **YouTube Data API v3** y actívala

### Paso 2: Configurar pantalla de consentimiento OAuth

1. Ve a **APIs y servicios → Pantalla de consentimiento de OAuth**
2. Tipo de usuario: **Externo** → **Crear**
3. Completá los campos obligatorios (nombre de la app, correo de asistencia, correo del desarrollador)
4. En **Usuarios de prueba**, agregá tu cuenta de Google
5. Guardá y continuá hasta el final

> Este paso es obligatorio antes de crear las credenciales OAuth.

### Paso 3: Crear credenciales OAuth2

1. Ve a **APIs y servicios → Credenciales**
2. Click en **Crear credenciales → ID de cliente OAuth 2.0**
3. Tipo de aplicación: **Aplicación web**
4. En **"Orígenes autorizados de JavaScript"**, agrega:
   ```
   https://tu-dominio.com
   ```
5. En **"URIs de redireccionamiento autorizados"**, agrega:
   ```
   https://tu-dominio.com/auth/youtube/callback
   ```
6. Descarga el JSON o copia el **Client ID** y **Client Secret**
6. Agrégalos a tu `.env`:
   ```env
   GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-...
   ```

### Paso 4: Conectar en la UI

1. Ve a `/settings` en FlowCast
2. Click en **Conectar con YouTube**
3. Autoriza el acceso con tu cuenta de Google

---

## Agregar podcasts

1. Ve a `/podcasts` → **Agregar podcast**
2. Completá nombre, URL del feed RSS y opcionalmente la Playlist ID de YouTube
3. Click en **Revisar feed** para importar los episodios existentes

> **Importante**: la URL del feed debe ser la URL directa del RSS (termina en `.rss`, `.xml` o similar), no la URL del perfil del podcast en la plataforma.

---

## Rendimiento de render

| VPS | Episodio 20 min | Episodio 60 min |
|-----|----------------|----------------|
| 2 cores / 4GB | ~15-20 min | ~45-60 min |
| 4 cores / 8GB | ~8-10 min | ~20-25 min |

El render usa todos los cores disponibles. Se recomienda procesar episodios en lotes fuera del horario de publicación.

---

## Actualizar schema de base de datos

Si actualizás FlowCast y hay cambios en el schema de la DB:

```bash
rm ~/flowcast/data/db/flowcast.db
docker compose restart flowcast
```

> Esto borra todos los datos. Hacelo solo en instalaciones nuevas o cuando se indique explícitamente en el CHANGELOG.

---

## Uso manual (episodios existentes)

1. Ve a `/episodes` — verás los episodios descubiertos del feed
2. Filtrá por podcast si tenés varios
3. Para cada episodio que quieras procesar:
   - Click en **Descargar** → descarga el MP3
   - Click en **Crear Audiograma** → selecciona plantilla → renderiza
   - Click en **Publicar en YouTube** → sube el video

---

## Modo automático

En tu `.env`:

```env
FLOWCAST_AUTO_PUBLISH=true
POLL_INTERVAL_MINUTES=60
YOUTUBE_PRIVACY=public    # o unlisted / private
```

Reinicia el contenedor. A partir de ahora:
- Cada 60 minutos FlowCast revisa el feed
- Los nuevos episodios se descargan, renderizan y publican automáticamente

---

## Personalizar plantillas

1. Ve a `/templates` → **Nueva plantilla**
2. En el editor:
   - Sube una **imagen de fondo** (PNG/JPG 1920×1080 recomendado)
   - Sube tu **logo/watermark** (opcional)
   - Ajusta colores, posición y tamaño de la onda de audio
   - Ajusta posición y tamaño del título
   - Vista previa en tiempo real
3. Guarda y establece como plantilla predeterminada

---

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | — | OAuth2 Client ID de Google Cloud |
| `GOOGLE_CLIENT_SECRET` | — | OAuth2 Client Secret |
| `FLOWCAST_AUTO_PUBLISH` | `false` | Publicación automática al detectar nuevos eps |
| `POLL_INTERVAL_MINUTES` | `60` | Frecuencia de revisión del feed (minutos) |
| `YOUTUBE_PRIVACY` | `unlisted` | Privacidad: `public`, `unlisted`, `private` |
| `YOUTUBE_CATEGORY_ID` | `22` | Categoría YouTube (22 = Personas y blogs) |
| `MAX_RENDER_AGE_DAYS` | `30` | Días antes de limpiar MP4s del disco (0 = nunca) |
| `DATA_DIR` | `/app/data` | Directorio de datos (DB, descargas, renders) |
| `APP_BASE_URL` | `http://localhost:8000` | URL pública de la app (para OAuth2 callback) |
| `SECRET_KEY` | `change-me` | Clave secreta de sesión (¡cámbiala!) |
| `ADMIN_USERNAME` | `admin` | Usuario del panel de administración |
| `ADMIN_PASSWORD` | `change-me` | Contraseña del panel (¡cámbiala!) |
| `SESSION_MAX_AGE` | `604800` | Duración de la sesión en segundos (default: 7 días) |
| `LOG_LEVEL` | `INFO` | Nivel de log: DEBUG, INFO, WARNING, ERROR |

---

## Estructura del proyecto

```
app/
├── main.py              # FastAPI app
├── config.py            # Configuración via variables de entorno
├── database.py          # SQLite + SQLAlchemy async
├── models/              # ORM: Episode, Podcast, Template, RenderJob
├── schemas/             # Pydantic schemas
├── routers/             # API endpoints + páginas web
├── services/
│   ├── rss.py           # Parseo de feed RSS
│   ├── downloader.py    # Descarga de MP3
│   ├── renderer.py      # Orquestador del pipeline
│   ├── publisher.py     # YouTube Data API
│   └── scheduler.py     # APScheduler (polling automático)
├── ffmpeg/
│   ├── pipeline.py      # Construcción y ejecución del comando FFmpeg
│   ├── waveform.py      # Renderizador Python de forma de onda (FFT + Pillow)
│   └── escape.py        # Escape seguro para drawtext
├── utils/
│   ├── url_validator.py # Validación anti-SSRF para URLs externas
│   └── html_sanitizer.py # sanitize_html() + html_to_text() para descripciones RSS
└── auth/
    ├── session.py       # Cookie de sesión firmada (itsdangerous)
    ├── totp.py          # TOTP 2FA (pyotp + qrcode)
    ├── limiter.py       # Rate limiter (slowapi)
    └── youtube_oauth.py # OAuth2 flow para YouTube (token cifrado con Fernet)
```

---

## Pipeline de render

El render tiene dos fases:

### Fase 1 — Generación de forma de onda (Python)
`app/ffmpeg/waveform.py` analiza el audio con FFT (numpy), calcula la amplitud por bandas de frecuencia para cada frame y renderiza barras simétricas con bordes redondeados y efecto glow usando Pillow. El resultado se guarda en un archivo MKV temporal con canal alpha.

### Fase 2 — Composición FFmpeg
FFmpeg compone las capas con `-filter_complex`:

1. **Input 0**: imagen de fondo (loop infinito con `-loop 1`)
2. **Input 1**: archivo MP3
3. **Input 2**: overlay de forma de onda (MKV generado en Fase 1)
4. `overlay` compone la onda sobre el fondo
5. `drawtext` superpone el título del episodio
6. `-shortest` detiene la codificación cuando termina el audio

Output: MP4 H.264/AAC, 1920×1080, 25fps, listo para YouTube.

---

## Prueba del pipeline

```bash
# En el contenedor o con las dependencias instaladas localmente:
python scripts/test_render.py
```

Genera un audio de 10 segundos con FFmpeg y renderiza un audiograma de prueba.

---

## Producción con HTTPS (Caddy)

Caddy está incluido en `docker-compose.yml` y maneja TLS automáticamente.

1. Asegurate de que el dominio apunta a la IP del VPS (registro DNS `A`)
2. Los puertos 80 y 443 deben estar abiertos en el firewall
3. Editá el `Caddyfile` con tu dominio:
   ```
   tu-dominio.com {
       reverse_proxy flowcast:8000
   }
   ```
4. Actualizá `APP_BASE_URL=https://tu-dominio.com` en `.env`
5. Actualizá el URI de callback en Google Cloud Console: `https://tu-dominio.com/auth/youtube/callback`
6. `docker compose up -d` — Caddy obtiene el certificado automáticamente

---

## Licencia

Copyright (c) 2026 **Looking for Ways LLC** — Todos los derechos reservados.

FlowCast se distribuye bajo la [PolyForm Noncommercial License 1.0.0](LICENSE).

| | |
|---|---|
| ✅ Uso personal y educativo | Permitido |
| ✅ Modificar y redistribuir | Permitido con atribución |
| ❌ Uso comercial | **Prohibido** |
| ❌ Vender o monetizar | **Prohibido** |
| ℹ️ Atribución | Obligatoria — debe indicar "Based on FlowCast by Looking for Ways LLC" |
| ℹ️ Garantía | Sin garantía de ningún tipo |

**"FlowCast"** es una marca registrada de Looking for Ways LLC. Los forks y derivados no pueden usar el nombre "FlowCast" como nombre de su producto sin permiso escrito.

Para licencias comerciales o consultas: [hello@lookingforways.com](mailto:hello@lookingforways.com)
