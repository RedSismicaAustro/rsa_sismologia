# CONTEXTO INTEGRAL DE MANTENIMIENTO

gestor_fases.py - Gestor Interactivo de Fases Sísmicas

Versión del documento: 1.0
Fecha: 2026-06-11
Propósito: Servir como referencia técnica única para mantenimiento, evolución y comprensión del gestor de fases sísmicas que permite interacción con gráficos de matplotlib.



ÍNDICE

VISIÓN GENERAL DEL SISTEMA

ARQUITECTURA TÉCNICA DETALLADA

MODELO DE DATOS COMPLETO

FLUJOS DE EJECUCIÓN PRINCIPALES

INTERACCIÓN CON MATPLOTLIB

RELACIÓN CON OTROS MÓDULOS

DEUDA TÉCNICA CATALOGADA

PROTOCOLOS DE MODIFICACIÓN SEGURA

ESTRATEGIA DE REFACTORIZACIÓN

GLOSARIO DE TÉRMINOS



## 1. VISIÓN GENERAL DEL SISTEMA

### 1.1 Propósito fundamental

gestor_fases.py implementa la clase GestorFases, que proporciona interactividad en tiempo real sobre gráficos de matplotlib para el marcado de fases sísmicas. Permite:

Visualizar líneas verticales representando fases P, S y Coda sobre un registro sísmico

Agregar nuevas fases mediante doble clic (en orden: P → S → Coda)

Mover fases existentes mediante arrastre (clic y arrastre)

Eliminar fases mediante doble clic sobre una línea existente

Gestionar el estado de las fases durante la interacción del usuario

### 1.2 Contexto de uso

Esta librería es utilizada exclusivamente por fases.py (VentanaGrafico) para proporcionar una interfaz interactiva de marcado de fases. Es un ejemplo de buena separación de responsabilidades: la lógica de interacción está separada de la visualización.

### 1.3 Flujo de trabajo típico

text

Usuario abre ventana detallada de estación

│

▼

GestorFases.inicializar_fases(ax) → Dibuja líneas existentes

│

▼

Conectar eventos de matplotlib:

- button_press_event → al_presionar

- button_release_event → al_soltar

- motion_notify_event → al_mover

│

▼

Usuario interactúa:

- Doble clic en espacio vacío → Agrega nueva fase (P, luego S, luego Coda)

- Clic y arrastre sobre línea → Mueve fase

- Doble clic sobre línea → Elimina fase (asigna 0.0)

│

▼

Al cerrar: GestorFases.obtener_fases() → Retorna diccionario actualizado



## 2. ARQUITECTURA TÉCNICA DETALLADA

### 2.1 Diagrama de clases

python

┌─────────────────────────────────────────────────────────────────┐

│                        GestorFases                              │

├─────────────────────────────────────────────────────────────────┤

│ ATRIBUTOS:                                                      │

│   - fases: Dict[str, List[float]]     # Fases almacenadas      │

│   - colores: Dict[str, str]           # Colores por tipo       │

│   - lineas: Dict[str, Any]            # Líneas matplotlib      │

│   - textos: Dict[str, Any]            # Textos (no usado)      │

│   - linea_seleccionada: Any           # Línea en movimiento    │

│   - tipo_fase: str                    # Tipo de fase movida    │

│   - arrastrando: bool                 # Flag de arrastre       │

│   - texto_info: Any                   # Info (no usado)        │

├─────────────────────────────────────────────────────────────────┤

│ MÉTODOS:                                                        │

│   + __init__(fases_detectadas)                                  │

│   + al_presionar(evento, ax, canvas)   # Clic/arrastre inicio  │

│   + al_soltar(evento)                  # Fin de arrastre       │

│   + al_mover(evento, canvas)           # Arrastre              │

│   + doble_click(evento, ax, canvas)    # Agregar/eliminar      │

│   + encontrar_fase_mas_cercana(x, ax)  # Busca fase cerca      │

│   + eliminar_fase_por_tipo(tipo, ax, canvas)                   │

