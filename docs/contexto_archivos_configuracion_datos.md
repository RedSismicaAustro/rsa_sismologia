---
proyecto: rsa_sismologia
tipo: contexto_tecnico
archivo: docs/contexto_archivos_configuracion_datos.md
temas: [configuracion, estaciones, digitales, analogicas, responsables, poblaciones, mapas, cartografia]
generado: 2026-08-25
---

# Archivos de Configuración del Repositorio (`datos/` y `datos/mapas/`) — Contexto Técnico Maestro

> **Propósito**: Servir como referencia técnica unificada para comprender el papel, estructura de campos, tipos de datos y consumo en el código de los archivos maestros de configuración: `estaciones.csv`, `digitales.csv`, `analogicas.csv`, `responsables.csv`, `poblaciones.csv` y `mapas.csv`.

---

## 1. Catálogo Maestro de Estaciones: `datos/estaciones.csv`

Es el inventario instrumental central de la Red Sísmica del Austro. Contiene 101 estaciones con 25 parámetros operacionales por fila delimitados por punto y coma (`;`).

* **Consumidores Clave**: [`metodos_gestion.parametros_estaciones()`](file:///c:/proyectos/rsa_sismologia/src/librerias/metodos_gestion.py), [`metodos_gestion.cargar_parametros()`](file:///c:/proyectos/rsa_sismologia/src/librerias/metodos_gestion.py), [`extraer_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/extraer_integrado.py), [`procesamiento_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/procesamiento_integrado.py), [`fases.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/fases.py).

### Estructura de Campos (25 Columnas):

| Índice | Campo de Cabecera | Clave Dict | Tipo | Descripción y Uso Sismológico |
|:---:|:---|:---|:---:|:---|
| **0** | `ESTACION(21)` | `NUM_ESTACION` | `int` | Índice numérico secuencial de la estación (`0` a `100`). Define la posición $i$ de la columna $i+3$ en la matriz `AAAAMMDD000000.csv`. |
| **1** | `NOMBRE(0)` | `NOMBRE` | `str` | Nombre completo descriptivo de la estación (ej. `LABRADO`, `CUSHINHUAYCO`, `CHANLUD`). |
| **2** | `CODIGO(1)` | `CODIGO` | `str` | Código mnemotécnico de 4 letras mayúsculas (ej. `LABR`, `CUSH`, `CHAI`, `PATS`). |
| **3** | `SENSOR(2)` | `SENSOR` | `str` | Tipo de instrumentación (`SISMICO` para sismómetros de velocidad o `ACELEROGRAFICO` para acelerógrafos). |
| **4** | `CANALES(3)` | `CANALES` | `int` | Número de canales del sensor (`1`, `3` o `6` componentes). |
| **5** | `HAB_CANAL(4)` | `HAB_CANAL` | `int` | Bandera de habilitación de adquisición del canal (`1` = habilitada, `0` = deshabilitada). |
| **6** | `COMPONENTE(5)` | `COMPONENTE` | `str` | Componente predeterminada para el análisis (ej. `1` = Vertical/Z, `2` = Norte/N, `3` = Este/E). |
| **7** | `HAB_GRAFICO(6)` | `HAB_GRAFICO` | `int` | Habilitación de trazado gráfico predeterminado en pantallas de monitoreo. |
| **8** | `BITS(7)` | `BITS` | `int` | Resolución de conversión analógico/digital del digitalizador (`16`, `20` o `24` bits). |
| **9** | `CALIBRACION(8)` | `CALIBRACION` | `float` | Factor de calibración o sensibilidad instrumental. |
| **10** | `GANANCIA(9)` | `GANANCIA` | `float` | Ganancia de amplificación electrónica aplicada al canal. |
| **11** | `DIEZ_PLT(10)` | `DIEZ_PLT` | `int` | Factor de diezmado aplicado para la generación del sismograma helicoidal (*dayplot*). |
| **12** | `FACTOR_MUL(11)` | `FACTOR_MUL` | `float` | Multiplicador de escala para conversión a unidades físicas de velocidad/amplitud. |
| **13** | `CALIDAD(16)` | `CALIDAD` | `str` | Calidad de la señal MiniSEED (estándar `D` = Data). |
| **14** | `UBICACION(17)` | `UBICACION` | `str` | Código de localización SEED (ej. `0` o `00`). |
| **15** | `CANAL(18)` | `CANAL` | `str` | Código de canal SEED de 3 caracteres (ej. `ENZ`, `EHZ`, `HHZ`, `HNZ`, `XYZ`, `TRV`). |
| **16** | `RED(19)` | `RED` | `str` | Código de red sismológica FDSN (ej. `UC` = Universidad de Cuenca / Red Sísmica del Austro). |
| **17** | `MUESTREO(20)` | `MUESTREO` | `float` | Frecuencia de muestreo nominal en Hz / sps (ej. `64`, `100`, `200`, `250`). |
| **18** | `LONGITUD(12)` | `LONGITUD` | `float` | Coordenada geográfica de longitud en grados decimales (WGS-84, ej. `-79.0723`). |
| **19** | `LATITUD(13)` | `LATITUD` | `float` | Coordenada geográfica de latitud en grados decimales (WGS-84, ej. `-2.7284`). |
| **20** | `ALTITUD(14)` | `ALTITUD` | `float` | Elevación de la estación sobre el nivel del mar en metros (ej. `3440`). |
| **21** | `RUIDO(15)` | `RUIDO` | `float` | Nivel base de ruido estimado para umbrales de disparo automático STA/LTA. |
| **22** | `FILTRO(22)` | `FILTRO` | `str` | Parámetros o tipo de filtro analógico/digital base. |
| **23** | `POLARIDAD(23)` | `POLARIDAD` | `str` | Polaridad del primer arribo de onda P (`P` = Positiva / Up, `N` = Negativa / Down). |
| **24** | `ORIEN(N)` | `RESERVA` | `str` | Orientación o campo de reserva institucional. |

---

## 2. Ingesta de Acelerógrafos Digitales: `datos/digitales.csv`

Define la correspondencia entre las carpetas de adquisición de acelerógrafos digitales locales (Kinemetrics/Etna/Basalt) y el índice de estación en `estaciones.csv`.

* **Consumidores Clave**: [`modulos externos/consolidacion_mseed.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/consolidacion_mseed.py), [`modulos externos/Insercion de estaciones EVT.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Insercion%20de%20estaciones%20EVT.py).

### Estructura de Campos:

```text
Est. Digital;Numero;Habilitado
```

* **`Est. Digital`** (`str`): Subcarpeta donde el registrador almacena los datos (ej. `TENG\mseed`, `CHA01\mseed`, `CHA02\mseed`, `LAB01`, `LAB02`, `PRM01`, `TST1`).
* **`Numero`** (`int`): Índice de la estación en `estaciones.csv` (ej. `7` para `TENG`, `54` para `CHA01`, `53` para `CHA02`, `55` para `LAB01`).
* **`Habilitado`** (`int`): `1` = Procesar e integrar en la consolidación MiniSEED; `0` = Ignorar.

---

## 3. Telemetría Analógica Continua: `datos/analogicas.csv`

Lista el subconjunto de estaciones telemétricas analógicas continuas adquiridas en tiempo real por el sistema de digitalización central (64 sps continuos).

* **Consumidores Clave**: [`rsa_utilidades.extraccion()`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_utilidades.py), [`consolidacion_mseed.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/consolidacion_mseed.py).

### Estructura de Campos:

```text
ESTACION;NOMBRE;CODIGO
```

* **`ESTACION`** (`int`): Índice de estación en `estaciones.csv`.
* **`NOMBRE`** (`str`): Nombre de la estación analógica (ej. `LABRADO`, `CUSHINHUAYCO`, `CHANLUD`, `JAVIN`, `EL ROMERAL`, `UNIVERSIDAD VERTICAL`, `TENGUEL`, `IRQUIS`, `NERO`, `SOLDADOS`, `PORTETE`, `NABON`, `HUASCACHACA`, `SARAYUNGA`, `CHURUTE`).
* **`CODIGO`** (`str`): Código de 4 letras (`LABR`, `CUSH`, `CHAI`, `JAVI`, `ROME`, `UVER`, `CHA2`, `TENG`, `IRQS`, `NERO`, `SOLD`, `PORT`, `NABN`, `HUAS`, `SARA`, `CHUR`).

---

## 4. Analistas y Unidades de Trabajo: `datos/responsables.csv`

Mapea a los operadores y analistas de turno sismológico con sus unidades de red o rutas de procesamiento asignadas.

* **Consumidores Clave**: [`inicio.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio.py), [`rsa_procesamiento.archivos_fast()`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_procesamiento.py), [`procesamiento_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/procesamiento_integrado.py).

### Estructura de Campos:

```text
Responsable;Ruta_dia;Ruta_fast
```

* **`Responsable`** (`str`): Nombre del operador (ej. `RSA`, `Freddy Saquicela`, `Henry Bermeo`, `Remigio Guevara`).
* **`Ruta_dia`** (`str`): Unidad de red o directorio base para archivos `.sis`/`.fas` del analista (ej. `O:\`, `K:\`, `M:\`).
* **`Ruta_fast`** (`str`): Unidad de red o directorio para la ejecución de FastHypo/Hypocenter (ej. `P:\`, `L:\`, `N:\`).

---

## 5. Base de Datos Geográfica de Localidades: `datos/poblaciones.csv`

Base de datos geográfica con más de 1040 poblaciones, parroquias, cantones y ciudades de Ecuador. Se utiliza para generar la referencia geográfica automática del epicentro en catálogos y boletines.

* **Consumidor Clave**: [`rsa_utilidades.ubicacion(latitud, longitud)`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_utilidades.py#L491-L518).

### Estructura de Campos:

```text
x;Y;Nombre 2;Nombre;Tipo;Provincia;Canton
```

* **`x`** (`float`): Longitud geográfica en grados decimales (ej. `-78.9850`).
* **`Y`** (`float`): Latitud geográfica en grados decimales (ej. `-2.8540`).
* **`Nombre 2`** (`str`): Nombre alternativo o recinto / cabecera (opcional).
* **`Nombre`** (`str`): Nombre oficial de la localidad (ej. `Cuenca`, `Gualaceo`, `Paute`, `Santa Isabel`).
* **`Tipo`** (`str`): Jerarquía administrativa (`Ciudad`, `cantón`, `parroquia`).
* **`Provincia`** (`str`): Provincia (ej. `Azuay`, `Cañar`, `Guayas`, `Loja`, `Morona Santiago`).
* **`Canton`** (`str`): Cantón al que pertenece la parroquia.

#### Lógica de Referenciación Automática:
La función calcula la distancia euclidiana en kilómetros ($d \times 111.321$) a todas las poblaciones del archivo y genera textos descriptivos como:
* `"a 12 Km. de Gualaceo, cantón Gualaceo, Azuay"`
* `"a 8 Km. de la Ciudad de Cuenca, Azuay"`

---

## 6. Catálogo Cartográfico de Reportes: `datos/mapas/mapas.csv`

Define los recortes cartográficos vectoriales (archivos `.emf`) disponibles para incrustar en los boletines y reportes PDF de sismos individuales o acumulados.

* **Consumidores Clave**: [`rsa_pdf_graficos.mapa_configuracion()`](file:///c:/proyectos/rsa_sismologia/src/librerias/rsa_pdf_graficos.py#L434-L457), [`reporte_acumulado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_acumulado.py).

### Estructura de Campos:

```text
nombre;lat_min;lat_max;long_min;long_max;salto;estaciones
```

* **`nombre`** (`str`): Identificador del mapa cartográfico (ej. `Region`, `Ecuador`, `Austro`, `Facultad`, `Reportes`, `Chanlud`, `Labrado`, `Huascachaca`, `Soldados`, `Ocana`, `Nabon`, `Tenguel`, `Puyango`, `Puna`, `Pichacay`).
* **`lat_min` / `lat_max`** (`float`): Límites de latitud sur y norte del recuadro del mapa.
* **`long_min` / `long_max`** (`float`): Límites de longitud oeste y este del recuadro del mapa.
* **`salto`** (`float`): Intervalo de la cuadrícula o grilla de coordenadas en grados (ej. `1.0°`, `0.5°`, `0.1°`).
* **`estaciones`** (`str`): Lista separada por espacios de los índices de estaciones a graficar en ese mapa (ej. `0 1 2 53 54 69 70`).

#### Correspondencia con Archivos EMF:
Para cada entrada `nombre`, existen en `datos/mapas/` sus capas vectoriales por nivel de detalle:
* `{nombre}_0.emf`: Capa base / contorno.
* `{nombre}_1.emf`: Capa hidrográfica / fallas.
* `{nombre}_2.emf`: Capa de infraestructura / relieve.
