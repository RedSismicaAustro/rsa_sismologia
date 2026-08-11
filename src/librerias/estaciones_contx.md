# CONTEXTO INTEGRAL DE MANTENIMIENTO

estaciones.py - Diálogo de Selección y Configuración de Estaciones

Versión del documento: 1.0
Fecha: 2026-06-11
Propósito: Servir como referencia técnica única para mantenimiento, evolución y comprensión del diálogo de configuración de estaciones, canales y filtros.



ÍNDICE

VISIÓN GENERAL DEL SISTEMA

ARQUITECTURA TÉCNICA DETALLADA

MODELO DE DATOS COMPLETO

FLUJOS DE EJECUCIÓN PRINCIPALES

INTERFAZ DE USUARIO

RELACIÓN CON OTROS MÓDULOS

DEUDA TÉCNICA CATALOGADA

PROTOCOLOS DE MODIFICACIÓN SEGURA

ESTRATEGIA DE REFACTORIZACIÓN

GLOSARIO DE TÉRMINOS



## 1. VISIÓN GENERAL DEL SISTEMA

### 1.1 Propósito fundamental

estaciones.py implementa un diálogo de configuración de estaciones (estaciones_) que permite a los usuarios:

Seleccionar qué estaciones se visualizarán en los gráficos de eventos sísmicos

Configurar filtros pasa banda individuales por estación (orden, frecuencia inferior, frecuencia superior)

Seleccionar el canal físico de cada estación (1, 2 o 3, correspondiente a componente Z, N, E)

Aplicar configuraciones masivas (plot todos, filtro todos)

Persistir los cambios en las estructuras del padre (parent)

### 1.2 Posición en el ecosistema

Este diálogo es reutilizado por múltiples scripts del sistema RSA:

text

┌─────────────────┐

│  estaciones.py  │

│   (QDialog)     │

└────────┬────────┘

│

┌───────────────────┼───────────────────┐

│                   │                   │

▼                   ▼                   ▼

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐

│  extraer_       │ │  procesamiento_ │ │  reporte_       │

│  integrado.py   │ │  integrado.py   │ │  diario.py      │

│  (Extraer_      │ │  (estaciones_)  │ │  (estaciones_   │

│   evento)       │ │   propia)       │ │   propia)       │

└─────────────────┘ └─────────────────┘ └─────────────────┘

Nota importante: Existen múltiples versiones de estaciones_ en el sistema:

Una en extraer_integrado.py (clase interna)

Una en procesamiento_integrado.py (clase interna con señales)

Una en reporte_diario.py (clase interna para calidad)

Esta es una versión independiente reutilizable

### 1.3 Flujo de trabajo típico

Script padre (ej. extraer_integrado.py) crea instancia de estaciones_

Usuario ve lista de estaciones del evento actual

Puede marcar/desmarcar estaciones para graficar

Puede ajustar filtros (orden, f_inf, f_sup) por estación

Puede cambiar el canal (1, 2, 3)

Botones "PLOT TODOS" y "FILTRO TODOS" para configuraciones masivas

Al cerrar, modifica directamente los atributos del padre:

parent.estaciones_eventos (estaciones seleccionadas)

parent.filtros_estaciones (filtros por estación)

parent.hab_grafico (habilitación de gráfico)



## 2. ARQUITECTURA TÉCNICA DETALLADA

### 2.1 Diagrama de clases

python

┌─────────────────────────────────────────────────────────────────┐

│                      QDialog (PyQt5)                            │

└─────────────────────────────────────────────────────────────────┘

▲

│

┌─────────────────────────────────────────────────────────────────┐

│                        estaciones_                              │

├─────────────────────────────────────────────────────────────────┤

│ ATRIBUTOS:                                                      │

│   - parent: object                     # Script padre          │

│   - parametros: dict                   # Parámetros estaciones │

│   - estaciones_eventos: List[int]      # Índices de estaciones │

│   - filtros: List[str]                 # Filtros (6 dígitos)   │

│   - numero_estaciones: int             # Cantidad a mostrar    │

│   - hab_grafico: List[str]             # Habilitación de gráfico│

│                                                                 │

│ WIDGETS DINÁMICOS:                                              │

