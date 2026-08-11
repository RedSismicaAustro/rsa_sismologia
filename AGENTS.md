# Reglas del Agente - `rsa_sismologia`

Este archivo define las reglas de comportamiento, restricciones y pautas técnicas que deben seguir tanto **Codex** como **Antigravity** al operar dentro de este repositorio.

---

## 1. Identidad y Contexto del Proyecto

* **Repositorio**: `rsa_sismologia` (Red Sísmica de Alerta - Análisis Sismológico e Instrumentación).
* **Entorno Técnico**: Python 3, PyQt5 (interfaces gráficas), ObsPy (procesamiento de datos sísmicos en formato MiniSEED/EVT), y scripts auxiliares de microcontroladores (ESP32).
* **Herramienta de desarrollo**: Optimizado para su ejecución integrada y depuración a través de Spyder y terminales de comandos de Windows.

---

## 2. Regla de Oro: Prioridad de Archivos de Contexto (`_contx.md`)

Antes de modificar o depurar cualquier script Python, el agente **DEBE** buscar y leer el archivo de contexto técnico asociado (con el sufijo `_contx.md`) en el mismo directorio o subdirectorios. Estos archivos documentan el comportamiento real, contratos de datos, riesgos específicos y checklists de regresión.

### Tabla de Correspondencia de Contextos

| Script Python | Archivo de Contexto (`_contx.md`) |
| :--- | :--- |
| [`modulos externos/acelerografo.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/acelerografo.py) | [`acelerografo_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/acelerografo_contx.md) |
| [`modulos externos/automatico.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/automatico.py) | [`automatico_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/automatico_contx.md) |
| [`modulos externos/caudales_filtraciones.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/caudales_filtraciones.py) | [`caudales_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/caudales_contx.md) |
| [`modulos externos/consolidacion_mseed.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/consolidacion_mseed.py) | [`consolidacion_mseed_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/consolidacion_mseed_contx.md) |
| [`modulos externos/Corrección de EVT por reseteo.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Correcci%C3%B3n%20de%20EVT%20por%20reseteo.py) | [`Correccion_EVT_reseteo_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Correccion_EVT_reseteo_contx.md) |
| [`modulos externos/Insercion de estaciones EVT.py`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Insercion%20de%20estaciones%20EVT.py) | [`Insercion_estaciones_contx.md`](file:///c:/proyectos/rsa_sismologia/modulos%20externos/Insercion_estaciones_contx.md) |
| [`src/programa_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/programa_integrado.py) | [`programa_integrado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/programa_integrado_contx.md) |
| [`src/librerias/analizar metodos_rsa.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/analizar%20metodos_rsa.py) | [`analizar_metodos_rsa_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/analizar_metodos_rsa_contx.md) |
| [`src/librerias/estaciones.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/estaciones.py) | [`estaciones_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/estaciones_contx.md) |
| [`src/librerias/gestor_fases.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/gestor_fases.py) | [`gestor_fases_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/gestor_fases_contx.md) |
| [`src/subprogramas/extraer_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/extraer_integrado.py) | [`extraer_integrado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/extraer_integrado_contx.md) |
| [`src/subprogramas/fases.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/fases.py) | [`fases_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/fases_contx.md) |
| [`src/subprogramas/inicio.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio.py) | [`inicio_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio_contx.md) |
| [`src/subprogramas/marcar_eventos.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/marcar_eventos.py) | [`marcar_eventos_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/marcar_eventos_contx.md) |
| [`src/subprogramas/procesamiento_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/procesamiento_integrado.py) | [`procesamiento_integrado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/procesamiento_integrado_contx.md) |
| [`src/subprogramas/reporte_acumulado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_acumulado.py) | [`reporte_acumulado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_acumulado_contx.md) |
| [`src/subprogramas/reporte_diario.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_diario.py) | [`reporte_diario_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/reporte_diario_contx.md) |

> [!IMPORTANT]
> Los archivos `_contx.md` prevalecen sobre suposiciones del agente. Si hay discrepancia entre el código actual y la descripción del contexto, el agente debe priorizar la funcionalidad real documentada y proponer correcciones conservadoras.

---

## 3. Restricciones Críticas (No hacer sin autorización)

* **Estructura de Datos**: No alterar los esquemas JSON de configuración, los formatos de la matriz de eventos o el comportamiento de `GestorFases`.
* **Nombres de Interfaz (UI)**: No renombrar widgets de PyQt5 que provengan de archivos `.ui` o que estén referenciados dinámicamente en el código.
* **Firmas de Métodos**: Mantener las firmas de los métodos y funciones existentes para evitar romper otros módulos que dependan de ellos de manera implícita.
* **Refactorización**: No realizar refactorizaciones masivas o traducciones idiomáticas del código (por ejemplo, cambiar español a inglés o viceversa). Se debe respetar la nomenclatura actual del archivo bajo edición.

---

## 4. Guía de Desarrollo e Implementación

* **Control de Rutas**: Utilizar siempre `os.path.join` o `pathlib.Path` para manejar rutas, garantizando la compatibilidad con entornos Windows.
* **Preservación de Comentarios**: Mantener todos los docstrings y comentarios existentes que no estén relacionados con las modificaciones sugeridas.
* **Depuración**: Asegurar que las validaciones previas de existencia de archivos, directorios e integridad de los datos ocurran al inicio de los flujos críticos.

---

## 5. Control de Commits (Regla `GENERA COMMIT`)

* **No Hacer Commits Automáticos**: El agente **NUNCA** debe realizar commits automáticos en Git de forma autónoma al finalizar o verificar cambios locales simples. Esto evita generar un historial de Git fragmentado y desordenado.
* **Activación por Palabra Clave**: El agente sólo generará y ejecutará un commit cuando el usuario lo solicite explícitamente escribiendo un mensaje que contenga la palabra clave **`GENERA COMMIT`**.
* **Procedimiento al Recibir `GENERA COMMIT`**:
  1. Revisar los cambios pendientes (`git status`).
  2. Preparar el área de stage (`git add .` o archivos específicos).
  3. Redactar un mensaje de commit descriptivo e integral que agrupe y ponga en contexto todas las modificaciones realizadas durante la sesión.
  4. Ejecutar el commit definitivo en una sola operación acumulada.

