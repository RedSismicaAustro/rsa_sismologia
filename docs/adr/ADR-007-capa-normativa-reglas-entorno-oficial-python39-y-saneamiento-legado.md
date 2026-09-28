---
proyecto: rsa_sismologia
tipo: adr
numero: "007"
estado: Aprobado
fecha: 2026-09-25
decisores: [Usuario, Agente]
---

# ADR-007: Institución de la Capa Normativa `.agents/rules/`, Declaración del Entorno Oficial Python 3.9 y Saneamiento de Artefactos Legados

## 1. Contexto y Planteamiento del Problema

Durante la sesión de reconocimiento inicial se detectaron cinco defectos estructurales en la gobernanza y el entorno del agente:

1. **Referencia Normativa Rota**: Los seis documentos oficiales del protocolo (`AGENTS.md` §6, `README.md`, `docs/contexto_maestro_agente.md`, `ayuda/manual_repositorio.html`, `ayuda/guia_uso_agente.html` y la plantilla de sesión del usuario) instruyen textualmente *"Considera las reglas y skills definidos en `.agents/rules` y `.agents/skills`"*. Sin embargo, `.agents/` contenía **únicamente** `skills/` (4 archivos): el directorio `rules/` **no existía**. La primera instrucción de cada sesión apuntaba a una ruta inexistente en su mitad normativa.
2. **Ausencia de Capa Normativa Propia**: Las reglas operativas del proyecto vivían embutidas dentro de `AGENTS.md` (200+ líneas) mezcladas con identidad, contratos de datos y protocolo de sesión. No existía un lugar donde alojar reglas **atómicas**, citables por nombre, ni donde declarar formalmente la **jerarquía de precedencia** entre fuentes.
3. **Conflicto de Autoridad Ya Materializado**: La skill `generar_contexto.md` ordena escribir en `docs/context/<nombre>_context.md` y actualizar un índice alojado **en GitHub** (`RSA-Metodologias`), lo que contradice la convención real del repositorio (`<script>_contx.md` junto al script) y la **Regla Madre 2** (cero acceso a GitHub). Al no existir capa de reglas, **no había dónde registrar el desempate**.
4. **Ambigüedad del Entorno de Ejecución**: Los 7 lanzadores `.bat` operativos y `Spyder.bat` invocan `C:\entornos\venv_py309` (**Python 3.9**), mientras `src/entorno.yml` declara un entorno conda `sismologia` con **Python 3.11**; coexistían archivos `.pyc` de `cpython-39` y `cpython-311` en los `__pycache__`. **ObsPy —núcleo del procesamiento sísmico— es estable y funcional en Python 3.9 y no en 3.11**, por lo que la ambigüedad no era inocua.
5. **Contaminación por Artefactos Legados**: `src/programa_integrado_alt.py` (629 líneas, versión guardada muy antigua e inarrancable) seguía contando como módulo activo y aparecía como **segundo importador de 5 subprogramas**, distorsionando el grafo de dependencias. Persistía además un `.pyc` huérfano y los dos reportes de auditoría estaban desactualizados (foto previa a un mes de trabajo: no reflejaban, por ejemplo, las 1.454 líneas actuales de `subprogramas/fases.py`).

---

## 2. Decisión Tomada

Se adoptaron tres decisiones arquitectónicas estructurantes:

1. **Institución de la Capa Normativa `.agents/rules/`**: Se crearon **6 reglas atómicas** bajo el modelo **`AGENTS.md` canónico + reglas que referencian sin duplicar**:
   - `00-prioridad-y-alcance.md`: jerarquía de precedencia de 6 niveles, reglas de desempate, Scope Lock y vigencia.
   - `10-codigo-python.md`: entorno oficial, estilo, rutas Windows, excepciones y retrocompatibilidad.
   - `20-interfaz-pyqt5.md`: invariantes C++, flujo `.ui`/Qt Designer, subprogramas `QWidget`, `QThread`, UX/UI.
   - `30-datos-sismologicos.md`: token `EEEECBFFIISS`, offset `+3`, árbol `DIA`, prohibiciones sobre datos.
   - `40-prohibiciones.md`: Reglas Madres, lista negra de acciones y autorizaciones requeridas.
   - `50-sesion-documentacion.md`: protocolo de apertura/cierre, artefactos y gobernanza de librerías compartidas.
   Se declara la jerarquía **Reglas Madres → `AGENTS.md` → `.agents/rules/` → `.agents/skills/` → `_contx.md` → código**, y la regla de desempate *"gana el nivel menor y el agente reporta la discrepancia"*. En el mismo acto se **anula formalmente** la salida `docs/context/` y el índice en GitHub de la skill `generar_contexto.md`, estableciendo como canónica la ruta `<script>_contx.md` junto al script.