│   + obtener_tipo_fase()                # Próxima fase a agregar│

│   + inicializar_fases(ax)              # Dibuja fases iniciales│

│   + obtener_fases()                    # Retorna dict actual   │

└─────────────────────────────────────────────────────────────────┘

### 2.2 Estados de interacción

text

┌─────────────────────────────────────────────────────────┐

│                     ESTADO INICIAL                      │

│              arrastrando = False                        │

│              linea_seleccionada = None                  │

└─────────────────────────────────────────────────────────┘

│

▼

button_press_event

│

┌───────────────┴───────────────┐

│                               │

▼                               ▼

┌─────────────────┐             ┌─────────────────┐

│ Clic en línea   │             │ Clic en vacío   │

│ arrastrando=True│             │ arrastrando=False│

│ línea_selecc.=  │             └─────────────────┘

│ línea           │                      │

└────────┬────────┘                      │

│                               │

▼                               ▼

motion_notify_event              doble_click? (en al_presionar)

│                               │

▼                               ▼

┌─────────────────┐             ┌─────────────────┐

│ Mover línea     │             │ Agregar/Eliminar│

│ actualizar xdata│             │ fase            │

└────────┬────────┘             └─────────────────┘

│

▼

button_release_event

│

▼

┌─────────────────┐

│ arrastrando=False│

│ linea_selecc=None│

└─────────────────┘



## 3. MODELO DE DATOS COMPLETO

### 3.1 Estructura de self.fases

Tipo: Dict[str, List[float]]

python

{

"P": [tiempo_p],      # Lista con un solo valor (tiempo en segundos)

"S": [tiempo_s],      # Lista con un solo valor

"Coda": [tiempo_coda] # Lista con un solo valor

}

Valores especiales:

[0.0] - Fase no detectada/eliminada

[valor > 0] - Fase presente en ese tiempo (segundos)

⚠️ NOTA CRÍTICA: Cada fase solo puede tener un solo tiempo (lista de 1 elemento). No soporta múltiples marcaciones por tipo de fase.

### 3.2 Estructura de self.colores

python

{

"P": "red",

"S": "blue",

"Coda": "green"

}

### 3.3 Parámetro de entrada fases_detectadas

python

# Valor por defecto

fases_detectadas = {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}



# Ejemplo con valores reales

fases_detectadas = {'P': [1.23], 'S': [2.34], 'Coda': [10.0]}

### 3.4 Salida de obtener_fases()

Mismo formato que entrada: Dict[str, List[float]]



## 4. FLUJOS DE EJECUCIÓN PRINCIPALES

### 4.1 Inicialización (__init__)

python

def __init__(self, fases_detectadas=None):

self.linea_seleccionada = None

self.arrastrando = False

self.fases = fases_detectadas if fases_detectadas else {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}

self.colores = {'P': 'red', 'S': 'blue', 'Coda': 'green'}

self.lineas = {'P': None, 'S': None, 'Coda': None}

self.textos = {'P': None, 'S': None, 'Coda': None}

self.texto_info = None

Atributos internos:

### 4.2 Manejo de presión de mouse (al_presionar)

python

def al_presionar(self, evento, ax, canvas):

if not evento.dblclick:  # Clic simple

x = evento.xdata

tipo_fase = self.encontrar_fase_mas_cercana(x, ax)

if tipo_fase is not None:

# Iniciar arrastre

self.linea_seleccionada = self.lineas[tipo_fase]

self.arrastrando = True

self.tipo_fase = tipo_fase

else:  # Doble clic

self.doble_click(evento, ax, canvas)

canvas.draw()

Comportamiento:

Clic simple cerca de línea → Inicia modo arrastre

Clic simple en vacío → No hace nada

Doble clic → Llama a doble_click (agregar/eliminar)

### 4.3 Manejo de arrastre (al_mover)

python

def al_mover(self, evento, canvas):

if self.linea_seleccionada is not None and self.arrastrando:

if evento.inaxes == canvas.figure.gca():

x = evento.xdata

