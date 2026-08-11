# CONTEXTO INTEGRAL DE MANTENIMIENTO

fases.py - Sistema de Detección y Marcado de Fases Sísmicas

Versión del documento: 1.0
Fecha: 2026-06-11
Propósito: Servir como referencia técnica única para mantenimiento, evolución y comprensión del sistema de marcado interactivo de fases sísmicas (P, S, Coda) sobre registros de estaciones.



## ÍNDICE

## VISIÓN GENERAL DEL SISTEMA

## ARQUITECTURA TÉCNICA DETALLADA

## MODELO DE DATOS COMPLETO

## FLUJOS DE EJECUCIÓN PRINCIPALES

## GESTIÓN DE FASES Y DETECCIÓN

## ESTRUCTURA DE DIRECTORIOS Y ARCHIVOS

## INTERFAZ DE USUARIO

## DEUDA TÉCNICA CATALOGADA

## PROTOCOLOS DE MODIFICACIÓN SEGURA

## ESTRATEGIA DE REFACTORIZACIÓN POR FASES

## DIAGRAMA DE FLUJO DE DATOS

## GLOSARIO DE TÉRMINOS TÉCNICOS



## 1. VISIÓN GENERAL DEL SISTEMA

### 1.1 Propósito fundamental

fases.py es el sistema de marcado interactivo de fases sísmicas del ecosistema RSA. Sus responsabilidades principales son:

Visualizar registros sísmicos de estaciones individuales para un evento específico

Detectar automáticamente fases (P, S, Coda) utilizando algoritmos sísmicos

Permitir marcado manual interactivo de fases mediante clics en el gráfico

Gestionar la paginación de estaciones (5 por página) para visualización eficiente

Persistir las fases detectadas/manuales en archivos JSON

Integrar información de aporte de estaciones (si la estación contribuye al evento)

### 1.2 Posición en el ecosistema

```text

[Evento extraído] → [PROCESAMIENTO] → [FASES (este script)] → [Archivo JSON]

↓                      ↓

- Datos MSEED          - Fases P detectadas

- Matriz eventos       - Fases S detectadas

- Parámetros           - Coda detectada

- Filtros por estación - Marcado manual

### 1.3 Flujo de trabajo típico

Usuario selecciona directorio de trabajo (o usa el predeterminado)

Selecciona una fecha en el calendario

Sistema carga todos los archivos .sis disponibles para esa fecha

Usuario selecciona un evento de la lista desplegable

Sistema muestra las estaciones que tienen datos para ese evento (5 por página)

Cada estación se grafica con color azul si aporta al evento, gris si no

Usuario puede hacer doble clic en una estación para abrir una ventana detallada

En la ventana detallada, puede ver las fases detectadas automáticamente y:

Agregar nuevas fases manualmente (clic)

Mover fases existentes (arrastrar)

Eliminar fases (clic derecho)

Las fases se guardan automáticamente al cerrar la ventana detallada



## 2. ARQUITECTURA TÉCNICA DETALLADA

### 2.1 Diagrama de clases simplificado

```python

┌─────────────────────────────────────────────────────────────────┐

│                      QMainWindow (PyQt5)                        │

└─────────────────────────────────────────────────────────────────┘

▲

│

┌─────────────────────────────────────────────────────────────────┐

│                      VentanaPrincipal                           │

├─────────────────────────────────────────────────────────────────┤

## │ ATRIBUTOS PRINCIPALES:                                          │

│   - directorio_trabajo: str                 # Ruta base "G:\Mi unidad\DIA"

│   - estaciones_por_pagina: int = 5          # Estaciones por página

│   - pagina_actual: int = 0                  # Página actual (0-index)

│   - archivos_mseed: List[str]               # Archivos MSEED del evento

│   - fases_detectadas: dict                  # {archivo: {fase: [tiempos]}}

│   - matriz_eventos: List[list]              # Datos del archivo CSV

│   - mapa_estaciones: dict                   # {código: (nombre, componente)}

│   - directorios: dict                       # Directorios del día

├─────────────────────────────────────────────────────────────────┤

## │ MÉTODOS CRÍTICOS:                                               │

│   + graficar_evento()                       # Dibuja estaciones paginadas

│   + cambio_de_fecha()                       # Carga datos de la fecha

