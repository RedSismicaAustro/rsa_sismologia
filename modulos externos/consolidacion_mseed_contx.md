# Contexto del Programa: `consolidacion_mseed.py`

## Alcance

`consolidacion_mseed.py` es el programa integrado para consolidar MiniSEED diarios.

Combina las responsabilidades seguras de:

- `automatico.py`: estructura diaria y registro continuo analogico desde `R:`;
- `acelerografo.py`: union e incorporacion de estaciones digitales/acelerograficas desde `Datos Estaciones`.

Los programas originales quedan separados para poder ejecutar cada flujo de forma independiente.

## Proposito

Generar la estructura diaria de informacion sismica si no existe, regenerar los MiniSEED analogicos del dia y agregar las estaciones digitales a la misma estructura.

## Entradas

### Analogicas

- Fuente: unidad `R:`.
- Nombre esperado: `AAMMDDhhmmss`.
- Los archivos se copian al directorio diario de trabajo con prefijo de siglo: `20AAMMDDhhmmss`.

### Digitales

- Fuente: `directorio_trabajo/Datos Estaciones/`.
- Configuracion: `datos/digitales.csv`.
- Cada fila valida indica la carpeta digital y el indice de estacion en `parametros_estaciones()`.

## Supuestos Operativos

- Los codigos de estacion/canal tienen siempre 4 caracteres.
- El registro analogico tiene 16 canales y 64 muestras por segundo.
- `analogico.csv` no se usa como puntero ni como control de reanudacion.
- La carpeta de trabajo por defecto es `G:/Mi unidad/DIA/`.
- La carpeta digital por defecto es `G:/Mi unidad/DIA/Datos Estaciones/`.
- Si no hay analogicos, el programa puede igualmente crear la estructura diaria y procesar digitales.

## Flujo General

1. Se inicia la interfaz PyQt5 reutilizando `src/ui/automatico.ui`.
2. Se carga `parametros_estaciones()`.
3. Se lee `datos/digitales.csv`.
4. Se selecciona la fecha del dia a consolidar.
5. Se buscan y copian los binarios analogicos desde `R:`.
6. Se crea la estructura diaria con `definir_dia()`.
7. Se eliminan los MiniSEED existentes del dia en `mseed/registros`.
8. Se convierten los binarios analogicos a MiniSEED.
9. Si hay varios bloques analogicos, se unen por canal.
10. Se procesan las estaciones digitales configuradas.
11. Se generan los MiniSEED digitales en la misma estructura diaria.
12. Se generan los PNG al final, cuando los MiniSEED analogicos y digitales ya estan en su directorio definitivo.

## Logging

`mensaje_lbl()`:

- antepone `[HH:MM:SS]`;
- imprime en consola;
- conserva el historial;
- compacta saltos de linea con ` | `;
- deja visible el final del registro.

Ejemplo:

```text
[14:36:14] Lectura terminada, | Segundos leidos: 62077 | Segundos faltantes: 0
```

## Procesamiento Analogico

La lectura binaria:

- localiza la cabecera con `loc_cabecera()`;
- lee desde el inicio util del archivo;
- valida marca fija, segundo, cabecera y cuerpo;
- resta linea base por archivo;
- reporta segundos faltantes segun saltos del contador.

La conversion:

- usa `conversion_mseed_bloque()`;
- conserva la hora real de cada archivo;
- escribe MiniSEED con `STEIM1`, `reclen=512` y `sampling_rate = 64.0`;
- usa escritura atomica.

La union de bloques analogicos:

```python
merge(method=1, fill_value=None)
split()
```

Esto mantiene los espacios sin senal como huecos reales, sin rellenarlos con el ultimo valor.

## Procesamiento Digital

`procesar_digitales()`:

- valida cada fila de `datos/digitales.csv`;
- consulta la habilitacion y los codigos desde una copia intacta de `parametros_estaciones()`;
- ubica la carpeta de la estacion dentro de `Datos Estaciones`;
- lee archivos MiniSEED del dia seleccionado;
- filtra trazas por codigo de estacion;
- revisa huecos y solapes antes y despues de unir;
- fusiona con `merge(method=1, fill_value=None)` y luego `split()`;
- escribe un MiniSEED diario por estacion.

La configuracion digital se mantiene separada de las listas mutables usadas por la conversion analogica. Esto evita que `Btn_Mseed()` altere `HAB_CANAL` o `CODIGO` antes de procesar estaciones digitales como `TENG`.

## Generacion de PNG

Los PNG se generan como etapa final:

- primero se consolidan todos los MiniSEED analogicos y digitales;
- luego se generan los PNG analogicos;
- finalmente se generan los PNG digitales.

Los PNG digitales se generan leyendo nuevamente el MiniSEED final desde `mseed/registros`, no desde el `Stream` temporal usado durante la union.

El nombre de salida digital mantiene el formato:

```text
CODIGO_AAAAMMDD_000000.mseed
CODIGO_AAAAMMDD_000000.png
```

## Salidas

Todas las salidas se ubican en la estructura del dia creada por `obtener_directorios()`:

- MiniSEED analogicos y digitales en `mseed/registros`;
- PNG de revision en la carpeta base del dia;
- archivo de estaciones del dia cuando corresponde.

## Separacion de Responsabilidades

- Usar `automatico.py` cuando solo se quiera procesar el continuo analogico desde `R:`.
- Usar `acelerografo.py` cuando solo se quiera unir estaciones digitales/acelerograficas.
- Usar `consolidacion_mseed.py` cuando se quiera construir el dia completo en una sola corrida.
