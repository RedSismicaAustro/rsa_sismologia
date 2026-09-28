---
proyecto: rsa_sismologia
tipo: regla_agente
archivo: .agents/rules/20-interfaz-pyqt5.md
temas: [pyqt5, qt_designer, invariantes_cpp, maquina_estados, qthread, ux_ui]
origen: AGENTS.md
---

# 20 — Interfaz Gráfica: PyQt5, Qt Designer e Invariantes C++

> **Propósito**: Blindar la estabilidad del binding PyQt5/C++ y la ergonomía científica de las interfaces, evitando las fallas que ya se documentaron en los ADR 003, 004 y 006.

---

## 1. Invariantes C++ (violarlos corrompe punteros del binding)

> [!CAUTION]
> Estas tres prohibiciones son **causa raíz conocida de cierres abruptos** de la aplicación:

1. **NUNCA** usar `delattr` sobre instancias o atributos de `QMainWindow` / `QWidget`.
2. **NUNCA** llamar `plt.close()` sobre figuras incrustadas en `FigureCanvasQTAgg`.
   * Alternativa obligatoria: `self.figura.clear()` seguido de `self.canvas.draw()`.
3. **NUNCA** reemplazar widgets ni vaciar layouts sin pasar por los métodos previstos de la máquina de estados.

---

## 2. Nombres de Interfaz (UI)

* **Prohibido renombrar** widgets PyQt5 provenientes de archivos `.ui` o referenciados dinámicamente en el código (`self.btn_graficar`, `self.tabla_eventos`, `self.date_edit`, `objectName` en general).
* Renombrar un `objectName` rompe silenciosamente la conexión `uic.loadUi` ↔ código.

---

## 3. Flujo Híbrido `.ui` / Qt Creator

| Caso | Acción obligatoria |
|:---|:---|
| **Módulo existente** | Editar su archivo `.ui` en [`src/ui/`](../../src/ui) según sea necesario; el usuario puede inspeccionarlo en Qt Designer. |
| **Módulo nuevo** | Generar un `.ui` base con layouts limpios y `objectName` **descriptivos en español**, para que el usuario lo abra, lo inspeccione y lo ajuste visualmente **antes** de la conexión en Python. |

---

## 4. Arquitectura de Subprogramas (ADR-003 / ADR-004)

* Los subprogramas montados en `centralWidget` deben ser **`QWidget` puro**, nunca `QMainWindow` (un `QMainWindow` insertado como widget central produce comportamientos erráticos de menús).
* Ciclo de vida estándar:
  * El subprograma expone la señal `cerrado = pyqtSignal()`.
  * El retorno del control a la ventana principal es **asíncrono y atómico**: `QTimer.singleShot(0, self.volver_estado_trabajo)` con guarda de reentrada (`self._retomando_control`).
* **Prohibido manipular la pila LIFO** (`pila_estados`) fuera de `apilar_estado_actual()` / `desapilar_y_restaurar_estado()`.
* La marca de agua institucional solo se dibuja cuando **no** hay subprograma activo; el `paintEvent` siempre cierra con `painter.end()` protegido por `try/finally`.

---

## 5. Concurrencia

* Todo proceso pesado (corte de MiniSEED, filtrado, inversión hipocentral, generación de PDF) se encapsula en **`QThread`** para mantener fluida la interfaz.
* Durante el procesamiento: **deshabilitar** los controles implicados, mostrar **barra de progreso** y estado visual claro.
* Prohibido bloquear el hilo de la GUI con bucles de espera o `sleep`.

---

## 6. Estándares UX/UI Científicos

* Alineación rigurosa con `QFormLayout` y `QGridLayout`.
* Redimensionamiento adaptativo: `Expanding` en gráficos y tablas (dentro de `QSplitter`), `Preferred`/`Fixed` en paneles de control.
* *Tooltips* con **unidades sismológicas** explícitas (Hz, sps, km, °, UTC, counts, nm/s).
* Etiquetado consistente de colores de aporte: **azul = estación que aporta (`B=1`)**, **gris = no aporta (`B=0`)**.
* Separación de responsabilidades: la lógica de datos no se mezcla con el pintado de la interfaz (delegación de UI, ADR-004).

---

## 7. Checklist de Verificación

- [ ] Ningún `delattr` sobre objetos Qt ni `plt.close()` sobre canvas embebidos.
- [ ] Ningún `objectName` ni widget existente renombrado.
- [ ] Subprogramas nuevos implementados como `QWidget` con señal `cerrado`.
- [ ] Retorno de control vía `QTimer.singleShot` con guarda de reentrada.
- [ ] Procesos pesados en `QThread`, con controles deshabilitados y progreso visible.
- [ ] Tooltips con unidades y colores de aporte coherentes con la convención azul/gris.
