# PROCESAMIENTO INTEGRADO

## Contexto General del Script

Este script es la aplicación principal (GUI) de un sistema de procesamiento sismológico integrado llamado **PROCESAMIENTO INTEGRADO**. Es una herramienta profesional para el análisis, procesamiento y gestión de datos sísmicos.

---

# Arquitectura del Sistema

## Estructura de Directorios (inferida del código)

```text
rsa_sismologia/                # Proyecto raíz
├── src/
│   ├── librerias/            # Bibliotecas compartidas
│   └── subprogramas/         # Módulos funcionales
│       ├── fases.py
│       ├── extraer_integrado.py
│       ├── marcar_eventos.py
│       ├── procesamiento_integrado.py
│       ├── reporte_diario.py
│       ├── reporte_acumulado.py
│       ├── inicio.py
│       └── otras_redes.py
├── datos/                    # Datos (CSVs, configuraciones)
├── rsa_procesamiento.py      # Módulo central de procesamiento
└── programa_integrado.py     # Punto de entrada principal
```

## Propósito Principal

Sistema de escritorio para sismólogos e investigadores que permite:

1. Inicializar días de trabajo con datos sísmicos.
2. Procesar registros continuos de estaciones sísmicas.
3. Detectar, marcar y extraer eventos sísmicos.
4. Generar reportes diarios y por períodos.
5. Integrar datos de otras redes (IGEPN, USGS).

---

# Análisis Detallado del Código

## 1. Configuración Inicial

### Localización dinámica del proyecto

```python
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    # Busca 'rsa_sismologia' en la ruta y recorta hasta ahí
```

### Propósito

Permite localizar dinámicamente la carpeta raíz del proyecto (`rsa_sismologia`) independientemente del directorio desde el que se ejecute la aplicación.

### Configuración de rutas

- `ruta_librerias`: acceso a bibliotecas compartidas.
- `ruta_datos`: acceso a configuraciones y archivos de datos.

Ambas rutas son agregadas a `sys.path` para facilitar la importación de módulos.

### Importaciones relevantes

- `matplotlib.use('Qt5Agg')`: integración con PyQt5.
- Módulos funcionales:
  - fases
  - extraer_integrado
  - marcar_eventos
  - procesamiento_integrado
  - reporte_diario
  - reporte_acumulado
  - otras_redes
- `rsa_procesamiento`: motor principal del procesamiento sísmico.

---

## 2. Clase Principal: `VentanaPrincipal`

### Atributos Clave

| Atributo | Propósito | Valor por defecto |
|-----------|------------|------------------|
| directorio_trabajo | Ruta base de trabajo | `G:/Mi unidad/DIA/` |
| responsable | Analista responsable | `RSA` |
| periodo | Turno de procesamiento | `''` |
| archivo | Archivo del día actual | `YYYYMMDD000000` |
| datos_inicializados | Estado de inicialización | `False` |
| widget_activo | Widget actualmente mostrado | `None` |

### Máquina de Estados

```text
[ESTADO INICIAL]
        ↓
(Inicializar día)
        ↓
[INICIALIZANDO]
        ↓
(Éxito)
        ↓
[ESTADO TRABAJO]
        ↓
(Abrir subprograma)
        ↓
[SUBPROGRAMA ACTIVO]
        ↓
(Cerrar)
        ↓
[ESTADO TRABAJO]
```

### Métodos de transición

#### `configurar_estado_inicial()`
Establece un estado limpio con únicamente el menú de inicio habilitado.

#### `cargar_widget_inicializacion()`
Carga la interfaz de inicialización del día.

#### `completar_inicializacion()`
Realiza la transición al estado operativo.

#### `volver_estado_trabajo()`
Restaura completamente el entorno de trabajo después de cerrar un subprograma.

---

# 3. Estructura de Menús

## Menú 1: Inicio

- Inicialización de día.
- Salir.

**Comportamiento dual de salida:**

- Si no hay datos cargados → cierra la aplicación.
- Si existe una sesión activa → vuelve al estado inicial.

---

## Menú 2: Configuración

Disponible únicamente cuando el período está vacío.

Opciones:

- Estaciones.
- Enlaces digitales.
- Ingreso de datos:
  - RG (Registro Continuo)
  - EV (Eventos)
- Datos externos:
  - IGEPN
  - USGS

---

## Menú 3: Informes

- Reporte por período.
- Reporte de enjambre sísmico.
- Generación de archivos Shape (GIS).

---

## Menú 4: Procesamiento

Disponible cuando existe un período definido.

