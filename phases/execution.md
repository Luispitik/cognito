# Fase: Execution

## Objetivo

Construir según plan sin desviarse; verificar sobre la marcha.

## Modos activos por defecto

- **Ejecutor**: checklist rígido, zero drift.
- **Verificador**: fact-check continuo.

## Determinismo en esta fase

- **Alto**: plantillas + hooks activos.
- `gate-validator`: **HIGH**. Bloquea anti-patrones críticos.
- `mode-injector`: **high**.
- `phase-detector`: **high** (detecta cuándo pasar a Review).

## Qué NO hacer en Execution

- Diverger (cambia drásticamente el contexto).
- Re-abrir decisiones cerradas en Planning.
- Refactor fuera del scope del plan.
- Ignorar bloqueos del gate-validator.

## Señales de salida

- "Hemos terminado"
- "Hora de revisar"
- "Ship it"
- "Review"

## Reminder para Claude
>
> Sin ideación libre. Si aparece sorpresa, vuelve a Discovery explícitamente (no la resuelvas creativamente aquí).

## Plantillas primarias

- `templates/checklist-deploy.md` (obligatoria).

## Output esperado

- Checklist con estado de cada paso (✓ / ⏳ / ✗).
- Sección de verificación (claims validados, cifras con fuente).
- Bloqueantes explícitos si los hay.
- Sin especulación: solo lo hecho y su estado real.
