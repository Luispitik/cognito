# Cognito Dashboard

Dashboard web estático para visualizar la actividad de Cognito: fases, modos, gates, sesiones, integración Sinapsis.

## Stack

- **HTML estático** + **Tailwind CSS** (CDN) + **Chart.js** (CDN) + **vanilla JS**
- **Sin build step**: abres `index.html` y funciona.
- **Sin backend**: lee un único `data.json` generado por un script Python.
- **Portable**: funciona offline una vez cargadas las CDNs.

## Arquitectura

```
dashboard/
├── index.html         ← entry point
├── styles.css         ← estilos complementarios a Tailwind
├── app.js             ← fetch data.json + render charts/tablas
├── data.json          ← (generado, .gitignore) datos consolidados
├── api/
│   └── build_data.py  ← consolida sessions/ + logs/ → data.json
├── serve.sh           ← regenera data y sirve vía http.server
└── README.md
```

## Cómo funciona

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│ sessions/*.json │ ───▶ │ build_data.py    │ ───▶ │   data.json     │
│ logs/*.log      │      │  (consolidación) │      │                 │
│ config/*.json   │      └──────────────────┘      └────────┬────────┘
└─────────────────┘                                         │
                                                            ▼
                                              ┌─────────────────────────┐
                                              │  index.html + app.js    │
                                              │  (render browser)       │
                                              └─────────────────────────┘
```

## Uso rápido

```bash
# 1. Generar datos
python3 dashboard/api/build_data.py

# 2. Servir (regenera data + abre puerto)
bash dashboard/serve.sh

# 3. Abrir en navegador
# http://localhost:8765
```

## Vistas

### Header

- Fase actual con color dinámico
- Perfil activo
- Botón "Refrescar"

### KPIs (4 cards)

- Sesiones totales
- Modos distintos usados (de 7)
- Gates disparados
- Detecciones de fase sugeridas

### Charts

- **Uso por modo** (bar horizontal): cuántas inyecciones por modo
- **Sesiones por fase** (doughnut): distribución por fase de cierre
- **Actividad reciente** (line 30d): sesiones + gates + inyecciones por día
- **Top 10 gates disparados**: con barra de proporción

### Sinapsis bridge

- Badge ○ Standalone / ● Activo
- Si activo: versión, count de instincts, auto-detect

### Tabla de sesiones recientes

- Session ID, fecha relativa, fase, métricas

## Regenerar datos periódicamente

En un cron o scheduled task:

```bash
# Cada 10 min
*/10 * * * * cd ~/cognito && python3 dashboard/api/build_data.py
```

O confía en el botón "Refrescar" del dashboard (que NO regenera, solo re-lee data.json).

## Personalización

### Cambiar el puerto

```bash
bash dashboard/serve.sh --port 8080
```

### Apuntar a otra instalación Cognito

```bash
bash dashboard/serve.sh --cognito-dir ~/otro-cognito
```

### Cambiar colores

Edita la constante `PALETTE` en `app.js`.

### Cambiar branding

Edita el `<header>` de `index.html`. La C en la esquina es el logo default.

## Deploy remoto (opcional)

Si quieres exponer el dashboard a tu equipo:

1. **GitHub Pages** (si no hay datos sensibles):
   - Habilita Pages en el repo, branch `gh-pages` sirviendo `/dashboard/`.
   - Genera `data.json` en el CI con datos anónimos.

2. **Vercel / Netlify** (static hosting):
   - Deploy `dashboard/` como static site.
   - `build_data.py` como build step en CI.

3. **Privado con auth**:
   - Servidor propio con nginx + basic auth.
   - Regenera `data.json` cada hora con cron.

## Limitaciones v1

- **Solo lectura**: no se puede modificar config desde el dashboard (por diseño).
- **Sin auto-refresh**: requiere clic en "Refrescar" o F5.
- **Sin filtros temporales interactivos**: el rango lo decide `build_data.py` (últimos 30 días por defecto).

## Roadmap dashboard

- [ ] v1.1: auto-refresh cada 60s vía WebSocket o polling
- [ ] v1.2: filtros por fecha, fase, modo
- [ ] v1.3: comparativa entre perfiles
- [ ] v1.4: export CSV/PDF de la vista actual
- [ ] v2.0: integración bidireccional (editar config desde dashboard)
