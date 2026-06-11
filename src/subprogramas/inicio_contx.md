# Contexto del Script: `inicio.py`

## 1. Propósito General

El script `inicio.py` define una ventana de diálogo (`Inicio_proceso`) para la configuración inicial de un sistema de procesamiento sísmico llamado **`rsa_sismologia`**.

Su función es permitir al operador seleccionar los parámetros necesarios antes de iniciar el procesamiento de un día o período específico:

- Fecha del día a procesar.
- Directorio de trabajo (ubicación de los datos).
- Responsable del procesamiento.
- Período horario (turno).

Una vez confirmado, la ventana emite señales con estos datos para que la ventana principal del sistema comience el procesamiento.

---

## 2. Estructura del Proyecto Implícita

Por las rutas manipuladas en el script, se infiere la siguiente estructura de directorios:

```text
rsa_sismologia/
├── src/
│   ├── librerias/                  # Módulos personalizados del sistema
│   │   ├── metodos_rsa.py
│   │   └── metodos_gestion.py
│   ├── ui/
│   │   └── inicio.ui               # Interfaz diseñada en Qt Designer
│   └── inicio.py                   # Este script
├── datos/
│   └── responsables.csv            # Lista de operadores
└── otros directorios:
    ├── resultados/
    ├── logs/
    └── etc.
```

---

## 3. Dependencias Clave

### 3.1. Módulos externos

| Módulo | Uso |
|---|---|
| `sys`, `os`, `pathlib` | Manejo de rutas y configuración de `sys.path`. |
| `PyQt5.QtWidgets`, `PyQt5.QtCore` | Interfaz gráfica y señales. |
| `matplotlib` | Gráficos del panel derecho, actualmente sin uso activo. |
| `datetime` | Manejo de fechas. |

### 3.2. Módulos propios del proyecto

| Módulo | Función |
|---|---|
| `metodos_rsa.lectura_archivo` | Lee archivos CSV, principalmente `responsables.csv`. |
| `metodos_gestion.parametros_estaciones` | Obtiene configuración de canales sísmicos. |

### 3.3. Archivo `.ui`

El archivo **`inicio.ui`** corresponde a la interfaz diseñada en Qt Designer. Contiene, al menos, los siguientes elementos:

- Selector de fecha: `dia`
- Combo de responsables: `cmbx_resposables`

  > **Nota ortográfica:** en el código el objeto aparece como `cmbx_resposables`. Lo correcto ortográficamente sería `cmbx_responsables`, pero el contexto conserva el nombre real usado en el script para evitar inconsistencias.

- Combo de período: `cmbx_periodo`
- Botones: `Btn_Iniciar`, `Btn_drive`
- Radio buttons: `radioButton_diario`, `radioButton_periodo`
- Widget de mensajes HTML: `mensajes`

---

## 4. Funciones Auxiliares

### `extraer_hasta_directorio(ruta_completa, nombre_directorio)`

**Propósito:** recortar una ruta absoluta hasta el directorio especificado.

Ejemplo:

```python
extraer_hasta_directorio(
    "/home/user/rsa_sismologia/src/librerias",
    "rsa_sismologia"
)
```

Resultado esperado:

```text
/home/user/rsa_sismologia/
```

**Utilidad:** obtener la raíz del proyecto independientemente de la ubicación de ejecución.

### Configuración de `sys.path`

```python
ruta_librerias = os.path.abspath(
    os.path.join(ruta_proyecto, "src", "librerias")
)

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
```

Esta configuración inserta la ruta de `librerias` al inicio de `sys.path`, permitiendo importaciones absolutas de módulos propios del proyecto.

---

## 5. Clase `Inicio_proceso`

La clase `Inicio_proceso` representa el diálogo inicial de configuración del procesamiento.

### 5.1. Señales personalizadas

| Señal | Tipo | Emisión | Propósito |
|---|---|---|---|
| `cerrado` | `pyqtSignal()` | Al cerrar la ventana. | Notificar a la ventana principal que el diálogo terminó. |
| `inicializado` | `pyqtSignal(str, str, str, str)` | Al hacer clic en **Iniciar** y también al cerrar la ventana. | Enviar `archivo_base`, `directorio_trabajo`, `responsable` y `periodo`. |