│   + cargar_evento()                         # Carga evento seleccionado

│   + seleccionar_grafico_mseed()             # Abre ventana detallada

│   + anterior_pagina() / siguiente_pagina()  # Navegación

│   + guardar_evento()                        # Guarda fases en JSON

└─────────────────────────────────────────────────────────────────┘

│

│ crea

▼

┌─────────────────────────────────────────────────────────────────┐

│                      VentanaGrafico (QMainWindow)                │

├─────────────────────────────────────────────────────────────────┤

## │ ATRIBUTOS:                                                      │

│   - directorio_eventos: str                # Directorio con MSEEDs

│   - archivo_seleccionado: str              # Nombre del archivo

│   - gestor_fases: GestorFases              # Gestor de interacción

│   - fases_detectadas: dict                 # Referencia a dict padre

│   - parent: VentanaPrincipal               # Ventana padre

├─────────────────────────────────────────────────────────────────┤

## │ MÉTODOS:                                                        │

│   + graficar_mseed()                       # Grafica con fases

│   + closeEvent()                           # Actualiza fases en padre

└─────────────────────────────────────────────────────────────────┘

│

│ utiliza

▼

┌─────────────────────────────────────────────────────────────────┐

│                      GestorFases (externa)                       │

├─────────────────────────────────────────────────────────────────┤

## │ ATRIBUTOS:                                                      │

│   - fases: dict                           # {fase: [tiempos]}

│   - colores: dict                         # {fase: color}

│   - modo_edicion: str                     # 'add', 'move', None

│   - fase_seleccionada: str                # Fase en movimiento

│   - indice_tiempo: int                    # Índice del tiempo movido

├─────────────────────────────────────────────────────────────────┤

## │ MÉTODOS:                                                        │

│   + inicializar_fases(ax)                 # Dibuja líneas iniciales

│   + al_presionar(event, ax, canvas)       # Maneja clics

│   + al_mover(event, canvas)               # Maneja arrastre

│   + al_soltar(event)                      # Finaliza movimiento

│   + obtener_fases()                       # Retorna dict actualizado

└─────────────────────────────────────────────────────────────────┘

### 2.2 Flujo de datos entre componentes

```text

VentanaPrincipal

│

├── fecha → directorios → matriz_eventos (archivo_csv)

│                        → archivos_sis (combo_sis)

│

├── evento seleccionado → archivos_mseed (Directorio_eventos)

│                       → patron_mseed: "_{fecha}_{hora}.mseed"

│

├── graficar_evento() → por cada archivo_mseed:

│                       - Leer con obspy

│                       - Determinar color (azul si aporta, gris si no)

│                       - Detectar fases (detectar_y_marcar_fases)

│                       - Almacenar en fases_detectadas

│

└── seleccionar_grafico_mseed() → VentanaGrafico

│

├── graficar_mseed()

├── GestorFases (interacción)

└── closeEvent() → actualiza fases_detectadas



## 3. MODELO DE DATOS COMPLETO

### 3.1 Estructura de self.fases_detectadas

Tipo: Dict[str, Dict[str, List[float]]]

Formato:

```python

{

"BOB1_20240505_143022.mseed": {

## "P": [1.23, 4.56],

## "S": [2.34, 5.67],

"Coda": [10.0, 12.5]

},

"BOB2_20240505_143022.mseed": {

## "P": [1.45],

## "S": [2.78],

"Coda": []

}

}

Observaciones:

Las claves son los nombres de archivos MSEED

Cada archivo tiene un diccionario con fases

Cada fase tiene una lista de tiempos en segundos

El tiempo 0 se usa como marcador "no detectado" (no se dibuja)

### 3.2 Estructura de self.matriz_eventos

Tipo: List[list]
Origen: Archivo CSV del día (directorios['archivo_csv'])

Formato (por evento):

```python

[

[id_evento, nombre_archivo, tipo_evento,

"BOB1HHZ1 020406",   # Estación 0 (cadena de 12 caracteres)

"BOB2HHN1 000000",   # Estación 1

...                  # Hasta 101 estaciones

],

...

]

Formato de cadena de estación (12 caracteres):

```text

Posiciones:

0-3:  Código estación (ej: "BOB1")

4-6:  Componente (ej: "HHZ")

7:    Aporta ("0" o "1")

