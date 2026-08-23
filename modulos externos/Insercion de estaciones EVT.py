import sys
import os
import hashlib
import csv
from pathlib import Path
from collections import deque
from datetime import datetime, timedelta

ruta_librerias = os.path.dirname(__file__)
from rsa_io import lectura_archivo, escritura_archivo, extraer_hasta_directorio

ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
if not ruta_proyecto:
    raise RuntimeError('No se encontro la raiz del proyecto rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

# Insertar rutas al inicio de sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

# Programa para insertar registros fuera de tiempo (disparos EVT de Kinemetrics ETNA u otros digitalizadores)
# Estructura de informacion: ..\AAAA\ESTA\Datos evt
# AAAA: anio, ESTA: estacion, Datos EVT: archivos .evt

from metodos_rsa import parametros_estaciones, obtener_directorios, recolectar_evt, clasificar_evento_sismico, ejecutar_en_vm
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox)
from obspy import read, UTCDateTime, Stream
from PyQt5.QtCore import QUrl

DICCIONARIO_ESTACIONES_EVT = {
    "ACC1": "EEAS",
    "CHB": "CHAB",
    "CHC": "CHAC",
    "MZB": "MABA",
    "MZC": "MACI",
    "MZD": "MADE",
    "PABA": "DPBA",
    "PACI": "DPCI",
    "UCET": "UCET",
    "UDEC": "UCET",
}

DICCIONARIO_ESTACIONES_DIRECTORIO = {
    "Azogues": "CICA",
    "CICA": "CICA",
    "ChaBase": "CHAB",
    "ChaCima": "CHAC",
    "Chanlbas": "CHAB",
    "Chanlcim": "CHAC",
    "ChanludBase": "CHAB",
    "ChanludCima": "CHAC",
    "EEAlNor": "EEAN",
    "EEALNor": "EEAN",
    "EEAlSur": "EEAS",
    "EEAltSur": "EEAS",
    "EEBase": "EEBA",
    "EEE-AltNort": "EEAN",
    "EEE-AltSur": "EEAS",
    "EEE-Base": "EEBA",
    "EEEBASE": "EEAS",
    "HUAJIBAM": "AHUA",
    "Huajibam": "AHUA",
    "Huajibamba": "AHUA",
    "Huajibamba-SSA": "AHUA",
    "MABA": "MABA",
    "MACI": "MACI",
    "MADE": "MADE",
    "MazarBas": "MABA",
    "MazarBase": "MABA",
    "MazarCim": "MACI",
    "MazarCima": "MACI",
    "MazarDer": "MADE",
    "Miraflo": "MIRA",
    "Miraflor": "MIRA",
    "Miraflores": "MIRA",
    "PauMed": "DPME",
    "PauteBas": "DPBA",
    "PauteBase": "DPBA",
    "PauteCim": "DPCI",
    "PauteCima": "DPCI",
    "Regcivil": "REGC",
    "UAzuay": "UDAZ",
    "UCCamp": "UCET",
    "UCcamp": "UCET",
    "UCET": "UCET",
    "UCoficin": "UCAO",
    "UDEC": "UCET",
}


def normalizar_codigo_estacion_desde_directorio(entrada):
    entrada = str(entrada).strip()
    if entrada in DICCIONARIO_ESTACIONES_DIRECTORIO:
        return DICCIONARIO_ESTACIONES_DIRECTORIO[entrada]
    entrada_lower = entrada.lower()
    for clave, valor in DICCIONARIO_ESTACIONES_DIRECTORIO.items():
        if str(clave).lower() == entrada_lower:
            return valor
    return entrada


def normalizar_codigo_estacion_desde_evt(entrada):
    return DICCIONARIO_ESTACIONES_EVT.get(entrada, entrada)


def extraer_fecha_evt_desde_ruta(archivo_evt):
    for parte in reversed(Path(archivo_evt).parts[:-1]):
        if len(parte) == 8 and parte.isdigit():
            try:
                return datetime.strptime(parte, "%Y%m%d").date()
            except ValueError:
                continue
    return None


