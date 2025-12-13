# Guia de Estilos Corporativos SCRAM para IA

Este documento contiene las especificaciones de identidad visual de SCRAM para ser usado como referencia por asistentes de IA al generar codigo, diseno o contenido.

---

## 1. COLORES CORPORATIVOS

### Colores Primarios (OBLIGATORIOS)

| Nombre | Hex | RGB | Uso |
|--------|-----|-----|-----|
| **Amarillo SCRAM** | `#ff9900` | rgb(255, 153, 0) | CTAs, botones principales, enlaces, acentos destacados |
| **Amarillo Hover** | `#ff8c00` | rgb(255, 140, 0) | Estado hover de elementos amarillos |
| **Negro SCRAM** | `#1a1a1a` | rgb(26, 26, 26) | Textos principales, fondos oscuros, headers |

### Colores Secundarios

| Nombre | Hex | RGB | Uso |
|--------|-----|-----|-----|
| **Verde SCRAM** | `#44ce6f` | rgb(68, 206, 111) | Estados de exito, validaciones, acentos secundarios |
| **Verde Oscuro** | `#007a3d` | rgb(0, 122, 61) | Variante dark del verde |
| **Morado** | `#c679e3` | rgb(198, 121, 227) | Acentos alternativos, temas especiales |

### Colores Neutrales

| Nombre | Hex | Uso |
|--------|-----|-----|
| **Blanco** | `#ffffff` | Fondos principales, textos sobre oscuro |
| **Fondo Claro** | `#f7fafd` | Fondos de secciones alternas |
| **Fondo Claro Alt** | `#f9f6f6` | Fondos secundarios |
| **Texto Navegacion** | `#4a6f8a` | Links de navegacion, textos secundarios |
| **Texto Parrafo** | `#6084a4` | Cuerpo de texto, descripciones |
| **Borde Claro** | `#e0e0e0` | Bordes, separadores |

### Colores Semanticos

| Estado | Hex | Uso |
|--------|-----|-----|
| **Success** | `#00A859` | Mensajes de exito, confirmaciones |
| **Warning** | `#ff9900` | Advertencias (usa el amarillo primario) |
| **Error** | `#eb6b3d` | Errores, alertas criticas |
| **Info** | `#4a6f8a` | Informacion neutral |

### Gradientes Corporativos

```css
/* Gradiente primario (botones destacados) */
background: linear-gradient(135deg, #ff9900 0%, #ff8c00 100%);

/* Gradiente verde */
background: linear-gradient(135deg, #23bdb8 0%, #43e794 100%);

/* Gradiente morado */
background: linear-gradient(135deg, #9a56ff 0%, #e36cd9 100%);
```

### Sombras Corporativas

```css
/* Sombra de tarjetas */
box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);

/* Sombra hover de tarjetas */
box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12);

/* Sombra de botones amarillos */
box-shadow: 0 4px 12px rgba(255, 153, 0, 0.25);

/* Sombra verde (success) */
box-shadow: 0 13px 27px 0 rgba(68, 206, 111, 0.25);
```

---

## 2. TIPOGRAFIAS

### Familias de Fuentes

| Tipo | Fuente | Fallback |
|------|--------|----------|
| **Encabezados** | ASAP | sans-serif |
| **Cuerpo de texto** | Cabin | system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif |

### Especificaciones por Elemento

#### Encabezados (Fuente: ASAP)

| Elemento | Peso | Estilo | Tamano | Line Height | Letter Spacing |
|----------|------|--------|--------|-------------|----------------|
| H1 | 700 (Bold) | Italic | 42-48px | 1.2 | -0.02em |
| H2 | 700 (Bold) | Italic | 28-32px | 1.2 | -0.01em |
| H3 | 600 (SemiBold) | Normal | 24px | 1.2-1.5 | -0.01em |
| H4 | 600 (SemiBold) | Normal | 22px | 1.5 | normal |
| H5 | 600 (SemiBold) | Normal | 20px | 1.5 | normal |
| H6 | 600 (SemiBold) | Normal | 18px | 1.5 | normal |

