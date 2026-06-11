# Contexto del Programa: `Insercion de estaciones EVT.py`
## Alcance de este contexto

Este documento describe el comportamiento real del script `Insercion de estaciones EVT.py` y sirve como contexto de trabajo para cualquier agente de revisión o corrección de código. El objetivo no es reescribir completamente el programa, sino permitir que un agente entienda su propósito, su flujo operativo y los puntos reproducibles que deben verificarse antes de modificarlo.

El contexto debe usarse junto con el script real. Cuando exista diferencia entre este documento y el código, el agente debe priorizar la conducta efectivamente implementada en el script y proponer correcciones puntuales.

## Identidad del Programa

Este script implementa una aplicación de escritorio para **inserción de eventos sísmicos** provenientes de archivos EVT, formato propietario usado por digitalizadores Kinemetrics, dentro de la estructura de datos del sistema RSA.

Su función principal es leer archivos EVT, intentar ajustar sus tiempos contra el catálogo de eventos del día correspondiente, clasificarlos automáticamente, generar una verificación gráfica opcional y, si corresponde, insertar el registro como archivo MiniSEED en la estructura de datos del proyecto.

El script maneja tres modos de carga de archivos EVT:

- Desde una estructura de directorios organizada por año y subdirectorios.
- Desde una lista CSV con rutas a archivos EVT.
- Desde una búsqueda recursiva en un directorio completo.

## Propósito Principal

Automatizar el proceso de ingesta de registros sísmicos provenientes de equipos digitalizadores ETNA u otros equipos que generen archivos EVT compatibles con ObsPy.

El script permite:

- Leer archivos EVT mediante `obspy.read(..., format='KINEMETRICS_EVT')`.
- Extraer metadatos del equipo, como modelo, versión y número de serie.
- Normalizar códigos de estación mediante diccionarios internos.
- Localizar el catálogo de eventos del día correspondiente.
- Ajustar el tiempo del registro contra eventos existentes del catálogo, usando una tolerancia fija de 5 minutos.
- Clasificar automáticamente el evento mediante `clasificar_evento_sismico()`.
- Mostrar gráficos de verificación si la opción está habilitada.
- Insertar el archivo MiniSEED y actualizar el catálogo CSV si la inserción está habilitada y el evento calza con el catálogo.
- Generar un reporte consolidado del procesamiento.

## Arquitectura General

### Estilo de Aplicación

- Aplicación de escritorio con interfaz gráfica PyQt5.
- Flujo controlado por eventos de la interfaz.
- Procesamiento por lotes con barra de progreso.
- Ayuda integrada cargada desde un archivo HTML.
- Soporte para tres modos de selección de archivos EVT.
- Uso de ObsPy para lectura de EVT y escritura MiniSEED.
- Uso de Matplotlib para verificación gráfica.

### Modos de Operación

#### Modo Directorio 1

El usuario selecciona un directorio raíz. El script lista sus subdirectorios y los muestra en `cmbx_eventos`. En el uso esperado, estos subdirectorios corresponden a años, aunque el script no valida que realmente sean años.

Al seleccionar uno de esos subdirectorios, el script carga en `cmbx_subdirectorios` los directorios internos encontrados. Estos pueden usarse como filtro, o se puede seleccionar `Todos`.

#### Modo Lista CSV

El usuario selecciona un archivo CSV. El script lee el archivo y busca rutas EVT en las filas. La función `extraer_rutas_evt_desde_lista()` no se limita estrictamente a la primera columna: si una fila tiene varias celdas, busca la primera celda no vacía que termine en `.evt`. Si no encuentra una, usa la primera celda no vacía como ruta candidata.

#### Modo Directorio 2

El usuario selecciona un directorio raíz. El script recorre recursivamente todos sus subdirectorios y acumula los archivos cuya extensión termina en `.evt`, sin distinguir mayúsculas y minúsculas.

### Modo de Destino

Si el radio `radio_estacion_serial` está activado, el script solicita un directorio destino. En ese caso, los archivos insertados se guardan en subcarpetas nombradas con el número de serie del equipo, y el nombre del archivo MiniSEED usa el serial como prefijo.

Si no está activado, el script guarda los MiniSEED directamente en el directorio de eventos del día determinado por `obtener_directorios()`.

## Flujo de Ejecución