8-9:  Orden del filtro (ej: "02")

10-11: Frecuencia inf (ej: "04")

12-13: Frecuencia sup (ej: "06")

### 3.3 Estructura de self.mapa_estaciones

Tipo: Dict[str, tuple]
Origen: cargar_parametros() (desde librerias.metodos_gestion)

Formato:

```python

{

"BOB1": ("Estación Bobonaza", "1"),  # (nombre_completo, componente)

"BOB2": ("Estación Bobonaza 2", "2"),

"CHAB": ("Estación Chambo", "1"),

...

}

### 3.4 Estructura de self.directorios

Tipo: dict
Origen: obtener_directorios(archivo)

Claves principales:

```python

{

'Directorio_base': str,        # Ruta base del día

'Directorio_dia': str,         # Directorio con archivos .sis

'Directorio_eventos': str,     # Directorio con archivos .mseed

'Directorio_registros': str,   # Directorio con registros continuos

'archivo_csv': str,            # Ruta al CSV de eventos

'archivo_reporte': str,        # Ruta al reporte

'archivo_catalogo': str,       # Ruta al catálogo

'sufijo_mseed': str            # Sufijo para archivos MSEED

}

### 3.5 Archivo JSON de fases

Ubicación: Mismo directorio que el archivo .fas (con extensión .json)

Ejemplo (240505_143022.json):

```json

{

"BOB1_20240505_143022.mseed": {

## "P": [1.23, 4.56],

## "S": [2.34, 5.67],

"Coda": [10.0]

},

"BOB2_20240505_143022.mseed": {

## "P": [1.45],

## "S": [],

"Coda": []

}

}



## 4. FLUJOS DE EJECUCIÓN PRINCIPALES

### 4.1 Inicialización (__init__)

```python

## 1. Configurar ventana maximizada

## 2. Establecer directorio_trabajo = "G:\\Mi unidad\\DIA"  ← HARDCODEADO

## 3. Inicializar atributos:

- estaciones_por_pagina = 5

- pagina_actual = 0

- archivos_mseed = []

- fases_detectadas = {}

- gestor_fases = None

## 4. Cargar mapa_estaciones = cargar_parametros()

## 5. Llamar a init_ui()

### 4.2 Inicialización de UI (init_ui)

```python

## 1. Crear layout principal (HBox: izquierdo=UI, derecho=gráfico)

## 2. Cargar UI desde 'ui/marcar_fases.ui'

## 3. Conectar señales:

- boton_directorio.clicked → cambiar_directorio

- date_edit.dateChanged → cambio_de_fecha

- combo_sis.currentIndexChanged → cargar_evento

- checkbox_filtro.stateChanged → cargar_evento

- boton_salir.clicked → cerrar_ventana

- lista_mseed.itemDoubleClicked → seleccionar_grafico_mseed

- boton_anterior.clicked → anterior_pagina

- boton_siguiente.clicked → siguiente_pagina

## 4. Inicializar fecha actual en date_edit

## 5. Llamar a cambio_de_fecha()

### 4.3 Cambio de fecha (cambio_de_fecha)

```python

## 1. Reiniciar fases_detectadas = {}

## 2. Obtener fecha seleccionada

## 3. Construir archivo = directorio_trabajo + '/' + fecha.toString('yyMMdd') + '000000'

## 4. Obtener directorios (obtener_directorios)

## 5. Leer matriz_eventos = lectura_archivo(directorios['archivo_csv'])

## 6. Intentar:

a. Listar archivos .sis en Directorio_dia

b. Limpiar y poblar combo_sis

c. Si hay archivos, seleccionar primero y llamar a cargar_evento()

## 7. Si hay error (directorio no existe): mostrar mensaje y limpiar

### 4.4 Carga de evento (cargar_evento)

```python

## 1. Obtener archivo_sis seleccionado

## 2. Si no hay, retornar

## 3. Extraer hora del archivo .sis (parte después de '_' antes de '.')

## 4. Construir patrón_mseed = f"_{fecha_seleccionada:%Y%m%d}_{hora}.mseed"

## 5. Listar archivos MSEED en Directorio_eventos que coincidan con patrón

## 6. Actualizar lista_mseed (con nombres completos si están en mapa_estaciones)

## 7. Llamar a graficar_evento()

### 4.5 Graficar evento paginado (graficar_evento)

```python