> **Advertencia:** si el usuario hace clic en **Iniciar**, el método `Iniciar()` emite `inicializado` y luego llama a `self.close()`. Al cerrarse la ventana, `closeEvent()` vuelve a emitir `inicializado`. Por tanto, puede existir una doble emisión de la señal.

### 5.2. Constructor

```python
__init__(self, directorio_trabajo, responsable, periodo, parent=None)
```

#### Parámetros de entrada

- `directorio_trabajo`: ruta base donde están los datos.
- `responsable`: nombre del operador por defecto.
- `periodo`: turno inicial, por ejemplo `"00:00 - 12:00"`.
- `parent`: ventana padre opcional.

#### Acciones principales

1. Configura el layout:
   - Panel izquierdo: interfaz cargada desde `inicio.ui`.
   - Panel derecho: figura de `matplotlib`, reservada para futuras visualizaciones.

2. Carga la interfaz:

```python
uic.loadUi(ruta_ui, self)
```

3. Carga responsables desde CSV:

```python
datos = lectura_archivo(ruta_csv)
lista_resp = [sublista[0] for sublista in datos]
self.cmbx_resposables.addItems(lista_resp)
```

> **Nota:** el nombre usado en el script es `cmbx_resposables`. Si se corrige a `cmbx_responsables`, debe corregirse también en el archivo `.ui` y en todas las referencias del código.

4. Carga períodos predefinidos:

```python
horario = ("00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00")
self.cmbx_periodo.addItems(horario)
```

5. Carga parámetros de estaciones:

```python
self.parametros = parametros_estaciones()
```

Esta información se carga desde `metodos_gestion`, pero dentro de `inicio.py` no se utiliza activamente después de ser asignada.

6. Conecta señales de la interfaz:

| Elemento | Método conectado |
|---|---|
| `Btn_Iniciar.clicked` | `Iniciar` |
| `Btn_drive.clicked` | `seleccionar_drive` |
| `dia.clicked[QtCore.QDate]` | `showDate` |
| `radioButton_diario.toggled` | `seleccionar_diario` |
| `radioButton_periodo.toggled` | `seleccionar_periodo` |
| `cmbx_periodo.currentTextChanged` | `cambio_periodo` |
| `cmbx_resposables.currentTextChanged` | `cambio_responsable` |

7. Establece la fecha actual:

```python
d = datetime.today()
d = QDate(d.year, d.month, d.day)
self.showDate(d)
```

8. Establece por defecto el segundo período del combo:

```python
self.cmbx_periodo.setCurrentIndex(1)
```

Esto selecciona `"12:00 - 18:00"` después de cargar los períodos.

---

## 6. Métodos Principales

### `seleccionar_diario(estado)`

Activa el modo de procesamiento diario.

#### Acciones

- Habilita el selector de fecha.
- Limpia el combo de períodos.
- Restaura los tres turnos horarios.
- Habilita el combo de períodos.
- Selecciona por defecto el primer período: `"00:00 - 12:00"`.

### `seleccionar_periodo(estado)`

Activa el modo de período especial, sin fecha fija.

#### Acciones

- Deshabilita el selector de fecha.
- Limpia el combo de períodos.
- Agrega un ítem vacío `" "`.
- Deshabilita el combo.
- Intenta seleccionar el índice 4.

> **Problema potencial:** el uso de `setCurrentIndex(4)` puede causar un comportamiento inconsistente, porque el combo queda con un solo ítem. Lo más coherente sería usar `setCurrentIndex(0)` o evitar cambiar el índice.

### `Iniciar()`

```python
self.date = self.dia.selectedDate()

self.archivo = os.path.join(
    self.directorio_trabajo,
    self.date.toString("yyyyMMdd000000")
)

self.responsable = self.cmbx_resposables.currentText()

self.inicializado.emit(
    self.archivo,
    self.directorio_trabajo,
    self.responsable,
    self.periodo
)

self.close()
```