#### Cuerpo de Texto (Fuente: Cabin)

| Elemento | Peso | Tamano | Line Height |
|----------|------|--------|-------------|
| Body (normal) | 400 (Regular) | 16px | 1.7-1.8 |
| Body (pequeno) | 400 (Regular) | 14px | 1.6 |
| Body (extra pequeno) | 400 (Regular) | 12px | 1.5 |
| Boton | 600 (SemiBold) | 16px | 1.5 |
| Caption | 400 (Regular) | 12px | 1.4 |

### Escala de Tamanos de Fuente

```
12px  - Extra pequeno (captions, notas)
14px  - Pequeno (body secundario)
16px  - Base (body principal, botones)
18px  - Medio (subtitulos)
20px  - H6
22px  - H5/Large
24px  - H4
28px  - H3
32px  - H2
42px  - H1 (desktop)
48px  - H1 (hero grande)
52px  - Display
```

### Pesos Disponibles

- **400** - Regular (textos normales)
- **500** - Medium (enfasis leve)
- **600** - SemiBold (subtitulos, botones, enfasis)
- **700** - Bold (titulos principales)

---

## 3. REGLAS DE USO

### Titulos
- Los titulos H1 y H2 SIEMPRE usan **ASAP Bold Italic**
- Los titulos H3-H6 usan **ASAP SemiBold** sin italica
- Color de titulos: `#1a1a1a` sobre fondo claro, `#ffffff` sobre fondo oscuro

### Cuerpo de Texto
- Todo el texto de parrafo usa **Cabin Regular**
- Color principal de parrafos: `#6084a4`
- Line-height generoso (1.7-1.8) para legibilidad

### Botones y CTAs
- Botones principales: Fondo `#ff9900`, texto `#ffffff`
- Botones hover: Fondo `#ff8c00`, elevar con `translateY(-2px)`
- Border-radius de botones: `100px` (pill shape) o `12px` (redondeado)
- Texto de boton: **Cabin SemiBold**, sin mayusculas forzadas

### Enlaces
- Color de enlaces: `#ff9900`
- Hover: Subrayado o cambio a `#ff8c00`

### Tarjetas
- Border-radius: `16px`
- Sombra base: `0 5px 15px rgba(0, 0, 0, 0.08)`
- Sombra hover: `0 10px 25px rgba(0, 0, 0, 0.12)`
- Transicion: `0.3s ease`

---

## 4. ESPACIADOS

### Sistema de Espaciado

```
8px   - xs (espacios minimos, gaps pequenos)
15px  - sm (padding interno pequeno)
20px  - md (padding estandar)
30px  - lg (separacion entre elementos)
40px  - xl (separacion entre secciones pequenas)
60px  - 2xl (separacion entre secciones)
80px  - 3xl (separacion grande)
100px - 4xl (separacion hero/footer)
120px - 5xl (separacion maxima)
```

### Border Radius

```
5px   - Pequeno (inputs, badges)
12px  - Medio (cards, modales)
16px  - Grande (cards destacadas)
100px - Pill (botones principales)
50%   - Circular (avatares, iconos)
```

---

## 5. TOKENS CSS (Variables)

