---
proyecto: rsa_sismologia
tipo: adr
numero: 003
estado: Aprobado
fecha: 2026-08-24
decisores: Usuario, Agente (Antigravity)
---

# ADR-003: Máquina de Estados Jerárquica LIFO, Interceptor Universal de Subprogramas, Desacoplamiento de Diagnóstico y Estabilidad C++

## 1. Contexto y Planteamiento del Problema
La interfaz gráfica principal (`src/programa_integrado.py`) y sus módulos satélites (especialmente `extraer_integrado.py`) presentaban inconsistencias de navegación, fugas de memoria y bloqueos de bajo nivel:
1. **Pérdida de Estado al Salir**: Al cerrar un subprograma, la ventana principal no restauraba con precisión el estado previo de los menús según el modo seleccionado (**Diario** con turnos vs **Período** consolidado).
2. **Dependencia y Acoplamiento en Subprogramas**: Ciertos submódulos (como `fases.py` con su botón `boton_salir`) no notificaban el cierre de forma estandarizada, bloqueando la interfaz.
3. **Reseteos del Núcleo en Spyder por Corrupción C++**:
   * Llamadas destructivas a `plt.close(self.visor)` durante la graficación interactiva rompían el gestor C++ de `FigureCanvasQTAgg`.
   * Bucles `delattr(self, var)` sobre la instancia `QMainWindow` eliminaban punteros internos de PyQt5.
   * Acumulación de copias no recolectadas de streams de 24 horas (`Stream.copy()`) al extraer 30 o más eventos.
4. **Persistencia Visual Residual**: Tras guardar un evento extraído, el visor mantenía las trazas del evento anterior en pantalla.

---

## 2. Decisión Tomada

Se adoptó una arquitectura integral de alta estabilidad basada en cinco directivas:

1. **Máquina de Estados Jerárquica con Pila LIFO (*Last In, First Out*)**:
   * **Nivel 1, Estado A (Inicial / No Inicializado)**: Pantalla limpia con marca de agua institucional RSA y menús de procesamiento bloqueados.
   * **Nivel 1, Estado B (Trabajo Activo)**: Día configurado en modo Diario o Período con menús habilitados.
   * **Nivel 2 (Subprograma en Foco)**: Subprograma incrustado en `setCentralWidget` con menús superiores deshabilitados.
   * **Instantánea LIFO**: `apilar_estado_actual()` guarda el estado completo y `desapilar_y_restaurar_estado()` lo recupera con exactitud al cerrar.

2. **Interceptor Universal de Cierre Asíncrono en `VentanaPrincipal`**:
   * `cargar_widget_menu()` envuelve el `closeEvent` y mapea los botones de salida estándar.
   * `volver_estado_trabajo()` opera de forma asíncrona (`QTimer.singleShot(0, ...)`) con una guarda atómica `if self.widget_activo is None: return`, descartando señales duplicadas.

3. **Protección de Punteros C++ e Integridad de `QMainWindow`**:
   * Se prohibió terminantemente el uso de `delattr` sobre `QMainWindow`, delegando la limpieza a la recolección de basura nativa (`gc.collect()`).
   * Se eliminó `plt.close(self.visor)` del ciclo de dibujo interactivo en `extraer_integrado.py`, usando únicamente `self.visor.clear()`.

4. **Gestión Plana de Memoria y Refresco Visual Inmediato**:
   * Unificación de `copiar_stream_dia()` en `extraer_integrado.py` para reciclar streams de ObsPy antes de cada copia, manteniendo el consumo de RAM constante.
   * En `guardar_evento()`, se ejecuta `visor_limpiar_completo()` seguido de `self.canvas.draw()`, garantizando que el lienzo quede en blanco inmediatamente tras la extracción.

5. **Desacoplamiento Modular del Panel de Diagnóstico (`panel_estado.py`)**:
   * Se extrajo `PanelEstadoJornada` a [`src/librerias/panel_estado.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/panel_estado.py) exclusivo para `Inicio_proceso`, con filtro estricto de las 12 estaciones continuas ($\text{HAB\_CANAL} == \text{'1'} \land \text{HAB\_GRAFICO} == \text{'1'}$).

---

## 3. Justificación Técnica
- **Aislamiento C++/Python**: Respetar las convenciones del binding PyQt5/C++ evita violaciones de acceso de memoria (`0xC0000005`) en Windows.
- **Flujo Ergonómico Sin Residuos**: El operador sismológico trabaja con una pantalla limpia al guardar y regresa al estado de trabajo previo sin interrupciones.

---

## 4. Consecuencias e Impacto
- **Positivas**:
  - Eliminación total de reinicios de kernel al salir de subprogramas tras procesar múltiples eventos.
  - Navegación fluida y predecible entre todos los módulos del sistema.
  - Preservación exacta de la sesión activa (Diario vs Período).
- **Riesgos / Trade-offs**:
  - Todo nuevo subprograma debe incrustarse a través de `cargar_widget_menu()` para heredar la protección LIFO.

---

## 5. Módulos y Archivos Afectados
- [`src/programa_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/programa_integrado.py): Gestor LIFO, interceptor asíncrono, guarda atómica y protección de punteros `QMainWindow`.
- [`src/subprogramas/extraer_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/extraer_integrado.py): Limpieza segura de canvas, gestión plana de streams en `copiar_stream_dia`, y borrado del lienzo al guardar.
- [`src/subprogramas/inicio.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio.py): Integración modular de diagnóstico y filtro de 12 estaciones.
- [`src/librerias/panel_estado.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/panel_estado.py): Componente modular desacoplado de diagnóstico.
