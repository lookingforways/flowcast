# Changelog

Todos los cambios notables de este proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versionado semántico: MAJOR.MINOR.PATCH

---

## [0.9.3] — 2026-04-07

### Agregado

**Barras de progreso en tiempo real**
- Las operaciones de descarga, render y publicación en YouTube muestran una barra de progreso en `/episodes` y en el detalle de episodio
- Render en dos fases: waveform Python 0→50%, encoding FFmpeg 50→100%
- FFmpeg reporta progreso parseando `time=HH:MM:SS.ss` de stderr leído en chunks — compatible con `\r` (carriage return) que usa FFmpeg cuando stderr es un pipe
- Progreso persiste si se recarga la página durante una operación activa
- Protección anti-doble publicación: HTTP 409 si ya hay un upload en curso para ese episodio

### Corregido

**Badges de estado en español**
- `/episodes` y `/episodes/{id}`: "discovered" → "Descubierto", "downloaded" → "Descargado", "rendered" → "Renderizado", "published" → "Publicado", "failed" → "Error"

**Barra de progreso — bugs**
- La barra desaparecía inmediatamente cuando el progreso era 0%: corregido con `_active: set[str]` en el store — `is_active()` distingue "activo al 0%" de "sin operación"
- El render se quedaba trabado al 50%: corregido leyendo stderr en chunks de 4096 bytes y splitteando en `\r` y `\n`
- Race condition entre primera encuesta y tarea en background: `set_progress()` se llama en el router ANTES de encolar la tarea

---

## [0.9.2] — 2026-04-07

### Seguridad

**Sanitización HTML de descripciones RSS**
- Las descripciones de episodios ahora se sanitizan con `nh3` (ammonia) al parsear el feed RSS, antes de guardar en DB — elimina XSS via contenido malicioso en feeds
- Allowlist estricto: solo `p`, `br`, `strong`, `em`, `a[href=http/https/mailto]`, `ul`, `ol`, `li`, `blockquote`, headings. Todo lo demás se borra
- El filtro Jinja2 `sanitize_html` se aplica también al mostrar — cubre episodios existentes en DB con HTML sin sanitizar
- `mp3_url` validado a `http/https` al parsear el RSS — bloquea esquemas `javascript:` y similares antes de que lleguen a la DB
- Nueva dependencia: `nh3>=0.2.17`

**YouTube embed (CSP)**
- Agregado `frame-src https://www.youtube.com` al CSP — los iframes de YouTube en el detalle de episodio ya no son bloqueados por el browser

### Corregido

**Descripciones en YouTube**
- `html_to_text()` reemplaza el strip de tags con regex — convierte el HTML sanitizado a texto plano estructurado: párrafos separados por línea en blanco, listas como `• item`, links como `texto (url)`, emails sin prefijo `mailto:`
- Las descripciones publicadas en YouTube ahora preservan la estructura legible del episodio original

**Estado de conexión YouTube**
- `is_connected()` ya no devuelve `True` cuando el token fue revocado pero no expiró localmente
- Al publicar con `invalid_grant` → se borra el archivo de token → sidebar y dashboard muestran "Desconectado" en el próximo page load
- Al refrescar el token con `invalid_grant` → mismo comportamiento
- Mensajes de error de publicación en español con contexto y pasos de acción:
  - `invalid_grant` → explica el vencimiento + pasos para reconectar + nota sobre modo Testing en Google Cloud
  - 403/quota → permisos o cuota
  - 401 → sin sesión activa
  - Archivo faltante → sugiere re-renderizar
  - Error genérico → incluye el mensaje original del sistema

**Tipografía**
- Font size base: `14px` → `17px` — el tamaño anterior (GTK nativo) era demasiado pequeño para web; 17px es cómodo sin necesitar zoom en el browser

**Dashboard**
- Eliminada la stat card de YouTube ("Conectado/Desconectado") — información redundante con el badge del sidebar

---

## [0.9.1] — 2026-04-06

### Corregido — polish UI post-rediseño

**Tema / colores**
- `prefers-color-scheme` ahora se sigue en tiempo real: listener `matchMedia('change')` en `app.js`, `login.html` y `totp_verify.html` — el tema cambia al instante cuando el sistema cambia, sin recargar la página. Solo actúa si no hay preferencia manual guardada en `localStorage`

