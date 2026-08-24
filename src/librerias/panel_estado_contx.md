---
proyecto: rsa_sismologia
tipo: contexto_tecnico
archivo: src/librerias/panel_estado.py
temas: [diagnostico_sismico, monitoreo_estaciones, turnos_guardia, pyqt5]
generado: 2026-08-23
---

# `src/librerias/panel_estado.py` — Contexto Técnico para Agentes IA

> Componente modular reutilizable en PyQt5 para la visualización del estado operativo de la jornada sísmica, verificación de archivos MiniSEED de registro continuo, evacuación de turnos y emisión de reportes.

**Ruta**: `src/librerias/panel_estado.py`  
**Lenguaje**: Python 3 (PyQt5)  
**Dependencias**: `PyQt5`, `metodos_rsa`, `metodos_gestion`  

---

## 1. Estructura Visual

`PanelEstadoJornada` hereda de `QWidget` y organiza el diagnóstico en tres grupos:
1. **Estado General**: Directorio base, fecha formateada y estado de existencia de la estructura de carpetas.
2. **Grid de Estaciones Sísmicas**: Matriz adaptativa de tarjetas para las 12 estaciones habilitadas (`🟢 OK` si existen registros MiniSEED, `⚪ Sin Reg.` si no hay datos).
3. **Turnos y Reportes Oficiales**: Conteo analítico de sismos por turno (00H-12H, 12H-18H, 18H-24H) y estado del informe diario en PDF.

---

## 2. Métodos Clave

| Método | Descripción |
|---|---|
| `actualizar_diagnostico(ruta_archivo, dir_base, parametros)` | Inspecciona el sistema de archivos para la fecha indicada y actualiza en caliente los indicadores visuales. |
