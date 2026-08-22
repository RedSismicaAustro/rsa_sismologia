# Skill: Crear Transición Técnica (Handover de Sesión)

> [!IMPORTANT]
> **Reglas Madres:** Esta habilidad genera el documento de transición exclusivamente en el sistema de archivos local. El agente **NO ejecuta commits** ni interactúa con la nube de GitHub.

**Descripción de Activación:** Ejecuta este flujo cuando el usuario indique:
* *"Genera la transición técnica de esta sesión según la skill crear_transicion_tecnica.md."*
* *"Genera el handover de esta sesión"*

**Objetivo:** Crear un documento de relevo técnico (*Handover*) que resuma el estado exacto del proyecto al cierre de la sesión, los cambios implementados, las tareas pendientes y las instrucciones precisas para que la próxima sesión de IA (o el propio usuario) retome el trabajo sin perder contexto.

---

## Pasos de Ejecución

### 1. Recolección del Estado de la Sesión
Revisar:
- Archivos creados, modificados, renombrados o migrados.
- Tareas completadas vs. tareas pendientes o pendientes de validación por el usuario.
- Riesgos descubiertos, bloqueos o consideraciones para la siguiente sesión.

### 2. Ubicación y Nomenclatura del Archivo
- **Ruta de destino**: `docs/transiciones/` (crear el directorio si no existe).
- **Formato de nombre**: `transicion_YYYYMMDD_HHMM.md` (ej. `transicion_20260821_1915.md`).

### 3. Plantilla Estándar de la Transición Técnica

```markdown
---
proyecto: rsa_sismologia
tipo: transicion_tecnica
fecha: YYYY-MM-DD HH:MM
sesion_id: [Identificador o fecha/hora]
estado_general: [Completado / En Progreso / Bloqueado]
---

# Transición Técnica de Sesión — YYYY-MM-DD

## 1. Resumen Ejecutivo de la Sesión
[Breve descripción de los objetivos abordados y el resultado global alcanzado.]

## 2. Trabajo Realizado y Archivos Modificados
| Archivo / Recurso | Tipo de Acción | Detalle Técnico |
|---|---|---|
| `[ruta/archivo.py]` | Creado / Editado / Migrado | [Descripción del cambio] |
| `[ruta/archivo_contx.md]` | Contexto actualizado | [Secciones añadidas o ajustadas] |

## 3. Estado Actual del Sistema (Invariantes y Salidas)
- **Compilabilidad / Sintaxis**: [Verificado sin errores]
- **Compatibilidad**: [VS Code / Windows / ObsPy / PyQt5]
- **Salidas Operativas**: [Gráficos, catálogos o archivos MiniSEED validados]

## 4. Tareas Pendientes / Próximos Pasos (Backlog Inmediato)
1. **[Tarea 1]**: [Descripción de lo que debe hacerse a continuación]
2. **[Tarea 2]**: [Validación o prueba pendiente]

## 5. Instrucciones para la Siguiente Sesión de IA
> **Mensaje de Reanudación**: Al iniciar la siguiente sesión, lee este archivo junto con `AGENTS.md` y los `_contx.md` relevantes para continuar desde este punto sin alterar el trabajo completado.
```

### 4. Confirmación al Usuario
- Indicar la ruta del archivo de transición creado.
- Mostrar una síntesis de los próximos pasos prioritarios.