│   - ck_box_hab_canal: dict[int, QCheckBox]  # Plot por estación│

│   - ck_box_filtro: dict[int, QCheckBox]     # Filtro activo    │

│   - spbox_fil_orden: dict[int, QSpinBox]    # Orden (1-10)     │

│   - spbox_fil_finf: dict[int, QSpinBox]     # Frec. inf (1-10) │

│   - spbox_fil_fsup: dict[int, QSpinBox]     # Frec. sup (5-20) │

│   - spbox_canal: dict[int, QSpinBox]        # Canal (1-3)      │

│   - lbl_nombre/lbl_codigo: dict[int, QLabel]                   │

│                                                                 │

│ WIDGETS CONTROLES:                                              │

│   - ck_box_todos: QCheckBox            # Plot todas            │

│   - ck_box_filtros: QCheckBox          # Filtro todas          │

├─────────────────────────────────────────────────────────────────┤

│ MÉTODOS:                                                        │

│   + __init__(hab_grafico, estaciones_eventos, filtros, parent) │

│   + validar()                           # Plot todas           │

│   + validar_filtros()                   # Filtro todas         │

│   + closeEvent(event)                   # Guarda cambios       │

│   + Salir_()                            # Cierra diálogo       │

└─────────────────────────────────────────────────────────────────┘

### 2.2 Características técnicas

### 2.3 Configuración de UI (sobrescritura)

Aunque carga secundaria.ui, inmediatamente sobrescribe la UI con widgets creados dinámicamente:

python

ruta_ui = os.path.join(ruta_proyecto, "src", "ui", "secundaria.ui")

uic.loadUi(ruta_ui, self)  # Carga, pero luego se reemplaza todo

Luego crea:

Cabeceras (ESTACION, CÓDIGO, PLOT, CANAL, FILTRO, ORDEN, f inf., f sup.)

Una fila por estación con sus controles

Botones "PLOT TODOS" y "FILTRO TODOS"



## 3. MODELO DE DATOS COMPLETO

### 3.1 Parámetros de entrada

### 3.2 Estructura de self.filtros (entrada)

Formato de cada elemento: "OOFFSS" (6 dígitos)

Ejemplo: "020406" = orden=2, f_inf=4 Hz, f_sup=6 Hz

Valor especial: "000000" indica filtro desactivado

### 3.3 Estructura de self.parent.filtros_estaciones (salida)

Tipo: List[str]
Mismo formato que entrada (6 dígitos)
Modificada en closeEvent según selección del usuario

### 3.4 Estructura de self.parametros (desde parametros_estaciones)

python

{

'NUM_ESTACION': List[int],     # [0, 1, 2, ...]

'CODIGO': List[str],           # ["BOB1", "BOB2", ...]

'COMPONENTE': List[str],       # ["1", "2", "3", ...]

'NOMBRE': List[str],           # ["Estación Bobonaza", ...]

'HAB_CANAL': List[str],        # ["1", "0", ...]

'HAB_GRAFICO': List[str],      # Copia de HAB_CANAL

# ... otros campos

}

### 3.5 Mapeo de posiciones (geometría fija)

Fórmula Y: i * 25 + 35, donde i es índice de estación (0-index)

### 3.6 Posiciones de controles adicionales



## 4. FLUJOS DE EJECUCIÓN PRINCIPALES

### 4.1 Inicialización (__init__)

python

## 1. Llamar a super().__init__(parent) dos veces (error, ver deuda)

## 2. Guardar referencias: parent, parametros, estaciones_eventos, filtros, hab_grafico

## 3. Configurar tamaño fijo: setFixedSize(410, 420)

## 4. Cargar secundaria.ui (luego se sobrescribe)

## 5. Inicializar diccionarios para widgets dinámicos

## 6. Crear cabeceras con setGeometry

## 7. Para cada estación en estaciones_eventos:

a. Crear label nombre

b. Crear label código

c. Crear CheckBox PLOT (marcado por defecto)

d. Crear SpinBox CANAL (1-3, valor desde COMPONENTE)

e. Extraer filtro actual del string de 6 dígitos

f. Crear CheckBox FILTRO (marcado si orden != 0)

g. Crear SpinBox ORDEN (1-10)

