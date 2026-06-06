# Contexto del Programa: `automatico V2.py`

## Alcance del documento

Este documento describe el comportamiento real del script `automatico V2.py` y está pensado para servir como contexto de trabajo para cualquier agente de revisión, refactorización o corrección de código.

El objetivo del contexto no es idealizar el funcionamiento del programa, sino dejar claro qué hace actualmente, qué supuestos contiene, qué partes están verificadas en el flujo real y qué puntos requieren corrección o revisión técnica.

## Identidad del Programa

Este script implementa una aplicación de escritorio para procesamiento sísmico, especializada en **registro continuo analógico/digital de 16 canales**. Su función principal es leer archivos binarios de un formato propietario generado por un sistema de adquisición sísmica, convertirlos al estándar MiniSEED y generar productos organizados por día y canal.

El script está diseñado para operar en un entorno donde:

- Los datos crudos pueden estar disponibles en una unidad de red `R:`.
- El procesamiento se realiza por defecto en `G:/Mi unidad/DIA/`, aunque el usuario puede seleccionar otro directorio de trabajo.
- Se requiere capacidad de reanudación mediante un archivo de control llamado `analogico.csv`.
- Los productos principales son archivos MiniSEED por canal y gráficos tipo `dayplot`.

## Propósito Principal

Procesar **registros sísmicos continuos** desde archivos binarios crudos de formato propietario, convertirlos a MiniSEED y organizarlos por día y canal para posterior análisis o revisión con herramientas sismológicas.

## Hallazgos principales de comparación entre script y contexto

La comparación entre el script y el contexto original muestra que el documento estaba bien encaminado en la descripción general, pero requería varios ajustes importantes:

1. El contexto original indicaba que el archivo terminado en `235959` se renombra a `000000` del día siguiente. Eso era incorrecto. El script lo renombra a `000000` del mismo día representado en el nombre del archivo, y este comportamiento debe documentarse como la regla actual del programa.
2. El contexto indicaba que, si no hay archivos para el día, se crea una entrada ficticia. En realidad, eso solo ocurre si la unidad `R:` no existe y se produce `FileNotFoundError`. Si `R:` existe pero no hay archivos del día, la lista queda vacía.
3. La reanudación existe, pero es más limitada de lo que parecía. `analogico.csv` guarda un único estado y `Leer_binario_comun()` solo reanuda si el archivo guardado coincide exactamente con el archivo binario actual.
4. La corrección de línea base no se conserva de un archivo a otro. El offset se calcula dentro de cada ejecución de `Leer_binario_comun()` y se reinicia en cada archivo procesado.
5. La variable `huecos` siempre queda en `0`; el script no calcula realmente segundos faltantes.
6. La validación de MSEEDs existentes puede marcar como inconsistente un archivo válido si `contador_s` vale `0` en `analogico.csv`.
7. La función `eliminar_mseeds_del_dia()` solo elimina archivos cuyo código inicial tiene exactamente cuatro caracteres. Esto puede fallar si los códigos de canal/estación tienen tres caracteres, como `EHZ`, `EHN` o `EHE`.
8. La escritura atómica solo se aplica en `unir_mseed()`, no necesariamente en la conversión inicial realizada por `conversion_mseed()`.
9. `Abrir_archivo__()` es una versión alternativa o histórica, muy similar a `Abrir_archivo()`, pero no está conectada a la interfaz.
10. La detección de la raíz del proyecto `rsa_sismologia` no tiene validación temprana. Si no se encuentra esa carpeta, se pueden construir rutas inválidas.
11. El programa usa `processEvents()` para mantener viva la interfaz, pero el procesamiento sigue ejecutándose en el hilo principal de Qt.

## Flujo de Ejecución Verificado

### Fase 1: Inicialización de la Aplicación

Al iniciar el programa:

1. Se determina la ubicación del proyecto buscando el directorio `rsa_sismologia` en la ruta del script.
2. Se configuran las rutas `src/librerias` y `datos` dentro de `sys.path`.
3. Se importa código interno desde:
   - `rsa_io`
   - `rsa_utilidades`
   - `metodos_gestion`
