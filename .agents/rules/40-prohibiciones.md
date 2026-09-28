---
proyecto: rsa_sismologia
tipo: regla_agente
archivo: .agents/rules/40-prohibiciones.md
temas: [reglas_madres, prohibiciones, limites_de_autoridad, acciones_destructivas]
origen: AGENTS.md
---

# 40 — Prohibiciones Absolutas y Límites de Autoridad

> **Propósito**: Lista negativa de acciones que el agente **no ejecuta nunca**, con independencia de lo que se le pida o de lo que parezca eficiente. Ante duda, **preguntar antes de actuar**.

---

## 1. Reglas Madres (nivel 1 — inviolables)

### 🚫 Prohibición 1 — Ejecutar commits

* El agente **NUNCA** ejecuta `git commit`, `git push`, `git tag`, `git merge`, `git rebase`, `git reset` ni ninguna otra operación que altere el control de versiones.
* Ante `GENERA COMMIT` / `REDACTA COMMIT`, la labor se limita a **redactar y proponer** el mensaje estructurado y descriptivo.
* La ejecución real en Git y la gestión local/remota es **responsabilidad exclusiva del usuario**.

### 🔒 Prohibición 2 — Acceso a GitHub

* El agente **NO TIENE ACCESO A GITHUB**: ni repositorios remotos, ni credenciales, ni tokens, ni PRs, ni issues, ni sincronizaciones.
* **Prohibido** llamar a la API de GitHub o a cualquier servicio en la nube del proyecto.
* **Prohibido** documentar pasos que exijan subir, enlazar o indexar contenido en GitHub (ver caso resuelto en [`00-prioridad-y-alcance.md`](00-prioridad-y-alcance.md) §2).

---

## 2. Prohibiciones de Estructura y Código (sin autorización expresa del usuario)

| # | Prohibido | Motivo |
|:---:|:---|:---|
| 1 | Alterar esquemas JSON de configuración | Rompe scripts existentes |
| 2 | Alterar el formato de la matriz de eventos o el comportamiento de `GestorFases` | Corrompe catálogos y boletines |
| 3 | Renombrar widgets PyQt5 de archivos `.ui` o referenciados dinámicamente | Rompe la conexión UI ↔ código |
| 4 | Cambiar firmas de métodos y funciones existentes | Rompe dependencias implícitas entre módulos |
| 5 | Refactorizaciones masivas | Dispersa el foco y multiplica el riesgo |
| 6 | Traducciones idiomáticas (español ↔ inglés) | Viola la nomenclatura establecida del proyecto |
| 7 | Borrar archivos de código | Se **mueven** a `obsoletos/` preservando el original |
| 8 | Escribir fuera del Scope Lock declarado | Viola el protocolo de sesión |

---

## 3. Acciones que requieren autorización explícita previa

1. **Mover o archivar** cualquier módulo (incluido el traslado a `obsoletos/`).
2. **Crear directorios o archivos nuevos** fuera del alcance natural de la tarea pedida.
3. **Modificar** `AGENTS.md`, los archivos de `.agents/` o los `_contx.md` de módulos no intervenidos en la sesión.
4. **Ejecutar** cualquier comando de terminal que escriba, mueva o elimine archivos.
5. **Tocar datos operativos** en las unidades de producción sismológica.

---

## 4. Prohibiciones de Conducta Profesional

* **No afirmar que algo funciona sin haberlo verificado** con el intérprete oficial (Python 3.9). Si no se pudo validar, se declara explícitamente.
* **No inventar** rutas, nombres de archivo, APIs ni resultados operativos.
* **No silenciar** una contradicción entre fuentes normativas, código y documentación: se reporta.
* **No presentar trabajo incompleto como terminado**, ni omitir archivos modificados en el resumen de cierre.
* **No resolver la ambigüedad a la fuerza**: si una instrucción es ambigua o destructiva, se pregunta.

---

## 5. Checklist de Verificación

- [ ] No ejecuté ninguna operación Git.
- [ ] No realicé ni propuse ninguna interacción con GitHub o servicios en la nube.
- [ ] No renombré widgets, funciones, ni cambié firmas existentes.
- [ ] No borré archivos (los archivé en `obsoletos/` solo con autorización).
- [ ] Pedí autorización antes de mover, crear o escribir fuera del alcance.
- [ ] Declaré con precisión qué validé y qué quedó sin verificar.
