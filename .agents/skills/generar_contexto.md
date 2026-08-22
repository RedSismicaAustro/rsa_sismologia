# Skill: Generar Contexto Técnico de Archivo/Componente

> [!IMPORTANT]
> **Reglas Madres:** Esta habilidad genera/actualiza documentación y contextos técnicos exclusivamente en el entorno de archivos locales. El agente **NO ejecuta commits** ni interactúa con servicios o repositorios remotos de GitHub.

**Descripción de Activación:** Ejecuta este flujo ÚNICAMENTE cuando el usuario indique: **"genera el contexto de [nombre_archivo.ext]"** o variantes similares.

**Objetivo:** Analizar el código/configuración de un archivo y generar un documento de contexto técnico estandarizado que sirva como memoria semántica para agentes IA, usando la Opción C: el contexto vive en el proyecto, pero el índice en RSA-Metodologias incluye un resumen de una línea + enlace al repo de GitHub.

---

## Pasos de Ejecución

### 1. Localización y Lectura del Archivo
- Busca el archivo solicitado en el directorio de trabajo actual.
- Lee el contenido completo para comprender su funcionamiento, dependencias y arquitectura.

### 2. Identificación de la Ruta de Salida
- Localiza la raíz del proyecto al que pertenece el archivo.
- La ruta de destino SIEMPRE es `<raiz_del_proyecto>/docs/context/`.
- El archivo se nombrará: `<nombre_sin_extension>_context.md`.
  - Ejemplo: `mqtt_coordinator.py` → `docs/context/mqtt_coordinator_context.md`

### 3. Análisis del Archivo
- **Metadatos:** Proyecto, lenguaje/formato, dependencias, LOC.
- **Descripción:** Una línea sobre el propósito principal.
- **Arquitectura:** Diagrama Mermaid del flujo de datos o estructura interna.
- **Configuraciones:** Variables de entorno, puertos, constantes clave.
- **Componentes/Funciones/Servicios:** Tabla de elementos principales.
- **Limitaciones/TODOs:** Límites críticos conocidos.

### 4. Escritura del Archivo de Contexto

Usa la siguiente estructura:

```markdown
---
proyecto: [nombre_del_proyecto]
tipo: contexto_tecnico
archivo: [ruta_relativa_en_producción]
temas: [tema1, tema2]
generado: YYYY-MM-DD
---
# [Nombre del Archivo] — Contexto para Agentes IA

> [Descripción de una línea]

**Ruta**: `[ruta]`  
**LOC**: [N] | **Lenguaje**: [lenguaje] | **Dependencias**: [deps]  
**Proceso**: [cómo se ejecuta]

---

## Arquitectura

[Explicación]

```mermaid
[diagrama]
```

---

## Configuraciones / Variables de Entorno

[detalle]

---

## Componentes / Funciones / Servicios Clave

| Elemento | Descripción |
|----------|-------------|
| `elemento` | [descripción] |

---

## Limitaciones Conocidas / TODOs

- [Limitación 1]
```

### 5. Actualización del Índice (Opción C)
- Abre `rsa/RSA-Metodologias/indice/indice_tematico.md`.
- Bajo la sección `## Contextos Técnicos`, añade o actualiza la entrada del entorno/proyecto:
  ```markdown
  - **acelerografo**:
    - `mqtt_coordinator.py`: [Descripción de una línea] → [RSA-Acelerografo/docs/context/mqtt_coordinator_context.md](https://github.com/RedSismicaAustro/RSA-Acelerografo/blob/main/docs/context/mqtt_coordinator_context.md)
  ```
- **Si el entorno no existe**, créalo bajo `## Contextos Técnicos`.
- **No dupliques** entradas existentes; actualiza si ya existe.

### 6. Confirmación al Usuario
- Reporta la ruta del archivo de contexto generado.
- Resume las dependencias y arquitectura detectadas.
- Confirma la actualización del índice.
