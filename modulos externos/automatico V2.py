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
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src','librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))
# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

import re
import time
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QObject, QDate
import shutil
import struct
import numpy as np
from pathlib import Path as _Path
from metodos_rsa import loc_cabecera, imprimir_plt, conversion_mseed, leer_mseed, lectura_archivo, escritura_archivo
from metodos_gestion import parametros_estaciones, obtencion_hora, obtener_directorios
from datetime import datetime
import obspy
import csv
from PyQt5.QtCore import QThread, pyqtSignal, Qt
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

def mensaje_lbl(Lbl_Mensajes, mensaje, borrar=False):
    """
    Escribe en Lbl_Mensajes (QTextEdit).
    - borrar=True: reemplaza el texto.
    - borrar=False: agrega el mensaje en la siguiente línea.
    """
    try:
        Lbl_Mensajes.setAlignment(Qt.AlignLeft)
        Lbl_Mensajes.setLineWrapMode(QTextEdit.WidgetWidth)

        texto_nuevo = "" if mensaje is None else str(mensaje)

        if borrar:
            Lbl_Mensajes.setPlainText(texto_nuevo)
        else:
            cursor = Lbl_Mensajes.textCursor()
            cursor.movePosition(QTextCursor.End)
            Lbl_Mensajes.setTextCursor(cursor)
            if Lbl_Mensajes.toPlainText():
                Lbl_Mensajes.insertPlainText("\n")
            Lbl_Mensajes.insertPlainText(texto_nuevo)

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

def extraer_id_evento_desde_ruta(texto):
    """
    Obtiene AAAAMMDDhhmmss a partir de:
    - .../AAAAMMDD_hhmmss.sis
    - .../AAAAMMDDhhmmss...
    - .../G:/Mi unidad/DIA/AAAAMMDDhhmmss
    """
    s = str(texto)
    m = re.search(r'(\d{14})', s)
    if m:
        return m.group(1)
    m2 = re.search(r'(\d{8})[^\d]?(\d{6})', s)
    if m2:
        return m2.group(1) + m2.group(2)
    return ""

def dia_de_id_evento(id_evt):
    """ Devuelve AAAAMMDD a partir de AAAAMMDDhhmmss """
    if not id_evt or len(id_evt) < 8:
        return ""
    return id_evt[:8]

def lectura_ultima_fila_analogico(archivo_analogico):
    """ Devuelve cabecera y última fila válida o valores por defecto si no existe. """
    cab = ['Archivo', 'puntero', 'segundo_m', 'contador_s']
    if not os.path.exists(archivo_analogico):
        return cab, [ "", '0', '00000', '0' ]
    try:
        filas = lectura_archivo(archivo_analogico)
        if not filas or len(filas) < 2:
            return cab, [ "", '0', '00000', '0' ]
        fila = filas[-1]
        fila_ext = [
            fila[0] if len(fila) > 0 else "",
            fila[1] if len(fila) > 1 else "0",
            fila[2] if len(fila) > 2 else "00000",
            fila[3] if len(fila) > 3 else "0",
        ]
        return cab, fila_ext
    except Exception:
        return cab, [ "", '0', '00000', '0' ]

def escribir_analogico(archivo_analogico, fila):
    """ Escribe analogico.csv con cabecera + única fila (último estado). """
    cab = ['Archivo', 'puntero', 'segundo_m', 'contador_s']
    escritura_archivo(archivo_analogico, [cab, fila])

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

def verificar_o_resetear_por_dia(directorio_trabajo, directorio_registros, archivo_base, Lbl_Mensajes):
    """
    Verifica si el día de trabajo (derivado de archivo_base) coincide con el día guardado en analogico.csv.
    Si no coincide: reinicia analogico.csv y elimina MSEED del día actual.
    Retorna (dia_actual, fila_analogico) tras la verificación (fila ya coherente con el día).
    """
    archivo_analogico = os.path.join(directorio_trabajo, "analogico.csv")
    id_evt_actual = extraer_id_evento_desde_ruta(archivo_base)
    dia_actual = dia_de_id_evento(id_evt_actual)

    cab, fila = lectura_ultima_fila_analogico(archivo_analogico)
    dia_guardado = dia_de_id_evento(extraer_id_evento_desde_ruta(fila[0]))

    if dia_guardado and dia_actual and (dia_guardado != dia_actual):
        # Reset requerido
        mensaje_lbl(Lbl_Mensajes, f"[INFO] Día diferente: {dia_guardado} → {dia_actual}. Reiniciando control.", False)
        try:
            # reset analogico.csv
            fila_reset = [ archivo_base, '0', '00000', '0' ]
            escribir_analogico(archivo_analogico, fila_reset)
            # eliminar MSEED del día actual
            eliminar_mseeds_del_dia(directorio_registros, dia_actual, Lbl_Mensajes)
            return dia_actual, fila_reset
        except Exception as e:
            mensaje_lbl(Lbl_Mensajes, f"[ERROR] No se pudo reiniciar analogico.csv: {e}", False)
            # aun así intentar borrar mseeds del día para empezar limpio
            eliminar_mseeds_del_dia(directorio_registros, dia_actual, Lbl_Mensajes)
            return dia_actual, fila  # devuelve lo que había
    else:
        # Si no hay fila previa útil, asegura que esté alineada con el archivo_base actual
        if not fila[0]:
            fila = [ archivo_base, '0', '00000', '0' ]
            escribir_analogico(archivo_analogico, fila)
        return dia_actual, fila

