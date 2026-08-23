import sys
import os
from pathlib import Path

def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    else:
        return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
if not ruta_proyecto:
    raise RuntimeError('No se encontro la raiz del proyecto rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src','librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))
# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

import re
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QDate
import shutil
import numpy as np
from pathlib import Path as _Path

from rsa_io import leer_mseed,lectura_archivo

from rsa_utilidades import loc_cabecera
from metodos_gestion import parametros_estaciones, obtencion_hora, obtener_directorios
from rsa_dominio import obtenerTraza
from datetime import datetime
import obspy

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import ( QMainWindow, QMessageBox, QFileDialog )
from PyQt5.QtCore import QCoreApplication

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()

# ==========================
# Utilitarios de mensajes UI
# ==========================
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor

def mensaje_lbl(Lbl_Mensajes, mensaje, borrar=False, tipo='auto'):
    """
    Agrega mensajes con timestamp formateados en HTML con código de colores en Lbl_Mensajes y consola.
    """
    try:
        Lbl_Mensajes.setAlignment(Qt.AlignLeft)
        Lbl_Mensajes.setLineWrapMode(QTextEdit.WidgetWidth)

        texto_nuevo = "" if mensaje is None else str(mensaje)
        texto_limpio = " | ".join(linea.strip() for linea in texto_nuevo.splitlines() if linea.strip())
        timestamp = datetime.now().strftime("%H:%M:%S")
        texto_log = f"[{timestamp}] {texto_limpio}"
        print(texto_log)

        # Determinar estilo y color visual
        texto_lower = texto_limpio.lower()
        if tipo == 'error' or '[comunicacion]' in texto_lower or 'corte de comunicacion' in texto_lower or 'no hay mseed' in texto_lower or 'carpeta no existe' in texto_lower or 'error' in texto_lower:
            estilo = "color:#b91c1c; font-weight:bold; background:#fef2f2; padding:1px 3px; border-left:3px solid #dc2626;"
            prefijo = "⚠️ "
        elif tipo == 'exito' or 'unido:' in texto_lower or 'terminado' in texto_lower or 'grabación mseed terminada' in texto_lower:
            estilo = "color:#15803d; font-weight:bold; background:#f0fdf4; padding:1px 3px;"
            prefijo = "🟢 "
        elif '===' in texto_limpio:
            estilo = "color:#1e40af; font-weight:bold; background:#eff6ff; padding:2px 4px; border-bottom:1px solid #bfdbfe;"
            prefijo = "📌 "
        elif 'png' in texto_lower:
            estilo = "color:#0f766e;"
            prefijo = "🖼️ "
        else:
            estilo = "color:#334155;"
            prefijo = ""

        html_msg = f"<span style='font-family:Consolas, monospace; font-size:11px; {estilo}'><span style='color:#64748b; font-weight:normal;'>[{timestamp}]</span> {prefijo}{texto_limpio}</span>"
        Lbl_Mensajes.append(html_msg)

        QCoreApplication.processEvents()
    except Exception:
        pass
def mostrar_advertencia(self):
    msg_box = QMessageBox(self)
    msg_box.setWindowTitle('Advertencia')
    texto = '<div style="text-align: center; font-size: 30px;">¡Registro Continuo no conectado!   ¡Verificar que esté en red!</div>'
    msg_box.setText(texto)
    msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
    msg_box.resize(800, 400)
    msg_box.exec_()

# ==========================
# Helpers de control/validación
# ==========================

def eliminar_mseeds_del_dia(directorio_registros, dia_yyyymmdd, Lbl_Mensajes):
    """
    Elimina todos los MSEED del día AAAAMMDD en directorio_registros con patrón:
    EEEE_20YYMMDD_*.mseed  (tolerante a EEEE alfanumérico)
    """
    patron = re.compile(r'^[A-Za-z0-9]{4}_' + re.escape(dia_yyyymmdd) + r'_\d{6}.*\.mseed$', re.IGNORECASE)
    try:
        for nombre in os.listdir(directorio_registros):
            if patron.match(nombre):
                ruta = os.path.join(directorio_registros, nombre)
                try:
                    os.remove(ruta)
                    mensaje_lbl(Lbl_Mensajes, f"[RESET] Borrado MSEED del día: {ruta}", False)
                except Exception as e:
                    mensaje_lbl(Lbl_Mensajes, f"[RESET] No se pudo borrar {ruta}: {e}", False)
    except Exception as e:
        mensaje_lbl(Lbl_Mensajes, f"[RESET] No se pudo listar {directorio_registros}: {e}", False)

def escribir_atomico_mseed(stream, destino):
    """
    Escribe un Stream en formato MSEED de manera atómica (tmp + replace) con reintentos para Windows.
    """
    import time
    carpeta = os.path.dirname(destino)
    base = os.path.basename(destino)
    tmp = os.path.join(carpeta, "." + base + ".tmp")
    # escribir
    stream.write(tmp, format='MSEED', encoding='STEIM1', reclen=512)
    # asegurar persistencia
    try:
        with open(tmp, 'rb') as _f:
            os.fsync(_f.fileno())
    except Exception:
        pass

    # Reemplazo atómico con reintentos ante bloqueos de sincronización
    for intento in range(3):
        try:
            os.replace(tmp, destino)
            return
        except (PermissionError, OSError):
            if intento < 2:
                time.sleep(0.12)
            else:
                try:
                    if os.path.exists(destino):
                        os.remove(destino)
                    os.replace(tmp, destino)
                    return
                except Exception as e:
                    raise e

def conversion_mseed_bloque(canal, hab_canal, nombre_canal, fecha_, directorio, Lbl_Mensajes):
    """
    Convierte un binario ya leido a MSEEDs por bloque, conservando la hora real
    del archivo binario. No acumula ni rellena huecos.
    """
    trCanal = [[] for _ in range(16)]
    hora_string = fecha_.strftime('%Y%m%d_%H%M%S')

    for i in range(16):
        if str(hab_canal[i]) == "0":
            continue

        datos = np.asarray(canal[i], dtype=np.int32)
        if datos.size == 0:
            mensaje_lbl(Lbl_Mensajes, f"[MSEED] {nombre_canal[i]} sin muestras para convertir", False)
            continue

        traza = obtenerTraza(
            nombre_canal[i],
            1,
            datos,
            fecha_.year,
            fecha_.month,
            fecha_.day,
            fecha_.hour,
            fecha_.minute,
            fecha_.second,
            0
        )
        traza.stats.sampling_rate = 64.0
        traza.stats.starttime = obspy.UTCDateTime(
            fecha_.year,
            fecha_.month,
            fecha_.day,
            fecha_.hour,
            fecha_.minute,
            fecha_.second
        )
        stream = obspy.Stream(traces=[traza])
        nombre_mseed = os.path.join(directorio, f"{nombre_canal[i]}_{hora_string}.mseed")
        escribir_atomico_mseed(stream, nombre_mseed)
        trCanal[i] = stream

    return trCanal

# ==========================
# Lector binario (tu versión original, sin cambios de lógica interna)
# ==========================

def Leer_binario_comun(directorio_trabajo, archivo_binario, barra_progreso, Lbl_Mensajes):
    """
    (Tu implementación original, mantenida. Se deja intacta la lógica interna,
    y se ubican los controles de día/MSEED fuera de esta función.)
    """
    import os
    import csv
    import numpy as np
    from PyQt5.QtCore import QCoreApplication

    # ------------------- Constantes de formato --------------------------- #
    bytes_por_segundo = 2077
    n_canales = 16
    sps = 64
    marca_fija = b'\x08\x00\x05\x00'
    cabecera_1_esperada = (
        b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00'
    )
    bytes_cuerpo = 2048

    def es_segundo_ascii_valido(b):
        if b is None or len(b) != 5:
            return False
        try:
            t = b.decode('ascii')
        except Exception:
            return False
        return len(t) == 5 and t.isdigit()

    # ------------------- Estructuras de salida --------------------------- #
    canal = [[] for _ in range(n_canales)]
    linea = [0] * n_canales
    ultimo_texto_segundo = "00000"

    # ------------------- Directorios y cabecera de estaciones ------------ #
    directorios = obtener_directorios(archivo_binario)

    try:
        if (not os.path.exists(directorios['archivo_estaciones'])) or (os.path.getsize(directorios['archivo_estaciones']) == 0):
            with open(archivo_binario, 'rb') as ftmp:
                numero_segundo_tmp, configuracion_tmp, puntero_cab_tmp = loc_cabecera(ftmp)
            with open(directorios['archivo_estaciones'], 'w', newline='') as archivo_estaciones:
                escritor_csv_ = csv.writer(archivo_estaciones, delimiter=';')
                for fila in configuracion_tmp:
                    escritor_csv_.writerow(fila)
    except Exception:
        pass

    # La lectura siempre inicia desde la cabecera localizada del binario.
    contador_segundos = 0
    huecos = 0
    segundo_anterior = None

    def registrar_segundo_leido(texto_segundo):
        nonlocal huecos, segundo_anterior
        try:
            segundo_actual = int(texto_segundo)
        except Exception:
            return
        if segundo_anterior is not None:
            salto = (segundo_actual - segundo_anterior) % 86400
            if salto > 1:
                huecos += salto - 1
        segundo_anterior = segundo_actual
    with open(archivo_binario, 'rb') as f_loc:
        numero_segundo, configuracion, puntero_cabecera = loc_cabecera(f_loc)
    puntero_inicio_marca = max(0, int(puntero_cabecera) - 5)

    f = open(archivo_binario, 'rb')
    try:
        tamano_archivo = os.path.getsize(archivo_binario)

        puntero_lectura = max(0, puntero_inicio_marca)

        f.seek(puntero_lectura)
        pre = f.read(4)
        if pre != marca_fija:
            f.seek(puntero_lectura)
            ventana = 5 * bytes_por_segundo
            avanzado = 0
            encontrado = False
            while avanzado < ventana:
                b4 = f.read(4)
                if len(b4) < 4:
                    break
                if b4 == marca_fija:
                    numero_segundo_b = f.read(5)
                    if not es_segundo_ascii_valido(numero_segundo_b):
                        f.seek(-8, os.SEEK_CUR)
                        avanzado += 1
                        continue
                    cab_1 = f.read(20)
                    if cab_1 != cabecera_1_esperada:
                        f.seek(-24, os.SEEK_CUR)
                        avanzado += 1
                        continue
                    resto = f.read(bytes_cuerpo)
                    if len(resto) < bytes_cuerpo:
                        break
                    encontrado = True
                    puntero_lectura = f.tell()
                    f.seek(-bytes_cuerpo - 20 - 5 - 4, os.SEEK_CUR)
                    break
                else:
                    f.seek(-3, os.SEEK_CUR)
                    avanzado += 1
            if not encontrado:
                f.seek(tamano_archivo)

        pos_inicio_efectiva = f.tell()
        bytes_restantes = max(0, tamano_archivo - pos_inicio_efectiva)
        segundos_estimados = (bytes_restantes // bytes_por_segundo)

        try:
            mensaje_lbl(Lbl_Mensajes, f"Segundos estimados: {segundos_estimados}", True)
        except Exception:
            pass

        if barra_progreso is not None:
            try:
                barra_progreso.setRange(0, int(segundos_estimados))
                barra_progreso.setValue(0)
                QCoreApplication.processEvents()
            except Exception:
                pass

        contador = 0
        contador_m = 0
        bandera_linea = 1

        try:
            while True:
                pos_inicio_candidato = f.tell()
                cab_0 = f.read(4)
                if len(cab_0) == 0:
                    break
                if cab_0 != marca_fija:
                    f.seek(pos_inicio_candidato)
                    ventana = 10 * bytes_por_segundo
                    avanzado = 0
                    encontrado = False
                    while avanzado < ventana:
                        b4 = f.read(4)
                        if len(b4) < 4:
                            break
                        if b4 == marca_fija:
                            numero_segundo_b = f.read(5)
                            if not es_segundo_ascii_valido(numero_segundo_b):
                                f.seek(-8, os.SEEK_CUR)
                                avanzado += 1
                                continue
                            cab_1 = f.read(20)
                            if cab_1 != cabecera_1_esperada:
                                f.seek(-24, os.SEEK_CUR)
                                avanzado += 1
                                continue
                            cuerpo_ = f.read(bytes_cuerpo)
                            if len(cuerpo_) < bytes_cuerpo:
                                break
                            ultimo_texto_segundo = numero_segundo_b.decode('ascii')
                            registrar_segundo_leido(ultimo_texto_segundo)
                            datos = np.frombuffer(cuerpo_, dtype='<i2')
                            try:
                                datos = datos.reshape((sps, n_canales))
                            except ValueError:
                                break

                            if bandera_linea:
                                offset = datos.mean(axis=0).astype(np.int32)
                                datos = (datos.astype(np.int32) - offset).astype(np.int16)
                                linea[:] = offset.tolist()
                                bandera_linea = 0
                            else:
                                datos = (datos.astype(np.int32) - np.array(linea, dtype=np.int32)).astype(np.int16)

                            for m in range(n_canales):
                                canal[m].extend(datos[:, m].tolist())

                            contador += 1
                            contador_m += 1
                            if contador_m == 3600:
                                contador_m = 0

                            contador_segundos += 1
                            if barra_progreso is not None:
                                try:
                                    barra_progreso.setValue(min(contador_segundos, int(segundos_estimados)))
                                    QCoreApplication.processEvents()
                                except Exception:
                                    pass

                            encontrado = True
                            break
                        else:
                            f.seek(-3, os.SEEK_CUR)
                            avanzado += 1
                    if not encontrado:
                        break
                    continue

                numero_segundo_b = f.read(5)
                if not es_segundo_ascii_valido(numero_segundo_b):
                    f.seek(pos_inicio_candidato + 1)
                    continue

                cab_1 = f.read(20)
                if cab_1 != cabecera_1_esperada:
                    f.seek(pos_inicio_candidato + 1)
                    continue

                cuerpo_ = f.read(bytes_cuerpo)
                if len(cuerpo_) < bytes_cuerpo:
                    break

                datos = np.frombuffer(cuerpo_, dtype='<i2')
                try:
                    datos = datos.reshape((sps, n_canales))
                except ValueError:
                    break

                if bandera_linea:
                    offset = datos.mean(axis=0).astype(np.int32)
                    datos = (datos.astype(np.int32) - offset).astype(np.int16)
                    linea[:] = offset.tolist()
                    bandera_linea = 0
                else:
                    datos = (datos.astype(np.int32) - np.array(linea, dtype=np.int32)).astype(np.int16)

                for m in range(n_canales):
                    canal[m].extend(datos[:, m].tolist())

                ultimo_texto_segundo = numero_segundo_b.decode('ascii')
                registrar_segundo_leido(ultimo_texto_segundo)
                contador += 1
                contador_m += 1
                if contador_m == 3600:
                    contador_m = 0

                contador_segundos += 1
                if barra_progreso is not None:
                    try:
                        barra_progreso.setValue(min(contador_segundos, int(segundos_estimados)))
                        QCoreApplication.processEvents()
                    except Exception:
                        pass

        finally:
            pass

    finally:
        try:
            f.close()
        except Exception:
            pass

    try:
        mensaje_lbl(Lbl_Mensajes, f"Lectura terminada,\nSegundos leídos: {contador}\nSegundos faltantes: {huecos}", True)
    except Exception:
        pass

    if barra_progreso is not None:
        try:
            barra_progreso.setValue(min(contador, int(segundos_estimados)))
            QCoreApplication.processEvents()
        except Exception:
            pass

    return canal, huecos

# ==========================
# UI principal
# ==========================

ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src','ui',"automatico.ui"))
ruta_ui = os.path.abspath(ruta_ui)
qtCreatorFile = ruta_ui
Ui_MainWindow, QtBassClass = uic.loadUiType(qtCreatorFile)

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super(MyApp,self).__init__(parent)
        QMainWindow.__init__(self)
        uic.loadUi(ruta_ui, self)
        self.setWindowTitle("CONSOLIDACION MSEED")
        self.btn_abrir.clicked.connect(self.Abrir_archivo)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.dateEdit.dateChanged.connect(self.showDate)

        self.parametros = parametros_estaciones()
        self.config_estaciones = {
            clave: list(valor) if isinstance(valor, list) else valor
            for clave, valor in self.parametros.items()
        }
        self.inicializar_()

        self.nombre_canal = list(self.config_estaciones['CODIGO'])
        self.n_canales = list(self.config_estaciones['CANALES'])
        self.hab_canal = list(self.config_estaciones['HAB_CANAL'])
        self.componente = list(self.config_estaciones['COMPONENTE'])
        self.grafico = list(self.config_estaciones['HAB_GRAFICO'])
        self.hab_plt = list(self.config_estaciones['HAB_GRAFICO'])
        self.gan_plt = list(self.config_estaciones['GANANCIA'])
        self.diez_plt = list(self.config_estaciones['DIEZMADO_PLT'])
        self.bits_ = list(self.config_estaciones['FACTOR_MUL'])
        self.tipo_canal = list(self.config_estaciones['CANAL'])
        archivo_digitales = os.path.join(ruta_proyecto, 'datos', "digitales.csv")
        self.est_digitales_ = lectura_archivo(archivo_digitales)

        now = datetime.now()
        fecha = QDate(now.year, now.month, now.day)
        directorio_trabajo = os.path.abspath(os.getcwd())
        aux = len(directorio_trabajo)
        self.directorio_trabajo = 'G:/Mi unidad/DIA/'
        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
        d = datetime.today()
        d = QDate(d.year, d.month, d.day)
        self.dateEdit.setDate(d)
        self.dia = fecha.toString('yyMMdd')
        self.showDate(d)
        mensaje_lbl(self.Lbl_Mensajes, "CONSOLIDACION MSEED:", False)

        if os.path.exists('R:'):
            self.bandera_drive_r = 1
        else:
            mostrar_advertencia(self)
            self.bandera_drive_r = 0

    def showDate(self, date):
        self.date = date
        self.dia = self.date.toString('yyyyMMdd')
        self.archivo = self.directorio_trabajo + self.dia + '000000'

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if not folderpath:
            return
        if folderpath[-1] != '/':
            folderpath = folderpath + '/'
        self.directorio_trabajo = folderpath
        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
        mensaje_lbl(self.Lbl_Mensajes, self.directorio_trabajo, True)
        self.showDate(self.date)

    def validar_fila_digital(self, fila, numero_fila):
        if len(fila) < 2:
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] digitales.csv fila {numero_fila} incompleta - omitida", False)
            return None

        nombre_carpeta = fila[0].strip()
        numero_estacion = fila[1].strip()
        if not nombre_carpeta:
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] digitales.csv fila {numero_fila} sin carpeta - omitida", False)
            return None

        try:
            num_estacion = int(numero_estacion)
        except ValueError:
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] digitales.csv fila {numero_fila} con numero invalido '{numero_estacion}' - omitida", False)
            return None

        limites = (
            len(self.config_estaciones['HAB_CANAL']),
            len(self.config_estaciones['NOMBRE']),
            len(self.config_estaciones['CODIGO']),
            len(self.config_estaciones['COMPONENTE']),
            len(self.config_estaciones['CANAL']),
        )
        if num_estacion < 0 or any(num_estacion >= limite for limite in limites):
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] digitales.csv fila {numero_fila} referencia estacion {num_estacion} fuera de rango - omitida", False)
            return None

        return nombre_carpeta, num_estacion

    def filas_digitales_validas(self):
        filas_validas = []
        for numero_fila, fila in enumerate(self.est_digitales_[1:], start=2):
            datos_fila = self.validar_fila_digital(fila, numero_fila)
            if datos_fila is not None:
                filas_validas.append((numero_fila, fila, datos_fila[0], datos_fila[1]))
        return filas_validas

    def registrar_huecos_stream(self, stream, codigo_estacion, momento):
        huecos = stream.get_gaps()
        if not huecos:
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: sin huecos detectados {momento}", False)
            return

        mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: {len(huecos)} huecos/solapes detectados {momento}", False)
        for hueco in huecos[:5]:
            red, estacion, ubicacion, canal, inicio, fin, delta, muestras = hueco
            id_traza = ".".join(parte for parte in (red, estacion, ubicacion, canal) if parte)
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {id_traza}: {inicio} a {fin}, delta={delta:.4f}s, muestras={muestras}", False)
        if len(huecos) > 5:
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] ... {len(huecos) - 5} huecos/solapes adicionales", False)

    def seleccionar_traza_png_digital(self, stream, num_estacion, codigo_estacion):
        canal_idx = int(self.config_estaciones['COMPONENTE'][num_estacion]) - 1
        if canal_idx < 0:
            canal_idx = 0

        stream_ordenado = stream.copy()
        stream_ordenado.sort(keys=['network', 'station', 'location', 'channel', 'starttime'])

        orientaciones = str(self.config_estaciones['CANAL'][num_estacion]).strip().upper()
        if canal_idx < len(orientaciones):
            componente = orientaciones[canal_idx]
            for traza in stream_ordenado:
                canal = str(traza.stats.channel).upper()
                if canal.endswith(componente):
                    mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: PNG usando canal {traza.id} por componente {componente}", False)
                    return traza
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: no se encontro componente {componente}; fallback por indice", False)

        if len(stream_ordenado) > canal_idx:
            traza = stream_ordenado[canal_idx]
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: PNG usando canal {traza.id} por indice {canal_idx + 1}", False)
            return traza

        return None

    def procesar_digitales(self):
        mensaje_lbl(self.Lbl_Mensajes, "=== PROCESANDO ESTACIONES DIGITALES ===", False)

        if not os.path.isdir(self.directorio_binario):
            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] No existe el directorio: {self.directorio_binario}", False)
            return []

        dia_yyyymmdd = self.date.toString('yyyyMMdd')
        archivo_evento = dia_yyyymmdd + "_000000"
        patron_mseed_dia = re.compile(r'^([A-Za-z0-9]{4})_(\d{8})_(\d{6}).*\.mseed$', re.IGNORECASE)
        estaciones_procesadas = 0
        png_pendientes = []
        estado_comunicaciones = {}

        for numero_fila, estacion_digital, nombre_carpeta, num_estacion in self.filas_digitales_validas():
            if self.config_estaciones['HAB_CANAL'][num_estacion] != '1':
                mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] Estacion {self.config_estaciones['NOMBRE'][num_estacion]} no habilitada - omitida", False)
                continue

            codigo_estacion = self.config_estaciones['CODIGO'][num_estacion]
            ruta_carpeta = os.path.join(self.directorio_binario, nombre_carpeta)
            if not os.path.isdir(ruta_carpeta):
                # Búsqueda resiliente de variantes (ej: LAB02 <-> LAB2, CHA02 <-> CHA2)
                carpeta_encontrada = None
                try:
                    nombre_norm = nombre_carpeta.strip().upper()
                    variantes = {nombre_carpeta.upper(), nombre_norm, codigo_estacion.upper()}
                    match_num = re.search(r'([A-Za-z]+)(\d+)$', nombre_norm)
                    if match_num:
                        prefix = match_num.group(1)
                        num_int = int(match_num.group(2))
                        variantes.add(f"{prefix}{num_int}")
                        variantes.add(f"{prefix}{num_int:02d}")
                    
                    for sub in os.listdir(self.directorio_binario):
                        if sub.upper() in variantes:
                            sub_path = os.path.join(self.directorio_binario, sub)
                            if os.path.isdir(sub_path):
                                carpeta_encontrada = sub_path
                                break
                except Exception:
                    pass

                if carpeta_encontrada:
                    ruta_carpeta = carpeta_encontrada
                else:
                    mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: carpeta no existe: {ruta_carpeta}", False)
                    continue

            archivos_mseed = []
            archivos_otro_codigo = 0
            try:
                for archivo in os.listdir(ruta_carpeta):
                    match = patron_mseed_dia.match(archivo)
                    if not match or match.group(2) != dia_yyyymmdd:
                        continue
                    codigo_archivo = match.group(1).upper()
                    if codigo_archivo != codigo_estacion.upper():
                        archivos_otro_codigo += 1
                        continue
                    archivos_mseed.append(os.path.join(ruta_carpeta, archivo))
            except Exception as e:
                mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: error al listar {ruta_carpeta}: {e}", False)
                continue

            if archivos_otro_codigo:
                mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: {archivos_otro_codigo} archivos del dia ignorados por otro codigo", False)

            if not archivos_mseed:
                mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: no hay MSEED para este dia", False)
                continue

            mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: {len(archivos_mseed)} archivos encontrados", False)

            archivos_con_tiempo = []
            archivos_sin_tiempo = []
            for ruta in archivos_mseed:
                try:
                    st = obspy.read(ruta, headonly=True)
                    t0 = min(tr.stats.starttime for tr in st)
                    archivos_con_tiempo.append((t0, ruta))
                except Exception as e:
                    archivos_sin_tiempo.append(ruta)
                    mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: sin cabecera legible {os.path.basename(ruta)}: {e}", False)

            archivos_con_tiempo.sort(key=lambda x: x[0])
            rutas_ordenadas = [r for _, r in archivos_con_tiempo] + archivos_sin_tiempo

            stream_unido = obspy.Stream()
            for ruta in rutas_ordenadas:
                try:
                    stream_unido += obspy.read(ruta)
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: error al leer {os.path.basename(ruta)}: {e}", False)

            if len(stream_unido) == 0:
                mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: no se pudo leer ningun dato", False)
                continue

            self.registrar_huecos_stream(stream_unido, codigo_estacion, "antes de unir")
            stream_unido.merge(method=1, fill_value=None)
            stream_unido = stream_unido.split()
            self.registrar_huecos_stream(stream_unido, codigo_estacion, "despues de unir")

            archivo_salida = os.path.join(self.directorio_registros, f"{codigo_estacion}_{archivo_evento}.mseed")
            try:
                escribir_atomico_mseed(stream_unido, archivo_salida)
                mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] Unido: {codigo_estacion}_{archivo_evento}.mseed", False)
                png_pendientes.append((archivo_salida, num_estacion, codigo_estacion, archivo_evento))
            except Exception as e:
                mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: error al guardar: {e}", False)
                continue

            estaciones_procesadas += 1
            estado_comunicaciones[codigo_estacion] = 1
            QCoreApplication.processEvents()

        # Registrar estado 0 para estaciones habilitadas sin datos
        for numero_fila, estacion_digital, nombre_carpeta, num_estacion in self.filas_digitales_validas():
            if self.config_estaciones['HAB_CANAL'][num_estacion] == '1':
                codigo = self.config_estaciones['CODIGO'][num_estacion]
                if codigo not in estado_comunicaciones:
                    estado_comunicaciones[codigo] = 0

        # Guardar archivo sobrio de estado de comunicaciones
        try:
            archivo_com = os.path.join(self.directorio_trabajo, "comunicaciones.csv")
            lineas_com = ["ESTACION,TIPO,ESTADO,FECHA\n"]
            for cod, est in sorted(estado_comunicaciones.items()):
                lineas_com.append(f"{cod},digital,{est},{dia_yyyymmdd}\n")
            with open(archivo_com, "w", encoding="utf-8") as f_com:
                f_com.writelines(lineas_com)
        except Exception as e:
            mensaje_lbl(self.Lbl_Mensajes, f"[COMUNICACION] Error al guardar comunicaciones.csv: {e}", False)

        cortadas = [cod for cod, est in estado_comunicaciones.items() if est == 0]
        if cortadas:
            mensaje_lbl(self.Lbl_Mensajes, f"[COMUNICACION] Corte de comunicacion ({len(cortadas)} estaciones): {', '.join(cortadas)}", False, tipo='error')
        else:
            mensaje_lbl(self.Lbl_Mensajes, "[COMUNICACION] Todas las estaciones con enlace operativo", False, tipo='exito')

        mensaje_lbl(self.Lbl_Mensajes, f"=== DIGITALES COMPLETADO: {estaciones_procesadas} estaciones ===", False)
        return png_pendientes

    def imprimir_png_digitales(self, png_pendientes):
        if not png_pendientes:
            return

        import matplotlib.pyplot as plt
        mensaje_lbl(self.Lbl_Mensajes, "Imprimiendo PNGs digitales:", False)
        for archivo_salida, num_estacion, codigo_estacion, archivo_evento in png_pendientes:
            try:
                stream_unido = obspy.read(archivo_salida)
                traza_png = self.seleccionar_traza_png_digital(stream_unido, num_estacion, codigo_estacion)
                if traza_png is not None:
                    png_salida = os.path.join(self.directorio, f"{codigo_estacion}_{archivo_evento}.png")
                    traza_png.plot(type='dayplot', outfile=png_salida, dpi=200, size=(2400, 1800), linewidth=0.2, show=False)
                    plt.close('all')
                    mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] PNG: {codigo_estacion}_{archivo_evento}.png", False)
                else:
                    mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: no existe canal valido para PNG", False)
            except Exception as e:
                mensaje_lbl(self.Lbl_Mensajes, f"[DIGITAL] {codigo_estacion}: error al generar PNG: {e}", False)
            QCoreApplication.processEvents()

    def Abrir_archivo(self):
        lista_archivos = []
        directorio_origen = 'R:'

        try:
            archivos_auxiliar = os.listdir(directorio_origen)

            # aceptar cualquier archivo con formato AAMMDDhhmmss y sin extensión
            archivos_filtrados = [
                f for f in archivos_auxiliar
                if re.fullmatch(r'\d{12}', Path(f).stem)
                and Path(f).suffix == ''
            ]

            for archivo_copiar in archivos_filtrados:

                # solo archivos del día seleccionado
                if archivo_copiar[0:6] == self.dia[2:]:

                    arch_aux = '20' + archivo_copiar
                    archivo_origen = 'R:/' + archivo_copiar
                    archivo_destino = self.directorio_trabajo + '20' + archivo_copiar

                    # corrección del caso AAMMDD235959 -> AAMMDD000000
                    if archivo_copiar[6:12] == "235959":
                        archivo_destino = self.directorio_trabajo + '20' + archivo_copiar[0:6] + "000000"
                        arch_aux = '20' + archivo_copiar[0:6] + "000000"

                    lista_archivos.append(arch_aux)
                    mensaje_lbl(
                        self.Lbl_Mensajes,
                        "Copiando archivos:\n " + archivo_origen + ' en ' + archivo_destino,
                        True
                    )
                    shutil.copy(archivo_origen, archivo_destino)

        except (FileNotFoundError, OSError):
            pass

        # Si no se encontraron archivos en R:/, buscar binarios analógicos del día existentes en directorio_trabajo
        if not lista_archivos:
            try:
                for f_local in os.listdir(self.directorio_trabajo):
                    if re.fullmatch(r'\d{14}', f_local) and f_local.startswith(self.dia):
                        lista_archivos.append(f_local)
            except Exception:
                pass
            if not lista_archivos:
                candidato_base = self.dia + '000000'
                if os.path.isfile(os.path.join(self.directorio_trabajo, candidato_base)):
                    lista_archivos.append(candidato_base)

        lista_archivos = sorted(list(set(lista_archivos)))
        mensaje_lbl(self.Lbl_Mensajes, str(lista_archivos), False)

        self.inicializar_()
        self.archivo = self.directorio_trabajo + (lista_archivos[0] if lista_archivos else self.dia + '000000')
        self.definir_dia()

        eliminar_mseeds_del_dia(self.directorio_registros, self.dia, self.Lbl_Mensajes)
        for archivo_ in lista_archivos:
            self.inicializar_()
            self.archivo = self.directorio_trabajo + archivo_
            self.definir_dia()
            self.archivo_binario = self.directorio_trabajo + archivo_

            if not os.path.exists(self.archivo_binario):
                nombre_archivo = self.archivo_binario[-12:]
                self.archivo_binario, _ = QFileDialog.getOpenFileName(
                    None, "Seleccionar archivo", "", f"{nombre_archivo} ({nombre_archivo})"
                )
                if not self.archivo_binario:
                    mensaje_lbl(self.Lbl_Mensajes, "Seleccion manual cancelada. Se omite el archivo.", False)
                    continue

            self.canal, huecos = Leer_binario_comun(
                self.directorio_trabajo,
                self.archivo_binario,
                self.progressBar,
                self.Lbl_Mensajes
            )

            mensaje_lbl(self.Lbl_Mensajes, "Lectura terminada, \n Segundos faltantes " + str(huecos), True)
            self.Btn_Mseed()

        for i in range(1, len(lista_archivos)):
            self.unir_mseed(lista_archivos[0], lista_archivos[i])

        if lista_archivos:
            self.archivo = self.directorio_trabajo + lista_archivos[0]
            self.fecha_ = obtencion_hora(self.archivo)
            mensaje_lbl(self.Lbl_Mensajes, self.archivo, False)
            self.trCanal = leer_mseed(self.archivo, 0)
            png_digitales = self.procesar_digitales()
            self.imprimir_png()
            self.imprimir_png_digitales(png_digitales)
            mensaje_lbl(self.Lbl_Mensajes, "Terminado:", True)
        else:
            self.archivo = self.directorio_trabajo + self.dia + '000000'
            self.definir_dia()
            png_digitales = self.procesar_digitales()
            self.imprimir_png_digitales(png_digitales)
            mensaje_lbl(self.Lbl_Mensajes, "No hay registros analogicos para ese dia. Archivo buscado: " + self.archivo, True)


    def inicializar_(self):
        self.canal_np = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
        self.trCanal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
        self.linea = [0]*16
        self.suma = [0]*16
        self.canal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]

    def definir_dia(self):
        mensaje_lbl(self.Lbl_Mensajes, "Dia: " + self.archivo, True)
        self.directorios_ = obtener_directorios(self.archivo)
        self.directorio = self.directorios_['Directorio_base']
        self.directorio_dia = self.directorios_['Directorio_dia']
        self.directorio_eventos = self.directorios_['Directorio_eventos']
        self.directorio_registros = self.directorios_['Directorio_registros']
        self.directorio_reportes = self.directorios_['Directorio_reportes']
        self.directorio_acel = self.directorios_['Directorio_acelerogramas']
        self.estaciones = self.directorios_['archivo_estaciones']
        self.fecha_ = obtencion_hora(self.archivo)

        if os.path.exists(self.estaciones):
            try:
                os.remove(self.estaciones)
            except Exception:
                pass

        for ruta in (self.directorio, self.directorio_dia, self.directorio_eventos,
                     self.directorio_registros, self.directorio_reportes, self.directorio_acel,
                     os.path.join(self.directorio, "fastHypo")):
            try:
                _Path(ruta).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        # (Mensaje informativo de MSEED ya existentes del día)
        hora_string = self.fecha_.strftime('%y%m%d_%H%M%S')
        mensaje = ""
        contador = 0
        for i in range(0, len(self.nombre_canal)):
            nombreMseed = os.path.join(self.directorio_registros, f"{self.nombre_canal[i]}_20{hora_string}.mseed")
            try:
                with open(nombreMseed, 'rb'):
                    contador += 1
                    mensaje += self.nombre_canal[i] + "  "
                    if contador == 4:
                        mensaje += "\n"
                        contador = 0
            except Exception:
                pass

        if len(mensaje) == 0:
            mensaje = "Iniciando lectura y consolidación continua del día..."
        else:
            mensaje = "Archivos analógicos existentes:\n\n" + mensaje
        mensaje_lbl(self.Lbl_Mensajes, mensaje, True)

    def Btn_Mseed(self):
        mensaje_lbl(self.Lbl_Mensajes, "Grabando Mseed... ", True)
        try:
            estaciones_completo = lectura_archivo(self.estaciones)
            for i in range(0, 16):
                self.hab_canal[i] = estaciones_completo[i+1][1]
                self.nombre_canal[i] = estaciones_completo[i+1][2]
        except Exception:
            pass

        self.trCanal = conversion_mseed_bloque(
            self.canal,
            self.hab_canal,
            self.nombre_canal,
            self.fecha_,
            self.directorio_registros,
            self.Lbl_Mensajes
        )
        mensaje_lbl(self.Lbl_Mensajes, "Grabación Mseed Terminada ", False)

    def unir_mseed(self, archivo_1, archivo_2):
        """
        Une por canal el MSEED del primer bloque con el del segundo y
        reescribe el primero (escritura atómica).
        """
        fecha_1 = obtencion_hora(archivo_1)
        hora_string_1 = fecha_1.strftime('%y%m%d_%H%M%S')
        fecha_2 = obtencion_hora(archivo_2)
        hora_string_2 = fecha_2.strftime('%y%m%d_%H%M%S')

        for i in range(0, 16):
            if str(self.hab_canal[i]) != "0":
                nombreMseed_1 = os.path.join(self.directorio_registros, f"{self.nombre_canal[i]}_20{hora_string_1}.mseed")
                nombreMseed_2 = os.path.join(self.directorio_registros, f"{self.nombre_canal[i]}_20{hora_string_2}.mseed")

                try:
                    st1 = obspy.read(nombreMseed_1)
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes, f"No se pudo abrir base {nombreMseed_1}: {e}", False)
                    continue

                try:
                    st2 = obspy.read(nombreMseed_2)
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes, f"No se pudo abrir suma {nombreMseed_2}: {e}", False)
                    continue

                mensaje_lbl(self.Lbl_Mensajes, f"Uniendo archivo: {nombreMseed_1} + {nombreMseed_2}", False)
                st1 += st2
                huecos_antes = st1.get_gaps()
                if huecos_antes:
                    mensaje_lbl(self.Lbl_Mensajes, f"[UNION] {self.nombre_canal[i]}: {len(huecos_antes)} huecos/solapes antes de unir", False)
                st1.merge(method=1, fill_value=None)
                st1 = st1.split()
                huecos_despues = st1.get_gaps()
                if huecos_despues:
                    mensaje_lbl(self.Lbl_Mensajes, f"[UNION] {self.nombre_canal[i]}: {len(huecos_despues)} huecos preservados", False)

                try:
                    escribir_atomico_mseed(st1, nombreMseed_1)
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes, f"[ERROR] No se pudo escribir unido {nombreMseed_1}: {e}", False)
                    continue

                try:
                    os.remove(nombreMseed_2)
                    mensaje_lbl(self.Lbl_Mensajes, f'Archivo "{nombreMseed_2}" borrado exitosamente.', False)
                except FileNotFoundError:
                    mensaje_lbl(self.Lbl_Mensajes, f'Error: El archivo "{nombreMseed_2}" no existe.', False)
                except PermissionError:
                    mensaje_lbl(self.Lbl_Mensajes, f'Error: Permiso denegado para borrar "{nombreMseed_2}".', False)
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes, f'Ocurrió un error: {e}', False)

        mensaje_lbl(self.Lbl_Mensajes, "Archivos Unidos ", False)

    def imprimir_png(self):
        import matplotlib.pyplot as plt
        hora_string = self.fecha_.strftime('%Y%m%d_%H%M%S')
        mensaje_lbl(self.Lbl_Mensajes, 'Imprimiendo PNGs analógicos: \n', True)
        for i in range(0, 16):
            if str(self.hab_canal[i]) == '1':
                nombrepng = f"{self.nombre_canal[i]}_{hora_string}.png"
                mensaje_lbl(self.Lbl_Mensajes, '\n' + nombrepng, False)
                nombrepng = os.path.join(self.directorio, nombrepng)
                try:
                    self.trCanal[i].plot(type='dayplot', outfile=nombrepng, dpi=200, size=(2400,1800), linewidth=0.2, show=False)
                    plt.close('all')
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes, f"No se pudo generar PNG {nombrepng}: {e}", False)
            QCoreApplication.processEvents()

    def Salir_(self):
        self.close()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.closeAllWindows()

    def closeEvent(self, event):
        print("Cerrando la aplicación desde la ventana.")
        event.accept()

# ==========================
# Main
# ==========================
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    app.exec_()



