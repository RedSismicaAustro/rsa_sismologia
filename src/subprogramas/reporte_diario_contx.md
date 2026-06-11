# CONTEXTO INTEGRAL DE MANTENIMIENTO V3
## reporte_diario.py

> Documento maestro de mantenimiento a largo plazo.
>
> Esta versión reemplaza completamente al contexto anterior e incorpora criterios de ingeniería de software, contratos internos, invariantes, riesgos operativos, acoplamientos, deuda técnica y estrategia de evolución.

---

# 1. Propósito

El módulo `reporte_diario.py` es responsable de la generación, edición, validación y consolidación de los reportes diarios de actividad sísmica dentro del ecosistema RSA.

Responsabilidades principales:

- Carga de información diaria.
- Gestión de eventos reportables.
- Edición y validación de eventos.
- Visualización de señales sísmicas.
- Gestión de estaciones participantes.
- Evaluación de calidad operativa.
- Generación de reportes.
- Persistencia de resultados.

---

# 2. Arquitectura General

```text
Reporte_diario
│
├── Gestión de día
├── Gestión de catálogo
├── Gestión de eventos
├── Gestión de señales
├── Gestión de estaciones
├── Evaluación de calidad
├── Reportes
└── Persistencia
```

---

# 3. Componentes Principales

## Reporte_diario

Clase principal.

Responsabilidades:

- cargar día;
- cargar eventos;
- administrar catálogo;
- administrar reportes;
- generar salidas finales.

## estaciones_

Ventana auxiliar utilizada para:

- evaluación de estaciones;
- comportamiento;
- disponibilidad;
- detalle operativo.

## filtro_evento()

Función auxiliar de filtrado de señales.

---

# 4. Dependencias Internas

- metodos_rsa
- metodos_gestion
- rsa_pdf_catalogo
- metodos_reportes_individuales
- módulos de lectura y persistencia RSA

---

# 5. Dependencias Externas

- PyQt5
- matplotlib
- numpy
- xml.etree.ElementTree
- ObsPy

---

# 6. Modelo de Datos

## catalogo

Catálogo completo del día.

## eventos

Eventos simplificados.

## eventos_reporte

Eventos utilizados para generación de reportes.

## trCanal

Contenedor principal de señales sísmicas.

## root

Raíz XML activa.

## resumen

Resumen estadístico diario.

---

# 7. Contratos Internos

## Contrato de catalogo

- Debe existir después de cargar_dia().
- Debe mantenerse sincronizado con XML.
- Debe mantenerse sincronizado con eventos_reporte.

## Contrato de eventos_reporte

- La fila 0 es cabecera.
- No debe eliminarse.
- Todas las filas posteriores representan eventos válidos.

## Contrato de trCanal

- Índice de estación = índice de parámetros.
- No modificar manualmente fuera de Cargar_evento().

## Contrato de estaciones_eventos

- Contiene índices.
- Nunca nombres.
- Nunca códigos.

---

# 8. Invariantes

Después de cargar_dia():

```python
self.catalogo is not None
self.root is not None
self.responsables is not None
```

Antes de Graficar_():

```python
len(self.estaciones_eventos) > 0
```

Antes de Guardar_():

```python
self.root is not None
```

Siempre:

```python
len(self.eventos_reporte) >= 1
self.pagina >= 0
```

---

# 9. Inventario de Estado

| Atributo | Descripción |
|-----------|------------|
| archivo | Ruta base |
| directorio_trabajo | Directorio activo |
| responsable | Responsable operativo |
| periodo | Franja horaria |
| catalogo | Catálogo diario |
| eventos | Eventos |
| eventos_reporte | Reportables |
| trCanal | Señales |
| root | XML |
| resumen | Resumen |
| pagina | Página actual |
| estaciones_eventos | Estaciones activas |
| indice | Índice actual |
| evento_escogido | Evento seleccionado |

---

# 10. Flujo Principal

```text
showDate()
    ↓
cargar_dia()
    ↓
Cargar_evento()
    ↓
Graficar_()
    ↓
Guardar_()
```

---

# 11. Matriz Método → Estado

| Método | Modifica |
|----------|----------|
| showDate | archivo, directorios |
| cargar_dia | catalogo, eventos, root |
| Cargar_evento | trCanal, estaciones_eventos |
| Modificar_ | eventos_reporte |
| Insertar_evento | catalogo, eventos_reporte |
| Guardar_ | archivos externos |

---

# 12. Riesgos Operativos

## División por cero

En cálculo de comportamiento:

```python
comp = evaluacion / enlace
```

Validar enlace antes de dividir.

## Dependencia de orden

Debe mantenerse:

```text
showDate()
→ cargar_dia()
→ Cargar_evento()
```

## Dependencia XML

Guardar_() depende de root válido.

---

# 13. Acoplamientos

## estaciones_ ↔ Reporte_diario

Modifica directamente:

- enlace
- comportamiento
- detalle

Nivel: ALTO.

---

# 14. Deuda Técnica

## DT-01

trCanal inicializado para 100 estaciones cuando el sistema maneja 101.

## DT-02

Uso parcial o incorrecto de self.pagina.

## DT-03

archivo_comportamiento utilizado sin definición clara.

## DT-04

Acoplamiento elevado entre GUI y lógica.

---

# 15. Matriz de Impacto

| Método | Impacto |
|----------|----------|
| cargar_dia | Muy Alto |
| Cargar_evento | Muy Alto |
| Guardar_ | Muy Alto |
| Modificar_ | Alto |
| Insertar_evento | Alto |
| Graficar_ | Medio |

---

# 16. Checklist de Regresión

## Carga

- [ ] Carga día.
- [ ] Carga catálogo.
- [ ] Carga XML.

## Eventos

- [ ] Selección correcta.
- [ ] Edición correcta.
- [ ] Inserción correcta.

## Señales

- [ ] Graficación.
- [ ] Filtrado.

## Reportes

- [ ] Generación PDF.
- [ ] Generación XML.
- [ ] Persistencia.

---

# 17. Reglas para Desarrolladores

1. No modificar contratos internos sin documentarlo.
2. Mantener compatibilidad histórica.
3. Mantener sincronización catálogo/XML.
4. Ejecutar checklist de regresión antes de liberar cambios.
5. Documentar nuevas estructuras de datos.

---

# 18. Estrategia de Evolución

Fase 1:
- Corregir problemas críticos identificados.

Fase 2:
- Reducir acoplamiento.

Fase 3:
- Separar lógica de negocio y GUI.

Fase 4:
- Incorporar pruebas automatizadas.

---

# 19. Conocimiento Crítico

Los elementos más sensibles del sistema son:

1. cargar_dia()
2. Cargar_evento()
3. Guardar_()
4. XML root
5. eventos_reporte
6. estaciones_

Toda modificación debe validarse mediante pruebas funcionales completas.