4. Se configura Matplotlib en modo `Agg` y se desactiva el modo interactivo con `plt.ioff()`.
5. Se carga la interfaz gráfica desde `automatico.ui`.
6. Se conectan los controles principales:
   - `btn_abrir` → `Abrir_archivo`
   - `Btn_Salir` → `Salir_`
   - `Btn_drive` → `seleccionar_drive`
   - `dateEdit.dateChanged` → `showDate`
7. Se cargan los parámetros de estaciones mediante `parametros_estaciones()`.
8. Se inicializan buffers internos de 16 canales.
9. Se establece como directorio de trabajo por defecto:

```text
G:/Mi unidad/DIA/
```

10. Se configura la fecha actual en el selector de fecha.
11. Se construye `self.archivo` con el formato:

```text
G:/Mi unidad/DIA/AAAAMMDD000000
```

12. Se verifica si existe la unidad `R:`.
    - Si existe, se marca `self.bandera_drive_r = 1`.
    - Si no existe, se muestra una advertencia y se marca `self.bandera_drive_r = 0`.

## Punto a corregir: validación de raíz del proyecto

El script depende de encontrar `rsa_sismologia` en la ruta del archivo. Si no se encuentra, `ruta_proyecto` queda como cadena vacía y aun así se construyen rutas para `src/librerias`, `datos` y `src/ui/automatico.ui`.

Un agente debe agregar una validación temprana. Si no se encuentra la raíz del proyecto, el programa debe abortar con un mensaje claro.

## Fase 2: Selección de Fecha y Directorio

### Selección de fecha (`showDate`)

Cuando el usuario cambia la fecha en `dateEdit`:

- Se actualiza `self.date`.
- Se actualiza `self.dia` en formato `AAAAMMDD`.
- Se construye `self.archivo` como:

```text
self.directorio_trabajo + self.dia + '000000'
```

Ejemplo:

```text
G:/Mi unidad/DIA/20260115000000
```

### Selección de directorio (`seleccionar_drive`)

El botón `Btn_drive` permite seleccionar un nuevo directorio de trabajo.

El script:

- Abre un diálogo de selección de carpeta.
- Asegura que la ruta termine en `/`.
- Actualiza `self.directorio_trabajo`.
- Muestra la ruta en `Lbl_Mensajes`.
- Llama a `showDate(self.date)` para reconstruir `self.archivo`.

## Fase 3: Procesamiento Principal (`Abrir_archivo`)

`Abrir_archivo()` es la función principal conectada al botón `btn_abrir`.

### Paso 3.1: Escaneo y copia desde `R:`

El script intenta listar la unidad:

```text
R:
```

Luego filtra archivos que cumplan estas condiciones:

- El nombre sin extensión tiene exactamente 12 dígitos.
- No tiene extensión.
- El nombre representa `AAMMDDhhmmss`.
- Los primeros seis dígitos coinciden con el día seleccionado en formato `AAMMDD`.

La condición real del script es equivalente a:

```python
re.fullmatch(r'\d{12}', Path(f).stem) and Path(f).suffix == ''
```

Para cada archivo encontrado:

- Construye el nombre de destino agregando el prefijo `20`.
- Copia el archivo desde `R:/archivo` hacia el directorio de trabajo.
- Agrega el nombre convertido a `lista_archivos`.

Ejemplo:

```text
R:/260115120000
G:/Mi unidad/DIA/20260115120000
```

## Punto crítico: tratamiento de archivos terminados en `235959`

El contexto original decía que el archivo `AAMMDD235959` se renombraba a `AAMMDD000000` del día siguiente. Eso no coincide con el script.

El script hace lo siguiente:

```text
AAMMDD235959 → 20AAMMDD000000
```

Es decir, cambia la hora a `000000`, pero mantiene el mismo día del nombre original.

Ejemplo real según el código:

```text
260115235959 → 20260115000000
```

No se convierte a:

```text
20260116000000
```