### Fase 1: Inicio de la Aplicación (`__init__`)

Al iniciar el programa:

1. Se determina la ubicación del proyecto buscando el directorio `rsa_sismologia` dentro de la ruta del script.
2. Se construyen rutas hacia `src/librerias` y `datos`.
3. Se agregan esas rutas a `sys.path`.
4. Se carga la interfaz gráfica desde `src/ui/Insertar_evt.ui`.
5. Se carga la ayuda HTML desde `ayuda/ayuda_insercion_evt.html`; si no existe, se usa `datos/ayuda_insercion_evt.html` como respaldo.
6. Se establece el directorio de trabajo por defecto: `G:/Mi unidad/DIA/`.
7. Se inicializa la barra de progreso en cero.
8. Se conectan los botones de la interfaz a sus métodos.
9. Se cargan los parámetros de estaciones mediante `parametros_estaciones()`.

## Punto reproducible: raíz del proyecto no validada

El script busca el directorio `rsa_sismologia` mediante `extraer_hasta_directorio()`. Si no lo encuentra, `ruta_proyecto` queda como cadena vacía. A partir de eso se construyen rutas potencialmente inválidas hacia librerías, datos e interfaz.

El agente debe agregar una validación temprana para detener el programa con un mensaje claro si no se encuentra la raíz del proyecto.

## Fase 2: Selección de Origen de Datos

El método `cargar_directorio_origen()` responde según el radio seleccionado:

### Opción 1: Directorio EVT estructurado

- Abre un diálogo para seleccionar un directorio raíz.
- Lista sus subdirectorios.
- Los carga en `cmbx_eventos`.
- Actualiza `cmbx_subdirectorios` con los subdirectorios del elemento seleccionado.

### Opción 2: Lista CSV

- Abre un diálogo para seleccionar un archivo CSV.
- Guarda la ruta en `self.ruta_csv`.
- El procesamiento real de las rutas ocurre luego, en `iniciar_procesamiento()`.

### Opción 3: Directorio EVT completo

- Abre un diálogo para seleccionar un directorio raíz.
- Recorre recursivamente todos los subdirectorios.
- Acumula los archivos `.evt` encontrados.
- Muestra cuántos archivos EVT fueron encontrados.

## Fase 3: Inicio del Procesamiento

El método `iniciar_procesamiento()` orquesta el flujo principal.

Primero revisa si se debe insertar por serial. Si `radio_estacion_serial` está activado, solicita un directorio destino. Si no se selecciona, cancela el proceso.

Luego, según el modo activo:

- En modo Directorio 1, recolecta archivos EVT desde el directorio seleccionado y aplica el filtro del subdirectorio si corresponde.
- En modo Lista CSV, lee el CSV y extrae las rutas EVT mediante `extraer_rutas_evt_desde_lista()`.
- En modo Directorio 2, usa la lista de EVT recolectada previamente.

Después llama a `procesar_lista_archivos_evt()` y finalmente guarda el reporte en:

```text
procesados_desde_csv.csv
```

Este nombre se usa siempre, incluso cuando el procesamiento no proviene de un CSV.

## Punto reproducible: nombre del reporte

El reporte final siempre se llama `procesados_desde_csv.csv`, aun cuando los datos se procesan desde directorio estructurado o desde búsqueda recursiva. El agente puede evaluar si conviene renombrarlo a algo más general, por ejemplo `procesamiento_evt.csv`, o mantenerlo por compatibilidad.

## Fase 4: Procesamiento por Lote

La función `procesar_lista_archivos_evt()`:

1. Crea una lista de resumen con encabezado.
2. Configura la barra de progreso según la cantidad de archivos.
3. Itera por cada archivo EVT.
4. Llama a `procesar_archivo_evt()`.
5. Si ocurre un error inesperado, genera una fila de error mediante `construir_fila_resumen_error()`.
6. Actualiza la barra de progreso.
7. Devuelve el resumen completo.

## Fase 5: Procesamiento de un Archivo EVT Individual

La función `procesar_archivo_evt()` es el núcleo del script.

### Subpaso 1: Lectura del EVT

Intenta leer el archivo con:

```python
read(archivo_evt, format='KINEMETRICS_EVT')
```

Si falla:

