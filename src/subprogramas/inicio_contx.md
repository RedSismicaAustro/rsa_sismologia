# CONTEXTO INTEGRAL DE MANTENIMIENTO V3 EXHAUSTIVA ORIENTADA A AGENTES

## `fases.py` — Sistema de Detección, Revisión y Marcado de Fases Sísmicas

**Versión del documento:** 3.0 exhaustiva  
**Fecha:** 2026-06-11  
**Fuente primaria:** `fases.py`  
**Objetivo:** servir como contexto operativo para mantenimiento humano y agentes de IA.  

---

# 0. Uso previsto de este documento

Este documento está diseñado para que un agente de mantenimiento pueda modificar `fases.py` sin romper comportamiento funcional.

Debe usarse antes de cualquier cambio en:

- carga de fechas;
- carga de eventos `.sis`;
- búsqueda de MSEED;
- detección automática de fases;
- edición interactiva de fases;
- persistencia JSON;
- integración con `GestorFases`;
- estructura de directorios RSA.

---

# 1. Veredicto técnico sobre el estado actual

El script es funcionalmente pequeño, pero delicado. Su riesgo principal no está en el tamaño, sino en la mezcla de:

- GUI PyQt5;
- lectura de archivos;
- Matplotlib embebido;
- ObsPy;
- detección automática;
- edición manual interactiva;
- persistencia JSON;
- dependencias implícitas de nombres de archivos y estructura de directorios.

El módulo funciona como puente entre el procesamiento sísmico y una capa de revisión/manualización de fases. Por eso, cualquier cambio debe mantener los contratos de datos y la estructura de rutas.

---

# 2. Papel dentro del ecosistema RSA

```text
Evento procesado / día disponible
        ↓
Directorio diario RSA
        ↓
Archivos .sis + .mseed + CSV de matriz de eventos
        ↓
fases.py
        ↓
Detección automática P/S/Coda
        ↓
Edición manual por estación
        ↓
fases_detectadas en memoria
        ↓
archivo JSON de fases
```

El módulo no reemplaza al procesamiento integrado. Su papel es especializarse en revisión de fases por evento y estación.

---

# 3. Responsabilidades

## 3.1 Responsabilidades incluidas

- Seleccionar directorio de trabajo.
- Seleccionar fecha.
- Obtener directorios del día mediante `obtener_directorios()`.
- Leer matriz de eventos mediante `lectura_archivo()`.
- Listar archivos `.sis`.
- Cargar evento seleccionado.
- Encontrar archivos `.mseed` asociados a un evento.
- Graficar estaciones paginadas.
- Determinar si una estación aporta al evento.
- Detectar fases automáticamente mediante `detectar_y_marcar_fases()`.
- Abrir una ventana detallada por estación/MSEED.
- Delegar edición interactiva a `GestorFases`.
- Actualizar fases en memoria al cerrar la ventana detallada.
- Guardar fases en JSON mediante `guardar_evento()`.

## 3.2 Responsabilidades excluidas

Este módulo no debe encargarse de:

- localizar eventos;
- calcular hipocentros;
- generar reportes PDF;
- generar catálogos diarios;
- corregir señales;
- procesar todo el día;
- modificar la matriz de eventos;
- decidir si una fase es definitiva para catálogo oficial sin revisión externa.

---

# 4. Arquitectura lógica

```text
VentanaPrincipal
│
├── init_ui()
│   ├── carga marcar_fases.ui
│   ├── crea figura/canvas principal
│   └── conecta señales
│
├── cambio_de_fecha()
│   ├── obtiene fecha
│   ├── obtiene directorios
│   ├── lee matriz_eventos
│   └── lista archivos .sis
│
├── cargar_evento()
│   ├── selecciona archivo .sis
│   ├── construye patrón MSEED
│   ├── lista archivos MSEED
│   ├── actualiza lista_mseed
│   └── llama graficar_evento()
│
├── graficar_evento()
│   ├── lee MSEED
│   ├── selecciona componente
│   ├── detecta aporte por matriz_eventos
│   ├── detecta fases automáticas
│   └── dibuja estaciones por página
│
├── seleccionar_grafico_mseed()
│   ├── extrae archivo seleccionado
│   ├── crea GestorFases
│   └── abre VentanaGrafico
│
└── guardar_evento()
    └── escribe fases_detectadas en JSON

VentanaGrafico
│
├── graficar_mseed()
│   ├── lee MSEED
│   ├── grafica trace
│   ├── dibuja fases
│   └── conecta eventos Matplotlib a GestorFases
│
└── closeEvent()
    ├── obtiene fases actualizadas
    ├── actualiza parent.fases_detectadas
    └── redibuja VentanaPrincipal
```

---

# 5. Dependencias

## 5.1 Imports detectados

```text
os
obspy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QMessageBox
from PyQt5.QtCore import QDate
from librerias.metodos_rsa import lectura_archivo
from librerias.metodos_sismicos import detectar_y_marcar_fases
from librerias.metodos_gestion import obtener_directorios, cargar_parametros
json
from librerias.gestor_fases import GestorFases
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from PyQt5 import uic
```

## 5.2 Dependencias internas

| Dependencia | Uso | Riesgo |
|---|---|---|
| `librerias.metodos_rsa.lectura_archivo` | Lee CSV de matriz de eventos | Si cambia formato de retorno, se rompe `matriz_eventos` |
| `librerias.metodos_sismicos.detectar_y_marcar_fases` | Detección automática P/S/Coda | Define contrato de `fases_detectadas` |
| `librerias.metodos_gestion.obtener_directorios` | Estructura rutas del día | Crítico para carga |
| `librerias.metodos_gestion.cargar_parametros` | Mapa estación → nombre/componente | Crítico para selección de trace |
| `librerias.gestor_fases.GestorFases` | Edición interactiva | Crítico para edición manual |