**Botones — estilo Adwaita**
- Todos los botones son ahora **pill** (`border-radius: 9999px`) — diseño uniforme sin mezcla de estilos
- `btn-outline-*` ya no son transparentes: fondo tintado permanente en cada variante (azul, rojo, verde, amarillo, neutro) — alineado con el paradigma de botones de GNOME (siempre con fondo)
- `btn-group` preserva el aspecto de grupo — los botones dentro resetean el pill internamente
- "Guardar cambios" en el editor de plantillas: ya no ocupa todo el ancho (`flex-grow-1` eliminado), alineado a la derecha junto a "Cancelar"

**Diálogos**
- El CSS reset (`* { margin: 0 }`) borraba el `margin: auto` del browser que centra el `<dialog>` nativo — restaurado explícitamente. Los diálogos ahora aparecen centrados en pantalla

**Páginas de autenticación**
- `login.html` y `totp_verify.html` cargaban sin diseño en producción porque `/static/css/` requería autenticación — agregado a rutas públicas

---

## [0.9.0] — 2026-04-06

### UI — Rediseño completo Adwaita (Fases 2–5)

Cierre del rediseño visual iniciado en v0.8.0. Todas las vistas migradas al design system Adwaita.

**Fase 2 — Páginas de autenticación**
- `login.html` y `totp_verify.html` reescritos como páginas standalone (no extienden `base.html`)
- Tarjeta centrada estilo GNOME con logo SVG "Stream" incrustado
- Todos los estilos en `<style nonce>` — sin `style=""` inline (cumple CSP)
- Primera vez: QR con fondo blanco forzado para lectura correcta por apps de autenticación

**Fase 3 — Dashboard, Podcasts y Episodios**
- `index.html`: stat cards (`fc-stat-card`), content grid 2 columnas, `fc-empty-state`, `table-wrapper`
- `podcasts.html`: `fc-page-header`, dialogs con `dialog-header/body/footer`, `dialog-header-destructive` en delete, `data-close-dialog` — sin `onclick` inline
- `episodes.html`: filtros de podcast/estado sin `onchange` inline, `table-wrapper`, dialog de render con clases del sistema
- `episodes.js`: handlers para `data-close-dialog` y podcast filter añadidos

**Fase 4 — Detalle, Plantillas y Configuración**
- `episode_detail.html`: embed YouTube con `ratio ratio-16x9`, `show-notes`, `job-log`, acciones sin `innerHTML`
- `templates.html`: `fc-page-header`, dialog nativo, swatches de color via JS
- `template_editor.html`: canvas sin `style=""` inline, JS sin `innerHTML`, `canvas-dark-bg`
- `settings.html`: alertas dismissibles con `data-close-alert`, sin `onclick`

**Fase 5 — Accesibilidad y transiciones**
- `job_badge.html`: usa `status-job-*` del design system (adaptativo al tema)
- `theme.css`: transición suave de tema (background/color/border, 0.15–0.18s en elementos estructurales), `color-scheme: light dark`, skip-to-content
- Skip-to-content link visible al hacer Tab en `base.html`
- `aria-modal="true"` en todos los `<dialog>`, `scope="col"` en todos los `<th>`, `aria-label` en selects de filtro
- Toasts con `role="status"` + `aria-live="polite"` en `app.js`

**Cache busting**
- `?v=0.9.0` en todos los links CSS/JS — fuerza descarga en browsers con caché anterior

**Fix: páginas de auth sin diseño**
- `/static/css/` y `/static/js/` ahora son rutas públicas — necesario para que login y 2FA carguen el design system antes de autenticarse
- El CSS/JS no contiene información sensible (es el design system visual, no lógica de negocio)

---

## [0.8.0] — 2026-04-06

### UI — Fase 1: Design System Adwaita + Sidebar GNOME

Primera fase del rediseño visual completo inspirado en GNOME HIG / Adwaita.

**Design system nuevo (`theme.css`)**
- Sistema de tokens CSS completo: variables para colores, tipografía, radios, sombras y espaciado — tema claro y oscuro
- Paleta Adwaita oficial: Blue 3 (`#3584e4`) como primario, Purple 3 (`#9141ac`) como acento, escala completa de semánticos (success/warning/error/info)
- Tipografía Inter Variable cargada localmente (`/static/fonts/`) — sin dependencias externas

