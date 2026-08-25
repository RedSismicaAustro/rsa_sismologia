---
proyecto: rsa_sismologia
tipo: contexto_tecnico
archivo: src/librerias/rsa_utilidades.py
temas: [utilidades_sismologicas, generacion_sis, resolucion_rutas, remuestreo_64hz, binarios_rsa]
generado: 2026-08-24
---

# `src/librerias/rsa_utilidades.py` — Contexto Técnico para Agentes IA

> Módulo transversal de utilidades sismológicas de bajo nivel: resolución heurística de rutas del repositorio `DIA`, conversión de series de tiempo a formato binario `.sis` (remuestreadas a 64 Hz para eventos de tipo `SISMO`), conversión binaria a MiniSEED y creación de estructuras de carpetas.

**Ruta**: `src/librerias/rsa_utilidades.py`  
**Lenguaje**: Python 3 (ObsPy, SciPy Signal, NumPy)  
**Dependencias**: `obspy`, `scipy.signal`, `numpy`, `pathlib.Path`, `re`  
**Proceso**: Invocado como soporte de bajo nivel por `extraer_integrado.py`, `rsa_procesamiento.py` y `metodos_gestion.py`.

---

## 1. Arquitectura y Flujo de Procesamiento

```mermaid
graph TD
    A[Cualquier ruta de archivo o subcarpeta bajo DIA] --> B[referencia_directorio_completa]
    B --> C{Extracción de Fecha YYYYMMDD}
    C -->|Por nombre de archivo| D[Regex 20\\d{6}]
    C -->|Por carpetas DIA/YYYY/YYYY_MM/YYYY_MM_DD| E[Desglose de partes de ruta]
    D --> F[Ruta Canónica .../DIA/AAAAMMDD000000]
    E --> F
    
    G[Evento tipo SISMO en extraccion] --> H[Lectura MiniSEED por estación analógica]
    H --> I[Remuestreo con scipy.signal.resample a 64 Hz]
    I --> J[Ajuste de muestras y ensamblaje con cabecera_sismo]
    J --> K[Generación de archivo binario AAAAMMDD_hhmmss.sis]
```

---

## 2. Contratos de Datos y E/S

* **Función `referencia_directorio_completa(archivo) -> str`**:
  * Entrada: Ruta arbitraria de archivo (ej. `C:/DIA/2026/2026_08/2026_08_24/mseed/registros/LABR_20260824.mseed`).
  * Salida: Ruta canónica sin extensión `C:/DIA/20260824000000`.

* **Generación de Archivo `.sis` (`extraccion`)**:
  * Solo se construye si `tipo_evento == "SISMO"`.
  * Busca la cabecera binaria en candidatos: `directorios['Directorio_trabajo']/cabecera_sismo`, `datos/cabecera_sismo`, `C:/DIA/cabecera_sismo`.
  * Remuestrea canales analógicos a 64 Hz con enteros de 32 bits (`int32`).

---

## 3. Componentes y Métodos Clave

| Función | Firma | Descripción |
|---|---|---|
| `referencia_directorio_completa` | `(archivo) -> str` | Resuelve la ruta canónica `DIA/AAAAMMDD000000` extrayendo la fecha por regex o desglose jerárquico. |
| `extraccion` | `(t_ini, t_fin, canales, tipo_evento, directorios, parametros, ...)` | Recorta trazas sísmicas, genera MiniSEED de eventos y emite `.sis` binario para sismos. |
| `binario_a_mseed` | `(ruta_binario, ruta_salida, ...)` | Convierte registros binarios directos a archivos MiniSEED con metadatos de traza. |
| `ubicacion` | `(latitud, longitud) -> list` | Normaliza coordenadas geográficas en grados decimales. |
| `generar_directorios_unidades_basicas` | `(directorio_base)` | Crea las carpetas del día (`mseed/registros`, `mseed/eventos`, `sis`, `reporte`). |

---

## 4. Decisiones de Diseño y Algoritmos

1. **Resolución Heurística y Robusta de Fechas**:
   * `referencia_directorio_completa` implementa búsqueda múltiple: primero inspecciona el stem del archivo buscando patrones `20\d{6}`, luego itera de forma inversa por las carpetas secundarias, asegurando compatibilidad con estructuras planas o anidadas.
2. **Localización de `cabecera_sismo`**:
   * Búsqueda en cascada en directorios de trabajo, datos del proyecto y raíz `C:/DIA` para garantizar la generación del binario `.sis` en cualquier estación de trabajo.
3. **Copia Segura de Streams**:
   * Antes de mutar componentes o ejecutar `detrend`, se genera `stcanal = stcanal.copy()` previniendo corrupción de trazas en memoria compartida.

---

## 5. Riesgos Técnicos y Deuda Técnica

* **Índices de Canales Analógicos Fuera de Rango**:
  * Se aplica guarda `min(max(0, componente), len(stcanal) - 1)` para evitar excepciones `IndexError` si una estación tiene menos canales de los esperados.

---

## 6. Checklist de Verificación y Regresión

- [x] `referencia_directorio_completa` resuelve correctamente nombres de archivo con guiones o prefijos.
- [x] Generación de `.sis` solo ocurre para tipo `SISMO` y omite eventos de ruido o calibración.
- [x] Remuestreo a 64 Hz produce tamaño exacto de muestras con padding en caso de discrepancias mínimas.