h. Crear SpinBox f_inf (1-10)

i. Crear SpinBox f_sup (5-20)

## 8. Crear controles "PLOT TODOS" y "FILTRO TODOS"

## 9. Conectar señales: toggled → validar / validar_filtros

### 4.2 Validación de "PLOT TODOS" (validar)

python

def validar(self):

if self.ck_box_todos.checkState() == 2:  # Marcado

for i in range(self.numero_estaciones):

self.ck_box_hab_canal[i].setChecked(True)

else:

for i in range(self.numero_estaciones):

self.ck_box_hab_canal[i].setChecked(False)

⚠️ Nota: checkState() == 2 significa Qt.Checked

### 4.3 Validación de "FILTRO TODOS" (validar_filtros)

python

def validar_filtros(self):

if self.ck_box_filtros.checkState() == 2:

for i in range(self.numero_estaciones):

if self.ck_box_hab_canal[i].checkState() == 2:  # Solo si está habilitada

self.ck_box_filtro[i].setChecked(True)

else:

for i in range(self.numero_estaciones):

self.ck_box_filtro[i].setChecked(False)

### 4.4 Cierre y guardado (closeEvent) - ⚠️ CRÍTICO

python

def closeEvent(self, event):

auxiliar = []  # Estaciones seleccionadas (PLOT marcado)



for i in range(self.numero_estaciones):

canal_ = self.estaciones_eventos[i]

estacion_i = self.estaciones_eventos[i]



# Encontrar índice en la lista total del padre

indice = self.parent.estaciones_eventos_total.index(estacion_i)



# 1. Actualizar lista de estaciones habilitadas

if self.ck_box_hab_canal[i].checkState() == 2:

auxiliar.append(canal_)



# 2. Actualizar filtro

if self.ck_box_filtro[i].checkState() == 2:

orden_i = self.spbox_fil_orden[i].value()

finf_i = self.spbox_fil_finf[i].value()

fsup_i = self.spbox_fil_fsup[i].value()

string_concatenado = f"{orden_i:02}{finf_i:02}{fsup_i:02}"

self.parent.filtros_estaciones[indice] = string_concatenado

else:

self.parent.filtros_estaciones[indice] = '000000'



# 3. Actualizar atributos del padre

self.parent.estaciones_eventos = auxiliar

self.parent.filtros_estaciones = self.filtros  # ⚠️ Esto sobrescribe cambios anteriores



# 4. Actualizar hab_grafico

for i in range(self.numero_estaciones):

canal_ = self.estaciones_eventos[i]

self.parent.componente_canal = str(self.spbox_canal[i])  # ⚠️ Solo guarda el último

if self.ck_box_hab_canal[i].checkState() == 2:

self.parent.hab_grafico[canal_] = '1'

else:

self.parent.hab_grafico[canal_] = '0'



super().closeEvent(event)

⚠️ PROBLEMAS IDENTIFICADOS:

self.parent.filtros_estaciones = self.filtros sobrescribe los cambios hechos en el bucle

self.parent.componente_canal se asigna repetidamente (solo guarda el último valor)



## 5. INTERFAZ DE USUARIO

### 5.1 Estructura visual

text

┌─────────────────────────────────────────────────────────────────────────────┐

│  ESTACION    CÓDIGO    PLOT    CANAL    FILTRO    ORDEN    f inf.   f sup.  │

├─────────────────────────────────────────────────────────────────────────────┤

│  Estación 1   BOB1      ☑       2        ☐        2        1        10     │

│  Estación 2   BOB2      ☑       1        ☑        4        2        15     │

│  Estación 3   CHAB      ☐       3        ☐        2        1        10     │

│  ...                                                                        │

├─────────────────────────────────────────────────────────────────────────────┤

│                                                              ┌─────────────┐│

│  PLOT TODOS ☑                                                ┌───────────┐ │

│  FILTRO TODOS ☐                                             │           │ │

│                                                             │  Ventana   │ │

└─────────────────────────────────────────────────────────────────────────────┘

### 5.2 Controles

### 5.3 Archivo UI base (secundaria.ui)