- Marca el archivo como no compatible.
- Intenta ejecutar `ejecutar_en_vm(archivo_evt, r'O:\KINEMETRICS')`.
- Devuelve una fila de resumen indicando que no fue insertado.

### Subpaso 2: Construcción de ruta base del día

A partir del `starttime` de la primera traza, construye una ruta base:

```text
AAAAMMDDhhmmss
```

Esa ruta se combina con el directorio de trabajo y se pasa a `obtener_directorios()`.

### Subpaso 3: Extracción de metadatos

El script intenta extraer:

- `comment` como modelo del equipo.
- `instrument` como versión del instrumento.
- `serialnumber` como número de serie.

Si falla, conserva valores por defecto como `Desconocido` o `Desconocida`.

### Subpaso 4: Normalización de estación

La estación se toma de:

```python
st[0].stats.station
```

Luego se normaliza con `normalizar_codigo_estacion_desde_evt()`.

El diccionario de directorios se usa para construir una descripción de la ruta de almacenamiento, pero no determina directamente la estación insertada en el catálogo.

### Subpaso 5: Localización del catálogo del día

El script intenta obtener la ruta del CSV de eventos con:

```python
directorios.get('Archivo_csv') or directorios.get('archivo_csv')
```

Si la ruta existe, lee los eventos del día.

Si no existe, marca el archivo como no localizado y no puede insertar el evento.

## Fase 6: Ajuste de Tiempos contra Catálogo

La función `ajustar_tiempos_stream_con_catalogo()` busca el evento más cercano dentro del catálogo.

Proceso:

1. Toma la primera traza del stream.
2. Normaliza la estación desde `stats.station`.
3. Toma el tiempo inicial del stream.
4. Recorre los eventos del catálogo.
5. Considera solo eventos con tipo `FF`, `FC` o `SISMO`.
6. Extrae el texto temporal desde `evento[1]`, esperando el formato `YYYYMMDD_HHMMSS.sis` o al menos `YYYYMMDD_HHMMSS`.
7. Calcula la diferencia absoluta entre el tiempo del stream y el evento.
8. Selecciona el evento más cercano dentro de una tolerancia de 5 minutos.
9. Si hay coincidencia, calcula el delta y ajusta el `starttime` de todas las trazas del stream.
10. Retorna el stream ajustado, la bandera de localización, el tipo de evento encontrado y un nombre nominal de MSEED.

## Punto reproducible crítico: nombre nominal del MSEED se arma antes del ajuste

Dentro de `ajustar_tiempos_stream_con_catalogo()`, el nombre nominal del MSEED se construye antes de ajustar el tiempo del stream:

```python
inicio = tr.stats.starttime
archivo_mseed = f"{estacion}_{inicio.strftime('%Y%m%d_%H%M%S')}.mseed"
```

Luego, si se encuentra un evento cercano, se ajusta el `starttime` de las trazas.

Esto significa que `archivo_mseed` puede quedar con el tiempo original, no con el tiempo ajustado. En cambio, `insertar_evento_en_catalogo()` vuelve a construir el nombre del archivo usando el `starttime` ya ajustado.

Consecuencia:

- El archivo realmente escrito puede tener un nombre.
- La ruta reportada en `archivo_mseed` puede tener otro nombre.

El agente debe corregir esto para que el nombre nominal se construya después del ajuste temporal, o para que el reporte use la ruta real devuelta por la inserción.

## Fase 7: Clasificación Automática

Después del ajuste temporal, el script crea una copia del stream y llama a:

```python
clasificar_evento_sismico(st_copia)
```

El resultado se convierte en texto usando pares clave-valor.

La clasificación no cambia directamente el tipo del evento en el catálogo. El tipo `FF`, `FC` o `SISMO` usado para localizar el evento proviene del catálogo existente.

## Fase 8: Verificación Gráfica Opcional

Si `bandera_verificar` está activada:

- Se cierran figuras previas de Matplotlib.
- Se crea una figura con una subgráfica por traza.
- Se grafica cada traza.
- Se muestra la figura de forma no modal con `fig.show()` y `plt.pause(0.001)`.
- Se guarda una referencia a la figura en la ventana principal para evitar que se cierre prematuramente.
- Se limita el número de figuras mantenidas a 5.

## Punto verificado: el grafico se muestra, pero no se guarda como PNG

