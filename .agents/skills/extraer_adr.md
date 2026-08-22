# Skill: Extraer y Registrar ADR (Architectural Decision Record)

> [!IMPORTANT]
> **Reglas Madres:** Esta habilidad documenta decisiones de arquitectura exclusivamente en archivos locales del repositorio. El agente **NO ejecuta commits** ni interactúa con servicios o APIs remotas de GitHub.

**Descripción de Activación:** Ejecuta este flujo cuando el usuario indique:
* *"Extrae o actualiza el ADR de las decisiones tomadas durante la sesión, según la skill extraer_adr.md."*
* *"Registra el ADR de esta sesión"*

**Objetivo:** Capturar y registrar decisiones de diseño, refactorizaciones estratégicas, migraciones de módulos o cambios arquitectónicos críticos ocurridos durante la sesión, garantizando que el razonamiento técnico quede preservado para futuras intervenciones.

---

## Pasos de Ejecución

### 1. Detección de Decisiones Clave
Analizar el trabajo realizado en la sesión para identificar:
- **Cambios estructurales**: Unificación de módulos, eliminación/migración de scripts a `obsoletos/`, creación de pipelines.
- **Contratos y esquemas**: Nuevas reglas de nombrado, formatos de datos (MiniSEED, CSV, EVT).
- **Herramientas o estándares**: Migración de entornos (ej. Spyder ➔ VS Code), directivas del Ingeniero de Software.

### 2. Ubicación y Nomenclatura del Archivo ADR
- **Ruta de destino**: `docs/adr/` (crear el directorio si no existe).
- **Formato de nombre**: `ADR-[NUM]-[titulo_corto_en_espanol].md` (ej. `ADR-001-unificacion-consolidacion-mseed.md`).
- Si ya existe un ADR para el tema, actualizarlo respetando el histórico.

### 3. Plantilla Estándar del ADR

```markdown
---
proyecto: rsa_sismologia
tipo: adr
numero: [NUM]
estado: [Aprobado / Propuesto / Superado]
fecha: YYYY-MM-DD
decisores: [Usuario / Agente]
---

# ADR-[NUM]: [Título Descriptivo de la Decisión]

## 1. Contexto y Planteamiento del Problema
[Describir la necesidad operativa, deuda técnica o motivación que originó la decisión.]

## 2. Decisión Tomada
[Explicar claramente la solución adoptada, los componentes involucrados y la nueva arquitectura.]

## 3. Justificación Técnica
- **Ventaja 1**: [Por qué es mejor que la alternativa previa]
- **Ventaja 2**: [Impacto en rendimiento, mantenimiento o claridad]
- **Alternativas consideradas y descartadas**: [Otras opciones evaluadas y por qué no se eligieron]

## 4. Consecuencias e Impacto
- **Positivas**: [Mejoras operativas, simplificación de código, coherencia]
- **Riesgos / Trade-offs**: [Limitaciones a considerar, cambios en scripts `.bat` o rutas]

## 5. Módulos y Archivos Afectados
- `[ruta/archivo1.py]`: [Qué cambió]
- `[ruta/archivo2_contx.md]`: [Actualización de contexto]
```

### 4. Confirmación al Usuario
- Indicar la ruta del ADR generado.
- Presentar un resumen ejecutivo de 3 viñetas con la decisión adoptada.
