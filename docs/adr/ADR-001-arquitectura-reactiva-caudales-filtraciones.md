---
proyecto: rsa_sismologia
tipo: adr
numero: 001
estado: Aprobado
fecha: 2026-08-22
decisores: [Usuario, Antigravity]
---

# ADR-001: Rediseño Reactivo Multilienzo y Flujo de Validación en Caudales y Filtraciones

## 1. Contexto y Planteamiento del Problema
El script [`modulos externos/caudales_filtraciones.py`](file:///c:/Proyectos/rsa_sismologia/modulos%20externos/caudales_filtraciones.py) utilizaba ventanas emergentes independientes de Matplotlib (`plt.show()`) y botones manuales redundantes (`boton_graficar`, `boton_graficar_caudales`, `boton_cargar_eventos_control`). Esto presentaba las siguientes deficiencias:
1. **Flujo Disperso**: Ventanas modales emergentes que tapaban la interfaz de usuario, dificultando la sincronización visual entre la serie histórica de caudales y el sismograma del día.
2. **Pérdida de Contexto y Encuadre**: Al validar marcas con `guardar_marcas()`, la gráfica se reiniciaba al inicio del día perdiendo el zoom de amplitud (`ylim`) y tiempo (`xlim`) que el analista había ajustado para recortar picos.
3. **Gestión de Mediciones Incoherentes**: No existía un mecanismo ágil para desestimar lecturas de caudal anómalas (ruido o lecturas espurias) directamente desde la gráfica sin alterar los valores físicos calculados.
4. **Respuesta Lenta**: Carga y renderizado redundante sin diezmado optimizado ni sincronización reactiva de señales Qt.

## 2. Decisión Tomada
Se rediseñó la arquitectura de la interfaz gráfica y el flujo de control del módulo:
1. **Integración Multilienzo Vertical en `QSplitter`**:
   - Se incrustaron 3 lienzos de Matplotlib (`FigureCanvasQTAgg` y `NavigationToolbar2QT` con altura fija de 24px) apilados verticalmente a la derecha en [`src/ui/caudales.ui`](file:///c:/Proyectos/rsa_sismologia/src/ui/caudales.ui):
     - **Lienzo 1 (Superior)**: Serie temporal de caudales del periodo histórico.
     - **Lienzo 2 (Medio)**: Sismograma diario de 24 horas (`CHA2_AAAAMMDD_000000.mseed`) con líneas verticales de eventos clasificados.
     - **Lienzo 3 (Inferior)**: Ventana de zoom de alta resolución ($\pm 10$ min) para marcado interactivo.
2. **Eliminación de Botones Redundantes y Automatización Reactiva**:
   - Se conectaron las señales `dateChanged` e `currentIndexChanged` para actualizar automáticamente las series y sismogramas en tiempo real, eliminando `boton_graficar`, `boton_graficar_caudales` y `boton_cargar_eventos_control`.
3. **Navegación Sincrónica Bidireccional (Top-Down)**:
   - Clic izquierdo en Lienzo 1 $\to$ Sincroniza fecha, carga traza 24h en Lienzo 2 y centra el zoom de alta resolución en Lienzo 3 sobre el instante del evento clickeado.
   - Clic derecho en Lienzo 1 $\to$ Resalta en rojo el punto para exclusión (`bandera='0'`) mediante el botón `🚫 Ignorar Punto Seleccionado`.
4. **Preservación Estricta de Encuadre (`mantener_vista=True`)**:
   - Al validar marcas o cambiar el estado de eventos, se memorizan y restauran automáticamente tanto el rango temporal (`xlim`) como el de amplitud (`ylim`), permitiendo continuar analizando los picos contiguos sin perder la escala.
5. **Discriminación de Banderas en `caudales.csv` sin Recálculo Innecesario**:
   - La desestimación de una medición conmuta únicamente la columna `bandera` a `'0'`, preservando intactos los valores de caudal calculados y filtrándolos en la visualización.

## 3. Justificación Técnica
- **Ergonomía y Velocidad Operativa**: El analista puede revisar meses de registros haciendo clic directo sobre los puntos de la curva de caudales, saltando de inmediato a la forma de onda en alta resolución.
- **Inmutabilidad de Datos Físicos**: Evita sobreescribir o distorsionar los caudales calculados entre eventos cronológicos reales, utilizando la bandera de validación (`1`/`0`) como filtro de renderizado.
- **Contención de Excepciones**: Dibuja mensajes discretos en los lienzos ante ausencia o corrupción de archivos MiniSEED en lugar de emitir ventanas de alerta intrusivas.
- **Alternativas Descartadas**:
  - *Mantener `plt.show()` emergente*: Descartado por bloquear el hilo principal de PyQt5 y fragmentar la experiencia de usuario.
  - *Recalcular caudales al ignorar un punto*: Descartado porque la fórmula de descarga física depende de la ocurrencia cronológica real del ciclo y no debe alterar mediciones históricas.

## 4. Consecuencias e Impacto
- **Positivas**:
  - Panel de control lateral compacto (~280px) maximizando el área visual de gráficos al 100% de ancho.
  - Reducción drástica del tiempo necesario para validar y depurar periodos históricos de filtraciones.
  - Trazabilidad visual inmediata: líneas verdes (confirmados / bandera 1) y rojas (ignorados o pendientes / bandera 0).
- **Riesgos / Trade-offs**:
  - Requiere que la resolución de pantalla permita visualizar cómodamente los 3 lienzos verticales apilados (mitigado con `self.showMaximized()` y `QSplitter` ajustable).

## 5. Módulos y Archivos Afectados
- [`src/ui/caudales.ui`](file:///c:/Proyectos/rsa_sismologia/src/ui/caudales.ui): Reestructuración de layout, incorporación de `QSplitter` vertical para los 3 gráficos, panel lateral compacto y cuadro de ayuda interactiva HTML.
- [`modulos externos/caudales_filtraciones.py`](file:///c:/Proyectos/rsa_sismologia/modulos%20externos/caudales_filtraciones.py): Incrustación de `FigureCanvas`, gestión de eventos de ratón sincrónicos, preservación de `xlim`/`ylim` y gestión de bandera `1`/`0`.
- [`modulos externos/caudales_filtraciones_contx.md`](file:///c:/Proyectos/rsa_sismologia/modulos%20externos/caudales_filtraciones_contx.md): Actualización técnica del contrato de datos y diagrama Mermaid.
