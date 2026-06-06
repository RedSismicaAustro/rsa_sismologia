# Contexto del Programa: acelerografo_v02.py

## Identidad del Programa

Este script implementa una aplicación de escritorio para procesamiento sísmico, especializada en **acelerógrafos digitales**. Su función principal es **unir archivos MiniSEED** fragmentados de un mismo día, agrupándolos por estación, y generar productos unificados (archivo MSEED diario + gráfico dayplot).

**Aclaración fundamental:** El script **no realiza conversión de formato binario propietario a MiniSEED**. Las funciones de decodificación que aparecen en el código (`nombre_mseed`, `conversion_mseed_digital`, `verificacion_archivo`, `lectura_archivo_digital`) son **código muerto** (no invocadas en ningún punto del flujo de ejecución). Se conservan únicamente como referencia histórica del algoritmo de decodificación original.

## Propósito

Resolver el problema de tener **múltiples archivos MSEED fragmentados por hora o evento** para una misma estación y un mismo día. El script los detecta, ordena cronológicamente, fusiona y genera un único archivo MSEED por estación/día, más un gráfico de visualización rápida.

## Arquitectura General

### Estilo de Aplicación
- Aplicación de escritorio con interfaz gráfica (PyQt5)
- Flujo controlado por eventos (botones, selección de fecha)
- Logs visibles en tiempo real dentro de la propia interfaz, con timestamp automático
- Barra de progreso para feedback visual durante el procesamiento

### Modo de Operación
- **Batch por día**: El usuario selecciona una fecha y el script procesa todas las estaciones habilitadas para ese día
- **Procesamiento por estación**: Cada estación se procesa de forma independiente, con su propio flujo de lectura, unión y escritura
- **Salida estructurada**: Los resultados se organizan en subdirectorios predefinidos dentro de la estructura del proyecto

## Flujo de Ejecución (Alto Nivel)

### 1. Inicio de la Aplicación (`__init__`)

- Se carga la interfaz desde el archivo `acelerografos.ui`
- Se conectan los botones (`Btn_Iniciar`, `Btn_drive`, `Btn_Salir`) a sus funciones
- Se establecen las rutas por defecto:
  - `directorio_trabajo`: `G:/Mi unidad/DIA/`
  - `directorio_binario`: `G:/Mi unidad/DIA/Datos Estaciones/`
- Se lee el archivo de configuración `digitales.csv` (mapea estaciones a carpetas). Este archivo **sí tiene cabecera**, por lo que el script omite intencionalmente la primera fila mediante `self.est_digitales_[1:]`.
- Se cargan los parámetros de estaciones mediante `parametros_estaciones()`
- Se extraen las listas de configuración: habilitación, nombres, códigos, ganancias, diezmado, factor multiplicador y canal a graficar
- Se muestra la fecha actual en el selector de fecha
- Se inicializa el área de mensajes con un log de inicio

### 2. Configuración Previa al Procesamiento

El usuario puede realizar dos acciones de configuración:

**Cambio de fecha** (`showDate`):
- Al seleccionar una fecha en el calendario (`dateEdit`)
- Se actualiza la variable `self.date`
- Se construye la ruta `self.archivo` como `directorio_trabajo + AAAAMMDD000000`
- Se registra un mensaje con la fecha seleccionada

**Cambio de directorios** (`seleccionar_drive`):
- Abre un diálogo para seleccionar la carpeta base `DIA`
- Actualiza `self.directorio_trabajo` y la etiqueta correspondiente
- Construye la ruta de `Datos Estaciones` como subdirectorio
- Si no existe, abre un segundo diálogo para seleccionar manualmente
- Actualiza la segunda etiqueta y registra los cambios

### 3. Procesamiento Principal (`Iniciar`)

Esta es la función central del script, ejecutada al presionar el botón "Iniciar".

#### Paso 1 – Preparación
- Llama a `definir_dia()` para crear la estructura de directorios del día
- Resetea la barra de progreso a 0
- Verifica que el directorio `self.directorio_binario` exista
- Si no existe, muestra un mensaje de advertencia y aborta

#### Paso 2 – Configuración del Día
- Obtiene la fecha seleccionada en formato `AAAAMMDD`
- Construye el nombre base del evento: `AAAAMMDD_000000`
- Define el patrón de búsqueda de archivos MSEED: `^([A-Za-z0-9]{4})_(\d{8})_(\d{6}).*\.mseed$`
  - Grupo 1: código de estación (4 caracteres alfanuméricos)
  - Grupo 2: fecha (AAAAMMDD)
  - Grupo 3: hora (HHMMSS)