self.linea_seleccionada.set_xdata([x, x])

self.fases[self.tipo_fase][0] = x

canvas.draw()

⚠️ PROBLEMA: No hay límite inferior/verificación de que x sea válido (puede ser None si el mouse sale del gráfico).

### 4.4 Manejo de doble clic (doble_click)

python

def doble_click(self, evento, ax, canvas):

x = evento.xdata

tipo_fase = self.encontrar_fase_mas_cercana(x, ax)

if tipo_fase is not None:

# Eliminar fase existente

self.eliminar_fase_por_tipo(tipo_fase, ax, canvas)

self.fases[tipo_fase] = [0.0]

else:

# Agregar nueva fase

tipo_fase = self.obtener_tipo_fase()

if tipo_fase:

self.fases[tipo_fase][0] = x

self.lineas[tipo_fase] = ax.axvline(x, color=self.colores[tipo_fase],

linestyle='--', label=f'Fase {tipo_fase}')

canvas.draw()

Orden de agregación: P → S → Coda (definido por obtener_tipo_fase)

### 4.5 Búsqueda de fase cercana (encontrar_fase_mas_cercana)

python

def encontrar_fase_mas_cercana(self, x, ax):

tipo_fase_mas_cercana = None

for tipo_fase in ['P', 'S', 'Coda']:

if self.fases[tipo_fase] and self.fases[tipo_fase][0] > 0:

tiempo = self.fases[tipo_fase][0]

x_min, x_max = ax.get_xlim()

distancia_minima = (x_max - x_min) * 0.01  # 1% del rango total

distancia = abs(tiempo - x)

if distancia < distancia_minima:

tipo_fase_mas_cercana = tipo_fase

return tipo_fase_mas_cercana

Margen de tolerancia: 1% del ancho total del gráfico

### 4.6 Determinación de próxima fase a agregar (obtener_tipo_fase)

python

def obtener_tipo_fase(self):

if self.fases['P'] == [0.0]:

return 'P'

elif self.fases['S'] == [0.0]:

return 'S'

else:

return 'Coda'

Orden fijo: Primero P, luego S, luego Coda (incluso si Coda ya tiene valor, permite sobrescribir)

### 4.7 Inicialización de fases (inicializar_fases)

python

def inicializar_fases(self, ax):

for tipo_fase in ['P', 'S', 'Coda']:

if self.fases[tipo_fase] and self.fases[tipo_fase][0] > 0:

tiempo = self.fases[tipo_fase][0]

if self.lineas[tipo_fase] is not None:

self.lineas[tipo_fase].remove()

self.lineas[tipo_fase] = ax.axvline(tiempo, color=self.colores[tipo_fase],

linestyle='--')



## 5. INTERACCIÓN CON MATPLOTLIB

### 5.1 Eventos de matplotlib utilizados

### 5.2 Conexión típica (desde fases.py)

python

self.canvas.mpl_connect('button_press_event',

lambda event: self.gestor_fases.al_presionar(event, ax, self.canvas))

self.canvas.mpl_connect('button_release_event',

self.gestor_fases.al_soltar)

self.canvas.mpl_connect('motion_notify_event',

lambda event: self.gestor_fases.al_mover(event, self.canvas))

### 5.3 Métodos de matplotlib utilizados



## 6. RELACIÓN CON OTROS MÓDULOS

### 6.1 Dependencias (imports)

python

import json          # No utilizado en esta clase (posiblemente relicto)

import os            # No utilizado en esta clase

from obspy.signal.trigger import classic_sta_lta, trigger_onset  # ¡NO UTILIZADOS!

⚠️ PROBLEMA CRÍTICO: Se importan classic_sta_lta y trigger_onset pero nunca se usan. Son dependencias muertas que aumentan el tiempo de carga.

### 6.2 Módulos consumidores

### 6.3 Diagrama de dependencias

text

┌─────────────────┐

│   gestor_fases  │

└────────┬────────┘

│ (importa pero no usa)

┌───────────────────┼───────────────────┐