La verificacion grafica muestra una figura Matplotlib. En el script actual no se llama a `savefig()` ni se genera un archivo PNG de verificacion.

Ademas, el mensaje de confirmacion al usuario dice:

```text
Se abrio la figura de verificacion.
Deseas insertar este evento en la estructura de datos?
```

El mensaje es coherente con la accion real: el script muestra la figura, no la guarda.
## Punto reproducible: confirmación gráfica e inserción son opciones distintas

Si `bandera_verificar` está activada y el evento calza, el script pregunta al usuario si desea insertar el evento. Esto ocurre aunque el checkbox de inserción no esté activado.

Sin embargo, la inserción real solo ocurre si también está activa `bandera_insertar`.

Por tanto:

- Verificación activa + inserción desactivada: puede preguntar por inserción, pero no insertará.
- Verificación desactivada + inserción activada: insertará automáticamente si el evento calza, sin confirmación visual.

El agente debe revisar si esta lógica es la deseada.

## Fase 9: Inserción en Catálogo

La función `insertar_evento_en_catalogo()`:

1. Toma la primera traza del stream.
2. Normaliza la estación desde `stats.station`.
3. Define el prefijo del archivo.
4. Si hay serial, usa el serial como prefijo y crea una subcarpeta con ese serial.
5. Si no hay serial, usa la estación como prefijo.
6. Guarda el stream como MiniSEED.
7. Busca la estación en los parámetros de configuración.
8. Busca el evento correspondiente en el catálogo por nombre `YYYYMMDD_HHMMSS.sis`.
9. Calcula la columna destino como índice de estación + 3.
10. Escribe en la celda correspondiente el valor:

```text
ESTACION + COMPONENTE + 1000000
```

## Punto reproducible: nombre del archivo cuando se inserta por serial

Cuando se inserta por serial, el script usa:

```python
prefijo = str(serial_equipo) if serial_equipo else estacion
nombre_archivo = f"{prefijo}_{inicio.strftime('%Y%m%d_%H%M%S')}.mseed"
```

Por tanto, el archivo se guarda como:

```text
SERIAL_AAAAMMDD_HHMMSS.mseed
```

no como:

```text
ESTACION_AAAAMMDD_HHMMSS.mseed
```

Además, la ruta de reporte se arma en `procesar_archivo_evt()` con una operación dependiente de que el código de estación tenga 4 caracteres:

```python
serial_para_nombre + archivo_mseed_nominal[4:]
```

Esto puede ser frágil si el prefijo nominal no tiene exactamente cuatro caracteres o si cambia la nomenclatura.

El agente debe hacer coherente el nombre real del archivo, la ruta reportada y la lógica por serial.

## Punto reproducible: escritura MiniSEED sin parámetros explícitos

La escritura se hace con:

```python
st.write(ruta_completa, format='MSEED')
```

No se especifican codificación, longitud de registro ni escritura atómica. Si el proyecto requiere codificación específica, por ejemplo STEIM1 y `reclen=512`, el agente debe ajustarlo de forma coherente con los demás programas de la RSA.

## Fase 10: Reporte Consolidado

El archivo `procesados_desde_csv.csv` contiene una fila por archivo EVT procesado.

Columnas:

| Columna | Contenido |
|---|---|
| archivo_evt | Ruta del archivo EVT procesado |
| archivo_mseed | Ruta nominal o ruta prevista del MiniSEED |
| mensaje | Resultado de localización |
| archivo | Ruta base del día |
| insercion | Estado de inserción |
| resultado_str | Resultado de clasificación automática |
| directorio_estacion_almacenado | Ruta de origen con partes normalizadas |
| estacion | Código de estación normalizado desde EVT |
| equipo_modelo | Modelo extraído del EVT |
| equipo_version | Versión o instrumento extraído del EVT |
| equipo_serial | Número de serie extraído del EVT |

## Punto reproducible: `archivo_mseed` del reporte puede ser nominal, no real

Por la diferencia entre `archivo_mseed_nominal` y el nombre realmente escrito por `insertar_evento_en_catalogo()`, el reporte puede quedar apuntando a una ruta que no existe.

El agente debe verificar este punto ejecutando el flujo con un EVT cuyo tiempo sea ajustado contra catálogo. Si el nombre del reporte no coincide con el archivo insertado, debe corregirse.

