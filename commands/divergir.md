---
description: Fuerza modo Divergente sobre el problema actual. Salta diagnóstico, ejecuta divergencia (5+ alternativas, 3+ marcos) + convergencia con matriz explícita.
---

# /divergir

Atajo rápido al modo Divergente del sistema Cognito. Asume que el problema ya está definido en la conversación.

## Tu tarea

Sin preguntar, ejecuta este workflow sobre el problema/decisión en curso.

### 1. Activar modo divergente (en segundo plano)

- Añade `divergente` a `overrideModes` en `_phase-state.json` (si no está).

### 2. Re-encuadre breve (máx. 3 líneas)

- **Problema reformulado** sin asumir solución actual.
- **Asunción fundacional** del enfoque previo (la creencia invisible).
- **Pre-mortem en 1 línea**: si fracasa en 6 meses, el motivo más probable es…

### 3. Divergencia forzada

**Mínimo 5 alternativas ejecutivamente distintas** usando **mínimo 3 marcos diferentes** del catálogo (ver `modes/divergente/references/marcos.md`):

- **Inversión (Munger)**: qué evitar
- **Constraint shock**: 1/10× recursos, 100× recursos, sin stack habitual
- **Cross-domain**: cómo lo resuelven en otro sector
- **Primeros principios**: descomponer en verdades irreductibles
- **SCAMPER**: sustituir/combinar/adaptar/modificar/poner/eliminar/reordenar
- **TRIZ contradicción**: separar en tiempo/espacio/condiciones/nivel
- **Random concept (De Bono)**: inyectar concepto sin relación
- **Cambio stakeholder**: competidor, becario, consultor 50k€, IA 2030
- **Time-horizon shift**: cómo se ve en 10 años / 2 semanas
- **Eliminación radical**: ¿y si no haces nada / eliminas el problema?

Cada alternativa con: **nombre corto** *(marco)* — descripción 2-3 líneas — **insight** que revela.

### 4. Matriz de decisión

Usa plantilla `templates/matriz-decision.md`. Define 3-5 criterios operacionalizables (no genéricos).

Tabla: alternativa × criterios × peso, puntuación 1-5, columna final con trade-off.

### 5. Recomendación

- **Elegida** + justificación 2-3 líneas referenciando criterios.
- **Plan B** + condición de activación.
- **Revisar si**: evidencia que cambiaría elección en 1-3 meses.

## Reglas

- No pidas confirmación, ejecuta.
- Mínimo 5 alternativas. Si llegas a 4 y cuesta más, cambia de marco y fuerza 2 más.
- Alternativas ejecutivamente distintas (cambian el *qué* o el *cómo*, no solo el stack).
- No mezcles divergencia y crítica: en Fase 3, todas valen.
- Si el usuario ya tenía razón, dilo. Validar contra 6 alternativas > validar por defecto.
- Aplica contexto del operador (desde `_operator-config.json`): stack retirado, marcas, tarifas, compliance.
- Idioma: español por defecto, tuteo, sin filler.

## Header de output

```
[Modo: Divergente (override) · Fase: [current]]
```