▼                   ▼                   ▼

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐

│     obspy       │ │      json       │ │       os        │

│ (signal.trigger)│ │                 │ │                 │

└─────────────────┘ └─────────────────┘ └─────────────────┘

│

▼ (no usado)

┌─────────────────┐

│  fases.py       │ ← Único consumidor real

└─────────────────┘



## 7. DEUDA TÉCNICA CATALOGADA

### 7.1 Deuda crítica

Corrección inmediata para G-01:

python

# Eliminar imports no utilizados

# import json

# import os

# from obspy.signal.trigger import classic_sta_lta, trigger_onset



class GestorFases:

# ...

Corrección para G-03:

python

def al_mover(self, evento, canvas):

if self.linea_seleccionada is not None and self.arrastrando:

if evento.inaxes == canvas.figure.gca() and evento.xdata is not None:

x = evento.xdata

# Opcional: limitar x al rango válido

x_min, x_max = canvas.figure.gca().get_xlim()

x = max(x_min, min(x_max, x))

self.linea_seleccionada.set_xdata([x, x])

self.fases[self.tipo_fase][0] = x

canvas.draw()

### 7.2 Deuda alta

### 7.3 Deuda media

### 7.4 Deuda baja



## 8. PROTOCOLOS DE MODIFICACIÓN SEGURA

### 8.1 Reglas de oro

NUNCA modificar self.fases directamente sin actualizar self.lineas

SIEMPRE llamar a canvas.draw() después de cambios visuales

VERIFICAR que evento.xdata no sea None antes de usar

RESPETAR el formato de self.fases (lista de 1 elemento)

### 8.2 Protocolo para agregar nuevo tipo de fase

python

# 1. Agregar a estructuras existentes

def __init__(self, fases_detectadas=None):

# ...

self.colores['NUEVA_FASE'] = 'purple'

self.lineas['NUEVA_FASE'] = None

self.textos['NUEVA_FASE'] = None



if fases_detectadas and 'NUEVA_FASE' in fases_detectadas:

self.fases['NUEVA_FASE'] = fases_detectadas['NUEVA_FASE']

else:

self.fases['NUEVA_FASE'] = [0.0]



# 2. Actualizar métodos que iteran sobre fases

def inicializar_fases(self, ax):

for tipo_fase in ['P', 'S', 'Coda', 'NUEVA_FASE']:

# ... código existente



def encontrar_fase_mas_cercana(self, x, ax):

for tipo_fase in ['P', 'S', 'Coda', 'NUEVA_FASE']:

# ... código existente



# 3. Actualizar orden de agregación

def obtener_tipo_fase(self):

if self.fases['P'] == [0.0]:

return 'P'

elif self.fases['S'] == [0.0]:

return 'S'

elif self.fases['NUEVA_FASE'] == [0.0]:

return 'NUEVA_FASE'

else:

return 'Coda'

### 8.3 Protocolo para soportar múltiples fases por tipo

python

# Cambiar estructura: lista de tiempos en lugar de un solo tiempo

# Ejemplo: {'P': [1.23, 4.56], 'S': [2.34], 'Coda': [10.0, 12.5]}



def __init__(self, fases_detectadas=None):

# ...

self.fases = fases_detectadas if fases_detectadas else {'P': [], 'S': [], 'Coda': []}

self.lineas = {'P': [], 'S': [], 'Coda': []}  # Lista de líneas por fase



def agregar_fase(self, tipo, tiempo, ax):

self.fases[tipo].append(tiempo)

linea = ax.axvline(tiempo, color=self.colores[tipo], linestyle='--')

self.lineas[tipo].append(linea)



def eliminar_fase(self, tipo, indice, ax):

if 0 <= indice < len(self.fases[tipo]):

self.lineas[tipo][indice].remove()

del self.lineas[tipo][indice]

del self.fases[tipo][indice]

### 8.4 Protocolo para mejorar feedback visual

python

# Cambiar cursor durante arrastre

from PyQt5.QtCore import Qt



