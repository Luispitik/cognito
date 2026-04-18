# Plantilla — Checklist de Ejecución / Deploy

Usa esta plantilla en modo **Ejecutor** (fases Execution y Shipping).

---

## Metadata

- **Plan ejecutado**: [nombre/referencia]
- **Fase Cognito**: Execution / Shipping
- **Iniciado**: [timestamp]
- **Operador**: [perfil]

## Pre-check (obligatorio antes de cualquier paso)

- [ ] Plan aprobado en fase Planning (matriz decisión + pre-mortem firmados).
- [ ] Prerequisites verificados:
  - [ ] [Dependencia 1]
  - [ ] [Dependencia 2]
  - [ ] [Credencial / acceso 1]
- [ ] Backup o plan de rollback definido y ensayado.
- [ ] Ventana de ejecución confirmada (si aplica).
- [ ] Stakeholders notificados (si aplica).
- [ ] Gates de Cognito revisados: ningún bloqueo pendiente conocido.

**Si alguno sin ✓**: no iniciar. Resolver primero.

## Pasos de ejecución

### Paso 1: [Nombre del paso]

- [ ] Acción: [descripción]
- Verificación de éxito: [criterio concreto]
- Si falla: [acción específica, NO improvisar]
- Estado: ⏳ pendiente / 🟢 ejecutando / ✓ completado / ✗ fallido

### Paso 2: [Nombre del paso]

- [ ] Acción: [...]
- Verificación: [...]
- Si falla: [...]
- Estado: ...

### Paso N:

## Post-check

- [ ] Todos los pasos completados con ✓.
- [ ] Tests automáticos pasan.
- [ ] Smoke tests manuales:
  - [ ] [Test 1]
  - [ ] [Test 2]
- [ ] Logs sin errores críticos en los últimos X minutos.
- [ ] Métricas de éxito medidas y dentro de rango:
  - [ ] [Métrica 1]: valor [v], rango esperado [r]
  - [ ] [Métrica 2]: ...
- [ ] Documentación actualizada (README, changelog, runbook si aplica).
- [ ] Handoff doc generado (si shipping a cliente).

## Rollback (si procede)

### Condición de activación

[Evidencia concreta que dispara rollback]
*Ejemplo: "Error rate > 1% durante 5 minutos consecutivos", no "si algo va mal"*

### Pasos de rollback

1. [...]
2. [...]
3. [...]

### Post-rollback

- [ ] Root cause analysis iniciado.
- [ ] Stakeholders notificados.
- [ ] Volver a fase Review antes de re-intentar.

## Progreso actual

```
Progreso global: [X]/[N] ([X%])
Bloqueantes: [lista o "ninguno"]
ETA restante: [estimación]
```

## Bloqueantes (actualizar según aparezcan)

| # | Bloqueante | Causa probable | Acción requerida | Dueño |
|---|------------|----------------|------------------|-------|
| 1 | [...] | [...] | [...] | [...] |

Si hay bloqueantes, **parar ejecución** hasta resolverlos. No improvisar.

---

## Validación del checklist

- [ ] Cada paso tiene acción concreta y verificación específica.
- [ ] Cada "si falla" es una acción predefinida, no improvisación.
- [ ] Rollback tiene condición accionable.
- [ ] Pre-check y post-check están completos.
- [ ] No hay pasos vagos tipo "verificar que todo está bien".
