# Contexto del Programa: `caudales_filtraciones.py`

## Alcance del documento

Este documento describe el comportamiento real del script `caudales_filtraciones.py`, contrastado contra su implementación actual.

Está pensado como contexto técnico para cualquier agente de revisión, depuración o corrección de código. No está orientado exclusivamente a Codex ni a una herramienta específica.

El objetivo no es rediseñar el programa desde cero, sino dejar claro qué hace actualmente, qué supuestos maneja, qué partes están correctamente representadas en el contexto original y qué puntos deben revisarse con prioridad.

---

# Identidad del Programa

Este script implementa una aplicación de escritorio en PyQt5 para **análisis de caudales de filtración** a partir de eventos sísmicos de tipo `CONTROL`.

El programa trabaja principalmente con el archivo MiniSEED diario del canal:

```text
CHA2_AAAAMMDD_000000.mseed
```

Su función operativa es permitir que el operador visualice una traza sísmica, marque dos puntos en el gráfico y registre un evento `CONTROL` asociado a un intervalo de tiempo. Luego, el historial de eventos `CONTROL` se usa para recalcular una serie de caudales.

---

# Propósito Principal

El propósito principal es estimar caudales de filtración a partir del tiempo transcurrido entre eventos consecutivos de tipo `CONTROL`.

La relación usada es inversa:

```text
Caudal = 1.214 × 3,500,000 / segundos entre eventos
```

Donde:

- `3,500,000` es una constante base usada históricamente.
- `1.214` es un factor de corrección empírico documentado en el código como ajuste por errores cometidos en el cálculo.
- `segundos entre eventos` corresponde a la diferencia temporal entre un evento `CONTROL` y el evento `CONTROL` anterior dentro del historial.

El primer evento de la serie recibe caudal `0`, porque no tiene evento anterior contra el cual calcular diferencia.

---

# Arquitectura General

## Estilo de Aplicación

- Aplicación de escritorio con interfaz gráfica en PyQt5.
- Interfaz cargada desde `caudales.ui`.
- Visualización de señales mediante Matplotlib.
- Selección interactiva de marcas con clic derecho.
- Uso de archivos CSV para almacenamiento del historial de caudales y eventos.
- Guardado automático de `caudales.csv` al cerrar la aplicación.

## Modo de Operación

- **Por día:** el usuario selecciona una fecha para cargar y visualizar el MiniSEED diario.
- **Por canal fijo de archivo:** el archivo MiniSEED buscado siempre usa el código `CHA2`.
- **Por traza dentro del stream:** si el MiniSEED contiene varias trazas, el usuario puede elegir la traza desde un combo.
- **Histórico:** el programa permite cargar eventos `CONTROL` en un rango de fechas y graficar la evolución del caudal.

---

# Flujo de Ejecución Verificado

## Fase 1: Inicio de la Aplicación

Al iniciar el programa:

1. Se determina la raíz del proyecto buscando el directorio `rsa_sismologia`.
2. Se agregan al `sys.path` las rutas:
   - `src/librerias`
   - `datos`
3. Se carga la interfaz gráfica desde:

```text
src/ui/caudales.ui
```

4. Se configura la ventana con el título:

```text
CAUDALES    --
```

5. Se configuran fechas por defecto:
   - Fecha de gráfico: día actual.
   - Fecha inicial de serie: 7 días antes.
   - Fecha final de serie: día actual.
6. Se configura el combo de diezmado con:

```text
1, 2, 5, 8, 10
```

7. El diezmado por defecto se establece en `10`.
8. Se define como directorio de trabajo por defecto:

```text
G:/Mi unidad/DIA/
```

9. Se conectan los botones de la interfaz:
   - `boton_cargar_eventos_control`
   - `boton_directorio`
   - `boton_graficar`
   - `boton_guardar_marcas`
   - `boton_graficar_caudales`
   - `boton_salir`
10. Se inicializan variables internas.
11. Se llama automáticamente a `cargar_componentes_fecha()`.

---

# Rutas del Proyecto

El script usa la función:

```python
extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
```

Esto significa que depende de que el archivo se ejecute dentro de una estructura que contenga el directorio:

