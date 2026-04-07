# FlowCast — Guía de Marca e Identidad Visual

## Qué es FlowCast

App de escritorio que toma un episodio de podcast, genera un audiograma y lo publica automáticamente en YouTube. El diseño se inspira en el entorno de escritorio GNOME (Adwaita).

---

## Filosofía de diseño

Seguir los principios de GNOME HIG (Human Interface Guidelines):

- **Simplicidad:** interfaces limpias, sin ruido visual. Solo lo necesario.
- **Consistencia:** los mismos patrones en toda la app.
- **Geometría simple:** iconos y elementos basados en formas básicas.
- **Profundidad sutil:** no es flat puro. Se usa un perfil inferior más oscuro para dar volumen sin sombras externas.
- **Adaptativo:** la UI se ajusta al espacio disponible.

Referencia completa: https://developer.gnome.org/hig/

---

## Tipografía

Siguiendo GNOME 48+:

| Uso | Fuente | Fallback |
|-----|--------|----------|
| UI / Títulos / Cuerpo | **Adwaita Sans** (basada en Inter) | Inter, system-ui, sans-serif |
| Código / Monoespaciado | **Adwaita Mono** (basada en Iosevka) | Iosevka, monospace |

- Tamaño base: 11pt (equivalente GNOME).
- Pesos principales: Regular (400), Medium (500), Bold (700).
- No usar más de 2 pesos por vista.

---

## Paleta de colores GNOME Adwaita

### Colores primarios de FlowCast

Para FlowCast, usar **Blue** como color principal (acción, enlaces, botones primarios) y **Purple** como acento secundario (creatividad, audio, podcasting).

| Rol | Color | Hex | RGB |
|-----|-------|-----|-----|
| Primario | Blue 3 | `#3584e4` | (53, 132, 228) |
| Primario hover | Blue 4 | `#1c71d8` | (28, 113, 216) |
| Primario activo | Blue 5 | `#1a5fb4` | (26, 95, 180) |
| Acento | Purple 3 | `#9141ac` | (145, 65, 172) |
| Acento hover | Purple 4 | `#813d9c` | (129, 61, 156) |

### Colores semánticos

| Rol | Color | Hex |
|-----|-------|-----|
| Éxito | Green 3 | `#33d17a` |
| Éxito fuerte | Green 5 | `#26a269` |
| Advertencia | Yellow 3 | `#f6d32d` |
| Advertencia fuerte | Yellow 5 | `#e5a50a` |
| Error / Destructivo | Red 3 | `#e01b24` |
| Error fuerte | Red 5 | `#a51d2d` |
| Info | Blue 2 | `#62a0ea` |

### Paleta completa de referencia

**Azules:**
- Blue 1: `#99c1f1` | Blue 2: `#62a0ea` | Blue 3: `#3584e4` | Blue 4: `#1c71d8` | Blue 5: `#1a5fb4`

**Verdes:**
- Green 1: `#8ff0a4` | Green 2: `#57e389` | Green 3: `#33d17a` | Green 4: `#2ec27e` | Green 5: `#26a269`

**Amarillos:**
- Yellow 1: `#f9f06b` | Yellow 2: `#f8e45c` | Yellow 3: `#f6d32d` | Yellow 4: `#f5c211` | Yellow 5: `#e5a50a`

**Naranjas:**
- Orange 1: `#ffbe6f` | Orange 2: `#ffa348` | Orange 3: `#ff7800` | Orange 4: `#e66100` | Orange 5: `#c64600`

**Rojos:**
- Red 1: `#f66151` | Red 2: `#ed333b` | Red 3: `#e01b24` | Red 4: `#c01c28` | Red 5: `#a51d2d`

**Púrpuras:**
- Purple 1: `#dc8add` | Purple 2: `#c061cb` | Purple 3: `#9141ac` | Purple 4: `#813d9c` | Purple 5: `#613583`

**Marrones:**
- Brown 1: `#cdab8f` | Brown 2: `#b5835a` | Brown 3: `#986a44` | Brown 4: `#865e3c` | Brown 5: `#63452c`

### Tema claro (Light)

| Rol | Color | Hex |
|-----|-------|-----|
| Fondo ventana | Light 2 | `#f6f5f4` |
| Fondo tarjeta/header | Light 1 | `#ffffff` |
| Borde sutil | Light 3 | `#deddda` |
| Borde fuerte | Light 4 | `#c0bfbc` |
| Texto secundario | Light 5 | `#9a9996` |
| Texto primario | Dark 4 | `#241f31` |
| Texto subtítulo | Dark 2 | `#5e5c64` |

### Tema oscuro (Dark)