## 1. Limpiar figura (figura.clear())

## 2. Calcular inicio/fin según página_actual

## 3. Para cada archivo MSEED en el rango:

a. Leer con obspy.read()

b. Extraer nombre_corto (antes de '_')

c. Obtener componente del mapa_estaciones

d. Seleccionar trace según componente (índice = componente - 1)

e. Determinar color_linea:

- Por defecto "lightgray"

- Buscar en matriz_eventos si la estación aporta (carácter posición 7 = '1')

- Si aporta: color_linea = "blue"

f. Si checkbox_filtro está marcado: aplicar filtro (actualmente comentado)

g. Crear subplot y graficar

h. Almacenar eje en self.axes[archivo]

i. Si archivo no está en fases_detectadas:

- Llamar a detectar_y_marcar_fases(tr)

- Almacenar en fases_detectadas

## 4. Ajustar layout y dibujar

### 4.6 Selección de estación (seleccionar_grafico_mseed)

```python

## 1. Extraer archivo_seleccionado del texto del item (entre paréntesis)

## 2. Obtener fases_estacion = fases_detectadas[archivo_seleccionado]

## 3. Crear gestor_fases = GestorFases(fases_estacion)

## 4. Crear VentanaGrafico con:

- directorio_eventos

- archivo_seleccionado

- fecha

- fases_detectadas (referencia)

- gestor_fases

- self (como parent)

## 5. Mostrar ventana

### 4.7 Navegación de páginas

```python

def anterior_pagina(self):

if self.pagina_actual > 0:

self.pagina_actual -= 1

self.graficar_evento()



def siguiente_pagina(self):

max_pagina = (len(self.archivos_mseed) - 1) // self.estaciones_por_pagina

if self.pagina_actual < max_pagina:

self.pagina_actual += 1

self.graficar_evento()

### 4.8 Guardado de fases (guardar_evento)

```python

## 1. Verificar que hay fases_detectadas

## 2. Verificar que archivo_json está definido

## 3. Guardar fases_detectadas en archivo JSON con json.dump()

## 4. Manejar excepciones

⚠️ NOTA CRÍTICA: guardar_evento() está definido pero nunca se conecta a ningún botón en la UI actual.

### 4.9 Ventana detallada (VentanaGrafico)

```python

def graficar_mseed(self):

## 1. Limpiar figura

## 2. Leer archivo MSEED con obspy

## 3. Crear subplot y graficar

## 4. Obtener fases_estacion de fases_detectadas

## 5. Dibujar líneas verticales para cada fase (colores según gestor)

## 6. Inicializar gestor_fases con el axes

## 7. Conectar eventos de matplotlib:

- button_press_event → gestor.al_presionar

- button_release_event → gestor.al_soltar

- motion_notify_event → gestor.al_mover



def closeEvent(self, event):

fases_actualizadas = self.gestor_fases.obtener_fases()

self.parent.fases_detectadas[self.archivo_seleccionado] = fases_actualizadas

self.parent.graficar_evento()  # Refrescar gráfico padre

super().closeEvent(event)



## 5. GESTIÓN DE FASES Y DETECCIÓN

### 5.1 Detección automática de fases

Función: detectar_y_marcar_fases(tr) (desde librerias.metodos_sismicos)

Entrada: Trace de ObsPy con datos sísmicos
Salida: Diccionario {"P": [tiempos], "S": [tiempos], "Coda": [tiempos]}

Algoritmo esperado (no implementado en este script):

Detección de fase P: cambio abrupto en amplitud, frecuencias altas

Detección de fase S: mayores amplitudes, frecuencias más bajas

Detección de coda: decaimiento exponencial después de S

### 5.2 Gestor de fases interactivo (GestorFases)

Funcionalidades:

Colores de fases:

```python

self.gestor_fases.colores = {

"P": "red",

"S": "blue",

"Coda": "green"

}

### 5.3 Estructura de GestorFases (externa)

Atributos esperados:

```python

class GestorFases:

def __init__(self, fases):

self.fases = fases  # {"P": [1.23, 4.56], "S": [2.34], "Coda": []}

self.colores = {"P": "red", "S": "blue", "Coda": "green"}

self.modo_edicion = None  # 'add', 'move'

