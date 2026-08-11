# CONTEXTO INTEGRAL DE MANTENIMIENTO V3 EXHAUSTIVA
## `reporte_diario.py` — Sistema de Reporte y Visualización de Eventos Sísmicos Diarios

**Versión del documento:** 3.0 exhaustiva orientada a mantenimiento asistido por agente  
**Fecha:** 2026-06-11  
**Fuente primaria:** `reporte_diario.py`  
**Fuente secundaria:** contexto previo `reporte_diario_contx.md`  

---

# 0. Propósito de esta versión

Este documento reemplaza al contexto anterior y está pensado para que un desarrollador o un agente de mantenimiento pueda trabajar sobre `reporte_diario.py` con menor riesgo.

El objetivo no es solamente describir qué hace el módulo, sino dejar explícitos:

- responsabilidades reales;
- dependencias internas y externas;
- contratos de datos;
- invariantes;
- atributos y estados;
- flujos de ejecución;
- riesgos de modificación;
- deuda técnica;
- matriz método → estado modificado;
- puntos seguros de intervención;
- checklist de regresión.

---

# 1. Papel del módulo dentro del ecosistema RSA

`reporte_diario.py` es el módulo de operación diaria para revisar, visualizar, modificar y consolidar eventos sísmicos de un día ya procesado.

Su papel dentro del sistema es posterior al procesamiento diario y anterior a la generación/consolidación de reportes acumulados.

```text
Procesamiento diario
      ↓
Archivos diarios generados
      ↓
reporte_diario.py
      ↓
Revisión, edición, visualización, inserción de redes externas
      ↓
Guardar_dia()
      ↓
PDF diario + CSV/XML actualizados
      ↓
Reportes acumulados / catálogos históricos
```

---

# 2. Responsabilidades del módulo

## 2.1 Responsabilidades incluidas

- Cargar la información diaria desde archivos generados por el procesamiento.
- Poblar la lista de eventos del día.
- Seleccionar un evento específico.
- Cargar las señales MiniSEED asociadas al evento.
- Graficar señales por estaciones.
- Aplicar filtro pasa banda a las señales cargadas.
- Cambiar el tipo de evento en el reporte diario.
- Insertar información de otras redes, como IGEPN, USGS u otras redes.
- Generar reporte individual de sismo.
- Generar reporte de acelerograma.
- Evaluar calidad diaria de estaciones.
- Guardar los archivos diarios modificados.
- Generar el PDF diario oficial mediante `reporte_resumen_modos()`.
- Liberar recursos gráficos al cerrar.

## 2.2 Responsabilidades excluidas

Este módulo no debería encargarse de:

- localizar eventos sísmicos;
- calcular fases;
- corregir relojes;
- generar catálogos acumulados;
- decidir modos institucionales/oficiales acumulados;
- procesar automáticamente nuevos eventos;
- reemplazar `procesamiento_integrado.py`;
- administrar la estructura completa del proyecto.

---

# 3. Arquitectura general

```text
Reporte_diario (QMainWindow)
│
├── Carga del día
│   ├── showDate()
│   └── cargar_dia()
│
├── Gestión de evento
│   ├── Cargar_evento()
│   ├── Modificar_()
│   ├── Insertar_evento()
│   └── reiniciar_evento()
│
├── Visualización y señal
│   ├── Graficar_()
│   ├── cambio_pagina()
│   ├── filtrar_evento()
│   └── filtro_evento()
│
├── Reportes
│   ├── Guardar_()
│   ├── Generar_reporte_sismo()
│   └── Acelerograma_()
│
├── Calidad de estaciones
│   ├── estacion_calidad()
│   └── estaciones_ (QDialog)
│
└── Cierre
    ├── Salir_()
    ├── limpiar_estado()
    └── closeEvent()
```

---

# 4. Dependencias

## 4.1 Dependencias internas del proyecto

| Dependencia | Elementos usados | Rol |
|---|---|---|
| `rsa_io` | `leer_mseed`, `Guardar_dia` | Lectura de MiniSEED diario y persistencia de archivos diarios |
| `rsa_dominio` | `calidad_estacion` | Cálculo de evaluación/calidad de estaciones |
| `metodos_rsa` | `grafico_evento_int`, `cargar_evento`, `cargar_dia`, `insertar_evento_otras_redes` | Carga, visualización e inserción de datos externos |
| `rsa_pdf_catalogo` | `reporte_resumen_modos` | Generación del PDF diario |
| `metodos_gestion` | `parametros_estaciones`, `obtener_directorios` | Parámetros de estaciones y rutas del sistema |
| `metodos_reportes_individuales` | `generar_reporte_sismo`, `generar_reporte_acelerograma` | Reportes individuales |

## 4.2 Dependencias externas

| Dependencia | Uso |
|---|---|
| `PyQt5` | GUI principal y diálogos |
| `matplotlib` | Figura embebida y gráficas auxiliares |
| `numpy` | Eje temporal para evaluación de ruido |
| `xml.etree.ElementTree` | Construcción de árbol XML para reporte |
| `pathlib` / `os` / `sys` | Rutas del proyecto y configuración de imports |

---

# 5. Clases y funciones

## 5.1. Clase `Reporte_diario`

### Métodos detectados

- `__init__()`
- `reiniciar_estado_dia()`
- `iniciar_variables()`
- `showDate()`
- `cargar_dia()`
- `Guardar_()`
- `estacion_calidad()`
- `reiniciar_evento()`
- `Cargar_evento()`
- `Insertar_evento()`
- `Generar_reporte_sismo()`
- `Graficar_()`
- `cambio_pagina()`
- `Modificar_()`
- `Acelerograma_()`
- `filtrar_evento()`
- `Salir_()`
- `limpiar_estado()`
- `closeEvent()`

### Atributos referenciados en la clase

