# Flowcast

Self-hosted audiogram generator para podcasts. Convierte episodios en videos 16:9 con forma de onda animada y los publica automáticamente en YouTube.

## Características

- **Multi-podcast**: gestiona varios podcasts, cada uno con su feed RSS y playlist de YouTube
- **Audiogramas 1920×1080** con forma de onda animada (FFmpeg)
- **Plantillas personalizables**: fondo, colores, posición de onda y título por podcast
- **Modo manual**: procesa episodios existentes uno a uno
- **Modo automático**: detecta nuevos episodios via RSS → descarga → renderiza → publica
- **Publicación en YouTube** con OAuth2 — asigna automáticamente la playlist del podcast
- **Autenticación**: login con usuario/contraseña + 2FA TOTP (Google Authenticator, Authy, 1Password)
- **Self-hosted**: corre en tu VPS con Docker

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

### 4. Configurar variables de entorno

```bash
cp .env.example .env
nano .env
```

Completá como mínimo:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
APP_BASE_URL=http://IP-DE-TU-VPS:8000
SECRET_KEY=una-clave-aleatoria-larga
ADMIN_USERNAME=tu-usuario
ADMIN_PASSWORD=una-contraseña-segura
```

### 5. Arrancar

```bash
docker compose up -d
```

Accedé a `http://IP-DE-TU-VPS:8000`.

Para ver los logs:
```bash
docker compose logs -f flowcast
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

Flowcast protege toda la interfaz con usuario/contraseña + TOTP (autenticación de dos factores).

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
2. Crea un proyecto nuevo (p.ej. "Flowcast")
3. En el menú izquierdo: **APIs y servicios → Biblioteca**
4. Busca **YouTube Data API v3** y actívala

### Paso 2: Crear credenciales OAuth2

1. Ve a **APIs y servicios → Credenciales**
2. Click en **Crear credenciales → ID de cliente OAuth 2.0**
3. Tipo de aplicación: **Aplicación web**
4. En "URI de redireccionamiento autorizados", agrega:
   ```
   https://tu-dominio.com/auth/youtube/callback
   ```
5. Descarga el JSON o copia el **Client ID** y **Client Secret**
6. Agrégalos a tu `.env`:
   ```env
   GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-...
   ```

### Paso 3: Conectar en la UI

1. Ve a `/settings` en Flowcast
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

Si actualizás Flowcast y hay cambios en el schema de la DB:

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
- Cada 60 minutos Flowcast revisa el feed
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
| `RSS_FEED_URL` | — | URL del feed RSS del podcast (requerido) |
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
├── models/              # ORM: Episode, Template, RenderJob
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
│   └── escape.py        # Escape seguro para drawtext
└── auth/
    ├── session.py       # Cookie de sesión firmada (itsdangerous)
    ├── totp.py          # TOTP 2FA (pyotp + qrcode)
    └── youtube_oauth.py # OAuth2 flow para YouTube
```

---

## Pipeline FFmpeg

Cada audiograma usa un único comando FFmpeg con `-filter_complex`:

1. **Input 0**: imagen de fondo (loop infinito con `-loop 1`)
2. **Input 1**: archivo MP3
3. `showwaves` convierte el audio en video de forma de onda animada
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

## Producción con HTTPS

1. Descomenta el servicio `nginx` en `docker-compose.yml`
2. Configura `nginx.conf` con tu dominio
3. Obtén certificado con Certbot:
   ```bash
   docker run --rm -v ./data/certbot:/etc/letsencrypt certbot/certbot certonly \
     --standalone -d tu-dominio.com
   ```
4. Actualiza `APP_BASE_URL=https://tu-dominio.com` en `.env`
5. Actualiza el URI de callback en Google Cloud Console
