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

def mensaje_lbl(Lbl_Mensajes, mensaje, borrar=False):
    """
    Agrega mensajes con timestamp en Lbl_Mensajes y consola.
    El historial no se borra aunque se reciba borrar=True.
    """
    try:
        Lbl_Mensajes.setAlignment(Qt.AlignLeft)
        Lbl_Mensajes.setLineWrapMode(QTextEdit.WidgetWidth)

        texto_nuevo = "" if mensaje is None else str(mensaje)
        texto_nuevo = " | ".join(linea.strip() for linea in texto_nuevo.splitlines() if linea.strip())
        timestamp = datetime.now().strftime("%H:%M:%S")
        texto_log = f"[{timestamp}] {texto_nuevo}"
        print(texto_log)

        cursor = Lbl_Mensajes.textCursor()
        cursor.movePosition(QTextCursor.End)
        Lbl_Mensajes.setTextCursor(cursor)
        if Lbl_Mensajes.toPlainText():
            Lbl_Mensajes.insertPlainText("\n")
        Lbl_Mensajes.insertPlainText(texto_log)

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

        except FileNotFoundError:
            auxiliar = self.dia + '000000'
            lista_archivos.append(auxiliar)

        lista_archivos.sort()
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
            self.imprimir_png()
            mensaje_lbl(self.Lbl_Mensajes, "Terminado:", True)
        else:
            self.archivo = self.directorio_trabajo + self.dia + '000000'
            mensaje_lbl(self.Lbl_Mensajes, "No hay registros para ese dia. Archivo buscado: " + self.archivo, True)


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
            mensaje = "¡No hay archivos mseed!\n\nProceder a leer el \nregistro continuo\nSe procesarán solo\nlos resgistros analógicos"
        else:
            mensaje = "Archivos encontrados:\n\n" + mensaje
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



