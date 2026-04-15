---
description: Activa o desactiva un modo puntual de Cognito como override (no cambia la fase). Uso `/modo <nombre>` o `/modo off <nombre>` o `/modo list`.
argument-hint: [divergente|verificador|devils-advocate|consolidador|ejecutor|estratega|auditor|off <nombre>|list]
---

# /modo

Activa un modo puntual (override) sin cambiar la fase del proyecto.

## Tu tarea

Parsea `$ARGUMENTS`:

### `/modo <nombre>` — activar

1. Valida que `<nombre>` exista en `~/.claude/cognito/config/_modes.json → modes`.
2. Lee `~/.claude/cognito/config/_phase-state.json`.
3. Añade `<nombre>` a `overrideModes` si no está ya.
4. Guarda estado.
5. Aplica el modo al contexto actual: lee el SKILL.md del modo (`modes/<nombre>/SKILL.md`) y sigue sus instrucciones para el turno.
6. Reporta:

   ```
   ✓ Modo activado: [nombre]
   Fase actual: [current] — sin cambios
   Modos activos ahora: [defaults de fase + overrides]
   ```

### `/modo off <nombre>` — desactivar override

1. Lee `_phase-state.json`.
2. Quita `<nombre>` de `overrideModes`.
3. Guarda.
4. Reporta:

   ```
   ✓ Override desactivado: [nombre]
   Modos activos ahora: [defaults de fase]
   ```

Nota: `/modo off <nombre>` solo quita override. Si el modo está activo por ser default de la fase, sigue activo hasta cambiar de fase.

### `/modo list` — listar modos

Muestra:

```
🧠 Modos activos
Fase: [current]
Por defecto: [lista con ✓]
Overrides: [lista con ⭐]
Disponibles (no activos): [resto]

Para activar: /modo <nombre>
Para desactivar override: /modo off <nombre>
```

### `/modo help <nombre>` — explicar modo

Lee `modes/<nombre>/SKILL.md` y muestra:

```
## [Modo nombre]

Determinismo: [low/medium/high]
Plantilla: [path o "ninguna"]
Fases por defecto: [lista]

[Resumen del principio rector]

Triggers principales:
- [...]

Reglas clave:
- [...]
```

## Reglas

1. **Si el modo no existe**: mostrar modos disponibles.
2. **Si ya está activo**: reportar "Modo [x] ya está activo".
3. **Validar perfil**: si el perfil activo no tiene el modo habilitado (ver `_operator-config.json → modes.enabled`), avisar.
4. **Conflictos**: si se activa Divergente mientras Ejecutor está activo, advertir que son antagónicos y preguntar si pausar Ejecutor.
