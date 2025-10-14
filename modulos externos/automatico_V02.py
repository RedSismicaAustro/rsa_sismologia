"""
PROCESAMIENTO SISMICO – Programa unificado (Automático + Acelerógrafos)

Fases encadenadas en una sola corrida:
1) Analógico (Automático): reanuda binario con analogico.csv, une al MSEED diario y genera PNG.
2) Digital (Acelerógrafos): recorre estaciones habilitadas, detecta MSEED del día, une SIEMPRE lo nuevo,
   actualiza digital.csv (multiestación) y genera PNG.

Reglas operativas:
- OBSID es una estación más. Sin tratamiento especial.
- Fechas siempre en YYYYMMDD; identificador del día: AAAAMMDD000000.
- En modo Analógico solo se toca analogico.csv. En modo Digital solo se toca digital.csv.
- Los mensajes del flujo Digital se imprimen en Lbl_Mensajes con el mismo estilo que Automático.
"""

import sys
import os
import re
import shutil
import struct
import csv
from pathlib import Path
from datetime import datetime

from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QObject, QDate, QThread, pyqtSignal, Qt, QCoreApplication
from PyQt5.QtWidgets import (QMainWindow, QMessageBox, QFileDialog, QTextEdit)
from PyQt5.QtGui import QTextCursor

import numpy as np
import obspy
from obspy import UTCDateTime, Trace, Stream

# ==== Rutas base del proyecto ====
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + os.sep
    else:
        return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

# ==== Librerías del proyecto ====
from metodos_rsa import (
    loc_cabecera,          # ya lo usas en analógico
    conversion_mseed,      # analógico
    leer_mseed,            # analógico
    lectura_archivo,       # utilidades csv
    escritura_archivo      # utilidades csv
)
from metodos_gestion import (
    parametros_estaciones,
    obtencion_hora,
    obtener_directorios
)

# ==== Matplotlib en modo no interactivo ====
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()

# =============================================================================
# Mensajería (mantengo tu firma y comportamiento)
# =============================================================================

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

# =============================================================================
# Analógico (con tu implementación completa — sin tocar lógica)
# =============================================================================

