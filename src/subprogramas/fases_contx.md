---
proyecto: rsa_sismologia
tipo: contexto_tecnico
archivo: src/subprogramas/fases.py
temas: [marcado_fases, formato_fas, hypo71, persitencia_json_fas, configuracion_csv, pyqt5, obspy, ventana_grafico]
generado: 2026-08-25
---

# `src/subprogramas/fases.py` — Contexto Técnico para Agentes IA

> Subprograma de visualización y marcado interactivo de fases sísmicas (P, S, Coda), sincronización bidireccional con formato binario `.fas` (HYPO71), edición interactiva de la matriz de eventos `.csv`, y despliegue integrado en `VentanaPrincipal` y `VentanaGrafico`.

**Ruta**: `src/subprogramas/fases.py`  
**Lenguaje**: Python 3 (PyQt5, ObsPy, Matplotlib)  
**Dependencias**: `PyQt5`, `obspy`, `matplotlib`, `librerias.gestor_fases.GestorFases`, `librerias.metodos_rsa`, `librerias.metodos_gestion`, `librerias.rsa_io`  
**Proceso**: Invocado desde `src/programa_integrado.py` (`Procesamiento -> Marcar fases`).

---

## 1. Arquitectura y Flujos de Ejecución

```mermaid
graph TD
    A[Inicio: Cargar Día Inicializado self.archivo] --> B[obtener_directorios y lectura_archivo CSV]
    B --> C{Filtrar filas con tipo_evento == 'SISMO'}
    C -- Hay Sismos --> D[Poblar self.combo_sis y cargar primer sismo]
    C -- 0 Sismos --> E[Mostrar mensaje en canvas: 'No existen eventos clasificados como SISMO']
    
    D --> F{Existe .fas binario en dia/?}
    F -- Sí --> G[decodificar_archivo_fas: P, S, Coda, Tipo, Disparo, Peso]
    F -- No --> H{Existe .json?}
    H -- Sí --> I[Cargar fases desde .json]
    H -- No --> J[Detección automática ObsPy / Valores iniciales]
    
    G --> K[Sincronizar self.fases_detectadas y guardar .json]
    I --> K
    J --> K
    
    K --> L[Renderizar Trazas en VentanaPrincipal: 4 slots fijos]
    L --> M[Doble Clic en Traza o Lista -> Abrir VentanaGrafico]
    M --> N[VentanaGrafico: Nombre completo estacion, sin leyenda, zoom clic derecho]
    N --> O[Al cerrar VentanaGrafico: Guardar .json/.fas, actualizar combos y graficos]
```

---

## 2. Contratos de Datos y Formato Binario `.fas` (HYPO71)

### 2.1. Estructura del Diccionario `self.fases_detectadas[archivo]`
```python
{
    "P": [4.87],            # Tiempo de arribo fase P en segundos relativos
    "S": [16.11],           # Tiempo de arribo fase S en segundos relativos
    "Coda": [20.47],        # Tiempo absoluto de término de coda en segundos
    "tipo_p": "I",          # 'I' (Impulsivo), 'E' (Emergente) o ' '
    "polaridad_p": "+",     # '+' (Up/Compresión), '-' (Down/Dilatación) o ' '
    "peso_p": 0,            # Ponderación HYPO71 de 0 (100%) a 4 (0%/Excluir)
    "polaridad_s": " ",     # '+' / '-' / ' '
    "peso_s": 2             # Ponderación HYPO71 de 0 a 4
}
```

### 2.2. Estructura Binaria Canónica del Archivo `.fas` (16 ranuras x 61 bytes)
Cada ranura de estación contiene bloques binarios estructurados de longitud fija:
* **Bloque P (24 bytes)**: `{cod_est:<4}{tipo_p}P{polaridad_p}{peso_p} {AAMMDDhhmmss.ss}` precedido por headers `\x02\x00\x01\x00\x08\x00\x18\x00`.
* **Bloque S (9 bytes)**: `{segundo:5.2f} S{polaridad_s}{peso_s}` precedido por float64 Little-Endian de segundos y headers `\x08\x00\x09\x00`.
* **Bloque Coda (4 bytes)**: `{coda_dur:4.1f}` precedido por headers `\x02\x00\x01\x00\x08\x00\x04\x00`.