Este comportamiento debe documentarse como la regla actual del programa: el archivo `AAMMDD235959` se considera un registro correspondiente al mismo día `AAMMDD`, pero identificado operativamente como iniciado a `000000`. No se debe afirmar que pasa al día siguiente. Solo debe revisarse si, desde el funcionamiento real del registrador, ese archivo representara datos iniciados verdaderamente a las `23:59:59`; en ese caso sí habría un problema conceptual de tiempo.

## Punto crítico: caso en que `R:` existe pero no hay archivos del día

El contexto original indicaba que, si no hay archivos, se crea una entrada ficticia con `AAAAMMDD000000`.

El script solo agrega esa entrada ficticia en el bloque `except FileNotFoundError`, es decir, cuando no existe la unidad `R:`.

Si `R:` sí existe, pero no contiene archivos del día seleccionado, `lista_archivos` queda vacía y el flujo cae al mensaje final:

```text
No hay registros para ese día..
Archivo buscado: AAAAMMDD000000
```

Por tanto, la frase correcta es:

- Si `R:` no existe, se agrega una entrada basada en `AAAAMMDD000000`.
- Si `R:` existe pero no hay archivos válidos del día, no se agrega entrada ficticia.

## Paso 3.2: Inicialización del día

Luego de construir `lista_archivos`, el script:

1. Ordena la lista.
2. Llama a `inicializar_()`.
3. Define `self.archivo` usando el primer archivo de la lista si existe.
4. Llama a `definir_dia()`.

Si hay archivos:

```python
self.archivo = self.directorio_trabajo + lista_archivos[0]
```

Si no hay archivos:

```python
self.archivo = self.directorio_trabajo + self.dia + '000000'
```

## Fase 4: Control de día y reanudación

### `verificar_o_resetear_por_dia()`

Esta función compara el día actual de procesamiento con el día guardado en `analogico.csv`.

Usa:

- `extraer_id_evento_desde_ruta()` para obtener un identificador `AAAAMMDDhhmmss`.
- `dia_de_id_evento()` para obtener solo `AAAAMMDD`.
- `lectura_ultima_fila_analogico()` para obtener el último estado guardado.

Si el día guardado y el día actual son distintos:

1. Escribe una fila de reinicio en `analogico.csv`:

```text
Archivo,puntero,segundo_m,contador_s
archivo_base,0,00000,0
```

2. Llama a `eliminar_mseeds_del_dia()`.
3. Retorna la fila reseteada.

Si no hay fila previa útil, inicializa `analogico.csv` con el archivo base actual.

## Punto crítico: `analogico.csv` es un control único

`analogico.csv` guarda una sola fila de estado. No guarda un estado separado por canal ni por archivo.

Además, dentro de `Leer_binario_comun()` la reanudación solo se acepta si el identificador guardado en `analogico.csv` coincide exactamente con el identificador del archivo binario actual.

Por tanto, la reanudación existe, pero no debe describirse como una reanudación general para cualquier interrupción del día. Es una reanudación condicionada al archivo exacto que se está procesando.

## Punto crítico: eliminación de MSEEDs del día

La función `eliminar_mseeds_del_dia()` usa el patrón:

```regex
^[A-Za-z0-9]{4}_AAAAMMDD_\d{6}.*\.mseed$
```

Esto exige que el código inicial tenga exactamente cuatro caracteres.

Sin embargo, el propio contexto y varios sistemas sísmicos pueden usar códigos de tres caracteres, como:

```text
EHZ
EHN
EHE
```

Si `self.nombre_canal[i]` tiene tres caracteres, esta función no eliminará esos MSEEDs aunque pertenezcan al día actual.

Un agente debe revisar si el patrón debe permitir longitudes variables, por ejemplo:

```regex
^[A-Za-z0-9]+_AAAAMMDD_\d{6}.*\.mseed$
```

También debe confirmarse si los nombres reales de canal en este proyecto son de tres, cuatro o más caracteres.

## Fase 5: Validación de MSEEDs existentes

Antes de leer el binario, `Abrir_archivo()` intenta validar los MSEEDs ya existentes para los canales habilitados.

Para cada canal habilitado:

1. Construye el nombre esperado del MiniSEED.
2. Lee el archivo si existe.
3. Verifica:
   - tiempo inicial (`t0_real`) contra `t0_esperado`;
   - tasa de muestreo esperada de 64 Hz;
   - número total de muestras contra `contador_s * 64`.