El contenido de secundaria.ui es completamente ignorado porque el script sobrescribe toda la UI con widgets creados dinámicamente. El único propósito de cargarlo es obtener una ventana base (posición, título, etc.).



## 6. RELACIÓN CON OTROS MÓDULOS

### 6.1 Dependencias (imports)

python

from PyQt5.QtWidgets import (QLabel, QCheckBox)

from PyQt5 import uic

from metodos_gestion import parametros_estaciones

from PyQt5.QtWidgets import (QDialog, QSpinBox)

### 6.2 Módulos consumidores

### 6.3 Diagrama de dependencias

text

┌─────────────────┐

│  metodos_       │

│  gestion.py     │

└────────┬────────┘

│ (parametros_estaciones)

▼

┌─────────────────┐

│  estaciones.py  │

└────────┬────────┘

│ (instancia)

┌───────────────────┼───────────────────┐

▼                   ▼                   ▼

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐

│  extraer_       │ │  procesamiento_ │ │  reporte_       │

│  integrado.py   │ │  integrado.py   │ │  diario.py      │

└─────────────────┘ └─────────────────┘ └─────────────────┘



## 7. DEUDA TÉCNICA CATALOGADA

### 7.1 Deuda crítica

Corrección inmediata para E-02 y E-03:

python

def closeEvent(self, event):

auxiliar = []

# Guardar componentes por estación

componentes_actualizados = {}



for i in range(self.numero_estaciones):

canal_ = self.estaciones_eventos[i]

estacion_i = self.estaciones_eventos[i]

indice = self.parent.estaciones_eventos_total.index(estacion_i)



if self.ck_box_hab_canal[i].checkState() == 2:

auxiliar.append(canal_)



if self.ck_box_filtro[i].checkState() == 2:

orden_i = self.spbox_fil_orden[i].value()

finf_i = self.spbox_fil_finf[i].value()

fsup_i = self.spbox_fil_fsup[i].value()

self.parent.filtros_estaciones[indice] = f"{orden_i:02}{finf_i:02}{fsup_i:02}"

else:

self.parent.filtros_estaciones[indice] = '000000'



# Guardar componente correctamente

componentes_actualizados[canal_] = str(self.spbox_canal[i].value())



self.parent.estaciones_eventos = auxiliar

# NO sobrescribir: self.parent.filtros_estaciones = self.filtros



# Actualizar componentes

for canal_, componente in componentes_actualizados.items():

# Necesitaríamos un mecanismo para guardar componente por estación

pass

### 7.2 Deuda alta

### 7.3 Deuda media

### 7.4 Deuda baja



## 8. PROTOCOLOS DE MODIFICACIÓN SEGURA

### 8.1 Reglas de oro

NUNCA asumir que self.parent tiene ciertos atributos sin verificar

SIEMPRE usar señales en lugar de modificar atributos del padre directamente

VALIDAR que estacion_i existe en estaciones_eventos_total antes de usar index()

RESPETAR el formato de 6 dígitos para filtros

### 8.2 Protocolo para modificar estructura de filtros

python

# Si se necesita agregar más parámetros al filtro:

# 1. Mantener compatibilidad con formato existente

# 2. Agregar nuevos campos al final

# Ejemplo: "02040601" (orden, f_inf, f_sup, nuevo_param)



def empaquetar_filtro(orden, finf, fsup, nuevo=None):

base = f"{orden:02}{finf:02}{fsup:02}"

if nuevo:

base += f"{nuevo:02}"

return base



def desempaquetar_filtro(filtro_str):

orden = int(filtro_str[0:2])

finf = int(filtro_str[2:4])

fsup = int(filtro_str[4:6])

nuevo = int(filtro_str[6:8]) if len(filtro_str) >= 8 else None

return orden, finf, fsup, nuevo

### 8.3 Protocolo para migrar a señales (recomendado)

python

from PyQt5.QtCore import pyqtSignal



class estaciones_(QDialog):

# Señales en lugar de modificación directa

datos_actualizados = pyqtSignal(list, list, dict)  # (habilitadas, filtros, componentes)



def closeEvent(self, event):

# Recopilar datos

habilitadas, filtros, componentes = self._recopilar_datos()



# Emitir señal en lugar de modificar padre