## Estructura de Directorios

```text
rsa_sismologia/
├── src/
│   ├── librerias/
│   │   ├── rsa_io.py
│   │   └── metodos_rsa.py
│   └── ui/
│       └── Insertar_evt.ui
├── datos/
│   └── ayuda_insercion_evt.html
│
└── G:/Mi unidad/DIA/
    ├── procesados_desde_csv.csv
    └── (carpetas por día según obtener_directorios)
        ├── archivo_csv
        └── Directorio_eventos/
            ├── ESTACION_AAAAMMDD_HHMMSS.mseed
            └── SERIAL/
                └── SERIAL_AAAAMMDD_HHMMSS.mseed
```

## Diccionarios de Normalización

### `DICCIONARIO_ESTACIONES_EVT`

Mapea códigos de estación presentes en los EVT hacia códigos normalizados del sistema.

Ejemplos:

| Código EVT | Código normalizado |
|---|---|
| CHB | CHAB |
| CHC | CHAC |
| MZB | MABA |
| MZC | MACI |
| MZD | MADE |
| PABA | DPBA |
| PACI | DPCI |
| ACC1 | EEAS |
| UCET | UCET |
| UDEC | UCET |

### `DICCIONARIO_ESTACIONES_DIRECTORIO`

Mapea variantes de nombres de directorios hacia códigos normalizados. Se usa principalmente para construir una descripción de la ruta de almacenamiento, no para decidir directamente la estación del stream.

Ejemplos:

| Nombre de directorio | Código normalizado |
|---|---|
| Azogues, CICA | CICA |
| ChanludBase, ChaBase, Chanlbas | CHAB |
| Chanlcim, ChaCima, ChanludCima | CHAC |
| EEEBASE, EEBase, EEE-Base | EEBA |
| EEAlNor, EEALNor, EEE-AltNort | EEAN |
| EEAltSur, EEAlSur, EEE-AltSur | EEAS |
| Huajibam, Huajibamba, HUAJIBAM, Huajibamba-SSA | AHUA |
| MazarBas, MazarBase | MABA |
| MazarCim, MazarCima | MACI |
| MazarDer | MADE |
| Miraflo, Miraflor, Miraflores | MIRA |
| PauteBas, Pautebas, PauteBase | DPBA |
| PauMed | DPME |
| PauteCim, PauteCima | DPCI |
| Regcivil | REGC |
| UAzuay | UDAZ |
| UCCamp, UCcamp | UCET |
| UCoficin | UCAO |

## Punto reproducible: claves duplicadas o vacías en diccionarios

El script contiene algunas entradas duplicadas o vacías en los diccionarios, por ejemplo claves `""` repetidas y algunas variantes repetidas como `Chanlbas` o `PauteCim`.

No necesariamente rompen el programa, porque Python conserva la última asignación, pero conviene limpiarlas para evitar confusión.

## Interfaz de Usuario

### Controles de modo de origen

| Control | Propósito |
|---|---|
| `radioDirectorio1` | Procesar desde estructura de directorios |
| `radioLista` | Procesar desde CSV con rutas EVT |
| `radioDirectorio2` | Procesar recursivamente un directorio completo |

### Controles de modo de destino

| Control | Propósito |
|---|---|
| `radio_estacion_serial` | Guardar por subcarpetas de serial y usar serial como prefijo del archivo |

### Controles principales

| Control | Propósito |
|---|---|
| `Btn_directorio_datos` | Seleccionar origen de datos |
| `Btn_iniciar` | Iniciar procesamiento |
| `Btn_drive` | Cambiar directorio de trabajo |
| `Btn_salir` | Cerrar ventana |
| `cmbx_eventos` | Seleccionar subdirectorio principal, usualmente año |
| `cmbx_subdirectorios` | Filtrar subdirectorio o seleccionar Todos |
| `checkBox_verificacion` | Activar verificación gráfica |
| `checkBox_insercion` | Activar inserción en catálogo |
| `progressBar` | Mostrar progreso |
| `txt_ayuda` | Mostrar ayuda HTML |

## Manejo de Errores

