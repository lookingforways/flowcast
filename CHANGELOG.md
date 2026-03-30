# Changelog

Todos los cambios notables de este proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versionado semántico: MAJOR.MINOR.PATCH

---

## [0.3.1] — 2026-03-30

### Corregido
- Middleware de autenticación no interceptaba las requests (BaseHTTPMiddleware no funciona con el stack async de FastAPI + StaticFiles)
- Reemplazado por decorador `@app.middleware("http")` directamente en `main.py`
- Confirmado funcionando en producción (VPS 2 cores / 4GB RAM)

---

## [0.3.0] — 2026-03-30

### Añadido
- Autenticación con formulario de login propio (usuario + contraseña)
- 2FA con TOTP (Google Authenticator, Authy, 1Password, etc.)
- Primer login muestra QR para vincular la app de autenticación
- Cookie de sesión firmada con `itsdangerous` (7 días de duración)
- Auto-submit del código 2FA al ingresar 6 dígitos
- Botón de logout en el navbar
- Variables `ADMIN_USERNAME` y `ADMIN_PASSWORD` en `.env`
- Secreto TOTP generado automáticamente en `data/tokens/totp_secret.txt`

---

## [0.2.1] — 2026-03-30

### Notas de la primera puesta en producción
- Primer render exitoso en VPS 2 cores / 4GB RAM
- Tiempo de render ~15-20 min por episodio de 20 min en VPS de 2 cores
- Feed RSS debe ser la URL directa del feed (no la URL del perfil del podcast)
- Al actualizar schema de DB es necesario eliminar `data/db/flowcast.db` para que se recree

---

## [0.2.0] — 2026-03-29

### Añadido
- Soporte multi-podcast: cada podcast tiene su propio feed RSS y playlist de YouTube
- Tabla `podcasts` con nombre, feed URL, playlist ID y plantilla por defecto
- Página de gestión de podcasts (`/podcasts`) con alta, edición y polling manual
- Filtro de episodios por podcast en `/episodes`
- Publicación automática asigna el video a la playlist del podcast correspondiente
- Scheduler ahora pollea todos los podcasts activos (en lugar de un único feed global)

### Cambiado
- `RSS_FEED_URL` en `.env` ya no es necesario (los feeds se gestionan en la DB)
- Dashboard muestra contador de podcasts
- Settings simplificado: feeds RSS gestionados desde la página de Podcasts

---

## [0.1.0] — 2026-03-29

### Añadido
- Pipeline FFmpeg: audiogramas 1920×1080 con forma de onda animada (`showwaves`)
- Sistema de plantillas: fondo personalizable, colores, posición de onda y título
- Editor de plantillas con vista previa en canvas (tiempo real)
- Parseo de feed RSS con detección automática de nuevos episodios
- Descarga streaming de MP3
- Publicación en YouTube via OAuth2 (YouTube Data API v3)
- Modo manual: descargar → renderizar → publicar por episodio
- Modo automático: pipeline completo al detectar nuevos episodios en el feed
- Dashboard web con estadísticas y estado de trabajos
- APScheduler para polling del feed (intervalo configurable)
- Limpieza automática de renders antiguos
- Deploy con Docker Compose (Ubuntu 24.04 x86)

### Pendiente
- Autenticación básica (login) para proteger el acceso
- Mejoras de diseño en el dashboard
- Configuración de RSS feed y plantilla por defecto

---
