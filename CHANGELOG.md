# Changelog

Todos los cambios notables de este proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versionado semántico: MAJOR.MINOR.PATCH

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
