# Contexto del Programa: `Corrección de EVT por reseteo.py`

## Alcance

Este script es una herramienta de escritorio PyQt5 para revisar, corregir y preclasificar archivos EVT de acelerografos ETNA cuando el equipo pierde energia, reinicia su reloj y genera registros con fechas cercanas a 1980.

No inserta directamente eventos en la estructura RSA. Su funcion principal es reconstruir fechas probables, separar ruido/sismos, asociar eventos con el catalogo diario y exportar los EVT corregidos a una carpeta de destino.

## Problema que Resuelve

Cuando un ETNA pierde energia, el reloj interno puede volver a fechas de fabrica, por ejemplo:

```text
1980-01-01
1980-01-04
1980-01-08
```

En los respaldos esto suele aparecer como carpetas:

```text
800101/
800104/
800108/
```

o como fechas `AAAAMMDD` anteriores al 2000. El programa intenta reconstruir el tiempo real usando:

- la fecha de descarga;
- las fechas de modificacion de los archivos EVT;
- un EVT marcado manualmente como sismo;
- eventos existentes en el catalogo RSA;
- continuidad temporal entre periodos.

## Entrada Esperada

El usuario selecciona una carpeta de descarga con nombre `AAAAMMDD`, por ejemplo:

```text
20260306/
```

Dentro de ella el programa busca subcarpetas de reseteo validas:

```text
800101/
800104/
800108/
```

Tambien acepta carpetas de reseteo con formato `AAAAMMDD`, siempre que sean fechas entre 1980-01-01 y antes del 2000-01-01.

## Relacion con el Almacenamiento Ordenado

En respaldos ordenados como:

```text
ChaBase/
  2025/
    20251204/
      800101/
        FR001.EVT
```

el script debe ejecutarse sobre la carpeta de descarga, por ejemplo `20251204`, no necesariamente sobre toda la estacion.

Las carpetas posteriores al 2000 dentro de la descarga se consideran registros con fechas ya plausibles y se preclasifican aparte.

## Flujo Operativo

1. Seleccionar carpeta de destino.
2. Seleccionar carpeta de descarga `AAAAMMDD`.
3. El programa detecta subcarpetas de reseteo anteriores al 2000.
4. Los EVT encontrados se cargan en una lista.
5. Todos los archivos inician marcados como `ruido`.
6. El usuario revisa graficos y marca sismos con botones o atajos.
7. Se selecciona la raiz que contiene `DIA`.
8. Se calibra contra el catalogo usando el ultimo sismo o periodos detectados.
9. El programa asigna automaticamente eventos cercanos dentro del margen elegido.
10. Al guardar, exporta los EVT a carpetas por fecha corregida.

## Interfaz

Controles principales:

| Control | Uso |
|---|---|
| Seleccionar carpeta de destino | Define donde se exportaran los EVT corregidos |
| Seleccionar carpeta de descarga | Carga una descarga `AAAAMMDD` con subcarpetas de reseteo |
| Marcar como Evento | Marca el EVT actual como sismo |
| Marcar como Ruido | Marca el EVT actual como ruido |
| Mostrar fechas de sismos | Lista fechas corregidas de los EVT marcados como sismo |
| Calibrar y asignar con catalogo | Ajusta fechas contra eventos RSA |
| Guardar eventos | Exporta y limpia origen |

Atajos:

```text
Ctrl+S -> marcar como evento
Ctrl+R -> marcar como ruido
```

## Reconstruccion Temporal

La referencia inicial se toma de la carpeta de descarga:

```python
fecha_base_ref_original = fecha_descarga a las 17:00:00
```

Luego se busca el archivo EVT mas reciente dentro de las carpetas de reseteo. Ese archivo define `mtime_ref`.

La fecha corregida preliminar de cada EVT se calcula como:

```text
fecha_base_ref + (mtime_evt - mtime_ref)
```

Esta aproximacion presupone que las marcas de modificacion conservan continuidad temporal respecto a la descarga.

## Calibracion Contra Catalogo

El usuario marca uno o mas EVT como sismo. Luego el programa:

- toma el ultimo EVT marcado como sismo;
- estima su fecha corregida preliminar;
- busca el catalogo RSA del dia estimado;
- muestra candidatos dentro de una ventana de +/- 5 horas;
- permite seleccionar el evento real;
- recalibra la referencia para que ese EVT quede con diferencia cero;
- asigna automaticamente los demas EVT dentro del margen configurado.

El margen para asignacion automatica se configura en minutos. Por defecto es `5 min`.

## Periodos por Reseteos Multiples

El programa detecta posibles reseteos adicionales agrupando los EVT por prefijo de serie:

```text
FR001, FR002, ...
FS001, FS002, ...
FW001, FW002, ...
```

Cada prefijo se trata como un periodo. Si hay mas de un periodo, la reconstruccion con una sola referencia puede no ser suficiente.

En ese caso el programa:

- reconstruye desde el ultimo periodo hacia atras;
- usa el ultimo sismo marcado de cada periodo como ancla cuando existe;
- evita reutilizar el mismo evento de catalogo como ancla en varios periodos;
- permite periodos sin sismo marcado, reconstruidos solo por continuidad temporal.

## Catalogos RSA

La raiz configurada debe contener:

```text
DIA/
  AAAA/
    AAAA_MM/
      AAAA_MM_DD/
        AAAAMMDD000000.csv
```

El programa lee el CSV diario con separador `;` y usa:

- columna 0: numero de evento;
- columna 1: nombre de evento;
- columna 2: tipo de evento cuando existe.

La hora se extrae del nombre del evento con formato:

```text
AAAAMMDD_HHMMSS
```

## Exportacion

Al guardar, el programa exporta todos los EVT cargados, tanto ruido como evento, a la carpeta de destino.

La estructura de salida es:

```text
destino/
  AAAAMMDD/
    archivo_original.EVT
```

La fecha `AAAAMMDD` proviene de:

1. fecha asignada por catalogo, si existe;
2. fecha corregida por reconstruccion, si no existe asignacion.

El archivo conserva su nombre original. Si hay colision de nombres, agrega sufijo:

```text
FR001_001.EVT
```

Ademas ajusta la fecha de modificacion del archivo exportado a la fecha corregida/asignada.

## Salidas Auxiliares

En la carpeta destino se generan:

```text
evt_exportados_todos.csv
eventos_sismos.txt
asociaciones_sismos.txt
```

`evt_exportados_todos.csv` resume:

- ruta original;
- ruta exportada;
- etiqueta;
- fecha corregida;
- subcarpeta original;
- nombre original;
- si el origen fue borrado.

## Advertencia Importante

Este programa no es solo un visor.

Al guardar:

- copia EVT al destino;
- cambia la marca de modificacion del archivo exportado;
- elimina el archivo original;
- elimina carpetas vacias del origen;
- puede copiar carpetas posteriores al 2000 al destino y borrar esas carpetas del origen, siempre con confirmacion.

Antes de usarlo sobre respaldos unicos, conviene trabajar sobre una copia verificable.

## Relacion con `Insercion de estaciones EVT.py`

Este script debe verse como paso previo cuando los EVT tienen fechas reseteadas.

Flujo recomendado:

1. Usar `Corrección de EVT por reseteo.py` para reconstruir fechas y ordenar/exportar EVT.
2. Revisar el resumen generado.
3. Usar `Insercion de estaciones EVT.py` sobre los EVT ya corregidos o preclasificados.

## Limitaciones y Riesgos

- La referencia inicial asume la hora `17:00:00` de la fecha de descarga.
- La reconstruccion depende de marcas de modificacion (`mtime`), que pueden cambiar al copiar archivos.
- Si el respaldo no conserva marcas originales, la reconstruccion puede fallar.
- Si no hay sismos marcados, la calibracion contra catalogo no puede anclarse.
- En periodos sin sismo, la reconstruccion depende solo de continuidad temporal.
- El programa usa rutas de catalogo `DIA` construidas manualmente y no `obtener_directorios()`.

## Archivos Relacionados

- `Insercion de estaciones EVT.py`: inserta EVT ya ubicados temporalmente dentro de la estructura RSA.
- `ayuda/ayuda_insercion_evt.html`: explica el flujo de insercion EVT general.
