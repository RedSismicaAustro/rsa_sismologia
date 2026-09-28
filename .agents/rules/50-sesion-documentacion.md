---
proyecto: rsa_sismologia
tipo: regla_agente
archivo: .agents/rules/50-sesion-documentacion.md
temas: [protocolo_sesion, scope_lock, skills, adr, transiciones, cierre]
origen: AGENTS.md
---

# 50 — Protocolo de Sesión y Documentación Obligatoria

> **Propósito**: Definir cómo se abre, se conduce y se cierra una sesión de trabajo, y qué artefactos documentales deben quedar en disco al terminar.

---

## 1. Apertura de Sesión (Scope Lock)

```text
Considera las reglas y skills definidos en .agents/rules y .agents/skills.
Para esta sesión, nuestro directorio de trabajo exclusivo será [DIRECTORIO]. No modifiques ni busques archivos fuera de esta ruta a menos que te lo pida.
Revisa los archivos del directorio [DIRECTORIO] para que entiendas el contexto actual del proyecto. Todavia no modifiques ni crees ningun archivo.
```

**Obligaciones del agente al abrir**:
1. Leer `AGENTS.md` y los archivos de `.agents/rules/` aplicables a la tarea.
2. Leer los `_contx.md` de los módulos que estén dentro del alcance declarado.
3. **No modificar ni crear ningún archivo** hasta recibir la instrucción explícita.
4. Revisar la última transición técnica en [`docs/transiciones/`](../../docs/transiciones) para conocer el estado real del proyecto.

---

## 2. Cierre de Sesión (secuencia de 4 pasos)

| Paso | Instrucción del usuario | Artefacto producido | Skill |
|:---:|:---|:---|:---|
| 1 | *"Genera o actualiza el contexto técnico de los archivos modificados…"* | `<script>_contx.md` **junto al script** | [`generar_contexto.md`](../skills/generar_contexto.md) |
| 2 | *"Extrae o actualiza el ADR de las decisiones tomadas…"* | `docs/adr/ADR-NNN-<titulo>.md` | [`extraer_adr.md`](../skills/extraer_adr.md) |
| 3 | *"Genera la transición técnica de esta sesión…"* | `docs/transiciones/transicion_YYYYMMDD_HHMM.md` | [`crear_transicion_tecnica.md`](../skills/crear_transicion_tecnica.md) |
| 4 | *"Genera un resumen detallado de todos los cambios…"* | Resumen en el chat de la sesión | — |

> [!NOTE]
> El **paso 1 se rige por [`00-prioridad-y-alcance.md`](00-prioridad-y-alcance.md) §2**: la salida canónica es `<script>_contx.md` en el directorio del script. Se ignoran las rutas `docs/context/` y el índice en GitHub que menciona la skill.

---

## 3. Documentación: qué se escribe y dónde

| Artefacto | Ubicación canónica | Nomenclatura |
|:---|:---|:---|
| Contexto técnico de módulo | Junto al script | `<nombre_sin_extension>_contx.md` |
| Decisión arquitectónica | `docs/adr/` | `ADR-NNN-titulo-corto-en-espanol.md` |
| Transición / handover | `docs/transiciones/` | `transicion_YYYYMMDD_HHMM.md` |
| Contexto maestro / estructura de datos | `docs/` | `contexto_*.md` |

* Los `_contx.md` documentan: flujo (Mermaid), contratos de datos, métodos clave, riesgos y checklist de regresión.
* Los ADR preservan el **porqué** de los cambios estructurales; se actualizan respetando el histórico, no se reescriben.
* **Nunca dejar referencias rotas**: si se crea, mueve o renombra un recurso, se actualizan los documentos que lo citan en la misma sesión.

---

## 4. Modificación de Librerías Compartidas

Antes de tocar cualquier función de [`src/librerias/`](../../src/librerias) (skill [`auditoria_librerias_e_integracion.md`](../skills/auditoria_librerias_e_integracion.md)):

1. **Mapear llamadores** con búsqueda de texto en `src/subprogramas/` y `modulos externos/`.
2. **Diseñar retrocompatibilidad** con parámetros opcionales.
3. **Notificar el impacto** al usuario en un bloque explícito (función modificada, módulo en depuración, scripts pendientes de compatibilizar).
4. **Registrar la deuda** en la sección de riesgos del `_contx.md` de cada script afectado.
5. **No tocar los demás scripts en la misma sesión**, salvo petición expresa.
6. Integrar en [`src/programa_integrado.py`](../../src/programa_integrado.py) solo cuando el módulo satélite complete su depuración y compatibilización.

---

## 5. Cierre de Cada Respuesta

* Al terminar una tarea, presentar un **resumen claro y estructurado** de archivos creados, modificados, movidos o depurados.
* Declarar siempre el **estado de verificación**: qué se validó con Python 3.9 y qué quedó pendiente de validación operativa por el usuario.
* La validación final de resultados (dayplots, MiniSEED/EVT, catálogos CSV, fluidez de las interfaces PyQt5) corresponde al **usuario**.

---

## 6. Checklist de Verificación

- [ ] Respeté el Scope Lock durante toda la sesión.
- [ ] Leí los `_contx.md` antes de editar y los actualicé después.
- [ ] Generé los artefactos de cierre en sus rutas canónicas.
- [ ] Notifiqué el impacto si toqué librerías compartidas.
- [ ] No dejé referencias rotas ni documentación desactualizada.
- [ ] Entregué el resumen final de cambios con su estado de verificación.