Opciones:

- Marcar eventos en registro continuo.
- Extraer eventos detectados.
- Procesamiento de eventos extraídos.
- Análisis de fases sísmicas.
- Reextracción directa.

---

## Menú 5: Otros Informes

- Reporte diario.

---

## Menú 6: Ayuda

- Acerca de.

---

# 4. Gestión de Ventanas (Subprogramas)

## Patrón de carga de widgets

```python
def cargar_widget_menu(self, widget, titulo, mostrar_detalles):
    # 1. Verifica inicialización
    # 2. Limpia widget actual
    # 3. Establece nuevo widget central
    # 4. Deshabilita menús
    # 5. Conecta señal de cierre
```

### Objetivo

Garantizar que solo un subprograma permanezca activo al mismo tiempo, evitando conflictos de estado.

## Subprogramas Integrados

| Función | Clase | Ubicación |
|----------|--------|-----------|
| Inicialización | Inicio_proceso | subprogramas.inicio |
| Marcado de eventos | Marcar_evento | subprogramas.marcar_eventos |
| Extracción | Extraer_evento | subprogramas.extraer_integrado |
| Procesamiento | Procesar_evento | subprogramas.procesamiento_integrado |
| Fases sísmicas | VentanaPrincipal | subprogramas.fases |
| Reporte diario | Reporte_diario | subprogramas.reporte_diario |
| Reporte por período | Reporte_periodo | subprogramas.reporte_acumulado |
| Datos externos | Otras_redes | subprogramas.otras_redes |

---

# 5. Características Técnicas Destacadas

## Prevención de Errores de Estado

### Protección de variables críticas

Las listas:

- `variables_permitidas`
- `variables_esenciales`

evitan que atributos fundamentales sean eliminados durante procesos de limpieza.

### Limpieza segura

```python
limpiar_estado_completo()
```

Elimina únicamente variables temporales identificadas mediante el prefijo:

```text
tmp_
```

### Gestión segura de señales

Antes de destruir widgets se desconectan señales activas para evitar referencias inválidas.

---

## Ciclo de Vida de Widgets

```python
widget.destroyed.connect(on_widget_closed)
widget.cerrado.connect(on_widget_closed)
```

Se utilizan simultáneamente:

- Señal nativa de Qt (`destroyed`)
- Señal personalizada (`cerrado`)

para asegurar la restauración correcta del estado.

---

## Mejoras de Interfaz

### Fondo institucional

- Logo de la Universidad de Cuenca.
- Opacidad aproximada: 20%.

### Barra superior

- Logo RSA.
- Título dinámico.
- Información contextual del procesamiento.

### Maximización automática

```python
showMaximized()
```

Permite aprovechar completamente el espacio de trabajo.

---

# 6. Flujo de Trabajo Típico

```text
1. Usuario ejecuta la aplicación
        ↓
2. Inicio → Inicializar día
        ↓
3. Inicio_proceso configura:
        - Directorio de trabajo
        - Responsable
        - Período
        ↓
4. Se habilitan menús según el período
        ↓
5. Procesamiento:
        Marcar
           ↓
        Extraer
           ↓
        Procesar
           ↓
        Fases
           ↓
        Reportes
        ↓
6. Cierre del subprograma
        ↓
7. Retorno al estado de trabajo
```

---

# 7. Posibles Problemas Identificados

| Problema | Riesgo | Recomendación |
|-----------|---------|--------------|
| Ruta fija `G:/Mi unidad/DIA/` | Dependencia de Google Drive montado | Hacer configurable |
| `plt.ioff()` sin `plt.close('all')` | Acumulación de figuras | Limpiar figuras al cerrar |
| Logo fijo `logo rsa.png` | Fallo si el archivo no existe | Validar existencia |
| `extraer_dia()` bloqueante | Congelamiento de interfaz | Ejecutar mediante `QThread` |
| Variables temporales sin uso | Código innecesario | Eliminar o implementar |

---

# 8. Conclusión

El sistema constituye una plataforma integral para procesamiento sismológico, caracterizada por:

- Arquitectura robusta basada en máquinas de estado.
- Gestión segura de memoria y widgets.
- Flujo de trabajo estructurado para análisis sísmico.
- Integración con redes externas (IGEPN y USGS).
- Mecanismos preventivos para evitar inconsistencias de estado.

La aplicación cubre todo el ciclo operativo de procesamiento sísmico, desde la carga inicial de información hasta la generación de reportes finales, manteniendo un enfoque orientado a la estabilidad, trazabilidad y facilidad de uso.