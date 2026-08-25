---
proyecto: rsa_sismologia
tipo: adr
numero: '005'
estado: Aprobado
fecha: 2026-08-25
decisores: [Usuario, Agente]
---

# ADR-005: Sincronización Bidireccional de Formato Binario .fas (HYPO71), Configuración CSV Interactiva y Ergonomía Visual en Fases

## 1. Contexto y Planteamiento del Problema
El subprograma de marcado de fases (`src/subprogramas/fases.py`) requería modernización y consistencia en tres frentes críticos:
1. **Falta de soporte del formato binario `.fas`**: Las fases marcadas históricamente se almacenaban en archivos binarios estructurados de 16 ranuras compatibles con HYPO71 (con polaridades de impulso, tipos y ponderaciones de 0 a 4). La versión anterior sólo leía/escribía archivos `.json`, lo que generaba pérdida de sincronización con eventos procesados fuera de la aplicación.
2. **Falta de interactividad en los parámetros CSV**: Los parámetros de filtrado y aporte de cada estación en la matriz diaria (`AAAAMMDD000000.csv`) se presentaban como una etiqueta de sólo lectura (`lbl_info_csv`), obligando al analista a recurrir a otros subprogramas para ajustar canales, aportes o frecuencias de corte.
3. **Ergonomía de Interfaz y Navegación**: Se requería mantener la ventana principal incrustada sin popups flotantes invasivos, visualización de parámetros sismológicos en rojo en cada traza, lanzamiento de zoom fino por doble clic en la traza/lista, y corrección del solapamiento del logo y calendario en el orquestador principal.

## 2. Decisión Tomada
1. **Ingeniería Inversa y Sincronización Bidireccional `.fas` $\leftrightarrow$ `.json`**:
   * Implementación de decodificador binario (`decodificar_archivo_fas`) que extrae P, S, Coda, tipo de impulso (`I`/`E`), polaridad (`+`/`-`) y pesos (0..4) de las 16 ranuras binarias de 61 bytes.
   * Implementación de constructor binario (`construir_archivo_fas`) para generar archivos `.fas` canónicos de longitud exacta y sincronizarlos con `{evento}.json` en tiempo real.
2. **Panel Interactivo de Configuración CSV In-Situ**:
   * Reemplazo de `lbl_info_csv` por widgets interactivos (`chk_csv_aporta`, `spbox_csv_canal`, `spbox_csv_orden`, `spbox_csv_finf`, `spbox_csv_fsup`).
   * Sincronización bidireccional inmediata con el token `EEEECBFFIISS` en la matriz de eventos y persistencia en disco con `escritura_archivo`.
3. **UX Sismológico y Navegación Reactiva**:
   * Despliegue de parámetros sismológicos en color rojo en la esquina superior derecha de cada subplot (`ax.set_title(loc='right')`).
   * Lanzamiento de la subventana de detalle (`VentanaGrafico`) por doble clic tanto en el gráfico de traza como en la lista de estaciones.
   * Optimización del encabezado del orquestador (`programa_integrado.py`) con logo agrandado ($155\times 65$ px) y calendario compacto en `inicio.ui`.

## 3. Justificación Técnica
- **Compatibilidad Total con el Histórico Sísmico RSA**: Permite auditar y procesar eventos marcados en décadas previas en formato HYPO71 sin requerir migraciones manuales de base de datos.
- **Flujo de Trabajo Continuo sin Fricción**: El analista puede modificar filtros de estaciones y pesos de fases en la misma pantalla sin cambiar de módulo ni abrir ventanas emergentes redundantes.
- **Doble Retroalimentación Visual**: Los parámetros están visibles tanto en los controles interactivos como en el encabezado de cada señal, minimizando errores de interpretación.

## 4. Consecuencias e Impacto
- **Positivas**:
  * Coexistencia armónica entre formato `.fas` legado y JSON moderno.
  * Modificación instantánea de filtros y aportes persistidos en el CSV del día.
  * Interfaz más limpia, responsiva y ergonómica.
- **Riesgos / Limitaciones**:
  * El formato `.fas` tiene un límite inherente de 16 estaciones fijas impuesto por el estándar HYPO71 de la RSA; canales adicionales se preservan en JSON y CSV.

## 5. Módulos y Archivos Afectados
- `src/subprogramas/fases.py`: Decodificación/codificación `.fas`, interactividad CSV, doble clic en canvas y cabeceras en rojo.
- `src/ui/marcar_fases.ui`: Sustitución de etiquetas estáticas por layouts y controles interactivos CSV y HYPO71.
- `src/librerias/gestor_fases.py`: Esquema oficial de colores P (rojo), S (naranja), Coda (verde) y preservación de metadatos.
- `src/programa_integrado.py`: Logo institucional agrandado y espaciado de datos generales.
- `src/ui/inicio.ui` y `src/subprogramas/inicio.py`: Calendario compacto y cuadro de información legible.
- `src/subprogramas/fases_contx.md`, `src/librerias/gestor_fases_contx.md`, `src/programa_integrado_contx.md`, `src/subprogramas/inicio_contx.md`: Actualización de contextos técnicos.