| Atributo | Observación |
|---|---|
| `Acelerograma_` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_Salir` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_acelerograma` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_estacion` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_filtrar` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_generar` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_graficar` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_guardar` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_insertar` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_limpiar` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_modificar` | Referenciado o asignado dentro de `Reporte_diario` |
| `Btn_pagina` | Referenciado o asignado dentro de `Reporte_diario` |
| `Cargar_evento` | Referenciado o asignado dentro de `Reporte_diario` |
| `Generar_reporte_sismo` | Referenciado o asignado dentro de `Reporte_diario` |
| `Graficar_` | Referenciado o asignado dentro de `Reporte_diario` |
| `Guardar_` | Referenciado o asignado dentro de `Reporte_diario` |
| `Insertar_evento` | Referenciado o asignado dentro de `Reporte_diario` |
| `Lbl_directorio` | Referenciado o asignado dentro de `Reporte_diario` |
| `Modificar_` | Referenciado o asignado dentro de `Reporte_diario` |
| `Salir_` | Referenciado o asignado dentro de `Reporte_diario` |
| `archivo` | Referenciado o asignado dentro de `Reporte_diario` |
| `archivo_comportamiento` | Referenciado o asignado dentro de `Reporte_diario` |
| `archivo_escogido` | Referenciado o asignado dentro de `Reporte_diario` |
| `archivo_reporte` | Referenciado o asignado dentro de `Reporte_diario` |
| `bandera_evento` | Referenciado o asignado dentro de `Reporte_diario` |
| `calendarWidget` | Referenciado o asignado dentro de `Reporte_diario` |
| `cambio_pagina` | Referenciado o asignado dentro de `Reporte_diario` |
| `canales` | Referenciado o asignado dentro de `Reporte_diario` |
| `canvas` | Referenciado o asignado dentro de `Reporte_diario` |
| `cargar_dia` | Referenciado o asignado dentro de `Reporte_diario` |
| `catalogo` | Referenciado o asignado dentro de `Reporte_diario` |
| `cerrado` | Referenciado o asignado dentro de `Reporte_diario` |
| `close` | Referenciado o asignado dentro de `Reporte_diario` |
| `cmbx_evento` | Referenciado o asignado dentro de `Reporte_diario` |
| `cmbx_evento_escogido` | Referenciado o asignado dentro de `Reporte_diario` |
| `cmbx_red` | Referenciado o asignado dentro de `Reporte_diario` |
| `cmbx_tipo_mag` | Referenciado o asignado dentro de `Reporte_diario` |
| `comportamiento` | Referenciado o asignado dentro de `Reporte_diario` |
| `date` | Referenciado o asignado dentro de `Reporte_diario` |
| `detalle` | Referenciado o asignado dentro de `Reporte_diario` |
| `dia_reporte` | Referenciado o asignado dentro de `Reporte_diario` |
| `directorio_trabajo` | Referenciado o asignado dentro de `Reporte_diario` |
| `directorios` | Referenciado o asignado dentro de `Reporte_diario` |
| `enlace` | Referenciado o asignado dentro de `Reporte_diario` |
| `estacion_calidad` | Referenciado o asignado dentro de `Reporte_diario` |
| `estaciones_eventos` | Referenciado o asignado dentro de `Reporte_diario` |
| `evento_canales` | Referenciado o asignado dentro de `Reporte_diario` |
| `evento_escogido` | Referenciado o asignado dentro de `Reporte_diario` |
| `eventos` | Referenciado o asignado dentro de `Reporte_diario` |
| `eventos_reporte` | Referenciado o asignado dentro de `Reporte_diario` |
| `fecha_ini` | Referenciado o asignado dentro de `Reporte_diario` |
| `filtrar_evento` | Referenciado o asignado dentro de `Reporte_diario` |
| `hab_canal` | Referenciado o asignado dentro de `Reporte_diario` |
| `hab_grafico` | Referenciado o asignado dentro de `Reporte_diario` |
| `indice` | Referenciado o asignado dentro de `Reporte_diario` |
| `indice_catalogo` | Referenciado o asignado dentro de `Reporte_diario` |
| `indice_local` | Referenciado o asignado dentro de `Reporte_diario` |
| `label_1` | Referenciado o asignado dentro de `Reporte_diario` |
| `label_2` | Referenciado o asignado dentro de `Reporte_diario` |
| `label_3` | Referenciado o asignado dentro de `Reporte_diario` |
| `label_4` | Referenciado o asignado dentro de `Reporte_diario` |
| `label_5` | Referenciado o asignado dentro de `Reporte_diario` |
| `label_6` | Referenciado o asignado dentro de `Reporte_diario` |
| `lbl_responsable_1` | Referenciado o asignado dentro de `Reporte_diario` |
| `lbl_responsable_2` | Referenciado o asignado dentro de `Reporte_diario` |
| `lbl_responsable_3` | Referenciado o asignado dentro de `Reporte_diario` |
| `limpiar_estado` | Referenciado o asignado dentro de `Reporte_diario` |
| `lista_eventos` | Referenciado o asignado dentro de `Reporte_diario` |
| `n_canales_` | Referenciado o asignado dentro de `Reporte_diario` |
| `nombre_canal` | Referenciado o asignado dentro de `Reporte_diario` |
| `nombre_canal_total_` | Referenciado o asignado dentro de `Reporte_diario` |
| `numero_canal_` | Referenciado o asignado dentro de `Reporte_diario` |
| `pagina` | Referenciado o asignado dentro de `Reporte_diario` |
| `parametros` | Referenciado o asignado dentro de `Reporte_diario` |
| `periodo` | Referenciado o asignado dentro de `Reporte_diario` |
| `reiniciar_estado_dia` | Referenciado o asignado dentro de `Reporte_diario` |
| `reiniciar_evento` | Referenciado o asignado dentro de `Reporte_diario` |
| `responsable` | Referenciado o asignado dentro de `Reporte_diario` |
| `responsables` | Referenciado o asignado dentro de `Reporte_diario` |
| `resumen` | Referenciado o asignado dentro de `Reporte_diario` |
| `root` | Referenciado o asignado dentro de `Reporte_diario` |
| `showDate` | Referenciado o asignado dentro de `Reporte_diario` |
| `sp_Box_finf` | Referenciado o asignado dentro de `Reporte_diario` |
| `sp_Box_fsup` | Referenciado o asignado dentro de `Reporte_diario` |
| `sp_Box_orden` | Referenciado o asignado dentro de `Reporte_diario` |
| `stLeido` | Referenciado o asignado dentro de `Reporte_diario` |
| `textEdit` | Referenciado o asignado dentro de `Reporte_diario` |
| `textEdit_2` | Referenciado o asignado dentro de `Reporte_diario` |
| `tipo_canal_` | Referenciado o asignado dentro de `Reporte_diario` |
| `tr` | Referenciado o asignado dentro de `Reporte_diario` |
| `trCanal` | Referenciado o asignado dentro de `Reporte_diario` |
| `vector` | Referenciado o asignado dentro de `Reporte_diario` |
| `visor` | Referenciado o asignado dentro de `Reporte_diario` |

## 5.2. Clase `estaciones_`

### Métodos detectados

- `__init__()`
- `graficar()`
- `calcular()`
- `closeEvent()`
- `Salir_()`

### Atributos referenciados en la clase