### 2.3. Formato del Token de Estación en Matriz CSV (`EEEECBFFIISS`)
* `EEEE`: Código de estación (4 caracteres, ej. `LABR`, `CUSH`).
* `C`: Canal / Componente (`1`, `2`, `3`, `Z`, etc.).
* `B`: Aporte a la solución (`1` = Aporta, `0` = No aporta).
* `FF`: Orden del filtro Butterworth (2 dígitos, ej. `02`).
* `II`: Frecuencia de corte inferior $f_{\text{inf}}$ en Hz (2 dígitos, ej. `01`).
* `SS`: Frecuencia de corte superior $f_{\text{sup}}$ en Hz (2 dígitos, ej. `10`).

---

## 3. Componentes y Métodos Clave

| Método / Clase | Tipo | Descripción |
|---|---|---|
| `VentanaPrincipal` | `QMainWindow` | Ventana principal que incrusta controles y visualizador paginado. |
| `cargar_dia()` / `cambio_de_fecha()` | Método | Resuelve directorios del día inicializado, lee el CSV y extrae exclusivamente sismos. |
| `decodificar_archivo_fas(ruta_fas)` | Método | Realiza ingeniería inversa sobre el archivo `.fas` extrayendo marcas, polaridades y pesos. |
| `construir_archivo_fas(ruta_fas)` | Método | Genera el archivo binario estructurado de 16 ranuras canónicas `.fas`. |
| `al_cambiar_estacion_seleccionada(current)` | Slot | Sincroniza los combos y controles interactivos al cambiar de estación en la lista. |
| `actualizar_controles_estacion_activa(archivo)` | Método | Helper para sincronizar los controles al cerrar la subventana de detalle. |
| `al_modificar_parametros_estacion()` | Slot | Actualiza `fases_detectadas` y guarda concurrentemente `{evento}.json` y `{evento}.fas`. |
| `al_modificar_config_csv_estacion()` | Slot | Actualiza el token `EEEECBFFIISS`, guarda el archivo `.csv` y refresca el filtrado. |
| `VentanaGrafico` | `QMainWindow` | Subventana de zoom y marcado interactivo con nombre oficial de estación, sin leyenda, zoom con clic derecho, cálculo de distancia y sincronización total al salir. |

---

## 4. Decisiones de Diseño y Algoritmos

1. **Unificación con la Arquitectura Global del Sistema**:
   * Se eliminó el selector de fecha independiente dentro de `marcar_fases.ui`. La fecha de trabajo proviene exclusivamente del día inicializado en `programa_integrado.py`.
2. **Matriz CSV como Fuente Única de Clasificación**:
   * Los sismos se filtran estrictamente evaluando `fila[2] == 'SISMO'` en el archivo CSV delimitado por `;`.
3. **Optimización de la Subventana `VentanaGrafico`**:
   * Visualización limpia de borde a borde sin cuadro flotante de leyenda (`ax.legend()` removido).
   * **Clic Derecho**: Alterna el modo Zoom rectangular (o doble clic derecho para restaurar vista global *Home*).
   * **Clic Izquierdo**: Pica y arrastra marcas P, S y Coda sin interferencias.
   * **Barra Superior**: Permite modificar parámetros HYPO71 in situ y ver el cálculo de `Ts-Tp` y la distancia epicentral aproximada en tiempo real.
4. **Sincronización Bidireccional `.fas` $\leftrightarrow$ `.json`**:
   * Persistencia transparente al mover marcas o cerrar ventanas.

---

## 5. Checklist de Verificación y Regresión

- [x] Carga automática de los sismos del día inicializado desde `programa_integrado.py`.
- [x] Mensaje informativo claro en el canvas cuando la jornada no contiene sismos clasificados.
- [x] Apertura de `VentanaGrafico` con nombre completo de estación (ej. `LOMA DE LA VIRGEN (LABR)`).
- [x] Zoom con clic derecho y restauración con doble clic derecho.
- [x] Sincronización instantánea de marcas, archivo `.json` y archivo binario canónico `.fas` al cerrar la subventana.
