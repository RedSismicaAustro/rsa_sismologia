---
proyecto: rsa_sismologia
tipo: contexto_tecnico
archivo: src/programa_integrado.py
temas: [interfaz_grafica, maquina_estados, pila_lifo, integracion_subprogramas, pyqt5]
generado: 2026-08-23
---

# `src/programa_integrado.py` — Contexto Técnico para Agentes IA

> Orquestador principal y contenedor de ventana única (`QMainWindow`) para todos los módulos y subprogramas de procesamiento sísmico de la Red Sísmica de Alerta (RSA).

**Ruta**: `src/programa_integrado.py`  
**Lenguaje**: Python 3 (PyQt5, Matplotlib)  
**Dependencias**: `PyQt5`, `obspy`, `matplotlib`, `librerias.metodos_rsa`, `librerias.metodos_gestion`, `librerias.rsa_procesamiento`  
**Proceso**: `python src/programa_integrado.py` o `%runfile` en Spyder IDE.

---

## 1. Arquitectura y Máquina de Estados (LIFO Stack)

`VentanaPrincipal` opera como un contenedor de ventana única con una máquina de estados jerárquica y una pila LIFO de preservación de estado:

```mermaid
stateDiagram-v2
    [*] --> Nivel1_EstadoA: Lanzamiento

    state "Nivel 1: Estado A (Inicial / No Inicializado)" as Nivel1_EstadoA {
        [*] --> MenuBloqueado
        note right of MenuBloqueado: Menús deshabilitados\nOpción 'Inicialización de día' activa
    }

    state "Nivel 1: Estado B (Trabajo Activo / Día Inicializado)" as Nivel1_EstadoB {
        [*] --> MenusHabilitados
        note right of MenusHabilitados: Menús activos (Diario o Período)\nOpción 'Inicialización' oculta
    }

    state "Nivel 2: Subprograma en Foco" as Nivel2 {
        [*] --> SubprogramaMontado
        note right of SubprogramaMontado: Menús superiores bloqueados\nSubprograma como centralWidget
    }

    Nivel1_EstadoA --> Nivel1_EstadoB: Completar inicialización (Inicio_proceso)
    Nivel1_EstadoB --> Nivel2: Invocar subprograma (apilar_estado_actual LIFO)
    Nivel2 --> Nivel1_EstadoB: Salir de subprograma (desapilar_y_restaurar_estado LIFO)
    Nivel1_EstadoB --> Nivel1_EstadoA: Menú Inicio -> Salir (Cerrar sesión activa)
    Nivel1_EstadoA --> [*]: Menú Inicio -> Salir (Cerrar aplicación)
```

---

## 2. Componentes y Métodos Clave

| Método / Atributo | Tipo | Descripción |
|---|---|---|
| `pila_estados` | Lista (LIFO) | Almacena instantáneas de estado (`dict`) antes de entrar a cada subprograma. |
| `apilar_estado_actual()` | Método | Guarda el estado completo de variables, menús, títulos y modo activo (Diario vs Período). |
| `desapilar_y_restaurar_estado()` | Método | Restaura con exactitud la instantánea superior de la pila LIFO al cerrar cualquier subprograma. |
| `configurar_estado_inicial()` | Método | Establece el Estado A limpio (menús deshabilitados, ventana lista para inicializar). |
| `establecer_estado_trabajo()` | Método | Establece el Estado B con los menús habilitados para el modo configurado y ventana limpia. |
| `cargar_widget_menu(widget, titulo)` | Método | Impregna el subprograma como `centralWidget`, conecta señales y envuelve `closeEvent` dinámicamente. |
| `accion_salir_ejecutar()` | Método | Gestiona la salida jerárquica: de Estado B regresa a Estado A, de Estado A cierra el software. |
| `paintEvent(event)` | Evento | Dibuja la marca de agua del nuevo logo RSA (+50% escala, 60% eje X) solo en estado inactivo. |

---

## 3. Contratos y Reglas de Integración

1. **Cero Subventanas Flotantes**: Todos los subprogramas se montan exclusivamente en `self.setCentralWidget(widget)`.
2. **Interceptor Universal de Cierre**: `cargar_widget_menu` envuelve el `closeEvent` del subprograma para garantizar que cualquier salida invoque `volver_estado_trabajo()` sin requerir modificaciones en los subprogramas.
3. **Identidad Visual Oficial**: Utiliza el logo institucional RSA en la barra superior (`110x50 px`) y como marca de agua en el fondo.