**Layout GNOME (sidebar)**
- Navegación lateral fija estilo GNOME: logo animado con CSS vars, secciones de nav, footer con estado YouTube, toggle de tema y logout
- `base.html` completamente reescrito con grid `sidebar + main`
- El ícono del logo (concepto "Stream") usa `var(--fc-primary)` — se adapta automáticamente al tema

**Tema claro / oscuro**
- Toggle manual en el sidebar (ícono sol/luna) persiste en `localStorage`
- Detección automática de `prefers-color-scheme` como valor por defecto
- Sin flash de tema incorrecto: script inline (con nonce) aplica el tema antes del primer paint

**Seguridad — mejora adicional**
- Eliminada dependencia de `cdn.jsdelivr.net`: Bootstrap Icons y fuente Inter ahora se sirven desde `/static/fonts/` y `/static/css/` localmente
- CSP simplificada: `style-src 'self' 'nonce-{nonce}'` y `font-src 'self'` — sin whitelist de CDN externo
- `/static/fonts/` agregado a rutas públicas para que la página de login cargue la fuente sin autenticación (los archivos de fuente no son sensibles)
- Bootstrap CSS CDN eliminado del `<head>` — shims de compatibilidad incluidos en `theme.css` para la transición

---

## [0.7.0] — 2026-04-05

### Seguridad — auditoría externa completa (4 rondas, score 78 → 92/100)

Resumen del hardening completo realizado en esta versión:

- **Bootstrap JS eliminado**: reemplazado con APIs nativas del browser (`<dialog>`, `<details>/<summary>`). Elimina la dependencia de JS externo y el único motivo para `unsafe-inline` en `style-src`
- **CSP sin `unsafe-inline` en ninguna directiva**: `script-src` y `style-src` usan nonces por request exclusivamente
- **Archivos estáticos protegidos**: `/static/js/` y `/static/css/` requieren autenticación — un atacante sin sesión no puede leer el código fuente ni inferir la arquitectura
- **Orden de middleware corregido**: `security_middleware` es verdaderamente el más externo — todas las respuestas (401, 403, 404, redirects) reciben el set completo de headers de seguridad
- **API devuelve 401 JSON**: endpoints `/api/*` responden `{"detail":"No autenticado"}` para sesiones no iniciadas en lugar de redirigir a HTML
- **`robots.txt`**: `Disallow: /` — ningún bot indexa nada
- **`security.txt`** (RFC 9116): `/.well-known/security.txt` dinámico con `Contact`, `Expires`, `Canonical` y `Scope`
- **HSTS a 2 años** (63,072,000 s) — recomendación OWASP/Mozilla Observatory
- **Headers COOP/CORP**: `Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Resource-Policy: same-origin`
- **XSS en `showToast`**: reemplazado `innerHTML` con `textContent` + DOM methods
- **`innerHTML` eliminado en todo el JS**: `episodes.js` y scripts inline usan `createElement`/`appendChild`
- **CSRF expirado redirige con flash**: en lugar de devolver JSON 400 al usuario
- **Favicon real** + `<link rel="icon">` explícito en todas las templates
- **ARIA en alertas de error**: `role="alert"` + `aria-live="assertive"` en login y 2FA
- **404 real** para usuarios autenticados (sin redirigir al dashboard)
- **`/health` requiere autenticación**
- **`minlength="8"`** en campo de contraseña

---

## [0.6.9] — 2026-04-05

### Seguridad
- **Headers completos en todas las respuestas**: corregido el orden de los middlewares — `security_middleware` ahora es verdaderamente el más externo (se registra último en Starlette = corre primero). Todas las respuestas — incluyendo 401, 403, redirects — reciben el set completo de headers: CSP, COOP, CORP, X-Frame-Options, etc.
- **API unauthenticated → 401 con JSON**: cambiado de 403 vacío a `{"detail":"No autenticado"}` con status 401 y `Content-Type: application/json` — semánticamente correcto (401 = sin autenticar) y permite que el frontend maneje sesiones expiradas correctamente
- **`Canonical` en security.txt**: añadido campo `Canonical` requerido por RFC 9116

---

## [0.6.8] — 2026-04-05

### Seguridad
- **Archivos estáticos requieren autenticación**: `/static/js/` y `/static/css/` ya no son accesibles sin sesión activa — un atacante no autenticado recibe 403 y no puede leer el código fuente JS ni inferir la arquitectura interna de la app. Las páginas de login/2FA usan únicamente recursos CDN (Bootstrap) y no dependen de archivos locales, por lo que nada se rompe.

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