self.fase_seleccionada = None

self.indice_tiempo = None

self.lineas = {}  # {fase: [líneas matplotlib]}



def inicializar_fases(self, ax):

# Dibuja líneas para cada fase



def al_presionar(self, event, ax, canvas):

# Maneja clics: agregar, seleccionar, eliminar



def al_mover(self, event, canvas):

# Mueve línea si está en modo 'move'



def al_soltar(self, event):

# Finaliza movimiento



def obtener_fases(self):

# Retorna dict actualizado

return self.fases



## 6. ESTRUCTURA DE DIRECTORIOS Y ARCHIVOS

### 6.1 Estructura esperada

```text

G:\Mi unidad\DIA\                      ← directorio_trabajo (HARDCODEADO)

│

├── {fecha:yyMMdd}000000\              ← Directorio del día (ej: 240505000000)

│   ├── {fecha:yyMMdd}000000_cat.csv   ← Catálogo

│   ├── {fecha:yyMMdd}000000_rep.csv   ← Reporte de eventos

│   ├── {fecha:yyMMdd}000000.csv       ← Matriz de eventos (archivo_csv)

│   │

│   ├── eventos\                       ← Directorio_eventos

│   │   ├── BOB1_20240505_143022.mseed

│   │   ├── BOB2_20240505_143022.mseed

│   │   └── ...

│   │

│   ├── registro\                      ← Directorio_registros

│   │   └── ...

│   │

│   └── reportes\                      ← Directorio_reportes

│       └── ...

│

├── 240505_143022.sis                  ← Archivos .sis (en Directorio_dia)

├── 240505_143022.fas                  ← Archivo .fas (mismo nombre)

├── 240505_143022.json                 ← Archivo JSON de fases

└── ...

### 6.2 Patrones de nombres de archivos

### 6.3 Ruta del archivo JSON

Construcción (en cargar_evento):

```python

self.archivo_fas = self.directorios['archivo_csv'] + '/' + self.archivo_sis[:-3] + 'fas'

self.archivo_json = self.archivo_fas[:-3] + 'json'

⚠️ PROBLEMA: self.directorios['archivo_csv'] es un archivo, no un directorio. Debería ser:

```python

self.archivo_json = os.path.join(self.directorios['Directorio_dia'],

self.archivo_sis[:-3] + 'json')



## 7. INTERFAZ DE USUARIO

### 7.1 Widgets del archivo marcar_fases.ui

### 7.2 Ventana de gráfico detallado (VentanaGrafico)

Características:

Tamaño fijo: 800x600

Toolbar de matplotlib (zoom, pan, guardar)

Líneas verticales para cada fase (colores: rojo=P, azul=S, verde=Coda)

Interacción: clic para agregar, arrastrar para mover, clic derecho para eliminar

Al cerrar, actualiza fases en ventana padre y refresca gráfico

### 7.3 Flujo de interacción del usuario

```text

## 1. Seleccionar fecha → calendario

## 2. Seleccionar evento → combo_sis

## 3. Ver estaciones → lista_mseed (5 por página)

## 4. Hacer doble clic en estación → ventana detallada

## 5. En ventana detallada:

- Ver fases automáticas

- Clic izquierdo → agregar fase P

- Arrastrar línea → mover fase

- Clic derecho → eliminar fase

## 6. Cerrar ventana → fases guardadas en memoria

## 7. (Opcional) Cambiar página → ver más estaciones



## 8. DEUDA TÉCNICA CATALOGADA

### 8.1 Deuda crítica (requiere atención inmediata)

Código de corrección inmediata:

```python

# D-F01: Permitir configuración dinámica

def __init__(self):

# ...

self.directorio_trabajo = os.environ.get('RSA_DIRECTORIO', "G:\\Mi unidad\\DIA")



# D-F02: Conectar botón de guardado (agregar a UI o crear)

# Si no hay botón en UI, agregar uno:

self.boton_guardar = QPushButton("Guardar Fases")

self.boton_guardar.clicked.connect(self.guardar_evento)



# D-F03: Corregir ruta del JSON

def cargar_evento(self):

# ...

self.archivo_json = os.path.join(self.directorios['Directorio_dia'],

self.archivo_sis.replace('.sis', '.json'))



# D-F04: Implementar filtro

if self.checkbox_filtro.isChecked():

tr.filter('bandpass', freqmin=II, freqmax=SS, corners=OO)

### 8.2 Deuda alta (resolver en 3 meses)

Código para D-F09 (cargar JSON existente):

```python

