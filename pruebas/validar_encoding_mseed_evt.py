# Regresion: seleccion de codificacion MiniSEED y reporte real de insercion.
#   Etapa 1: los dos origenes de datos conviven sin redondeo (enteros -> STEIM1, flotantes -> FLOAT).
#   Etapa 2: el reporte de insercion declara el estado real (antes afirmaba 'Insertado' sin insertar).
# Ejecutar con: C:\entornos\venv_py309\Scripts\python.exe pruebas\validar_encoding_mseed_evt.py
import importlib.util
import os
import shutil
import sys
import tempfile

import numpy as np
import obspy
from obspy import Stream, Trace, UTCDateTime

RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_MODULO = os.path.join(RAIZ_PROYECTO, "modulos externos", "Insercion de estaciones EVT.py")
RECUENTOS_ENTEROS = np.arange(200) + 4096
UNIDADES_FISICAS = (np.arange(200) - 100) * 0.000440599  # m/s2, estilo UCHU
FALLOS = []


def construir_traza(datos, estacion="TEST", canal="Z"):
    traza = Trace(data=datos)
    traza.stats.station = estacion
    traza.stats.channel = canal
    traza.stats.starttime = UTCDateTime(2026, 1, 1, 0, 0, 0)
    traza.stats.sampling_rate = 200.0
    return traza


def cargar_modulo():
    for ruta in (os.path.join(RAIZ_PROYECTO, "src", "librerias"),
                 os.path.join(RAIZ_PROYECTO, "datos")):
        if ruta not in sys.path:
            sys.path.insert(0, ruta)
    especificacion = importlib.util.spec_from_file_location("insercion_evt", RUTA_MODULO)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def comprobar(condicion, descripcion):
    print("      %s %s" % ("OK  " if condicion else "FALLA", descripcion))
    if not condicion:
        FALLOS.append(descripcion)


def escribir_y_leer(modulo, stream, carpeta):
    ruta = os.path.join(carpeta, "prueba.mseed")
    encoding = modulo.escribir_atomico_mseed(stream, ruta)
    lectura = obspy.read(ruta, format="MSEED")
    return encoding, lectura, os.path.getsize(ruta)


print("=" * 78)
print("obspy", obspy.__version__, "| numpy", np.__version__, "| python", sys.version.split()[0])
print("=" * 78)

modulo = cargar_modulo()
carpeta_temporal = tempfile.mkdtemp(prefix="rsa_evt_")

print("\n[1] SELECCION DE CODIFICACION SIN PERDIDA (ambos origenes)")
casos = [
    ("int32 registro continuo", Stream([construir_traza(RECUENTOS_ENTEROS.astype(np.int32))]),
     "STEIM1", [RECUENTOS_ENTEROS.astype(np.int32)]),
    ("int64", Stream([construir_traza(RECUENTOS_ENTEROS.astype(np.int64))]),
     "STEIM1", [RECUENTOS_ENTEROS.astype(np.int32)]),
    ("float32 entero (ETNA VM)", Stream([construir_traza(RECUENTOS_ENTEROS.astype(np.float32))]),
     "STEIM1", [RECUENTOS_ENTEROS.astype(np.int32)]),
    ("float32 m/s2 (UCHU)", Stream([construir_traza(UNIDADES_FISICAS.astype(np.float32))]),
     "FLOAT32", [UNIDADES_FISICAS.astype(np.float32)]),
    ("float64 m/s2 (UCHU nativo)", Stream([construir_traza(UNIDADES_FISICAS.astype(np.float64))]),
     "FLOAT64", [UNIDADES_FISICAS.astype(np.float64)]),
    ("MIXTO int32 + float32 m/s2", Stream([
        construir_traza(RECUENTOS_ENTEROS.astype(np.int32), "LABR", "Z"),
        construir_traza(UNIDADES_FISICAS.astype(np.float32), "UCHU", "0")]),
     "FLOAT64", [RECUENTOS_ENTEROS.astype(np.float64),
                 UNIDADES_FISICAS.astype(np.float32).astype(np.float64)]),
    ("int64 fuera de rango int32", Stream([construir_traza(
        np.array([0, 3000000000], dtype=np.int64))]),
     "FLOAT64", [np.array([0.0, 3000000000.0])]),
]
for etiqueta, stream, encoding_esperado, esperados in casos:
    print("   %s" % etiqueta)
    try:
        encoding, lectura, tamano = escribir_y_leer(modulo, stream, carpeta_temporal)
        comprobar(encoding == encoding_esperado,
                  "encoding %s (esperado %s)" % (encoding, encoding_esperado))
        comprobar(all(traza.stats.mseed.encoding == encoding_esperado for traza in lectura),
                  "encoding grabado en el registro MiniSEED")
        comprobar(tamano % 512 == 0, "longitud de registro multiple de 512 bytes")
        comprobar(all(np.array_equal(traza.data, esperado) and traza.data.dtype == esperado.dtype
                      for traza, esperado in zip(lectura, esperados)),
                  "datos identicos al original, sin redondeo")
    except Exception as error:
        comprobar(False, "excepcion inesperada: %s: %s" % (type(error).__name__, error))