- Calcula el total de estaciones habilitadas para la barra de progreso. **Punto a corregir:** el avance debe calcularse sobre las estaciones habilitadas efectivamente evaluadas/procesadas, no sobre el índice de todas las filas del CSV, para evitar porcentajes incoherentes cuando existan estaciones deshabilitadas.

#### Paso 3 – Iteración por Estación

Para cada estación definida en `digitales.csv`, omitiendo la cabecera:

**3.1 - Validación de la estación**
- Obtiene el número de estación desde la segunda columna del CSV
- Actualiza la barra de progreso según el índice
- Si la estación no está habilitada (`estacion_habilitada[num] != '1'`), la omite y registra el motivo

**3.2 - Localización de archivos**
- Obtiene el nombre de la carpeta desde la primera columna del CSV
- Obtiene el código de estación desde `self.codigo_estacion[num]`
- Construye la ruta completa a la carpeta de la estación
- Si la carpeta no existe, registra el error y continúa con la siguiente
- Escanea la carpeta en busca de archivos que coincidan con el patrón y la fecha seleccionada. **Corrección requerida:** también debe validar que el código de estación del archivo coincida con `codigo_estacion`, para evitar unir accidentalmente archivos de otra estación ubicados en la misma carpeta.

**3.3 - Unión de fragmentos**
- Si no hay archivos para el día, lo registra y continúa
- Clasifica los archivos en dos grupos:
  - **Con tiempo legible**: se lee la cabecera (`headonly=True`) y se extrae el tiempo de inicio
  - **Sin tiempo legible**: se colocan al final sin ordenar
- Ordena los archivos con tiempo cronológicamente
- Construye una lista ordenada (primero los ordenados, luego los no ordenados)
- Lee el contenido completo de todos los archivos en orden y los acumula en un `Stream` de ObsPy
- Fusiona las trazas con `merge(method=1, fill_value='latest')`. **Punto a revisar:** `fill_value='latest'` completa huecos con el último valor válido, lo cual puede crear tramos artificiales constantes en datos acelerográficos. Conviene evaluar si debe mantenerse, cambiarse por `fill_value=None`, o registrar los huecos con `get_gaps()` antes y después de la fusión.

**3.4 - Escritura del resultado**
- Construye la ruta de salida en `self.directorio_registros` con el formato: `CODIGO_AAAAMMDD_000000.mseed`
- Guarda el stream unificado en formato MiniSEED (codificación STEIM1, registro de 512 bytes)
- Registra mensaje de éxito o error

**3.5 - Generación del gráfico**
- Determina el canal a graficar desde `self.canal_[num_estacion]` (valor 1, 2 o 3)
- Convierte a índice de base 0 (resta 1)
- **Punto a revisar:** esta selección depende del orden interno de las trazas dentro del `Stream`. Si ese orden no está garantizado, debe seleccionarse la traza por identificación real de canal (`stats.channel`) y no solo por índice.
- Si el índice es válido dentro del stream, genera un gráfico dayplot:
  - Tipo: `dayplot` (visualización de día completo)
  - Resolución: 200 DPI
  - Dimensiones: 2400 × 1800 píxeles
  - Grosor de línea: 0.2
  - Guarda como PNG en `self.directorio` con nombre: `CODIGO_AAAAMMDD_000000.png`
- Registra mensaje de éxito o advertencia si el canal no existe

**3.6 - Actualización de UI**
- Incrementa el contador de estaciones procesadas
- Llama a `processEvents()` para mantener la interfaz responsiva

#### Paso 4 – Finalización
- Establece la barra de progreso en 100%
- Registra un resumen con la cantidad de estaciones procesadas

### 4. Cierre de la Aplicación (`salir`)

- Registra un mensaje de cierre
- Cierra la ventana principal
- Procesa eventos pendientes
- Termina el proceso inmediatamente con `os._exit(0)` (solución para Windows que fuerza la terminación de todos los hilos)

## Estructura de Directorios

### Entrada (Datos fuente)
directorio_trabajo/ (ej: G:/Mi unidad/DIA/)
│
└── Datos Estaciones/ # Directorio raíz de datos por estación
│
├── ESTACION_01/ # Nombre según primera columna de digitales.csv
│ ├── CODA_20240101_120000.mseed # Fragmento 1 del día
│ ├── CODA_20240101_121500.mseed # Fragmento 2 del día
│ ├── CODA_20240101_123000.mseed # Fragmento 3 del día
│ └── ... # Más fragmentos del mismo día
│
├── ESTACION_02/
│ ├── PETA_20240101_130000.mseed
│ ├── PETA_20240101_131500.mseed
│ └── ...
│
└── ...

