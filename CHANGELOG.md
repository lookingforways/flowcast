# Changelog

Todos los cambios notables de este proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versionado semántico: MAJOR.MINOR.PATCH

---

## [0.6.7] — 2026-04-05

### Seguridad
- **Eliminado `innerHTML` de `episodes.js`**: reemplazado con DOM methods (`createElement`, `appendChild`, `textContent`) — patrón seguro por diseño, imposible de convertirse en vector XSS aunque el código cambie en el futuro
- **Eliminado `innerHTML` de `podcasts.html`**: mismo fix para el botón de spinner de "Revisar feed"

---

## [0.6.6] — 2026-04-05

### Seguridad
- **XSS en `showToast`**: reemplazado `innerHTML` con `textContent` para el mensaje, y el botón de cierre ahora se crea programáticamente con `addEventListener` — elimina vector de inyección HTML y cumple CSP sin `onclick` inline
- **API devuelve 401**: el middleware de auth ahora devuelve `{"detail":"No autenticado"}` con status 401 para rutas `/api/*` en vez de redirigir a login HTML — evita que `fetch()` reciba HTML inesperado en sesiones expiradas
- **`minlength="8"`** en campo de contraseña del login (validación client-side)

---

## [0.6.5] — 2026-04-05

### Añadido
- **`security.txt`** (`/.well-known/security.txt`): generado dinámicamente — `Contact` apunta a `support@lookingforways.com`, `Scope` usa `APP_BASE_URL` del entorno (se adapta a cualquier dominio de despliegue), `Expires` siempre 1 año desde el momento del request

---

## [0.6.4] — 2026-04-05

### Seguridad / Hardening
- **`/health` requiere autenticación**: removido de rutas públicas — solo accesible con sesión activa
- **`robots.txt`**: endpoint público que devuelve `Disallow: /` — bloquea indexación a todos los bots
- **HSTS max-age a 2 años**: aumentado de 31,536,000 a 63,072,000 segundos (recomendación OWASP/Mozilla Observatory)
- **404 real**: rutas inexistentes para usuarios autenticados devuelven HTTP 404 en lugar de redirigir a `/`
- **`/.well-known/` público**: preparado para security.txt

### Accesibilidad
- **ARIA en alertas de error**: añadidos `role="alert"` y `aria-live="assertive"` al div de error en login y 2FA — los lectores de pantalla anuncian el error automáticamente
- **`<noscript>`** en login: mensaje informativo cuando JS está deshabilitado

### UI
- **Favicon real**: se sirve `/favicon.ico` correctamente desde `app/static/favicon.ico`
- **`<link rel="icon">`** declarado explícitamente en base.html, login.html y totp_verify.html

---

## [0.6.3] — 2026-04-05

### Seguridad — CSP style-src completamente endurecida
- **Eliminado `unsafe-inline` de `style-src`**: Bootstrap JS era el responsable de setear estilos inline dinámicamente en modales y acordeón, requiriendo `unsafe-inline`. Al eliminarlo desaparece el único motivo para permitirlo.
- **Eliminado Bootstrap JS** (`bootstrap.bundle.min.js`): removido del bundle. Solo se mantiene Bootstrap CSS (estilos estáticos, sin riesgo).
- **Modales → `<dialog>` nativo**: los 5 modales (podcasts ×3, episodios ×1, plantillas ×1) se reemplazaron con el elemento HTML nativo `<dialog>` que usa `showModal()`/`close()` — no toca `element.style` en absoluto.
- **Acordeón → `<details>`/`<summary>` nativo**: el acordeón de trabajos de render reemplazado con elementos HTML nativos.
- **Inline `style="..."` eliminados de todas las templates**: 10 atributos de estilo inline convertidos a clases CSS en `app.css`.
- **`showToast` arreglado**: eliminado `el.style.cssText`, reemplazado con clase CSS `.fc-toast`.
- **`episodes.js` arreglado**: `row.style.display` reemplazado con `classList.toggle('d-none', ...)`.
- **CSP final**: `script-src 'self' 'nonce-{nonce}'` y `style-src 'self' 'nonce-{nonce}' cdn.jsdelivr.net` — sin `unsafe-inline` en ninguna directiva.

