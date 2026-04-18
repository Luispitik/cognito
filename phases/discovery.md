# Fase: Discovery

## Objetivo

Entender el problema, explorar el espacio de soluciones, evitar cerrarse pronto.

## Modos activos por defecto

- **Divergente** (principal): anti-ancla, exploración de alternativas.
- **Estratega** (secundario): perspectiva temporal y de stakeholder.

## Determinismo en esta fase

- **Bajo**: creatividad importa más que rigidez.
- `gate-validator`: activo en nivel **low** (solo anti-patrones muy críticos como commitear `.env`).
- `mode-injector`: **high** (inyectar bien los dos modos).
- `phase-detector`: **normal**.

## Qué NO hacer en Discovery

- Converger prematuramente en una solución.
- Bloquear ideas por "implementabilidad" antes de explorar.
- Cerrar scope sin entender requisitos.

## Señales de salida (suggest phase change)

- "Tenemos los requisitos"
- "Vamos a planificar"
- "Suficiente exploración"
- "Ya tengo claro qué hacer"

## Reminder para Claude
>
> Aún es pronto para cerrar opciones. Diverge antes de converger. No pongas pesos a alternativas todavía.

## Plantillas primarias

Ninguna obligatoria en Discovery — la estructura del modo Divergente es suficiente.

## Output esperado

- Lista de alternativas (mínimo 5).
- Análisis de stakeholders si aplica.
- Horizontes temporales si decisión estratégica.
- Sin decisión final (esa es responsabilidad de Planning).