| Atributo | Observación |
|---|---|
| `archivo` | Referenciado o asignado dentro de `estaciones_` |
| `btn_Calcular` | Referenciado o asignado dentro de `estaciones_` |
| `btn_Graficar` | Referenciado o asignado dentro de `estaciones_` |
| `calcular` | Referenciado o asignado dentro de `estaciones_` |
| `ck_box_comentario` | Referenciado o asignado dentro de `estaciones_` |
| `ck_box_disp_canal` | Referenciado o asignado dentro de `estaciones_` |
| `ck_box_hab_canal` | Referenciado o asignado dentro de `estaciones_` |
| `cmb_box_comentario` | Referenciado o asignado dentro de `estaciones_` |
| `destroy` | Referenciado o asignado dentro de `estaciones_` |
| `evaluacion` | Referenciado o asignado dentro de `estaciones_` |
| `graficar` | Referenciado o asignado dentro de `estaciones_` |
| `hab_canal` | Referenciado o asignado dentro de `estaciones_` |
| `indice` | Referenciado o asignado dentro de `estaciones_` |
| `indice_estaciones` | Referenciado o asignado dentro de `estaciones_` |
| `lbl_codigo` | Referenciado o asignado dentro de `estaciones_` |
| `lbl_comportamiento` | Referenciado o asignado dentro de `estaciones_` |
| `lbl_grafico` | Referenciado o asignado dentro de `estaciones_` |
| `lbl_nombre` | Referenciado o asignado dentro de `estaciones_` |
| `lnedit_eval_canal` | Referenciado o asignado dentro de `estaciones_` |
| `numero_estaciones` | Referenciado o asignado dentro de `estaciones_` |
| `parametros` | Referenciado o asignado dentro de `estaciones_` |
| `parent` | Referenciado o asignado dentro de `estaciones_` |
| `setFixedSize` | Referenciado o asignado dentro de `estaciones_` |
| `sp_box_canal` | Referenciado o asignado dentro de `estaciones_` |
| `tr_Canal` | Referenciado o asignado dentro de `estaciones_` |

## 5.3. Función local `filtro_evento()`

La función `filtro_evento()` aplica un filtro pasa banda directamente sobre los streams recibidos y luego redibuja usando `grafico_evento_int()`.

### Punto crítico

El filtrado se aplica **in-place**:

```python
stLeido[canal_].filter("bandpass", ...)
```

Esto significa que la señal original cargada en `trCanal` se modifica. Si se desea volver a la señal sin filtrar, debe recargarse el evento o conservarse una copia previa.

---

# 6. Modelo de datos principal

## 6.1 `self.eventos_reporte`

Estructura usada para mostrar y guardar eventos reportables del día.

| Índice | Campo | Descripción |
|---:|---|---|
| 0 | Nº | Número del evento en el día |
| 1 | Fecha; Hora (UTC) | Fecha y hora formateada |
| 2 | Evento | Tipo: SISMO, FF, FC, Ruido, etc. |
| 3 | Magn. | Magnitud |
| 4 | Prof.(km) | Profundidad |
| 5 | Lat. | Latitud |
| 6 | Long. | Longitud |
| 7 | Ubicación | Descripción textual |

### Contrato

- La fila 0 siempre es cabecera.
- Las filas desde índice 1 representan eventos.
- `Modificar_()` modifica la columna 2 y limpia la columna 3.
- `Insertar_evento()` puede modificar `eventos_reporte`.

## 6.2 `self.catalogo`

Catálogo detallado del día. Se obtiene desde `cargar_dia()` externo.

| Índice | Campo | Descripción |
|---:|---|---|
| 0 | Id | Identificador del evento |
| 1 | año | Año |
| 2 | mes | Mes |
| 3 | día | Día |
| 4 | hora | Hora |
| 5 | min | Minuto |
| 6 | seg | Segundo |
| 7 | lat | Latitud |
| 8 | long | Longitud |
| 9 | prof | Profundidad |
| 10 | rms | RMS |
| 11 | e-x | Error X |
| 12 | e-y | Error Y |
| 13 | e-0 | Error profundidad |
| 14 | e-z | Error vertical |
| 15 | Mag | Magnitud |
| 16 | Tipo Mag | Tipo de magnitud |
| 17 | Fuente | RSA, IGEPN, USGS u otra red |
| 18 | ruta | Ruta relativa del evento |
| 19 | Ubicación | Lugar |

### Contrato

- Debe existir antes de `Cargar_evento()`, `Insertar_evento()`, `Generar_reporte_sismo()`, `Acelerograma_()` y `Guardar_()`.
- Debe permanecer sincronizado con `eventos_reporte`.
- Debe permanecer sincronizado con el XML `root`.

## 6.3 `self.eventos`

Lista simplificada de eventos del día. Se usa en `Cargar_evento()` para extraer fecha, hora y tipo.

Formato conceptual:

```python
(
    numero,
    nombre_archivo,
    tipo_evento,
    estacion_0,
    estacion_1,
    ...
)
```

## 6.4 `self.trCanal`

Contenedor principal de señales cargadas del evento actual.

### Contrato

- El índice de `trCanal` corresponde al índice de estación en `parametros_estaciones()`.
- Cada posición contiene un `Stream` de ObsPy o una lista vacía.
- Se carga desde `Cargar_evento()`.
- Se modifica in-place al aplicar `filtrar_evento()`.

### Punto crítico

El script inicializa:

```python
self.trCanal = [[] for _ in range(100)]
```

pero el sistema maneja 101 estaciones. Esto está documentado como deuda técnica crítica.

## 6.5 `self.root`

Raíz XML del día.

### Contrato

- Se carga en `cargar_dia()`.
- Se usa en `Guardar_()` para generar el árbol XML y el reporte.
- Debe ser válido antes de guardar.

## 6.6 `self.responsables`

Responsables del día/franjas horarias.

Se usa para poblar:

- `lbl_responsable_1`
- `lbl_responsable_2`
- `lbl_responsable_3`

y para generar el reporte diario.

## 6.7 `self.resumen`

Resumen estadístico diario usado por `Guardar_()` y `reporte_resumen_modos()`.

---

# 7. Inventario de atributos de `Reporte_diario`

| Atributo | Tipo esperado | Se crea/modifica en | Consumido por | Riesgo |
|---|---|---|---|---|
| `archivo` | str | `__init__`, `showDate`, `reiniciar_estado_dia` | `obtener_directorios`, `leer_mseed` | Alto si queda vacío |
| `directorio_trabajo` | str | `__init__` | cargas/reportes | Alto |
| `responsable` | str | `__init__` | contexto externo | Bajo |
| `periodo` | str | `__init__` | contexto externo | Bajo |
| `eventos_reporte` | list | `__init__`, `reiniciar_estado_dia`, `cargar_dia`, `Insertar_evento`, `Modificar_` | `Guardar_`, UI | Muy alto |
| `catalogo` | list | `cargar_dia`, `Insertar_evento` | reportes/eventos | Muy alto |
| `eventos` | list | `__init__`, `reiniciar_estado_dia`, `cargar_dia` | `Cargar_evento` | Alto |
| `evento_canales` | list | `__init__`, `reiniciar_estado_dia`, `cargar_dia` | `Cargar_evento` | Alto |
| `vector` | list | `reiniciar_estado_dia`, `cargar_dia` | no claro en este script | Medio |
| `root` | XML root | `reiniciar_estado_dia`, `cargar_dia` | `Guardar_` | Muy alto |
| `resumen` | list | `reiniciar_estado_dia`, `cargar_dia` | `Guardar_` | Alto |
| `responsables` | list | `reiniciar_estado_dia`, `cargar_dia` | `Guardar_`, labels | Alto |
| `directorios` | dict | `showDate` | `cargar_dia`, `Guardar_`, `Cargar_evento` | Muy alto |
| `trCanal` | list | `reiniciar_estado_dia`, `Cargar_evento` | gráfica/filtro/reportes | Muy alto |
| `estaciones_eventos` | list[int] | `__init__`, `reiniciar_estado_dia`, `Cargar_evento` | gráfica/filtro/página | Muy alto |
| `pagina` | int | `__init__`, `reiniciar_estado_dia`, `cambio_pagina` | gráfica/paginación | Medio |
| `indice` | int | `reiniciar_estado_dia`, `cargar_dia`, `Cargar_evento` | modificar/insertar/acelerograma | Alto |
| `indice_local` | int | `Cargar_evento` | evento actual | Alto |
| `indice_catalogo` | int | `Cargar_evento` | inserción externas | Alto |
| `evento_escogido` | list | `Cargar_evento` | reportes/inserción | Alto |
| `archivo_escogido` | str | `reiniciar_estado_dia`, `Cargar_evento` | acelerograma | Medio |
| `archivo_reporte` | str | `reiniciar_estado_dia`, `Cargar_evento` | reporte individual | Medio |
| `bandera_evento` | int | `showDate`, `Cargar_evento` | `reiniciar_evento` | Medio/Confuso |
| `enlace` | list | `estacion_calidad`, `estaciones_` | CSV calidad | Alto |
| `comportamiento` | list | `estacion_calidad`, `estaciones_` | CSV calidad | Alto |
| `detalle` | list | `estacion_calidad`, `estaciones_` | CSV calidad | Alto |
| `archivo_comportamiento` | str | No se observa definición | `estacion_calidad` | Crítico |

