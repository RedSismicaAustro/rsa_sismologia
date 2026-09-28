---
proyecto: rsa_sismologia
tipo: regla_agente
archivo: .agents/rules/10-codigo-python.md
temas: [python39, entorno_oficial, estilo, rutas_windows, excepciones, retrocompatibilidad]
origen: AGENTS.md
---

# 10 — Código Python: Entorno, Estilo y Contratos Técnicos

> **Propósito**: Fijar el intérprete oficial de validación y las directivas de escritura de código Python para el procesamiento sismológico.

---

## 1. Entorno de Ejecución Oficial (dato crítico)

> [!IMPORTANT]
> **Intérprete oficial y único de validación**: `C:\entornos\venv_py309\Scripts\python.exe` — **Python 3.9**.
>
> El núcleo del procesamiento sísmico es **ObsPy**, que es **estable y funcional en Python 3.9**, y **no** en 3.11.

| Recurso | Estado | Uso permitido |
|:---|:---|:---|
| `C:\entornos\venv_py309` (Python 3.9) | ✅ **OFICIAL / OPERATIVO** | Validación, ejecución y referencia de APIs. Es el que usan los 7 lanzadores `.bat` y también `Spyder.bat`. |
| `C:\entornos\venv_esp32` | ✅ Operativo, pero **ajeno** a este repositorio | Solo MicroPython/ESP32 (`esp_32/`). |
| [`src/entorno.yml`](../../src/entorno.yml) (conda `sismologia`, Python 3.11) | ⚠️ **LEGADO / NO OPERATIVO** | **Prohibido** usarlo como referencia de APIs, sintaxis o dependencias. |

**Consecuencias obligatorias:**

1. **Prohibida la sintaxis exclusiva de 3.10+**: nada de `match/case`, `typing.Self`, `tomllib`, `ExceptionGroup`, `itertools.pairwise`, uniones `X | Y` en anotaciones evaluadas, ni `zip(strict=True)`.
2. Ante duda sobre una firma de ObsPy, PyQt5, Matplotlib o ReportLab, **verificarla contra el venv 3.9**, nunca contra la documentación de la última versión.
3. Los `.pyc` de `cpython-311` presentes en los `__pycache__` provienen del entorno legado: **son ruido**, no evidencia de compatibilidad.

---

## 2. Idioma y Nomenclatura

* **Todo en español**: variables, métodos, funciones, clases, comentarios y docstrings, con nombres descriptivos del dominio sismológico.
* **Prohibidas las traducciones idiomáticas**: no convertir español a inglés (ni viceversa) en código existente. Se respeta el idioma del archivo bajo edición.
* **Prohibido renombrar** funciones, métodos, clases o variables existentes sin autorización expresa.

---

## 3. Estilo y Estructura

* **PEP 8** como base, sin reformateos masivos de archivos ajenos a la tarea.
* **Métodos cohesivos**: se **permite y fomenta** que una función supere las 20 líneas cuando eso preserva un flujo lógico continuo y legible. No fragmentar en funciones artificiales solo por longitud.
* **Optimización**: cuidar complejidad algorítmica, estructuras de control y uso de CPU/memoria al manipular series temporales extensas (streams de 24 h, matrices de 101 estaciones).
* **Preservación de comentarios**: mantener todos los docstrings y comentarios existentes que no se relacionen con la modificación solicitada.
* **Sin código muerto ni parches intermedios**: se prioriza el flujo directo y limpio sobre soluciones transitorias.

---

## 4. Manejo de Rutas (Windows)

* Usar siempre `os.path.join` o `pathlib.Path`. **Prohibido** codificar barras (`/` o `\`) a mano en rutas.
* **Prohibido** concatenar rutas absolutas fijas a `G:\`. La resolución es dinámica mediante `metodos_gestion.obtener_directorios(archivo)` y `extraer_hasta_directorio()`.
* Portabilidad dev/producción: el código debe funcionar tanto en el árbol local como en las unidades de red del laboratorio.

---

## 5. Excepciones y Validaciones

* Control granular con `try/except/finally`; **nunca** `except:` desnudo ni silencios de excepción sin registro.
* **Validaciones preventivas al inicio del flujo crítico**: existencia de archivos y directorios, integridad de datos, permisos y codificación.
* Codificación explícita (UTF-8 / cp1252) al leer archivos heredados del sistema sismológico.
* Los errores deben reportarse con contexto suficiente para el analista (ruta, archivo, evento, estación).

---

## 6. Contratos de Librerías y E/S

* **E/S atómica**: usar `metodos_rsa.lectura_archivo()` y `rsa_io.escritura_archivo()` en lugar de `open()` directo para los archivos del sistema.
* Librerías de dominio y su alcance:
  * **ObsPy**: Stream/Trace, lectura MiniSEED y EVT, filtrado Butterworth, detección de gaps, decimado.
  * **PyQt5**: señales/slots, hilos (`QThread`) — ver [`20-interfaz-pyqt5.md`](20-interfaz-pyqt5.md).
  * **Matplotlib** y **ReportLab**: gráficos y boletines PDF.
* **Prohibido alterar firmas de métodos y funciones existentes**: otros módulos dependen de ellas de forma implícita.
* **Retrocompatibilidad obligatoria**: al extender una función, añadir **parámetros opcionales con valor por defecto** (`def fn(a, b, nuevo_param=None):`) para no romper llamadores.

---

## 7. Checklist de Verificación

- [ ] El código es ejecutable y fue validado con `C:\entornos\venv_py309\Scripts\python.exe` (3.9).
- [ ] No introduje sintaxis ni APIs exclusivas de Python 3.10+.
- [ ] Nombres, comentarios y docstrings en español, coherentes con el archivo.
- [ ] Rutas resueltas con `os.path.join` / `pathlib.Path` y `obtener_directorios()`.
- [ ] Validaciones de existencia e integridad al inicio del flujo.
- [ ] Firmas existentes intactas; extensiones mediante parámetros opcionales.