4. Si no cumple, lo mueve a `_inconsistentes/`.

## Punto crítico: validación contra `contador_s`

La validación usa:

```python
npts_esp = int(contador_s) * int(fs_esperada)
```

Si `contador_s` vale `0`, cualquier MSEED existente con datos será marcado como inconsistente.

Esto puede ser correcto si se está reiniciando el día, pero puede ser peligroso si el archivo MSEED es válido y el archivo de control está desactualizado, incompleto o recién reseteado.

Un agente debe revisar si esta validación debe considerar casos especiales:

- `contador_s == 0`;
- `analogico.csv` recién creado;
- MSEEDs existentes generados en una ejecución anterior;
- archivos válidos que no deberían moverse automáticamente.

## Fase 6: Lectura del binario (`Leer_binario_comun`)

`Leer_binario_comun()` es la función nuclear de decodificación.

### Parámetros

```python
Leer_binario_comun(directorio_trabajo, archivo_binario, barra_progreso, Lbl_Mensajes)
```

### Formato binario asumido

El formato propietario se asume fijo:

| Elemento | Valor |
|---|---:|
| Bytes por segundo | 2077 |
| Número de canales | 16 |
| Muestras por segundo | 64 |
| Marca fija | `\x08\x00\x05\x00` |
| Número de segundo | 5 bytes ASCII |
| Cabecera fija | 20 bytes |
| Cuerpo de datos | 2048 bytes |
| Tipo de dato | entero little-endian de 16 bits con signo |
| Forma de datos | 64 muestras × 16 canales |

La relación de tamaño es:

```text
4 bytes marca + 5 bytes segundo + 20 bytes cabecera + 2048 bytes datos = 2077 bytes por segundo
```

### Proceso real

La función:

1. Define constantes del formato.
2. Crea una lista de 16 canales vacíos.
3. Usa `obtener_directorios(archivo_binario)` para ubicar rutas asociadas.
4. Si `archivo_estaciones` no existe o está vacío:
   - abre el binario;
   - llama a `loc_cabecera()`;
   - escribe la configuración en `archivo_estaciones`.
5. Lee `analogico.csv`.
6. Decide si reanuda desde el puntero guardado o empieza desde la cabecera localizada.
7. Si el puntero no está alineado con la marca fija, busca hacia adelante.
8. Estima segundos restantes con:

```python
segundos_estimados = bytes_restantes // bytes_por_segundo
```

9. Lee segundo por segundo:
   - valida marca fija;
   - valida segundo ASCII de 5 dígitos;
   - valida cabecera de 20 bytes;
   - lee el cuerpo de 2048 bytes;
   - convierte a `np.frombuffer(..., dtype='<i2')`;
   - reorganiza a `(64, 16)`;
   - resta offset;
   - acumula muestras por canal.
10. Actualiza `analogico.csv` al final con:

```text
Archivo,puntero,segundo_m,contador_s
```

11. Retorna:

```python
return canal, huecos
```

## Punto crítico: `huecos` no se calcula realmente

Dentro de `Leer_binario_comun()` se define:

```python
huecos = 0
```

Pero no existe una lógica real que incremente esa variable cuando faltan segundos, hay saltos o hay pérdida de sincronización.

Por tanto, el mensaje:

```text
Segundos faltantes: 0
```

no debe interpretarse como una verificación real de continuidad temporal.

Un agente debe implementar o documentar correctamente el cálculo de huecos si ese dato se va a usar como criterio técnico.

## Punto crítico: corrección de línea base

El script calcula un offset por canal a partir del primer bloque válido leído dentro de cada llamada a `Leer_binario_comun()`:

```python
offset = datos.mean(axis=0).astype(np.int32)
```

Ese offset se guarda en la variable local `linea`, no en un archivo ni en un atributo persistente.

Por tanto:

- El offset se recalcula en cada archivo binario procesado.
- No se conserva entre archivos.
- No queda trazabilidad del valor de offset usado.
- El contexto no debe decir que las lecturas posteriores del día usan un offset guardado, porque eso no ocurre en el script actual.

