---
proyecto: rsa_sismologia
tipo: contexto_tecnico
archivo: src/programa_integrado.py
temas: [orquestador_principal, maquina_estados, pila_lifo, integracion_subprogramas, pyqt5]
generado: 2026-08-24
---

# `src/programa_integrado.py` — Contexto Técnico para Agentes IA

> Contenedor principal de ventana única (`QMainWindow`) que orquesta todos los subprogramas sísmicos de la Red Sísmica de Alerta (RSA), administrando la máquina de estados, la navegación LIFO y la identidad visual institucional.

**Ruta**: `src/programa_integrado.py`  
**Lenguaje**: Python 3 (PyQt5, Matplotlib)  
**Dependencias**: `PyQt5`, `obspy`, `matplotlib`, `librerias.metodos_rsa`, `librerias.metodos_gestion`, `librerias.rsa_procesamiento`, `librerias.panel_estado`  

---

## 1. Arquitectura de Navegación y Pila LIFO

`VentanaPrincipal` gestiona el ciclo de vida de los subprogramas y la preservación de sesión mediante una pila LIFO (*Last In, First Out*):

```mermaid
stateDiagram-v2
    [*] --> Nivel1_EstadoA: Inicio

    state "Nivel 1: Estado A (Lanzamiento Limpio)" as Nivel1_EstadoA {
        [*] --> MenuBloqueado
        note right of MenuBloqueado: Menús de procesamiento inactivos\nMarca de agua RSA visible\nOpción 'Inicialización de día' activa
    }

    state "Nivel 1: Estado B (Trabajo Activo)" as Nivel1_EstadoB {
        [*] --> MenusHabilitados
        note right of MenusHabilitados: Menús activos (Diario o Período)\nSesión activa en barra superior
    }

    state "Nivel 2: Subprograma en Foco" as Nivel2 {
        [*] --> CentralWidgetMontado
        note right of CentralWidgetMontado: Subprograma montado en setCentralWidget\nMenús superiores bloqueados
    }

    Nivel1_EstadoA --> Nivel1_EstadoB: Inicialización completada (Inicio_proceso)
    Nivel1_EstadoB --> Nivel2: Invocar subprograma (apilar_estado_actual LIFO)
    Nivel2 --> Nivel1_EstadoB: Cerrar subprograma (desapilar_y_restaurar_estado LIFO)
    Nivel1_EstadoB --> Nivel1_EstadoA: Menú Inicio -> Salir (Cerrar sesión activa)
    Nivel1_EstadoA --> [*]: Menú Inicio -> Salir (Cerrar aplicación)
```

---

## 2. Componentes y Contratos de Estabilidad

1. **Pila LIFO de Navegación (`pila_estados`)**:
   * `apilar_estado_actual()`: Almacena variables de sesión, estado de cada menú y rótulos antes de abrir cualquier subprograma.
   * `desapilar_y_restaurar_estado()`: Restaura con exactitud el estado previo al cerrar cualquier módulo.
2. **Retorno de Control Atómico (`volver_estado_trabajo`)**:
   * Ejecutado de forma asíncrona mediante `QTimer.singleShot(0, self.volver_estado_trabajo)`.
   * Protegido por una guarda `if self.widget_activo is None: return` que descarta llamadas duplicadas y garantiza ejecución única.
   * **Invariante C++**: No ejecuta `delattr` sobre `QMainWindow` para no corromper punteros internos de PyQt5.
3. **Identidad Visual Oficial RSA**:
   * Icono de aplicación y banner superior (`110x50 px`).
   * Marca de agua central/derecha escalada al +50% en `paintEvent` (únicamente visible cuando no hay subprograma activo).
