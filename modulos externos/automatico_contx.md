# Contexto del Programa: `automatico.py`

## Alcance

`automatico.py` es el programa diario para procesar exclusivamente el registro continuo analogico proveniente de `R:`.

No integra estaciones digitales/acelerograficas. Ese flujo queda separado en `acelerografo.py` y en el programa integrado `consolidacion_mseed.py`.

## Proposito

Generar la estructura diaria de informacion sismica, copiar los binarios analogicos del dia desde `R:`, convertirlos a MiniSEED y generar los PNG de revision.

## Supuestos Operativos

- Los archivos fuente en `R:` tienen nombre de 12 digitos: `AAMMDDhhmmss`.
- Los codigos de estacion/canal tienen siempre 4 caracteres.
- El binario analogico contiene 16 canales.
- La frecuencia de muestreo analogica es 64 Hz.
- La carpeta de trabajo por defecto es `G:/Mi unidad/DIA/`.
- `analogico.csv` ya no se usa como puntero ni como control de reanudacion.
- `datos/analogicas.csv`, si existe, pertenece a informacion general externa y no debe confundirse con el control eliminado.

## Flujo General

1. Se inicia la interfaz PyQt5 desde `src/ui/automatico.ui`.
2. Se cargan parametros de estaciones con `parametros_estaciones()`.
3. Se toma la fecha seleccionada en la interfaz.
4. Se buscan en `R:` los archivos analogicos del dia seleccionado.
5. Se copian los binarios encontrados a la carpeta diaria de trabajo.
6. Se crea o actualiza la estructura diaria con `definir_dia()`.
7. Se eliminan los MiniSEED existentes del dia en `mseed/registros`.
8. Se convierte cada binario analogico a MiniSEED.
9. Si hay mas de un bloque binario del mismo dia, se unen los MiniSEED por canal.
10. Se generan los PNG de revision.

## Logging

`mensaje_lbl()`:

- antepone la referencia horaria `[HH:MM:SS]`;
- imprime tambien en consola;
- conserva el historial del label;
- compacta mensajes multilnea usando ` | `;
- mantiene auto-scroll al final.

Ejemplo:

```text
[14:36:14] Lectura terminada, | Segundos leidos: 62077 | Segundos faltantes: 0
```

## Lectura Binaria

La lectura se hace siempre desde el inicio util del archivo:

- se localiza la cabecera con `loc_cabecera()`;
- no se consulta ni actualiza `analogico.csv`;
- se valida marca fija, contador de segundo, cabecera y tamano del cuerpo;
- se resta una linea base calculada desde el primer bloque valido;
- se acumulan las muestras por canal;
- se reportan huecos detectados por saltos en el contador de segundos.

Formato asumido por segundo:

| Elemento | Valor |
|---|---:|
| Bytes por segundo | 2077 |
| Canales | 16 |
| Muestras por segundo | 64 |
| Marca fija | `\x08\x00\x05\x00` |
| Segundo | 5 bytes ASCII |
| Cabecera | 20 bytes |
| Datos | 2048 bytes |

## Conversion a MiniSEED

`conversion_mseed_bloque()`:

- convierte cada bloque respetando la hora real del archivo;
- no rellena huecos;
- escribe con `sampling_rate = 64.0`;
- usa `STEIM1` y `reclen=512`;
- guarda de forma atomica mediante archivo temporal y reemplazo final.

Nombre de salida:

```text
CODIGO_AAAAMMDD_HHMMSS.mseed
```

## Union de Bloques

Cuando existen dos o mas binarios analogicos del mismo dia:

- el primer bloque queda como base;
- los bloques siguientes se suman al MiniSEED base por canal;
- se revisan huecos y solapes antes de unir;
- la fusion usa:

```python
merge(method=1, fill_value=None)
split()
```

No se usa `fill_value='latest'`, para no rellenar silenciosamente espacios sin senal.

## Salidas

Las salidas principales se escriben en la estructura diaria creada por `obtener_directorios()`:

- MiniSEED analogicos en `mseed/registros`;
- PNG diarios en la carpeta base del dia;
- archivo de estaciones del dia cuando corresponde.

## Relacion con otros programas

- `acelerografo.py`: procesa estaciones digitales/acelerograficas desde `Datos Estaciones`.
- `consolidacion_mseed.py`: integra el flujo analogico de `automatico.py` con el flujo digital de `acelerografo.py`.