## 5.3 Dependencias externas

| Dependencia | Uso |
|---|---|
| `PyQt5` | Ventanas, widgets, señales de UI |
| `Matplotlib` | Gráficas embebidas y eventos de mouse |
| `ObsPy` | Lectura de MSEED |
| `json` | Persistencia de fases |
| `os` | Rutas y listado de archivos |

---

# 6. Componentes y clases

## 6.1. Clase `VentanaPrincipal`

### Métodos

- `__init__()`
- `init_ui()`
- `cerrar_ventana()`
- `graficar_evento()`
- `cambiar_directorio()`
- `cambio_de_fecha()`
- `cargar_evento()`
- `seleccionar_grafico_mseed()`
- `anterior_pagina()`
- `siguiente_pagina()`
- `guardar_evento()`

### Atributos usados/asignados

| Atributo | Comentario |
|---|---|
| `self.anterior_pagina` | Referenciado dentro de `VentanaPrincipal` |
| `self.archivo_fas` | Referenciado dentro de `VentanaPrincipal` |
| `self.archivo_json` | Referenciado dentro de `VentanaPrincipal` |
| `self.archivo_sis` | Referenciado dentro de `VentanaPrincipal` |
| `self.archivos_mseed` | Referenciado dentro de `VentanaPrincipal` |
| `self.axes` | Referenciado dentro de `VentanaPrincipal` |
| `self.boton_anterior` | Referenciado dentro de `VentanaPrincipal` |
| `self.boton_directorio` | Referenciado dentro de `VentanaPrincipal` |
| `self.boton_salir` | Referenciado dentro de `VentanaPrincipal` |
| `self.boton_siguiente` | Referenciado dentro de `VentanaPrincipal` |
| `self.cambiar_directorio` | Referenciado dentro de `VentanaPrincipal` |
| `self.cambio_de_fecha` | Referenciado dentro de `VentanaPrincipal` |
| `self.canvas` | Referenciado dentro de `VentanaPrincipal` |
| `self.cargar_evento` | Referenciado dentro de `VentanaPrincipal` |
| `self.centralWidget` | Referenciado dentro de `VentanaPrincipal` |
| `self.cerrar_ventana` | Referenciado dentro de `VentanaPrincipal` |
| `self.checkbox_filtro` | Referenciado dentro de `VentanaPrincipal` |
| `self.close` | Referenciado dentro de `VentanaPrincipal` |
| `self.combo_sis` | Referenciado dentro de `VentanaPrincipal` |
| `self.date_edit` | Referenciado dentro de `VentanaPrincipal` |
| `self.directorio_trabajo` | Referenciado dentro de `VentanaPrincipal` |
| `self.directorios` | Referenciado dentro de `VentanaPrincipal` |
| `self.estaciones_por_pagina` | Referenciado dentro de `VentanaPrincipal` |
| `self.fases_detectadas` | Referenciado dentro de `VentanaPrincipal` |
| `self.fecha_seleccionada` | Referenciado dentro de `VentanaPrincipal` |
| `self.figura` | Referenciado dentro de `VentanaPrincipal` |
| `self.gestor_fases` | Referenciado dentro de `VentanaPrincipal` |
| `self.graficar_evento` | Referenciado dentro de `VentanaPrincipal` |
| `self.init_ui` | Referenciado dentro de `VentanaPrincipal` |
| `self.lista_mseed` | Referenciado dentro de `VentanaPrincipal` |
| `self.mapa_estaciones` | Referenciado dentro de `VentanaPrincipal` |
| `self.matriz_eventos` | Referenciado dentro de `VentanaPrincipal` |
| `self.pagina_actual` | Referenciado dentro de `VentanaPrincipal` |
| `self.seleccionar_grafico_mseed` | Referenciado dentro de `VentanaPrincipal` |
| `self.setCentralWidget` | Referenciado dentro de `VentanaPrincipal` |
| `self.setWindowTitle` | Referenciado dentro de `VentanaPrincipal` |
| `self.showMaximized` | Referenciado dentro de `VentanaPrincipal` |
| `self.siguiente_pagina` | Referenciado dentro de `VentanaPrincipal` |

## 6.2. Clase `VentanaGrafico`

### Métodos

- `__init__()`
- `init_ui()`
- `graficar_mseed()`
- `closeEvent()`

### Atributos usados/asignados

| Atributo | Comentario |
|---|---|
| `self.archivo_seleccionado` | Referenciado dentro de `VentanaGrafico` |
| `self.canvas` | Referenciado dentro de `VentanaGrafico` |
| `self.directorio_eventos` | Referenciado dentro de `VentanaGrafico` |
| `self.fases_detectadas` | Referenciado dentro de `VentanaGrafico` |
| `self.fases_estacion` | Referenciado dentro de `VentanaGrafico` |
| `self.fecha` | Referenciado dentro de `VentanaGrafico` |
| `self.figura` | Referenciado dentro de `VentanaGrafico` |
| `self.gestor_fases` | Referenciado dentro de `VentanaGrafico` |
| `self.graficar_mseed` | Referenciado dentro de `VentanaGrafico` |
| `self.id_estacion` | Referenciado dentro de `VentanaGrafico` |
| `self.init_ui` | Referenciado dentro de `VentanaGrafico` |
| `self.parent` | Referenciado dentro de `VentanaGrafico` |
| `self.setCentralWidget` | Referenciado dentro de `VentanaGrafico` |
| `self.setGeometry` | Referenciado dentro de `VentanaGrafico` |
| `self.setWindowTitle` | Referenciado dentro de `VentanaGrafico` |
| `self.toolbar` | Referenciado dentro de `VentanaGrafico` |