---

# 8. Máquina de estados operativa

```text
CREADO
  ↓ __init__()
DÍA_INICIALIZADO
  ↓ showDate()
DÍA_CARGADO
  ↓ cargar_dia()
EVENTOS_DISPONIBLES
  ↓ Cargar_evento()
EVENTO_CARGADO
  ├── Graficar_()
  ├── cambio_pagina()
  ├── filtrar_evento()
  ├── Modificar_()
  ├── Insertar_evento()
  ├── Generar_reporte_sismo()
  └── Acelerograma_()
  ↓ Guardar_()
DÍA_GUARDADO
  ↓ Salir_()/closeEvent()
CERRADO
```

## Estado crítico no formalizado

El código usa `self.bandera_evento` para diferenciar estado de día/evento, pero su semántica no es suficientemente clara:

- `bandera_evento = 1` en `showDate()`;
- `bandera_evento = 0` en `Cargar_evento()`.

Para mantenimiento futuro conviene reemplazarla por un `Enum`.

---

# 9. Invariantes

## I-01. Después de `cargar_dia()`

Debe cumplirse:

```python
self.catalogo is not None
self.eventos is not None
self.eventos_reporte is not None
self.root is not None
self.responsables is not None
self.resumen is not None
self.directorios is not None
```

## I-02. Antes de `Cargar_evento()`

Debe cumplirse:

```python
self.catalogo is not None
self.eventos is not None
len(self.eventos_reporte) > 1
self.directorios['Directorio_reportes'] existe o es construible
```

## I-03. Antes de `Graficar_()`

Debe cumplirse:

```python
len(self.estaciones_eventos) > 0
self.trCanal[self.estaciones_eventos[0]] != []
```

## I-04. Antes de `filtrar_evento()`

Debe cumplirse:

```python
len(self.estaciones_eventos) > 0
self.trCanal contiene al menos un Stream no vacío
```

## I-05. Antes de `Guardar_()`

Debe cumplirse:

```python
self.catalogo is not None
self.eventos is not None
self.eventos_reporte is not None
self.root is not None
self.responsables is not None
self.resumen is not None
self.directorios is not None
```

## I-06. Calidad de estaciones

Antes de guardar calidad:

```python
hasattr(self, 'archivo_comportamiento')
len(self.enlace) == len(self.parametros['CODIGO'])
len(self.comportamiento) == len(self.parametros['CODIGO'])
len(self.detalle) == len(self.parametros['CODIGO'])
```

---

# 10. Análisis método por método

## 10.1. `reiniciar_estado_dia()`

### Responsabilidad

Reinicia el estado interno relacionado con un día cargado.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.archivo` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.archivo_escogido` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.archivo_reporte` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.catalogo` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.estaciones_eventos` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.evento_canales` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.eventos` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.eventos_reporte` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.indice` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.pagina` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.responsables` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.resumen` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.root` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.trCanal` | Referenciado/modificado en `reiniciar_estado_dia()` |
| `self.vector` | Referenciado/modificado en `reiniciar_estado_dia()` |

### Riesgo de mantenimiento

Puede dejar `catalogo` sin reinicializar porque la línea está comentada; por tanto `cargar_dia()` debe ejecutarse antes de acceder a catálogo.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.2. `iniciar_variables()`

### Responsabilidad

Limpia variables y deshabilita controles de evento.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.Btn_acelerograma` | Referenciado/modificado en `iniciar_variables()` |
| `self.Btn_graficar` | Referenciado/modificado en `iniciar_variables()` |
| `self.Btn_modificar` | Referenciado/modificado en `iniciar_variables()` |
| `self.Btn_pagina` | Referenciado/modificado en `iniciar_variables()` |
| `self.catalogo` | Referenciado/modificado en `iniciar_variables()` |
| `self.cmbx_evento` | Referenciado/modificado en `iniciar_variables()` |
| `self.cmbx_evento_escogido` | Referenciado/modificado en `iniciar_variables()` |
| `self.evento_canales` | Referenciado/modificado en `iniciar_variables()` |
| `self.eventos` | Referenciado/modificado en `iniciar_variables()` |
| `self.eventos_reporte` | Referenciado/modificado en `iniciar_variables()` |
| `self.indice` | Referenciado/modificado en `iniciar_variables()` |
| `self.vector` | Referenciado/modificado en `iniciar_variables()` |

### Riesgo de mantenimiento

Es parcialmente redundante con `reiniciar_estado_dia()` y no parece invocarse desde el flujo actual principal.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.3. `showDate()`

### Responsabilidad

Construye la ruta base del día, obtiene directorios y carga datos si existe CSV diario.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.archivo` | Referenciado/modificado en `showDate()` |
| `self.bandera_evento` | Referenciado/modificado en `showDate()` |
| `self.cargar_dia` | Referenciado/modificado en `showDate()` |
| `self.date` | Referenciado/modificado en `showDate()` |
| `self.dia_reporte` | Referenciado/modificado en `showDate()` |
| `self.directorio_trabajo` | Referenciado/modificado en `showDate()` |
| `self.directorios` | Referenciado/modificado en `showDate()` |
| `self.fecha_ini` | Referenciado/modificado en `showDate()` |
| `self.reiniciar_estado_dia` | Referenciado/modificado en `showDate()` |
| `self.tr` | Referenciado/modificado en `showDate()` |

### Riesgo de mantenimiento

Depende de concatenación directa `directorio_trabajo + fecha`; asume que el directorio termina con separador.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.4. `cargar_dia()`