Un agente debe revisar si este comportamiento es técnicamente correcto para el procesamiento esperado.

## Punto crítico: función `archivo_vacio()` sin uso

Dentro de `Leer_binario_comun()` se define `archivo_vacio()`, pero no se usa en el flujo actual.

No afecta la ejecución, pero debe considerarse código muerto local o residuo de una versión anterior.

## Fase 7: Conversión a MiniSEED (`Btn_Mseed`)

Después de leer el binario, `Abrir_archivo()` llama a `Btn_Mseed()`.

`Btn_Mseed()`:

1. Convierte `self.canal` a arreglo NumPy:

```python
self.canal_np = np.asarray(self.canal)
```

2. Muestra mensaje de grabación.
3. Intenta leer `self.estaciones`.
4. Si la lectura de estaciones es exitosa, actualiza:

```python
self.hab_canal[i]
self.nombre_canal[i]
```

5. Llama a:

```python
conversion_mseed(self.canal_np, self.hab_canal, self.nombre_canal, self.fecha_, self.directorio_registros)
```

6. Guarda el resultado en:

```python
self.trCanal
```

## Punto a revisar: escritura inicial no necesariamente atómica

El contexto original hablaba de escritura atómica de MSEEDs. En el script, la escritura atómica está implementada explícitamente en `escribir_atomico_mseed()` y se usa dentro de `unir_mseed()`.

La conversión inicial depende de la función externa `conversion_mseed()`. Con este script solamente no se puede asegurar que esa escritura inicial sea atómica.

Por tanto, el contexto debe decir:

- La unión usa escritura atómica.
- La conversión inicial debe revisarse en `rsa_io.conversion_mseed()` para confirmar si también es segura.

## Fase 8: Unión de MSEEDs (`unir_mseed`)

Cuando hay más de un archivo binario para el día, el script une los MSEEDs de los archivos adicionales contra el primer archivo de `lista_archivos`.

Para cada archivo adicional:

1. Obtiene la hora del archivo base y del archivo adicional usando `obtencion_hora()`.
2. Construye los nombres MiniSEED por canal.
3. Lee el MSEED base con `obspy.read()`.
4. Lee el MSEED adicional con `obspy.read()`.
5. Suma ambos `Stream`:

```python
st1 += st2
```

6. Fusiona con:

```python
st1.merge(method=0, fill_value='latest')
```

7. Escribe el resultado mediante `escribir_atomico_mseed()`.
8. Elimina el MSEED adicional.

## Punto crítico: uso de `fill_value='latest'`

El uso de:

```python
fill_value='latest'
```

puede crear tramos artificiales constantes cuando existan huecos entre segmentos.

Para datos sísmicos o acelerográficos, esto debe revisarse con cuidado. Un agente debe evaluar si conviene:

- mantenerlo y documentarlo;
- cambiarlo por `fill_value=None`;
- registrar huecos con `get_gaps()` antes y después del `merge`;
- impedir que se rellenen artificialmente vacíos de adquisición.

## Fase 9: Generación de gráficos (`imprimir_png`)

Al finalizar el procesamiento, si `lista_archivos` no está vacía:

1. Se toma el primer archivo como base.
2. Se actualiza `self.fecha_`.
3. Se carga `self.trCanal` con:

```python
self.trCanal = leer_mseed(self.archivo, 0)
```

4. Se llama a `imprimir_png()`.

`imprimir_png()` recorre los 16 canales y, para cada canal habilitado, genera un gráfico tipo `dayplot`:

```python
self.trCanal[i].plot(
    type='dayplot',
    outfile=nombrepng,
    dpi=200,
    size=(2400,1800),
    linewidth=0.2,
    show=False
)
```

El nombre del PNG se construye como:

```text
CODIGO_AAAAMMDD_HHMMSS.png
```

## Punto a revisar: dependencia de `leer_mseed()`

El script no muestra la implementación de `leer_mseed()`. Por tanto, el contexto no debe afirmar con certeza cómo organiza internamente `self.trCanal`.