# 7. Modelo de datos

## 7.1 `fases_detectadas`

Diccionario central del módulo.

```python
{
    "BOB1_20240505_143022.mseed": {
        "P": [1.23, 4.56],
        "S": [2.34],
        "Coda": [10.0]
    }
}
```

### Contrato

- Clave principal: nombre exacto del archivo `.mseed`.
- Valor: diccionario de fases.
- Claves internas esperadas: `"P"`, `"S"`, `"Coda"`.
- Cada fase contiene una lista de tiempos en segundos.
- No almacenar objetos `Trace`, `Stream`, `numpy.ndarray` ni líneas de Matplotlib.
- El valor `0` puede usarse como marcador no dibujable, según el contexto previo.

### Productores

- `graficar_evento()` al llamar `detectar_y_marcar_fases(tr)`.
- `VentanaGrafico.closeEvent()` al obtener fases editadas.

### Consumidores

- `seleccionar_grafico_mseed()`.
- `VentanaGrafico.graficar_mseed()`.
- `guardar_evento()`.

---

## 7.2 `matriz_eventos`

Se carga desde:

```python
self.matriz_eventos = lectura_archivo(self.directorios['archivo_csv'])
```

### Contrato de fila

```text
[ id_evento, nombre_archivo, tipo_evento, estacion_0, estacion_1, ... ]
```

Las columnas desde la posición 3 describen estaciones.

### Contrato de cadena de estación

El script asume posiciones fijas:

```text
info[0:4]   código estación
info[5]     indicador de aporte
info[6:8]   orden filtro
info[8:10]  frecuencia inferior
info[10:12] frecuencia superior
```

### Riesgo

El contexto previo indicaba otra distribución con componente incluida. El script real usa índices `5`, `6:8`, `8:10`, `10:12`. Para evitar errores, el contrato debe ajustarse al script real o corregir el script si el formato correcto es otro.

---

## 7.3 `mapa_estaciones`

Se carga con:

```python
self.mapa_estaciones = cargar_parametros()
```

Formato esperado:

```python
{
    "BOB1": ("Nombre completo", "1"),
    "BOB2": ("Nombre completo", "2")
}
```

### Contrato

- Clave: código corto de estación extraído antes de `_` en el nombre MSEED.
- Valor posición 0: nombre completo.
- Valor posición 1: componente como cadena convertible a entero.
- El componente se transforma en índice con `int(componente) - 1`.

---

## 7.4 `directorios`

Se obtiene mediante:

```python
self.directorios = obtener_directorios(archivo)
```

Claves usadas directamente por el script:

| Clave | Uso |
|---|---|
| `archivo_csv` | lectura de matriz de eventos; construcción actual incorrecta de FAS/JSON |
| `Directorio_dia` | listar `.sis` |
| `Directorio_eventos` | listar y leer `.mseed` |

---

## 7.5 `archivos_mseed`

Lista de archivos MSEED asociados al evento `.sis` seleccionado.

Se construye con:

```python
[f for f in os.listdir(Directorio_eventos) if f.endswith(patron_mseed)]
```

### Contrato

- Contiene nombres de archivo, no rutas absolutas.
- Para leer se combina con `Directorio_eventos`.

---

## 7.6 `archivo_sis`, `archivo_fas`, `archivo_json`

### `archivo_sis`

Archivo de evento seleccionado desde `combo_sis`.

### `archivo_fas`

Actualmente se construye así:

```python
self.archivo_fas = self.directorios['archivo_csv'] + '/' + self.archivo_sis[:-3] + 'fas'
```

### `archivo_json`

Actualmente se construye así:

```python
self.archivo_json = self.archivo_fas[:-3] + 'json'
```

### Problema confirmado

`archivo_csv` normalmente es ruta de archivo, no directorio. Por tanto, esta construcción es frágil y probablemente incorrecta.

### Recomendación

```python
self.archivo_json = os.path.join(
    self.directorios['Directorio_dia'],
    self.archivo_sis.replace('.sis', '.json')
)
```

---

# 8. Máquina de estados

```text
CREADO
  ↓ __init__()
UI_INICIALIZADA
  ↓ init_ui()
FECHA_CARGANDO
  ↓ cambio_de_fecha()
FECHA_CARGADA
  ↓ combo_sis seleccionado
EVENTO_CARGANDO
  ↓ cargar_evento()
EVENTO_CARGADO
  ↓ graficar_evento()
FASES_DETECTADAS_EN_MEMORIA
  ↓ seleccionar_grafico_mseed()
VENTANA_DETALLE_ABIERTA
  ↓ edición GestorFases
FASES_EDITADAS_EN_MEMORIA
  ↓ guardar_evento()
FASES_PERSISTIDAS_JSON
  ↓ cerrar_ventana()
CERRADO
```

## Estados no formalizados

El script no tiene una variable `estado`. El estado se infiere de la existencia de atributos como:

- `directorios`
- `matriz_eventos`
- `archivo_sis`
- `archivos_mseed`
- `fases_detectadas`
- `archivo_json`

Para un agente, esto es crítico: antes de modificar un método, debe verificar qué atributos presupone.

---

# 9. Invariantes

## I-01. Después de `init_ui()`

Debe existir:

```python
self.figura
self.canvas
self.boton_directorio
self.date_edit
self.combo_sis
self.checkbox_filtro
self.boton_salir
self.lista_mseed
self.boton_anterior
self.boton_siguiente
```