def corregir_tiempo_reset_1980(stream, archivo_evt):
    if not stream or stream[0].stats.starttime.year != 1980:
        return False, ""

    inicio_original = stream[0].stats.starttime
    fecha_referencia = extraer_fecha_evt_desde_ruta(archivo_evt)
    origen_fecha = "ruta"

    if fecha_referencia is None:
        fecha_referencia = datetime.fromtimestamp(os.path.getmtime(archivo_evt)).date()
        origen_fecha = "fecha de modificacion"

    inicio_corregido = datetime(
        fecha_referencia.year,
        fecha_referencia.month,
        fecha_referencia.day,
        inicio_original.hour,
        inicio_original.minute,
        inicio_original.second,
        inicio_original.microsecond,
    )
    diferencia = UTCDateTime(inicio_corregido) - inicio_original
    for traza in stream:
        traza.stats.starttime += diferencia

    return True, f"Tiempo EVT 1980 corregido con {origen_fecha}: {inicio_corregido:%Y-%m-%d %H:%M:%S}"


def ajustar_tiempos_stream_con_catalogo(eventos, stream, tolerancia_minutos=5):
    """
    Ajusta el starttime de cada traza del Stream para calzar con el evento más cercano
    dentro de una tolerancia dada. Devuelve el stream ajustado, una bandera de si hubo
    calce, el tipo de evento ('FF', 'FC', 'SISMO') y el nombre sugerido del .mseed.
    """
    tr = stream[0]
    estacion = normalizar_codigo_estacion_desde_evt(str(tr.stats.station).strip().upper())
    inicio = tr.stats.starttime

    tiempo_stream = inicio.datetime
    archivo_mseed = f"{estacion}_{inicio.strftime('%Y%m%d_%H%M%S')}.mseed"
    tolerancia_segundos = int(tolerancia_minutos) * 60

    mejor_evento = None
    mejor_diferencia = float('inf')
    mejor_tipo = None

    for evento in eventos:
        if not evento or len(evento) < 3:
            continue

        tipo = str(evento[2]).strip().upper()
        if tipo not in ("FF", "FC", "SISMO"):
            continue

        crudo = str(evento[1]).strip()
        if "_" not in crudo:
            continue

        ts_txt = crudo[:15]
        try:
            tiempo_evento = datetime.strptime(ts_txt, "%Y%m%d_%H%M%S")
        except Exception:
            try:
                fecha, hora = ts_txt.split("_")
                if len(fecha) == 8 and len(hora) == 6:
                    tiempo_evento = datetime.strptime(f"{fecha}_{hora}", "%Y%m%d_%H%M%S")
                else:
                    continue
            except Exception:
                continue

        diferencia = abs((tiempo_stream - tiempo_evento).total_seconds())
        if diferencia <= tolerancia_segundos and diferencia < mejor_diferencia:
            mejor_evento = tiempo_evento
            mejor_diferencia = diferencia
            mejor_tipo = tipo

    if mejor_evento is not None:
        diferencia_tiempo = mejor_evento - tiempo_stream
        bandera = True
    else:
        diferencia_tiempo = timedelta(seconds=0)
        bandera = False

    for traza in stream:
        traza.stats.starttime += diferencia_tiempo

    return stream, bandera, mejor_tipo, archivo_mseed


def escribir_atomico_mseed(stream, destino):
    """
    Escribe un Stream en formato MSEED de manera atómica con compresión STEIM1 y reclen=512.
    """
    import time
    carpeta = os.path.dirname(destino)
    base = os.path.basename(destino)
    tmp = os.path.join(carpeta, "." + base + ".tmp")
    stream.write(tmp, format='MSEED', encoding='STEIM1', reclen=512)
    try:
        with open(tmp, 'rb') as _f:
            os.fsync(_f.fileno())
    except Exception:
        pass
    for intento in range(3):
        try:
            os.replace(tmp, destino)
            return
        except (PermissionError, OSError):
            if intento < 2:
                time.sleep(0.1)
            else:
                try:
                    if os.path.exists(destino):
                        os.remove(destino)
                    os.replace(tmp, destino)
                    return
                except Exception as e:
                    raise e


