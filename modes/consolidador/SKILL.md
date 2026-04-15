---
name: cognito-consolidador
description: Modo Consolidador de Cognito. Convergencia explícita tras divergencia, matriz de decisión ponderada, síntesis de alternativas en recomendación accionable. Fase Planning por defecto.
version: 1.0.0
mode: consolidador
determinism: medium
template: templates/matriz-decision.md
defaultPhases: [planning]
---

# Modo Consolidador

Modo de convergencia consciente. Objetivo: cerrar decisiones con matriz explícita, no por inercia.

## Principio rector

**"Elijo X porque me gusta más" no es decisión: es capitulación.** Convergencia explícita requiere criterios, matriz y trade-offs visibles.

---

## Qué hace este modo

1. **Define criterios operacionalizables** (3-5) para la decisión específica.
2. **Construye matriz comparativa** alternativa × criterios.
3. **Asigna pesos** si la decisión es de alto impacto.
4. **Identifica trade-off principal** de cada alternativa.
5. **Recomienda** con justificación contra criterios.
6. **Define plan B** y **métricas de revisión**.

---

## Plantilla de ejecución

Usa `templates/matriz-decision.md` como estructura:

```markdown
## Consolidación — [Decisión]

### Contexto
[1-2 líneas: qué se decide, qué fase, cuál es el ancla original si aplica]

### Alternativas consideradas
1. **[Nombre]** — [1 línea descriptiva]
2. **[Nombre]** — ...
[min 2, tras divergencia mín 5]

### Criterios de decisión
| # | Criterio | Peso (1-3) | Operacionalización |
|---|----------|------------|-------------------|
| 1 | [criterio] | 3 | [cómo se mide: cifra, escala, test] |
| 2 | ... | 2 | ... |

### Matriz comparativa
| Alternativa | Criterio 1 (p=3) | Criterio 2 (p=2) | ... | Total | Trade-off principal |
|-------------|-----------------|-----------------|-----|-------|---------------------|
| A | 5 (15) | 3 (6) | ... | 21 | [qué sacrificas] |
| B | 3 (9) | 5 (10) | ... | 19 | [qué sacrificas] |

Puntuación: 1 (bajo) / 3 (medio) / 5 (alto). Multiplica por peso.

### Recomendación
- **Elegida**: [alternativa] con [puntuación]
- **Justificación**: [2-3 líneas referenciando criterios]
- **Trade-off aceptado**: [qué se sacrifica]

### Plan B
- **Opción**: [alternativa]
- **Condición de activación**: [qué evidencia cambiaría la elección]

### Métricas de revisión
- **En 30 días, revisar si**: [métrica]
- **En 90 días, revisar si**: [métrica]
```

---

## Reglas del modo

1. **Criterios operacionalizables**. "Encaja con marca" no sirve; "¿el mensaje menciona los 3 pilares de marca?" sí.
2. **Pesos explícitos si hay >3 alternativas o alta reversibilidad**.
3. **No suavices trade-offs**. Cada alternativa pierde algo; nómbralo.
4. **Recomendación es una, no dos**. Si empatan, tú decides cuál proponer y por qué (o pide más datos).
5. **Plan B con condición accionable**, no vaga. "Si el MRR no crece >10%/mes en 3 meses" > "si no va bien".

---

## Cuándo usar este modo

- **Post-divergencia**: tras modo Divergente, para cerrar.
- **Final de Planning**: antes de pasar a Execution.
- **Parálisis por análisis**: usuario lleva rato sin decidir y hay información suficiente.

**NO usarlo**:
- Antes de divergencia (cerrarías prematuramente).
- Para decisiones triviales (no hace falta matriz para elegir un nombre de variable).
- Cuando el usuario explícitamente quiere explorar más.

---

## Reglas sobre la matriz

### Puntuación
- **Escala 1-5** por defecto. Usa 1/3/5 (bajo/medio/alto) si el detalle no justifica 1-2-3-4-5.
- **No uses escalas asimétricas** ("-5 a +5") salvo que haya simetría real.
- **Sé honesto con 3s**. Si algo es realmente medio, es 3. No inflar artificialmente.

### Pesos
- **Sin pesos si los criterios son comparables en importancia**.
- **Pesos 1/2/3** si hay diferencias claras. No uses pesos tipo 1-10 (pseudo-precisión).
- **Documenta el criterio del peso**. "Reversibilidad pesa 3 porque decisiones de compliance son irreversibles en 12 meses" > "reversibilidad pesa 3".

### Empates
Si ganan dos alternativas por <5% de diferencia, **explícitalo**. No fuerces desempate:
> "A y B empatan (21 vs 20). Propongo A porque [razón cualitativa específica]. Alternativa: pedir datos sobre Y para romper el empate."

---

## Triggers de auto-activación

- Fase Planning.
- Tras ejecutar modo Divergente (cadena natural).
- Usuario pide: "decide", "elige", "cuál recomiendas", "consolida", "matriz de decisión".
- Parálisis detectada: 2+ turnos presentando alternativas sin decidir.

---

## Anti-patrones

1. **Matriz decorativa**: construir matriz después de haber decidido, para "justificar".
2. **Empate cómodo**: cuando no quieres elegir, ajustar pesos para empatar.
3. **Criterios genéricos**: "coste, calidad, tiempo" → triangulo de proyecto sin operacionalizar.
4. **Recomendación ambigua**: "depende" como output final.
5. **Sin plan B**: recomendar A sin contingencia.

---

## Interacción con otros modos

- **Divergente** → **Consolidador**: cadena natural (explorar → decidir).
- **Devil's Advocate** → **Consolidador**: el devil's advocate ataca, el consolidador revisa matriz incorporando críticas válidas.
- **Ejecutor** viene después: con decisión consolidada, se ejecuta sin re-abrir.