self.datos_actualizados.emit(habilitadas, filtros, componentes)



super().closeEvent(event)

### 8.4 Protocolo para manejar ventanas con muchas estaciones

python

# Si numero_estaciones > 15, usar QScrollArea

if self.numero_estaciones > 15:

scroll_area = QScrollArea(self)

scroll_widget = QWidget()

scroll_layout = QVBoxLayout(scroll_widget)



for i in range(self.numero_estaciones):

# Crear fila de widgets

fila_layout = QHBoxLayout()

# ... agregar widgets

scroll_layout.addLayout(fila_layout)



scroll_area.setWidget(scroll_widget)

# Reemplazar layout con scroll_area



## 9. ESTRATEGIA DE REFACTORIZACIÓN

### 9.1 Fase 0: Corrección inmediata (1 día)

### 9.2 Fase 1: Migración a señales (2 días)

python

class estaciones_(QDialog):

senal_cerrar = pyqtSignal(list, list, dict)  # habilitadas, filtros, componentes



def closeEvent(self, event):

habilitadas = []

filtros_actualizados = []

componentes = {}



for i in range(self.numero_estaciones):

idx = self.estaciones_eventos[i]

if self.ck_box_hab_canal[i].isChecked():

habilitadas.append(idx)



if self.ck_box_filtro[i].isChecked():

orden = self.spbox_fil_orden[i].value()

finf = self.spbox_fil_finf[i].value()

fsup = self.spbox_fil_fsup[i].value()

filtros_actualizados.append(f"{orden:02}{finf:02}{fsup:02}")

else:

filtros_actualizados.append("000000")



componentes[idx] = self.spbox_canal[i].value()



self.senal_cerrar.emit(habilitadas, filtros_actualizados, componentes)

super().closeEvent(event)

### 9.3 Fase 2: Migración a layouts (1 semana)

python

def _crear_layout(self):

layout_principal = QVBoxLayout(self)



# Cabeceras

cabeceras_layout = QHBoxLayout()

cabeceras = ["ESTACIÓN", "CÓDIGO", "PLOT", "CANAL", "FILTRO", "ORDEN", "f inf.", "f sup."]

for texto in cabeceras:

cabeceras_layout.addWidget(QLabel(texto))

layout_principal.addLayout(cabeceras_layout)



# Área de scroll para estaciones

scroll = QScrollArea()

scroll_widget = QWidget()

scroll_layout = QVBoxLayout(scroll_widget)



for i in range(self.numero_estaciones):

fila = self._crear_fila_estacion(i)

scroll_layout.addLayout(fila)



scroll.setWidget(scroll_widget)

layout_principal.addWidget(scroll)



# Controles inferiores

controles_layout = QHBoxLayout()

self.ck_box_todos = QCheckBox("PLOT TODOS")

self.ck_box_filtros = QCheckBox("FILTRO TODOS")

controles_layout.addWidget(self.ck_box_todos)

controles_layout.addWidget(self.ck_box_filtros)

layout_principal.addLayout(controles_layout)



self.setLayout(layout_principal)



## 10. GLOSARIO DE TÉRMINOS TÉCNICOS



## 11. REGISTRO DE CAMBIOS



CONCLUSIÓN

estaciones.py es un diálogo funcional pero con problemas significativos de diseño:

Fortalezas:

✅ Proporciona interfaz completa para configuración de estaciones

✅ Soporta configuración individual por estación

✅ Ofrece controles masivos (PLOT TODOS, FILTRO TODOS)

Debilidades críticas:

⚠️ Pérdida de datos: self.parent.filtros_estaciones = self.filtros sobrescribe cambios

⚠️ Alto acoplamiento: Modifica atributos del padre directamente

⚠️ No responsivo: Geometrías fijas no se adaptan a diferentes resoluciones

⚠️ Código duplicado: Existen múltiples versiones de estaciones_ en el sistema

Para el mantenimiento a largo plazo, se recomienda:

Inmediato: Corregir los bugs de pérdida de datos (E-02, E-03)

Corto plazo: Migrar a comunicación por señales

Mediano plazo: Unificar todas las versiones de estaciones_ en una sola clase reutilizable

Largo plazo: Migrar a layouts responsivos