| Situación | Comportamiento actual |
|---|---|
| EVT no legible | Registra incompatibilidad, intenta VM y continúa |
| CSV del día inexistente | No localiza ni inserta |
| Estación no configurada | Advierte y retorna eventos sin insertar |
| Evento no encontrado en catálogo | No inserta |
| Error gráfico | Captura excepción y continúa |
| Error inesperado por archivo | Genera fila de error y continúa el lote |

## Puntos Reproducibles para el Agente

Estos puntos deben revisarse directamente en el script antes de corregir:

1. El nombre nominal del MSEED se arma antes del ajuste temporal en `ajustar_tiempos_stream_con_catalogo()`. Puede causar reporte incoherente.
2. La verificación gráfica no guarda PNG aunque el mensaje al usuario dice que se guardó una imagen.
3. La confirmación de inserción aparece ligada a la verificación gráfica, no exclusivamente al checkbox de inserción.
4. En modo serial, el archivo real usa `SERIAL_AAAAMMDD_HHMMSS.mseed`, no `ESTACION_AAAAMMDD_HHMMSS.mseed`.
5. La ruta reportada en modo serial se arma con `archivo_mseed_nominal[4:]`, lo cual supone prefijo de cuatro caracteres.
6. El reporte siempre se llama `procesados_desde_csv.csv`, incluso si no se procesa desde CSV.
7. La raíz `rsa_sismologia` no se valida explícitamente.
8. La escritura MiniSEED no especifica codificación ni se hace de forma atómica.
9. Los diccionarios contienen claves duplicadas o vacías que deberían limpiarse.
10. Si no hay CSV del día, `mensaje_1` puede quedar vacío en lugar de registrar explícitamente `No insertado`.
11. La lista CSV permite rutas en cualquier celda, no solo en la primera columna.
12. El diccionario de directorios se usa para descripción de ruta, pero no para normalizar la estación real del EVT.

## Prioridades de Corrección Recomendadas

1. Corregir la incoherencia entre nombre nominal, nombre real del archivo insertado y ruta reportada.
2. Decidir si la verificación gráfica debe guardar realmente un PNG o solo mostrar la figura.
3. Hacer coherente la lógica entre `checkBox_verificacion`, confirmación del usuario y `checkBox_insercion`.
4. Revisar y documentar la lógica de inserción por serial.
5. Validar tempranamente la raíz del proyecto `rsa_sismologia`.
6. Mejorar el reporte de errores cuando no existe CSV del día o no se puede insertar.
7. Limpiar diccionarios de normalización.
8. Evaluar escritura MiniSEED con parámetros explícitos y/o escritura atómica.
9. Renombrar el reporte a un nombre más general si se desea evitar confusión.
10. Revisar si la tolerancia fija de 5 minutos debe ser configurable.

## Objetivo de la Corrección

El objetivo de las correcciones no debe ser cambiar la lógica general del programa, sino fortalecer el flujo actual de inserción de EVT para que:

- el reporte final coincida con los archivos realmente generados;
- el ajuste temporal no produzca nombres inconsistentes;
- la verificación gráfica sea coherente con lo que se informa al usuario;
- la inserción por serial sea clara y reproducible;
- los errores queden registrados de forma explícita;
- la aplicación sea más robusta frente a rutas inválidas, estaciones no configuradas y catálogos faltantes.

---

*Este documento describe el comportamiento real del script según su flujo de ejecución verificado y añade puntos reproducibles para que un agente pueda corregir el código sin reinterpretar el objetivo original del programa.*

## Actualizacion 2026-06-06

Cambios aplicados para coherencia entre codigo, interfaz y ayuda:

- El script valida tempranamente que exista la raiz `rsa_sismologia`.
- La ayuda HTML se carga primero desde `ayuda/ayuda_insercion_evt.html` y luego, por compatibilidad, desde `datos/ayuda_insercion_evt.html`.
- Se creo una copia versionable de la ayuda en `ayuda/`, porque `datos/` esta excluido por `.gitignore`.
- Se retiro del HTML un script externo inyectado por Kaspersky.
- La verificacion grafica queda documentada como visualizacion de figura Matplotlib; no guarda PNG.
- El mensaje de confirmacion ahora dice que se abrio la figura de verificacion, no que se guardo una imagen.
- La barra de progreso del UI inicia en `0`.
- Se deshabilitaron controles que existen en la interfaz pero no tienen accion operativa implementada: estacion por almacenamiento, coherencia metadatos/almacenamiento y guardado en un solo directorio.
- Se agregaron validaciones para evitar iniciar procesamiento sin seleccionar directorio fuente o lista CSV.