## I-02. Después de `cambio_de_fecha()` exitoso

Debe existir:

```python
self.fecha_seleccionada
self.directorios
self.matriz_eventos
```

Además:

```python
isinstance(self.fases_detectadas, dict)
```

## I-03. Antes de `cargar_evento()`

Debe cumplirse:

```python
hasattr(self, 'directorios')
self.combo_sis.currentText() != ""
```

## I-04. Después de `cargar_evento()` exitoso

Debe existir:

```python
self.archivo_sis
self.archivo_json
self.archivos_mseed
```

## I-05. Antes de `graficar_evento()`

Debe cumplirse:

```python
hasattr(self, 'directorios')
hasattr(self, 'matriz_eventos')
hasattr(self, 'archivo_sis')
isinstance(self.archivos_mseed, list)
```

## I-06. Antes de `seleccionar_grafico_mseed()`

Debe cumplirse:

```python
archivo_seleccionado in self.fases_detectadas
```

## I-07. Antes de `guardar_evento()`

Debe cumplirse:

```python
hasattr(self, 'archivo_json')
isinstance(self.fases_detectadas, dict)
len(self.fases_detectadas) > 0
```

## I-08. Antes de `VentanaGrafico.graficar_mseed()`

Debe cumplirse:

```python
self.archivo_seleccionado in self.fases_detectadas
self.gestor_fases is not None
```

---

# 10. Análisis método por método

## 10.1. `VentanaPrincipal.__init__()`

### Rol

Inicializa la ventana principal, fija el directorio de trabajo, inicializa estado de paginación, contenedor de fases y mapa de estaciones.

### Precondiciones

PyQt5 disponible; librerías internas importables; archivo UI disponible indirectamente en `init_ui()`.

### Postcondiciones

`directorio_trabajo`, `estaciones_por_pagina`, `pagina_actual`, `archivos_mseed`, `fases_detectadas`, `mapa_estaciones` inicializados.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.archivos_mseed` | Referenciado en `__init__()` |
| `self.directorio_trabajo` | Referenciado en `__init__()` |
| `self.estaciones_por_pagina` | Referenciado en `__init__()` |
| `self.fases_detectadas` | Referenciado en `__init__()` |
| `self.gestor_fases` | Referenciado en `__init__()` |
| `self.init_ui` | Referenciado en `__init__()` |
| `self.mapa_estaciones` | Referenciado en `__init__()` |
| `self.pagina_actual` | Referenciado en `__init__()` |
| `self.setWindowTitle` | Referenciado en `__init__()` |
| `self.showMaximized` | Referenciado en `__init__()` |

### Riesgo de mantenimiento

Contiene ruta hardcodeada y llama a `init_ui()`, que a su vez dispara carga de fecha. Cualquier error de rutas puede ocurrir durante construcción del objeto.

---

## 10.2. `VentanaPrincipal.init_ui()`

### Rol

Construye layout combinado UI+gráfico, carga `marcar_fases.ui`, crea figura Matplotlib y conecta señales.

### Precondiciones

Debe existir `src/ui/marcar_fases.ui` relativo al script.

### Postcondiciones

Señales conectadas; `figura` y `canvas` disponibles; se intenta cargar fecha actual.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.anterior_pagina` | Referenciado en `init_ui()` |
| `self.boton_anterior` | Referenciado en `init_ui()` |
| `self.boton_directorio` | Referenciado en `init_ui()` |
| `self.boton_salir` | Referenciado en `init_ui()` |
| `self.boton_siguiente` | Referenciado en `init_ui()` |
| `self.cambiar_directorio` | Referenciado en `init_ui()` |
| `self.cambio_de_fecha` | Referenciado en `init_ui()` |
| `self.canvas` | Referenciado en `init_ui()` |
| `self.cargar_evento` | Referenciado en `init_ui()` |
| `self.centralWidget` | Referenciado en `init_ui()` |
| `self.cerrar_ventana` | Referenciado en `init_ui()` |
| `self.checkbox_filtro` | Referenciado en `init_ui()` |
| `self.combo_sis` | Referenciado en `init_ui()` |
| `self.date_edit` | Referenciado en `init_ui()` |
| `self.figura` | Referenciado en `init_ui()` |
| `self.lista_mseed` | Referenciado en `init_ui()` |
| `self.seleccionar_grafico_mseed` | Referenciado en `init_ui()` |
| `self.setCentralWidget` | Referenciado en `init_ui()` |
| `self.siguiente_pagina` | Referenciado en `init_ui()` |

### Riesgo de mantenimiento

Depende de nombres exactos de widgets del UI. Llama a `cambio_de_fecha()` al final.

---

## 10.3. `VentanaPrincipal.cerrar_ventana()`

### Rol

Cierra la ventana principal.

### Precondiciones

Ninguna.

### Postcondiciones

Ventana cerrada.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.close` | Referenciado en `cerrar_ventana()` |

### Riesgo de mantenimiento

No guarda fases antes de cerrar. Si hay cambios en memoria y `guardar_evento()` no fue llamado, se pierden.

---

## 10.4. `VentanaPrincipal.graficar_evento()`

### Rol

Grafica los MSEED del evento actual por página, colorea según aporte y detecta fases automáticas si aún no existen.

### Precondiciones

`directorios`, `archivos_mseed`, `matriz_eventos`, `archivo_sis`, `mapa_estaciones`, `figura`, `canvas` deben estar definidos.

### Postcondiciones

`axes` actualizado; `fases_detectadas` puede ampliarse; canvas redibujado.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.archivo_sis` | Referenciado en `graficar_evento()` |
| `self.archivos_mseed` | Referenciado en `graficar_evento()` |
| `self.axes` | Referenciado en `graficar_evento()` |
| `self.canvas` | Referenciado en `graficar_evento()` |
| `self.checkbox_filtro` | Referenciado en `graficar_evento()` |
| `self.directorios` | Referenciado en `graficar_evento()` |
| `self.estaciones_por_pagina` | Referenciado en `graficar_evento()` |
| `self.fases_detectadas` | Referenciado en `graficar_evento()` |
| `self.figura` | Referenciado en `graficar_evento()` |
| `self.mapa_estaciones` | Referenciado en `graficar_evento()` |
| `self.matriz_eventos` | Referenciado en `graficar_evento()` |
| `self.pagina_actual` | Referenciado en `graficar_evento()` |

