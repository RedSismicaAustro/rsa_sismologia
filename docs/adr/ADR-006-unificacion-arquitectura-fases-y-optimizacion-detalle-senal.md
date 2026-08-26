---
proyecto: rsa_sismologia
tipo: adr
numero: "006"
estado: Aprobado
fecha: 2026-08-25
decisores: [Usuario, Agente]
---

# ADR-006: Unificación Arquitectónica de Fases Sísmicas y Optimización de Señal a Detalle

## 1. Contexto y Planteamiento del Problema

Durante el uso operativo del subprograma de marcado de fases (`src/subprogramas/fases.py`), se identificaron tres problemas arquitectónicos críticos:
1. **Desalineación del Selector de Fecha**: `marcar_fases.ui` contaba con un `QDateEdit` independiente que retenía rutas anteriores o entraba en conflicto con la fecha global definida en `Inicio -> Inicialización de día` de `programa_integrado.py`.
2. **Ambigüedad en el Descubrimiento de Sismos**: La búsqueda de sismos dependía de archivos binarios `.sis` en disco o de listas de rutas tentativas, lo que provocaba que eventos reclasificados a `FF`, `FC` o `INDEFINIDO` aparecieran indebidamente o que el cambio de fecha mostrara cero eventos.
3. **Sobrecarga Visual e Inflexibilidad en `VentanaGrafico`**: La subventana de zoom carecía del nombre descriptivo de la estación, mantenía una leyenda flotante (`ax.legend()`) que tapaba la traza y requería alternar herramientas manualmente para ampliar la señal sin un control ágil de mouse.

---

## 2. Decisión Tomada

Se adoptaron cuatro decisiones arquitectónicas estructurantes:

1. **Eliminación del Selector de Fecha en Fases**: Se suprimieron el widget `date_edit` y su etiqueta de `marcar_fases.ui`. La jornada de trabajo es inyectada exclusivamente por `programa_integrado.py` mediante `self.archivo`, alineando `fases.py` con el patrón arquitectónico de `marcar_eventos.py`, `extraer_integrado.py` y `procesamiento_integrado.py`.
2. **El CSV como Fuente Única de Verdad de Clasificación**: Los sismos del día se descubren leyendo el archivo CSV del día mediante `lectura_archivo()` y filtrando de forma determinista las filas donde `fila[2].strip().upper() == 'SISMO'`.
3. **Indicador Explícito de Ausencia de Sismos**: Cuando una jornada no contiene sismos (o aún no han sido clasificados), se despliega un mensaje central en el visualizador Matplotlib y en la barra de estado, evitando pantallas en blanco confusas.
4. **Ergonomía Sismológica Avanzada en `VentanaGrafico`**:
   - Título y encabezado con nombre oficial completo de estación (obtenido de `estaciones.csv`).
   - Retiro total de la leyenda flotante para maximizar el área de inspección de la señal.
   - **Clic Derecho**: Alterna el modo Zoom rectangular (doble clic derecho restaura escala *Home*).
   - **Clic Izquierdo**: Exclusivo para colocación y arrastre de marcas de fase con `GestorFases`.
   - **Barra Superior Compacta**: Selectores de parámetros HYPO71 (Tipo, Polaridad y Peso de P/S) y cálculo en tiempo real de $T_s - T_p$ y distancia epicentral aproximada ($D \approx \Delta t \times 8\text{ km/s}$).
   - **Sincronización Total al Salir**: Actualización atómica de `fases_detectadas`, `.json`, binario canónico `.fas` y controles de la ventana principal al cerrar la subventana.

---

## 3. Justificación Técnica

- **Coherencia Global del Sistema**: Elimina estados divergentes de fecha y asegura que el cambio de día se centralice en `Inicialización de día`.
- **Determinismo Operativo**: La matriz CSV delimita estrictamente qué registros son sismos, independientemente de archivos remanentes en disco.
- **Eficiencia en Análisis Sísmico**: El analista puede ampliar rápidamente la señal con un clic derecho, picar la fase con clic izquierdo, ajustar polaridad/peso en la barra superior y cerrar con `Esc`, quedando todo guardado y sincronizado automáticamente.
- **Alternativas descartadas**:
  - *Mantener el calendario local en `fases.py`*: Descartado por romper la máquina de estados del contenedor principal.
  - *Detectar sismos por escaneo de archivos `.sis` en `dia/`*: Descartado porque no refleja reclasificaciones a ruido o eventos no sísmicos.

---

## 4. Consecuencias e Impacto

- **Positivas**:
  - Navegación fluida y homogénea en toda la suite sismológica.
  - Interfaz de picado rápido y ergonómico sin colisiones entre zoom y marcas.
  - Persistencia canónica dual garantizada (`.json` estructurado y binario de 16 ranuras `.fas`).
- **Riesgos / Trade-offs Mitigados**:
  - La restricción de `GestorFases` a `evento.button == 1` previene desplazamientos accidentales de líneas al usar el botón derecho para zoom.

---

## 5. Módulos y Archivos Afectados

- `src/ui/marcar_fases.ui`: Eliminación de `date_edit` y actualización de etiqueta a `"Sismos del día:"`.
- `src/subprogramas/fases.py`: Simplificación de `cargar_dia()`, integración de `VentanaGrafico` optimizada y método `actualizar_controles_estacion_activa()`.
- `src/librerias/gestor_fases.py`: Restricción estricta de interacción al clic izquierdo (`button == 1`).
- `src/subprogramas/procesamiento_integrado.py`: Soporte de filtro global `'TODOS'` en `cargar_combo_eventos()`.
- `src/subprogramas/fases_contx.md`, `src/librerias/gestor_fases_contx.md`, `src/subprogramas/procesamiento_integrado_contx.md`: Actualización de contextos técnicos.