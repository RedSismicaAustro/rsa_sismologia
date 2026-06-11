# Contexto Técnico de Mantenimiento V3: `inicio.py`

## 0. Identificación del documento

| Elemento | Detalle |
|---|---|
| Archivo documentado | `inicio.py` |
| Versión del contexto | V3 integral para mantenimiento |
| Sistema | `rsa_sismologia` |
| Tipo de módulo | Ventana inicial de configuración operativa |
| Lenguaje | Python |
| Framework GUI | PyQt5 |
| Fecha de generación | 2026-06-11 10:32:11 |

---

## 1. Propósito general del módulo

El módulo `inicio.py` define la clase `Inicio_proceso`, una ventana de configuración inicial usada por el sistema `rsa_sismologia`.

Su función principal es construir y emitir el contexto mínimo necesario para iniciar el procesamiento sísmico de un día o de un período específico.

Los parámetros operativos que prepara son:

- archivo base del día;
- directorio de trabajo;
- responsable del procesamiento;
- período horario.

Este módulo no procesa datos sísmicos. Su responsabilidad es inicializar correctamente el contexto de trabajo y comunicarlo a la ventana principal mediante señales Qt.

---

## 2. Papel dentro del sistema RSA

`Inicio_proceso` debe entenderse como el punto de entrada operativo de la cadena de procesamiento.

El resto del sistema depende de la señal:

```python
inicializado.emit(archivo, directorio_trabajo, responsable, periodo)
```

Esta señal entrega la configuración base que utilizarán los módulos posteriores.

Flujo conceptual:

```text
Usuario
  ↓
Inicio_proceso
  ↓
Señal inicializado(...)
  ↓
Ventana principal
  ↓
Módulos posteriores:
  - marcado de eventos
  - extracción
  - procesamiento integrado
  - reportes
```

---

## 3. Responsabilidades del módulo

### 3.1. Responsabilidades incluidas

- Cargar la interfaz `inicio.ui`.
- Localizar la raíz del proyecto `rsa_sismologia`.
- Configurar temporalmente `sys.path` para importar librerías propias.
- Cargar responsables desde `datos/responsables.csv`.
- Permitir selección de fecha.
- Permitir selección de directorio de trabajo.
- Permitir selección de responsable.
- Permitir selección de período horario.
- Construir el archivo base con formato `yyyyMMdd000000`.
- Mostrar al usuario un resumen HTML de los parámetros seleccionados.
- Emitir señales hacia la ventana principal.
- Ejecutar limpieza básica del canvas y figura al cerrar.

### 3.2. Responsabilidades excluidas

Este módulo no debe encargarse de:

- leer archivos sísmicos;
- procesar eventos;
- graficar señales sísmicas reales;
- generar catálogos;
- generar reportes;
- validar calidad de datos;
- administrar estaciones;
- corregir tiempos;
- ejecutar algoritmos de procesamiento.

---

## 4. Estructura esperada del proyecto

Por las rutas usadas en el código, se espera una estructura similar a:

```text
rsa_sismologia/
├── src/
│   ├── inicio.py
│   ├── ui/
│   │   └── inicio.ui
│   └── librerias/
│       ├── metodos_rsa.py
│       └── metodos_gestion.py
├── datos/
│   └── responsables.csv
└── otros directorios de trabajo
```

El script intenta localizar la raíz del proyecto buscando el directorio llamado `rsa_sismologia`.

---

## 5. Dependencias explícitas

### 5.1. Módulos estándar

| Módulo | Uso |
|---|---|
| `sys` | Modificación de `sys.path` |
| `os` | Construcción y normalización de rutas |
| `pathlib.Path` | Descomposición de rutas |
| `datetime.datetime` | Fecha actual |

### 5.2. PyQt5

| Elemento | Uso |
|---|---|
| `QMainWindow` | Clase base de la ventana |
| `QVBoxLayout`, `QHBoxLayout` | Organización de paneles |
| `QWidget` | Widget central |
| `QtWidgets.QFileDialog` | Selección de directorio |
| `QtCore.QDate` / `QDate` | Manejo de fecha en la interfaz |
| `pyqtSignal` | Señales personalizadas |
| `uic.loadUi` | Carga del archivo `.ui` |