---

## [0.6.2] — 2026-04-05

### Seguridad
- **Headers Cross-Origin**: añadidos `Cross-Origin-Opener-Policy: same-origin` y `Cross-Origin-Resource-Policy: same-origin` — protegen contra ataques side-channel (Spectre) entre orígenes
- **CSRF expirado**: en lugar de devolver JSON 400 al usuario, redirige a `/login` (o `/2fa`) con flash message "Sesión expirada. Intentá de nuevo." — mejor UX y sin exponer detalles técnicos

### Corregido
- **`Cache-Control: no-store`** en `/health` — evita que proxies intermedios cacheen la respuesta de disponibilidad

### Performance
- **Compresión HTTP**: habilitado `gzip` y `zstd` en Caddy para respuestas HTML/JSON

---

## [0.6.1] — 2026-04-05

### Corregido
- **CSRF roto en producción**: el browser pedía `/favicon.ico` automáticamente, el middleware lo redirigía a `/login`, generando un nuevo token CSRF que sobreescribía la cookie — el form ya cargado tenía el token viejo y fallaba. Fix: reusar el token existente si es válido; agregar `/favicon.ico` a rutas públicas
- **CSP ignorado**: el Caddyfile tenía un CSP estático que sobreescribía el CSP dinámico (con nonces) de FastAPI. Eliminado el CSP del Caddyfile — FastAPI lo maneja exclusivamente

### Añadido
- **Proxy de imágenes** (`/api/img`): endpoint que descarga imágenes externas server-side con protección SSRF, allowlist de content-types y límite de 5 MB. Las imágenes externas (ej. avatar de YouTube) pasan por el proxy y `img-src` queda en `'self' data:` únicamente
- Avatar del canal de YouTube en configuración ahora se sirve vía proxy

---

## [0.6.0] — 2026-04-05

### Seguridad — hardening completo (auditoría externa)

#### Crítico
- **CSRF**: protección con patrón double-submit cookie usando itsdangerous — token firmado en cookie httponly + campo oculto en formulario, verificado en POST a `/login` y `/2fa`; token inválido devuelve 400 explícito
- **CSP `script-src`**: eliminado `'unsafe-inline'` y `cdn.jsdelivr.net`; Bootstrap JS permitido solo por su hash SHA-384; scripts inline requieren nonce generado por request
- **CSP bypass CDN**: ya no se permite cargar scripts arbitrarios desde jsdelivr.net

#### Alto
- **Nonces CSP**: nonce único por request (`secrets.token_hex(16)`) inyectado en todos los `<script>` y `<style>` inline en los 11 templates afectados
- **Nuevas directivas CSP**: `base-uri 'none'`, `form-action 'self'`, `object-src 'none'`, `upgrade-insecure-requests`
- **Headers de seguridad en FastAPI**: middleware propio aplica todos los headers (HSTS via Caddy, X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy, Permissions-Policy) — funciona independiente de Caddy

#### Medio
- **Cache-Control**: `no-store, no-cache, must-revalidate` en respuestas de `/login` y `/2fa`
- **Body size limit**: máximo 2 KB en POST a `/login` y `/2fa`, rechazado en middleware antes de leer el body
- **Rate limit en `/health`**: 30 req/minuto
- **`Retry-After: 60`** en respuestas 429

#### Bajo / Hardening general
- **Headers `server` y `via`** eliminados de todas las respuestas
- **Flash messages**: errores de login/2FA via cookie httponly en lugar de query string (`?error=...`)
- **SRI**: atributos `integrity` y `crossorigin="anonymous"` en Bootstrap CSS, Bootstrap Icons CSS y Bootstrap JS
- **Error handlers**: `RequestValidationError` → 400 genérico; `HTTPException` → mensaje genérico (no expone estructura de FastAPI ni nombres de campos)
- **OpenAPI/Swagger deshabilitados**: `openapi_url=None`, `docs_url=None`, `redoc_url=None`
- **Inputs de login**: `maxlength` en HTML (150/256) + validación en backend; placeholder `"admin"` → `"Usuario"`; labels vinculadas con `for`/`id`
- **Meta robots**: `noindex, nofollow` en página de login
- **Mensaje rate limit**: genérico, no expone la configuración exacta

