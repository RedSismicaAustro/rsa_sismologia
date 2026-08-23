---
proyecto: rsa_sismologia
tipo: adr
numero: 002
estado: Aprobado
fecha: 2026-08-23
decisores: [Usuario, Antigravity]
---

# ADR-002: Pipeline Modular Independiente y Estandarización de Registros Acelerográficos EVT

## 1. Contexto y Planteamiento del Problema
El procesamiento de datos provenientes de acelerógrafos autónomos Kinemetrics (ETNA, K2, Altus) presentaba deudas técnicas acumuladas y duplicidad aparente de propósitos entre dos herramientas del repositorio:
1. [`modulos externos/Corrección de EVT por reseteo.py`](file:///c:/Proyectos/rsa_sismologia/modulos%20externos/Correcci%C3%B3n%20de%20EVT%20por%20reseteo.py):
   - Inestabilidad al reconstruir descargas complejas con múltiples caídas de energía (reseteo del reloj interno a 1980 y reinicio de prefijos de serie de nombres como `EVT`, `EAA`, `EAB`).
   - Búsqueda rígida y fallida de catálogos diarios (`AAAAMMDD000000.csv` hardcodeado).
   - Filtros excesivamente estrictos que descartaban sismos reales por derivas naturales de osciladores de cuarzo (*clock drift*).
   - Borrado destructivo de archivos crudos en la carpeta de origen al exportar.
2. [`modulos externos/Insercion de estaciones EVT.py`](file:///c:/Proyectos/rsa_sismologia/modulos%20externos/Insercion%20de%20estaciones%20EVT.py):
   - Existencia de 6 deudas técnicas: diccionarios con claves duplicadas, escrituras MiniSEED no estandarizadas, ausencia de verificación de la unidad montada `O:\KINEMETRICS` (VM VirtualBox `kw2asc.exe`), fugas de memoria en bucles de lectura masiva y falta de deduplicación criptográfica de archivos idénticos.
3. **Cuestión Arquitectónica**: Se evaluó si convenía fusionar ambos scripts en un único programa o preservar su independencia modular.

## 2. Decisión Tomada
Se adoptaron las siguientes decisiones estructurales y operativas:

1. **Preservación de la Independencia Modular de Scripts**:
   - Se mantiene la **separación estricta de responsabilidades** en un pipeline de dos etapas consecutivas e independientes:
     - **Etapa 1 (Triaje y Calibración Temporal en Disco)**: `Corrección de EVT por reseteo.py` resuelve el "juego de ventanas" de múltiples reseteos, filtra ruidos (`Ctrl+R`) vs eventos (`Ctrl+S`), ancla cada período contra el catálogo de la red central y reorganiza los archivos en carpetas físicas `AAAAMMDD/` ajustando sus estampas `os.utime`.
     - **Etapa 2 (Conversión a MiniSEED e Inserción en Catálogo)**: `Insercion de estaciones EVT.py` toma las carpetas por día ya limpias, convierte las señales a MiniSEED estándar, maneja el fallback a la VM `kw2asc` si se requiere reconstrucción ASCII y actualiza atómicamente las matrices de eventos de la RSA.
2. **Preservación del Modelo Temporal `mtime` de Campo**:
   - Se mantiene la fecha de modificación (`mtime`) del sistema de archivos FAT16/FAT32 grabado por el firmware Kinemetrics como el vector temporal primario del equipo, preservando la compatibilidad histórica.
3. **Estandarización Canónica de MiniSEED y Escritura Atómica**:
   - Todo archivo MiniSEED generado se estandariza con codificación **`STEIM1`** y tamaño de bloque **`reclen=512`** mediante escritura atómica (`.tmp` $\to$ `.mseed`), garantizando interoperabilidad universal (SeisComP, SAC, Geopsy, ObsPy).
4. **Resguardo No Destructivo de Datos Originales**:
   - Las carpetas de descarga de campo se tratan como **respaldos crudos de solo lectura**, eliminando cualquier instrucción de borrado en origen.
5. **Creación de la Skill Oficial de Auditoría e Integración**:
   - Se instituyó la 5ta habilidad en [`.agents/skills/auditoria_librerias_e_integracion.md`](file:///c:/Proyectos/rsa_sismologia/.agents/skills/auditoria_librerias_e_integracion.md) para auditar llamadores de librerías compartidas y guiar la futura integración progresiva de estos módulos satélite hacia [`src/programa_integrado.py`](file:///c:/Proyectos/rsa_sismologia/src/programa_integrado.py).

## 3. Justificación Técnica
- **Respeto a la Física del Hardware Sismológico**: Un apagón de energía en el ETNA crea una discontinuidad temporal de duración indeterminada. Forzar un único $\Delta T$ global o asumir que el calce local de $\pm 5$ minutos es suficiente corrompe los catálogos. La segmentación por series alfabéticas (`EVT`, `EAA`, `EAB`) es el único método matemáticamente riguroso para resolver múltiples caídas de reloj.
- **Robustez y Rendimiento**: La deduplicación por hash SHA-1 evita reprocesar sismos ya indexados, la compresión STEIM1 reduce el almacenamiento en un 70% respecto a enteros de 32 bits, y la liberación de memoria en `finally:` (`st.clear()`, `del st`, `gc.collect()`) previene bloqueos del sistema operativo.
- **Alternativas Descartadas**:
  - *Fusionar ambos scripts en un solo ejecutable masivo*: Descartado para no acoplar la interfaz gráfica interactiva de triaje con los procesos de procesamiento por lotes de directorios completos.

## 4. Consecuencias e Impacto
- **Positivas**:
  - Pipeline claro, predecible y reproducible para la gestión de campañas de descarga de acelerógrafos.
  - Cero riesgo de pérdida de datos crudos de campo durante la calibración.
  - Compatibilidad total de los archivos MiniSEED resultantes con el resto del ecosistema sismológico internacional.
  - Código compilado limpiamente y verificado con `python -m py_compile`.
- **Riesgos / Trade-offs**:
  - El analista debe ejecutar primero la herramienta de reseteo cuando la descarga contenga series de 1980 antes de invocar la inserción al catálogo central.

## 5. Módulos y Archivos Afectados
- [`modulos externos/Corrección de EVT por reseteo.py`](file:///c:/Proyectos/rsa_sismologia/modulos%20externos/Correcci%C3%B3n%20de%20EVT%20por%20reseteo.py): Soporte multi-serie, carga flexible de catálogos, diálogo interactivo por $\Delta T$ y exportación no destructiva.
- [`modulos externos/Insercion de estaciones EVT.py`](file:///c:/Proyectos/rsa_sismologia/modulos%20externos/Insercion%20de%20estaciones%20EVT.py): Resolución de 6 deudas técnicas, compresión `STEIM1`, `reclen=512`, fallback seguro a `O:\KINEMETRICS`, SHA-1 y limpieza de memoria.
- [`ayuda/ayuda_insercion_evt.html`](file:///c:/Proyectos/rsa_sismologia/ayuda/ayuda_insercion_evt.html) y [`datos/ayuda_insercion_evt.html`](file:///c:/Proyectos/rsa_sismologia/datos/ayuda_insercion_evt.html): Manuales interactivos actualizados.
- [`.agents/skills/auditoria_librerias_e_integracion.md`](file:///c:/Proyectos/rsa_sismologia/.agents/skills/auditoria_librerias_e_integracion.md): Nueva skill oficial de integración y gobernanza de dependencias.
- [`AGENTS.md`](file:///c:/Proyectos/rsa_sismologia/AGENTS.md): Registro oficial de la suite de 5 skills del repositorio.
