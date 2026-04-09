# FlowCast — Seguridad

Documento de referencia de todos los controles de seguridad implementados en la aplicación.
Última actualización: v0.9.7 (2026-04-09).

---

## Índice

1. [Autenticación](#1-autenticación)
2. [Gestión de sesión](#2-gestión-de-sesión)
3. [Protección CSRF](#3-protección-csrf)
4. [Rate limiting](#4-rate-limiting)
5. [Content Security Policy (CSP)](#5-content-security-policy-csp)
6. [HTTP Security Headers](#6-http-security-headers)
7. [Protección XSS](#7-protección-xss)
8. [Protección SSRF](#8-protección-ssrf)
9. [Token de YouTube (OAuth2)](#9-token-de-youtube-oauth2)
10. [Validación de secrets al arranque](#10-validación-de-secrets-al-arranque)
11. [Control de tamaño de cuerpo](#11-control-de-tamaño-de-cuerpo)
12. [CORS](#12-cors)
13. [Caché de páginas sensibles](#13-caché-de-páginas-sensibles)
14. [Archivos estáticos y rutas públicas](#14-archivos-estáticos-y-rutas-públicas)
15. [Manejo de errores](#15-manejo-de-errores)
16. [Permisos de archivos sensibles](#16-permisos-de-archivos-sensibles)
17. [Infraestructura (producción)](#17-infraestructura-producción)
18. [Auditoría externa](#18-auditoría-externa)
19. [Limitaciones conocidas / en scope](#19-limitaciones-conocidas--en-scope)

---

## 1. Autenticación

**Dos factores obligatorios** para acceder a cualquier ruta protegida.

### Paso 1 — Contraseña
- Credenciales configuradas en `.env` (`ADMIN_USERNAME`, `ADMIN_PASSWORD`).
- La app **no arranca** si la contraseña es el valor por defecto `changeme` (ver §10).
- Comparación directa de string; el username/password se trunca antes de comparar para evitar timing attacks en cadenas largas (`_MAX_USERNAME=150`, `_MAX_PASSWORD=256`).

**Archivo:** `app/routers/auth.py:58-84`

### Paso 2 — TOTP (2FA)
- Implementado con `pyotp` (RFC 6238, ventana de 1 paso para tolerancia de reloj).
- El secreto TOTP se genera con `pyotp.random_base32()` en el primer arranque y se persiste en `data/tokens/totp_secret.txt` con permisos `0o600`.
- Hasta que el usuario no complete el TOTP (`totp_verified: True` en sesión), la sesión queda en estado intermedio — no accede a rutas protegidas.
- El QR de configuración solo se muestra en el primer acceso (`first_time = not is_2fa_configured()`).

**Archivo:** `app/auth/totp.py`

### Flujo completo
```
GET /login → POST /login → sesión {authenticated: True, totp_verified: False}
           → GET /2fa   → POST /2fa  → sesión {authenticated: True, totp_verified: True}
           → redirect /
```

---

## 2. Gestión de sesión

**Librería:** `itsdangerous.URLSafeTimedSerializer` — cookie firmada con HMAC-SHA1.

| Atributo       | Valor                                             |
|----------------|---------------------------------------------------|
| Nombre cookie  | `flowcast_session`                                |
| Firma          | HMAC con `SECRET_KEY` + salt `"flowcast-session"` |
| Expiración     | 7 días (`SESSION_MAX_AGE=604800`)                 |
| `HttpOnly`     | Sí — inaccesible desde JavaScript                 |
| `SameSite`     | `lax` — bloquea envío cross-site en POST          |
| `Secure`       | Sí cuando `APP_BASE_URL` comienza con `https://`  |

- `is_fully_authenticated()` verifica **ambas** flags (`authenticated` AND `totp_verified`).
- El logout borra la cookie completamente (`clear_session`).

**Archivo:** `app/auth/session.py`

---

## 3. Protección CSRF

Implementación doble: **token firmado en cookie** + **mismo token en formulario** (double-submit + firma criptográfica).

- Token generado con `secrets.token_hex(16)` envuelto en `URLSafeTimedSerializer` (salt `"flowcast-csrf"`, TTL 1 hora).
- Comparación con `secrets.compare_digest` para evitar timing attacks.
- Aplicado en: `POST /login` y `POST /2fa`.
- Cookie CSRF: `HttpOnly`, `SameSite=lax`, `Secure` en HTTPS, TTL 1 hora.

```python
# verify_csrf en app/auth/csrf.py
return secrets.compare_digest(str(form_nonce), str(cookie_nonce))
```

**Archivo:** `app/auth/csrf.py`, `app/routers/auth.py`

---

## 4. Rate limiting

**Librería:** `slowapi` (wrapper de `limits` sobre FastAPI).

| Endpoint      | Límite     | Clave       |
|---------------|------------|-------------|
| `POST /login` | 5/minuto   | IP remota   |
| `GET /health` | 30/minuto  | IP remota   |

- Respuesta 429 con `Retry-After: 60` en JSON `{"detail": "Demasiados intentos. Reintentá en un momento."}`.
- No expone información sobre la existencia de usuarios (mismo mensaje para usuario correcto/incorrecto).

**Archivo:** `app/auth/limiter.py`, `app/main.py:92-100`

---

## 5. Content Security Policy (CSP)

Cabecera generada dinámicamente en cada request con un **nonce único por request** (`secrets.token_hex(16)`).

```
default-src 'self';
script-src  'self' 'nonce-{nonce}';
style-src   'self' 'nonce-{nonce}';
font-src    'self';
img-src     'self' data:;
connect-src 'self';
frame-src   https://www.youtube.com;
frame-ancestors 'none';
base-uri    'none';
form-action 'self';
object-src  'none';
upgrade-insecure-requests
```

**Reglas de uso en templates:**
- Todo `<script>` y `<style>` inline lleva `nonce="{{ request.state.csp_nonce }}"`.
- **No se usan** `onclick=`, `onchange=` u otros event handlers inline — serían bloqueados por el CSP. Toda la lógica JS va en bloques `<script nonce="...">` con `addEventListener`.
- Scripts externos: ninguno — solo `'self'`.

**Archivo:** `app/main.py:175-189`

---

## 6. HTTP Security Headers

Aplicados en `security_middleware` a todas las respuestas:

| Header                          | Valor                                  | Propósito                              |
|---------------------------------|----------------------------------------|----------------------------------------|
| `X-Content-Type-Options`        | `nosniff`                              | Previene MIME sniffing                 |
| `X-Frame-Options`               | `DENY`                                 | Bloquea clickjacking (complementa CSP) |
| `Referrer-Policy`               | `strict-origin-when-cross-origin`      | Limita info en Referer header          |
| `Permissions-Policy`            | `camera=(), microphone=(), geolocation=()` | Deshabilita APIs de hardware       |
| `Cross-Origin-Opener-Policy`    | `same-origin`                          | Aísla el contexto de navegación        |
| `Cross-Origin-Resource-Policy`  | `same-origin`                          | Bloquea carga cross-origin de recursos |
| `server`                        | `""` (vacío)                           | No expone tecnología del servidor      |

**Archivo:** `app/main.py:151-197`

---

## 7. Protección XSS

### Descripciones de episodios (RSS)
El contenido HTML de feeds RSS es potencialmente malicioso. Doble sanitización:

1. **Al parsear el RSS** (`app/services/rss.py:99`): `sanitize_html()` filtra con `nh3` antes de guardar en DB.
2. **Al renderizar** (`app/routers/ui.py:19`): filtro Jinja2 `sanitize_html` aplicado nuevamente como defensa en profundidad.

```python
# episode_detail.html — único uso de | safe en todo el proyecto
{{ episode.description | sanitize_html | safe }}
```

**Tags permitidos:** `p br strong b em i u a ul ol li blockquote h1-h6`  
**Atributos permitidos:** solo `<a href="...">` con esquemas `http`, `https`, `mailto`  
**Atributos bloqueados:** `style`, `class`, `id`, `on*`, `data-*`, etc.

### Autoescape Jinja2
Todos los templates usan autoescape (comportamiento por defecto de Jinja2 con `.html`). No hay otros usos de `| safe` en ningún template.

**Archivo:** `app/utils/html_sanitizer.py`

---

## 8. Protección SSRF

Toda URL externa que la app fetcha pasa por `validate_external_url()` antes de hacer la petición.

**Puntos de aplicación:**
- `app/services/rss.py` — fetch del feed RSS
- `app/services/downloader.py` — descarga del MP3
- `app/routers/proxy.py` — proxy de imágenes (`/api/img`)

**Bloqueos:**
- Esquemas distintos a `http`/`https` (bloquea `file://`, `javascript:`, `ftp://`, etc.)
- Direcciones loopback (`127.0.0.1`, `::1`)
- Rangos privados (`10.x`, `172.16-31.x`, `192.168.x`)
- Link-local (`169.254.x.x`, `fe80::`)
- Rangos reservados

```python
# app/utils/url_validator.py
if parsed.scheme not in ("http", "https"):
    raise ValueError(...)
addr = ipaddress.ip_address(hostname)
if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved:
    raise ValueError(...)
```

**Archivo:** `app/utils/url_validator.py`

---

## 9. Token de YouTube (OAuth2)

El token OAuth2 de YouTube (access + refresh token) se almacena cifrado en disco.

- **Cifrado:** Fernet (AES-128-CBC + HMAC-SHA256) de la librería `cryptography`.
- **Clave derivada:** `SHA-256(SECRET_KEY)` → base64url → clave Fernet. Misma entropía que la SECRET_KEY del sistema.
- **Permisos de archivo:** `0o600` (solo lectura/escritura del propietario del proceso).
- **Rotación automática:** si el refresh token expira (`invalid_grant`), se borra el archivo y la UI muestra "desconectado" con instrucciones para reconectar.
- **Migración:** archivos en formato plain JSON previo al cifrado se re-cifran automáticamente al cargar.

**Archivo:** `app/auth/youtube_oauth.py`

---

## 10. Validación de secrets al arranque

La app lanza `RuntimeError` y **no arranca** si detecta credenciales inseguras por defecto:

```python
if self.secret_key in ("change-me", ""):
    errors.append("SECRET_KEY no puede ser 'change-me'")
if self.admin_password in ("changeme", ""):
    errors.append("ADMIN_PASSWORD no puede ser 'changeme'")
```

Esto previene despliegues accidentales con credenciales predeterminadas.

**Archivo:** `app/config.py:79-90`

---

## 11. Control de tamaño de cuerpo

Los endpoints de autenticación rechazan bodies mayores a **2 KB** antes de que FastAPI lea el cuerpo:

```python
_MAX_FORM_BODY = 2048
if request.method == "POST" and request.url.path in ("/login", "/2fa"):
    content_length = int(request.headers.get("content-length", 0))
    if content_length > _MAX_FORM_BODY: return JSONResponse(400)
```

Mitiga ataques de cuerpo grande en los endpoints más expuestos (son públicos, sin auth previa).

**Archivo:** `app/main.py:159-162`

---

## 12. CORS

CORS configurado con `allow_origins=[]` — no se permiten peticiones cross-origin desde ningún origen externo.

```python
CORSMiddleware(allow_origins=[], allow_credentials=False, ...)
```

Esto complementa `SameSite=lax` en cookies para bloquear ataques CSRF vía fetch cross-origin.

**Archivo:** `app/main.py:127-133`

---

## 13. Caché de páginas sensibles

Las páginas de autenticación usan `Cache-Control: no-store, no-cache, must-revalidate` para evitar que el browser o proxies intermedios almacenen páginas con tokens CSRF.

Los assets estáticos usan `Cache-Control: public, max-age=31536000, immutable` (1 año) — son content-addressed por versión (`?v=X.Y.Z`).

**Archivo:** `app/main.py:167-173`

---

## 14. Archivos estáticos y rutas públicas

Solo las siguientes rutas son accesibles sin autenticación:

```python
_PUBLIC_PREFIXES = (
    "/login", "/2fa", "/logout",
    "/favicon.ico", "/robots.txt", "/.well-known/",
    "/static/css/",    # necesario para login/2FA antes de auth
    "/static/js/",
    "/static/fonts/",
)
```

El directorio `/static/uploads/` (imágenes de fondo, fuentes personalizadas, renders) **requiere autenticación** — no es accesible sin sesión activa.

Cualquier ruta `/static/` no incluida en los prefijos públicos retorna `403` (no redirige a `/login`).

**Archivo:** `app/main.py:30`, `app/main.py:138-148`

---

## 15. Manejo de errores

Los handlers de excepción no exponen stack traces ni detalles internos al cliente:

- `400 ValidationError` → `{"detail": "Solicitud inválida"}`
- `4xx/5xx HTTP` (no-API) → página HTML genérica sin información del error
- `500 unhandled` → HTML genérico; el detalle se loguea internamente con `exc_info`
- Errores de API → `{"detail": "Error"}` o `{"detail": "Error interno"}`

**Archivo:** `app/main.py:104-123`

---

## 16. Permisos de archivos sensibles

| Archivo                              | Permisos | Contenido                    |
|--------------------------------------|----------|------------------------------|
| `data/tokens/totp_secret.txt`        | `0o600`  | Secreto TOTP en base32       |
| `data/tokens/youtube_token.json`     | `0o600`  | Token OAuth2 cifrado (Fernet)|

Ambos son creados/actualizados con `os.chmod(path, 0o600)` explícito después de cada escritura.

---

## 17. Infraestructura (producción)

- **TLS:** Caddy con HTTPS automático (Let's Encrypt) en dominio `avalos.xyz`.
- **Reverse proxy:** Caddy → Docker container (solo el puerto HTTP interno expuesto a localhost).
- **Contenedor Docker:** usuario no-root, sin privilegios adicionales.
- **`robots.txt`:** `Disallow: /` — evita indexación por crawlers.
- **`/.well-known/security.txt`:** contacto de seguridad publicado con expiración anual.

---

## 18. Auditoría externa

Score: **92/100** en auditoría de seguridad externa (fecha: 2026-Q1).

Hallazgos menores ya corregidos incluidos en esta documentación.

---

## 19. Limitaciones conocidas / en scope

| Item | Estado | Notas |
|------|--------|-------|
| YouTube OAuth en modo *Testing* | Intencional durante desarrollo | Tokens expiran cada 7 días. La UI avisa claramente con pasos para reconectar. Cambiar a modo producción en Google Cloud Console antes del release público. |
| Usuario único (`admin`) | Diseño intencional | App self-hosted de un solo usuario. No hay sistema multi-usuario ni roles. |
| Sin 2FA para desconectar YouTube | Aceptado | Requiere sesión completamente autenticada (password + TOTP). |
| TOTP sin protección anti-replay | Bajo riesgo | `valid_window=1` permite el mismo token en ~60 segundos. Mitigado por rate limiting en login y HTTPS. |
