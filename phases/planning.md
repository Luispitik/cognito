# Fase: Planning

## Objetivo
Decidir qué hacer, anticipar fallos, consolidar trade-offs.

## Modos activos por defecto
- **Devil's Advocate**: pre-mortem, crítica estructurada.
- **Consolidador**: matriz decisión, convergencia explícita.
- **Estratega**: criterios estratégicos en la matriz.

## Determinismo en esta fase
- **Medio**: plantillas fijas (pre-mortem, matriz) + análisis libre.
- `gate-validator`: activo en nivel **medium** (empiezan a importar anti-patrones técnicos).
- `mode-injector`: **high**.
- `phase-detector`: **normal**.

## Qué NO hacer en Planning
- Re-abrir exploración pura (para eso está Discovery).
- Ejecutar cualquier acción (para eso está Execution).
- Decidir sin pre-mortem en decisiones irreversibles.

## Señales de salida
- "Vamos a ejecutar"
- "Plan aprobado"
- "Manos a la obra"
- "Implementa"

## Reminder para Claude
> Antes de ejecutar: pre-mortem + matriz decisión + plan B. No hay planning sin veredicto claro.

## Plantillas primarias
- `templates/pre-mortem.md` (obligatoria si decisión de alto impacto).
- `templates/matriz-decision.md` (obligatoria).
- `templates/steel-man.md` (opcional, recomendada).

## Output esperado
- Pre-mortem con 3+ causas raíz y mitigaciones.
- Matriz decisión con criterios operacionalizables.
- Recomendación + Plan B + métricas de revisión.
- Checklist preliminar para Execution.