### Responsabilidad

Carga CSV/XML/resumen/responsables del día mediante función externa `cargar_dia()`.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.Btn_acelerograma` | Referenciado/modificado en `cargar_dia()` |
| `self.Btn_graficar` | Referenciado/modificado en `cargar_dia()` |
| `self.Btn_guardar` | Referenciado/modificado en `cargar_dia()` |
| `self.Btn_limpiar` | Referenciado/modificado en `cargar_dia()` |
| `self.Btn_modificar` | Referenciado/modificado en `cargar_dia()` |
| `self.Btn_pagina` | Referenciado/modificado en `cargar_dia()` |
| `self.catalogo` | Referenciado/modificado en `cargar_dia()` |
| `self.cmbx_evento` | Referenciado/modificado en `cargar_dia()` |
| `self.cmbx_evento_escogido` | Referenciado/modificado en `cargar_dia()` |
| `self.directorios` | Referenciado/modificado en `cargar_dia()` |
| `self.evento_canales` | Referenciado/modificado en `cargar_dia()` |
| `self.eventos` | Referenciado/modificado en `cargar_dia()` |
| `self.eventos_reporte` | Referenciado/modificado en `cargar_dia()` |
| `self.indice` | Referenciado/modificado en `cargar_dia()` |
| `self.lbl_responsable_1` | Referenciado/modificado en `cargar_dia()` |
| `self.lbl_responsable_2` | Referenciado/modificado en `cargar_dia()` |
| `self.lbl_responsable_3` | Referenciado/modificado en `cargar_dia()` |
| `self.responsables` | Referenciado/modificado en `cargar_dia()` |
| `self.resumen` | Referenciado/modificado en `cargar_dia()` |
| `self.root` | Referenciado/modificado en `cargar_dia()` |
| `self.tr` | Referenciado/modificado en `cargar_dia()` |
| `self.vector` | Referenciado/modificado en `cargar_dia()` |

### Riesgo de mantenimiento

Es el punto que inicializa `catalogo`, `root`, `responsables` y `resumen`; debe ejecutarse antes de guardar o seleccionar eventos.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.5. `Guardar_()`

### Responsabilidad

Guarda los archivos diarios y genera el PDF diario con `reporte_resumen_modos()`.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.catalogo` | Referenciado/modificado en `Guardar_()` |
| `self.dia_reporte` | Referenciado/modificado en `Guardar_()` |
| `self.directorio_trabajo` | Referenciado/modificado en `Guardar_()` |
| `self.directorios` | Referenciado/modificado en `Guardar_()` |
| `self.estaciones_eventos` | Referenciado/modificado en `Guardar_()` |
| `self.eventos` | Referenciado/modificado en `Guardar_()` |
| `self.eventos_reporte` | Referenciado/modificado en `Guardar_()` |
| `self.fecha_ini` | Referenciado/modificado en `Guardar_()` |
| `self.responsables` | Referenciado/modificado en `Guardar_()` |
| `self.resumen` | Referenciado/modificado en `Guardar_()` |
| `self.root` | Referenciado/modificado en `Guardar_()` |
| `self.tr` | Referenciado/modificado en `Guardar_()` |

### Riesgo de mantenimiento

Depende de `catalogo`, `eventos`, `root`, `responsables`, `resumen`, `directorios`; si alguno no existe o está inconsistente falla o genera reporte incorrecto.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.6. `estacion_calidad()`

### Responsabilidad

Calcula calidad de estaciones leyendo MSEED completo del día y abre diálogo `estaciones_`.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.archivo` | Referenciado/modificado en `estacion_calidad()` |
| `self.archivo_comportamiento` | Referenciado/modificado en `estacion_calidad()` |
| `self.comportamiento` | Referenciado/modificado en `estacion_calidad()` |
| `self.detalle` | Referenciado/modificado en `estacion_calidad()` |
| `self.directorios` | Referenciado/modificado en `estacion_calidad()` |
| `self.enlace` | Referenciado/modificado en `estacion_calidad()` |
| `self.parametros` | Referenciado/modificado en `estacion_calidad()` |

### Riesgo de mantenimiento

Usa `self.archivo_comportamiento` sin definición visible en el script; riesgo de crash.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.7. `reiniciar_evento()`

### Responsabilidad

Restablece controles del evento actual o carga evento si `bandera_evento == 1`.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.Btn_generar` | Referenciado/modificado en `reiniciar_evento()` |
| `self.Btn_graficar` | Referenciado/modificado en `reiniciar_evento()` |
| `self.Btn_insertar` | Referenciado/modificado en `reiniciar_evento()` |
| `self.Btn_pagina` | Referenciado/modificado en `reiniciar_evento()` |
| `self.Cargar_evento` | Referenciado/modificado en `reiniciar_evento()` |
| `self.bandera_evento` | Referenciado/modificado en `reiniciar_evento()` |
| `self.cmbx_red` | Referenciado/modificado en `reiniciar_evento()` |
| `self.cmbx_tipo_mag` | Referenciado/modificado en `reiniciar_evento()` |
| `self.evento_escogido` | Referenciado/modificado en `reiniciar_evento()` |
| `self.textEdit` | Referenciado/modificado en `reiniciar_evento()` |
| `self.textEdit_2` | Referenciado/modificado en `reiniciar_evento()` |

### Riesgo de mantenimiento

La semántica de `bandera_evento` es poco clara.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.8. `Cargar_evento()`

### Responsabilidad