def insertar_evento_en_catalogo(directorio_grabar: str, eventos: list, st: Stream, serial_equipo: str = None) -> list:
    """
    Inserta un evento en la lista de eventos, guardando el archivo MiniSEED (STEIM1)
    y marcando en 'eventos' la columna correspondiente a la estación.
    """
    tr = st[0]
    estacion = normalizar_codigo_estacion_desde_evt(str(tr.stats.station).strip().upper())
    inicio = tr.stats.starttime

    prefijo = str(serial_equipo) if serial_equipo else estacion
    nombre_archivo = f"{prefijo}_{inicio.strftime('%Y%m%d_%H%M%S')}.mseed"

    destino = directorio_grabar
    if serial_equipo:
        destino = os.path.join(directorio_grabar, str(serial_equipo))
    os.makedirs(destino, exist_ok=True)

    ruta_completa = os.path.join(destino, nombre_archivo)

    parametros = parametros_estaciones()
    estaciones = [str(x).strip().upper() for x in parametros['CODIGO']]
    componentes = parametros['COMPONENTE']
    try:
        idx_est = estaciones.index(estacion)
    except ValueError:
        print(f"[ADVERTENCIA] Estación '{estacion}' no está en la configuración.")
        return eventos

    archivo_evento = f"{inicio.strftime('%Y%m%d_%H%M%S')}.sis"
    segundos_elementos = [str(f[1]).strip() for f in eventos]
    try:
        n_evento = segundos_elementos.index(archivo_evento)
    except ValueError:
        try:
            n_evento = segundos_elementos[1:].index(archivo_evento) + 1
        except ValueError:
            return eventos

    for tr in st:
        if not hasattr(tr.stats, "calib"):
            tr.stats.calib = 1.0

    escribir_atomico_mseed(st, ruta_completa)
    print(f"\n[MSEED] Insertando evento consolidado: {ruta_completa}")

    col_destino = idx_est + 3
    if col_destino < len(eventos[n_evento]):
        eventos[n_evento][col_destino] = estacion + componentes[idx_est] + '1000000'
    else:
        faltan = col_destino - len(eventos[n_evento]) + 1
        eventos[n_evento].extend([''] * faltan)
        eventos[n_evento][col_destino] = estacion + componentes[idx_est] + '1000000'

    return eventos