def al_presionar(self, evento, ax, canvas):

if not evento.dblclick:

tipo_fase = self.encontrar_fase_mas_cercana(evento.xdata, ax)

if tipo_fase is not None:

# Cambiar cursor

canvas.setCursor(Qt.ClosedHandCursor)

# ... resto del código



def al_soltar(self, evento):

if self.arrastrando:

# Restaurar cursor

canvas = self.linea_seleccionada.axes.figure.canvas

canvas.setCursor(Qt.ArrowCursor)

# ... resto del código



## 9. ESTRATEGIA DE REFACTORIZACIÓN

### 9.1 Fase 0: Limpieza inmediata (1 hora)

### 9.2 Fase 1: Robustez (2 días)

Objetivo: Mejorar manejo de errores y validación de datos

python

class GestorFases:

def __init__(self, fases_detectadas=None):

# Validación de entrada

if fases_detectadas is None:

fases_detectadas = {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}



# Validar estructura

for fase in ['P', 'S', 'Coda']:

if fase not in fases_detectadas:

fases_detectadas[fase] = [0.0]

if not isinstance(fases_detectadas[fase], list):

fases_detectadas[fase] = [float(fases_detectadas[fase])]



self.fases = fases_detectadas

# ... resto



def _validar_tiempo(self, tiempo, ax):

"""Valida que el tiempo esté dentro del rango del gráfico"""

if tiempo is None:

return False

x_min, x_max = ax.get_xlim()

return x_min <= tiempo <= x_max



def al_mover(self, evento, canvas):

if self.linea_seleccionada is not None and self.arrastrando:

if evento.inaxes == canvas.figure.gca() and evento.xdata is not None:

if self._validar_tiempo(evento.xdata, evento.inaxes):

x = evento.xdata

self.linea_seleccionada.set_xdata([x, x])

self.fases[self.tipo_fase][0] = x

canvas.draw()

### 9.3 Fase 2: Soporte para múltiples fases (1 semana)

Ver sección 8.3 para implementación.

### 9.4 Fase 3: Refactorización completa (2 semanas)

Objetivo: Separar en clases más pequeñas y especializadas

python

class FaseModel:

"""Modelo de datos para fases"""

def __init__(self):

self._fases = {'P': [], 'S': [], 'Coda': []}



def agregar(self, tipo, tiempo): ...

def eliminar(self, tipo, indice): ...

def obtener(self, tipo): ...

def obtener_todos(self): ...



class FaseView:

"""Vista de fases en matplotlib"""

def __init__(self, ax):

self.ax = ax

self.lineas = {'P': [], 'S': [], 'Coda': []}



def dibujar(self, tipo, tiempo): ...

def mover(self, tipo, indice, nuevo_tiempo): ...

def eliminar(self, tipo, indice): ...



class FaseController:

"""Controlador para interacción usuario"""

def __init__(self, model, view):

self.model = model

self.view = view



def on_click(self, event): ...

def on_drag(self, event): ...



## 10. GLOSARIO DE TÉRMINOS TÉCNICOS



## 11. REGISTRO DE CAMBIOS



CONCLUSIÓN

gestor_fases.py es una librería bien diseñada en su propósito pero con problemas de implementación:

Fortalezas:

✅ Buena separación de responsabilidades (interacción vs visualización)

✅ Uso correcto de eventos de matplotlib

✅ Código relativamente compacto y enfocado

Debilidades críticas:

⚠️ Dependencias muertas que aumentan tiempo de carga innecesariamente

⚠️ Limitación de una fase por tipo (no soporta múltiples marcaciones)

⚠️ Falta de validación de datos de entrada y eventos

⚠️ Código muerto (self.textos, self.texto_info, al_soltar vacío)

Para el mantenimiento a largo plazo, se recomienda:

Inmediato: Limpiar imports y código muerto

Corto plazo: Agregar validaciones y manejo de errores

Mediano plazo: Implementar soporte para múltiples fases por tipo

Largo plazo: Separar en Modelo-Vista-Controlador