### 5.3. Matplotlib

| Elemento | Uso |
|---|---|
| `Figure` | Figura del panel derecho |
| `FigureCanvasQTAgg` | Canvas embebido en PyQt |
| `matplotlib.pyplot` | Cierre/liberación de figura |

### 5.4. Módulos internos

```python
from metodos_rsa import lectura_archivo
from metodos_gestion import parametros_estaciones
```

| Función | Uso |
|---|---|
| `lectura_archivo()` | Lee `responsables.csv` |
| `parametros_estaciones()` | Carga parámetros de estaciones, aunque no se usan activamente en este módulo |

---

## 6. Dependencias implícitas críticas

### DI-01: Dependencia de `showDate()` para crear `self.archivo`

El atributo `self.archivo` no se inicializa directamente en el constructor. Se crea indirectamente cuando el constructor llama a:

```python
self.showDate(d)
```

Dentro de `showDate()`:

```python
self.archivo = self.directorio_trabajo + date.toString('yyyyMMdd000000')
```

Esto es crítico porque `self.archivo` luego es usado por:

- `Iniciar()`;
- `closeEvent()`.

Si se elimina, retrasa o condiciona la llamada a `showDate()`, el módulo puede fallar por atributo inexistente o emitir valores incompletos.

### DI-02: Dependencia entre `.ui` y nombres de widgets

El código depende de que `inicio.ui` contenga exactamente los siguientes objetos:

- `Btn_Iniciar`;
- `Btn_drive`;
- `dia`;
- `cmbx_resposables`;
- `cmbx_periodo`;
- `radioButton_diario`;
- `radioButton_periodo`;
- `mensajes`.

Si se renombra un widget en Qt Designer sin actualizar el código, la ventana fallará al ejecutar.

### DI-03: Dependencia del nombre incorrecto `cmbx_resposables`

El nombre real usado en el código es:

```python
self.cmbx_resposables
```

Ortográficamente debería ser:

```python
self.cmbx_responsables
```

Sin embargo, no debe cambiarse solo en Python. Si se corrige, debe actualizarse simultáneamente:

- en `inicio.ui`;
- en todas las referencias del código;
- en cualquier documentación asociada.

### DI-04: Dependencia de `responsables.csv`

El constructor espera que exista:

```text
datos/responsables.csv
```

y que cada fila leída tenga al menos un primer elemento:

```python
lista_resp = [sublista[0] for sublista in datos]
```

Si el CSV está vacío, mal formado o contiene filas incompletas, puede fallar.

---

## 7. Señales personalizadas

### 7.1. `cerrado`

```python
cerrado = pyqtSignal()
```

Se emite al cerrar la ventana. Su objetivo es notificar a la ventana principal que el diálogo terminó.

### 7.2. `inicializado`

```python
inicializado = pyqtSignal(str, str, str, str)
```

Emite cuatro valores:

| Posición | Valor | Descripción |
|---:|---|---|
| 1 | `archivo` | Archivo base del día |
| 2 | `directorio_trabajo` | Directorio de trabajo |
| 3 | `responsable` | Responsable seleccionado |
| 4 | `periodo` | Período horario |

### Observación crítica

Actualmente `inicializado` se emite en dos lugares:

1. `Iniciar()`;
2. `closeEvent()`.

Por tanto, si el usuario hace clic en **Iniciar**, se emite una vez y luego se emite nuevamente al cerrarse la ventana.

---

## 8. Inventario de atributos

| Atributo | Se crea en | Uso | Observación |
|---|---|---|---|
| `self.directorio_trabajo` | Constructor / `seleccionar_drive()` | Ruta base de trabajo | Puede o no terminar en `/` |
| `self.responsable` | Constructor / `cambio_responsable()` / `Iniciar()` | Responsable operativo | Sale por señal |
| `self.periodo` | Constructor / `cambio_periodo()` | Turno horario | Sale por señal |
| `self.date` | `showDate()` / `Iniciar()` | Fecha seleccionada | Base para `self.archivo` |
| `self.archivo` | `showDate()` / `Iniciar()` | Archivo base | Dependencia crítica |
| `self.visor` | Constructor | Figura Matplotlib | No tiene uso gráfico real |
| `self.canvas` | Constructor | Canvas Qt-Matplotlib | Se crea pero no se grafica nada |
| `self.parametros` | Constructor | Parámetros de estaciones | No se usa posteriormente |
| `datos_sismo` | Global | Ninguno | Variable global sin uso |