def procesar_archivo_evt(archivo_evt, directorio_trabajo, bandera_verificar, bandera_insertar, directorio_destino=None, ventana_parent=None, tolerancia_minutos=5):
    """
    Lee un archivo EVT (Kinemetrics), trata de calzarlo en el catálogo del día para ajustar tiempos,
    clasifica el evento y, si corresponde, inserta el .mseed y actualiza el CSV.
    """
    import re, gc
    import matplotlib.pyplot as plt
    from PyQt5.QtWidgets import QMessageBox

    datos_completos = []

    directorios_almacenamiento = re.split(r"[\\/]", str(archivo_evt))
    partes_ruta_mapeadas = deque()
    for d in directorios_almacenamiento:
        if not d:
            continue
        partes_ruta_mapeadas.append(DICCIONARIO_ESTACIONES_DIRECTORIO.get(d, d))
    directorio_estacion_almacenado = " / ".join(partes_ruta_mapeadas) if partes_ruta_mapeadas else "Sin ruta"

    mensaje = ''
    mensaje_1 = ''
    resultado_str = ''
    archivo_mseed = ''
    archivo = ''
    estacion = 'Ninguna'
    equipo_modelo, equipo_version, equipo_serial = 'Desconocido', 'Desconocida', 'Desconocido'
    aviso_tiempo = ''

    st = None
    try:
        st = read(archivo_evt, format='KINEMETRICS_EVT')
        evt_info = getattr(st[0].stats, 'kinemetrics_evt', {})
    except Exception:
        if os.path.exists(r'O:\KINEMETRICS'):
            try:
                st = ejecutar_en_vm(Path(archivo_evt), Path(r'O:\KINEMETRICS'))
                evt_info = getattr(st[0].stats, 'kinemetrics_evt', {}) if st else {}
            except Exception as e:
                print(f"[AVISO] Fallback ejecutar_en_vm falló para {archivo_evt}: {e}")
                st = None
        else:
            st = None

        if not st:
            archivo_mseed = "No es compatible al formato"
            mensaje = "Error: archivo no legible como EVT (ObsPy/VM no disponible)"
            mensaje_1 = "No insertado"
            datos_grabar = [archivo_evt, archivo_mseed, mensaje, "", mensaje_1,
                            "", directorio_estacion_almacenado, "Desconocido",
                            "Desconocido", "Desconocida", "Desconocido"]
            datos_completos.append(datos_grabar)
            return datos_completos

    try:
        tiempo_corregido, aviso_tiempo = corregir_tiempo_reset_1980(st, archivo_evt)
        if tiempo_corregido:
            print(f"[TIEMPO] {aviso_tiempo} | {archivo_evt}")

        t = st[0].stats.starttime
        archivo = os.path.join(
            directorio_trabajo,
            f"{t.year:04d}{t.month:02d}{t.day:02d}{t.hour:02d}{t.minute:02d}{t.second:02d}"
        )
        directorios = obtener_directorios(archivo)

        try:
            equipo_modelo = str(evt_info.get('comment', 'Desconocido'))
            equipo_version = str(evt_info.get('instrument', 'Desconocida'))
            equipo_serial = str(evt_info.get('serialnumber', 'Desconocido'))
        except Exception:
            pass

        estacion = normalizar_codigo_estacion_desde_evt(str(st[0].stats.station).strip().upper())
        serial_para_nombre = str(equipo_serial) if directorio_destino else None
        directorio_final = directorio_destino if directorio_destino else directorios.get('Directorio_eventos', directorios.get('directorio_eventos', directorio_trabajo))

        ruta_csv = directorios.get('Archivo_csv') or directorios.get('archivo_csv')
        if ruta_csv and os.path.exists(ruta_csv):
            eventos = lectura_archivo(ruta_csv)

            st, bandera_localizacion, tipo, archivo_mseed_nominal = ajustar_tiempos_stream_con_catalogo(
                eventos, st, tolerancia_minutos=tolerancia_minutos
            )

            if serial_para_nombre:
                archivo_mseed = os.path.join(directorio_final, serial_para_nombre, serial_para_nombre + archivo_mseed_nominal[4:])
            else:
                archivo_mseed = os.path.join(directorio_final, archivo_mseed_nominal)

            st_copia = st.copy()
            resultado = clasificar_evento_sismico(st_copia)
            resultado_str = ' / '.join([f"{k}: {v}" for k, v in resultado.items()])

            mensaje = "Evento encontrado: " + (tipo if bandera_localizacion else "No encontrado")
            if aviso_tiempo:
                mensaje += f" | {aviso_tiempo}"

            if bandera_verificar:
                try:
                    plt.close('all')
                    fig, axs = plt.subplots(len(st), 1, figsize=(10, 6), sharex=True)
                    if len(st) == 1:
                        axs = [axs]
                    for ax, tr in zip(axs, st):
                        tiempo = tr.times("matplotlib")
                        ax.plot(tiempo, tr.data, label=tr.id)
                        ax.legend(loc='upper right')
                    axs[-1].set_xlabel("Tiempo")
                    nombre_evt = os.path.basename(archivo_evt)
                    titulo_grafico = (
                        f"Verificación del Evento\n"
                        f"EVT: {nombre_evt}  |  Evento: {os.path.basename(archivo)}  |  Resultado: {mensaje}"
                    )
                    plt.suptitle(titulo_grafico)

                    try:
                        fig.show()
                        plt.pause(0.001)

                        if ventana_parent is not None:
                            if not hasattr(ventana_parent, "_figs_abiertas"):
                                ventana_parent._figs_abiertas = []
                            ventana_parent._figs_abiertas.append(fig)
                            if len(ventana_parent._figs_abiertas) > 5:
                                fig_vieja = ventana_parent._figs_abiertas.pop(0)
                                try:
                                    plt.close(fig_vieja)
                                except Exception:
                                    pass
                    except Exception as e:
                        print(f"[AVISO] Mostrar figura no modal falló: {e}")

                    if bandera_localizacion:
                        respuesta = QMessageBox.question(
                            None, "Insertar evento",
                            "Se guardó una imagen de verificación.\n¿Deseas insertar este evento en la estructura de datos?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if respuesta == QMessageBox.No:
                            mensaje_1 = 'No insertado'
                            bandera_localizacion = False
                    else:
                        QMessageBox.information(None, "AVISO", f"EVT: {nombre_evt}  {mensaje}")
                except Exception as e:
                    print(f"[AVISO] Verificación falló: {e}")

            if bandera_insertar and bandera_localizacion:
                try:
                    eventos = insertar_evento_en_catalogo(directorio_final, eventos, st, serial_para_nombre)
                    escritura_archivo(ruta_csv, eventos)
                    mensaje_1 = 'Insertado'
                except Exception as e:
                    mensaje_1 = f"No insertado: {e}"
        else:
            archivo_mseed = f"No encontrado csv del dia: {ruta_csv}"
            mensaje = "Sin CSV, no se puede localizar/insertar"
    finally:
        try:
            if st is not None:
                st.clear()
                del st
        except Exception:
            pass
        gc.collect()

    datos_grabar = [archivo_evt, archivo_mseed, mensaje, archivo, mensaje_1,
                    resultado_str, directorio_estacion_almacenado, estacion,
                    equipo_modelo, equipo_version, equipo_serial]
    datos_completos.append(datos_grabar)
    return datos_completos


def extraer_rutas_evt_desde_lista(filas_csv_o_rutas):
    rutas_evt = []
    encabezado = None
    indice_ruta = None
    indice_procesar = None

    for fila in filas_csv_o_rutas:
        if isinstance(fila, (list, tuple)):
            if encabezado is None:
                posibles = [str(valor).strip().lower() for valor in fila]
                if "ruta_evt" in posibles:
                    encabezado = posibles
                    indice_ruta = posibles.index("ruta_evt")
                    indice_procesar = posibles.index("procesar") if "procesar" in posibles else None
                    continue

            if indice_ruta is not None:
                if indice_procesar is not None and indice_procesar < len(fila):
                    valor_procesar = str(fila[indice_procesar]).strip().lower()
                    if valor_procesar in ("0", "no", "false", "duplicado"):
                        continue
                ruta_evt = str(fila[indice_ruta]).strip() if indice_ruta < len(fila) else ""
                if ruta_evt:
                    rutas_evt.append(ruta_evt)
                continue

            candidatos = [str(valor).strip() for valor in fila if str(valor).strip()]
            ruta_evt = next((valor for valor in candidatos if valor.lower().endswith(".evt")), "")
            if not ruta_evt and candidatos:
                ruta_evt = candidatos[0]
        else:
            ruta_evt = str(fila).strip()

        if ruta_evt:
            rutas_evt.append(ruta_evt)
    return rutas_evt


def calcular_sha1_archivo(ruta_archivo):
    sha1 = hashlib.sha1()
    with open(ruta_archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            sha1.update(bloque)
    return sha1.hexdigest()


def sugerir_estacion_desde_ruta(ruta_evt):
    partes = Path(ruta_evt).parts
    for parte in reversed(partes[:-1]):
        codigo = normalizar_codigo_estacion_desde_directorio(parte)
        if codigo != parte:
            return codigo
    return ""


def extraer_metadata_evt_para_inventario(ruta_evt):
    metadata = {
        "evt_legible": "0",
        "requiere_vm": "1",
        "estacion_evt": "",
        "estacion_evt_homologada": "",
        "serial": "",
        "instrumento": "",
        "modelo": "",
        "inicio_evt": "",
        "n_trazas": "",
        "canales": "",
        "frecuencia": "",
        "duracion_s": "",
        "error_lectura": "",
    }
    try:
        st = read(ruta_evt, format='KINEMETRICS_EVT')
        metadata["evt_legible"] = "1"
        metadata["requiere_vm"] = "0"
        metadata["n_trazas"] = str(len(st))
        if len(st) > 0:
            tr = st[0]
            estacion_evt = str(tr.stats.station).strip().upper()
            metadata["estacion_evt"] = estacion_evt
            metadata["estacion_evt_homologada"] = normalizar_codigo_estacion_desde_evt(estacion_evt)
            metadata["inicio_evt"] = tr.stats.starttime.strftime("%Y-%m-%d %H:%M:%S")
            metadata["frecuencia"] = str(getattr(tr.stats, "sampling_rate", ""))
            try:
                metadata["duracion_s"] = f"{tr.stats.npts / tr.stats.sampling_rate:.3f}"
            except Exception:
                metadata["duracion_s"] = ""
            metadata["canales"] = ",".join(str(t.stats.channel) for t in st)

            evt_info = getattr(tr.stats, "kinemetrics_evt", {})
            try:
                metadata["serial"] = str(evt_info.get("serialnumber", "")).strip()
                metadata["instrumento"] = str(evt_info.get("instrument", "")).strip()
                metadata["modelo"] = str(evt_info.get("comment", "")).strip()
            except Exception:
                pass
        try:
            st.clear()
        except Exception:
            pass
    except Exception as e:
        metadata["error_lectura"] = str(e)
    return metadata


def construir_clave_organizacion(metadata, estacion_sugerida):
    serial = metadata.get("serial", "").strip()
    estacion_evt = metadata.get("estacion_evt_homologada", "").strip()
    if serial and serial.lower() != "desconocido":
        return f"SERIAL:{serial}"
    if estacion_evt:
        return f"ESTACION_EVT:{estacion_evt}"
    if estacion_sugerida:
        return f"ESTACION_RUTA:{estacion_sugerida}"
    return "SIN_CLAVE"


def generar_inventario_evt_directorio(ruta_base, ruta_salida_csv):
    filas = [[
        "procesar",
        "ruta_evt",
        "nombre",
        "tamano_bytes",
        "mtime_iso",
        "sha1",
        "duplicado_de",
        "estacion_sugerida",
        "evt_legible",
        "requiere_vm",
        "estacion_evt",
        "estacion_evt_homologada",
        "serial",
        "instrumento",
        "modelo",
        "inicio_evt",
        "n_trazas",
        "canales",
        "frecuencia",
        "duracion_s",
        "clave_organizacion",
        "clave_evento",
        "posible_repetido_de",
        "error_lectura",
    ]]
    rutas_evt = []
    vistos_por_hash = {}
    vistos_por_clave_evento = {}
    total = 0
    duplicados = 0

    for raiz, _, archivos in os.walk(ruta_base):
        for archivo in archivos:
            if not archivo.lower().endswith(".evt"):
                continue
            total += 1
            ruta_evt = os.path.join(raiz, archivo)
            try:
                tamano = os.path.getsize(ruta_evt)
                mtime = os.path.getmtime(ruta_evt)
                mtime_iso = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                sha1 = calcular_sha1_archivo(ruta_evt)
            except Exception:
                tamano = ""
                mtime_iso = ""
                sha1 = f"ERROR:{ruta_evt}"

            estacion_sugerida = sugerir_estacion_desde_ruta(ruta_evt)
            metadata = extraer_metadata_evt_para_inventario(ruta_evt)
            clave_organizacion = construir_clave_organizacion(metadata, estacion_sugerida)
            clave_evento = ""
            posible_repetido_de = ""
            if metadata["inicio_evt"]:
                clave_evento = f"{clave_organizacion}|{metadata['inicio_evt']}"
                posible_repetido_de = vistos_por_clave_evento.get(clave_evento, "")
                if not posible_repetido_de:
                    vistos_por_clave_evento[clave_evento] = ruta_evt

            duplicado_de = vistos_por_hash.get(sha1, "")
            procesar = "1"
            if duplicado_de:
                procesar = "0"
                duplicados += 1
            else:
                vistos_por_hash[sha1] = ruta_evt
                rutas_evt.append(ruta_evt)

            filas.append([
                procesar,
                ruta_evt,
                archivo,
                str(tamano),
                mtime_iso,
                sha1,
                duplicado_de,
                estacion_sugerida,
                metadata["evt_legible"],
                metadata["requiere_vm"],
                metadata["estacion_evt"],
                metadata["estacion_evt_homologada"],
                metadata["serial"],
                metadata["instrumento"],
                metadata["modelo"],
                metadata["inicio_evt"],
                metadata["n_trazas"],
                metadata["canales"],
                metadata["frecuencia"],
                metadata["duracion_s"],
                clave_organizacion,
                clave_evento,
                posible_repetido_de,
                metadata["error_lectura"],
            ])

    os.makedirs(os.path.dirname(ruta_salida_csv), exist_ok=True)
    with open(ruta_salida_csv, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerows(filas)

    return rutas_evt, total, duplicados


def construir_fila_resumen_error(ruta_evt, mensaje_error):
    return [
        ruta_evt,
        "",
        f"Error inesperado: {mensaje_error}",
        "",
        "No insertado",
        "",
        "",
        "Desconocido",
        "Desconocido",
        "Desconocida",
        "Desconocido",
    ]


def procesar_lista_archivos_evt(ventana, lista_rutas_evt):
    resumen_procesamiento = []
    encabezado = ['archivo_evt', 'archivo_mseed', 'mensaje', 'archivo', 'insercion',
                  'resultado_str', 'directorio_estacion_almacenado', 'estacion',
                  'equipo_modelo', 'equipo_version', 'equipo_serial']
    resumen_procesamiento.append(encabezado)
    total_archivos = len(lista_rutas_evt)

    ventana.progressBar.setMaximum(total_archivos)
    ventana.progressBar.setValue(0)

    for contador, archivo_evt in enumerate(lista_rutas_evt, start=1):
        print(archivo_evt)
        try:
            datos_archivo = procesar_archivo_evt(
                archivo_evt,
                ventana.directorio_trabajo,
                ventana.checkBox_verificacion.isChecked(),
                ventana.checkBox_insercion.isChecked(),
                ventana.directorio_destino,
                ventana,
            )
        except Exception as error:
            datos_archivo = [construir_fila_resumen_error(archivo_evt, error)]

        resumen_procesamiento.extend(datos_archivo)
        ventana.progressBar.setValue(contador)
        QtWidgets.QApplication.processEvents()

    ventana.progressBar.setValue(total_archivos)
    return resumen_procesamiento


class VentanaInsercionEVT(QMainWindow):
    def __init__(self, parent=None):
        super(VentanaInsercionEVT, self).__init__(parent)

        ruta_ui = os.path.join(ruta_proyecto, "src", "ui", "Insertar_evt.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)
        self.cargar_ayuda_desde_archivo()
        self.setWindowTitle("LECTURA EVT")
        self.parametros = parametros_estaciones()
        self.directorio_trabajo = 'G:/Mi unidad/DIA/'
        self.lbl_directorio_trabajo.setText("Directorio de trabajo:   " + self.directorio_trabajo)
        self.progressBar.setValue(0)

        self.Btn_drive.clicked.connect(self.seleccionar_directorio_trabajo)
        self.Btn_directorio_datos.clicked.connect(self.cargar_directorio_origen)
        self.Btn_iniciar.clicked.connect(self.iniciar_procesamiento)
        self.Btn_salir.clicked.connect(self.cerrar_ventana)
        self.cmbx_eventos.currentTextChanged.connect(self.actualizar_subdirectorios_por_anio)

        for control in (
            "radio_estacion_almacenamiento",
            "checkBox_verificacion_2",
            "radio_guardar_directorios",
        ):
            if hasattr(self, control):
                getattr(self, control).setEnabled(False)

    def cargar_ayuda_desde_archivo(self):
        try:
            rutas_ayuda = [
                os.path.abspath(os.path.join(ruta_proyecto, "ayuda", "ayuda_insercion_evt.html")),
                os.path.abspath(os.path.join(ruta_proyecto, "datos", "ayuda_insercion_evt.html")),
            ]
            ruta_ayuda = next((ruta for ruta in rutas_ayuda if os.path.exists(ruta)), rutas_ayuda[0])

            if not os.path.exists(ruta_ayuda):
                rutas_html = "".join(f"<li><code>{ruta}</code></li>" for ruta in rutas_ayuda)
                mensaje_html = f"""
                <html>
                <head>
                    <meta charset="utf-8">
                </head>
                <body>
                    <h2 style="color:#b85450;">Archivo de ayuda no encontrado</h2>
                    <p>No existe el archivo de ayuda esperado en estas rutas:</p>
                    <ul>{rutas_html}</ul>
                </body>
                </html>
                """
                self.txt_ayuda.setHtml(mensaje_html)
                return

            self.txt_ayuda.setSource(QUrl.fromLocalFile(ruta_ayuda))

        except Exception as error:
            mensaje_error = f"""
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body>
                <h2 style="color:#b85450;">Error al cargar la ayuda</h2>
                <p><b>Detalle:</b> {str(error)}</p>
            </body>
            </html>
            """
            self.txt_ayuda.setHtml(mensaje_error)

    def cargar_directorio_origen(self, event):
        if self.radioDirectorio1.isChecked():
            self.directorio_estacion = QtWidgets.QFileDialog.getExistingDirectory(None, 'Seleccione Directorio EVT')
            if not self.directorio_estacion:
                return

            nombres_directorios = os.listdir(self.directorio_estacion)
            self.directorio_principal = sorted(nombres_directorios)
            self.cmbx_eventos.clear()
            self.cmbx_eventos.addItems(self.directorio_principal)
            self.actualizar_subdirectorios_por_anio(self.cmbx_eventos.currentText())

        if self.radioLista.isChecked():
            self.ruta_csv, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Seleccionar archivo CSV", "", "CSV Files (*.csv)")

        if self.radioDirectorio2.isChecked():
            self.directorio_evt_completo = QtWidgets.QFileDialog.getExistingDirectory(None, 'Seleccione Directorio EVT (completo)')
            if self.directorio_evt_completo:
                salida_inventario = os.path.join(self.directorio_trabajo, "inventario_evt_directorio_completo.csv")
                try:
                    self.lista_evt_directorio_completo, total_evt, duplicados = generar_inventario_evt_directorio(
                        self.directorio_evt_completo,
                        salida_inventario
                    )
                    self.ruta_csv = salida_inventario
                    QMessageBox.information(
                        self,
                        "Inventario EVT generado",
                        "Se genero la lista de directorio completo:\n"
                        f"{salida_inventario}\n\n"
                        f"EVT encontrados: {total_evt}\n"
                        f"Duplicados exactos omitidos: {duplicados}\n"
                        f"EVT a procesar: {len(self.lista_evt_directorio_completo)}"
                    )
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"No se pudo generar inventario EVT:\n{e}")

    def actualizar_subdirectorios_por_anio(self, directorio_anio):
        self.cmbx_subdirectorios.clear()
        self.cmbx_subdirectorios.addItem("Todos")

        if not directorio_anio or not hasattr(self, "directorio_estacion"):
            return

        ruta_anio = os.path.join(self.directorio_estacion, directorio_anio)
        if not os.path.isdir(ruta_anio):
            return

        subdirectorios = [
            nombre
            for nombre in os.listdir(ruta_anio)
            if os.path.isdir(os.path.join(ruta_anio, nombre))
        ]
        self.cmbx_subdirectorios.addItems(sorted(subdirectorios))

    def iniciar_procesamiento(self):
        datos = None
        if self.radio_estacion_serial.isChecked():
            self.directorio_destino = QtWidgets.QFileDialog.getExistingDirectory(self, 'Seleccionar directorio destino por serial')
            if not self.directorio_destino:
                QMessageBox.warning(self, "Advertencia", "No se seleccionó un directorio de destino para el serial. Se cancelará el proceso.")
                return
        else:
            self.directorio_destino = None

        if self.radioDirectorio1.isChecked():
            directorio_anio = self.cmbx_eventos.currentText()
            subdirectorio_filtro = self.cmbx_subdirectorios.currentText()
            ruta_base = os.path.join(self.directorio_estacion, directorio_anio)
            self.estacion = Path(self.directorio_estacion).resolve()
            lista_evt = recolectar_evt(ruta_base)
            if subdirectorio_filtro != "Todos":
                lista_evt = [ruta for ruta in lista_evt if subdirectorio_filtro in Path(ruta).parts]
            total_archivos = len(lista_evt)
            self.progressBar.setMaximum(total_archivos)
            self.progressBar.setValue(0)
            datos = procesar_lista_archivos_evt(self, lista_evt)
        elif self.radioLista.isChecked():
            if not hasattr(self, "ruta_csv") or not self.ruta_csv or not os.path.isfile(self.ruta_csv):
                QMessageBox.warning(self, "Error", "Debes seleccionar un archivo CSV válido.")
                return
            rutas_evt = extraer_rutas_evt_desde_lista(lectura_archivo(self.ruta_csv))
            datos = procesar_lista_archivos_evt(self, rutas_evt)
        elif self.radioDirectorio2.isChecked():
            if hasattr(self, "lista_evt_directorio_completo"):
                lista_evt = self.lista_evt_directorio_completo
                datos = procesar_lista_archivos_evt(self, lista_evt)
            else:
                QMessageBox.warning(self, "Error", "No se ha seleccionado ningún directorio completo.")
                return

        if datos is None:
            QMessageBox.warning(self, "Error", "No hay datos para procesar.")
            return

        salida = os.path.join(self.directorio_trabajo, 'procesados_desde_csv.csv')
        escritura_archivo(salida, datos)
        QMessageBox.information(self, "Proceso finalizado", f"Archivo generado:\n{salida}")

    def seleccionar_directorio_trabajo(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Seleccionar carpeta de trabajo')
        if not folderpath:
            return
        if not folderpath.endswith('/'):
            folderpath += '/'
        self.directorio_trabajo = folderpath
        self.lbl_directorio_trabajo.setText("Directorio de trabajo:   " + self.directorio_trabajo)

    def cerrar_ventana(self):
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VentanaInsercionEVT()
    window.show()
    sys.exit(app.exec_())
