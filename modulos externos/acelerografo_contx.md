# Contexto del Programa: `acelerografo.py`

## Alcance del Documento

Este documento describe el comportamiento actual de `acelerografo.py`. El objetivo es servir como contexto operativo y técnico para mantenimiento futuro, evitando confundir el flujo vigente con versiones históricas ya eliminadas.

## Identidad del Programa

`acelerografo.py` implementa una aplicación de escritorio PyQt5 para procesamiento sísmico de acelerógrafos digitales. Su función principal es unir archivos MiniSEED fragmentados de un mismo día, agrupados por estación, y generar dos productos:

- un MiniSEED diario unificado por estación;
- un gráfico `dayplot` PNG por estación.

El programa no convierte formato binario propietario a MiniSEED. Las funciones históricas de decodificación binaria fueron eliminadas del archivo para reducir tamaño y evitar dependencias innecesarias.

## Propósito

Resolver el caso operativo en que una estación digital genera múltiples archivos `.mseed` por día. El script busca esos fragmentos, valida que correspondan a la estación esperada, los ordena cronológicamente, los fusiona sin rellenar huecos artificialmente y produce archivos diarios listos para revisión.

## Flujo de Ejecución

### 1. Inicialización

Al iniciar:

- busca la raíz del proyecto `rsa_sismologia`;
- aborta con un error claro si no encuentra esa raíz;
- agrega `src/librerias` al `sys.path`;
- carga la interfaz `src/ui/acelerografos.ui`;
- conecta `Btn_Iniciar`, `Btn_drive`, `Btn_Salir` y `dateEdit`;
- define como ruta por defecto `G:/Mi unidad/DIA/`;
- define como carpeta fuente `G:/Mi unidad/DIA/Datos Estaciones/`;
- lee `datos/digitales.csv`;
- carga parámetros desde `parametros_estaciones()`;
- inicializa fecha, directorios y log.

### 2. Selección de Fecha y Directorios

`showDate()` actualiza:

- `self.date`;
- `self.archivo`, con formato `directorio_trabajo/AAAAMMDD000000`.

`seleccionar_drive()` permite cambiar la carpeta base `DIA`. Si no encuentra `Datos Estaciones`, solicita al usuario elegirla manualmente.

### 3. Procesamiento Principal (`Iniciar`)

El flujo actual es:

1. Crea directorios del día mediante `definir_dia()`.
2. Verifica que exista `self.directorio_binario`.
3. Calcula la fecha seleccionada en formato `AAAAMMDD`.
4. Lee y valida filas de `digitales.csv`.
5. Calcula la barra de progreso sobre estaciones habilitadas válidas.
6. Para cada estación habilitada:
   - valida índice y configuración;
   - construye la carpeta fuente;
   - busca archivos con patrón `XXXX_AAAAMMDD_HHMMSS*.mseed`;
   - valida que `XXXX` coincida con el código esperado de la estación;
   - ignora y registra archivos del día con código distinto;
   - lee cabeceras para ordenar por `stats.starttime`;
   - registra advertencias si algún archivo no tiene cabecera legible;
   - lee los archivos completos;
   - registra huecos antes de unir;
   - fusiona con `merge(method=1, fill_value=None)`;
   - ejecuta `split()` para conservar discontinuidades reales;
   - registra huecos después de unir;
   - escribe el MiniSEED diario;
   - genera PNG del canal configurado.

### 4. Cierre

`salir()` registra mensaje de cierre, cierra la ventana, procesa eventos pendientes y termina con `os._exit(0)`. Esto evita procesos colgados en Windows, pero al ejecutarlo desde Spyder puede provocar que Spyder indique que el kernel se reinició.

## Archivos de Configuración

### `datos/digitales.csv`

Archivo con cabecera. El programa omite la primera fila.

Columnas usadas:

| Columna | Uso |
|---|---|
| 0 | Carpeta de la estación dentro de `Datos Estaciones` |
| 1 | Índice de estación en `parametros_estaciones()` |

Validaciones actuales:

