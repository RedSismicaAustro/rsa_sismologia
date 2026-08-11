# CONTEXTO INTEGRAL DE MANTENIMIENTO V3 EXHAUSTIVA ORIENTADA A AGENTES
## analizar_metodos_rsa.py

Versión: 3.0
Propósito: Contexto maestro para mantenimiento asistido por IA, evolución funcional y refactorización segura.

---

# 1. RESUMEN EJECUTIVO

`analizar_metodos_rsa.py` es una herramienta de análisis estático basada en AST cuyo objetivo es clasificar funciones de un archivo Python según su posible acoplamiento con GUI.

Actualmente analiza exclusivamente `metodos_rsa.py`, extrae funciones mediante AST y realiza una clasificación binaria basada en búsqueda de palabras clave.

No modifica archivos.

No ejecuta código analizado.

No genera artefactos persistentes.

---

# 2. RESPONSABILIDADES

## Incluidas

- Verificar existencia de archivo.
- Leer código fuente.
- Parsear AST.
- Extraer funciones.
- Determinar rango de líneas.
- Clasificar funciones.
- Mostrar resultados.

## Excluidas

- Refactorización automática.
- Modificación de código.
- Reescritura AST.
- Análisis semántico profundo.
- Resolución de imports.
- Detección de herencia.
- Detección de dependencias indirectas.

---

# 3. ARQUITECTURA

```text
main()
 │
 ├── leer_codigo()
 │
 ├── obtener_funciones()
 │      │
 │      └── ast.parse()
 │
 ├── clasificar_funciones()
 │
 └── impresión de resultados
```

---

# 4. DEPENDENCIAS

## Estándar

- ast
- os

## Dependencias implícitas

- Python ≥ 3.8 (end_lineno)

---

# 5. MODELO DE DATOS

## ARCHIVO

```python
ARCHIVO = "metodos_rsa.py"
```

Contrato:

- Debe existir.
- Debe ser Python válido.

## PALABRAS_GUI

```python
PALABRAS_GUI = [...]
```

Contrato:

- Lista de cadenas.
- Cada cadena representa un indicador GUI.

## Función detectada

```python
{
    "nombre": str,
    "inicio": int,
    "fin": int
}
```

---

# 6. CONTRATOS INTERNOS

## leer_codigo()

Entrada:

```python
ruta:str
```

Salida:

```python
str
```

No modifica estado.

## obtener_funciones()

Entrada:

```python
codigo:str
```

Salida:

```python
list[dict]
```

Contrato:

- Todas las funciones deben poseer:
  - nombre
  - inicio
  - fin

## clasificar_funciones()

Entrada:

```python
codigo:str
funciones:list
```

Salida:

```python
(funciones_gui, funciones_core)
```

Contrato:

- Una función pertenece a una sola categoría.

## main()

Contrato:

- Coordina flujo.
- No debe contener lógica de clasificación.

---

# 7. INVARIANTES

## I-01

Después de:

```python
codigo = leer_codigo(...)
```

debe cumplirse:

```python
len(codigo) > 0
```

## I-02

Después de:

```python
funciones = obtener_funciones(...)
```

debe cumplirse:

```python
isinstance(funciones,list)
```

## I-03

Cada elemento:

```python
funciones[i]
```

debe contener:

```python
nombre
inicio
fin
```

## I-04

Siempre:

```python
inicio <= fin
```

## I-05

Clasificación:

```python
len(gui)+len(core)==len(funciones)
```

---

# 8. ANÁLISIS MÉTODO POR MÉTODO

## leer_codigo()

### Función

Carga archivo completo.

### Riesgos

- Archivo inexistente.
- Problemas de codificación.

### Impacto

MEDIO.

---

## obtener_funciones()

### Función

Extrae FunctionDef mediante AST.

### Riesgos

- Código inválido.
- Dependencia de end_lineno.

### Impacto

ALTO.

---

## clasificar_funciones()

### Función

Clasificación por búsqueda textual.

### Riesgos

- Falsos positivos.
- Falsos negativos.
- No detecta imports GUI indirectos.

### Impacto

MUY ALTO.

---

## main()

### Función

Orquestación.

### Riesgos

- Dependencia de ARCHIVO hardcodeado.

### Impacto

ALTO.

---

# 9. MATRIZ MÉTODO → ESTADO

| Método | Lee | Modifica |
|----------|----------|----------|
| leer_codigo | archivo | ninguno |
| obtener_funciones | código | funciones |
| clasificar_funciones | funciones | gui/core |
| main | todo | salida consola |

---

# 10. LIMITACIONES FUNCIONALES

## L-01

Clasificación textual.

Ejemplo:

```python
texto = "QMessageBox"
```

genera falso positivo.

## L-02

No analiza imports.

## L-03

No analiza clases.

## L-04

No analiza métodos.

## L-05

No detecta dependencias transitivas.

---

# 11. DEUDA TÉCNICA REEVALUADA

## Crítica

### DT-01

ARCHIVO hardcodeado.

### DT-02

Dependencia Python 3.8+.

### DT-03

Sin persistencia.

## Alta

### DT-04

Clasificación binaria.

### DT-05

Sin análisis de imports.

### DT-06

Sin análisis de clases.

## Media

### DT-07

Sin type hints.

### DT-08

Sin docstrings.

---

# 12. RIESGOS PARA AGENTES

## R-01

Modificar PALABRAS_GUI cambia completamente la clasificación.

## R-02

Cambiar estructura de retorno rompe consumidores futuros.

## R-03

Cambiar nombre de claves:

```python
nombre
inicio
fin
```

rompe todo el flujo.

---

# 13. CHECKLIST DE REGRESIÓN

## Lectura

- [ ] Archivo existe.
- [ ] Lectura correcta.

## AST

- [ ] Parse exitoso.
- [ ] Todas las funciones detectadas.

## Clasificación

- [ ] GUI correctas.
- [ ] CORE correctas.

## Salida

- [ ] Consola correcta.
- [ ] Sin excepciones.

---

# 14. EVOLUCIÓN RECOMENDADA

## Fase 1

Agregar CLI:

```python
argparse
```

## Fase 2

Guardar JSON.

## Fase 3

Clasificación multinivel.

## Fase 4

Análisis de clases.

## Fase 5

Análisis de imports.

## Fase 6

Dependencias entre funciones.

---

# 15. CONTRATO PARA FUTURAS VERSIONES

Un agente NO debe modificar:

- formato de salida;
- estructura de funciones;
- contrato de clasificación;

sin actualizar documentación y pruebas.

---

# 16. CASOS DE PRUEBA MÍNIMOS

Caso 1:

Archivo inexistente.

Resultado esperado:

```text
No se encontró el archivo
```

Caso 2:

Archivo sin funciones.

Resultado esperado:

listas vacías.

Caso 3:

Función con QMessageBox.

Resultado esperado:

GUI.

Caso 4:

Función sin GUI.

Resultado esperado:

CORE.

---

# 17. CONCLUSIÓN

Los componentes más sensibles son:

1. obtener_funciones()
2. clasificar_funciones()
3. PALABRAS_GUI

La principal debilidad del sistema es que la clasificación se basa en búsqueda textual simple y no en análisis semántico.

Cualquier evolución futura debería migrar progresivamente hacia análisis AST enriquecido, clasificación multinivel y persistencia estructurada de resultados.