## Actualizacion 2026-06-06: Inventario para Directorio Completo

El modo `radioDirectorio2` ahora funciona como barrido con inventario previo:

- recorre recursivamente la carpeta seleccionada;
- detecta archivos `.evt`;
- calcula una huella `SHA1` por archivo;
- genera `inventario_evt_directorio_completo.csv` en el directorio de trabajo;
- marca duplicados exactos con `procesar=0`;
- procesa automaticamente solo la primera aparicion de cada archivo exacto.

Columnas principales del inventario:

| Columna | Uso |
|---|---|
| `procesar` | `1` para procesar, `0` para omitir |
| `ruta_evt` | Ruta completa del EVT |
| `nombre` | Nombre del archivo |
| `tamano_bytes` | Tamano del archivo |
| `mtime_iso` | Fecha de modificacion en formato legible |
| `sha1` | Huella del contenido para detectar duplicados exactos |
| `duplicado_de` | Ruta del primer archivo equivalente |
| `estacion_sugerida` | Codigo inferido desde nombres de carpeta cuando existe homologacion |
| `evt_legible` | `1` si ObsPy pudo leer el EVT; `0` si fallo |
| `requiere_vm` | `1` si probablemente requiere conversion externa/VM |
| `estacion_evt` | Estacion reportada en los metadatos EVT |
| `estacion_evt_homologada` | Estacion EVT normalizada por diccionario |
| `serial` | Numero serial del equipo cuando existe en metadatos |
| `inicio_evt` | Hora inicial leida desde el EVT |
| `clave_organizacion` | Clave priorizando serial, luego estacion EVT, luego ruta |
| `clave_evento` | `clave_organizacion + inicio_evt`, util para detectar repeticiones probables |
| `posible_repetido_de` | Primer EVT con la misma clave de evento, aunque no sea duplicado exacto |
| `error_lectura` | Error al leer EVT, si existe |

El modo `radioLista` reconoce inventarios con encabezado `ruta_evt` y respeta la columna `procesar`. Esto permite generar el inventario desde `Directorio 2`, revisarlo manualmente y luego cargarlo como lista.

El nombre del archivo EVT se conserva solo como dato descriptivo. No se usa como clave unica porque muchos equipos pueden generar nombres repetidos como `FF001.EVT`.

La prioridad de organizacion para inventario es:

1. serial del equipo;
2. estacion de metadatos EVT homologada;
3. estacion sugerida por ruta/carpeta;
4. `SIN_CLAVE`.

## Actualizacion 2026-06-06: Validacion para Directorio Ordenado

El modo `radioDirectorio1` valida la estructura ordenada antes de cargar los años disponibles.

La estructura esperada es:

```text
ESTACION/
  AAAA/
    AAAAMMDD/   fecha de bajada
      AAAAMMDD/ dia del EVT
        *.EVT
```

Al seleccionar la carpeta de estacion:

- se revisan años con formato `AAAA`;
- se revisan fechas de bajada con formato `AAAAMMDD`;
- se revisan dias EVT con formato `AAAAMMDD`;
- se cuentan los EVT encontrados;
- se registran advertencias solo por archivos `.EVT` ubicados fuera de la estructura esperada;
- la validacion se hace en memoria, sin generar reporte CSV;
- solo se cargan en `cmbx_eventos` los años si no existe ninguna advertencia o error.

Si no existe ningun año valido, o si existe cualquier anomalia, el programa muestra advertencia, vacia los combos y no permite continuar con el modo ordenado.

Esta validacion estricta aplica solo a `radioDirectorio1`. El modo `radioDirectorio2` no exige estructura de carpetas: genera inventario sobre cualquier arbol de directorios.

## Actualizacion 2026-06-07: Validacion estricta solo sobre EVT

La validacion de `radioDirectorio1` se hace exclusivamente sobre archivos con extension `.EVT`.
Cualquier otro archivo o extension dentro del arbol de la estacion se ignora.

Cada archivo EVT encontrado debe estar exactamente bajo esta forma:

```text
ESTACION/
  AAAA/
    AAAAMMDD/
      AAAAMMDD/
        archivo.EVT
```