def cargar_evento(self):

# ... código existente ...



# Cargar fases guardadas si existen

archivo_json = os.path.join(self.directorios['Directorio_dia'],

self.archivo_sis.replace('.sis', '.json'))

if os.path.exists(archivo_json):

with open(archivo_json, 'r', encoding='utf-8') as f:

fases_guardadas = json.load(f)

# Fusionar con detección automática (priorizar guardadas)

for archivo, fases in fases_guardadas.items():

if archivo in self.fases_detectadas:

self.fases_detectadas[archivo].update(fases)

else:

self.fases_detectadas[archivo] = fases

### 8.3 Deuda media (refactorización deseable)

### 8.4 Deuda baja (nice-to-have)



## 9. PROTOCOLOS DE MODIFICACIÓN SEGURA

### 9.1 Reglas de oro

NUNCA hardcodear rutas absolutas (usar os.path.join y variables configurables)

SIEMPRE verificar existencia de archivos antes de intentar leer

RESPETAR el formato del JSON de fases al guardar/cargar

MANTENER la paginación consistente (actualizar después de cambios)

NO modificar fases_detectadas directamente sin actualizar la UI

### 9.2 Protocolo para agregar nuevo tipo de fase

```python

# 1. Modificar GestorFases (en librerias.gestor_fases)

class GestorFases:

def __init__(self, fases):

self.colores = {

"P": "red",

"S": "blue",

"Coda": "green",

"NUEVA_FASE": "purple"  # Agregar color

}

# Asegurar que la fase existe en fases

if "NUEVA_FASE" not in self.fases:

self.fases["NUEVA_FASE"] = []



# 2. Modificar detectar_y_marcar_fases para detectar nueva fase

# 3. Actualizar la UI para permitir selección de fase al agregar

### 9.3 Protocolo para modificar número de estaciones por página

```python

# 1. Cambiar constante

self.estaciones_por_pagina = 6  # Por ejemplo



# 2. Asegurar que la paginación se recalcula

def cambiar_estaciones_por_pagina(self, nuevo_valor):

self.estaciones_por_pagina = nuevo_valor

self.pagina_actual = 0

self.graficar_evento()

### 9.4 Protocolo para agregar carga/guardado automático

```python

# En cargar_evento: cargar JSON si existe

def cargar_evento(self):

# ... código existente ...

self._cargar_fases_guardadas()



# En seleccionar_grafico_mseed: guardar automáticamente al cerrar

def seleccionar_grafico_mseed(self, item):

# ... código existente ...

nueva_ventana.show()

nueva_ventana.destroyed.connect(self._guardar_fases_si_cambian)



def _guardar_fases_si_cambian(self):

if hasattr(self, 'archivo_json') and self.archivo_json:

with open(self.archivo_json, 'w', encoding='utf-8') as f:

json.dump(self.fases_detectadas, f, indent=4)



## 10. ESTRATEGIA DE REFACTORIZACIÓN POR FASES

### 10.1 Fase 0: Corrección inmediata (1 día)

### 10.2 Fase 1: Robustez y UX (1 semana)

Objetivo: Mejorar experiencia de usuario y prevenir pérdida de datos

```python

# 1. Agregar barra de progreso mientras carga

def graficar_evento(self):

self.statusBar().showMessage("Cargando estaciones...")

QApplication.processEvents()

# ... procesamiento ...

self.statusBar().showMessage("Listo")



# 2. Confirmar salida si hay cambios sin guardar

def closeEvent(self, event):

if self.hay_cambios_sin_guardar():

reply = QMessageBox.question(self, "Guardar cambios",

"¿Guardar fases antes de salir?",

QMessageBox.Yes | QMessageBox.No)

if reply == QMessageBox.Yes:

self.guardar_evento()

event.accept()



# 3. Implementar filtro pasa banda funcional

def aplicar_filtro(self, tr, orden, fmin, fmax):

if orden and fmin and fmax:

return tr.filter('bandpass', freqmin=fmin, freqmax=fmax, corners=orden)

return tr

