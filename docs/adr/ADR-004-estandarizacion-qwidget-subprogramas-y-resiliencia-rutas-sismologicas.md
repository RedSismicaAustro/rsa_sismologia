---
proyecto: rsa_sismologia
tipo: adr
numero: 004
estado: Aprobado
fecha: 2026-08-24
decisores: Usuario, Agente (Antigravity)
---

# ADR-004: Estandarización de Subprogramas como QWidget Puro, Delegación de UI, Resiliencia de Rutas DIA y Consistencia en Formatos Sísmicos

## 1. Contexto y Planteamiento del Problema
Durante el ciclo de integración de los subprogramas en `src/programa_integrado.py`, se identificaron diversas fallas de diseño y fragilidades estructurales:
1. **Conflicto de Jerarquía `QMainWindow` Anidado**: Subprogramas como `marcar_eventos.py` y `extraer_integrado.py` heredaban de `QMainWindow` y montaban su UI reasignando `self.setCentralWidget()`. Al ser incrustados dentro del contenedor central de `VentanaPrincipal`, generaban conflictos de menús, márgenes anómalos y riesgo de corrupción en punteros de Qt/C++.
2. **Fragilidad en la Resolución de Rutas del Repositorio `DIA`**: La función `referencia_directorio_completa` asumía una estructura rígida de carpetas (`DIA/AAAA/AAAA_MM/AAAA_MM_DD`), fallando ante rutas con formatos planos, archivos con prefijos o rutas seleccionadas desde distintas profundidades.
3. **Pérdida de Filtros en el Diálogo de Estaciones**: En `src/librerias/estaciones.py`, la sobrescritura `self.parent.filtros_estaciones = self.filtros` reseteaba los parámetros editados por el analista en la interfaz modal.
4. **Excepciones por Tipos Inmutables en Catálogos**: `ordenar_y_eliminar_duplicados` fallaba con `TypeError` cuando las filas del catálogo eran tuplas en lugar de listas.
5. **Recorte Visual de Títulos en Windows (`QGroupBox`)**: En `panel_estado.py` e `inicio.py`, los títulos de los grupos se mostraban cortados debido a inconsistencias de renderizado en el estilo nativo de Windows.

---

## 2. Decisión Tomada

Se establecieron e implementaron las siguientes directivas arquitectónicas:

1. **Estandarización Canónica de Subprogramas a `QWidget`**:
   * Todos los subprogramas incrustados (`Extraer_evento`, `Marcar_evento`) deben heredar estrictamente de `QWidget`.
   * Los archivos `.ui` asociados (`Extraer.ui`, `marcar_eventos.ui`) se reestructuraron con elemento raíz `<widget class="QWidget">`.
   * Se adoptó el patrón de **delegación transparente** mediante `__getattr__`:
     ```python
     def __getattr__(self, name):
         if 'ui' in self.__dict__ and hasattr(self.ui, name):
             return getattr(self.ui, name)
         raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
     ```
   * Carga directa de la interfaz en un `QHBoxLayout(self)` con panel lateral de controles y área de visualización expansible.

2. **Resolución Heurística y Flexible de Rutas (`referencia_directorio_completa`)**:
   * Implementación de un algoritmo de búsqueda por capas:
     1. Verificación directa de formato canónico `.../DIA/AAAAMMDD000000`.
     2. Búsqueda por expresión regular `(20\d{6})` en el nombre del archivo.
     3. Desglose inverso de las partes de la ruta buscando carpetas con formato de fecha.

3. **Unificación y Corrección del Diálogo de Estaciones (`estaciones.py`)**:
   * Eliminación de la sobrescritura destructiva de filtros.
   * Centralización del guardado en `guardar_configuracion()`, invocado tanto por `closeEvent` como por el nuevo botón `Btn_salir`.

4. **Soporte Híbrido en Deduplicación y Generación Condicional de `.sis`**:
   * `ordenar_y_eliminar_duplicados` maneja tanto listas mutables como tuplas inmutables.
   * La generación de archivos binarios `.sis` (remuestreados a 64 Hz con cabecera) se restringe exclusivamente a eventos clasificados como `SISMO`, con búsqueda multi-candidato de `cabecera_sismo`.

5. **Ergonomía Visual y Corrección CSS de `QGroupBox`**:
   * Aplicación de hojas de estilo con márgenes explícitos (`margin-top: 14px; padding-top: 12px;`) y alineación de subcontroles de título para garantizar legibilidad perfecta en Windows.

---

## 3. Justificación Técnica
- **Aislamiento y Estabilidad Qt**: Un `QWidget` incrustado respeta el ciclo de vida del layout padre sin interferir con la barra de menús o barras de estado de `QMainWindow`.
- **Acceso Limpio a Widgets**: La delegación por `__getattr__` mantiene compatibilidad con todo el código legado sin requerir prefijos `self.ui.` en cada llamada.
- **Robustez de E/S**: El pipeline de extracción y consolidación opera de forma transparente con diferentes esquemas de almacenamiento de datos sísmicos.

---

## 4. Consecuencias e Impacto
- **Positivas**:
  - Subprogramas visualmente cohesivos y estables dentro de `VentanaPrincipal`.
  - Los filtros de estaciones y canales seleccionados persisten fielmente entre ejecuciones.
  - Eliminación de errores de ruta y fallos de tipo al procesar catálogos diarios.
- **Riesgos / Trade-offs**:
  - Los subprogramas restantes (`reporte_diario.py`, `procesamiento_integrado.py`) deben ser migrados a la arquitectura `QWidget` en fases posteriores.

---

## 5. Módulos y Archivos Afectados
- [`src/subprogramas/extraer_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/extraer_integrado.py): Migración a `QWidget`, delegación `__getattr__`, layout horizontal.
- [`src/ui/Extraer.ui`](file:///c:/proyectos/rsa_sismologia/src/ui/Extraer.ui): Raíz convertida a `QWidget`.
- [`src/subprogramas/marcar_eventos.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/marcar_eventos.py): Migración a `QWidget`, delegación `__getattr__`, limpieza de buffers.
- [`src/ui/marcar_eventos.ui`](file:///c:/proyectos/rsa_sismologia/src/ui/marcar_eventos.ui): Raíz convertida a `QWidget`.
- [`src/librerias/rsa_utilidades.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_utilidades.py): Resolución heurística de rutas y generación condicional de `.sis`.
- [`src/librerias/rsa_procesamiento.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_procesamiento.py): Deduplicación resistente a tuplas.
- [`src/librerias/estaciones.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/estaciones.py): Corrección de guardado de filtros y botón de salida.
- [`src/librerias/panel_estado.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/panel_estado.py): Estilos CSS anti-recorte y layout responsivo.
- [`src/subprogramas/inicio.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio.py): Estilos de grupo y ajuste de proporciones de panel.