def Leer_binario_comun(directorio_trabajo, archivo_binario, barra_progreso, Lbl_Mensajes):
    """
    Lee un binario (registro continuo o evento .sis) con 16 canales a 64 sps, int16 LE.
    Reanuda desde analogico.csv y NO corta por tiempo (no hay solapes al reanudar).
    """
    import numpy as _np

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

    canal = [[] for _ in range(n_canales)]
    linea = [0] * n_canales
    ultimo_texto_segundo = "00000"

    directorios = obtener_directorios(archivo_binario)
    # Escribir archivo_estaciones si está vacío
    try:
        if archivo_vacio(directorios['archivo_estaciones']):
            with open(archivo_binario, 'rb') as ftmp:
                _, configuracion_tmp, _puntero_cab_tmp = loc_cabecera(ftmp)
            with open(directorios['archivo_estaciones'], 'w', newline='') as archivo_estaciones:
                escritor_csv_ = csv.writer(archivo_estaciones, delimiter=';')
                for fila in configuracion_tmp:
                    escritor_csv_.writerow(fila)
    except Exception:
        pass

    archivo_analogico = os.path.join(directorio_trabajo, "analogico.csv")
    referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s']]
    contador_segundos = 0
    puntero_guardado = 0

    # Si existe analogico.csv, tomar su última fila como “verdad”
    if os.path.exists(archivo_analogico):
        try:
            filas = lectura_archivo(archivo_analogico)
        except Exception:
            filas = []
    else:
        filas = []

    if not filas or len(filas) < 2:
        fila_sel = [archivo_binario, '0', '00000', '0']
        referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila_sel]
    else:
        fila = filas[-1]
        referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila]

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

    # Posición segura del inicio de primer bloque
    with open(archivo_binario, 'rb') as f_loc:
        _, _, puntero_cabecera = loc_cabecera(f_loc)
    puntero_inicio_marca = max(0, int(puntero_cabecera) - 5)

    f = open(archivo_binario, 'rb')
    try:
        tamano_archivo = os.path.getsize(archivo_binario)
        if puntero_guardado > 0:
            puntero_lectura = min(max(0, puntero_guardado), tamano_archivo)
        else:
            puntero_lectura = max(0, puntero_inicio_marca)

        # Resync hacia adelante si no cae en marca
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
        mensaje_lbl(Lbl_Mensajes, f"Segundos estimados: {segundos_estimados}", True)

        if barra_progreso is not None:
            barra_progreso.setRange(0, int(segundos_estimados))
            barra_progreso.setValue(0)
            QCoreApplication.processEvents()

        contador = 0
        contador_m = 0
        bandera_linea = 1

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
                        datos = _np.frombuffer(cuerpo_, dtype='<i2')
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
                        contador_m = (contador_m + 1) % 3600
                        contador_segundos += 1
                        if barra_progreso is not None:
                            barra_progreso.setValue(min(contador_segundos, int(segundos_estimados)))
                            QCoreApplication.processEvents()

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

            datos = _np.frombuffer(cuerpo_, dtype='<i2')
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
            contador_m = (contador_m + 1) % 3600
            contador_segundos += 1
            if barra_progreso is not None:
                barra_progreso.setValue(min(contador_segundos, int(segundos_estimados)))
                QCoreApplication.processEvents()

        # Guardar reanudación
        puntero_siguiente = f.tell()
        fila_actual = [archivo_binario, str(puntero_siguiente), ultimo_texto_segundo, str(contador_segundos)]
        referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila_actual]
        escritura_archivo(archivo_analogico, referencias)

    finally:
        try:
            f.close()
        except Exception:
            pass

    huecos = 0
    mensaje_lbl(Lbl_Mensajes, f"Lectura terminada,\nSegundos leídos: {contador}\nSegundos faltantes: {huecos}", True)
    if barra_progreso is not None:
        barra_progreso.setValue(min(contador, int(segundos_estimados)))
        QCoreApplication.processEvents()

    return canal, huecos