---

## 9. Flujo de inicialización

```text
Inicio_proceso.__init__()
  ↓
Define título inicial
  ↓
Crea layout principal
  ↓
Carga inicio.ui
  ↓
Inserta UI en panel izquierdo
  ↓
Crea figura y canvas Matplotlib
  ↓
Inserta canvas en panel derecho
  ↓
Configura widget central
  ↓
Conecta botones principales
  ↓
Carga responsables.csv
  ↓
Carga períodos horarios
  ↓
Carga parametros_estaciones()
  ↓
Obtiene fecha actual
  ↓
Conecta señales de fecha, período y responsable
  ↓
Asigna directorio_trabajo, responsable y período iniciales
  ↓
Llama showDate(d)
  ↓
Conecta radio buttons
  ↓
Selecciona índice 1 del combo de períodos
```

---

## 10. Análisis método por método

### 10.1. `extraer_hasta_directorio(ruta_completa, nombre_directorio)`

#### Propósito

Extraer la ruta raíz del proyecto hasta encontrar el directorio `rsa_sismologia`.

#### Lógica

```python
partes = Path(ruta_completa).parts
if nombre_directorio in partes:
    indice = partes.index(nombre_directorio)
    ruta_recortada = Path(*partes[:indice + 1])
    return str(ruta_recortada) + '/'
else:
    return ''
```

#### Riesgo

Si el archivo se ejecuta desde una ruta que no contiene `rsa_sismologia`, devuelve cadena vacía. Esto puede provocar rutas inválidas para:

- `src/librerias`;
- `src/ui/inicio.ui`;
- `datos/responsables.csv`.

#### Recomendación

Lanzar una excepción explícita si no encuentra el proyecto.

---

### 10.2. `__init__()`

#### Propósito

Construir la ventana, cargar la interfaz, cargar datos iniciales y conectar señales.

#### Efectos secundarios

- Modifica layout de la ventana.
- Carga archivo UI.
- Carga CSV de responsables.
- Crea figura Matplotlib.
- Carga parámetros de estaciones.
- Genera archivo base inicial.

#### Riesgos

- Si falta `inicio.ui`, falla.
- Si falta `responsables.csv`, falla.
- Si los widgets del UI cambian de nombre, falla.
- Si `directorio_trabajo` no termina en separador, `showDate()` puede construir mal la ruta.
- `self.parametros` se carga pero no se usa.

---

### 10.3. `seleccionar_diario(estado)`

#### Propósito

Activar modo de procesamiento diario.

#### Acciones

- Habilita selector de fecha.
- Limpia combo de períodos.
- Carga tres períodos estándar.
- Habilita combo.
- Selecciona `"00:00 - 12:00"`.

#### Observación

Al hacer `setCurrentIndex(0)`, se dispara `currentTextChanged`, actualizando `self.periodo`.

---

### 10.4. `seleccionar_periodo(estado)`

#### Propósito

Activar un modo de período especial sin fecha fija.

#### Acciones reales

```python
self.dia.setEnabled(False)
self.cmbx_periodo.clear()
self.cmbx_periodo.addItem(" ")
self.cmbx_periodo.setEnabled(False)
self.cmbx_periodo.setCurrentIndex(4)
```

#### Problema confirmado

Después de `addItem(" ")`, el combo tiene un solo elemento. Por tanto, el índice válido es `0`, no `4`.

Debe corregirse a:

```python
self.cmbx_periodo.setCurrentIndex(0)
```

o eliminarse completamente si no es necesario.

#### Riesgo

Aunque Qt pueda tolerarlo sin lanzar error visible, el comportamiento no es correcto y depende de detalles internos del framework.

---

### 10.5. `Iniciar()`

#### Propósito