### Salida (Resultados)
rsa_sismologia/ # Raíz del proyecto
└── src/
└── (estructura del proyecto)

directorio_trabajo/ (ej: G:/Mi unidad/DIA/)
│
├── registros/ # Directorio de salida (creado por definir_dia)
│ ├── CODA_20240101_000000.mseed # MSEED unificado del día
│ ├── PETA_20240101_000000.mseed
│ └── ...
│
└── (directorio_base según obtener_directorios)
├── CODA_20240101_000000.png # Gráficos dayplot
├── PETA_20240101_000000.png
└── ...

**Nota:** Los directorios exactos de salida (`self.directorio` y `self.directorio_registros`) son determinados por la función `obtener_directorios()` del módulo `metodos_gestion`, que construye rutas basadas en el archivo base.

## Archivos de Configuración

### `digitales.csv`
Ubicado en `datos/digitales.csv`. Archivo CSV **con cabecera** que mapea cada estación con el nombre de su carpeta. El script usa `self.est_digitales_[1:]`, por lo que la primera fila se considera encabezado y no se procesa como estación:

| Columna | Contenido | Ejemplo |
|---------|-----------|---------|
| 0 | Nombre de la carpeta donde se almacenan los MSEED de esa estación | `ESTACION_01` |
| 1 | Número de estación (índice que referencia a `parametros_estaciones()`) | `1` |

**Validaciones recomendadas para Codex:**
- Verificar que cada fila tenga al menos dos columnas.
- Verificar que la segunda columna pueda convertirse a entero.
- Verificar que el índice exista dentro de las listas retornadas por `parametros_estaciones()`.
- Registrar con claridad las filas inválidas y continuar con el resto del procesamiento cuando sea posible.

### Parámetros de Estaciones (`parametros_estaciones()`)
Función del módulo `metodos_gestion` que retorna un diccionario con listas indexadas por número de estación (0 a 15):

| Clave | Descripción | Ejemplo |
|-------|-------------|---------|
| `HAB_CANAL` | Lista de habilitación (`'0'` = deshabilitado, `'1'` = habilitado) | `['1','1','0',...]` |
| `NOMBRE` | Nombre completo de la estación | `['Estación A','Estación B',...]` |
| `CODIGO` | Código corto para nombres de archivo (4 caracteres) | `['CODA','PETA',...]` |
| `GANANCIA` | Ganancia del sensor | `['1.0','1.0',...]` |
| `DIEZMADO_PLT` | Factor de diezmado para gráficos | `['1','1',...]` |
| `FACTOR_MUL` | Factor de multiplicación para datos | `['1.0','1.0',...]` |
| `COMPONENTE` | Canal a graficar (`1`, `2` o `3`) | `['1','2','3',...]` |

## Productos Generados

### Archivo MSEED Unificado
- **Formato**: MiniSEED estándar
- **Codificación**: STEIM1
- **Registro**: 512 bytes
- **Nombre**: `CODIGO_AAAAMMDD_000000.mseed`
- **Ubicación**: `self.directorio_registros`
- **Contenido**: Unión de todos los fragmentos del día, ordenados cronológicamente y fusionados

### Gráfico Dayplot (PNG)
- **Tipo**: `dayplot` (representación visual de un día completo de datos)
- **Resolución**: 200 DPI
- **Dimensiones**: 2400 × 1800 píxeles
- **Grosor de línea**: 0.2
- **Canal**: El especificado en `COMPONENTE` para esa estación (1, 2 o 3)
- **Nombre**: `CODIGO_AAAAMMDD_000000.png`
- **Ubicación**: `self.directorio`

## Manejo de Situaciones Especiales

### Archivos sin cabecera legible
Si un archivo no permite leer su cabecera con `headonly=True` (posible corrupción o formato incorrecto), se coloca al final de la lista de procesamiento (`archivos_sin_tiempo`), intentando igualmente leer su contenido completo.

**Punto a revisar:** este comportamiento permite no abortar el procesamiento, pero introduce incertidumbre en el orden temporal. Codex debe evaluar si conviene mantenerlo, excluir esos archivos, registrarlos como advertencia fuerte o enviarlos a revisión manual.

### Estaciones deshabilitadas
Se omiten completamente, registrando un mensaje informativo, sin generar errores.