```text
rsa_sismologia
```

Si no se encuentra ese directorio, `ruta_proyecto` queda vacío y pueden construirse rutas inválidas hacia:

- `src/librerias`
- `datos`
- `src/ui/caudales.ui`

## Punto a revisar

El script debería validar tempranamente que `ruta_proyecto` no esté vacío. Si no se encuentra la raíz del proyecto, debería mostrar un mensaje claro y detener la ejecución.

---

# Configuración del Directorio de Trabajo

El directorio de trabajo por defecto es:

```text
G:/Mi unidad/DIA/
```

El usuario puede cambiarlo con el botón de directorio.

Cuando se selecciona un nuevo directorio:

- Se asegura que termine con `/`.
- Se actualiza `self.directorio_trabajo`.
- Se actualiza la etiqueta `Lbl_directorio`.

## Matiz importante

Al cambiar el directorio de trabajo, el script no llama automáticamente a `cargar_componentes_fecha()`. Por tanto, el usuario puede quedar con datos cargados del directorio anterior hasta que cambie la fecha o presione una acción que fuerce recarga.

## Recomendación

Después de cambiar el directorio, conviene llamar explícitamente a:

```python
self.cargar_componentes_fecha()
```

---

# Carga de Datos del Día

La función principal para cargar el día es:

```python
cargar_componentes_fecha()
```

Cuando se ejecuta:

1. Obtiene la fecha desde `selector_fecha_grafico`.
2. Construye el nombre del archivo MiniSEED:

```text
CHA2_AAAAMMDD_000000.mseed
```

3. Construye `self.archivo` con:

```text
directorio_trabajo + AAAAMMDD000000
```

4. Obtiene los directorios del día mediante:

```python
obtener_directorios(self.archivo)
```

5. Busca el archivo MiniSEED en:

```python
self.directorios['Directorio_registros']
```

6. Si el archivo existe:
   - Lo carga con `obspy.read`.
   - Llama a `cargar_componentes(self.stream)`.
7. Si no existe:
   - Imprime en consola que no existe.
   - Asigna `self.stream = None`.

Luego carga `caudales.csv` desde el directorio de trabajo:

```text
G:/Mi unidad/DIA/caudales.csv
```

Si existe:

- Lo lee con `lectura_archivo`.
- Recalcula todos los caudales con `recalcular_caudales()`.
- Guarda inmediatamente el archivo recalculado.

Si no existe:

- Inicializa `self.caudales = []`.

---

# Archivo MiniSEED Principal

El script está hardcodeado para buscar archivos con el patrón:

```text
CHA2_AAAAMMDD_000000.mseed
```

Esto significa que el código `CHA2` está fijo en el script.

## Matiz importante

Aunque el archivo buscado es fijo (`CHA2`), dentro del stream se cargan todas las trazas disponibles en ese MiniSEED. Luego el usuario puede elegir la traza mediante `combo_traza`.

Por tanto, es más exacto decir:

- El archivo MiniSEED de entrada está fijado a `CHA2`.
- La traza mostrada puede seleccionarse entre las trazas contenidas en ese archivo.

---

# Carga y Selección de Trazas

La función:

```python
cargar_componentes(stream)
```

limpia el combo de trazas y agrega cada `traza.id` disponible en el stream.

Además, intenta seleccionar automáticamente una traza vertical:

```python
if traza.id.endswith("Z") or traza.id.endswith("ENV"):
    traza_vertical_index = i
```

Si encuentra una traza que termina en `Z` o `ENV`, la selecciona. Si no encuentra ninguna, selecciona la primera traza.

---

# Visualización del Gráfico Interactivo

La función:

```python
desplegar_grafico()
```

genera el gráfico interactivo.

## Validaciones iniciales

Si no existe `self.stream`, muestra advertencia:

```text
Debes seleccionar una fecha válida.
```

## Preparación

- Cierra figuras previas con `plt.close('all')`.
- Limpia `self.marcas_usuario`.
- Obtiene la traza seleccionada desde `combo_traza`.
- Copia la traza a `self.tr_segmento`.
- Aplica diezmado si el factor seleccionado es mayor a 1:

