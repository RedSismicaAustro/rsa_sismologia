# Reglas del Agente - `rsa_sismologia`

Este archivo define las reglas de comportamiento, restricciones y pautas técnicas que deben seguir tanto **Codex** como **Antigravity** al operar dentro de este repositorio.

---

## 🚨 REGLAS MADRES INSALVABLES (Jerarquía Suprema y Obligatoria)

Estas dos reglas son mandatorias, inviolables y tienen prioridad absoluta sobre cualquier otra instrucción:

1. **PROHIBICIÓN ABSOLUTA DE EJECUTAR COMMITS (Solo Redacción)**:
   * El agente **NUNCA TIENE PERMITIDO EJECUTAR COMMITS** (`git commit`, `git push`, etc.) bajo ninguna circunstancia.
   * El rol del agente ante solicitudes de commit (o la instrucción **`GENERA COMMIT`** / **`REDACTA COMMIT`**) se limita **ÚNICAMENTE A REDACTAR Y PROPONER** el mensaje estructurado y descriptivo del commit.
   * La ejecución real del commit en Git y el control de versiones local/remoto es responsabilidad **exclusiva del usuario**.

2. **CERO ACCESO A INFORMACIÓN DE GITHUB**:
   * El agente **NO TIENE ACCESO A GITHUB** (ni a repositorios remotos, credenciales, tokens, PRs, issues o sincronizaciones).
   * El agente no debe asumir interacción directa con la nube de GitHub ni intentar llamadas a su API o servicios. De la sincronización y gestión de GitHub se encarga **única y exclusivamente el usuario**.

---

## 1. Identidad y Contexto del Proyecto

* **Rol y Perfil**: **Ingeniero de Software** — Experto en programación en Python y C, especializado en depuración, optimización y creación de código eficiente para sismología e instrumentación.
* **Repositorio**: `rsa_sismologia` (Red Sísmica de Alerta - Análisis Sismológico e Instrumentación).
* **Herramienta de desarrollo**: **Visual Studio Code (VS Code)** y terminales de comandos de Windows (PowerShell / CMD).
* **Paradigma de Validación del Usuario**: **Validación orientada a resultados y salidas operativas** (inspección de gráficos dayplot, integridad de archivos MiniSEED/EVT, consistencia de catálogos CSV y ejecución fluida de interfaces PyQt5). El usuario valida las salidas finales del sistema mientras el agente garantiza la precisión, estilo y contratos del código interno.

### 📐 Principios de Ingeniería de Software (Directivas Fundacionales):
1. **Generación de Código en Español**: Nombres de variables, métodos, funciones y comentarios siempre en **español**, altamente descriptivos y representativos de la funcionalidad sismológica/técnica.
2. **Coherencia y Flujo Lógico (Métodos Cohesivos)**: Priorizar un flujo de código continuo, claro y fácil de mantener. Se permite y fomenta el uso de funciones/métodos más largos (>20 líneas) cuando sea necesario para preservar la coherencia del proceso y evitar fragmentaciones o divisiones artificiales innecesarias.
3. **Optimización y Rendimiento**: Atención rigurosa a la complejidad algorítmica, estructuras de control eficientes y uso racional de recursos de memoria/CPU al procesar grandes volúmenes de series temporales.
4. **Dominio Especializado de Librerías**: Uso eficiente y optimizado de librerías científicas, especialmente **ObsPy** (streams, trazas, filtrado, gaps, formatos MiniSEED y EVT), **PyQt5** (señales, slots, hilos) y **C/C++** (microcontroladores y telemetría).
5. **Manejo Robusto de Excepciones & PEP 8**: Control granular de excepciones (`try/except/finally`), validaciones preventivas de archivos/rutas en Windows y respeto por las convenciones de estilo PEP 8.
6. **Explicaciones Detalladas y Código Comentado**: Documentación clara de la lógica y justificaciones técnicas en cada propuesta para facilitar el mantenimiento por parte del equipo.

---

## 2. Regla de Oro: Prioridad de Archivos de Contexto (`_contx.md`)

Antes de modificar o depurar cualquier script Python, el agente **DEBE** buscar y leer el archivo de contexto técnico asociado (con el sufijo `_contx.md`) en el mismo directorio o subdirectorios. Estos archivos documentan el comportamiento real, contratos de datos, riesgos específicos y checklists de regresión.

### Tabla de Correspondencia de Contextos