### Riesgo de mantenimiento

Lee archivos MSEED en cada llamada; el filtro está comentado; no maneja errores de lectura individuales; re-detecta solo si archivo no existe en `fases_detectadas`.

---

## 10.5. `VentanaPrincipal.cambiar_directorio()`

### Rol

Permite seleccionar nuevo directorio de trabajo y recarga la fecha actual.

### Precondiciones

GUI activa.

### Postcondiciones

`directorio_trabajo` actualizado si el usuario selecciona ruta.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.cambio_de_fecha` | Referenciado en `cambiar_directorio()` |
| `self.directorio_trabajo` | Referenciado en `cambiar_directorio()` |

### Riesgo de mantenimiento

No valida estructura RSA del directorio seleccionado antes de llamar `cambio_de_fecha()`.

---

## 10.6. `VentanaPrincipal.cambio_de_fecha()`

### Rol

Reinicia fases en memoria, construye archivo base del día, obtiene directorios, lee matriz CSV y lista eventos `.sis`.

### Precondiciones

`directorio_trabajo` y `date_edit` disponibles.

### Postcondiciones

`fecha_seleccionada`, `directorios`, `matriz_eventos`, combo de `.sis` y gráfica inicial actualizados.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.canvas` | Referenciado en `cambio_de_fecha()` |
| `self.cargar_evento` | Referenciado en `cambio_de_fecha()` |
| `self.combo_sis` | Referenciado en `cambio_de_fecha()` |
| `self.date_edit` | Referenciado en `cambio_de_fecha()` |
| `self.directorio_trabajo` | Referenciado en `cambio_de_fecha()` |
| `self.directorios` | Referenciado en `cambio_de_fecha()` |
| `self.fases_detectadas` | Referenciado en `cambio_de_fecha()` |
| `self.fecha_seleccionada` | Referenciado en `cambio_de_fecha()` |
| `self.figura` | Referenciado en `cambio_de_fecha()` |
| `self.lista_mseed` | Referenciado en `cambio_de_fecha()` |
| `self.matriz_eventos` | Referenciado en `cambio_de_fecha()` |

### Riesgo de mantenimiento

Lee `archivo_csv` antes del bloque `try`; si el CSV no existe, puede fallar antes de manejar `FileNotFoundError` del directorio. Reinicia `fases_detectadas`, por lo que ignora JSON previo.

---

## 10.7. `VentanaPrincipal.cargar_evento()`

### Rol

Toma el `.sis` seleccionado, construye ruta FAS/JSON, lista MSEED coincidentes y dispara graficación.

### Precondiciones

`directorios`, `fecha_seleccionada`, `combo_sis` disponibles.

### Postcondiciones

`archivo_sis`, `archivo_fas`, `archivo_json`, `archivos_mseed` actualizados; `lista_mseed` poblada; gráfico redibujado.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.archivo_fas` | Referenciado en `cargar_evento()` |
| `self.archivo_json` | Referenciado en `cargar_evento()` |
| `self.archivo_sis` | Referenciado en `cargar_evento()` |
| `self.archivos_mseed` | Referenciado en `cargar_evento()` |
| `self.combo_sis` | Referenciado en `cargar_evento()` |
| `self.directorios` | Referenciado en `cargar_evento()` |
| `self.fecha_seleccionada` | Referenciado en `cargar_evento()` |
| `self.graficar_evento` | Referenciado en `cargar_evento()` |
| `self.lista_mseed` | Referenciado en `cargar_evento()` |
| `self.mapa_estaciones` | Referenciado en `cargar_evento()` |

### Riesgo de mantenimiento

Construye `archivo_json` desde `archivo_csv` como si fuera directorio; no carga JSON existente; no resetea `pagina_actual` al cambiar de evento.

---

## 10.8. `VentanaPrincipal.seleccionar_grafico_mseed()`

### Rol

Abre una ventana detallada para editar fases del MSEED seleccionado.

### Precondiciones

El archivo seleccionado debe existir en `fases_detectadas`.

### Postcondiciones

Se crea y muestra `VentanaGrafico`; `gestor_fases` queda apuntando al gestor de esa ventana.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.date_edit` | Referenciado en `seleccionar_grafico_mseed()` |
| `self.directorios` | Referenciado en `seleccionar_grafico_mseed()` |
| `self.fases_detectadas` | Referenciado en `seleccionar_grafico_mseed()` |
| `self.gestor_fases` | Referenciado en `seleccionar_grafico_mseed()` |

### Riesgo de mantenimiento

Asume que el texto contiene archivo entre paréntesis y que existe en `fases_detectadas`.

---

## 10.9. `VentanaPrincipal.anterior_pagina()`

### Rol

Retrocede una página y redibuja.

### Precondiciones

`pagina_actual >= 0`.

### Postcondiciones