Donde `AAAA` es el anio, `AAAAMMDD` es la fecha de bajada y el ultimo `AAAAMMDD` es el dia del EVT.
Si cualquier EVT aparece fuera de esa estructura, el programa muestra advertencia, limpia los combos de anios y subdirectorios, y no continua con el modo ordenado.

Esta validacion no genera reporte CSV. El inventario CSV queda reservado para `radioDirectorio2`, que acepta carpetas completas con organizacion libre.

## Actualizacion 2026-06-07: Mensaje de anomalias

Cuando `radioDirectorio1` encuentra errores en la estructura, el cuadro de advertencia muestra:

- la carpeta seleccionada;
- la estructura esperada: `AAAA/AAAAMMDD/AAAAMMDD/*.EVT` o `ESTACION/AAAA/AAAAMMDD/AAAAMMDD/*.EVT`;
- el numero de EVT encontrados;
- el numero de advertencias;
- las primeras anomalias con ruta completa y detalle.

Todas las anomalias tambien se imprimen en consola para poder ubicar archivos fuera de formato sin generar reporte CSV.

## Actualizacion 2026-06-07: Directorio DIA y origen EVT

Regla de diseno:

- `directorio_trabajo` apunta a `...\DIA\`, la estructura de datos sismica y catalogo de trabajo;
- `DIA` se usa para construir rutas de destino cuando un EVT ya fue procesado e identificado;
- `DIA` no participa en la validacion de la estructura de origen de los EVT;
- `Btn_directorio_datos` selecciona el origen de los EVT;
- los modos de origen EVT (`radioDirectorio1`, `radioDirectorio2`, `radioLista`) trabajan sobre las carpetas o listas seleccionadas por el usuario.

En `radioDirectorio1` se aceptan dos niveles de seleccion para fuentes ordenadas:

```text
FUENTE_ESTACION/
    AAAA/
    AAAAMMDD/
      AAAAMMDD/
        archivo.EVT

FUENTE_RAIZ/
  ESTACION/
    AAAA/
      AAAAMMDD/
        AAAAMMDD/
          archivo.EVT
```

El combo principal carga `AAAA` si se selecciono una carpeta de estacion, o `ESTACION/AAAA` si se selecciono una raiz que contiene estaciones.

## Actualizacion 2026-06-07: Retiro de validacion estricta en Directorio 1

Esta nota reemplaza las notas anteriores sobre validacion estricta de `radioDirectorio1`.

Comportamiento actual:

- `Btn_drive` conserva su funcion historica: escoger `...\DIA\`, la estructura de datos sismica y catalogo de trabajo;
- `Btn_directorio_datos` selecciona el origen de los EVT;
- `radioDirectorio1` no valida nombres ni niveles de carpetas;
- al seleccionar un origen, se cargan sus subdirectorios inmediatos en `cmbx_eventos`;
- si no hay subdirectorios, se carga la opcion `Todos`;
- al iniciar, se recolectan recursivamente todos los archivos `.EVT` bajo el directorio escogido;
- cualquier otra extension se ignora;
- no se bloquea la carga por anomalias de estructura.

El modo `radioDirectorio2` conserva el inventario CSV para carpetas completas o desordenadas.

## Actualizacion 2026-06-07: Restauracion del flujo de Iniciar y correccion 1980

Se restauro el flujo de `Iniciar` en `radioDirectorio1` para usar nuevamente `recolectar_evt()` de `metodos_rsa`.
El retiro de la validacion de estructura no debe cambiar el proceso de lectura, verificacion grafica ni decision de insercion que ya existia al presionar `Iniciar`.

La casilla `checkBox_verificacion` sigue controlando la visualizacion de la senial EVT para revisar si corresponde a evento o ruido.

Cuando ObsPy lee un EVT con `starttime` en 1980, el script corrige el dia antes de construir `archivo` y antes de buscar el CSV del catalogo:

1. usa primero una fecha `AAAAMMDD` encontrada en la ruta del EVT;
2. si no encuentra una fecha valida en la ruta, usa la fecha de modificacion del archivo EVT;
3. conserva la hora, minuto y segundo leidos del EVT.

Esto evita que el MiniSEED nominal y la busqueda del catalogo queden anclados en 1980 cuando el equipo se reseteo.