```python
self.tr_segmento.decimate(factor_diezmado, no_filter=True)
```

## Punto técnico importante

El diezmado se realiza con `no_filter=True`, por lo que no se aplica filtro antialias. Esto mejora velocidad, pero puede distorsionar visualmente componentes de alta frecuencia.

Como el uso es visual e interactivo, puede ser aceptable, pero debe quedar documentado.

---

# Marcado de Eventos CONTROL Existentes

El script lee el archivo de eventos del día:

```python
self.eventos = lectura_archivo(self.directorios['archivo_csv'])
```

Luego filtra eventos cuyo tipo sea exactamente:

```text
CONTROL
```

Para cada evento `CONTROL`:

- Busca si ya está en `self.caudales` con bandera `"1"`.
- Si existe, asigna color de texto verde.
- Si no existe, asigna color de texto rojo.

## Diferencia importante con el contexto original

El contexto original indicaba que las líneas verticales eran:

- Verde sólida para evento procesado.
- Roja punteada para evento nuevo.

El script real no hace eso.

Actualmente la línea vertical se dibuja siempre así:

```python
ax.axvline(x=tiempo_relativo, color='green', linestyle=':', linewidth=1)
```

Es decir:

- La línea siempre es verde.
- La línea siempre es punteada.
- Lo que cambia es el color del texto de la etiqueta.

## Corrección recomendada

Si se desea que la línea refleje el estado del evento, debería usarse `color_linea` también en `axvline`.

---

# Interacción con Clic Derecho

El usuario puede hacer clic derecho sobre el gráfico.

La lógica actual:

- Si el clic está cerca de una marca existente, elimina esa marca.
- Si no está cerca y hay menos de dos marcas, agrega una nueva.
- La tolerancia es:

```python
1 / 1440
```

Esto equivale aproximadamente a un minuto en unidades de días de Matplotlib.

## Punto crítico

Para redibujar las marcas, el script ejecuta:

```python
for line in ax.lines[1:]:
    line.remove()
```

Esto elimina todas las líneas excepto la primera.

El problema es que también puede eliminar líneas de eventos `CONTROL` previamente dibujadas, no solo las marcas del usuario.

## Recomendación

Guardar referencias separadas a las líneas de marcas del usuario y eliminar solo esas líneas, sin tocar las líneas de eventos existentes.

---

# Guardado de Marcas como Evento CONTROL

La función:

```python
guardar_marcas()
```

convierte dos marcas del usuario en un evento `CONTROL`.

## Validación

Exige exactamente dos marcas. Si no hay dos marcas, muestra advertencia y no guarda nada.

## Conversión de marcas

Las marcas se ordenan cronológicamente.

Luego se convierten a `datetime`:

```python
marca_dt_inicio = mdates.num2date(...).replace(tzinfo=None)
marca_dt_fin = mdates.num2date(...).replace(tzinfo=None)
```

Se calcula:

- `tiempo_inicio`: segundos desde el inicio del día hasta la primera marca.
- `tiempo_fin`: segundos desde el inicio del día hasta la segunda marca.

---

# Punto crítico: posible error al construir `fecha_real`

El script contiene:

```python
tiempo = obtencion_hora(self.archivo)
fecha_real = tiempo + tiempo_inicio
```

Si `obtencion_hora(self.archivo)` devuelve un objeto `datetime`, esta operación es incorrecta en Python, porque no se puede sumar directamente un entero a un `datetime`.

Lo correcto sería:

```python
fecha_real = tiempo + timedelta(seconds=tiempo_inicio)
```

## Recomendación prioritaria

Este punto debe revisarse en primer lugar, porque puede impedir guardar marcas correctamente.

---

# Creación del Evento Auxiliar

El script crea un evento auxiliar con:

```python
tipo_evento = 'CONTROL'
estaciones = "CHA231000000"
evento_auxiliar = (
    n_evento,
    nombre_sis,
    tipo_evento,
    ahora,
    tiempo_inicio,
    tiempo_fin,
    'RSA',
    estaciones,
    'Caudales'
)
```

Luego agrega ese evento al archivo auxiliar:

```python
eventos_auxiliar.append(evento_auxiliar)
escritura_archivo(self.directorios['archivo_auxiliar'], eventos_auxiliar)
```

Después procesa todos los eventos auxiliares mediante:

```python
extraccion(evento_auxiliar, solo_eventos, self.archivo, False)
```

Los eventos generados se agregan a `self.eventos`, se ordenan, se eliminan duplicados y se guarda el archivo principal de eventos.

---

# Punto a revisar: uso de `self.eventos`

`guardar_marcas()` usa:

```python
solo_eventos = [fila[1] for fila in self.eventos]
```

Esto presupone que `self.eventos` ya fue cargado previamente por `desplegar_grafico()`.

Si el usuario intenta guardar marcas sin haber ejecutado correctamente el flujo de graficado, puede haber problemas de estado.

En el uso normal, las marcas se hacen desde el gráfico, por lo que `self.eventos` debería existir. Aun así, conviene validar explícitamente.

---

# Recalculo de Caudales

La función:

```python
recalcular_caudales()
```

ordena los eventos por nombre y recalcula toda la serie.

El cálculo aplicado es:

```python
caudal = int(1.214 * 3500000 / segundos) if segundos > 0 else 0
```

## Características reales

- Los eventos se ordenan por el campo `fila[0]`.
- Se conserva la bandera de cada fila.
- El primer evento tiene caudal `0`.
- Si hay error al procesar un evento, se conserva el evento con caudal `0`.
- El cálculo se realiza independientemente de si la bandera es `0` o `1`.

---

# Punto crítico: posible error en compatibilidad con nombres antiguos

Dentro de `recalcular_caudales()` aparece:

```python
if len(fila[0]) == 17:
    fila[1] = '20' + fila[1]
```

Esto parece intentar corregir eventos con año de dos dígitos, pero modifica `fila[1]`, que corresponde al valor de caudal, no al nombre del evento.

Si la intención era convertir el nombre del evento de formato `AAMMDD_HHMMSS.sis` a `AAAAMMDD_HHMMSS.sis`, debería corregirse `fila[0]`, no `fila[1]`.

## Recomendación prioritaria

Revisar y corregir esta línea, porque puede corromper el valor del caudal y no corrige realmente el nombre del evento.

---

# Gráfico Histórico de Caudales

La función:

```python
graficar_caudales()
```

genera la serie histórica.

## Filtros aplicados

Solo grafica eventos que cumplan:

- Bandera igual a `"1"`.
- Fecha dentro del rango seleccionado.

## Exportación

Guarda el archivo:

```text
caudales_periodo.csv
```

en el directorio de trabajo.

El archivo contiene dos columnas sin encabezado:

1. Tiempo relativo en días desde la primera fecha graficada.
2. Valor graficado.

---

# Punto de nomenclatura: caudal vs tiempo

En `graficar_caudales()` el código usa:

```python
ax.plot(fechas, valores, linestyle='-', color='blue', label='Caudales (s)')
ax.set_ylabel("Tiempo (s)")
```

Pero el valor graficado es el resultado de:

```text
1.214 × 3,500,000 / segundos
```

Es decir, no es directamente el tiempo entre eventos, sino un valor calculado inversamente proporcional al tiempo.

## Recomendación

Aclarar la unidad real del valor o corregir las etiquetas del gráfico. Si el resultado representa caudal, el eje Y no debería llamarse `Tiempo (s)`.

---

# Carga Masiva de Eventos CONTROL

La función:

```python
cargar_eventos_control()
```

permite cargar eventos `CONTROL` en un rango de fechas.

## Flujo real

1. Carga `caudales.csv` si existe.
2. Construye un diccionario de eventos ya registrados.
3. Recorre fecha por fecha entre inicio y fin.
4. Para cada día:
   - Construye `AAAAMMDD000000`.
   - Obtiene directorios del día.
   - Busca `archivo_csv`.
   - Extrae eventos cuyo tipo sea `CONTROL`.
5. Elimina duplicados.
6. Agrega al historial solo eventos nuevos.
7. Marca los nuevos eventos con bandera `"1"`.
8. Recalcula toda la serie.
9. Guarda `caudales.csv`.

## Matiz importante