`pagina_actual` puede disminuir.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.graficar_evento` | Referenciado en `anterior_pagina()` |
| `self.pagina_actual` | Referenciado en `anterior_pagina()` |

### Riesgo de mantenimiento

No actualiza estado visual de botones.

---

## 10.10. `VentanaPrincipal.siguiente_pagina()`

### Rol

Avanza una página si existe página siguiente.

### Precondiciones

`archivos_mseed` definido.

### Postcondiciones

`pagina_actual` puede aumentar.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.archivos_mseed` | Referenciado en `siguiente_pagina()` |
| `self.estaciones_por_pagina` | Referenciado en `siguiente_pagina()` |
| `self.graficar_evento` | Referenciado en `siguiente_pagina()` |
| `self.pagina_actual` | Referenciado en `siguiente_pagina()` |

### Riesgo de mantenimiento

Si `archivos_mseed` está vacío, `max_pagina = -1`; no falla, pero la semántica es frágil.

---

## 10.11. `VentanaPrincipal.guardar_evento()`

### Rol

Persiste `fases_detectadas` en `archivo_json`.

### Precondiciones

`fases_detectadas` no vacío; `archivo_json` válido.

### Postcondiciones

Archivo JSON escrito si no hay errores.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.archivo_json` | Referenciado en `guardar_evento()` |
| `self.fases_detectadas` | Referenciado en `guardar_evento()` |

### Riesgo de mantenimiento

No está conectado a ningún botón según el script; la ruta JSON puede estar mal construida; sólo imprime errores.

---

## 10.12. `VentanaGrafico.__init__()`

### Rol

Inicializa ventana de detalle para un MSEED específico y conserva referencias compartidas.

### Precondiciones

Ruta de eventos y archivo seleccionado válidos.

### Postcondiciones

Ventana y gráfico inicializados.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.archivo_seleccionado` | Referenciado en `__init__()` |
| `self.directorio_eventos` | Referenciado en `__init__()` |
| `self.fases_detectadas` | Referenciado en `__init__()` |
| `self.fecha` | Referenciado en `__init__()` |
| `self.gestor_fases` | Referenciado en `__init__()` |
| `self.init_ui` | Referenciado en `__init__()` |
| `self.parent` | Referenciado en `__init__()` |
| `self.setGeometry` | Referenciado en `__init__()` |
| `self.setWindowTitle` | Referenciado en `__init__()` |

### Riesgo de mantenimiento

Mantiene referencia directa a `parent` y `fases_detectadas`.

---

## 10.13. `VentanaGrafico.init_ui()`

### Rol

Construye figura, canvas y toolbar; llama a `graficar_mseed()`.

### Precondiciones

Matplotlib y Qt disponibles.

### Postcondiciones

Canvas/toolbar visibles.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.canvas` | Referenciado en `init_ui()` |
| `self.figura` | Referenciado en `init_ui()` |
| `self.graficar_mseed` | Referenciado en `init_ui()` |
| `self.setCentralWidget` | Referenciado en `init_ui()` |
| `self.toolbar` | Referenciado en `init_ui()` |

### Riesgo de mantenimiento

Si el MSEED no puede abrirse, el error aparece en `graficar_mseed()`.

---

## 10.14. `VentanaGrafico.graficar_mseed()`

### Rol

Lee MSEED detallado, grafica un trace y dibuja fases existentes con GestorFases.

### Precondiciones

`archivo_seleccionado` debe existir en `fases_detectadas`; el archivo MSEED debe existir.

### Postcondiciones

Eventos Matplotlib conectados; fases dibujadas.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.archivo_seleccionado` | Referenciado en `graficar_mseed()` |
| `self.canvas` | Referenciado en `graficar_mseed()` |
| `self.directorio_eventos` | Referenciado en `graficar_mseed()` |
| `self.fases_detectadas` | Referenciado en `graficar_mseed()` |
| `self.fases_estacion` | Referenciado en `graficar_mseed()` |
| `self.figura` | Referenciado en `graficar_mseed()` |
| `self.gestor_fases` | Referenciado en `graficar_mseed()` |
| `self.id_estacion` | Referenciado en `graficar_mseed()` |

### Riesgo de mantenimiento

Usa `st[0]` aunque en la vista principal se selecciona componente según mapa; puede graficar componente distinta. Depende de claves de colores en `gestor_fases.colores`.

---

## 10.15. `VentanaGrafico.closeEvent()`

### Rol

Obtiene fases actualizadas del gestor, actualiza el diccionario del padre y redibuja la vista principal.

### Precondiciones

`gestor_fases` válido.

### Postcondiciones

`parent.fases_detectadas[archivo]` actualizado en memoria.

### Atributos usados

| Atributo | Uso |
|---|---|
| `self.archivo_seleccionado` | Referenciado en `closeEvent()` |
| `self.gestor_fases` | Referenciado en `closeEvent()` |
| `self.parent` | Referenciado en `closeEvent()` |

### Riesgo de mantenimiento

Actualiza memoria, pero no persiste a JSON automáticamente.

---

# 11. Matriz método → estado modificado