| Rol | Color | Hex |
|-----|-------|-----|
| Fondo ventana | Dark 4 | `#241f31` |
| Fondo tarjeta/header | Dark 3 | `#3d3846` |
| Borde sutil | Dark 2 | `#5e5c64` |
| Borde fuerte | Dark 1 | `#77767b` |
| Texto secundario | Light 5 | `#9a9996` |
| Texto primario | Light 1 | `#ffffff` |
| Texto subtítulo | Light 4 | `#c0bfbc` |

---

## Iconos

### Icono de app (full-color)

- Canvas: 128×128px, visualización típica a 64×64px, mínimo 32×32px.
- Estilo geométrico y simple, basado en formas básicas.
- No usar sombras externas (se generan programáticamente).
- Dar profundidad sutil con un perfil inferior más oscuro.
- Metáfora sugerida para FlowCast: onda de audio + flecha de flujo/publicación.
- Usar colores de la paleta Adwaita como base.
- La fuente de luz apunta directo desde arriba.

### Iconos de UI (symbolic)

- Monocromáticos, tamaño base 16×16px SVG.
- Se pueden usar a 32, 64 y 128px (evitar otros tamaños).
- Alinear todas las formas al pixel grid.
- Pueden recolorearse programáticamente.
- Usar los iconos existentes de GTK/Adwaita siempre que sea posible.
- Referencia: https://developer.gnome.org/hig/guidelines/ui-icons.html

---

## Componentes de UI (patrones Adwaita)

### Header Bar
- Barra superior con título centrado y controles a los lados.
- Fondo ligeramente diferenciado del contenido.

### Boxed Lists
- Listas agrupadas con bordes redondeados y fondo diferenciado.
- Ideal para configuraciones y listas de episodios.

### Toasts
- Notificaciones temporales en la parte inferior.
- Para confirmar acciones: "Audiograma generado", "Publicado en YouTube".

### Botones
- Primario (suggested): fondo Blue 3, texto blanco.
- Destructivo: fondo Red 3, texto blanco.
- Normal: fondo transparente o sutil, texto del color principal.
- Border-radius: 6px (estilo Adwaita).

### Spacing
- Unidad base: 6px.
- Padding interno de tarjetas: 12px.
- Separación entre elementos: 6px o 12px.
- Margen de secciones: 18px o 24px.

---

## Esquinas y bordes

- Border-radius general: 6px (botones, inputs, tarjetas).
- Border-radius ventana principal: 12px (si aplica).
- Bordes de 1px con colores de la fila "Borde sutil" del tema activo.

---

## Sombras

- Evitar sombras agresivas. Adwaita usa elevación mínima.
- Sombra de tarjetas flotantes: `0 1px 3px rgba(0, 0, 0, 0.12)`.
- Sombra de diálogos/popovers: `0 2px 8px rgba(0, 0, 0, 0.15)`.

---

## Variables CSS sugeridas

```css
:root {
  /* FlowCast - Tema claro */
  --fc-primary: #3584e4;
  --fc-primary-hover: #1c71d8;
  --fc-primary-active: #1a5fb4;
  --fc-accent: #9141ac;
  --fc-accent-hover: #813d9c;

  --fc-success: #33d17a;
  --fc-warning: #f6d32d;
  --fc-error: #e01b24;

  --fc-bg-window: #f6f5f4;
  --fc-bg-card: #ffffff;
  --fc-border: #deddda;
  --fc-border-strong: #c0bfbc;

  --fc-text: #241f31;
  --fc-text-secondary: #5e5c64;
  --fc-text-muted: #9a9996;

  --fc-radius: 6px;
  --fc-radius-lg: 12px;
  --fc-spacing: 6px;

  --fc-font: 'Inter', 'Adwaita Sans', system-ui, sans-serif;
  --fc-font-mono: 'Iosevka', 'Adwaita Mono', monospace;
}

[data-theme="dark"] {
  --fc-bg-window: #241f31;
  --fc-bg-card: #3d3846;
  --fc-border: #5e5c64;
  --fc-border-strong: #77767b;

  --fc-text: #ffffff;
  --fc-text-secondary: #c0bfbc;
  --fc-text-muted: #9a9996;
}
```

---

## Referencias

- GNOME HIG completa: https://developer.gnome.org/hig/
- Paleta oficial: https://developer.gnome.org/hig/reference/palette.html
- App Icons: https://developer.gnome.org/hig/guidelines/app-icons.html
- UI Icons: https://developer.gnome.org/hig/guidelines/ui-icons.html
- UI Styling: https://developer.gnome.org/hig/guidelines/ui-styling.html
- Typography: https://developer.gnome.org/hig/guidelines/typography.html
- Patterns (containers, nav, controls, feedback): https://developer.gnome.org/hig/patterns.html