print("\n   guardas")
for etiqueta, stream, codificable in (
        ("stream vacio", Stream(), False),
        ("dtype no numerico", Stream([construir_traza(np.array(["a", "b"]))]), False),
        ("NaN en float32", Stream([construir_traza(
            np.concatenate([UNIDADES_FISICAS[:100].astype(np.float32), [np.nan]]))]), True)):
    try:
        encoding, lectura, _ = escribir_y_leer(modulo, stream, carpeta_temporal)
        comprobar(codificable, "%s -> escrito en %s" % (etiqueta, encoding))
    except Exception as error:
        comprobar(not codificable, "%s -> rechazado: %s" % (etiqueta, type(error).__name__))

print("\n[2] REPORTE REAL DE INSERCION (matriz del dia simulada)")
fila_matriz = ["1", "20260101_000000.sis", "SISMO"] + ["-"] * 110
eventos = [["ID", "archivo_sis", "tipo"] + ["estacion_%d" % i for i in range(110)], fila_matriz]

print("   estacion homologada presente en el catalogo (CHAB)")
reporte = {}
eventos_resultado = modulo.insertar_evento_en_catalogo(
    carpeta_temporal, [list(f) for f in eventos],
    Stream([construir_traza(UNIDADES_FISICAS.astype(np.float32), "CHB", "0")]), None, reporte)
comprobar(reporte.get('insertado') is True, "reporte.insertado = True")
comprobar(reporte.get('encoding_mseed') == "FLOAT32",
          "reporte.encoding_mseed = %s" % reporte.get('encoding_mseed'))
comprobar(os.path.exists(reporte.get('ruta_mseed', "")), "MiniSEED escrito en %s" % reporte.get('ruta_mseed'))
comprobar(len(reporte.get('token', "")) == 12, "token de estacion de 12 caracteres: %s" % reporte.get('token'))

print("   estacion de cabecera NO catalogada (ZZZZ)")
reporte = {}
eventos_sin_catalogo = [list(f) for f in eventos]
eventos_sin_catalogo = modulo.insertar_evento_en_catalogo(
    carpeta_temporal, eventos_sin_catalogo,
    Stream([construir_traza(RECUENTOS_ENTEROS.astype(np.int32), "ZZZZ", "0")]), None, reporte)
comprobar(reporte.get('insertado') is False, "reporte.insertado = False (antes decia 'Insertado')")
comprobar("estaciones.csv" in str(reporte.get('motivo')), "motivo informado: %s" % reporte.get('motivo'))
comprobar(eventos_sin_catalogo == [list(f) for f in eventos], "matriz del dia intacta, sin cambios")

print("   evento inexistente en la matriz del dia")
traza_tardia = construir_traza(RECUENTOS_ENTEROS.astype(np.int32), "CHB", "0")
traza_tardia.stats.starttime = UTCDateTime(2026, 1, 1, 5, 0, 0)
reporte = {}
modulo.insertar_evento_en_catalogo(carpeta_temporal, [list(f) for f in eventos],
                                   Stream([traza_tardia]), None, reporte)
comprobar(reporte.get('insertado') is False, "reporte.insertado = False")
comprobar("no figura en la matriz" in str(reporte.get('motivo')),
          "motivo informado: %s" % reporte.get('motivo'))

shutil.rmtree(carpeta_temporal, ignore_errors=True)

print("\n" + "=" * 78)
print("RESULTADO: %d comprobaciones fallidas" % len(FALLOS))
for fallo in FALLOS:
    print("   - %s" % fallo)
print("=" * 78)