Confirmar parámetros y emitirlos hacia la ventana principal.

#### Flujo

1. Lee fecha seleccionada.
2. Construye `self.archivo` usando `os.path.join()`.
3. Lee responsable actual.
4. Emite `inicializado`.
5. Cierra ventana.

#### Código clave

```python
self.inicializado.emit(
    self.archivo,
    self.directorio_trabajo,
    self.responsable,
    self.periodo
)
self.close()
```

#### Problema crítico

`self.close()` activa `closeEvent()`, que vuelve a emitir `inicializado`. Esto puede provocar procesamiento duplicado.

#### Recomendación

Usar una bandera interna:

```python
self._iniciado = True
```

y en `closeEvent()` evitar emitir `inicializado` si ya fue emitida.

---

### 10.6. `seleccionar_drive()`

#### Propósito

Permitir al usuario seleccionar el directorio de trabajo.

#### Flujo

1. Abre diálogo de selección.
2. Si la ruta no termina en `/`, lo agrega.
3. Actualiza `self.directorio_trabajo`.
4. Llama `showDate(self.date)`.

#### Riesgo

Si el usuario cancela el diálogo, `folderpath` puede ser cadena vacía. En ese caso, esta línea puede fallar:

```python
if folderpath[-1] == '/':
```

#### Recomendación

Validar primero:

```python
if not folderpath:
    return
```

---

### 10.7. `showDate(date)`

#### Propósito

Actualizar fecha, archivo base y mensaje.

#### Código

```python
self.date = date
self.archivo = self.directorio_trabajo + date.toString('yyyyMMdd000000')
self.desplegar_mensaje()
```

#### Problema de mantenimiento

Construye la ruta por concatenación directa, mientras que `Iniciar()` usa `os.path.join()`.

Esto puede producir diferencias si `directorio_trabajo` no termina con `/`.

#### Recomendación

Crear un método único:

```python
def generar_archivo_base(self):
    return os.path.join(
        self.directorio_trabajo,
        self.date.toString('yyyyMMdd000000')
    )
```

---

### 10.8. `cambio_periodo(texto)`

#### Propósito

Actualizar el período seleccionado.

#### Código

```python
self.periodo = texto
self.desplegar_mensaje()
```

#### Observación

El cambio de período actualiza inmediatamente la vista HTML.

---

### 10.9. `cambio_responsable(texto)`

#### Propósito

Actualizar responsable seleccionado.

#### Código

```python
self.responsable = texto
self.desplegar_mensaje()
```

#### Observación

El comentario interno dice "asignar el valor del combobox a self.periodo", pero realmente actualiza `self.responsable`. El comentario debería corregirse.

---

### 10.10. `desplegar_mensaje()`

#### Propósito

Mostrar un resumen HTML de los parámetros actuales.

#### Campos mostrados

- Día;
- directorio de trabajo;
- responsable;
- período.

#### Observación

Cuando `self.periodo == ''`, el mensaje muestra `"PERIODO"` en lugar de la fecha.

Sin embargo, en `seleccionar_periodo()` se agrega `" "` con un espacio, no cadena vacía. Por tanto, esa rama probablemente no se ejecuta en el flujo actual.

#### Recomendación

Normalizar el período especial usando una constante clara, por ejemplo:

```python
PERIODO_ESPECIAL = ""
```

o usar `strip()`:

```python
if self.periodo.strip() == "":
```

---

### 10.11. `visor_limpiar_completo()`

#### Propósito

Limpiar y cerrar la figura Matplotlib.

#### Código

```python
self.visor.clear()
self.visor.clf()
plt.close(self.visor)
```

#### Observación

Es redundante usar `clear()` y `clf()` sobre la misma figura. Además, el panel gráfico no tiene uso operativo actual.

---

### 10.12. `limpiar_estado()`

#### Propósito

Eliminar referencias al canvas y figura.

#### Flujo

- Si existe `canvas`, llama `deleteLater()`.
- Si existe `visor`, llama `clf()` y lo pone en `None`.

#### Observación

El método es razonable, aunque debe coordinarse con `visor_limpiar_completo()` para evitar doble limpieza innecesaria.

---