Un agente debe revisar `rsa_io.leer_mseed()` para confirmar:

- si retorna 16 trazas en el mismo orden de canales;
- si omite canales deshabilitados;
- si conserva índices vacíos;
- si puede provocar errores cuando `imprimir_png()` accede a `self.trCanal[i]`.

## Estructura de Directorios

La estructura general esperada es:

```text
rsa_sismologia/
├── src/
│   ├── librerias/
│   │   ├── rsa_io.py
│   │   ├── rsa_utilidades.py
│   │   └── metodos_gestion.py
│   └── ui/
│       └── automatico.ui
├── datos/
└── G:/Mi unidad/DIA/        # Directorio de trabajo por defecto
    ├── AAAAMMDDhhmmss      # Archivo binario copiado desde R: o seleccionado manualmente
    ├── analogico.csv       # Control de progreso
    ├── registros/          # Archivos MiniSEED generados
    │   ├── CODIGO_20yymmdd_HHMMSS.mseed
    │   └── _inconsistentes/
    ├── reportes/
    ├── acelerogramas/
    └── fastHypo/
```

El archivo `estaciones.csv` no necesariamente está directamente en la raíz del directorio de trabajo. Su ubicación exacta depende de `obtener_directorios()` y de la clave `archivo_estaciones`.

## Archivos de Control

### `analogico.csv`

Permite guardar el estado de procesamiento.

| Campo | Descripción |
|---|---|
| `Archivo` | Identificador o ruta del archivo binario procesado |
| `puntero` | Posición en bytes dentro del archivo binario |
| `segundo_m` | Último número de segundo leído, en 5 dígitos ASCII |
| `contador_s` | Conteo acumulado de segundos procesados para el estado actual |

Limitaciones:

- Solo guarda una fila de estado.
- No guarda estado por canal.
- No guarda estado por múltiples archivos del mismo día.
- La reanudación exacta depende de que el archivo actual coincida con el identificador guardado.

### `estaciones.csv` / `archivo_estaciones`

Se genera desde la cabecera del binario mediante `loc_cabecera()` cuando no existe o está vacío.

En `definir_dia()`, si el archivo de estaciones existe, el script intenta eliminarlo. Luego `Leer_binario_comun()` puede regenerarlo desde el binario.

El contexto debe usar el nombre conceptual `archivo_estaciones`, porque la ruta exacta la define `obtener_directorios()`.

## Interfaz de Usuario

### Controles principales

| Elemento | Acción |
|---|---|
| `btn_abrir` | Inicia el procesamiento completo |
| `Btn_drive` | Permite seleccionar el directorio de trabajo |
| `Btn_Salir` | Cierra la aplicación |
| `dateEdit` | Selector de fecha |
| `Lbl_Mensajes` | Área de mensajes/logs |
| `progressBar` | Barra de progreso durante lectura del binario |

El script no actualiza etiquetas específicas de directorio como tal; muestra rutas principalmente en `Lbl_Mensajes`.

## Funciones del Script

### Utilidad general

| Función | Propósito |
|---|---|
| `extraer_hasta_directorio` | Recorta una ruta hasta el directorio raíz indicado |
| `mensaje_lbl` | Escribe mensajes en `Lbl_Mensajes` |
| `mostrar_advertencia` | Muestra advertencia si `R:` no está disponible |

### Control y validación

| Función | Propósito |
|---|---|
| `extraer_id_evento_desde_ruta` | Extrae `AAAAMMDDhhmmss` desde una ruta o nombre |
| `dia_de_id_evento` | Extrae `AAAAMMDD` desde un identificador de evento |
| `lectura_ultima_fila_analogico` | Lee la última fila válida de `analogico.csv` |
| `escribir_analogico` | Escribe cabecera y una fila en `analogico.csv` |
| `eliminar_mseeds_del_dia` | Elimina MSEEDs del día según patrón de nombre |
| `verificar_o_resetear_por_dia` | Compara día actual contra día guardado y reinicia si corresponde |
| `escribir_atomico_mseed` | Escribe un Stream MiniSEED usando archivo temporal y `os.replace()` |
| `verificar_mseed_contra_analogico` | Verifica MSEED existente contra tiempo inicial, frecuencia y número de muestras |