Carga el evento seleccionado, sus streams, índices, canales y estaciones activas mediante función externa `cargar_evento()`.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.Btn_generar` | Referenciado/modificado en `Cargar_evento()` |
| `self.Btn_graficar` | Referenciado/modificado en `Cargar_evento()` |
| `self.Btn_insertar` | Referenciado/modificado en `Cargar_evento()` |
| `self.Btn_pagina` | Referenciado/modificado en `Cargar_evento()` |
| `self.archivo_escogido` | Referenciado/modificado en `Cargar_evento()` |
| `self.archivo_reporte` | Referenciado/modificado en `Cargar_evento()` |
| `self.bandera_evento` | Referenciado/modificado en `Cargar_evento()` |
| `self.canales` | Referenciado/modificado en `Cargar_evento()` |
| `self.catalogo` | Referenciado/modificado en `Cargar_evento()` |
| `self.cmbx_evento` | Referenciado/modificado en `Cargar_evento()` |
| `self.cmbx_evento_escogido` | Referenciado/modificado en `Cargar_evento()` |
| `self.cmbx_red` | Referenciado/modificado en `Cargar_evento()` |
| `self.cmbx_tipo_mag` | Referenciado/modificado en `Cargar_evento()` |
| `self.directorio_trabajo` | Referenciado/modificado en `Cargar_evento()` |
| `self.directorios` | Referenciado/modificado en `Cargar_evento()` |
| `self.estaciones_eventos` | Referenciado/modificado en `Cargar_evento()` |
| `self.evento_canales` | Referenciado/modificado en `Cargar_evento()` |
| `self.evento_escogido` | Referenciado/modificado en `Cargar_evento()` |
| `self.eventos` | Referenciado/modificado en `Cargar_evento()` |
| `self.eventos_reporte` | Referenciado/modificado en `Cargar_evento()` |
| `self.indice` | Referenciado/modificado en `Cargar_evento()` |
| `self.indice_catalogo` | Referenciado/modificado en `Cargar_evento()` |
| `self.indice_local` | Referenciado/modificado en `Cargar_evento()` |
| `self.label_1` | Referenciado/modificado en `Cargar_evento()` |
| `self.label_2` | Referenciado/modificado en `Cargar_evento()` |
| `self.label_3` | Referenciado/modificado en `Cargar_evento()` |
| `self.label_4` | Referenciado/modificado en `Cargar_evento()` |
| `self.label_5` | Referenciado/modificado en `Cargar_evento()` |
| `self.label_6` | Referenciado/modificado en `Cargar_evento()` |
| `self.parametros` | Referenciado/modificado en `Cargar_evento()` |
| `self.textEdit` | Referenciado/modificado en `Cargar_evento()` |
| `self.textEdit_2` | Referenciado/modificado en `Cargar_evento()` |
| `self.trCanal` | Referenciado/modificado en `Cargar_evento()` |

### Riesgo de mantenimiento

Punto crítico: inicializa `trCanal`, `estaciones_eventos`, `indice`, `indice_local`, `indice_catalogo`, `evento_escogido`.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.9. `Insertar_evento()`

### Responsabilidad

Inserta datos de otras redes en catálogo y eventos_reporte.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.Btn_generar` | Referenciado/modificado en `Insertar_evento()` |
| `self.Btn_insertar` | Referenciado/modificado en `Insertar_evento()` |
| `self.catalogo` | Referenciado/modificado en `Insertar_evento()` |
| `self.cmbx_red` | Referenciado/modificado en `Insertar_evento()` |
| `self.cmbx_tipo_mag` | Referenciado/modificado en `Insertar_evento()` |
| `self.evento_escogido` | Referenciado/modificado en `Insertar_evento()` |
| `self.eventos_reporte` | Referenciado/modificado en `Insertar_evento()` |
| `self.indice` | Referenciado/modificado en `Insertar_evento()` |
| `self.indice_catalogo` | Referenciado/modificado en `Insertar_evento()` |
| `self.indice_local` | Referenciado/modificado en `Insertar_evento()` |
| `self.textEdit` | Referenciado/modificado en `Insertar_evento()` |
| `self.textEdit_2` | Referenciado/modificado en `Insertar_evento()` |

### Riesgo de mantenimiento

Modifica estructuras persistibles; requiere guardar posteriormente.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.10. `Generar_reporte_sismo()`

### Responsabilidad

Genera reporte PDF individual de un sismo.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.archivo_reporte` | Referenciado/modificado en `Generar_reporte_sismo()` |
| `self.canales` | Referenciado/modificado en `Generar_reporte_sismo()` |
| `self.catalogo` | Referenciado/modificado en `Generar_reporte_sismo()` |
| `self.directorio_trabajo` | Referenciado/modificado en `Generar_reporte_sismo()` |
| `self.evento_escogido` | Referenciado/modificado en `Generar_reporte_sismo()` |
| `self.trCanal` | Referenciado/modificado en `Generar_reporte_sismo()` |

### Riesgo de mantenimiento

Depende de evento cargado, `trCanal`, `canales` y `archivo_reporte`.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.11. `Graficar_()`

### Responsabilidad

Grafica señales del evento actual.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.estaciones_eventos` | Referenciado/modificado en `Graficar_()` |
| `self.parametros` | Referenciado/modificado en `Graficar_()` |
| `self.trCanal` | Referenciado/modificado en `Graficar_()` |
| `self.visor` | Referenciado/modificado en `Graficar_()` |

### Riesgo de mantenimiento

Accede a `estaciones_eventos[0]` sin validar; pasa página 0, ignorando `self.pagina`.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.12. `cambio_pagina()`

### Responsabilidad

Avanza página de visualización de estaciones y grafica.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.estaciones_eventos` | Referenciado/modificado en `cambio_pagina()` |
| `self.pagina` | Referenciado/modificado en `cambio_pagina()` |
| `self.parametros` | Referenciado/modificado en `cambio_pagina()` |
| `self.trCanal` | Referenciado/modificado en `cambio_pagina()` |
| `self.visor` | Referenciado/modificado en `cambio_pagina()` |

### Riesgo de mantenimiento

Valida límite de página de forma simple; también accede a `estaciones_eventos[0]` sin validar.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.13. `Modificar_()`

### Responsabilidad

Cambia el tipo de evento en `eventos_reporte` y limpia magnitud.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.cmbx_evento` | Referenciado/modificado en `Modificar_()` |
| `self.eventos_reporte` | Referenciado/modificado en `Modificar_()` |
| `self.indice` | Referenciado/modificado en `Modificar_()` |

### Riesgo de mantenimiento

No sincroniza explícitamente `catalogo` ni `eventos`; revisar impacto en persistencia.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.14. `Acelerograma_()`

### Responsabilidad

Genera reporte de acelerograma del evento actual.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.archivo_escogido` | Referenciado/modificado en `Acelerograma_()` |
| `self.catalogo` | Referenciado/modificado en `Acelerograma_()` |
| `self.evento_escogido` | Referenciado/modificado en `Acelerograma_()` |
| `self.eventos_reporte` | Referenciado/modificado en `Acelerograma_()` |
| `self.indice` | Referenciado/modificado en `Acelerograma_()` |

### Riesgo de mantenimiento

Depende de evento cargado.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.15. `filtrar_evento()`

### Responsabilidad

Aplica filtro pasa banda sobre `trCanal` y redibuja.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.estaciones_eventos` | Referenciado/modificado en `filtrar_evento()` |
| `self.pagina` | Referenciado/modificado en `filtrar_evento()` |
| `self.parametros` | Referenciado/modificado en `filtrar_evento()` |
| `self.sp_Box_finf` | Referenciado/modificado en `filtrar_evento()` |
| `self.sp_Box_fsup` | Referenciado/modificado en `filtrar_evento()` |
| `self.sp_Box_orden` | Referenciado/modificado en `filtrar_evento()` |
| `self.trCanal` | Referenciado/modificado en `filtrar_evento()` |
| `self.visor` | Referenciado/modificado en `filtrar_evento()` |

### Riesgo de mantenimiento

Filtra in-place; no conserva copia original. Itera rango(100), no 101.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.16. `Salir_()`

### Responsabilidad

Cierra la ventana desde botón.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.close` | Referenciado/modificado en `Salir_()` |

### Riesgo de mantenimiento

Dispara `closeEvent()`.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.17. `limpiar_estado()`

### Responsabilidad

Libera canvas/visor y referencias heredadas si existen.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.canvas` | Referenciado/modificado en `limpiar_estado()` |
| `self.lista_eventos` | Referenciado/modificado en `limpiar_estado()` |
| `self.stLeido` | Referenciado/modificado en `limpiar_estado()` |
| `self.visor` | Referenciado/modificado en `limpiar_estado()` |