### 10.13. `closeEvent(event)`

#### Propósito

Ejecutar limpieza, emitir señales y cerrar.

#### Flujo actual

1. Imprime `"Cerrando inicio"`.
2. Limpia visor.
3. Limpia estado.
4. Imprime parámetros.
5. Emite `inicializado`.
6. Emite `cerrado`.
7. Llama a `super().closeEvent(event)`.

#### Problema crítico

Emite `inicializado` aunque el usuario cierre la ventana sin presionar **Iniciar**.

Esto puede iniciar procesamiento con parámetros no confirmados.

También emite `inicializado` por segunda vez cuando se presiona **Iniciar**.

---

## 11. Gestión de estado

El estado de la ventana está distribuido en atributos simples. No existe una estructura central de configuración.

Actualmente el estado operativo está formado por:

```python
self.archivo
self.directorio_trabajo
self.responsable
self.periodo
self.date
```

### Recomendación

Crear una estructura explícita:

```python
@dataclass
class ContextoInicio:
    archivo: str
    directorio_trabajo: str
    responsable: str
    periodo: str
    fecha: QDate
```

Esto facilitaría pruebas y mantenimiento.

---

## 12. Gestión de recursos gráficos

El módulo crea un panel gráfico, pero no lo usa funcionalmente.

```python
self.visor = Figure(figsize=(8, 4), dpi=100)
self.canvas = FigureCanvas(self.visor)
```

No existe ningún método que grafique datos en `self.visor`.

### Clasificación

Esto debe considerarse deuda técnica o funcionalidad incompleta, no funcionalidad activa.

### Opciones

1. Eliminar panel gráfico.
2. Mantenerlo, pero documentar qué se planea mostrar.
3. Reutilizarlo para vista previa de datos o estado de procesamiento.

---

## 13. Integración con otros módulos RSA

La ventana principal probablemente conecta:

```python
self.inicio.inicializado.connect(self.procesar_dia)
self.inicio.cerrado.connect(self.limpiar_dialogo)
```

El contrato esperado es:

```python
archivo: str
directorio_trabajo: str
responsable: str
periodo: str
```

Cualquier cambio en el orden o significado de estos argumentos rompe compatibilidad con módulos consumidores.

---

## 14. Supuestos de diseño

1. El proyecto contiene un directorio llamado `rsa_sismologia`.
2. El archivo `inicio.py` está dentro de la estructura del proyecto.
3. Existe `src/ui/inicio.ui`.
4. Existe `datos/responsables.csv`.
5. Cada fila de `responsables.csv` tiene al menos una columna.
6. El combo de responsables se llama `cmbx_resposables`.
7. El directorio de trabajo puede concatenarse con el nombre de archivo si termina en `/`.
8. El período inicial recibido es válido.
9. La ventana principal controla adecuadamente las señales recibidas.
10. El usuario debe confirmar con **Iniciar**, aunque actualmente cerrar también emite `inicializado`.

---

## 15. Deuda técnica

| ID | Deuda técnica | Riesgo | Prioridad |
|---|---|---|---|
| DT-01 | Doble emisión de `inicializado` | Alto | Alta |
| DT-02 | `closeEvent()` inicia procesamiento sin confirmación | Alto | Alta |
| DT-03 | `setCurrentIndex(4)` inválido | Medio | Media |
| DT-04 | Panel gráfico sin uso operativo | Bajo | Media |
| DT-05 | `datos_sismo = {{}}` sin uso | Muy bajo | Baja |
| DT-06 | `parametros_estaciones()` cargado sin uso | Bajo | Baja |
| DT-07 | Construcción inconsistente de rutas | Medio | Media |
| DT-08 | Falta validación al cancelar selección de directorio | Medio | Media |
| DT-09 | Comentario incorrecto en `cambio_responsable()` | Muy bajo | Baja |
| DT-10 | Rama `self.periodo == ''` probablemente no se ejecuta | Bajo | Baja |

---

## 16. Riesgos de modificación

### Riesgo alto

Modificar:

- `Iniciar()`;
- `closeEvent()`;
- señal `inicializado`;
- orden de argumentos emitidos.

Puede romper la integración con la ventana principal.