#### Función

- Obtiene la fecha seleccionada.
- Construye el nombre de archivo base en formato `yyyyMMdd000000`.
- Obtiene el responsable seleccionado.
- Emite la señal `inicializado`.
- Cierra la ventana.

> **Advertencia:** al llamar a `self.close()`, se ejecuta `closeEvent()`, que vuelve a emitir `inicializado`.

### `seleccionar_drive()`

Abre un diálogo para seleccionar el directorio de trabajo.

#### Acciones

- Permite seleccionar el directorio.
- Normaliza la ruta, agregando `/` al final si falta.
- Actualiza `self.directorio_trabajo`.
- Llama a `showDate(self.date)` para actualizar el archivo base y el mensaje mostrado.

### `showDate(date)`

Actualiza la fecha seleccionada y reconstruye `self.archivo`.

```python
self.date = date
self.archivo = self.directorio_trabajo + date.toString("yyyyMMdd000000")
self.desplegar_mensaje()
```

> **Observación:** en `showDate()` se construye la ruta por concatenación directa, mientras que en `Iniciar()` se usa `os.path.join()`. Esto puede generar diferencias si `directorio_trabajo` no termina con `/`.

### `cambio_periodo(texto)`

Actualiza `self.periodo` con el texto seleccionado en `cmbx_periodo` y refresca el mensaje mostrado.

```python
self.periodo = texto
self.desplegar_mensaje()
```

### `cambio_responsable(texto)`

Actualiza `self.responsable` con el texto seleccionado en `cmbx_resposables` y refresca el mensaje mostrado.

```python
self.responsable = texto
self.desplegar_mensaje()
```

### `desplegar_mensaje()`

Actualiza el widget `mensajes` con información en HTML:

- Día.
- Directorio de trabajo.
- Responsable.
- Período.

Si `self.periodo == ""`, el mensaje muestra `"PERIODO"` en lugar de la fecha. En los demás casos, muestra la fecha en formato:

```text
yyyy\MM\dd
```

---

## 7. Manejo de Gráficos y Limpieza

| Método | Propósito |
|---|---|
| `visor_limpiar_completo()` | Limpia la figura de `matplotlib` y la cierra. |
| `limpiar_estado()` | Elimina referencias al canvas y al visor. |

El panel derecho con gráficos está implementado, pero no se utiliza activamente en este script. Está reservado para futuras expansiones, como visualización de formas de onda, espectros u otros productos gráficos.

### `visor_limpiar_completo()`

```python
self.visor.clear()
self.visor.clf()
plt.close(self.visor)
```

### `limpiar_estado()`

Elimina el `canvas` mediante `deleteLater()` y luego pone `self.canvas = None`.

También limpia la figura y pone `self.visor = None`.

---

## 8. Evento de Cierre

### `closeEvent(event)`

```python
def closeEvent(self, event):
    print("Cerrando inicio")
    self.visor_limpiar_completo()
    self.limpiar_estado()
    print(self.archivo, self.directorio_trabajo, self.responsable, self.periodo)
    self.inicializado.emit(
        self.archivo,
        self.directorio_trabajo,
        self.responsable,
        self.periodo
    )
    self.cerrado.emit()
    super().closeEvent(event)
```

#### Observación importante

La señal `inicializado` se emite incluso si el usuario cierra la ventana sin hacer clic en **Iniciar**.

Esto asegura que la ventana principal siempre reciba una señal, pero también puede causar procesamientos con parámetros incompletos o no validados.

Además, si el cierre ocurre después de presionar **Iniciar**, la señal puede emitirse dos veces.

---

## 9. Flujo de Trabajo Típico

