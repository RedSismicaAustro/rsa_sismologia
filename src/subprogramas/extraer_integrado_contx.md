# Revisión de adecuación para mantenimiento: `extraer_integrado.py`

## 1. Veredicto general

El contexto `extraer_integrado_contx.md` es una **buena base funcional y técnica**, pero **no está completamente adecuado todavía como documento de mantenimiento a largo plazo bajo criterios de ingeniería de software**.

Sirve para entender el módulo, pero requiere ajustes para convertirse en una referencia confiable de mantenimiento.

## 2. Evaluación resumida

| Criterio | Evaluación |
|---|---:|
| Correspondencia general con el script | 8/10 |
| Utilidad para mantenimiento | 7/10 |
| Claridad arquitectónica | 7/10 |
| Ingeniería de software | 6.5/10 |
| Calidad Markdown | 5.5/10 |
| Identificación de deuda técnica | 8/10 |
| Trazabilidad método por método | 7/10 |
| Checklist de regresión | 7/10 |

## 3. Aspectos adecuados

El contexto sí documenta correctamente:

- Propósito general del módulo.
- Flujo de trabajo del usuario.
- Relación entre `lectura_mseed_dia` y `trCanal`.
- Importancia de `copiar_stream_dia()`.
- Uso de `grafico_evento_int()` y `filtro_evento()`.
- Formato del archivo auxiliar.
- Deuda técnica relevante.
- Problemas de memoria.
- Existencia de métodos duplicados de desplazamiento.
- Necesidad de refactorización por fases.
- Checklist pre-commit.
- Riesgos asociados a `estaciones_`.

## 4. Problemas detectados en el contexto

### 4.1. El Markdown necesita limpieza

Hay bloques de código mal cerrados o fragmentados, por ejemplo:

```md
```python
def limpiar_estado_completo(self):
```
# 1. Detener timers
```

Eso no es Markdown limpio. Debe corregirse para que los bloques de código incluyan todo el contenido correspondiente.

### 4.2. El contexto mezcla documentación verificada con propuestas

El documento combina:

- comportamiento real del script;
- deuda técnica;
- propuestas futuras;
- plantillas de refactorización;
- estimaciones de esfuerzo.

Eso no está mal, pero debe separarse claramente en secciones como:

```text
Comportamiento actual
Problemas confirmados
Hipótesis / supuestos
Propuestas futuras
```

### 4.3. Faltan advertencias sobre métodos “wrapper”

El script real tiene métodos que reemplazan o envuelven métodos anteriores:

```python
limpiar_estado() -> limpiar_estado_completo()
Salir_() -> Salir_mejorado()
closeEvent() -> closeEvent_mejorado()
```

Esto debería quedar más explícito, porque es importante para mantenimiento.

### 4.4. Falta documentar que `Btn_Salir` conecta a `Salir_`, no directamente a `Salir_mejorado`

El contexto habla de `Salir_mejorado`, pero el código conecta:

```python
self.Btn_Salir.clicked.connect(self.Salir_)
```

y `Salir_()` llama a `Salir_mejorado()`.

No es grave, pero para documentación de mantenimiento debe quedar fiel al flujo real.

### 4.5. Falta una sección formal de contratos internos

Debería existir una sección que especifique contratos como:

- `lectura_mseed_dia` no debe modificarse directamente.
- `trCanal` es copia de trabajo.
- `eventos_auxiliar` debe conservar el formato de tupla.
- `filtros_estaciones` debe mantener formato de seis dígitos.
- `estaciones_eventos` contiene índices de estación, no nombres.

### 4.6. Faltan invariantes del sistema

Para ingeniería de software, conviene documentar invariantes:

```text
t_inicio < t_final
pagina >= 0
estaciones_eventos debe ser subconjunto de estaciones_eventos_total
len(filtros_estaciones) debe corresponder con estaciones_eventos_total
trCanal debe tener la misma estructura posicional que lectura_mseed_dia
```

### 4.7. Falta separar deuda técnica del estado del código

Por ejemplo, el documento dice que `limpiar_estado_completo()` fue agregado recientemente y que resuelve memoria, pero el código aún usa muchas copias de streams durante desplazamientos. La limpieza existe, pero no resuelve el problema operativo durante el uso normal.

## 5. Problemas detectados en el script que deben reflejarse mejor

### 5.1. Limpieza fuerte al cerrar, pero no durante operación

El script contiene `limpiar_estado_completo()`, `_limpiar_streams()`, `_limpiar_matplotlib()` y otros métodos de limpieza, pero el problema de memoria durante uso normal persiste porque `copiar_stream_dia()` sigue llamándose repetidamente.

### 5.2. Acoplamiento fuerte entre `estaciones_` y `Extraer_evento`

El diálogo `estaciones_` modifica directamente atributos del padre:

```python
self.parent.estaciones_eventos
self.parent.filtros_estaciones
self.parent.hab_grafico
```

Esto rompe separación de responsabilidades.

### 5.3. Métodos duplicados de desplazamiento

El script mantiene múltiples métodos casi idénticos:

- `mas_6_minutos`
- `menos_6_minutos`
- `mas_2_segundos`
- `menos_2_segundos`
- etc.

Esto es deuda técnica real y debe estar marcada como prioritaria.

### 5.4. Falta validación temporal

No se valida sistemáticamente:

```python
t_inicio >= 0
t_final <= duración del día
t_inicio < t_final
```

### 5.5. `chkBx_ajuste` se lee pero no tiene efecto funcional claro

El valor `bandera_ajuste` se calcula, pero no se usa posteriormente de forma efectiva en `guardar_evento()`.

## 6. Recomendación de estructura para una versión mejorada

Sugiero reorganizar el contexto así:

```text
1. Propósito y alcance
2. Papel dentro del sistema RSA
3. Arquitectura actual
4. Contratos internos del módulo
5. Invariantes obligatorios
6. Modelo de datos
7. Flujo de inicialización
8. Flujo de carga de evento
9. Flujo de filtrado
10. Flujo de guardado
11. Flujo de cierre
12. Método por método
13. UI y widgets
14. Dependencias externas e internas
15. Gestión de memoria
16. Problemas confirmados
17. Deuda técnica priorizada
18. Refactorización sugerida
19. Checklist de regresión
20. Checklist pre-commit
21. Guía para futuros desarrolladores
```

## 7. Conclusión

El contexto actual es útil, pero no lo dejaría todavía como documentación definitiva de mantenimiento.

Recomendación:

- Mantener el contenido técnico existente.
- Limpiar el Markdown.
- Separar comportamiento real de propuestas futuras.
- Agregar contratos internos e invariantes.
- Alinear mejor algunos flujos con el script real.
- Generar una versión V2 formal de mantenimiento.

## 8. Recomendación final

Sí amerita generar una versión corregida del contexto.

La prioridad no es agregar mucho más contenido, sino reorganizarlo y hacerlo más riguroso bajo criterios de ingeniería de software.