### Riesgo medio

Modificar:

- nombres de widgets del `.ui`;
- `showDate()`;
- construcción de rutas;
- selección de períodos.

### Riesgo bajo

Modificar:

- panel gráfico;
- comentarios;
- limpieza de figura;
- variable global no usada.

---

## 17. Refactorizaciones recomendadas

### RF-01: Evitar doble emisión

Agregar una bandera:

```python
self._confirmado = False
```

En `Iniciar()`:

```python
self._confirmado = True
self.inicializado.emit(...)
self.close()
```

En `closeEvent()`:

```python
if not self._confirmado:
    self.cerrado.emit()
    super().closeEvent(event)
    return
```

O, más simple, eliminar la emisión de `inicializado` desde `closeEvent()`.

### RF-02: Corregir índice de período especial

Cambiar:

```python
self.cmbx_periodo.setCurrentIndex(4)
```

por:

```python
self.cmbx_periodo.setCurrentIndex(0)
```

### RF-03: Método único de archivo base

Crear:

```python
def actualizar_archivo_base(self):
    self.archivo = os.path.join(
        self.directorio_trabajo,
        self.date.toString('yyyyMMdd000000')
    )
```

Usarlo tanto en `showDate()` como en `Iniciar()`.

### RF-04: Validar cancelación de directorio

```python
folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')

if not folderpath:
    return
```

### RF-05: Decidir destino del panel gráfico

Eliminarlo o implementarlo realmente.

### RF-06: Eliminar código no usado

- `datos_sismo`;
- `self.parametros`, si no se usa;
- importaciones asociadas si dejan de ser necesarias.

---

## 18. Checklist de regresión

### Inicialización

- [ ] La ventana abre sin errores.
- [ ] Se carga `inicio.ui`.
- [ ] Se carga `responsables.csv`.
- [ ] Se llena el combo de responsables.
- [ ] Se cargan los tres períodos horarios.
- [ ] La fecha actual se muestra correctamente.
- [ ] `self.archivo` queda inicializado.

### Selección de fecha

- [ ] Cambiar fecha actualiza `self.date`.
- [ ] Cambiar fecha actualiza `self.archivo`.
- [ ] Cambiar fecha actualiza el HTML de mensajes.

### Selección de directorio

- [ ] Seleccionar directorio actualiza `self.directorio_trabajo`.
- [ ] Cancelar selección no produce error.
- [ ] La ruta final se construye correctamente.

### Responsable y período

- [ ] Cambiar responsable actualiza `self.responsable`.
- [ ] Cambiar período actualiza `self.periodo`.
- [ ] Modo diario habilita fecha.
- [ ] Modo período deshabilita fecha sin error.

### Señales

- [ ] `inicializado` se emite una sola vez al presionar **Iniciar**.
- [ ] `cerrado` se emite al cerrar.
- [ ] Cerrar sin iniciar no dispara procesamiento no deseado.
- [ ] La ventana principal recibe los cuatro argumentos en orden correcto.

### Limpieza

- [ ] El canvas se elimina sin error.
- [ ] La figura se cierra sin error.
- [ ] No quedan excepciones al cerrar.

---

## 19. Checklist de integración

Antes de integrar cambios en `inicio.py`, verificar:

- [ ] La ventana principal mantiene la misma firma de conexión.
- [ ] Los módulos posteriores siguen recibiendo `archivo` con formato esperado.
- [ ] El directorio de trabajo se mantiene compatible con `obtener_directorios()` u otros módulos.
- [ ] El responsable se propaga correctamente a reportes o trazabilidad.
- [ ] El período sigue siendo compatible con módulos posteriores.

---

## 20. Guía para desarrolladores futuros

### Si se cambia el nombre `cmbx_resposables`

Actualizar simultáneamente:

- `inicio.ui`;
- `inicio.py`;
- documentación;
- cualquier prueba automatizada.

### Si se cambia el formato de `archivo`

Verificar todos los módulos que reciben `archivo` desde la señal `inicializado`.

### Si se elimina el panel gráfico

Eliminar también:

- `FigureCanvas`;
- `Figure`;
- `matplotlib.pyplot`;
- `visor_limpiar_completo()`;
- referencias a `self.visor`;
- referencias a `self.canvas`.

### Si se mantiene el panel gráfico

Documentar explícitamente qué debe mostrar y en qué momento.

---

## 21. Historial de problemas conocidos

| ID | Problema | Estado sugerido |
|---|---|---|
| HK-01 | Doble emisión de `inicializado` | Corregir |
| HK-02 | Índice inválido en modo período | Corregir |
| HK-03 | Panel gráfico sin uso | Decidir |
| HK-04 | `parametros_estaciones()` sin uso | Revisar |
| HK-05 | `datos_sismo` sin uso | Eliminar |
| HK-06 | Rutas construidas de forma inconsistente | Unificar |
| HK-07 | Cancelación de selección de directorio no validada | Corregir |

---

## 22. Recomendación final

Antes de ampliar este módulo, conviene corregir primero:

1. Doble emisión de `inicializado`.
2. Emisión de `inicializado` desde `closeEvent()`.
3. Índice inválido `setCurrentIndex(4)`.
4. Construcción inconsistente de rutas.
5. Falta de validación al cancelar selección de directorio.

Estas correcciones reducirán el riesgo de errores en cascada durante el procesamiento sísmico.

---

## 23. Código fuente de referencia

El siguiente bloque corresponde al archivo `inicio.py` utilizado como referencia para esta documentación.