```text
1. Usuario abre la ventana principal del sistema.
   ↓
2. Se crea Inicio_proceso con valores por defecto.
   ↓
3. Usuario selecciona:
   - Fecha, o modo período.
   - Directorio de trabajo, opcionalmente con el botón "drive".
   - Responsable.
   - Período horario.
   ↓
4. Usuario hace clic en "Iniciar".
   ↓
5. Se emite la señal:
   inicializado(archivo, directorio, responsable, período)
   ↓
6. Se llama a self.close().
   ↓
7. Se ejecuta closeEvent().
   ↓
8. Se emite nuevamente inicializado(...), además de cerrado().
   ↓
9. La ventana principal recibe las señales y comienza el procesamiento sísmico.
```

> **Nota:** si la ventana principal no controla la doble emisión, podría intentar iniciar el procesamiento dos veces.

---

## 10. Posibles Problemas y Mejoras Detectadas

| Problema | Descripción | Riesgo |
|---|---|---|
| Doble emisión de `inicializado` | `Iniciar()` emite la señal y luego `closeEvent()` la vuelve a emitir. | Alto |
| `setCurrentIndex(4)` en modo período | Si solo hay un ítem, el índice 4 queda fuera de rango. | Medio |
| Nombre `cmbx_resposables` | El nombre contiene una falta ortográfica. Lo correcto sería `cmbx_responsables`, pero debe coincidir con el `.ui`. | Bajo |
| `self.periodo` puede cambiar después del constructor | Se actualiza con `cambio_periodo()`, pero depende de las señales del combo. | Bajo |
| Construcción de ruta inconsistente | `showDate()` concatena texto; `Iniciar()` usa `os.path.join()`. | Medio |
| Normalización de rutas inconsistente | `seleccionar_drive()` normaliza agregando `/`, pero el constructor no necesariamente recibe una ruta normalizada. | Bajo |
| `closeEvent()` emite `inicializado` sin validación | Puede emitir valores incompletos si el usuario cierra sin configurar nada. | Medio |
| Gráfico sin uso activo | El panel derecho consume recursos sin aportar funcionalidad actual. | Bajo |
| Redundancia en `visor_limpiar_completo()` | `clear()` + `clf()` + `plt.close()` puede ser excesivo. | Muy bajo |
| Variable global `datos_sismo` sin uso | Se declara `datos_sismo = {}`, pero no se usa en este script. | Muy bajo |

---

## 11. Integración con el Resto del Sistema

### 11.1. Módulos que utiliza

- `metodos_rsa.lectura_archivo`: lectura de `responsables.csv`.
- `metodos_gestion.parametros_estaciones`: configuración de canales sísmicos.

### 11.2. Módulos que lo utilizan

Se espera que la ventana principal, probablemente `main.py` o un módulo equivalente:

- Cree una instancia de `Inicio_proceso`.
- Escuche la señal `inicializado`.
- Inicie el procesamiento del día o período al recibirla.
- Escuche la señal `cerrado` para saber que el diálogo terminó.

Ejemplo de uso esperado:

```python
self.inicio = Inicio_proceso(dir_trabajo, responsable_def, periodo_def)
self.inicio.inicializado.connect(self.procesar_dia)
self.inicio.cerrado.connect(self.limpiar_dialogo)
self.inicio.show()
```

---

## 12. Resumen

`inicio.py` es un módulo de orquestación inicial dentro de un sistema más grande de análisis sísmico.

No realiza procesamiento sísmico directamente. Su función es preparar el contexto de trabajo:

- Fecha.
- Responsable.
- Directorio.
- Período.

Luego notifica esos datos mediante señales a la ventana principal para que comience el trabajo real.

Su diseño sigue el patrón de diálogo de configuración previa a tarea, común en aplicaciones de procesamiento de datos por lotes.

---

## 13. Información Técnica Adicional

| Elemento | Detalle |
|---|---|
| Framework GUI | PyQt5 |
| Gráficos | Matplotlib, backend Qt5Agg |
| Formato de archivo base | `yyyymmdd000000` |
| Ejemplo de archivo base | `20250101000000` |
| Formato de fecha en UI | `yyyy\MM\dd` |
| CSV de responsables | Cada fila tiene una lista; se toma el primer elemento como nombre. |
| Nombre real del combo de responsables | `cmbx_resposables` |
| Nombre ortográficamente recomendado | `cmbx_responsables` |