---

## [0.5.3] — 2026-04-01

### Añadido
- Modal de confirmación con checkbox al eliminar un podcast, reemplaza el `confirm()` nativo del browser
- Sección de stack tecnológico y arquitectura en el README

### Corregido
- Al eliminar un podcast se borran también los RenderJobs asociados y los archivos MP3/MP4 del disco
- Mensaje de confirmación de borrado actualizado: indica que los videos de YouTube permanecen en el canal

---

## [0.5.2] — 2026-03-31

### Añadido
- Los videos subidos a YouTube incluyen la fecha de publicación original del episodio en la descripción ("Publicado originalmente el 20 de diciembre de 2025")
- Se envía `recordingDetails.recordingDate` con la fecha original del episodio como metadato de YouTube

---

## [0.5.1] — 2026-03-31

### Corregido
- Auto-pipeline ahora también procesa episodios que quedaron en estado `discovered` sin avanzar (ej. detectados cuando `FLOWCAST_AUTO_PUBLISH` estaba desactivado)

---

## [0.5.0] — 2026-03-31

### Añadido
- Renderizador de forma de onda en Python (`app/ffmpeg/waveform.py`): análisis FFT con numpy, barras simétricas con bordes redondeados y efecto glow renderizadas con Pillow — reemplaza `showwaves` de FFmpeg para resultados de calidad profesional

### Corregido
- Publicación en YouTube: errores en background tasks ya no se pierden silenciosamente — se loguean y el episodio pasa a estado `failed`
- Descripción del episodio: se eliminan tags HTML y caracteres de control antes de enviar a YouTube API (evitaba error `invalidDescription`)
- Upload de YouTube ejecutado en thread separado para no bloquear el event loop
- Parámetros numéricos de plantilla (ej. `title_x`) ahora aceptan expresiones FFmpeg como `(w-text_w)/2` además de enteros
- Scope OAuth de YouTube ampliado para incluir gestión de playlists (`youtube` scope completo)
- Relación `episode.podcast` usa `lazy="selectin"` para compatibilidad con SQLAlchemy async (evitaba Internal Server Error en `/episodes`)
- Al eliminar un podcast se eliminan en cascada todos sus episodios
- Eliminado modo de onda `cbuffer` (no válido en FFmpeg) del editor de plantillas

### Dependencias nuevas
- `numpy>=1.26.0` — análisis FFT para el renderizador de forma de onda

---

## [0.4.0] — 2026-03-30

### Seguridad — CRÍTICO
- Validación de credenciales al arrancar: la app falla explícitamente si `SECRET_KEY` o `ADMIN_PASSWORD` usan los valores default inseguros
- Protección SSRF en fetch de RSS: `validate_external_url()` bloquea esquemas no-HTTP y rangos de IP privados/reservados antes de hacer cualquier request saliente
- Protección SSRF en descarga de MP3: misma validación aplicada antes de descargar el audio del episodio
- Los mensajes de error en respuestas de API ya no exponen detalles internos (paths, stacktraces, tokens)

### Seguridad — ALTO
- Rate limiting en `/login`: máximo 5 intentos por minuto por IP (slowapi)
- Cookie de sesión con flag `Secure` activado automáticamente cuando `APP_BASE_URL` usa HTTPS
- Token de YouTube cifrado en disco con Fernet (AES-128-CBC) derivando la clave del `SECRET_KEY`; migración automática de tokens en formato JSON plano al formato cifrado

### Seguridad — MEDIO/BAJO
- `_safe_unlink()` en templates y episodios: previene eliminación de archivos fuera de los directorios permitidos (path traversal)
- Parámetros numéricos de plantilla clamped antes de pasarse al filtro FFmpeg (previene inyección en filter_complex)
- `/health` ya no expone la versión de la app
- Validación de longitud y esquema URL en schemas de podcast (Pydantic)
- Timeout de 5 segundos en conexiones SQLite
- CORS explícitamente configurado (sin origenes permitidos)

### Dependencias nuevas
- `slowapi==0.1.9` — rate limiting
- `cryptography>=43.0.0` — cifrado Fernet para tokens

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