2. **Declaración del Entorno Oficial Python 3.9**: Se declara `C:\entornos\venv_py309\Scripts\python.exe` (**Python 3.9.0**) como intérprete **oficial, único y de validación**, por ser el entorno donde ObsPy es estable. Se marca `src/entorno.yml` (conda `sismologia`, Python 3.11) como **legado / no operativo** mediante cabecera de advertencia en el propio archivo, y se **prohíbe la sintaxis y las APIs exclusivas de Python 3.10+** (`match/case`, `typing.Self`, `tomllib`, `ExceptionGroup`, etc.).
3. **Saneamiento de Artefactos Legados**: Se archivó `src/programa_integrado_alt.py` en `obsoletos/src/` **preservando el original íntegro** (629 líneas verificadas) y **sin borrarlo**, acompañado de su contexto técnico tipo *tombstone* y de su fila en la tabla de correspondencia de `AGENTS.md`. Se eliminó el bytecode huérfano `src/__pycache__/programa_integrado_alt.cpython-39.pyc` y se **regeneraron** los dos reportes de auditoría con el intérprete oficial 3.9, desde la raíz del repositorio.

---

## 3. Justificación Técnica

- **Cierre de la Referencia Rota**: La instrucción de apertura de sesión quedó válida **sin necesidad de editar los prompts** en los seis documentos que los contienen; bastó con crear la ruta que ya se citaba.
- **Ley Atómica y Citable**: Cada regla es un archivo de un solo tema, invocable por nombre en una sesión (*"aplica `.agents/rules/20-interfaz-pyqt5.md`"*), en lugar de exigir la lectura íntegra de un manifiesto de 200+ líneas para extraer ~10 reglas operativas.
- **Desempates Registrados**: El conflicto skill ↔ convención ↔ Regla Madre dejó de ser una decisión implícita de cada sesión y pasó a ser **norma escrita y auditable**, eliminando la causa de que un agente pudiera concluir legítimamente *"no hay reglas que considerar"*.
- **Entorno Inequívoco**: La validación se centraliza en un único intérprete verificable (Python 3.9.0 confirmado en consola), eliminando el riesgo de proponer código incompatible con el ObsPy operativo.
- **Fuente Única de Verdad sin Duplicación**: Al mantener `AGENTS.md` como canónico y hacer que las reglas lo **referencien**, se evita el escenario más peligroso de una capa normativa: dos copias de la ley que se desincronizan.
- **Auditoría Limpia y Topología Real**: Con el módulo archivado, la topología de dependencias quedó en **estrella** (solo `programa_integrado.py` importa los subprogramas) y los reportes pasaron a reflejar el estado real de 33 archivos Python.
- **Alternativas descartadas**:
  - *Mantener todas las reglas únicamente en `AGENTS.md`*: Descartado porque deja la referencia de apertura rota y convierte el manifiesto en un documento monolítico sin reglas citables.
  - *Invertir el modelo (`.agents/rules/` canónico y `AGENTS.md` como simple índice)*: Descartado por el usuario para no añadir riesgo de desincronización ni migrar las Reglas Madres fuera del manifiesto.
  - *Adoptar `docs/context/` y el índice en GitHub según la letra de la skill*: Descartado por violar la Regla Madre 2 y duplicar una convención ya asentada en 27 archivos `_contx.md`.
  - *Migrar el proyecto a Python 3.11 / entorno conda*: Descartado porque ObsPy —núcleo del procesamiento— no es estable allí, según la experiencia operativa del usuario.
  - *Borrar definitivamente `programa_integrado_alt.py`*: Descartado para preservar el respaldo histórico del orquestador.
  - *Reparar el módulo archivado para dejarlo ejecutable*: Descartado porque no aporta valor operativo y su restauración introduciría regresiones ya superadas (lanzamiento del reporte por `subprocess`, `paintEvent` sin `painter.end()`).