```python
import sys
import os
from pathlib import Path
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    else:
        return ''
ruta_librerias=os.path.dirname(__file__)
ruta_proyecto=extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src','librerias'))

# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)



from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget)
from PyQt5 import uic
from PyQt5 import QtWidgets,QtCore
from metodos_rsa import (lectura_archivo)

from metodos_gestion import parametros_estaciones

datos_sismo={}

import matplotlib.pyplot as plt
from datetime import datetime
from PyQt5.QtCore import QDate
from PyQt5.QtCore import pyqtSignal
 
class Inicio_proceso(QMainWindow):
    cerrado = pyqtSignal()  # señal que se emitire al cerrar
    inicializado = pyqtSignal(str, str, str,str)  # archivo, directorio_trabajo, responsable
    def __init__(self, directorio_trabajo, responsable, periodo,parent=None):
        super().__init__()
        self.setWindowTitle('Inizializacion de día')
        # Configurar el layout principal
        layout_principal = QHBoxLayout()
        # Panel izquierdo
        panel_izquierdo = QVBoxLayout()

        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src",  "ui", 'inicio.ui')
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        # Añadir la interfaz cargada al panel izquierdo
        panel_izquierdo.addWidget(self.centralWidget())  # Ahora centralWidget es la UI cargada
        layout_principal.addLayout(panel_izquierdo, 1)
        # Panel derecho (gráfico)
        panel_derecho = QVBoxLayout()
        self.visor = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.visor)
        self.canvas.setParent(self)# Importante para que Qt lo maneje bien
        panel_derecho.addWidget(self.canvas)
        layout_principal.addLayout(panel_derecho, 4)
        # Establecer el layout principal en el widget central
        widget_central = QWidget()
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)
        self.setWindowTitle("INICIO DE DIA")

        self.Btn_Iniciar.clicked.connect(self.Iniciar)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)



        ruta_csv =  os.path.join(ruta_proyecto, "datos", "responsables.csv")
        ruta_csv = os.path.abspath(ruta_csv)
        datos=lectura_archivo(ruta_csv)
        lista_resp = [sublista[0] for sublista in datos]
        self.cmbx_resposables.addItems(lista_resp)

        horario=("00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00")
        self.cmbx_periodo.addItems(horario)

        self.parametros=parametros_estaciones()#(nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual
        self.dia.clicked[QtCore.QDate].connect(self.showDate)
        self.cmbx_periodo.currentTextChanged.connect(self.cambio_periodo)
        self.cmbx_resposables.currentTextChanged.connect(self.cambio_responsable)
        #self.directorio_trabajo='G:\Mi unidad\DIA\\' #self.directorio_trabajo=dir_trabajo[0:aux-9]
        self.directorio_trabajo=directorio_trabajo
        self.responsable=responsable
        self.periodo=periodo
        self.showDate(d)

        # Conectar las señales en el __init__ de tu ventana
        self.radioButton_diario.toggled.connect(self.seleccionar_diario)
        self.radioButton_periodo.toggled.connect(self.seleccionar_periodo)
        self.cmbx_periodo.setCurrentIndex(1)
        

    # Métodos asociados
    def seleccionar_diario(self, estado):
            if estado:
                self.dia.setEnabled(True)
                self.cmbx_periodo.clear()
                self.cmbx_periodo.addItems(("00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00"))
                self.cmbx_periodo.setEnabled(True)
                self.cmbx_periodo.setCurrentIndex(0)
                

    def seleccionar_periodo(self, estado):
            if estado:
                self.dia.setEnabled(False)
                self.cmbx_periodo.clear()
                self.cmbx_periodo.addItem(" ")
                self.cmbx_periodo.setEnabled(False)
                self.cmbx_periodo.setCurrentIndex(4)


    def Iniciar(self):
        # Actualizar fecha y archivo
        self.date = self.dia.selectedDate()
        self.archivo = os.path.join(self.directorio_trabajo, self.date.toString('yyyyMMdd000000'))

        # Obtener responsable
        self.responsable = self.cmbx_resposables.currentText()

        # Emitir señal con la información
        self.inicializado.emit(self.archivo, self.directorio_trabajo, self.responsable,self.periodo)

        # Opcional: cerrar ventana luego de iniciar
        self.close()


    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath
        self.showDate(self.date)

    def visor_limpiar_completo(self):
        """Antes de cada gráfico nuevo"""
        self.visor.clear()
        self.visor.clf()
        # AGREGAAR ESTO:
        plt.close(self.visor)  # Liberar figura de matplotlib completamente

    def limpiar_estado(self):
        """Limpia figuras, visores, hilos, timers, etc., antes de cerrar."""
        try:
            if hasattr(self, 'canvas') and self.canvas is not None:
                self.canvas.deleteLater()
                self.canvas = None

            if hasattr(self, 'visor') and self.visor is not None:
                self.visor.clf()
                self.visor = None

 
        except Exception as e:
            print(f"Error en limpieza de Inicio: {e}")


    def closeEvent(self, event):
        """
        Emite la señal de cerrado para notificar a la ventana principal y realiza limpieza si es necesario.
        """
        print("Cerrando inicio")
        self.visor_limpiar_completo()
        self.limpiar_estado()
        print(self.archivo, self.directorio_trabajo, self.responsable,self.periodo)
        self.inicializado.emit(self.archivo, self.directorio_trabajo, self.responsable,self.periodo)
        self.cerrado.emit()
        super().closeEvent(event)

    def showDate(self, date):#Es como inicializar el dìa
        self.date=date
        self.archivo=self.directorio_trabajo+date.toString('yyyyMMdd000000')
        self.desplegar_mensaje()

    def cambio_periodo(self, texto):
        # asignar el valor del combobox a self.periodo
        self.periodo = texto
        self.desplegar_mensaje()

    def cambio_responsable(self, texto):
        # asignar el valor del combobox a self.periodo
        self.responsable = texto
        self.desplegar_mensaje()        
            
    def desplegar_mensaje(self):
        
        if self.periodo=='':
            mensaje = (
                "<b>DIA:</b><br>" + " PERIODO " +
                "<br><b>DIRECTORIO DE TRABAJO:</b><br>" + str(self.directorio_trabajo)+
                "<br><b>RESPONSABLE:</b><br>" + str(self.responsable)+
                "<br><b>PERIODO:</b><br>" + str(self.periodo)
                )
            
        else:
            mensaje = (
                "<b>DIA:</b><br>" + self.date.toString("yyyy\\MM\\dd") +
                "<br><b>DIRECTORIO DE TRABAJO:</b><br>" + str(self.directorio_trabajo)+
                "<br><b>RESPONSABLE:</b><br>" + str(self.responsable)+
                "<br><b>PERIODO:</b><br>" + str(self.periodo)
                )

        self.mensajes.setHtml(mensaje)
        
        


```