### 10.3 Fase 2: Refactorización de paginación (1 semana)

Objetivo: Centralizar lógica de paginación y mejorar rendimiento

```python

class PaginadorEstaciones:

def __init__(self, total_items, items_por_pagina=5):

self.total_items = total_items

self.items_por_pagina = items_por_pagina

self.pagina_actual = 0



@property

def total_paginas(self):

return (self.total_items - 1) // self.items_por_pagina + 1 if self.total_items > 0 else 1



@property

def inicio(self):

return self.pagina_actual * self.items_por_pagina



@property

def fin(self):

return min(self.inicio + self.items_por_pagina, self.total_items)



def hay_anterior(self):

return self.pagina_actual > 0



def hay_siguiente(self):

return self.pagina_actual < self.total_paginas - 1



def anterior(self):

if self.hay_anterior():

self.pagina_actual -= 1

return True

return False



def siguiente(self):

if self.hay_siguiente():

self.pagina_actual += 1

return True

return False

### 10.4 Fase 3: Separación de responsabilidades (2 semanas)

Objetivo: Extraer lógica de visualización a clase separada

```python

class GraficadorEventos:

"""Responsable de graficar estaciones paginadas"""



def __init__(self, figura, canvas, estaciones_por_pagina=5):

self.figura = figura

self.canvas = canvas

self.estaciones_por_pagina = estaciones_por_pagina

self.paginador = None



def graficar(self, archivos_mseed, directorio_eventos, matriz_eventos,

mapa_estaciones, checkbox_filtro, fases_detectadas):

# Lógica de graficado extraída de VentanaPrincipal

pass



class CargadorEventos:

"""Responsable de cargar datos de eventos"""



def cargar_directorios(self, fecha, directorio_trabajo):

# Lógica de obtención de directorios

pass



def cargar_matriz_eventos(self, directorios):

# Lógica de carga de CSV

pass



def listar_archivos_sis(self, directorios):

# Lógica de listado de .sis

pass



def listar_archivos_mseed(self, directorios, fecha, hora):

# Lógica de listado de .mseed

pass



## 11. DIAGRAMA DE FLUJO DE DATOS

```text

┌─────────────────────────────────────────────────────────────────────────────┐

## │                           USUARIO                                            │

│                                │                                            │

│                    Selecciona fecha y evento                                │

└────────────────────────────────┬────────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────────────┐

│                    cambio_de_fecha() + cargar_evento()                       │

│  ┌─────────────────────────────────────────────────────────────────────┐    │

│  │ 1. Obtener directorios del día                                       │    │

│  │ 2. Leer matriz_eventos (archivo_csv)                                 │    │

│  │ 3. Listar archivos .sis en Directorio_dia                            │    │

│  │ 4. Para evento seleccionado: listar archivos .mseed en eventos/      │    │

│  │ 5. Construir patron: "_{fecha}_{hora}.mseed"                         │    │

│  └─────────────────────────────────────────────────────────────────────┘    │

└─────────────────────────────────────────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────────────┐

│                         graficar_evento()                                    │

│  ┌─────────────────────────────────────────────────────────────────────┐    │

│  │ Por cada archivo MSEED en página actual:                             │    │

│  │   1. Leer con obspy.read()                                           │    │

│  │   2. Determinar componente (mapa_estaciones)                         │    │

│  │   3. Determinar color (matriz_eventos: posición 7 = '1'? azul: gris) │    │

│  │   4. Detectar fases (detectar_y_marcar_fases) → fases_detectadas     │    │

│  │   5. Graficar en subplot                                             │    │

│  └─────────────────────────────────────────────────────────────────────┘    │

└─────────────────────────────────────────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────────────┐

│                    Doble clic en estación (lista_mseed)                      │

└────────────────────────────────┬────────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────────────┐

│                    seleccionar_grafico_mseed()                               │

│  ┌─────────────────────────────────────────────────────────────────────┐    │

│  │ 1. Extraer archivo_seleccionado                                      │    │

│  │ 2. Obtener fases_estacion = fases_detectadas[archivo]                │    │

│  │ 3. Crear GestorFases(fases_estacion)                                 │    │

│  │ 4. Crear VentanaGrafico(...)                                         │    │

│  └─────────────────────────────────────────────────────────────────────┘    │

└─────────────────────────────────────────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────────────┐

│                    VentanaGrafico.graficar_mseed()                           │

│  ┌─────────────────────────────────────────────────────────────────────┐    │

│  │ 1. Leer MSEED completo                                               │    │

│  │ 2. Graficar trace                                                    │    │

│  │ 3. Dibujar líneas de fases (colores por tipo)                        │    │

│  │ 4. Conectar eventos de matplotlib (clic, arrastre, etc.)             │    │

│  └─────────────────────────────────────────────────────────────────────┘    │

└─────────────────────────────────────────────────────────────────────────────┘

│

▼ (usuario interactúa)

┌─────────────────────────────────────────────────────────────────────────────┐

│                    GestorFases (eventos de matplotlib)                       │

│  ┌─────────────────────────────────────────────────────────────────────┐    │

│  │ - Clic izquierdo: agrega fase P                                      │    │

│  │ - Clic en línea: selecciona fase para mover                          │    │

│  │ - Arrastre: mueve fase seleccionada                                  │    │

│  │ - Clic derecho: elimina fase más cercana                             │    │

│  └─────────────────────────────────────────────────────────────────────┘    │

└─────────────────────────────────────────────────────────────────────────────┘

│

▼ (cierra ventana)

┌─────────────────────────────────────────────────────────────────────────────┐

│                    VentanaGrafico.closeEvent()                               │

│  ┌─────────────────────────────────────────────────────────────────────┐    │

│  │ 1. fases_actualizadas = gestor_fases.obtener_fases()                 │    │

│  │ 2. parent.fases_detectadas[archivo] = fases_actualizadas             │    │

│  │ 3. parent.graficar_evento()  # Refrescar gráfico                     │    │

│  └─────────────────────────────────────────────────────────────────────┘    │

└─────────────────────────────────────────────────────────────────────────────┘



## 12. GLOSARIO DE TÉRMINOS TÉCNICOS



## 13. APÉNDICE: MAPA COMPLETO DE MÉTODOS

```python