| Método | Lee | Modifica | Impacto |
|---|---|---|---|
| `__init__()` | entorno/librerías | estado inicial | Alto |
| `init_ui()` | UI `.ui` | widgets, figura, canvas, conexiones | Muy alto |
| `cambio_de_fecha()` | `date_edit`, directorio | `fases_detectadas`, `fecha_seleccionada`, `directorios`, `matriz_eventos`, combo/lista/gráfico | Muy alto |
| `cargar_evento()` | `combo_sis`, `directorios`, fecha | `archivo_sis`, `archivo_fas`, `archivo_json`, `archivos_mseed`, lista, gráfico | Muy alto |
| `graficar_evento()` | MSEED, matriz, parámetros | `axes`, `fases_detectadas`, figura | Muy alto |
| `seleccionar_grafico_mseed()` | lista, `fases_detectadas` | `gestor_fases`, ventana hija | Alto |
| `anterior_pagina()` | `pagina_actual` | `pagina_actual`, gráfico | Medio |
| `siguiente_pagina()` | `archivos_mseed`, `pagina_actual` | `pagina_actual`, gráfico | Medio |
| `guardar_evento()` | `fases_detectadas`, `archivo_json` | JSON | Muy alto |
| `VentanaGrafico.graficar_mseed()` | MSEED, fases | figura, eventos Matplotlib | Alto |
| `VentanaGrafico.closeEvent()` | gestor | `parent.fases_detectadas`, gráfico padre | Muy alto |

---

# 12. Riesgos operativos detallados

## R-01. Ruta hardcodeada

```python
self.directorio_trabajo = "G:\Mi unidad\DIA"
```

### Impacto

Reduce portabilidad y puede fallar en otro equipo.

### Corrección segura

```python
self.directorio_trabajo = os.environ.get("RSA_DIRECTORIO", "G:\Mi unidad\DIA")
```

o cargar desde configuración.

---

## R-02. `guardar_evento()` no conectado

El método existe, pero no está conectado a botón ni a cierre de ventana principal.

### Impacto

Las fases editadas quedan sólo en memoria si no se invoca manualmente.

### Corrección segura

Agregar botón o conectar guardado automático con confirmación al cerrar.

---

## R-03. Ruta JSON mal construida

El script usa `archivo_csv` como si fuera directorio.

### Impacto

El guardado puede fallar o intentar escribir en ruta inválida.

### Corrección segura

Usar `Directorio_dia`.

---

## R-04. No se carga JSON existente

Cada cambio de fecha reinicia:

```python
self.fases_detectadas = {}
```

y `cargar_evento()` no intenta cargar JSON previo.

### Impacto

El usuario puede perder trabajo previo o ver detecciones automáticas en lugar de fases ya revisadas.

---

## R-05. Filtro UI no funcional

El filtro está comentado:

```python
# tr.filter(...)
pass
```

### Impacto

La interfaz sugiere funcionalidad inexistente.

---

## R-06. Contrato frágil de `matriz_eventos`

El script depende de posiciones fijas dentro de cadenas de estación.

### Impacto

Cualquier cambio de formato rompe detección de aporte/filtro.

---

## R-07. Relectura de MSEED en cada redibujado

`graficar_evento()` lee cada archivo con `obspy.read()` cada vez que se cambia página o se refresca.

### Impacto

Puede ser lento con eventos grandes.

---

## R-08. Selección de trace inconsistente

En `graficar_evento()` se elige trace según componente del mapa. En `VentanaGrafico.graficar_mseed()` se usa `st[0]`.

### Impacto

La vista detallada puede no corresponder a la misma componente graficada en la vista principal.

---

## R-09. Actualización en memoria sin persistencia

`VentanaGrafico.closeEvent()` actualiza `parent.fases_detectadas`, pero no escribe JSON.

### Impacto

Cambios manuales pueden perderse.

---

# 13. Contratos para `GestorFases`

Aunque `GestorFases` está fuera de este script, `fases.py` depende de este contrato:

## Métodos obligatorios

```python
inicializar_fases(ax)
al_presionar(event, ax, canvas)
al_mover(event, canvas)
al_soltar(event)
obtener_fases()
```

## Atributos esperados

```python
colores: dict[str, str]
```

Debe contener al menos:

```python
{
    "P": "red",
    "S": "blue",
    "Coda": "green"
}
```

## Contrato de salida

`obtener_fases()` debe devolver un diccionario compatible con `fases_detectadas[archivo]`.

---

# 14. Contrato de persistencia JSON

## Estructura obligatoria

```json
{
  "BOB1_20240505_143022.mseed": {
    "P": [1.23],
    "S": [2.34],
    "Coda": [10.0]
  }
}
```

## Reglas

- Codificación UTF-8.
- Indentación recomendada: 4 espacios.
- No guardar objetos Python no serializables.
- No guardar rutas absolutas como claves.
- Las claves deben ser nombres de archivo MSEED.
- Debe poder recargarse sin perder fases manuales.

---

# 15. Reglas para agentes de mantenimiento

## 15.1 Antes de modificar

Un agente debe identificar:

1. método afectado;
2. atributos leídos;
3. atributos modificados;
4. archivos afectados;
5. contratos de datos involucrados;
6. checklist mínimo de regresión.

## 15.2 No hacer sin autorización explícita

- Cambiar formato JSON.
- Cambiar formato de matriz de eventos.
- Eliminar `GestorFases`.
- Cambiar nombres de widgets del `.ui`.
- Cambiar estructura de directorios.
- Reemplazar detección automática sin mantener firma.
- Guardar fases automáticamente sin informar al usuario o registrar el flujo.

## 15.3 Cambios seguros recomendados

- Validaciones previas.
- Reemplazar rutas concatenadas por `os.path.join`.
- Separar funciones auxiliares sin cambiar comportamiento.
- Agregar mensajes de error más claros.
- Agregar carga de JSON previo preservando detecciones automáticas.

---

# 16. Checklist de regresión exhaustivo

## 16.1 Inicio

- [ ] La ventana abre maximizada.
- [ ] `marcar_fases.ui` se carga.
- [ ] Se crea `figura`.
- [ ] Se crea `canvas`.
- [ ] Se conectan botones principales.
- [ ] Se ejecuta `cambio_de_fecha()` sin errores con fecha válida.

## 16.2 Directorio

