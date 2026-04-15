# Fase: Review

## Objetivo
Revisar lo hecho, extraer aprendizajes, preparar cierre.

## Modos activos por defecto
- **Auditor**: post-mortem, QA outputs, lessons learned.
- **Devil's Advocate**: crítica de lo entregado antes de shipping.

## Determinismo en esta fase
- **Medio-Alto**: plantilla de auditoría obligatoria.
- `gate-validator`: **medium** (todavía algunas gates aplican).
- `mode-injector`: **high**.
- `session-closer`: **HIGH** (registrar todo lo relevante para futuras retros).

## Qué NO hacer en Review
- Entrar en nuevas features (eso abre un nuevo ciclo).
- Auditar con opiniones sin evidencia.
- Hacer blame storm.

## Señales de salida
- "Listo para entregar"
- "Vamos a shipping"
- "Aprendizajes capturados"
- "Nada más que revisar"

## Reminder para Claude
> No entres en nuevas features. Auditar lo hecho y capturar lessons. Cada lección debe ser formulable como regla.

## Plantillas primarias
- `templates/auditoria-output.md` (obligatoria).

## Output esperado
- Auditoría completa: retener / corregir / añadir.
- Lessons learned formuladas como reglas (candidatos a Sinapsis instincts).
- Veredicto: LISTO / AJUSTAR / REPLANTEAR.
- Si AJUSTAR: lista de acciones antes de Shipping.