```css
:root {
  /* Colores primarios */
  --color-primary: #ff9900;
  --color-primary-hover: #ff8c00;
  --color-secondary: #44ce6f;
  --color-dark: #1a1a1a;

  /* Colores neutrales */
  --color-white: #ffffff;
  --color-bg-light: #f7fafd;
  --color-bg-light-alt: #f9f6f6;
  --color-text-nav: #4a6f8a;
  --color-text-paragraph: #6084a4;
  --color-border: #e0e0e0;

  /* Colores semanticos */
  --color-success: #00A859;
  --color-warning: #ff9900;
  --color-error: #eb6b3d;
  --color-info: #4a6f8a;

  /* Tipografia */
  --font-heading: 'ASAP', sans-serif;
  --font-body: 'Cabin', system-ui, sans-serif;

  /* Tamanos de fuente */
  --font-size-xs: 12px;
  --font-size-sm: 14px;
  --font-size-base: 16px;
  --font-size-md: 18px;
  --font-size-lg: 20px;
  --font-size-xl: 24px;
  --font-size-2xl: 28px;
  --font-size-3xl: 32px;
  --font-size-4xl: 42px;
  --font-size-5xl: 48px;

  /* Pesos */
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  /* Line heights */
  --line-height-tight: 1.2;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.8;

  /* Espaciados */
  --spacing-xs: 8px;
  --spacing-sm: 15px;
  --spacing-md: 20px;
  --spacing-lg: 30px;
  --spacing-xl: 40px;
  --spacing-2xl: 60px;
  --spacing-3xl: 80px;

  /* Border radius */
  --radius-sm: 5px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-pill: 100px;

  /* Sombras */
  --shadow-card: 0 5px 15px rgba(0, 0, 0, 0.08);
  --shadow-card-hover: 0 10px 25px rgba(0, 0, 0, 0.12);
  --shadow-button: 0 4px 12px rgba(255, 153, 0, 0.25);

  /* Transiciones */
  --transition-fast: 0.2s ease;
  --transition-standard: 0.3s ease;
}
```

---

## 6. CONFIGURACION TAILWIND

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        scram: {
          primary: '#ff9900',
          primaryHover: '#ff8c00',
          secondary: '#44ce6f',
          dark: '#1a1a1a',
          navlink: '#4a6f8a',
          paragraph: '#6084a4',
          light: '#f7fafd',
          lightAlt: '#f9f6f6',
        }
      },
      fontFamily: {
        sans: ['Cabin', 'system-ui', 'sans-serif'],
        heading: ['ASAP', 'sans-serif'],
      },
      borderRadius: {
        'pill': '100px',
      }
    }
  }
}
```

---

## 7. CONFIGURACION MATERIAL UI

```typescript
// theme.ts
const theme = createTheme({
  palette: {
    primary: {
      main: '#ff9900',
      light: '#ffb84d',
      dark: '#cc7a00',
    },
    secondary: {
      main: '#1a1a1a',
      light: '#404040',
    },
    success: {
      main: '#00A859',
    },
    background: {
      default: '#ffffff',
      paper: '#f5f7fa',
    },
    text: {
      primary: '#1e293b',
      secondary: '#475569',
    },
  },
  typography: {
    fontFamily: '"Cabin", system-ui, sans-serif',
    h1: {
      fontFamily: '"ASAP", sans-serif',
      fontWeight: 700,
      fontStyle: 'italic',
    },
    h2: {
      fontFamily: '"ASAP", sans-serif',
      fontWeight: 700,
      fontStyle: 'italic',
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
    },
  },
});
```

---

## 8. EJEMPLOS DE COMPONENTES

### Boton Principal
```html
<button style="
  background: #ff9900;
  color: #ffffff;
  font-family: 'Cabin', sans-serif;
  font-weight: 600;
  font-size: 16px;
  padding: 12px 32px;
  border-radius: 100px;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
">
  Contactar
</button>
```

### Titulo H1
```html
<h1 style="
  font-family: 'ASAP', sans-serif;
  font-weight: 700;
  font-style: italic;
  font-size: 42px;
  line-height: 1.2;
  color: #1a1a1a;
  letter-spacing: -0.02em;
">
  Titulo Principal
</h1>
```

### Tarjeta
```html
<div style="
  background: #ffffff;
  border-radius: 16px;
  padding: 30px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
">
  Contenido de la tarjeta
</div>
```

---

## 9. RESUMEN RAPIDO

**Color principal:** `#ff9900` (Amarillo/Naranja SCRAM)
**Color secundario:** `#1a1a1a` (Negro)
**Acento:** `#44ce6f` (Verde)

**Fuente titulos:** ASAP Bold Italic
**Fuente cuerpo:** Cabin Regular

**Caracteristicas distintivas:**
- Titulos en italica
- Botones pill (border-radius 100px)
- Color amarillo/naranja vibrante
- Sombras suaves
- Transiciones de 0.3s

---

*Documento generado automaticamente a partir del codebase de SCRAM*
*Ultima actualizacion: Diciembre 2024*
