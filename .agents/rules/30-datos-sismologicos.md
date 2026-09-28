---
proyecto: rsa_sismologia
tipo: regla_agente
archivo: .agents/rules/30-datos-sismologicos.md
temas: [token_estaciones, matriz_eventos, directorio_dia, mseed_evt, contratos_datos]
origen: AGENTS.md
---

# 30 — Contratos de Datos Sismológicos (Invariantes de Formato)

> **Propósito**: Proteger la integridad de los formatos que sostienen todo el pipeline: el token de estación, la matriz maestra de eventos y el árbol de datos diario. **Romper uno de estos contratos corrompe catálogos y boletines de forma silenciosa.**
>
> 📖 Referencias canónicas: [`docs/contexto_estructura_datos_dia.md`](../../docs/contexto_estructura_datos_dia.md) y [`docs/contexto_archivos_configuracion_datos.md`](../../docs/contexto_archivos_configuracion_datos.md).

---

## 1. Token de Estación `EEEECBFFIISS` (12 caracteres exactos)

```text
Posición:  0   1   2   3   4   5   6   7   8   9  10  11
Carácter: [E] [E] [E] [E] [C] [B] [F] [F] [I] [I] [S] [S]
```

| Campo | Posición | Valores | Significado |
|:---|:---:|:---:|:---|
| `EEEE` | 0..3 | `BOB1`, `PATS`, `LABR`… | Código de la estación |
| `C` | 4 | `1`=Z, `2`=N, `3`=E | Componente procesada |
| `B` | 5 | `1` / `0` | **Aporte**: `1` = aporta (azul) · `0` = no aporta (gris) |
| `FF` | 6..7 | `00`, `02`, `04` | Orden del filtro Butterworth (`00` = sin filtro) |
| `II` | 8..9 | `01` = 1.0 Hz | Frecuencia de corte inferior |
| `SS` | 10..11 | `08` = 8.0 Hz | Frecuencia de corte superior |

**Modificación obligatoria por rebanada** (jamás por reconstrucción manual de la cadena):

```python
nueva_cadena = cadena_anterior[:5] + nuevo_aporte + nuevo_filtro_6caracteres
```

---

## 2. Matriz Maestra de Eventos `AAAAMMDD000000.csv`

* Delimitador **punto y coma (`;`)**. Una fila por evento detectado.
* `[Col 0]` = ID · `[Col 1]` = archivo `.sis` · `[Col 2]` = tipo de evento · `[Col 3..103]` = estaciones.
* **Offset fijo `+3`**: la estación de índice *i* de [`datos/estaciones.csv`](../../datos/estaciones.csv) ocupa **siempre** la columna *i+3* (hasta 101 estaciones).
* Estación sin datos = `"-"`. Estación con datos = token de 12 caracteres.

**Tipos de evento oficiales** (no inventar valores nuevos): `SISMO`, `FF`, `FC`, `TELESISMO`, `Ruido`, `INDEFINIDO`, `Evento_local`, `CONTROL`, `REVISION`.

---

## 3. Árbol de Datos Diario `..\DIA\AAAA\AAAA_MM\AAAA_MM_DD\`

* **Resolución dinámica obligatoria**: `metodos_gestion.obtener_directorios(archivo)` mantiene retrocompatibilidad con esquemas históricos (`DIA\AAAA_MM\AAAA_MM_DD\`, `DIA\AAAA_MM_DD\`, `DIA\AAMMDD000000\`).
* Archivos clave del día: `AAAAMMDD000000.csv` (matriz), `_cat.csv` (catálogo hipocentral, 20 columnas), `_rep.csv` (boletín), `_res.csv` (conteo), `_marcas.json` (picks UTC), `.xml`, `_rep.pdf`, `_estaciones.csv`, `_est.csv`, `_aux.csv`.
* Subdirectorios operativos: `dia\` (`.sis`, `.fas`, `.json`), `mseed\eventos\`, `mseed\registros\`, `fastHypo\`, `procesamiento\`, `reportes\`, `acelerogramas\`.

---

## 4. Prohibiciones sobre Datos

> [!CAUTION]
> Estas cuatro prohibiciones son **no negociables**:

1. **No alterar los esquemas JSON** de configuración ni los formatos de la matriz de eventos.
2. **No alterar el comportamiento de `GestorFases`** ni el contrato de datos de fases (P, S, Coda) sincronizado entre `.json` y `.fas` binario (HYPO71).
3. **No escribir ni borrar datos en las unidades de producción** (`G:\Mi unidad\DIA\` y unidades de red de responsables). Los datos sismológicos son irreemplazables.
4. **No inventar formatos** (MiniSEED, EVT, `.sis`, `.fas`, CSV, XML): toda E/S se realiza con las funciones existentes de `metodos_rsa`, `rsa_io`, `rsa_procesamiento` y `metodos_gestion`.

---

## 5. Prevalencia del Contexto Técnico

* Antes de modificar cualquier script: **leer su `<nombre>_contx.md`** (Regla de Oro, `AGENTS.md` §2).
* Si el `_contx.md` contradice el código real, **prevalece la funcionalidad real documentada** y se propone una corrección conservadora, reportando la discrepancia.
* Toda modificación de una función compartida debe **registrar la deuda técnica** en los `_contx.md` de los scripts afectados (skill [`auditoria_librerias_e_integracion.md`](../skills/auditoria_librerias_e_integracion.md)).

---

## 6. Checklist de Verificación

- [ ] Todo token escrito o modificado mide **exactamente 12 caracteres** y respeta `EEEECBFFIISS`.
- [ ] No se alteró el offset `+3` ni el delimitador `;` de la matriz maestra.
- [ ] Rutas resueltas con `obtener_directorios()`; ninguna ruta `G:\` codificada.
- [ ] Esquemas JSON, `GestorFases` y formatos de archivo intactos.
- [ ] El `_contx.md` del módulo fue leído antes de editar y actualizado después.
- [ ] Ninguna escritura ni borrado sobre datos operativos de producción.
