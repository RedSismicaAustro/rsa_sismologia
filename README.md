# RSA Sismología (`rsa_sismologia`)

Sistema de análisis sismológico, procesamiento de señales sísmicas (MiniSEED/EVT), marcado de fases y generación de boletines oficiales de la Red Sísmica del Austro (RSA).

---

## 📚 Documentación y Manuales del Sistema

- **Manual y Reglas del Agente**: [`AGENTS.md`](file:///c:/proyectos/rsa_sismologia/AGENTS.md)
- **Contexto Técnico Maestro**: [`docs/contexto_maestro_agente.md`](file:///c:/proyectos/rsa_sismologia/docs/contexto_maestro_agente.md)
- **Estructura de Datos `DIA`**: [`docs/contexto_estructura_datos_dia.md`](file:///c:/proyectos/rsa_sismologia/docs/contexto_estructura_datos_dia.md)
- **Archivos de Configuración**: [`docs/contexto_archivos_configuracion_datos.md`](file:///c:/proyectos/rsa_sismologia/docs/contexto_archivos_configuracion_datos.md)

---

## 🔄 Protocolo de Sesión con Agentes IA

### 🟢 Inicio de Sesión (Scope Lock):
```text
Considera las reglas y skills definidos en .agents/rules y .agents/skills.
Para esta sesión, nuestro directorio de trabajo exclusivo será [DIRECTORIO]. No modifiques ni busques archivos fuera de esta ruta a menos que te lo pida. 
Revisa los archivos del directorio [DIRECTORIO] para que entiendas el contexto actual del proyecto. Todavia no modifiques ni crees ningun archivo.
```

### 🔴 Cierre de Sesión:
1. `Genera o actualiza el contexto tecnico de los archivos que fueron modificados durante la sesión, según la skill generar_contexto.md.`
2. `Extrae o actualiza el ADR de las decisiones tomadas durante la sesión, según la skill extraer_adr.md.`
3. `Genera la transición técnica de esta sesión según la skill crear_transicion_tecnica.md.`
4. `Genera un resumen detallado de todos los cambios y archivos modificados durante esta sesión.`