### Decodificación

| Función | Propósito |
|---|---|
| `Leer_binario_comun` | Decodifica el binario propietario, maneja reanudación y retorna 16 canales como listas |

### Métodos de `MyApp`

| Método | Propósito |
|---|---|
| `__init__` | Inicializa UI, parámetros, fecha, rutas y advertencia de `R:` |
| `showDate` | Actualiza fecha y archivo base |
| `seleccionar_drive` | Cambia directorio de trabajo |
| `Abrir_archivo` | Método principal conectado al botón de procesamiento |
| `Abrir_archivo__` | Versión alternativa/histórica no conectada a la UI |
| `inicializar_` | Limpia buffers de 16 canales |
| `definir_dia` | Crea directorios y prepara rutas del día |
| `Btn_Mseed` | Convierte buffers a MiniSEED mediante `conversion_mseed()` |
| `unir_mseed` | Une MiniSEEDs de bloques adicionales contra el primer bloque |
| `imprimir_png` | Genera gráficos dayplot |
| `Salir_` | Cierra ventanas de Qt |
| `closeEvent` | Acepta cierre de ventana |

## Dependencias

### Externas

| Módulo | Uso |
|---|---|
| `PyQt5` | Interfaz gráfica |
| `numpy` | Conversión y organización de muestras |
| `obspy` | Lectura, escritura, fusión y graficación MiniSEED |
| `matplotlib` | Backend de gráficos en modo `Agg` |
| `shutil` | Copia, movimiento y eliminación indirecta de archivos |
| `re` | Validación de nombres de archivo |
| `csv` | Escritura de configuración de estaciones |
| `datetime` | Fechas y marcas temporales |
| `pathlib` | Manejo de rutas |

### Internas

| Módulo | Funciones usadas |
|---|---|
| `rsa_io` | `leer_mseed`, `conversion_mseed`, `lectura_archivo`, `escritura_archivo` |
| `rsa_utilidades` | `loc_cabecera` |
| `metodos_gestion` | `parametros_estaciones`, `obtencion_hora`, `obtener_directorios` |

## Manejo de errores y robustez

### Aspectos positivos

- El programa intenta continuar ante errores de lectura de MSEED en la unión.
- Los MSEEDs inconsistentes se mueven a `_inconsistentes/` cuando se proporciona esa carpeta.
- La unión usa escritura atómica mediante archivo temporal.
- Se intenta recuperar sincronización si el puntero no cae exactamente en la marca fija.
- Se crean directorios necesarios mediante `_Path(...).mkdir(parents=True, exist_ok=True)`.

### Aspectos frágiles

- Muchas excepciones se silencian con `except Exception: pass`, lo que dificulta diagnóstico.
- `loc_cabecera()` se llama sin protección suficiente en algunos puntos críticos.
- Si el usuario cancela la selección manual de archivo, `self.archivo_binario` puede quedar vacío y fallar después.
- `definir_dia()` recorre `range(0, 100)` para revisar MSEEDs, aunque los canales reales son 16; los errores se silencian.
- La barra de progreso mezcla segundos estimados del archivo actual con `contador_segundos` acumulado desde `analogico.csv`, lo que puede producir avances poco claros cuando hay reanudación.
- El cálculo real de huecos no existe.

## Productos Generados

### Archivos MiniSEED

- Formato: MiniSEED.
- Codificación esperada: STEIM1.
- Tamaño de registro esperado: 512 bytes.
- Nombre esperado:

```text
CODIGO_20yymmdd_HHMMSS.mseed
```

- Ubicación: `self.directorio_registros`.

La escritura inicial depende de `rsa_io.conversion_mseed()`.
La reescritura durante unión sí usa escritura atómica.

### Gráficos PNG

- Tipo: `dayplot`.
- Resolución: 200 DPI.
- Tamaño: 2400 × 1800 píxeles.
- Grosor de línea: 0.2.
- Nombre esperado:

```text
CODIGO_AAAAMMDD_HHMMSS.png
```

- Ubicación: `self.directorio`.

### Archivos de control

