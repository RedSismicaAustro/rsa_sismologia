---
proyecto: rsa_sismologia
tipo: adr
numero: 003
estado: Aprobado
fecha: 2026-08-23
decisores: Usuario, Agente (Antigravity)
---

# ADR-003: Máquina de Estados Jerárquica LIFO, Interceptor Universal de Subprogramas y Desacoplamiento de Diagnóstico

## 1. Contexto y Planteamiento del Problema
La interfaz gráfica principal (`src/programa_integrado.py`) presentaba inconsistencias en la navegación y control del ciclo de vida al invocar y cerrar subprogramas sismológicos (*Marcar*, *Extraer*, *Procesamiento*, *Fases*, *Reportes*):
1. **Pérdida de Estado al Salir**: Al cerrar un subprograma, la ventana principal no restauraba con precisión el estado previo de los menús según el modo seleccionado (**Diario** con turnos vs **Período** consolidado), requiriendo reiniciar el flujo.
2. **Dependencia y Acoplamiento en Subprogramas**: Ciertos subprogramas (como `fases.py` con su botón `boton_salir`) no notificaban el cierre de forma estandarizada, provocando que la ventana principal quedara con menús bloqueados.
3. **Intrusión Visual de Paneles**: Se intentó superponer el diagnóstico del día en la página de lanzamiento, lo cual generaba ruido visual y rompía la ergonomía del área de trabajo.
4. **Filtro Inadecuado de Estaciones**: El diagnóstico desplegaba estaciones acelerográficas de evento (EVT) que no forman parte del monitoreo continuo diario.

---

## 2. Decisión Tomada

Se adoptó una arquitectura limpia y robusta compuesta por cuatro pilares:

1. **Máquina de Estados Jerárquica con Pila LIFO (*Last In, First Out*)**:
   * **Nivel 1, Estado A (Inicial / No Inicializado)**: Pantalla limpia con marca de agua institucional RSA y menús de procesamiento bloqueados.
   * **Nivel 1, Estado B (Trabajo Activo)**: Día configurado en modo Diario o Período con los menús correspondientes habilitados.
   * **Nivel 2 (Subprograma en Foco)**: Subprograma incrustado en `setCentralWidget` con menús superiores deshabilitados.
   * **Instantánea LIFO**: Antes de abrir un subprograma se apila el estado completo (`apilar_estado_actual`); al cerrarse, se desapila (`desapilar_y_restaurar_estado`) recuperando la configuración exacta previa.

2. **Interceptor Universal de Cierre en `VentanaPrincipal`**:
   * `cargar_widget_menu()` envuelve dinámicamente el método `closeEvent` del subprograma montado y mapea todos los nombres estándar de botones de salida (`boton_salir`, `Btn_salir`, `Btn_Salir`, `btn_salir`, `Btn_cancelar`, `actionSalir`).
   * **Principio**: Los subprogramas no se modifican; la ventana principal asume la responsabilidad del ciclo de vida.

3. **Desacoplamiento Modular del Panel de Diagnóstico (`panel_estado.py`)**:
   * Se extrajo `PanelEstadoJornada` a [`src/librerias/panel_estado.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/panel_estado.py) para uso exclusivo dentro del subprograma de inicio (`Inicio_proceso`), dejando la página principal limpia.
   * Se aplicó el filtro estricto: $\text{HAB\_CANAL} == \text{'1'} \land \text{HAB\_GRAFICO} == \text{'1'}$, restringiendo el monitoreo a las 12 estaciones de registro continuo.

4. **Flujo de Salida Escalonado**:
   * Desde un subprograma &rarr; Regresa a Nivel 1, Estado B.
   * Desde Nivel 1, Estado B &rarr; **Inicio &rarr; Salir** limpia la sesión y regresa a Nivel 1, Estado A (para escoger otra fecha/turno).
   * Desde Nivel 1, Estado A &rarr; **Inicio &rarr; Salir** cierra completamente la aplicación.

---

## 3. Justificación Técnica
- **Aislamiento de Módulos**: Los subprogramas sismológicos se mantienen como cajas negras sin dependencias cruzadas con el contenedor principal.
- **Robustez en Entornos Interactivos (Spyder)**: La arquitectura LIFO evita fugas de estado o banderas desincronizadas en ejecuciones sucesivas con `%runfile`.
- **Claridad Ergonómica**: El analista trabaja sobre una interfaz despejada con el logo institucional y recibe diagnóstico en tiempo real únicamente al inicializar la jornada.

---

## 4. Consecuencias e Impacto
- **Positivas**:
  - Navegación predecible y consistente entre todos los módulos del sistema.
  - Cero subventanas flotantes o parpadeos.
  - Corrección automática del retorno en subprogramas con nomenclaturas dispares (ej. `fases.py`).
- **Riesgos / Trade-offs**:
  - Requiere que cualquier nuevo subprograma que se integre en el futuro sea montado a través de `cargar_widget_menu()` para heredar la protección LIFO.

---

## 5. Módulos y Archivos Afectados
- [`src/programa_integrado.py`](file:///c:/proyectos/rsa_sismologia/src/programa_integrado.py): Implementación del gestor de pila LIFO, interceptor dinámico de `closeEvent` y menú de salida jerárquico.
- [`src/subprogramas/inicio.py`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio.py): Sincronización del modo diario, filtro de 12 estaciones y carga modular de `PanelEstadoJornada`.
- [`src/librerias/panel_estado.py`](file:///c:/proyectos/rsa_sismologia/src/librerias/panel_estado.py): Nuevo componente modular de diagnóstico sismológico.
- [`src/programa_integrado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/programa_integrado_contx.md): Contexto técnico actualizado.
- [`src/subprogramas/inicio_contx.md`](file:///c:/proyectos/rsa_sismologia/src/subprogramas/inicio_contx.md): Contexto técnico actualizado.
- [`src/librerias/panel_estado_contx.md`](file:///c:/proyectos/rsa_sismologia/src/librerias/panel_estado_contx.md): Contexto técnico generado.