### Carpetas inexistentes
Si la carpeta de una estación configurada en `digitales.csv` no existe dentro de `Datos Estaciones/`, se registra el error y se continúa con la siguiente estación.

### Errores de lectura/escritura
Se capturan individualmente por archivo o estación, se registran en el log, y el procesamiento continúa con la siguiente estación.

También debe diferenciarse en los mensajes entre advertencias, errores recuperables y errores críticos.

### Directorio `Datos Estaciones` inexistente
Si al iniciar el procesamiento el directorio raíz no existe, se muestra un diálogo de advertencia y se aborta la operación.

## Interfaz de Usuario

### Controles principales
| Elemento | Acción |
|----------|--------|
| `Btn_Iniciar` | Inicia el procesamiento de unión de MSEEDs |
| `Btn_drive` | Abre diálogo para seleccionar directorios |
| `Btn_Salir` | Cierra la aplicación (con terminación forzosa) |
| `dateEdit` | Selector de fecha (calendario) |

### Retroalimentación visual
| Elemento | Propósito |
|----------|-----------|
| `area_texto` | Área de texto (solo lectura) que muestra logs con timestamp `[HH:MM:SS]` |
| `Lbl_directorio` | Muestra la ruta del directorio de trabajo actual |
| `Lbl_directorio_2` | Muestra la ruta de la carpeta `Datos Estaciones` |
| `progressBar` | Barra de progreso que avance según estaciones procesadas |

## Funciones del Script (Clasificadas por Uso)

### Funciones de Utilidad de Rutas
| Función | Propósito |
|---------|-----------|
| `extraer_hasta_directorio` | Recorta una ruta hasta un directorio específico (usa `rsa_sismologia` como referencia). Si no se encuentra esa raíz, Codex debe agregar una validación temprana para evitar rutas inválidas. |

### Métodos de Manejo de Mensajes
| Método | Propósito |
|--------|-----------|
| `agregar_mensaje` | Agrega un mensaje con timestamp al área de texto y a la consola; mantiene la UI responsiva |
| `limpiar_mensajes` | Limpia todo el contenido del área de texto |

### Métodos de Configuración de UI
| Método | Propósito |
|--------|-----------|
| `seleccionar_drive` | Abre diálogos para seleccionar carpetas base y de estaciones |
| `showDate` | Actualiza la fecha seleccionada y la ruta del archivo base |
| `definir_dia` | Obtiene los directorios desde `obtener_directorios()` y los crea si no existen |

### Método Principal
| Método | Propósito |
|--------|-----------|
| `Iniciar` | **Función principal**: ejecuta todo el flujo de unión de MSEEDs por día |

### Método de Cierre
| Método | Propósito |
|--------|-----------|
| `salir` | Cierra la aplicación con terminación forzosa del proceso (solución para Windows) |

### Código Muerto (No Utilizado)
Las siguientes funciones existen en el archivo pero **no son llamadas en ningún punto**:

| Función | Propósito original |
|---------|---------------------|
| `nombre_mseed` | Generaba nombre de archivo MSEED a partir de prefijo y timestamp |
| `conversion_mseed_digital` | Convertía datos numpy a formato MSEED para 3 canales |
| `verificacion_archivo` | Extraía timestamp de los últimos bytes de un archivo binario |
| `lectura_archivo_digital` | Decodificaba archivo binario propietario a arrays numpy |

Estas funciones se conservan como **referencia histórica** del algoritmo de decodificación del formato binario original.

## Dependencias

### Módulos Externos
| Módulo | Uso |
|--------|-----|
| `PyQt5` | Interfaz gráfica (widgets, eventos, diálogos) |
| `obspy` | Lectura/escritura de MSEED, merge de streams, generación de dayplots |
| `numpy` | Procesamiento de arrays (solo en código muerto) |
| `matplotlib` | Generación de gráficos (modo `Agg`, sin backend gráfico) |

### Módulos Internos del Proyecto
| Módulo | Funciones Utilizadas |
|--------|---------------------|
| `rsa_io` | `lectura_archivo` (lectura de archivos CSV) |
| `rsa_dominio` | `obtenerTraza` (solo en código muerto) |
| `metodos_gestion` | `parametros_estaciones`, `obtener_directorios` |

## Logging y Trazabilidad

El método `agregar_mensaje()` proporciona:

- **Timestamp automático**: Formato `[HH:MM:SS]` al inicio de cada mensaje
- **Salida dual**: Escribe tanto en consola (`print`) como en `area_texto` de la UI
- **Auto-scroll**: Desplaza automáticamente el cursor al final del área de texto
- **UI responsiva**: Llama a `QCoreApplication.processEvents()` para mantener la interfaz fluida

