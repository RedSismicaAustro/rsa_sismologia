# Reporte Auditoría Estructural v2

Fecha: 2026-03-05 16:26:23.700204

## Ciclos Detectados

 - librerias/lectura_datos.py
 - librerias/rsa_procesamiento.py
 - subprogramas/marcar_eventos.py
 - subprogramas/marcar_eventos.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/metodos_gestion.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/metodos_gestion.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/metodos_gestion.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/metodos_gestion.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_io.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_io.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_io.py → librerias/metodos_gestion.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_io.py → librerias/metodos_gestion.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_io.py → librerias/rsa_dominio.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_io.py → librerias/rsa_dominio.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_io.py → librerias/rsa_dominio.py → librerias/metodos_gestion.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_io.py → librerias/rsa_dominio.py → librerias/metodos_gestion.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_dominio.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_dominio.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_dominio.py → librerias/metodos_gestion.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_procesamiento.py → librerias/rsa_dominio.py → librerias/metodos_gestion.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_io.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_io.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_io.py → librerias/metodos_gestion.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_io.py → librerias/metodos_gestion.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_io.py → librerias/rsa_dominio.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_io.py → librerias/rsa_dominio.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_io.py → librerias/rsa_dominio.py → librerias/metodos_gestion.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_rsa.py → librerias/rsa_io.py → librerias/rsa_dominio.py → librerias/metodos_gestion.py
 - subprogramas/marcar_eventos.py → librerias/metodos_gestion.py → librerias/lectura_datos.py
 - subprogramas/marcar_eventos.py → librerias/metodos_gestion.py
 - librerias/metodos_rsa.py → librerias/rsa_procesamiento.py

## Uso de Qt dentro de librerias

 - librerias/estaciones.py usa Qt (mezcla de capa)
 - librerias/lectura_datos.py usa Qt (mezcla de capa)
 - librerias/metodos_gestion.py usa Qt (mezcla de capa)
 - librerias/metodos_gis_rsa.py usa Qt (mezcla de capa)
 - librerias/metodos_graficos_rsa.py usa Qt (mezcla de capa)
 - librerias/metodos_reportes_individuales.py usa Qt (mezcla de capa)
 - librerias/metodos_rsa.py usa Qt (mezcla de capa)
 - librerias/rsa_io.py usa Qt (mezcla de capa)
 - librerias/rsa_procesamiento.py usa Qt (mezcla de capa)
 - librerias/ventana_aceleraciones.py usa Qt (mezcla de capa)
 - librerias/ventana_estaciones.py usa Qt (mezcla de capa)

## Violaciones de capa (librerias → subprogramas)

 - librerias/estaciones.py importa subprogramas/marcar_eventos.py
 - librerias/gestor_fases.py importa subprogramas/marcar_eventos.py
 - librerias/lectura_datos.py importa subprogramas/marcar_eventos.py
 - librerias/metodos_gestion.py importa subprogramas/marcar_eventos.py
 - librerias/metodos_gis_rsa.py importa subprogramas/marcar_eventos.py
 - librerias/metodos_graficos_rsa.py importa subprogramas/marcar_eventos.py
 - librerias/metodos_reportes_individuales.py importa subprogramas/marcar_eventos.py
 - librerias/metodos_rsa.py importa subprogramas/marcar_eventos.py
 - librerias/rsa_dominio.py importa subprogramas/marcar_eventos.py
 - librerias/rsa_io.py importa subprogramas/marcar_eventos.py
 - librerias/rsa_procesamiento.py importa subprogramas/marcar_eventos.py
 - librerias/ventana_aceleraciones.py importa subprogramas/marcar_eventos.py
 - librerias/ventana_estaciones.py importa subprogramas/marcar_eventos.py

## Archivos grandes (posible mezcla de responsabilidades)

 - programa_integrado.py tiene 691 líneas
 - programa_integrado_alt.py tiene 628 líneas
 - librerias/metodos_gestion.py tiene 615 líneas
 - librerias/metodos_graficos_rsa.py tiene 2450 líneas
 - librerias/metodos_rsa.py tiene 1672 líneas
 - librerias/rsa_procesamiento.py tiene 721 líneas
 - subprogramas/extraer_integrado.py tiene 998 líneas
 - subprogramas/procesamiento_integrado.py tiene 1621 líneas
 - subprogramas/reporte_acumulado.py tiene 1077 líneas
 - subprogramas/reporte_diario.py tiene 544 líneas

## Módulos con muchos dependientes

 - librerias/lectura_datos.py es usado por 23 módulos
 - librerias/metodos_datos.py es usado por 23 módulos
 - librerias/metodos_gestion.py es usado por 18 módulos
 - librerias/metodos_graficos_rsa.py es usado por 6 módulos
 - librerias/metodos_rsa.py es usado por 15 módulos
 - librerias/metodos_sismicos.py es usado por 23 módulos
 - librerias/rsa_procesamiento.py es usado por 6 módulos
 - subprogramas/marcar_eventos.py es usado por 23 módulos