Al agregar eventos nuevos, inicialmente calcula una diferencia en segundos, pero luego llama a `recalcular_caudales()`, por lo que ese valor temporal inicial se reemplaza por el caudal recalculado.

---

# Archivos de Datos

## `caudales.csv`

Archivo principal del historial.

Contiene tres columnas:

| Columna | Contenido |
|---|---|
| 0 | Nombre del evento, normalmente `AAAAMMDD_HHMMSS.sis` |
| 1 | Caudal recalculado |
| 2 | Bandera: `1` confirmado, `0` pendiente |

## `caudales_periodo.csv`

Archivo generado al graficar caudales.

Contiene:

| Columna | Contenido |
|---|---|
| 0 | Tiempo relativo en días desde el primer evento graficado |
| 1 | Valor de caudal graficado |

No incluye encabezados.

## Archivos por día

El script usa rutas generadas por `obtener_directorios()`:

- `archivo_csv`
- `archivo_auxiliar`
- `Directorio_registros`

Los eventos `CONTROL` se leen desde `archivo_csv`.

Los eventos marcados manualmente se escriben primero en `archivo_auxiliar` y luego se procesan hacia `archivo_csv`.

---

# Interfaz de Usuario

## Controles de fecha

- `selector_fecha_grafico`: define el día de la traza sísmica.
- `selector_fecha_inicio`: fecha inicial para serie histórica.
- `selector_fecha_fin`: fecha final para serie histórica.

## Controles de visualización

- `combo_traza`: permite seleccionar una traza dentro del stream cargado.
- `combo_diezmado`: permite seleccionar el factor de diezmado.

## Botones de acción

| Botón | Método conectado |
|---|---|
| `boton_cargar_eventos_control` | `cargar_eventos_control` |
| `boton_directorio` | `seleccionar_directorio_trabajo` |
| `boton_graficar` | `desplegar_grafico` |
| `boton_guardar_marcas` | `guardar_marcas` |
| `boton_graficar_caudales` | `graficar_caudales` |
| `boton_salir` | `close` |

---

# Manejo de Errores

## Comportamiento actual

| Situación | Comportamiento |
|---|---|
| MiniSEED del día no existe | Se imprime en consola y `self.stream = None` |
| Se intenta graficar sin stream | Advertencia al usuario |
| `caudales.csv` no existe | Se inicializa lista vacía |
| Menos o más de 2 marcas | Advertencia al usuario |
| Error al procesar un evento de caudal | Se imprime en consola y se conserva con caudal `0` |
| Sin datos válidos para gráfico de caudales | Advertencia al usuario |
| Error al guardar al cerrar | Se imprime en consola |

## Punto a mejorar

Varios errores importantes se imprimen solo en consola. Para uso operativo, conviene mostrar también advertencias en la interfaz cuando afecten el resultado.


---

# Puntos Reproducibles para el Agente

Esta sección no describe únicamente el comportamiento esperado, sino puntos concretos que pueden verificarse directamente en el script. Deben ser usados por cualquier agente de revisión o corrección como guía para reproducir, confirmar y corregir los problemas sin cambiar innecesariamente el flujo general del programa.

## 1. Construcción de fecha en `guardar_marcas()`

En `guardar_marcas()`, el script obtiene la hora base del archivo mediante:

```python
tiempo = obtencion_hora(self.archivo)
```

Luego calcula el nombre del evento con:

```python
fecha_real = tiempo + tiempo_inicio
nombre_sis = fecha_real.strftime('%Y%m%d_%H%M%S.sis')
```

Este punto es reproducible revisando el tipo retornado por `obtencion_hora(self.archivo)`. Si `obtencion_hora()` retorna un objeto `datetime`, la suma directa con un entero no es válida. En ese caso debe usarse:

```python
fecha_real = tiempo + timedelta(seconds=tiempo_inicio)
```

El agente debe verificar el tipo real de `tiempo` antes de aplicar la corrección.

## 2. Posible corrupción de columna en `recalcular_caudales()`

En `recalcular_caudales()` existe esta condición:

```python
if len(fila[0]) == 17:
    fila[1] = '20' + fila[1]
```