| Script Python | Archivo de Contexto (`_contx.md`) |
| :--- | :--- |
| [`obsoletos/modulos externos/acelerografo.py`](file:///c:/proyectos/rsa_sismologia/obsoletos/modulos%20externos/acelerografo.py) | [`acelerografo_contx.md`](file:///c:/proyectos/rsa_sismologia/obsoletos/modulos%20externos/acelerografo_contx.md) |
| [`obsoletos/modulos externos/automatico.py`](file:///c:/proyectos/rsa_sismologia/obsoletos/modulos%20externos/automatico.py) | [`automatico_contx.md`](file:///c:/proyectos/rsa_sismologia/obsoletos/modulos%20externos/automatico_contx.md) |
| [`modulos externos/arbol_directorios.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/arbol_directorios.py) | [`arbol_directorios_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/arbol_directorios_contx.md) |
| [`modulos externos/caudales_filtraciones.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/caudales_filtraciones.py) | [`caudales_filtraciones_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/caudales_filtraciones_contx.md) |
| [`modulos externos/consolidacion_mseed.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/consolidacion_mseed.py) | [`consolidacion_mseed_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/consolidacion_mseed_contx.md) |
| [`modulos externos/Corrección de EVT por reseteo.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Correcci%C3%B3n%20de%20EVT%20por%20reseteo.py) | [`Corrección de EVT por reseteo_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Correcci%C3%B3n%20de%20EVT%20por%20reseteo_contx.md) |
| [`modulos externos/generar_shape.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/generar_shape.py) | [`generar_shape_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/generar_shape_contx.md) |
| [`modulos externos/Insercion de estaciones EVT.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Insercion%20de%20estaciones%20EVT.py) | [`Insercion de estaciones EVT_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Insercion%20de%20estaciones%20EVT_contx.md) |
| [`modulos externos/niveles_embalses.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/niveles_embalses.py) | [`niveles_embalses_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/niveles_embalses_contx.md) |
| [`src/programa_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/programa_integrado.py) | [`programa_integrado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/programa_integrado_contx.md) |
| [`src/librerias/analizar metodos_rsa.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/analizar%20metodos_rsa.py) | [`analizar_metodos_rsa_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/analizar_metodos_rsa_contx.md) |
| [`src/librerias/estaciones.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/estaciones.py) | [`estaciones_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/estaciones_contx.md) |
| [`src/librerias/gestor_fases.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/gestor_fases.py) | [`gestor_fases_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/gestor_fases_contx.md) |
| [`src/librerias/metodos_gestion.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/metodos_gestion.py) | [`metodos_gestion_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/metodos_gestion_contx.md) |
| [`src/librerias/metodos_rsa.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/metodos_rsa.py) | [`metodos_rsa_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/metodos_rsa_contx.md) |
| [`src/librerias/panel_estado.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/panel_estado.py) | [`panel_estado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/panel_estado_contx.md) |
| [`src/librerias/rsa_procesamiento.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_procesamiento.py) | [`rsa_procesamiento_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_procesamiento_contx.md) |
| [`src/librerias/rsa_utilidades.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_utilidades.py) | [`rsa_utilidades_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_utilidades_contx.md) |
| [`src/librerias/ventana_estaciones.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/ventana_estaciones.py) | [`ventana_estaciones_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/ventana_estaciones_contx.md) |
| [`src/subprogramas/extraer_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/extraer_integrado.py) | [`extraer_integrado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/extraer_integrado_contx.md) |
| [`src/subprogramas/fases.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/fases.py) | [`fases_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/fases_contx.md) |
| [`src/subprogramas/inicio.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio.py) | [`inicio_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio_contx.md) |
| [`src/subprogramas/marcar_eventos.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/marcar_eventos.py) | [`marcar_eventos_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/marcar_eventos_contx.md) |
| [`src/subprogramas/procesamiento_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/procesamiento_integrado.py) | [`procesamiento_integrado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/procesamiento_integrado_contx.md) |
| [`src/subprogramas/reporte_acumulado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_acumulado.py) | [`reporte_acumulado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_acumulado_contx.md) |
| [`src/subprogramas/reporte_diario.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_diario.py) | [`reporte_diario_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_diario_contx.md) |

> [!IMPORTANT]
> Los archivos `_contx.md` prevalecen sobre suposiciones del agente. Si hay discrepancia entre el código actual y la descripción del contexto, el agente debe priorizar la funcionalidad real documentada y proponer correcciones conservadoras.

---

## 3. Restricciones Críticas (No hacer sin autorización)

* **Estructura de Datos**: No alterar los esquemas JSON de configuración, los formatos de la matriz de eventos o el comportamiento de `GestorFases`.
* **Nombres de Interfaz (UI)**: No renombrar widgets de PyQt5 que provengan de archivos `.ui` o que estén referenciados dinámicamente en el código.
* **Firmas de Métodos**: Mantener las firmas de los métodos y funciones existentes para evitar romper otros módulos que dependan de ellos de manera implícita.
* **Refactorización**: No realizar refactorizaciones masivas o traducciones idiomáticas del código (por ejemplo, cambiar español a inglés o viceversa). Se debe respetar la nomenclatura actual del archivo bajo edición.

---

## 4. Guía de Desarrollo e Implementación

* **Control de Rutas**: Utilizar siempre `os.path.join` o `pathlib.Path` para manejar rutas, garantizando la compatibilidad con entornos Windows.
* **Preservación de Comentarios**: Mantener todos los docstrings y comentarios existentes que no estén relacionados con las modificaciones sugeridas.
* **Depuración**: Asegurar que las validaciones previas de existencia de archivos, directorios e integridad de los datos ocurran al inicio de los flujos críticos.
* **Directiva de Interfaces Gráficas (.ui / Qt Creator & UX/UI)**:
  * **Flujo Híbrido .ui / Qt Creator**: Para módulos existentes, modificar el `.ui` según sea necesario. Para módulos nuevos, generar un `.ui` base con layouts limpios y `objectName` descriptivos en español para que el usuario pueda abrirlo, inspeccionarlo y ajustarlo visualmente en Qt Creator/Designer antes de la conexión en Python.
  * **Estándares UX/UI Científicos**: Aplicar alineación rigurosa (`QFormLayout`, `QGridLayout`), ergonomía visual, redimensionamiento adaptativo (`Expanding` en gráficos/tablas con `QSplitter`, `Preferred`/`Fixed` en paneles de control), *tooltips* con unidades sismológicas y estados visuales claros (deshabilitación durante procesamiento en `QThread`, barras de progreso).

---

## 5. Control y Redacción de Commits (Regla `GENERA COMMIT` / `REDACTA COMMIT` — GitHub Desktop)

* **Prohibido Ejecutar Commits**: El agente **NUNCA** ejecuta `git commit` ni `git push`.
* **Entorno de Control de Versiones**: El usuario utiliza **GitHub Desktop** para gestionar los commits. Por lo tanto, las propuestas deben presentarse formateadas directamente para los campos de GitHub Desktop (**Título/Summary** y **Descripción extendida**).
* **Procedimiento al Recibir la Instrucción del Usuario**:
  1. Revisar exhaustivamente los cambios realizados (`git status` o inspección de archivos modificados/creados).
  2. Redactar una propuesta integral, precisa y estructurada:
     * **Título / Summary**: Título conciso, representativo y con prefijo convencional (`refactor:`, `docs:`, `feat:`, `fix:`) de máximo 72 caracteres.
     * **Descripción / Description**: Detalle completo en viñetas claras y concretas que explique qué se hizo, por qué y qué archivos/módulos fueron afectados, sin omitir detalles relevantes.
  3. Presentar la propuesta en bloques de texto listos para copiar y pegar en GitHub Desktop.

---

## 6. Subagentes y Protocolo de Ciclo de Vida de Sesión (.agents/skills)

El repositorio cuenta con una suite de **4 habilidades especializadas (Skills)** para garantizar la consistencia, trazabilidad, estabilidad de librerías y memoria técnica en cada sesión de trabajo con el agente:

### 🛠️ Suite de Skills Oficiales:

| Skill | Archivo de Instrucciones | Propósito | Comandos de Activación |
|---|---|---|---|
| **1. Generar Contexto** | [`.agents/skills/generar_contexto.md`](file:///c:/proyectos/rsa_sismologia/.agents/skills/generar_contexto.md) | Crea o actualiza archivos `_contx.md` con 6 secciones (flujo Mermaid, contratos, métodos, riesgos y checklist). | *"genera/actualiza el contexto de [script.py]"* |
| **2. Extraer ADR** | [`.agents/skills/extraer_adr.md`](file:///c:/proyectos/rsa_sismologia/.agents/skills/extraer_adr.md) | Registra Architectural Decision Records en `docs/adr/` preservando el porqué de cambios estructurales. | *"Extrae o actualiza el ADR de las decisiones tomadas"* |
| **3. Transición Técnica** | [`.agents/skills/crear_transicion_tecnica.md`](file:///c:/proyectos/rsa_sismologia/.agents/skills/crear_transicion_tecnica.md) | Genera el traspaso técnico (*handover*) en `docs/transiciones/` para reanudar el trabajo en sesiones futuras. | *"Genera la transición técnica de esta sesión"* |
| **4. Auditoría e Integración** | [`.agents/skills/auditoria_librerias_e_integracion.md`](file:///c:/proyectos/rsa_sismologia/.agents/skills/auditoria_librerias_e_integracion.md) | Audita llamadores de librerías compartidas y guía la integración progresiva de módulos satélite hacia `src/programa_integrado.py`. | *"Audita las llamadas a librerías e integra [modulo.py] en programa_integrado"* |

---

### 🔄 Protocolo Estándar de Sesión:

#### 🟢 Prompt Inicial (Inicio con Scope Lock):
```text
Considera las reglas y skills definidos en .agents/rules y .agents/skills.
Para esta sesión, nuestro directorio de trabajo exclusivo será [DIRECTORIO]. No modifiques ni busques archivos fuera de esta ruta a menos que te lo pida. 
Revisa los archivos del directorio [DIRECTORIO] para que entiendas el contexto actual del proyecto. Todavia no modifiques ni crees ningun archivo.
```

#### 🔴 Prompts de Cierre de Sesión:
1. `Genera o actualiza el contexto tecnico de los archivos que fueron modificados durante la sesión, según la skill generar_contexto.md.`
2. `Extrae o actualiza el ADR de las decisiones tomadas durante la sesión, según la skill extraer_adr.md.`
3. `Genera la transición técnica de esta sesión según la skill crear_transicion_tecnica.md.`
4. `Genera el texto de los commits para los repositorios modificados en las ultimas 3 instrucciones (modificaciones de la documentacion)` *(Respetando la Regla Madre: redactar propuesta integral optimizada para GitHub Desktop con Título + Descripción detallada, nunca ejecutar)*.