VentanaPrincipal

├── __init__

├── init_ui

├── cerrar_ventana

├── graficar_evento              ← PRINCIPAL (visualización paginada)

├── cambiar_directorio

├── cambio_de_fecha              ← Carga datos de fecha

├── cargar_evento                ← Carga evento específico

├── seleccionar_grafico_mseed    ← Abre ventana detallada

├── anterior_pagina

├── siguiente_pagina

├── guardar_evento               ← ⚠️ NO CONECTADO

└── (closeEvent no definido)



VentanaGrafico

├── __init__

├── init_ui

├── graficar_mseed

└── closeEvent                   ← Actualiza fases en padre



# Funciones externas (importadas)

- detectar_y_marcar_fases()      # desde metodos_sismicos

- cargar_parametros()            # desde metodos_gestion

- obtener_directorios()          # desde metodos_gestion

- lectura_archivo()              # desde metodos_rsa

- GestorFases                    # desde gestor_fases



## 14. REGISTRO DE CAMBIOS



## CONCLUSIÓN

Este documento constituye el contexto integral para fases.py. Contiene:

✅ Arquitectura completa con diagramas de clases

✅ Modelo de datos detallado (fases_detectadas, matriz_eventos, mapa_estaciones)

✅ Flujos de ejecución documentados línea por línea

✅ Gestión de fases y detección explicada

✅ Estructura de directorios y archivos

✅ Deuda técnica catalogada por prioridad (18 items)

✅ Estrategia de refactorización por fases (4 fases)

✅ Protocolos de modificación segura

✅ Diagrama de flujo de datos

Puntos críticos a recordar:

⚠️ directorio_trabajo está hardcodeado a "G:\Mi unidad\DIA"

⚠️ guardar_evento() está definido pero nunca se llama

⚠️ archivo_json se construye incorrectamente (usa archivo_csv como directorio)

⚠️ El filtro pasa banda está comentado (no funciona)

⚠️ No se cargan fases guardadas previamente al abrir un evento

Para el mantenimiento a largo plazo, este documento debe actualizarse con cada cambio significativo. El script es crítico para el análisis detallado de fases sísmicas y su correcto funcionamiento es esencial para la calidad del procesamiento sísmico.



<!-- Conversión estructurada para mantenimiento y repositorio -->