- `analogico.csv`: estado de lectura y reanudación.
- `archivo_estaciones`: configuración extraída desde la cabecera del binario.

## Escenario de Uso Típico

1. El sistema de registro continuo coloca archivos binarios en `R:` con nombres de 12 dígitos, por ejemplo:

```text
260115120000
```

2. El operador abre la aplicación.
3. Selecciona la fecha de procesamiento.
4. Presiona el botón de procesamiento.
5. El programa copia archivos del día desde `R:` hacia el directorio de trabajo.
6. El programa prepara los directorios del día.
7. Verifica o reinicia `analogico.csv` según el día.
8. Valida MSEEDs existentes contra el estado guardado.
9. Lee cada archivo binario.
10. Convierte cada lectura a MiniSEED por canal.
11. Si hay más de un archivo, une los MiniSEEDs contra el primer bloque.
12. Genera gráficos PNG.
13. Muestra mensaje de finalización.

## Limitaciones y Suposiciones

- La unidad `R:` puede no existir; en ese caso el programa permite continuar buscando un archivo local/manual.
- El formato binario es fijo: 2077 bytes por segundo, 16 canales, 64 muestras por segundo.
- La tasa de muestreo esperada en validación es 64 Hz.
- El número de canales está codificado como 16 en varias partes del script.
- El procesamiento se ejecuta en el hilo principal de la interfaz.
- La reanudación depende de `analogico.csv`, pero ese archivo solo guarda un estado único.
- El cálculo de huecos está pendiente o no implementado.
- La corrección de línea base se calcula por archivo leído, no por día completo.
- El patrón de borrado de MSEEDs puede fallar si los códigos no tienen exactamente cuatro caracteres.

## Prioridades de corrección recomendadas

1. Mantener documentado que los archivos terminados en `235959` se renombran a `000000` del mismo día, no del día siguiente; verificar únicamente si esa regla coincide con el significado real del archivo generado por el registrador.
2. Corregir o documentar el comportamiento cuando `R:` existe pero no hay archivos del día.
3. Revisar la lógica de `analogico.csv`, especialmente su uso como estado único para reanudación.
4. Proteger la validación de MSEEDs existentes cuando `contador_s == 0`.
5. Corregir el patrón de `eliminar_mseeds_del_dia()` para que coincida con la longitud real de los códigos de canal.
6. Implementar cálculo real de huecos o eliminar el mensaje de “segundos faltantes” como criterio técnico.
7. Revisar si `fill_value='latest'` es aceptable para datos sísmicos o si debe cambiarse.
8. Revisar la corrección de línea base y decidir si debe ser por archivo, por día o por canal con trazabilidad.
9. Validar tempranamente la existencia de la raíz `rsa_sismologia`.
10. Revisar la dependencia de `leer_mseed()` para asegurar que `imprimir_png()` accede a los canales correctos.
11. Eliminar o marcar claramente `Abrir_archivo__()` como versión histórica si no se usa.
12. Reducir los `except Exception: pass` o reemplazarlos por mensajes de log útiles.
13. Revisar el uso de `range(0, 100)` en `definir_dia()` y cambiarlo a 16 o a la longitud real de `self.nombre_canal`.
14. Validar el caso en que el usuario cancela la selección manual de archivo.
15. Confirmar si `conversion_mseed()` escribe de forma segura o si también requiere escritura atómica.

## Objetivo de futuras correcciones

El objetivo no debe ser reescribir completamente el programa, sino fortalecer el flujo existente para que:

- la reanudación sea confiable;
- no se borren o muevan MSEEDs válidos por un `analogico.csv` desactualizado;
- los archivos del día se identifiquen correctamente;
- los casos de cambio de día y `235959` queden documentados de forma coherente con la regla real del script;
- los huecos se calculen de forma real;
- la unión de trazas no introduzca datos artificiales sin trazabilidad;
- los gráficos se generen desde los canales correctos;
- los errores importantes queden visibles en la interfaz.

---

Este contexto describe el comportamiento real observado en `automatico V2.py` y corrige las diferencias detectadas respecto al contexto original `automatico_contx.md`.