---

## 4. Consecuencias e Impacto

- **Positivas**:
  - El protocolo de inicio de sesión es ahora **autoconsistente**: la ruta que ordena consultar existe y está indexada.
  - Existe un lugar formal para declarar precedencias, prohibiciones y autorizaciones, con reglas atómicas citables.
  - El entorno de ejecución es **inequívoco y verificable**: Python 3.9 para todo el procesamiento sísmico.
  - Los reportes de auditoría dejaron de contar módulos muertos y reflejan la topología real en estrella.
  - El módulo archivado dispone de trazabilidad completa: contexto *tombstone* (9 secciones), fila en el índice de `AGENTS.md` y registro de sus importaciones rotas (`FileMonitor` renombrado a `FileMonitorThread`; `activar_hilo` convertido en método), lo que **documenta objetivamente que es inarrancable** y desalienta su restauración.
- **Riesgos / Trade-offs Mitigados**:
  - *Divergencia `AGENTS.md` ↔ `.agents/rules/`*: Mitigado por la regla de no-duplicación y por la obligación de que, ante contradicción, gane `AGENTS.md` y la regla se corrija **en la misma sesión**.
  - *Reintroducción accidental del módulo archivado en `src/`*: Mitigado por las prohibiciones explícitas de su contexto y por la advertencia de que falsearía de nuevo la auditoría.
  - *Envejecimiento de los reportes de auditoría*: Se documenta que son artefactos **generados** (no se actualizan solos) y que deben regenerarse con el intérprete 3.9 desde la raíz tras cada refactorización relevante.
  - *Fricción deliberada en la escritura de código*: La prohibición de sintaxis 3.10+ limita opciones de estilo, pero es el precio de garantizar compatibilidad con el ObsPy operativo.

---

## 5. Módulos y Archivos Afectados

- `.agents/rules/00-prioridad-y-alcance.md`, `10-codigo-python.md`, `20-interfaz-pyqt5.md`, `30-datos-sismologicos.md`, `40-prohibiciones.md`, `50-sesion-documentacion.md`: **Creación** de la capa normativa completa (6 reglas atómicas).
- `AGENTS.md`: Retitulación de §6 a *"(.agents/rules y .agents/skills)"*, nueva tabla índice de las 6 reglas con la declaración de prevalencia, y nueva fila en la tabla de correspondencia de contextos para el módulo archivado.
- `src/entorno.yml`: Cabecera de advertencia que lo declara **legado / no operativo** y fija el entorno oficial Python 3.9 (contenido YAML intacto).
- `src/programa_integrado_alt.py` → `obsoletos/src/programa_integrado_alt.py`: **Traslado íntegro** (629 líneas, 26.254 bytes) por no ser importado por ningún módulo.
- `obsoletos/src/programa_integrado_alt_contx.md`: **Creación** del contexto técnico del módulo archivado (estado `obsoleto_archivado`, prohibiciones de uso, diferencias frente al sucesor).
- `docs/contexto_gobernanza_agente.md`: **Creación** del contexto técnico de la capa de gobernanza (jerarquía, entornos, contratos operativos, desempates resueltos, riesgos).
- `reporte_arquitectura_rsa.md`, `reporte_librerias_rsa.md`: **Regeneración** con el intérprete oficial 3.9 desde la raíz del repositorio (33 archivos Python; cero menciones del módulo archivado).
- `src/__pycache__/programa_integrado_alt.cpython-39.pyc`: **Eliminación** del bytecode huérfano.
