# Reporte de Auditoría Estructural

Fecha: 2026-02-26 19:05:04

## Resumen General

- Total módulos analizados: 23
- Total dependencias detectadas: 135

## Ciclos Detectados

- librerias/lectura_datos.py
- subprogramas/marcar_eventos.py
- librerias/lectura_datos.py → subprogramas/marcar_eventos.py
- librerias/lectura_datos.py → subprogramas/marcar_eventos.py → librerias/metodos_rsa.py
- librerias/lectura_datos.py → subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/metodos_gestion.py
- librerias/lectura_datos.py → subprogramas/marcar_eventos.py → librerias/metodos_gestion.py
- subprogramas/marcar_eventos.py → librerias/metodos_rsa.py
- subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/metodos_gestion.py
- subprogramas/marcar_eventos.py → librerias/metodos_gestion.py

## Módulos Más Centrales (Alto Acoplamiento)

- subprogramas/marcar_eventos.py (centralidad: 1.182)
- librerias/lectura_datos.py (centralidad: 1.091)
- librerias/metodos_datos.py (centralidad: 0.909)
- librerias/metodos_rsa.py (centralidad: 0.909)
- librerias/metodos_sismicos.py (centralidad: 0.909)
- librerias/metodos_gestion.py (centralidad: 0.864)
- librerias/metodos_graficos_rsa.py (centralidad: 0.591)
- programa_integrado.py (centralidad: 0.545)
- subprogramas/procesamiento_integrado.py (centralidad: 0.500)
- programa_integrado_alt.py (centralidad: 0.455)

## Observaciones Iniciales

- Se recomienda eliminar los ciclos antes de realizar refactorizaciones mayores.

---
Reporte generado automáticamente por auditor estructural.