Este punto es reproducible inspeccionando la estructura documentada de `caudales.csv`:

```text
[evento, caudal, bandera]
```

Por esa estructura, `fila[0]` contiene el nombre del evento y `fila[1]` contiene el caudal. Si la intención es corregir nombres de evento con año de dos dígitos, la operación no debería modificar `fila[1]`. El agente debe confirmar el formato histórico de `caudales.csv` y corregir la columna adecuada.

## 3. Redibujado de marcas en el gráfico

Dentro de `desplegar_grafico()`, el manejador de clic derecho elimina líneas con:

```python
for line in ax.lines[1:]:
    line.remove()
```

Esto es reproducible si primero se dibujan eventos `CONTROL` existentes y luego se agregan o eliminan marcas de usuario. Como las líneas de eventos también forman parte de `ax.lines`, pueden eliminarse accidentalmente al redibujar las marcas.

La corrección recomendada es conservar referencias separadas para las marcas del usuario, por ejemplo en una lista `self.lineas_marcas_usuario`, y eliminar solo esas líneas.

## 4. Color real de eventos `CONTROL`

El contexto original decía que los eventos procesados y no procesados se diferenciaban mediante líneas de diferente color. El script real calcula `color_linea`, pero no lo usa en la línea vertical:

```python
ax.axvline(x=tiempo_relativo, color='green', linestyle=':', linewidth=1)
```

El color calculado solo se usa en el texto:

```python
ax.text(..., color=color_linea)
```

Esto es reproducible visualmente: las líneas aparecen verdes punteadas, mientras que el texto cambia entre verde y rojo. El agente debe decidir si corrige el código para que la línea use `color_linea`, o si conserva el comportamiento actual y actualiza únicamente la descripción.

## 5. Etiquetas del gráfico histórico

En `graficar_caudales()` el eje Y se etiqueta como:

```python
ax.set_ylabel("Tiempo (s)")
```

Sin embargo, el valor graficado proviene de `fila[1]`, que luego de `recalcular_caudales()` corresponde al caudal calculado con la fórmula:

```python
caudal = int(1.214 * 3500000 / segundos)
```

Este punto es reproducible comparando el cálculo con la etiqueta del gráfico. El agente debe aclarar la unidad real o cambiar la etiqueta a una descripción coherente con el valor calculado.

## 6. Cambio de directorio sin recarga inmediata

En `seleccionar_directorio_trabajo()`, el script actualiza:

```python
self.directorio_trabajo = folderpath
self.Lbl_directorio.setText(...)
```

pero no llama a `cargar_componentes_fecha()`. Por tanto, después de cambiar el directorio, el `stream`, `archivo_mseed`, `directorios` y `caudales` pueden seguir correspondiendo al directorio anterior hasta que se cambie la fecha o se recargue manualmente.

Este punto es reproducible cambiando el directorio y presionando inmediatamente `Graficar`. El agente debe decidir si conviene llamar a `self.cargar_componentes_fecha()` al final del cambio de directorio.

---

# Hallazgos de Comparación entre Contexto y Script

## 1. El contexto general es correcto

El contexto original describe correctamente que el script:

- usa PyQt5;
- carga un MiniSEED diario;
- trabaja con eventos `CONTROL`;
- permite marcar puntos en un gráfico;
- recalcula caudales;
- guarda `caudales.csv`;
- grafica series históricas;
- exporta `caudales_periodo.csv`.

## 2. El archivo de entrada está más rígido de lo que parece

El contexto habla de canal fijo `CHA2`, lo cual es correcto para el nombre del archivo MiniSEED. Sin embargo, el usuario puede seleccionar trazas internas del stream mediante `combo_traza`.

## 3. Las líneas de eventos CONTROL no cambian como decía el contexto

El contexto decía que los eventos procesados y no procesados se diferenciaban por líneas verdes sólidas y rojas punteadas.

El script real dibuja todas las líneas de eventos en verde punteado. Solo cambia el color del texto.

## 4. Hay un posible error crítico en `guardar_marcas()`

La suma:

```python
fecha_real = tiempo + tiempo_inicio
```

probablemente debería ser:

```python
fecha_real = tiempo + timedelta(seconds=tiempo_inicio)
```