### Riesgo de mantenimiento

Referencia atributos no usados en este script (`stLeido`, `lista_eventos`), probablemente heredado de otros módulos.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

## 10.18. `closeEvent()`

### Responsabilidad

Limpia estado, emite señal `cerrado` y acepta cierre.

### Estado que modifica o consume

| Atributo | Uso probable |
|---|---|
| `self.cerrado` | Referenciado/modificado en `closeEvent()` |
| `self.limpiar_estado` | Referenciado/modificado en `closeEvent()` |

### Riesgo de mantenimiento

Correcto en principio; no guarda automáticamente cambios.

### Recomendación

Antes de modificar este método, revisar los contratos e invariantes relacionados y ejecutar el checklist de regresión correspondiente.

---

# 11. Matriz método → estado modificado

| Método | Estado principal que modifica | Impacto |
|---|---|---|
| `showDate()` | `archivo`, `date`, `fecha_ini`, `directorios`, `dia_reporte` | Muy alto |
| `cargar_dia()` | `eventos_reporte`, `catalogo`, `eventos`, `vector`, `evento_canales`, `root`, `responsables`, `resumen` | Muy alto |
| `Cargar_evento()` | `indice`, `indice_local`, `indice_catalogo`, `archivo_escogido`, `evento_escogido`, `canales`, `trCanal`, `archivo_reporte`, `HAB_GRAFICO`, `estaciones_eventos` | Muy alto |
| `Graficar_()` | Gráfica Matplotlib | Medio |
| `cambio_pagina()` | `pagina` y gráfica | Medio |
| `filtrar_evento()` | `trCanal` in-place y gráfica | Alto |
| `Modificar_()` | `eventos_reporte` | Alto |
| `Insertar_evento()` | `catalogo`, `eventos_reporte` | Muy alto |
| `Guardar_()` | Archivos diarios, PDF | Muy alto |
| `estacion_calidad()` | `enlace`, `comportamiento`, `detalle`, CSV calidad | Alto |
| `limpiar_estado()` | `canvas`, `visor`, referencias auxiliares | Medio |
| `closeEvent()` | Señal `cerrado`, cierre | Medio |

---

# 12. Riesgos operativos detallados

## R-01. `trCanal` con 100 posiciones

El sistema parece trabajar con 101 estaciones, pero `reiniciar_estado_dia()` inicializa:

```python
self.trCanal = [[] for _ in range(100)]
```

### Impacto

Puede producir errores al acceder a la estación 100 si el índice existe.

### Recomendación

Usar una constante:

```python
NUM_ESTACIONES = len(self.parametros['CODIGO'])
self.trCanal = [[] for _ in range(NUM_ESTACIONES)]
```

## R-02. `Graficar_()` no valida estaciones

`Graficar_()` accede directamente a:

```python
self.estaciones_eventos[0]
```

### Impacto

Si no hay estaciones activas, ocurre `IndexError`.

### Recomendación

```python
if not self.estaciones_eventos:
    QMessageBox.warning(self, "Advertencia", "No hay estaciones para graficar.")
    return
```

## R-03. `Graficar_()` ignora `self.pagina`

Actualmente llama:

```python
grafico_evento_int(..., 0, 0)
```

El último parámetro debería ser `self.pagina`.

## R-04. `archivo_comportamiento` sin definición

`estacion_calidad()` usa:

```python
with open(self.archivo_comportamiento, ...)
```

pero el atributo no se define en el script.

### Impacto

Crash al intentar guardar evaluación de calidad.

## R-05. División por cero en `estaciones_.calcular()`

```python
comp = round(100 * evaluacion / enlace, 1)
```

Si `enlace == 0`, ocurre error.

## R-06. Filtrado destructivo

`filtrar_evento()` modifica `trCanal` in-place.

### Impacto

No hay forma directa de volver a la señal original sin recargar el evento.

## R-07. `catalogo` no se reinicia explícitamente

En `reiniciar_estado_dia()` la reinicialización de `catalogo` está comentada. Por tanto el código depende de que `cargar_dia()` se ejecute antes de cualquier método que use `catalogo`.

## R-08. Acoplamiento fuerte con módulos externos

Las funciones externas `cargar_dia()`, `cargar_evento()`, `Guardar_dia()` y `reporte_resumen_modos()` definen gran parte del comportamiento real. Cualquier cambio en su firma rompe este módulo.

---

# 13. Acoplamientos

## A-01. `estaciones_` modifica directamente el padre

La clase `estaciones_` escribe en:

```python
self.parent.enlace
self.parent.comportamiento
self.parent.detalle
```

### Impacto

La ventana hija conoce demasiado del estado interno de `Reporte_diario`.

### Recomendación futura

Convertir `estaciones_` en diálogo que devuelva una estructura de resultados, por ejemplo:

```python
resultado = dialog.obtener_resultados()
```

## A-02. GUI y lógica mezcladas

Métodos como `Cargar_evento()`, `Guardar_()` y `estacion_calidad()` mezclan:

- lectura de datos;
- actualización de estado;
- actualización de widgets;
- persistencia;
- mensajes al usuario.

Esto complica pruebas automáticas.

## A-03. Dependencia de nombres de widgets del `.ui`

El script depende de widgets como:

- `Btn_Salir`
- `Btn_guardar`
- `Btn_modificar`
- `Btn_acelerograma`
- `Btn_generar`
- `Btn_insertar`
- `Btn_graficar`
- `Btn_estacion`
- `Btn_limpiar`
- `Btn_pagina`
- `Btn_filtrar`
- `cmbx_evento_escogido`
- `cmbx_evento`
- `cmbx_red`
- `cmbx_tipo_mag`
- `sp_Box_finf`
- `sp_Box_fsup`
- `sp_Box_orden`
- `calendarWidget`
- labels de fecha/responsables.

Cambiar nombres en Qt Designer sin actualizar Python rompe el módulo.

---

# 14. Deuda técnica priorizada

| ID | Deuda técnica | Prioridad | Riesgo |
|---|---|---:|---|
| DT-01 | `trCanal` usa 100 posiciones en vez de número real de estaciones | Alta | IndexError |
| DT-02 | `Graficar_()` ignora `self.pagina` | Alta | Paginación inconsistente |
| DT-03 | `archivo_comportamiento` no definido | Alta | Crash |
| DT-04 | `estaciones_.calcular()` puede dividir por cero | Alta | Crash |
| DT-05 | `filtrar_evento()` modifica señales in-place | Media | Pérdida de referencia original |
| DT-06 | `bandera_evento` tiene semántica poco clara | Media | Mantenimiento difícil |
| DT-07 | `estaciones_` usa geometría fija | Media | Mala escalabilidad UI |
| DT-08 | `filtro_evento()` local duplica o solapa lógica externa | Media | Duplicación |
| DT-09 | `catalogo` no se reinicia explícitamente | Media | Estado residual |
| DT-10 | `limpiar_estado()` contiene referencias heredadas (`stLeido`, `lista_eventos`) | Baja | Confusión |

