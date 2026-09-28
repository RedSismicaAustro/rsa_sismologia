---
proyecto: rsa_sismologia
tipo: regla_agente
archivo: .agents/rules/00-prioridad-y-alcance.md
temas: [jerarquia_normativa, precedencia, scope_lock, vigencia, desempate]
origen: AGENTS.md
---

# 00 — Prioridad, Alcance y Jerarquía Normativa

> **Propósito**: Establecer qué fuente manda cuando dos instrucciones se contradicen, y delimitar el alcance territorial del agente en cada sesión. Esta es la regla que se lee **primero**.

---

## 1. Jerarquía de Precedencia (de mayor a menor autoridad)

| Nivel | Fuente | Naturaleza |
|:---:|:---|:---|
| **1** | **Reglas Madres** — [`AGENTS.md`](../../AGENTS.md) (sección *REGLAS MADRES INSALVABLES*) | Inviolables. Solo el usuario puede modificarlas. |
| **2** | [`AGENTS.md`](../../AGENTS.md) | Manifiesto canónico del repositorio: identidad, contratos de datos, restricciones y protocolo de sesión. |
| **3** | **`.agents/rules/`** (estos archivos) | Capa normativa operativa. **Referencian** a `AGENTS.md`, no lo copian. |
| **4** | **`.agents/skills/`** | Procedimientos de producción documental (contexto, ADR, transición, auditoría). |
| **5** | **`_contx.md`** del script intervenido | Memoria técnica específica del módulo. Prevalece sobre las suposiciones del agente. |
| **6** | **Código y estado real en disco** | Fuente de verdad de último recurso, siempre que 1–5 no lo contradigan. |

**Regla de desempate**: ante contradicción, **manda el nivel numéricamente menor** y el agente **debe reportar la discrepancia** en el chat de la sesión; nunca resolverla en silencio.

---

## 2. Conflicto ya resuelto (caso registrado)

> [!IMPORTANT]
> La skill [`generar_contexto.md`](../skills/generar_contexto.md) indica generar la documentación en `docs/context/<nombre>_context.md` y actualizar un índice alojado en **GitHub** (`RSA-Metodologias`).
>
> **Esa indicación queda anulada por esta regla**, por dos motivos:
> 1. Contradice la **Regla Madre 2** (cero acceso a GitHub) — nivel 1 vence a nivel 4.
> 2. Contradice la convención real y verificada del repositorio.
>
> **Convención canónica vigente**: el contexto técnico se escribe como **`<nombre_del_script>_contx.md`, en el mismo directorio que el script**. Cualquier paso de la skill que exija `docs/context/`, `_context.md` o GitHub se ignora.

---

## 3. Alcance Territorial (Scope Lock)

1. El usuario declara en cada sesión un **directorio de trabajo exclusivo**.
2. El agente **no lee, no busca y no modifica** archivos fuera de esa ruta, salvo petición explícita.
3. Si una tarea requiere salir del alcance, **el agente lo pide antes de actuar**, explicando por qué.
4. **Nunca** se escriben archivos fuera del repositorio `rsa_sismologia` ni sobre las unidades de datos sismológicos (`G:\Mi unidad\DIA\`, `O:\`, `K:\`, `M:\`, `P:\`, `L:\`, `N:\`), que son **datos operativos de producción**, no código.

---

## 4. Vigencia y Mantenimiento de estas Reglas

* Si cualquier archivo de `.agents/rules/` contradice a `AGENTS.md`, **gana `AGENTS.md`** y la regla debe corregirse o retirarse en esa misma sesión.
* **Prohibida la duplicación de la ley**: las Reglas Madres viven únicamente en `AGENTS.md`. Estos archivos las citan por referencia.
* Toda regla nueva debe ser **atómica** (un tema por archivo) y **citable por nombre** para poder invocarla en una sesión: *"aplica `.agents/rules/20-interfaz-pyqt5.md`"*.
* Los archivos de reglas **no llevan fecha de generación**: son documentos estables, no artefactos de sesión.

---

## 5. Checklist de Verificación

- [ ] Identifiqué el nivel jerárquico de cada instrucción recibida.
- [ ] Confirmé que mi alcance respeta el Scope Lock declarado.
- [ ] Ante cualquier contradicción, la reporté en lugar de resolverla en silencio.
- [ ] No dupliqué contenido de `AGENTS.md` en esta carpeta.
