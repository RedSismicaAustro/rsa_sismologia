# CONTEXTO INTEGRAL DE MANTENIMIENTO V3 (EXHAUSTIVO)
## procesamiento_integrado.py

> Documento maestro de mantenimiento basado en el código fuente actual y la V2 existente.
> Su objetivo es preservar conocimiento técnico, facilitar correcciones futuras y reducir riesgos de modificación.

---

# 1. Propósito del módulo

`procesamiento_integrado.py` es el núcleo operativo del flujo de procesamiento sísmico RSA.

Coordina:

- Carga de días de trabajo.
- Selección de eventos.
- Gestión de procesamiento sísmico.
- Integración con ProcesoV2.
- Gestión Virtual ↔ Real.
- Monitoreo de archivos RSA.
- Generación de reportes.
- Gestión de estaciones.
- Integración GIS.
- Persistencia de resultados.

---

# 2. Arquitectura lógica

```text
Procesar_evento
│
├── Gestión GUI
├── Gestión eventos
├── Gestión procesamiento
├── Gestión estaciones
├── Gestión Virtual / Real
├── Monitor RSA
├── GIS
├── Reportes
└── Persistencia
```

---

# 3. Clases principales

## FileMonitorThread

Responsable de monitorear archivos RSA.

### Señales

```python
archivo_cambiado(str)
```

### Métodos

- run()
- sleep_interruptible()

### Responsabilidad

Detectar cambios en archivos RSA sin bloquear la GUI.

---

## Procesar_evento

Clase principal del sistema.

Responsabilidades:

- administrar eventos;
- controlar procesamiento;
- controlar monitor;
- gestionar estaciones;
- actualizar GIS;
- generar reportes.

---

## Cambio_Coeficientes_Filtro

Ventana auxiliar para edición de filtros.

---

## estaciones_

Editor de:

- estaciones habilitadas;
- filtros;
- visualización de señales;
- interacción GIS.

---

## reporte_

Inserción de eventos externos.

---

# 4. Dependencias internas

- rsa_io
- rsa_procesamiento
- rsa_pdf_catalogo
- metodos_rsa
- metodos_gestion
- metodos_gis_rsa
- metodos_reportes_individuales

---

# 5. Dependencias externas

- PyQt5
- matplotlib
- pathlib
- xml.etree.ElementTree
- datetime

---

# 6. Modelo de datos principal

## self.eventos

Eventos del día.

Contrato:

```text
[id, nombre_evento, tipo_evento, estaciones...]
```

---

## self.catalogo

Catálogo sísmico consolidado.

---

## self.eventos_reporte

Eventos utilizados en reportes.

---

## self.procesamiento

```text
Fila 0 → Cabecera
Fila 1 → Inicio
Fila N → Intentos
```

---

## self.trCanal

Datos sísmicos cargados mediante MiniSEED.

---

## self.responsables

Responsables por franja horaria.

---

## self.directorios

Diccionario de rutas operativas.

---

# 7. Máquina de estados

```text
Inicialización
      ↓
Abrir_archivo
      ↓
Preparar evento
      ↓
Procesamiento disponible
      ↓
Estaciones abiertas
      ↓
Monitoreo RSA
      ↓
Actualización procesamiento
      ↓
Cierre
```

---

# 8. Flujo completo de procesamiento

```text
Abrir_archivo()
      ↓
preparar_evento()
      ↓
procesar_()
      ↓
guardar_intento()
      ↓
actualizar_mapa()
      ↓
reportar_()
```

---

# 9. Flujo Virtual ↔ Real

```text
REAL
 ↓
Copiar a Virtual
 ↓
ProcesoV2
 ↓
RSA actualizado
 ↓
recalcular_procesamiento()
 ↓
Copiar Virtual → Real
```

Regla crítica:

No alterar esta secuencia.

---

# 10. Señales Qt documentadas

## FileMonitorThread

```python
archivo_cambiado(str)
```

---

## Procesar_evento

```python
cerrado()
```

---

## estaciones_

```python
senal_cerrar()
senal_actualizar_mapa()
senal_cambios_estaciones(list,list)
senal_cambio_vista(str)
```

---

# 11. Contratos internos

## filtros_estaciones

Formato:

```text
OOffss
```

## estaciones_eventos

Contiene índices reales de estaciones.

Nunca nombres.

---

## evento_procesar

Debe contener la fila completa del evento.

---

# 12. Invariantes

Siempre deben cumplirse:

```text
evento_procesar != ''
```

```text
estaciones_eventos ⊆ estaciones_eventos_total
```

```text
len(filtros_estaciones)
==
len(estaciones_eventos_total)
```

```text
file_monitor == None
o
file_monitor.isRunning()
```

---

# 13. Métodos críticos

## activar_hilo()

Activa monitoreo RSA.

Impacto: Muy Alto.

---

## recalcular_procesamiento()

Actualiza intentos automáticamente.

Impacto: Muy Alto.

---

## procesar_()

Método central de procesamiento.

Impacto: Crítico.

---

## guardar_evento()

Persistencia principal.

Impacto: Alto.

---

## Salir_()

Generación de reporte temporal.

Impacto: Medio.

---

# 14. Gestión GIS

Responsable:

```python
widget_grafico_mpl
```

Métodos asociados:

- actualizar_mapa()
- _estaciones_piden_actualizar_mapa()

---

# 15. Gestión de memoria

Elementos sensibles:

- visor
- canvas
- widget_mapa
- trCanal

Liberar siempre antes del cierre.

---

# 16. Acoplamientos identificados

## estaciones_ ↔ Procesar_evento

Acoplamiento Alto.

Comparte:

- estaciones_eventos
- filtros_estaciones
- eventos

---

## guardar_intento()

Impacta:

- GIS
- reportes
- monitoreo
- procesamiento

---

# 17. Riesgos de modificación

## Muy Alto

- procesar_()
- recalcular_procesamiento()
- guardar_intento()
- archivos_fast()
- verificar_coincidencias()

## Alto

- actualizar_mapa()
- _estaciones_cerraron()

---

# 18. Deuda técnica

## DT-01

Duplicidad:

```text
_estaciones_cerraron()
_estaciones_cerraron__()
```

---

## DT-02

Detección de bloqueo:

```python
os.rename(ruta,ruta)
```

Dependiente del sistema operativo.

---

## DT-03

GUI y lógica fuertemente acopladas.

---

## DT-04

Lógica Virtual/Real dispersa.

---

# 19. Responsabilidades por método

| Método | Responsabilidad |
|----------|----------|
| Abrir_archivo | Cargar día |
| preparar_evento | Preparar evento |
| procesar_ | Procesamiento |
| activar_hilo | Monitoreo |
| recalcular_procesamiento | Actualización |
| actualizar_mapa | GIS |
| guardar_evento | Persistencia |
| reportar_ | Reporte |
| insertar_ | Inserción externa |
| Salir_ | Salida controlada |

---

# 20. Estrategia de refactorización

Fase 1

- Unificar `_estaciones_cerraron`.

Fase 2

- Aislar Virtual/Real.

Fase 3

- Separar Reportes.

Fase 4

- Separar GUI y lógica.

Fase 5

- Crear pruebas automatizadas.

---

# 21. Checklist de regresión

## Procesamiento

- [ ] Carga día.
- [ ] Selección de evento.
- [ ] Procesamiento SISMO.
- [ ] Actualización automática.

## Virtual

- [ ] Copia REAL→VIRTUAL.
- [ ] RSA detectado.
- [ ] Copia VIRTUAL→REAL.

## GIS

- [ ] Actualización de mapa.
- [ ] Cambio de vista.

## Reportes

- [ ] Reporte individual.
- [ ] Reporte temporal.

## Cierre

- [ ] Hilo detenido.
- [ ] Recursos liberados.
- [ ] Señales emitidas.

---

# 22. Reglas para futuros desarrolladores

1. No alterar contratos internos.
2. Mantener compatibilidad histórica.
3. Mantener compatibilidad con ProcesoV2.
4. No eliminar señales Qt existentes.
5. Documentar nuevos modos de reporte.
6. Mantener separación Virtual/Real.
7. Ejecutar checklist de regresión antes de liberar cambios.

---

# 23. Conocimiento crítico

Los componentes más sensibles del sistema son:

1. Virtual ↔ Real.
2. guardar_intento().
3. verificar_coincidencias().
4. FileMonitorThread.
5. actualización GIS.
6. estaciones_.

Toda modificación debe validarse mediante pruebas funcionales completas.

---

# 24. Recomendación final

Antes de incorporar nuevas funcionalidades:

- estabilizar contratos;
- reducir acoplamiento;
- crear pruebas de regresión;
- aislar lógica de negocio.

Este documento debe evolucionar junto con el código y convertirse en la referencia oficial de mantenimiento.