## Escenario de Uso Típico

1. El operador sísmico abre la aplicación
2. Verifica que los directorios de datos estén correctos (visualmente en las etiquetas)
3. Si es necesario, usa "Seleccionar Drive" para cambiar las rutas
4. Selecciona el día que desea procesar en el calendario
5. Presiona "Iniciar"
6. La aplicación:
   - Lee `digitales.csv` para conocer la estructura de carpetas
   - Recorre todas las estaciones configuradas
   - Para cada estación habilitada, busca sus fragmentos MSEED en `Datos Estaciones/ESTACION_X/`
   - Ordena los fragmentos cronológicamente (usando solo cabeceras para velocidad)
   - Une todos los fragmentos en un solo Stream
   - Guarda el resultado como `CODIGO_AAAAMMDD_000000.mseed` en `registros/`
   - Genera un gráfico dayplot del canal principal como PNG
7. Muestra un log detallado del proceso con timestamps
8. Al finalizar, muestra un resumen de estaciones procesadas
9. Los archivos unificados están listos para análisis en otros programas

## Notas de Implementación

- **Modo Agg de Matplotlib**: `matplotlib.use('Agg')` permite generar gráficos sin necesidad de entorno gráfico (útil para servidores o ejecución remota)
- **Headonly**: La lectura con `headonly=True` es una optimización para ordenar archivos sin cargar todos los datos
- **Merge method=1**: Utiliza el método de ObsPy para fusionar trazas que se solapan o son contiguas
- **Fill_value='latest'**: En caso de huecos en los datos, completa con el último valor válido. **Debe revisarse técnicamente**, porque puede crear segmentos artificiales constantes en la señal.
- **Cierre forzoso**: `os._exit(0)` asegura la terminación completa del proceso en Windows, evitando hilos colgados. **Debe evaluarse** si puede reemplazarse por un cierre más limpio de Qt o mantenerse documentado como solución deliberada.
- **Patrón de nombres estricto**: Solo procesa archivos que cumplen el patrón `XXXX_AAAAMMDD_HHMMSS.mseed`, pero debe agregarse validación explícita para que `XXXX` coincida con el código de estación esperado.



## Puntos Críticos Detectados para Corrección con Codex

Los siguientes puntos no cambian la identidad del programa, pero deben ser considerados al corregir el script:

1. **`digitales.csv` tiene cabecera**: el uso de `self.est_digitales_[1:]` es correcto y debe mantenerse, salvo que se cambie la forma de lectura del CSV.
2. **Validar código de estación**: además de verificar la fecha del archivo, el script debe verificar que el código de cuatro caracteres del nombre del archivo coincida con `codigo_estacion`.
3. **Revisar `fill_value='latest'`**: puede generar datos artificiales en huecos. Se recomienda registrar huecos con `get_gaps()` y decidir si se conserva o se cambia por `fill_value=None`.
4. **Canal del PNG**: actualmente se selecciona por índice dentro del `Stream`; si el orden de trazas no está garantizado, debe seleccionarse por `stats.channel`.
5. **Validar filas e índices**: `digitales.csv` debe validarse para evitar filas incompletas, valores no enteros o índices fuera de rango.
6. **Barra de progreso**: el cálculo debe basarse en estaciones habilitadas efectivamente evaluadas/procesadas.
7. **Raíz del proyecto**: si no se encuentra `rsa_sismologia`, el programa debe detenerse con un mensaje claro antes de construir rutas inválidas.
8. **Código muerto**: las funciones de conversión binaria pueden mantenerse como referencia, pero conviene aislarlas o moverlas para evitar confusión y dependencias innecesarias.
9. **Cierre forzado**: `os._exit(0)` debe revisarse. Si se mantiene, debe documentarse como decisión deliberada para evitar procesos colgados en Windows.

## Objetivo de las Correcciones

El objetivo no es reescribir completamente el programa, sino fortalecer el flujo actual de unión diaria de archivos MiniSEED para que:

- no mezcle accidentalmente estaciones;
- no oculte huecos de datos sin trazabilidad;
- no genere gráficos del canal equivocado;
- no falle por errores simples en `digitales.csv`;
- mantenga logs más claros para operación y depuración;
- conserve la lógica actual de procesamiento por día y por estación.

---

*Este documento describe el comportamiento real del script según su flujo de ejecución verificado línea por línea. Las funciones de decodificación de binario no están activas y se conservan solo como referencia histórica.*