- fila con al menos dos columnas;
- carpeta no vacía;
- índice convertible a entero;
- índice dentro de rango para las listas de parámetros;
- estación habilitada en `HAB_CANAL`.

### `parametros_estaciones()`

Claves principales usadas:

| Clave | Uso |
|---|---|
| `HAB_CANAL` | Habilitación de estación |
| `NOMBRE` | Nombre descriptivo |
| `CODIGO` | Código de 4 caracteres esperado en nombres MSEED |
| `COMPONENTE` | Componente/canal a graficar |
| `CANAL` | Orientaciones de canal, por ejemplo `XYZ` o `TRV` |

## Productos Generados

### MiniSEED Diario

- Ubicación: `self.directorio_registros`.
- Nombre: `CODIGO_AAAAMMDD_000000.mseed`.
- Escritura: `format='MSEED'`, `encoding='STEIM1'`, `reclen=512`.
- Huecos: se preservan; no se rellenan con el último valor válido.

### PNG Dayplot

- Ubicación: `self.directorio`.
- Nombre: `CODIGO_AAAAMMDD_000000.png`.
- Tipo: `dayplot`.
- DPI: 200.
- Tamaño: 2400 x 1800.
- Línea: 0.2.
- Selección de canal: primero intenta buscar la traza por componente real (`stats.channel` termina en la orientación configurada); si no la encuentra, usa fallback por índice y lo registra.

## Logging

`agregar_mensaje()`:

- antepone timestamp `[HH:MM:SS]`;
- escribe en consola;
- escribe en el área de texto;
- mantiene auto-scroll;
- procesa eventos de Qt para mantener la interfaz responsiva.

## Dependencias

### Externas

| Módulo | Uso |
|---|---|
| `PyQt5` | Interfaz gráfica |
| `obspy` | Lectura, fusión, escritura y gráficos MiniSEED |
| `matplotlib` | Backend `Agg` para gráficos |

### Internas

| Módulo | Uso |
|---|---|
| `rsa_io` | `lectura_archivo` |
| `metodos_gestion` | `parametros_estaciones`, `obtener_directorios` |

## Funciones y Métodos Principales

| Nombre | Propósito |
|---|---|
| `extraer_hasta_directorio` | Ubica la raíz del proyecto |
| `validar_fila_digital` | Valida filas de `digitales.csv` |
| `filas_digitales_validas` | Construye lista de estaciones válidas |
| `actualizar_progreso` | Actualiza barra sobre estaciones habilitadas válidas |
| `registrar_huecos` | Registra huecos/solapes detectados por ObsPy |
| `seleccionar_traza_png` | Selecciona traza de PNG por componente real o fallback |
| `Iniciar` | Ejecuta procesamiento completo |
| `definir_dia` | Obtiene y crea directorios del día |
| `salir` | Cierra aplicación |

## Cambios Aplicados

- Renombrado final del script a `acelerografo.py`.
- Eliminadas versiones anteriores.
- Eliminado código muerto de conversión binaria.
- Eliminadas dependencias ya innecesarias (`numpy`, `rsa_dominio.obtenerTraza`).
- Validación temprana de raíz `rsa_sismologia`.
- Validación robusta de `digitales.csv`.
- Filtro por código de estación en nombres MSEED.
- Barra de progreso corregida.
- Registro de archivos con cabecera no legible.
- Registro de huecos antes y después de la unión.
- Cambio de `fill_value='latest'` a `fill_value=None`.
- Selección de PNG por componente real de canal.

## Limitaciones y Supuestos

- Los códigos de estación son de 4 caracteres.
- El procesamiento se ejecuta en el hilo principal de Qt.
- `os._exit(0)` puede reiniciar el kernel si se ejecuta desde Spyder.
- Si un archivo no tiene cabecera legible, se intenta leer al final de la lista, pero se registra advertencia.

## Estado Actual

El programa fue probado por el usuario y funciona correctamente con el flujo actualizado. El comportamiento actual evita mezclar estaciones, conserva discontinuidades reales y mantiene trazabilidad de advertencias relevantes.