def escribir_atomico_mseed(stream, destino):
    """
    Escribe un Stream en formato MSEED de manera atómica (tmp + replace).
    """
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
    # reemplazo atómico
    os.replace(tmp, destino)

def verificar_mseed_contra_analogico(ruta_mseed, t0_esperado, contador_s, Lbl_Mensajes, carpeta_inconsistentes=None, fs_esperada=64.0, tolerancia_fs=1e-6):
    """
    Verifica que el MSEED existente esté alineado con el control:
    - t0_real == t0_esperado
    - sampling_rate ≈ 64 Hz
    - npts == contador_s * 64
    Si no cumple, mueve a inconsistentes (si se indica) y retorna False.
    Si cumple retorna True.
    """
    if not os.path.exists(ruta_mseed):
        return True  # no hay nada que validar

    try:
        st = obspy.read(ruta_mseed)
    except Exception as e:
        mensaje_lbl(Lbl_Mensajes, f"[VERIF] No se pudo leer {ruta_mseed}: {e}", False)
        return False

    if len(st) == 0:
        return True

    # t0_real del stream (mínimo de trazas)
    try:
        t0_real = min(tr.stats.starttime for tr in st)
    except Exception:
        t0_real = None

    # fs y npts por canal (si hay varias trazas, sumar)
    fs_ok = True
    npts_total = 0
    try:
        for tr in st:
            if abs(float(tr.stats.sampling_rate) - fs_esperada) > tolerancia_fs:
                fs_ok = False
            npts_total += int(tr.stats.npts)
    except Exception:
        fs_ok = False

    npts_esp = int(contador_s) * int(fs_esperada)

    ok = True
    if t0_real is not None and t0_real != obspy.UTCDateTime(t0_esperado):
        ok = False
    if not fs_ok:
        ok = False
    if npts_total != npts_esp:
        ok = False

    if not ok:
        # mover a inconsistentes si se pidió
        if carpeta_inconsistentes:
            try:
                os.makedirs(carpeta_inconsistentes, exist_ok=True)
                base = os.path.basename(ruta_mseed)
                marca = datetime.now().strftime('%Y%m%d_%H%M%S')
                destino = os.path.join(carpeta_inconsistentes, f"{marca}_{base}")
                shutil.move(ruta_mseed, destino)
                mensaje_lbl(Lbl_Mensajes, f"[VERIF] MSEED incoherente movido a: {destino}", False)
            except Exception as e:
                mensaje_lbl(Lbl_Mensajes, f"[VERIF] No se pudo mover incoherente {ruta_mseed}: {e}", False)
        else:
            try:
                os.remove(ruta_mseed)
                mensaje_lbl(Lbl_Mensajes, f"[VERIF] MSEED incoherente eliminado: {ruta_mseed}", False)
            except Exception as e:
                mensaje_lbl(Lbl_Mensajes, f"[VERIF] No se pudo eliminar incoherente {ruta_mseed}: {e}", False)
        return False

    return True

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
    import re
    import numpy as np
    from pathlib import Path
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

    def archivo_vacio(ruta):
        try:
            return (not os.path.exists(ruta)) or (os.path.getsize(ruta) == 0)
        except Exception:
            return True

    def es_segundo_ascii_valido(b):
        if b is None or len(b) != 5:
            return False
        try:
            t = b.decode('ascii')
        except Exception:
            return False
        return len(t) == 5 and t.isdigit()

    def extraer_id_evento_desde_ruta_local(texto):
        s = str(texto)
        m = re.search(r'(\d{14})', s)
        if m:
            return m.group(1)
        m2 = re.search(r'(\d{8})[^\d]?(\d{6})', s)
        if m2:
            return m2.group(1) + m2.group(2)
        return ""

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

    # ------------------- Cargar analogico.csv (REANUDACIÓN) -------------- #
    archivo_analogico = os.path.join(directorio_trabajo, "analogico.csv")
    referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s']]
    contador_segundos = 0
    puntero_guardado = 0

    id_evt_bin = extraer_id_evento_desde_ruta_local(archivo_binario)

    filas = []
    if os.path.exists(archivo_analogico):
        try:
            filas = lectura_archivo(archivo_analogico)
        except Exception:
            filas = []

    if not filas or len(filas) < 2:
        fila_sel = [id_evt_bin or archivo_binario, '0', '00000', '0']
        referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila_sel]
    else:
        fila = filas[-1]
        id_evt_csv = extraer_id_evento_desde_ruta_local(fila[0]) if len(fila) > 0 else ""
        fila_sel = fila if id_evt_csv == id_evt_bin or id_evt_csv else fila
        referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila_sel]

    try:
        puntero_guardado = int(referencias[1][1])
    except Exception:
        puntero_guardado = 0
        referencias[1][1] = '0'

    try:
        contador_segundos = int(referencias[1][3])
    except Exception:
        contador_segundos = 0
        referencias[1][3] = '0'

    seg_m = str(referencias[1][2]) if len(referencias[1]) > 2 else "00000"
    ultimo_texto_segundo = seg_m if isinstance(seg_m, str) and len(seg_m) == 5 else "00000"

    with open(archivo_binario, 'rb') as f_loc:
        numero_segundo, configuracion, puntero_cabecera = loc_cabecera(f_loc)
    puntero_inicio_marca = max(0, int(puntero_cabecera) - 5)

    f = open(archivo_binario, 'rb')
    try:
        tamano_archivo = os.path.getsize(archivo_binario)

        if puntero_guardado > 0:
            puntero_lectura = min(max(0, puntero_guardado), tamano_archivo)
        else:
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

            puntero_siguiente = f.tell()
            fila_actual = [
                id_evt_bin or archivo_binario,
                str(puntero_siguiente),
                ultimo_texto_segundo,
                str(contador_segundos)
            ]
            escritura_archivo(archivo_analogico, [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila_actual])

        finally:
            pass

    finally:
        try:
            f.close()
        except Exception:
            pass

    huecos = 0
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
        self.setWindowTitle("PROCESAMIENTO SISMICO")
        self.btn_abrir.clicked.connect(self.Abrir_archivo)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.dateEdit.dateChanged.connect(self.showDate)

        self.parametros = parametros_estaciones()
        self.inicializar_()

        self.nombre_canal = self.parametros['CODIGO']
        self.n_canales = self.parametros['CANALES']
        self.hab_canal = self.parametros['HAB_CANAL']
        self.componente = self.parametros['COMPONENTE']
        self.grafico = self.parametros['HAB_GRAFICO']
        self.hab_plt = self.parametros['HAB_GRAFICO']
        self.gan_plt = self.parametros['GANANCIA']
        self.diez_plt = self.parametros['DIEZMADO_PLT']
        self.bits_ = self.parametros['FACTOR_MUL']

        now = datetime.now()
        fecha = QDate(now.year, now.month, now.day)
        directorio_trabajo = os.path.abspath(os.getcwd())
        aux = len(directorio_trabajo)
        self.directorio_trabajo = 'G:/Mi unidad/DIA/'
        d = datetime.today()
        d = QDate(d.year, d.month, d.day)
        self.dateEdit.setDate(d)
        self.dia = fecha.toString('yyMMdd')
        self.showDate(d)
        mensaje_lbl(self.Lbl_Mensajes, "AUTOMATICO:", False)

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
        mensaje_lbl(self.Lbl_Mensajes, self.directorio_trabajo, True)
        self.showDate(self.date)

    def Abrir_archivo(self):
        lista_archivos = []
        directorio_origen = 'R:'
        try:
            archivos_auxiliar = os.listdir(directorio_origen)
            archivos_filtrados = [f for f in archivos_auxiliar
                                  if re.fullmatch(r'\d{6}(?:000000|235959)', Path(f).stem)
                                  and Path(f).suffix == '']
            for archivo_copiar in archivos_filtrados:
                if archivo_copiar[0:6] == self.dia[2:]:
                    arch_aux = '20' + archivo_copiar
                    archivo_origen = 'R:/' + archivo_copiar
                    archivo_destino = self.directorio_trabajo + '20' + archivo_copiar
                    if archivo_copiar[6:12] == "235959":
                        archivo_destino = self.directorio_trabajo + '20' + archivo_copiar[0:6] + "000000"
                        arch_aux = '20' + archivo_copiar[0:6] + "000000"
                    lista_archivos.append(arch_aux)
                    mensaje_lbl(self.Lbl_Mensajes, "Copiando archivos:\n " + archivo_origen + ' en ' + archivo_destino, True)
                    shutil.copy(archivo_origen, archivo_destino)
        except FileNotFoundError:
            auxiliar = self.dia + '000000'
            lista_archivos.append(auxiliar)

        lista_archivos.sort()
        mensaje_lbl(self.Lbl_Mensajes, str(lista_archivos), False)

        # ====== Control de día & reset seguro antes de leer/convertir ======
        # Preparar rutas del día
        self.inicializar_()
        self.archivo = self.directorio_trabajo + (lista_archivos[0] if lista_archivos else self.dia + '000000')
        self.definir_dia()

        # Verificar día vs analogico.csv y resetear si corresponde
        dia_actual, fila_analogico = verificar_o_resetear_por_dia(
            self.directorio_trabajo,
            self.directorio_registros,
            self.archivo,
            self.Lbl_Mensajes
        )

        # Antes de leer nada, si existen MSEED destino por canal, validar contra analogico.csv
        # (Si no pasa verificación, se mueven a inconsistentes para forzar reconstrucción)
        try:
            contador_s = int(fila_analogico[3]) if len(fila_analogico) > 3 else 0
        except Exception:
            contador_s = 0

        # t0_esperado = obtencion_hora(self.archivo) en UTCDateTime
        dt0 = obtencion_hora(self.archivo)         # datetime de tu helper
        t0_esperado = obspy.UTCDateTime(dt0)       # convertir a UTCDateTime
        carpeta_inconsistentes = os.path.join(self.directorio_registros, "_inconsistentes")

        for i in range(0, 16):
            if str(self.hab_canal[i]) != "0":
                hora_string_primera = dt0.strftime('%y%m%d_%H%M%S')
                nombreMseed_destino = os.path.join(
                    self.directorio_registros,
                    f"{self.nombre_canal[i]}_20{hora_string_primera}.mseed"
                )
                verificar_mseed_contra_analogico(
                    nombreMseed_destino,
                    t0_esperado,
                    contador_s,
                    self.Lbl_Mensajes,
                    carpeta_inconsistentes=carpeta_inconsistentes
                )

        # ================== Loop de lectura/conversión =====================
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

            self.canal, huecos = Leer_binario_comun(
                self.directorio_trabajo,
                self.archivo_binario,
                self.progressBar,
                self.Lbl_Mensajes
            )
            mensaje_lbl(self.Lbl_Mensajes, "Lectura terminada, \n Segundos faltantes " + str(huecos), True)
            self.Btn_Mseed()

        # ====== Unión incremental segura (primero con el primer archivo de la lista) ======
        for i in range(1, len(lista_archivos)):
            self.unir_mseed(lista_archivos[0], lista_archivos[i])

        if lista_archivos:
            self.archivo = self.directorio_trabajo + lista_archivos[0]
            self.fecha_ = obtencion_hora(self.archivo)
            mensaje_lbl(self.Lbl_Mensajes, self.archivo, False)
            self.trCanal = leer_mseed(self.archivo, 0)
            self.imprimir_png()
            mensaje_lbl(self.Lbl_Mensajes, "Terminado:", True)
        else:
            self.archivo = self.directorio_trabajo + self.dia + '000000'
            mensaje_lbl(self.Lbl_Mensajes, "No hay registros para ese día..\nArchivo buscado: " + self.archivo, True)

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
        for i in range(0, 100):
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
            mensaje = "¡No hay archivos mseed!\n\nProceder a leer el \nregistro continuo\nSe procesarán solo\nlos resgistros analógicos"
        else:
            mensaje = "Archivos encontrados:\n\n" + mensaje
        mensaje_lbl(self.Lbl_Mensajes, mensaje, True)

    def Btn_Mseed(self):
        self.canal_np = np.asarray(self.canal)
        mensaje_lbl(self.Lbl_Mensajes, "Grabando Mseed... ", True)
        try:
            estaciones_completo = lectura_archivo(self.estaciones)
            for i in range(0, 16):
                self.hab_canal[i] = estaciones_completo[i+1][1]
                self.nombre_canal[i] = estaciones_completo[i+1][2]
        except Exception:
            pass

        # conversion_mseed escribe cada canal en self.directorio_registros (tu función)
        self.trCanal = conversion_mseed(self.canal_np, self.hab_canal, self.nombre_canal, self.fecha_, self.directorio_registros)
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
                st1.merge(method=0, fill_value='latest')

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
        hora_string = self.fecha_.strftime('%Y%m%d_%H%M%S')
        mensaje_lbl(self.Lbl_Mensajes, 'Imprimiendo PNGs: \n', True)
        for i in range(0, 16):
            if str(self.hab_canal[i]) == '1':
                nombrepng = f"{self.nombre_canal[i]}_{hora_string}.png"
                mensaje_lbl(self.Lbl_Mensajes, '\n' + nombrepng, False)
                nombrepng = os.path.join(self.directorio, nombrepng)
                try:
                    self.trCanal[i].plot(type='dayplot', outfile=nombrepng, dpi=200, size=(2400,1800), linewidth=0.2, show=False)
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes, f"No se pudo generar PNG {nombrepng}: {e}", False)

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



