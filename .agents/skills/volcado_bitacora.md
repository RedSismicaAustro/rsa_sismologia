# Skill: Volcado de Bitácora de Sesión

> [!IMPORTANT]
> **Reglas Madres:** La bitácora se almacena y actualiza de manera 100% local. El agente **NO ejecuta commits** ni interactúa con servicios o repositorios remotos de GitHub.

**Descripción de Activación:** Ejecuta este flujo cuando el usuario indique:
* *"Ejecuta el volcado de bitácora de esta sesión según la skill volcado_bitacora.md."*
* *"Actualiza la bitácora de trabajo"*

**Objetivo:** Mantener un registro cronológico, estructurado e incremental de todas las sesiones de desarrollo, depuración, refactorización y documentación ejecutadas en el repositorio.

---

## Pasos de Ejecución

### 1. Lectura de la Bitácora Existente
- Ubicación principal: `docs/bitacora/bitacora_trabajo.md` (o `bitacora.md` en la raíz si aplica; crear `docs/bitacora/` si no existe).
- Si el archivo no existe, inicializarlo con encabezado y tabla de contenidos.

### 2. Formato de Entrada de Sesión

Añadir la nueva entrada **al inicio de la lista cronológica** (orden descendente, la sesión más reciente arriba):

```markdown
## [YYYY-MM-DD] Sesión: [Título Breve de la Jornada]

* **Hora / Duración**: [HH:MM - HH:MM]
* **Objetivos Principales**:
  - [Objetivo 1]
  - [Objetivo 2]
* **Acciones Realizadas**:
  1. [Acción detallada 1]
  2. [Acción detallada 2]
* **Archivos Afectados**:
  - `[ruta/archivo1]` ([Creado / Modificado / Movido])
  - `[ruta/archivo2]` ([Contexto / Documentación])
* **Resultados y Validaciones**:
  - [Validación técnica, estado de la suite de pruebas o confirmación de salida]
* **Decisiones Clave**:
  - [Referencia a ADR si aplica o decisión de diseño]

---
```

### 3. Escritura y Verificación
- Insertar la entrada preservando todas las sesiones anteriores sin sobreescribir el historial histórico.
- Asegurar que las rutas a los archivos usen la sintaxis correcta del proyecto.

### 4. Confirmación al Usuario
- Confirmar que la sesión ha sido volcada en `docs/bitacora/bitacora_trabajo.md`.
- Mostrar un extracto de 3 líneas con el resumen de la entrada registrada.