---

# 15. Checklist de regresión para agente

## 15.1 Carga del día

- [ ] Abrir el módulo con un archivo válido.
- [ ] Verificar que `showDate()` construye correctamente `self.archivo`.
- [ ] Verificar que `self.directorios` contiene claves esperadas.
- [ ] Verificar que `cargar_dia()` llena `catalogo`, `eventos`, `eventos_reporte`, `root`, `responsables`, `resumen`.
- [ ] Verificar que el combo de eventos se llena correctamente.

## 15.2 Selección de evento

- [ ] Seleccionar evento SISMO.
- [ ] Confirmar que `Cargar_evento()` llena `trCanal`.
- [ ] Confirmar que `estaciones_eventos` no queda vacío.
- [ ] Confirmar que labels de fecha/hora se actualizan.
- [ ] Confirmar que botones de gráfica/reporte se habilitan.

## 15.3 Gráfica y paginación

- [ ] Ejecutar `Graficar_()`.
- [ ] Ejecutar `cambio_pagina()`.
- [ ] Verificar que la página cambia.
- [ ] Confirmar que no falla con eventos de pocas estaciones.
- [ ] Confirmar que no falla si `estaciones_eventos` está vacío.

## 15.4 Filtro

- [ ] Aplicar filtro con valores válidos.
- [ ] Confirmar que redibuja.
- [ ] Recargar evento para restaurar señal original.
- [ ] Confirmar que no falla si no hay streams.

## 15.5 Modificación de evento

- [ ] Cambiar tipo de evento.
- [ ] Confirmar que se modifica `eventos_reporte[indice][2]`.
- [ ] Confirmar que `eventos_reporte[indice][3]` se limpia.
- [ ] Guardar día.
- [ ] Recargar día y verificar persistencia.

## 15.6 Inserción de otras redes

- [ ] Insertar IGEPN.
- [ ] Insertar USGS.
- [ ] Confirmar que `catalogo` y `eventos_reporte` cambian.
- [ ] Generar reporte individual.
- [ ] Guardar día y recargar.

## 15.7 Reportes

- [ ] Generar reporte individual.
- [ ] Generar acelerograma.
- [ ] Ejecutar `Guardar_()`.
- [ ] Confirmar que se generan CSV/XML/PDF esperados.
- [ ] Confirmar que `reporte_resumen_modos()` recibe modo `MODO_DIARIO_REVISION`.

## 15.8 Calidad de estaciones

- [ ] Ejecutar `estacion_calidad()`.
- [ ] Confirmar que `leer_mseed()` retorna datos.
- [ ] Confirmar que `calidad_estacion()` retorna evaluación y tr_Canal.
- [ ] Probar `estaciones_.calcular()`.
- [ ] Probar enlace 0 para verificar manejo de división por cero.
- [ ] Confirmar que el archivo de comportamiento existe y se escribe.

## 15.9 Cierre

- [ ] Cerrar desde botón.
- [ ] Verificar que se llama `limpiar_estado()`.
- [ ] Confirmar que `cerrado.emit()` se emite una sola vez.
- [ ] Confirmar que no quedan errores de matplotlib/canvas.

---

# 16. Reglas de modificación segura

1. No modificar el formato de `eventos_reporte` sin actualizar `Guardar_dia()`, `insertar_evento_otras_redes()` y reportes.
2. No modificar el formato de `catalogo` sin actualizar reportes individuales, acelerogramas y PDF diario.
3. No llamar `Graficar_()` si no hay evento cargado.
4. No aplicar filtros sin saber que se modifican los streams in-place.
5. No modificar `estaciones_` sin revisar el contrato de `parent`.
6. No cambiar nombres de widgets del `.ui` sin actualizar este script.
7. No asumir que `catalogo` existe después de `reiniciar_estado_dia()`.
8. No guardar si `root` es `None`.
9. No editar `parametros['HAB_GRAFICO']` sin entender su uso compartido con gráficos.

---

# 17. Estrategia de refactorización recomendada

## Fase 0: Correcciones seguras

- Cambiar `trCanal` a tamaño dinámico.
- Validar `estaciones_eventos` antes de graficar.
- Usar `self.pagina` en `Graficar_()`.
- Definir correctamente `archivo_comportamiento`.
- Evitar división por cero en `estaciones_.calcular()`.

## Fase 1: Estado explícito

Reemplazar `bandera_evento` por:

```python
from enum import Enum, auto

class EstadoReporteDiario(Enum):
    DIA_SIN_CARGAR = auto()
    DIA_CARGADO = auto()
    EVENTO_CARGADO = auto()
```

## Fase 2: Separar servicios

Extraer lógica a servicios:

```text
ServicioCargaDia
ServicioEvento
ServicioReportesDiarios
ServicioCalidadEstaciones
ServicioGraficacion
```

## Fase 3: Desacoplar diálogo de estaciones

Hacer que `estaciones_` devuelva resultados en vez de modificar el padre directamente.

## Fase 4: Pruebas automatizadas

Crear pruebas sobre:

- carga de día;
- carga de evento;
- modificación de evento;
- inserción de redes externas;
- guardado;
- calidad de estaciones.

---

# 18. Recomendación para uso con agente

Para pedir cambios a un agente, conviene especificar siempre:

1. Método o flujo a modificar.
2. Contratos que no deben romperse.
3. Archivos de salida que deben permanecer compatibles.
4. Checklist mínimo a ejecutar.
5. Si se permite o no refactorizar.

Ejemplo:

```text
Modifica Graficar_() para usar self.pagina y validar estaciones_eventos.
No cambies la firma pública.
No modifiques cargar_evento().
Mantén el uso de grafico_evento_int().
Actualiza el contexto si cambia el flujo.
```

---

# 19. Fragmento de código fuente de referencia

El archivo fuente completo debe permanecer junto a esta documentación. Esta sección resume que el análisis se hizo sobre `reporte_diario.py` actual, sin modificar el script.

Para cambios futuros, actualizar este contexto cuando cambien:

- firmas de métodos;
- estructuras de datos;
- rutas de archivos;
- widgets del UI;
- contratos con funciones externas;
- formatos CSV/XML/PDF.

---

# 20. Conclusión

Esta versión está orientada a mantenimiento de largo plazo y trabajo con agentes.

Los puntos más importantes que debe recordar cualquier mantenedor son:

1. `cargar_dia()` inicializa el estado diario esencial.
2. `Cargar_evento()` inicializa el estado del evento y las señales.
3. `Guardar_()` depende de que catálogo, eventos, XML, resumen y responsables estén consistentes.
4. `trCanal` se modifica in-place al filtrar.
5. `estaciones_` modifica directamente el estado del padre.
6. La mayor fragilidad actual está en validaciones ausentes, tamaño de `trCanal`, paginación y archivo de comportamiento.