- [ ] Directorio predeterminado funciona en el entorno del usuario.
- [ ] Cambiar directorio actualiza `directorio_trabajo`.
- [ ] Cambiar directorio recarga fecha.
- [ ] Directorio inválido muestra error y limpia UI.

## 16.3 Fecha

- [ ] Cambiar fecha reinicia `fases_detectadas`.
- [ ] Se obtiene `directorios`.
- [ ] Se lee `archivo_csv`.
- [ ] Se listan `.sis`.
- [ ] Si no hay `.sis`, limpia lista y gráfico.

## 16.4 Evento

- [ ] Seleccionar `.sis` actualiza `archivo_sis`.
- [ ] Se calcula hora del `.sis`.
- [ ] Se genera patrón MSEED correcto.
- [ ] Se listan MSEED correctos.
- [ ] Se llena `lista_mseed`.

## 16.5 Gráfico principal

- [ ] Se grafica una página de hasta 5 estaciones.
- [ ] La estación que aporta se muestra azul.
- [ ] La estación que no aporta se muestra gris.
- [ ] Se detectan fases sólo si no existen previamente.
- [ ] `fases_detectadas` se llena con claves MSEED.
- [ ] Paginación anterior/siguiente funciona.
- [ ] No falla con cero MSEED.

## 16.6 Ventana detallada

- [ ] Doble clic abre `VentanaGrafico`.
- [ ] Se grafica el MSEED.
- [ ] Se muestran fases existentes.
- [ ] `GestorFases` recibe eventos Matplotlib.
- [ ] Cerrar ventana actualiza `fases_detectadas`.
- [ ] Vista principal se refresca.

## 16.7 Edición de fases

- [ ] Agregar fase.
- [ ] Mover fase.
- [ ] Eliminar fase.
- [ ] Cerrar ventana mantiene cambios en memoria.
- [ ] Guardar escribe JSON correcto.
- [ ] Reabrir evento carga JSON previo, si se implementa.

## 16.8 Persistencia

- [ ] `archivo_json` apunta a `Directorio_dia`.
- [ ] JSON se escribe con UTF-8.
- [ ] JSON conserva `P`, `S`, `Coda`.
- [ ] No se pierden fases manuales al cambiar página.
- [ ] No se pierden fases manuales al cerrar ventana detallada.

---

# 17. Estrategia de refactorización por fases

## Fase 0: Correcciones críticas sin cambiar arquitectura

1. Corregir ruta JSON.
2. Conectar `guardar_evento()`.
3. Cargar JSON existente al abrir evento.
4. Validar existencia de archivos.
5. Implementar o deshabilitar visualmente filtro.

## Fase 1: Robustez

1. Agregar método `_construir_archivo_base(fecha)`.
2. Agregar método `_construir_archivo_json()`.
3. Agregar método `_cargar_json_si_existe()`.
4. Agregar método `_guardar_json()`.
5. Agregar validaciones de `matriz_eventos`.

## Fase 2: Separación de servicios

Crear:

```text
ServicioDirectoriosFases
ServicioPersistenciaFases
ServicioListadoEventos
ServicioGraficacionFases
ServicioPaginacion
```

## Fase 3: Modelo de datos explícito

Crear dataclasses:

```python
@dataclass
class FasesEstacion:
    p: list[float]
    s: list[float]
    coda: list[float]

@dataclass
class EventoFases:
    archivo_sis: str
    archivos_mseed: list[str]
    fases: dict[str, FasesEstacion]
```

## Fase 4: Pruebas

- Pruebas de construcción de rutas.
- Pruebas de parseo de `.sis`.
- Pruebas de patrón MSEED.
- Pruebas de lectura/escritura JSON.
- Pruebas de paginación.
- Pruebas de preservación de fases editadas.

---

# 18. Puntos de intervención segura

## Corregir ruta JSON

Método: `cargar_evento()`

Cambio seguro:

```python
self.archivo_json = os.path.join(
    self.directorios['Directorio_dia'],
    self.archivo_sis.replace('.sis', '.json')
)
```

## Conectar guardado

Método: `init_ui()`

Opción mínima:

```python
self.boton_guardar.clicked.connect(self.guardar_evento)
```

si el widget existe.

## Guardar al cerrar ventana principal

Implementar `closeEvent()` en `VentanaPrincipal`, con confirmación.

## Cargar JSON existente

Método: `cargar_evento()`

Después de definir `archivo_json`, si existe, cargar y fusionar o reemplazar.

---

# 19. Plantilla de solicitud para agente

```text
Trabaja sobre fases.py.

Objetivo:
[describir cambio]

No romper:
- formato fases_detectadas;
- contrato con GestorFases;
- carga de .sis;
- patrón MSEED;
- JSON de fases.

Métodos permitidos:
- [listar métodos]

Checklist obligatorio:
- carga de fecha;
- carga de evento;
- gráfico principal;
- ventana detallada;
- edición de fases;
- guardado JSON;
- reapertura JSON.

Entrega:
- diff del código;
- actualización de este contexto si cambia el flujo.
```

---

# 20. Conclusión operativa

Para un agente, los puntos más importantes son:

1. `fases_detectadas` es el estado central.
2. `cargar_evento()` define el evento activo y la ruta JSON.
3. `graficar_evento()` detecta fases y llena memoria.
4. `VentanaGrafico.closeEvent()` actualiza memoria, no disco.
5. `guardar_evento()` escribe disco, pero actualmente no se llama desde UI.
6. La ruta JSON actual debe corregirse antes de confiar en persistencia.
7. No se debe cambiar el formato de `matriz_eventos` ni el contrato con `GestorFases` sin actualizar todo el flujo.
