# Fase: Shipping

## Objetivo
Entregar con máxima fiabilidad. Determinismo máximo.

## Modos activos por defecto
- **Ejecutor**: checklist de entrega estricto.
- **Verificador**: validación continua pre-release.

## Determinismo en esta fase
- **Máximo**: todos los gates activos, todos los hooks al máximo.
- `gate-validator`: **MAXIMUM**. Zero tolerance para anti-patrones.
- `mode-injector`: **high**.
- `session-closer`: **HIGH**.
- `phase-detector`: **low** (rara vez salimos de shipping hacia atrás).

## Qué NO hacer en Shipping
- Cambios de scope.
- Nuevas features ("ya que estamos...").
- Ignorar bloqueos del gate-validator.
- Atajos "por el momento" (deuda técnica disfrazada).

## Señales de salida
- "Entregado"
- "Cerrado"
- "Siguiente proyecto"
- "Archivo"

## Reminder para Claude
> Solo ejecución verificada. Cualquier duda: posponer y volver a Review.

## Plantillas primarias
- `templates/checklist-deploy.md` (versión shipping).

## Output esperado
- Checklist completo con 100% ✓.
- Verificación documentada de todos los claims.
- Artefactos de entrega listos (release notes, changelog, handoff doc).
- Veredicto: ENTREGADO + timestamp.

## Post-shipping automático
Al completar Shipping, `session-closer.sh` registra:
- Qué se entregó.
- Qué modos/fases se usaron.
- Qué gates se dispararon.
- Lessons candidatas a promoción (Sinapsis instincts si aplica).