# =============================================================================
# UI
# =============================================================================

ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'ui', "automatico.ui"))
Ui_MainWindow, QtBassClass = uic.loadUiType(ruta_ui)

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super(MyApp, self).__init__(parent)
        QMainWindow.__init__(self)
        uic.loadUi(ruta_ui, self)
        self.setWindowTitle("PROCESAMIENTO SISMICO")

        # === Conexiones Automático (preservadas) ===
        self.btn_abrir.clicked.connect(self.Abrir_archivo)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.dateEdit.dateChanged.connect(self.showDate)

        # === Parametrización / estado Automático (preservado) ===
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
        d = QDate.currentDate()
        self.dateEdit.setDate(d)
        self.dia = fecha.toString('yyyyMMdd')
        self.showDate(d)
        mensaje_lbl(self.Lbl_Mensajes, "AUTOMATICO:", False)
        if os.path.exists('R:'):
            self.bandera_drive_r = 1
        else:
            mostrar_advertencia(self)
            self.bandera_drive_r = 0

        # === Ajustes para DIGITAL (nuevo) ===
        # Directorio de estaciones digitales
        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep

        # Cargar lista de estaciones digitales desde datos/digitales.csv
        archivo_digitales = os.path.join(ruta_proyecto, 'datos', 'digitales.csv')
        try:
            self.est_digitales_ = lectura_archivo(archivo_digitales)
        except Exception:
            self.est_digitales_ = []

        # Reutilizamos de self.parametros para digital
        self.estacion_habilitada = self.parametros['HAB_CANAL']
        self.codigo_estacion = self.parametros['CODIGO']
        self.ganancia = list(map(float, self.parametros['GANANCIA']))
        self.diezmado = list(map(int, self.parametros['DIEZMADO_PLT']))
        self.factor_mult = list(map(float, self.parametros['FACTOR_MUL']))
        self.canal_ = list(map(int, self.parametros['COMPONENTE']))

    # ---------------- Funciones Automático (preservadas) ---------------- #

    def showDate(self, date):
        self.date = date
        self.dia = self.date.toString('yyyyMMdd')
        self.archivo = self.directorio_trabajo + self.dia + '000000'

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if not folderpath:
            return
        folderpath = folderpath if folderpath.endswith('/') else folderpath + '/'
        self.directorio_trabajo = folderpath
        self.Lbl_Mensajes.setText(self.directorio_trabajo)
        # actualizar base digital
        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
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
        mensaje_lbl(self.Lbl_Mensajes, lista_archivos, False)

        for archivo_ in lista_archivos:
            self.inicializar_()
            self.archivo = self.directorio_trabajo + archivo_
            self.definir_dia()
            self.archivo_binario = self.directorio_trabajo + archivo_
            if not os.path.exists(self.archivo_binario):
                nombre_archivo = self.archivo_binario[-12:]
                self.archivo_binario, _ = QFileDialog.getOpenFileName(None, "Seleccionar archivo", "", f"{nombre_archivo} ({nombre_archivo})")

            self.canal, huecos = Leer_binario_comun(
                self.directorio_trabajo,
                self.archivo_binario,
                self.progressBar,
                self.Lbl_Mensajes
            )
            mensaje_lbl(self, "Lectura terminada, \n Segundos faltantes " + str(huecos), True)
            self.Btn_Mseed()

        # Unir MSEED analógicos si hubo varios cortes
        for i in range(1, len(lista_archivos)):
            self.unir_mseed(lista_archivos[0], lista_archivos[i])

        if lista_archivos != []:
            self.archivo = self.directorio_trabajo + lista_archivos[0]
            self.fecha_ = obtencion_hora(self.archivo)
            mensaje_lbl(self.Lbl_Mensajes, self.archivo, False)
            self.trCanal = leer_mseed(self.archivo, 0)
            self.imprimir_png()
            mensaje_lbl(self.Lbl_Mensajes, "Terminado:", True)
        else:
            self.archivo = self.directorio_trabajo + self.dia + '000000'
            mensaje_lbl(self.Lbl_Mensajes, "No hay registros para ese día..\nArchivo buscado: " + self.archivo, True)

        # === HANDOFF a Digital ===
        mensaje_lbl(self.Lbl_Mensajes,
                    f"Sección Analógico finalizada.\nIniciando Acelerógrafos para {os.path.basename(self.archivo)}…",
                    True)
        self.procesar_modo_digital()

    def inicializar_(self):
        self.canal_np = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
        self.trCanal  = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
        self.linea = [0]*16
        self.suma  = [0]*16
        self.canal = [[] for _ in range(16)]

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

        # Inicialización de directorios
        for ruta in (self.directorio, self.directorio_dia, self.directorio_eventos,
                     self.directorio_registros, self.directorio_reportes,
                     self.directorio_acel, os.path.join(self.directorio, "fastHypo")):
            try:
                Path(ruta).mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                pass

        # Mensaje de archivos mseed (tu estilo)
        mensaje = ""
        hora_string = self.fecha_.strftime('%Y%m%d_%H%M%S')
        contador = 0
        for i in range(0, 100):
            nombreMseed = self.directorio_registros + "/" + self.nombre_canal[i] + '_' + hora_string + ".mseed"
            try:
                auxiliar = open(nombreMseed, 'r')
                auxiliar.close
                contador += 1
                mensaje = mensaje + self.nombre_canal[i] + "  "
                if contador == 4:
                    mensaje = mensaje + "\n"
                    contador = 0
            except FileNotFoundError:
                pass
        if len(mensaje) == 0:
            mensaje = "¡No hay archivos mseed!\n\nProceder a leer el \nregistro continuo\nSe procesarán solo\nlos resgistros analógicos"
        else:
            mensaje = "Archivos encontrados:\n\n" + mensaje
        mensaje_lbl(self.Lbl_Mensajes, mensaje, True)

    def Btn_Mseed(self):
        self.canal_np = np.asarray(self.canal)
        self.Lbl_Mensajes.setText("Grabando Mseed... ")
        mensaje_lbl(self.Lbl_Mensajes, "Grabando Mseed... \n" + str(self.canal_np), False)

        estaciones_completo = lectura_archivo(self.estaciones)
        for i in range(0, 16):
            self.hab_canal[i] = estaciones_completo[i+1][1]
            self.nombre_canal[i] = estaciones_completo[i+1][2]

        self.trCanal = conversion_mseed(self.canal_np, self.hab_canal, self.nombre_canal, self.fecha_, self.directorio_registros)
        self.Lbl_Mensajes.setText("Grabación Mseed Terminada ")
        mensaje_lbl(self.Lbl_Mensajes, "Grabación Mseed Terminada ", False)

    def unir_mseed(self, archivo_1, archivo_2):
        fecha_1 = obtencion_hora(archivo_1)
        hora_string_1 = fecha_1.strftime('%Y%m%d_%H%M%S')
        fecha_1 = obtencion_hora(archivo_2)
        hora_string_2 = fecha_1.strftime('%Y%m%d_%H%M%S')
        for i in range(0, 16):
            if self.hab_canal[i] != "0":
                nombreMseed_1 = self.directorio_registros + "/" + self.nombre_canal[i] + '_' + hora_string_1 + ".mseed"
                st1 = obspy.read(nombreMseed_1)
                nombreMseed_2 = self.directorio_registros + "/" + self.nombre_canal[i] + '_' + hora_string_2 + ".mseed"
                mensaje_lbl(self.Lbl_Mensajes, "Uniendo archivo: " + nombreMseed_1 + ' y ' + nombreMseed_2, True)
                st2 = obspy.read(nombreMseed_2)
                st1 += st2
                st1.merge(method=0, fill_value='latest')
                st1.write(nombreMseed_1, format='MSEED', encoding='STEIM1', reclen=512)
                try:
                    #os.remove(nombreMseed_2)
                    mensaje_lbl(self.Lbl_Mensajes, f'Archivo "{nombreMseed_2}" borrado exitosamente.', False)
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes, f'No se pudo borrar "{nombreMseed_2}": {e}', False)
        mensaje_lbl(self.Lbl_Mensajes, "Archivos Unidos ", False)

    def imprimir_png(self):
        hora_string = self.fecha_.strftime('%Y%m%d_%H%M%S')
        mensaje_lbl(self.Lbl_Mensajes, 'Imprimiendo PNGs: \n', True)
        for i in range(0, 16):
            if self.hab_canal[i] == '1':
                nombrepng = self.nombre_canal[i] + "_" + hora_string + ".png"
                mensaje_lbl(self.Lbl_Mensajes, '\n' + nombrepng, False)
                nombrepng = self.directorio + "/" + nombrepng
                self.trCanal[i].plot(type='dayplot', outfile=nombrepng, dpi=200, size=(2400, 1800), linewidth=0.2, show=False)

    def Salir_(self):
        self.close()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.closeAllWindows()

    def closeEvent(self, event):
        event.accept()

    # ===================== MODO DIGITAL (ACELERÓGRAFOS) ===================== #

    def procesar_modo_digital(self):
        """
        Para cada estación digital habilitada:
          1) Recolecta MSEED del día (regex YYYYMMDD)
          2) Calcula NUEVOS (digital.csv multiestación)
          3) Une SIEMPRE nuevos, merge(method=0)
          4) Actualiza/crea fila de esa estación en digital.csv
          5) Genera PNG EEEE_YYYYMMDD_000000.png
        """
        # Asegurar rutas del día
        self.definir_dia()

        # Directorio 'Datos Estaciones'
        try:
            dir_aux = os.listdir(self.directorio_binario)
        except FileNotFoundError:
            QMessageBox.information(self, "Advertencia", f"No existe el directorio: {self.directorio_binario}")
            return

        dia_yyyymmdd = self.date.toString('yyyyMMdd')
        archivo_evento = dia_yyyymmdd + "000000"
        archivo_digital = os.path.join(self.directorio_trabajo, "digital.csv")

        # Cargar/normalizar control
        if os.path.exists(archivo_digital):
            filas_ctrl = lectura_archivo(archivo_digital)
        else:
            filas_ctrl = []

        if not filas_ctrl or len(filas_ctrl) == 0 or filas_ctrl[0][0] != 'Archivo':
            filas_ctrl = [['Archivo', 'Estacion', 'mseeds']]

        # Reinicio por día: conservar solo filas del día actual
        filas_filtradas = [filas_ctrl[0]]
        for idx in range(1, len(filas_ctrl)):
            if len(filas_ctrl[idx]) >= 2 and filas_ctrl[idx][0] == archivo_evento:
                filas_filtradas.append(filas_ctrl[idx])
        filas_ctrl = filas_filtradas

        # Recorre estaciones listadas en digitales.csv (saltando cabecera si la hay)
        if self.est_digitales_:
            it_estaciones = self.est_digitales_[1:] if (self.est_digitales_[0] and len(self.est_digitales_[0]) > 0) else self.est_digitales_
        else:
            it_estaciones = []

        for estacion_digital in it_estaciones:
            # estacion_digital: [NombreDir, indice_estacion, habilitado?]  (según tu csv)
            try:
                num_estacion = int(estacion_digital[1])
            except Exception:
                continue

            if self.estacion_habilitada[num_estacion] != '1':
                mensaje_lbl(self.Lbl_Mensajes,
                            f"Estación {self.nombre_canal[num_estacion]} ({self.codigo_estacion[num_estacion]}) NO habilitada",
                            False)
                continue

            nombre_dir_estacion = estacion_digital[0]       # subcarpeta en "Datos Estaciones/"
            estacion = self.codigo_estacion[num_estacion]   # 'EEEE'
            lista_archivos_mseed = []

            # ¿Existe la carpeta?
            if nombre_dir_estacion not in dir_aux:
                mensaje_lbl(self.Lbl_Mensajes,
                            f"Estación {nombre_dir_estacion}: sin carpeta en 'Datos Estaciones' (sin registros)",
                            False)
                continue

            ruta_est = os.path.join(self.directorio_binario, nombre_dir_estacion)
            try:
                archivos_est = os.listdir(ruta_est)
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo listar {ruta_est}: {e}")
                continue

            # Detectar por regex EEEE_YYYYMMDD_hhmmss.mseed
            patron = re.compile(rf"^{re.escape(estacion)}_(\d{{8}})_(\d{{6}})\.mseed$", re.IGNORECASE)
            for nombre_arch in archivos_est:
                m = patron.match(nombre_arch)
                if not m:
                    continue
                fecha8 = m.group(1)
                if fecha8 == dia_yyyymmdd:
                    lista_archivos_mseed.append(os.path.join(ruta_est, nombre_arch))

            if not lista_archivos_mseed:
                mensaje_lbl(self.Lbl_Mensajes,
                            f"Estación {nombre_dir_estacion}: sin MSEED del día {dia_yyyymmdd}",
                            False)
                continue

            # Localizar/crear fila de esta estación en digital.csv
            indice_fila_est = None
            for idx in range(1, len(filas_ctrl)):
                if len(filas_ctrl[idx]) >= 2 and filas_ctrl[idx][0] == archivo_evento and filas_ctrl[idx][1] == estacion:
                    indice_fila_est = idx
                    break
            if indice_fila_est is None:
                filas_ctrl.append([archivo_evento, estacion, ''])
                indice_fila_est = len(filas_ctrl) - 1

            campo_prev = filas_ctrl[indice_fila_est][2] if len(filas_ctrl[indice_fila_est]) > 2 else ''
            previos = [p for p in str(campo_prev).strip().strip('"').strip("'").split(' ') if p]
            # dedup preservando orden
            previos = list(dict.fromkeys(previos))
            prev_set = set(previos)

            detectados_base = [os.path.basename(p) for p in lista_archivos_mseed]
            detectados_base = list(dict.fromkeys([p for p in detectados_base if p]))
            nuevos_base = [m for m in detectados_base if m not in prev_set]

            # Mapa basename → ruta completa
            mapa_rutas = {os.path.basename(p): p for p in lista_archivos_mseed}
            nuevos_rutas = [mapa_rutas[m] for m in nuevos_base if m in mapa_rutas]

            archivo_unido = os.path.join(self.directorio_registros, f"{estacion}_{archivo_evento}.mseed")

            mensaje_lbl(self.Lbl_Mensajes,
                        f"[{estacion}] Detectados: {len(detectados_base)} | Nuevos: {len(nuevos_base)}",
                        False)

            # Unión incremental (SIEMPRE lo nuevo)
            if nuevos_rutas:
                meta, atrasados = [], []
                for ruta_m in nuevos_rutas:
                    try:
                        st_head = obspy.read(ruta_m, headonly=True)
                        t0 = min(tr.stats.starttime for tr in st_head)
                        meta.append((t0, ruta_m))
                    except Exception:
                        atrasados.append(ruta_m)
                meta.sort(key=lambda x: x[0])
                ordenados = [r for _, r in meta] + atrasados

                if os.path.exists(archivo_unido):
                    st_base = obspy.read(archivo_unido)
                else:
                    st_base = obspy.Stream()

                st_add = obspy.Stream()
                for ruta_m in ordenados:
                    try:
                        st_add += obspy.read(ruta_m)
                    except Exception as e:
                        print(f"[ADVERTENCIA] No se pudo leer {ruta_m}: {e}")

                if len(st_add) > 0:
                    st_base += st_add
                    st_base.merge(method=0, fill_value='latest')
                    st_base.write(archivo_unido, format='MSEED', encoding='STEIM1', reclen=512)

            # Actualizar control: previos + nuevos
            totales = previos + [m for m in nuevos_base]
            filas_ctrl[indice_fila_est] = [archivo_evento, estacion, " ".join(totales)]
            mensaje_lbl(self.Lbl_Mensajes,
                        f"[{estacion}] Unión completada: {len(nuevos_base)} nuevos → {archivo_unido}",
                        False)

            # Dayplot PNG
            try:
                st_final = obspy.read(archivo_unido)
                idx_cfg = max(0, int(self.canal_[num_estacion]) - 1)
                canal_sel = idx_cfg if idx_cfg < len(st_final) else 0
                nombrepng = os.path.join(self.directorio, f"{estacion}_{archivo_evento[:8]}_{archivo_evento[8:]}.png")
                st_final[canal_sel].plot(
                    type='dayplot',
                    outfile=nombrepng,
                    dpi=200,
                    size=(2400, 1800),
                    linewidth=0.2
                )
                mensaje_lbl(self.Lbl_Mensajes, f"[{estacion}] Dayplot generado: {nombrepng}", False)
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo generar dayplot para {estacion}: {e}")

        # Escribir digital.csv al final
        escritura_archivo(archivo_digital, filas_ctrl)
        mensaje_lbl(self.Lbl_Mensajes, "Acelerógrafos finalizado.", False)


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    app.exec_()