## 5. Hay un posible error crítico en `recalcular_caudales()`

La línea:

```python
fila[1] = '20' + fila[1]
```

probablemente debería actuar sobre `fila[0]`, no sobre `fila[1]`.

## 6. Las marcas del usuario pueden borrar líneas de eventos existentes

El redibujado de marcas elimina `ax.lines[1:]`, lo que puede borrar líneas de eventos `CONTROL`.

## 7. Las etiquetas del gráfico histórico son ambiguas

El eje Y dice `Tiempo (s)`, pero el valor graficado es un caudal calculado mediante una fórmula inversa al tiempo.

## 8. El cambio de directorio no recarga automáticamente los datos

Después de cambiar `directorio_trabajo`, la interfaz actualiza la etiqueta, pero no recarga inmediatamente el MiniSEED ni `caudales.csv`.

## 9. No hay validación temprana de la raíz `rsa_sismologia`

Si el script se ejecuta fuera de la estructura esperada, puede fallar por rutas inválidas.

---

# Prioridades de Corrección Recomendadas

1. Corregir o verificar `fecha_real = tiempo + tiempo_inicio` en `guardar_marcas()`.
2. Corregir la línea de compatibilidad en `recalcular_caudales()` que modifica `fila[1]`.
3. Evitar que el redibujado de marcas elimine líneas de eventos `CONTROL`.
4. Hacer que las líneas de eventos cambien realmente de color según procesado/no procesado, o corregir el contexto si se prefiere solo cambiar texto.
5. Aclarar unidades y etiquetas del gráfico histórico de caudales.
6. Recargar datos después de cambiar el directorio de trabajo.
7. Validar que exista la raíz del proyecto `rsa_sismologia`.
8. Mejorar advertencias de interfaz cuando falte el archivo MiniSEED o existan errores de lectura de eventos.
9. Validar explícitamente la estructura de `caudales.csv`.
10. Documentar que el archivo MiniSEED de entrada está fijo a `CHA2`.

---

# Objetivo de la Corrección

El objetivo de futuras correcciones debe ser fortalecer el uso operativo del programa sin cambiar innecesariamente su flujo de trabajo.

La prioridad debe ser que:

- los eventos `CONTROL` se creen con fecha correcta;
- los caudales se recalculen sin corromper columnas;
- el gráfico mantenga visibles los eventos existentes;
- las unidades del gráfico histórico sean claras;
- el cambio de directorio actualice realmente los datos;
- el programa falle de forma explícita cuando no encuentre rutas o archivos críticos.

---

# Escenario de Uso Típico

## Uso diario

1. El operador abre la aplicación.
2. Selecciona la fecha del día.
3. El programa busca:

```text
CHA2_AAAAMMDD_000000.mseed
```

4. Si el archivo existe, carga sus trazas.
5. El operador presiona `Graficar`.
6. Selecciona visualmente dos marcas con clic derecho.
7. Presiona `Guardar Marcas`.
8. El sistema crea un evento `CONTROL`.
9. Se actualizan los archivos de eventos.
10. Se recarga el historial de caudales.

## Uso histórico

1. El operador define fecha inicial y fecha final.
2. Presiona `Cargar Eventos Control`.
3. El sistema busca eventos `CONTROL` en los archivos diarios.
4. Agrega eventos nuevos a `caudales.csv`.
5. Recalcula todos los caudales.
6. El operador presiona `Graficar Caudales`.
7. Se genera el gráfico histórico y se exporta `caudales_periodo.csv`.

---

# Notas Finales

El contexto original estaba bien estructurado y reflejaba adecuadamente la intención general del programa.

Sin embargo, al comparar contra el script real, aparecen varios matices importantes:

- algunos comportamientos visuales no coinciden exactamente;
- hay dos posibles errores de código que deben revisarse con prioridad;
- el flujo depende fuertemente de archivos y rutas externas;
- el programa necesita mejores validaciones para uso operativo.

Este documento conserva la estructura conceptual del contexto original, pero incorpora los hallazgos necesarios para que cualquier agente pueda revisar o corregir el script con menor riesgo de interpretar mal su funcionamiento.
