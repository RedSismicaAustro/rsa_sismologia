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
ruta_librerias=os.path.dirname(__file__)
ruta_proyecto=extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src','librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))
# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

import re
import time
import sys
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QDate
import shutil
import struct
import numpy as np
from pathlib import Path
from metodos_rsa import loc_cabecera,imprimir_plt,conversion_mseed,leer_mseed,lectura_archivo,escritura_archivo
from metodos_gestion import parametros_estaciones,obtencion_hora,obtener_directorios
from datetime import datetime
import os 
import obspy
import csv
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from PyQt5.QtWidgets import ( QMainWindow,QMessageBox,QFileDialog)

ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src','ui',"automatico.ui"))
ruta_ui = os.path.abspath(ruta_ui)

qtCreatorFile=ruta_ui# Nuestro archivo UI aquí.
Ui_MainWindow,QtBassClass=uic.loadUiType(qtCreatorFile)#El modulo ui carga

import os
from PyQt5.QtCore import QCoreApplication

import matplotlib
matplotlib.use('Agg')
# opcional:
import matplotlib.pyplot as plt
plt.ioff()

def Leer_binario_comun(directorio_trabajo, archivo_binario, barra_progreso, Lbl_Mensajes):
    """
    Lee un binario (registro continuo o evento .sis) con 16 canales a 64 sps, int16 LE.
    Estructura por segundo (tamaño fijo 2077 bytes):
        [4]   marca fija: b'\x08\x00\x05\x00'
        [5]   numero_segundo (ASCII, 5 dígitos)
        [20]  cabecera fija
        [2048] datos (16 canales × 64 muestras × 2 bytes)

    Características:
    - Reanuda desde analogico.csv (puntero del PRÓXIMO segundo).
    - Compara analogico.csv por ID de evento (AAAAMMDDhhmmss), no por ruta literal.
    - Resincroniza SOLO hacia adelante si el puntero cae en medio de un bloque.
    - Escribe analogico.csv con una sola fila (siempre la última).
    - Escribe archivo_estaciones una única vez (si está vacío).
    - Usa NumPy para convertir los 2048 bytes del cuerpo a (64,16) int16.
    - Mantiene contador_m (rueda en 3600) para tu uso posterior.
    - No recorta stream por tiempo: con esta reanudación no hay solapes.
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

    # ------------------- Helpers ---------------------------------------- #
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

    def extraer_id_evento_desde_ruta(texto):
        """
        Obtiene AAAAMMDDhhmmss de ruta/nombre. Acepta:
        - .../AAAAMMDD_hhmmss.sis
        - .../AAAAMMDDhhmmss...
        - .../G:/Mi unidad/DIA/AAAAMMDDhhmmss (tu caso de analogico.csv)
        """
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
    linea = [0] * n_canales                # offset DC por canal (del primer segundo)
    ultimo_texto_segundo = "00000"

    # ------------------- Directorios y cabecera de estaciones ------------ #
    directorios = obtener_directorios(archivo_binario)

    # Escribir archivo_estaciones SOLO si está vacío (evita duplicados múltiples)
    try:
        if archivo_vacio(directorios['archivo_estaciones']):
            with open(archivo_binario, 'rb') as ftmp:
                numero_segundo_tmp, configuracion_tmp, puntero_cab_tmp = loc_cabecera(ftmp)
            with open(directorios['archivo_estaciones'], 'w', newline='') as archivo_estaciones:
                escritor_csv_ = csv.writer(archivo_estaciones, delimiter=';')
                for fila in configuracion_tmp:
                    escritor_csv_.writerow(fila)
    except Exception:
        # No detener el flujo si hay problemas con archivo_estaciones
        pass

    # ------------------- Cargar analogico.csv (REANUDACIÓN) -------------- #
    archivo_analogico = directorios['archivo_analogico']
    referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s']]
    contador_segundos = 0
    puntero_guardado = 0
    id_evt_bin = extraer_id_evento_desde_ruta(archivo_binario)
    filas = []
    if os.path.exists(archivo_analogico):
        try:
            filas = lectura_archivo(archivo_analogico)  # lista de listas
        except Exception:
            filas = []

    if not filas or len(filas) < 2:
        fila_sel = [id_evt_bin or archivo_binario, '0', '00000', '0']
        referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila_sel]
    else:
        fila = filas[-1]  # tu CSV ya se guarda sin append → la última es la válida
        id_evt_csv = extraer_id_evento_desde_ruta(fila[0]) if len(fila) > 0 else ""
        # Si por alguna razón el ID no coincide, igual usamos la última (es tu “verdad”)
        fila_sel = fila if id_evt_csv == id_evt_bin or id_evt_csv else fila
        referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila_sel]

    # Parseo robusto de puntero/contador
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

    # ------------------- loc_cabecera para primera marca del archivo ----- #
    # NOTA: se usa SOLO si no hay puntero guardado (>0).
    with open(archivo_binario, 'rb') as f_loc:
        numero_segundo, configuracion, puntero_cabecera = loc_cabecera(f_loc)
    puntero_inicio_marca = max(0, int(puntero_cabecera) - 5)

    # ------------------- Abrir archivo y definir punto de arranque ------- #
    f = open(archivo_binario, 'rb')
    try:
        tamano_archivo = os.path.getsize(archivo_binario)

        # 1) Reanudar SIEMPRE desde puntero_guardado si es > 0; si no, desde la primera marca
        if puntero_guardado > 0:
            puntero_lectura = min(max(0, puntero_guardado), tamano_archivo)
        else:
            puntero_lectura = max(0, puntero_inicio_marca)

        # 2) Micro-resync: si no cae en marca, AVANZAR hasta próxima marca (nunca retroceder)
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
                    # Validar que existen 5+20+2048 siguientes
                    numero_segundo_b = f.read(5)
                    if not es_segundo_ascii_valido(numero_segundo_b):
                        f.seek(-8, os.SEEK_CUR)  # 4+5-1 → retrocede 8 para deslizar 1 byte
                        avanzado += 1
                        continue
                    cab_1 = f.read(20)
                    if cab_1 != cabecera_1_esperada:
                        f.seek(-24, os.SEEK_CUR)  # 4+5+20 - 5 → dejamos solape y avanzamos 1
                        avanzado += 1
                        continue
                    resto = f.read(bytes_cuerpo)
                    if len(resto) < bytes_cuerpo:
                        break
                    # Encontrado y válido; quedamos al final del cuerpo listo para continuar
                    encontrado = True
                    # IMPORTANTE: ya consumimos este segundo; procesaremos más abajo en el bucle general
                    # Ajustamos puntero_lectura a la posición actual para que el cálculo de estimados sea correcto
                    puntero_lectura = f.tell()
                    # Retrocedemos un segundo para que el while principal lo lea con su flujo normal
                    f.seek(-bytes_cuerpo - 20 - 5 - 4, os.SEEK_CUR)
                    break
                else:
                    f.seek(-3, os.SEEK_CUR)
                    avanzado += 1
            if not encontrado:
                # No se halló marca válida adelante → EOF efectivo
                f.seek(tamano_archivo)

        # 3) Estimación de segundos restantes desde donde estamos
        pos_inicio_efectiva = f.tell()
        bytes_restantes = max(0, tamano_archivo - pos_inicio_efectiva)
        segundos_estimados = (bytes_restantes // bytes_por_segundo)

        # UI progreso
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

        # ------------------- Bucle de lectura ---------------------------- #
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
                    # Resincronización hacia adelante en ventana razonable
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
                            # Segundo válido encontrado
                            ultimo_texto_segundo = numero_segundo_b.decode('ascii')
                            # Procesamiento de datos con NumPy
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
                            # Seguimos con el siguiente segundo (ya estamos al final del cuerpo)
                            break
                        else:
                            f.seek(-3, os.SEEK_CUR)
                            avanzado += 1
                    if not encontrado:
                        break
                    continue  # volvemos al while principal

                # Flujo normal: la marca coincide
                numero_segundo_b = f.read(5)
                if not es_segundo_ascii_valido(numero_segundo_b):
                    # Avanza 1 byte y reintenta
                    f.seek(pos_inicio_candidato + 1)
                    continue

                cab_1 = f.read(20)
                if cab_1 != cabecera_1_esperada:
                    f.seek(pos_inicio_candidato + 1)
                    continue

                cuerpo_ = f.read(bytes_cuerpo)
                if len(cuerpo_) < bytes_cuerpo:
                    break

                # Procesamiento
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

            # FIN while

            # Guardar puntero del PRÓXIMO segundo (posición actual del archivo)
            puntero_siguiente = f.tell()
            fila_actual = [
                id_evt_bin or archivo_binario,
                str(puntero_siguiente),
                ultimo_texto_segundo,
                str(contador_segundos)
            ]
            referencias = [['Archivo', 'puntero', 'segundo_m', 'contador_s'], fila_actual]
            escritura_archivo(archivo_analogico, referencias)

        finally:
            pass

    finally:
        try:
            f.close()
        except Exception:
            pass

    # ------------------- Finalización/UI --------------------------------- #
    huecos = 0  # no estimamos huecos vs 86400 porque puede no ser día completo
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

    # ------------------- Retorno ----------------------------------------- #
    return canal, huecos


def mostrar_advertencia(self):
    msg_box = QMessageBox(self)
    msg_box.setWindowTitle('Advertencia')
    
    texto = '<div style="text-align: center; font-size: 30px;">¡Registro Continuo no conectado!   ¡Verificar que esté en red!</div>'
    msg_box.setText(texto)    
    # Configura el mensaje para que se mantenga sobre todas las ventanas
    msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
    
    # Redimensionar el QMessageBox para hacerlo más grande
    msg_box.resize(800, 400)  # Ajusta estos valores según el tamaño que prefieras

    # Mostrar el cuadro de mensaje
    msg_box.exec_()


from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor


def mensaje_lbl(Lbl_Mensajes, mensaje, borrar=False):
    """
    Escribe en Lbl_Mensajes (QTextEdit).
    - borrar=True: reemplaza el texto.
    - borrar=False: agrega el mensaje en la siguiente línea.
    """
    try:
        # Ajustes propios de QTextEdit
        Lbl_Mensajes.setAlignment(Qt.AlignLeft)                 # alineación horizontal
        Lbl_Mensajes.setLineWrapMode(QTextEdit.WidgetWidth)     # ajuste de línea por ancho

        texto_nuevo = "" if mensaje is None else str(mensaje)

        if borrar:
            # Reemplaza todo el contenido
            Lbl_Mensajes.setPlainText(texto_nuevo)
        else:
            # Agrega en la última línea (sin interpretar HTML)
            cursor = Lbl_Mensajes.textCursor()
            cursor.movePosition(QTextCursor.End)
            Lbl_Mensajes.setTextCursor(cursor)

            if Lbl_Mensajes.toPlainText():      # si ya hay texto, anteponer salto de línea
                Lbl_Mensajes.insertPlainText("\n")

            Lbl_Mensajes.insertPlainText(texto_nuevo)

        QCoreApplication.processEvents()
    except Exception:
        pass


class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):


    def __init__(self,parent=None):#Constructor de la clase
        super(MyApp,self).__init__(parent)
        QMainWindow.__init__(self) #Constructor
        #Carga la configuración del archivo .ui en el objeto
        ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src','ui',"automatico.ui"))
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui,self)
        self.setWindowTitle("PROCESAMIENTO SISMICO")
        self.btn_abrir.clicked.connect(self.Abrir_archivo)
        
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.dateEdit.dateChanged.connect(self.showDate)
        self.parametros=parametros_estaciones()#(nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal,componente_canal,grafico_)
        self.inicializar_()
        self.nombre_canal=self.parametros['CODIGO']
        self.n_canales=self.parametros['CANALES']
        self.hab_canal=self.parametros['HAB_CANAL']
        self.componente=self.parametros['COMPONENTE']
        self.grafico=self.parametros['HAB_GRAFICO']        
        self.hab_plt=self.parametros['HAB_GRAFICO']
        self.gan_plt=self.parametros['GANANCIA']
        self.diez_plt=self.parametros['DIEZMADO_PLT']
        self.bits_=self.parametros['FACTOR_MUL']
        now = datetime.now()
        fecha = QDate(now.year, now.month,now.day)
        directorio_trabajo=os.path.abspath(os.getcwd())
        aux=len(directorio_trabajo)
        self.directorio_trabajo=directorio_trabajo[0:aux-9]
        self.directorio_trabajo='G:/Mi unidad/DIA/'
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual
        self.dateEdit.setDate(d)
        self.dia=fecha.toString('yyMMdd')
        self.showDate(d)
        mensaje_lbl(self.Lbl_Mensajes,"AUTOMATICO:", False)
        if os.path.exists('R:'):
            self.bandera_drive_r=1
        else:
            mostrar_advertencia(self)
            #QMessageBox.information(self, 'Advertencia', '¡Registro Continuo no conectado!')
            self.bandera_drive_r=0

    def showDate(self, date):#Es como inicializar el dìa
        self.date=date
        self.dia=self.date.toString('yyyyMMdd')
        self.archivo=self.directorio_trabajo+self.dia+'000000'


    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath
        self.Lbl_Mensajes.setText(self.directorio_trabajo)
        self.showDate(self.date)

    def Abrir_archivo(self):
        lista_archivos=[]
        directorio_origen='R:'
        try:
            archivos_auxiliar = os.listdir(directorio_origen)
            archivos_filtrados = [f for f in archivos_auxiliar
                      if re.fullmatch(r'\d{6}(?:000000|235959)', Path(f).stem)
                      and Path(f).suffix == '']
            for archivo_copiar in archivos_filtrados:
                if archivo_copiar[0:6]==self.dia[2:]:        
                    arch_aux='20'+archivo_copiar
                    archivo_origen='R:/'+archivo_copiar#  archivo_origen="C:/DIA/"+archivo_copiar
                    archivo_destino=self.directorio_trabajo+'20'+archivo_copiar
                    if archivo_copiar[6:12]=="235959":
                        archivo_destino=self.directorio_trabajo+'20'+archivo_copiar[0:6]+"000000"#    archivo_destino="C:/DIA/"+archivo_copiar[0:6]+"000000"
                        arch_aux='20'+archivo_copiar[0:6]+"000000"
                    lista_archivos.append(arch_aux)
                    mensaje_lbl(self.Lbl_Mensajes,"Copiando archivos:\n "+archivo_origen+' en '+archivo_destino,True)
                    shutil.copy(archivo_origen,archivo_destino)

        except FileNotFoundError:
            auxiliar=self.dia+'000000'
            lista_archivos.append(auxiliar)
# Loop para cada parte binaria
        lista_archivos.sort()
        mensaje_lbl(self.Lbl_Mensajes,lista_archivos,False)
        
        for archivo_ in lista_archivos:
            self.inicializar_()
            self.archivo=self.directorio_trabajo+archivo_# self.archivo="C:/DIA/"+archivo_
            self.definir_dia()
            self.archivo_binario=self.directorio_trabajo+archivo_#   self.archivo_binario="C:/DIA/"
            if os.path.exists(self.archivo_binario):
                pass
            else:
                nombre_archivo=self.archivo_binario[-12:]
                self.archivo_binario, _ = QFileDialog.getOpenFileName(None, "Seleccionar archivo", "", f"{nombre_archivo} ({nombre_archivo})")
            #self.leer_bianrio()
            self.canal, huecos = Leer_binario_comun(
                self.directorio_trabajo,
                self.archivo_binario,
                self.progressBar,
                self.Lbl_Mensajes)
            
            mensaje_lbl(self, "Lectura terminada, \n Segundos faltantes "+str(huecos),True)
            self.Btn_Mseed()
#Unir Mseed
        for i in range(1,len(lista_archivos)):
            self.unir_mseed(lista_archivos[0],lista_archivos[i])

        if lista_archivos!=[]:
            self.archivo=self.directorio_trabajo+lista_archivos[0]
            self.fecha_=obtencion_hora(self.archivo)
            print(self.archivo)
            mensaje_lbl(self.Lbl_Mensajes,self.archivo,False)
            self.trCanal=leer_mseed(self.archivo,0)
            self.imprimir_png()
            print("Terminado:")
            mensaje_lbl(self.Lbl_Mensajes,"Terminado:",True)
        else:
            self.archivo=self.directorio_trabajo+self.dia+'000000'
            print("No hay registros para ese día..\nArchivo buscado: ", self.archivo)
            mensaje_lbl(self.Lbl_Mensajes,"No hay registros para ese día..\nArchivo buscado: "+ self.archivo,True)
 
    def inicializar_(self):
        self.canal_np = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]#canal_np
        self.trCanal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]] #trCanal
        self.linea = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] # linea Variable que permite restar el promedio del priemr segundo por canal y bajar el offset
        self.suma = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #Variable que permite restar el promedio del priemr segundo por canal y bajar el offset
        self.canal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]   # canal Variable  para la lectura desde el archivo binario

    def definir_dia(self):
        mensaje_lbl(self.Lbl_Mensajes,"Dia: "+self.archivo,True)
        print("Dia: "+self.archivo)
        self.directorios_=obtener_directorios(self.archivo)
        self.directorio=self.directorios_['Directorio_base']
        self.directorio_dia=self.directorios_['Directorio_dia']
        self.directorio_eventos=self.directorios_['Directorio_eventos']
        self.directorio_registros=self.directorios_['Directorio_registros']
        self.directorio_reportes=self.directorios_['Directorio_reportes']
        self.directorio_acel=self.directorios_['Directorio_acelerogramas']
        self.estaciones=self.directorios_['archivo_estaciones']
        self.archivo_analogico = self.directorios_['archivo_analogico']
        print(self.archivo_analogico)
        if not os.path.exists(self.archivo_analogico):
            escritura_archivo(self.archivo_analogico, [['Archivo','puntero','segundo_m','contador_s'], ['','0','00000','0']])

        
        
        self.fecha_=obtencion_hora(self.archivo) #En la variable fecha_, como tupla se tiene (año, mes, dia, hora , minuto, segundo, y valor ensegundos) y (strin¿gs respectivos)
        hora_string=self.fecha_.strftime('%Y%m%d_%H%M%S')
        if os.path.exists(self.estaciones):
            os.remove(self.estaciones)
        try:
            path = Path(self.directorio)
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        try:
            path = Path(self.directorio_dia)
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        try:
            path = Path(self.directorio_eventos)
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        try:
            path = Path(self.directorio_registros)
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        try:
            path = Path(self.directorio_reportes)
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        try:
            path = Path(self.directorio_acel)
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        try:
            path = Path(self.directorio+"/fastHypo")
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        mensaje=""
        hora_string=self.fecha_.strftime('%y%m%d_%H%M%S')
        contador=0
        for i in range(0,100):
            nombreMseed = self.directorio_registros+"/"+self.nombre_canal[i]+'_20'+hora_string+".mseed"
            try:

                auxiliar=open(nombreMseed,'r')
                auxiliar.close
                contador=contador+1
                mensaje=mensaje+self.nombre_canal[i]+"  "
                if contador==4:
                    mensaje=mensaje+"\n"
                    contador=0
            except FileNotFoundError:
                pass
        #input("Enter:")
        if len(mensaje)==0:
            mensaje="¡No hay archivos mseed!\n\nProceder a leer el \nregistro continuo\nSe procesarán solo\nlos resgistros analógicos"
        else:
            mensaje="Archivos encontrados:\n\n"+mensaje
        mensaje_lbl(mensaje,True)


    def Btn_Mseed(self):#Depurado  Aquì se genera las trazas de los mseed.
        self.canal_np = np.asarray(self.canal)
        self.Lbl_Mensajes.setText("Grabando Mseed... ")

        mensaje_lbl("Grabando Mseed... \n"+str(self.canal_np),False)
        estaciones_completo=lectura_archivo(self.estaciones)
        for i in range(0, 16):
            self.hab_canal[i]=estaciones_completo[i+1][1]
            self.nombre_canal[i]=estaciones_completo[i+1][2]
        self.trCanal=conversion_mseed(self.canal_np,self.hab_canal,self.nombre_canal,self.fecha_,self.directorio_registros)
        self.Lbl_Mensajes.setText("Grabación Mseed Terminada ")
        mensaje_lbl(self.Lbl_Mensajes,"Grabación Mseed Terminada ",False)



    def unir_mseed(self,archivo_1,archivo_2):#Depurado  Aquì se genera las trazas de los mseed.
        fecha_1=obtencion_hora(archivo_1)
        hora_string_1=fecha_1.strftime('%y%m%d_%H%M%S')
        fecha_1=obtencion_hora(archivo_2)
        hora_string_2=fecha_1.strftime('%y%m%d_%H%M%S')
        for i in range(0, 16):
            if self.hab_canal[i]!="0":
                nombreMseed_1 = self.directorio_registros+"/"+self.nombre_canal[i]+'_20'+hora_string_1+".mseed"
                st1 = obspy.read(nombreMseed_1)
                nombreMseed_2 = self.directorio_registros+"/"+self.nombre_canal[i]+'_20'+hora_string_2+".mseed"
                print("Uniendo archivo: "+nombreMseed_1+' y '+nombreMseed_2)
                mensaje_lbl(self.Lbl_Mensajes,"Uniendo archivo: "+nombreMseed_1+' y '+nombreMseed_2,True)
                st2 = obspy.read(nombreMseed_2)
                st1+=st2
                st1.merge(method=0,fill_value ='latest')
                st1.write(nombreMseed_1, format = 'MSEED', encoding = 'STEIM1', reclen = 512)
        
                try:
                    os.remove(nombreMseed_2)
                    mensaje_lbl(self.Lbl_Mensajes,f'Archivo "{nombreMseed_2}" borrado exitosamente.',False)
                    print(f'Archivo "{nombreMseed_2}" borrado exitosamente.')
                except FileNotFoundError:
                    mensaje_lbl(self.Lbl_Mensajes,f'Error: El archivo "{nombreMseed_2}" no existe.',False)
                    print(f'Error: El archivo "{nombreMseed_2}" no existe.')
                except PermissionError:
                    mensaje_lbl(self.Lbl_Mensajes,f'Error: Permiso denegado para borrar "{nombreMseed_2}".',False)
                    print(self.Lbl_Mensajes,f'Error: Permiso denegado para borrar "{nombreMseed_2}".')
                except Exception as e:
                    mensaje_lbl(self.Lbl_Mensajes,f'Ocurrió un error: {e}',False)
                    print(f'Ocurrió un error: {e}')
        mensaje_lbl(self.Lbl_Mensajes,"Archivos Unidos ",False)
        print("Archivos Unidos ")

    def imprimir_png(self):
        hora_string=self.fecha_.strftime('%Y%m%d_%H%M%S')
        mensaje_lbl(self.Lbl_Mensajes,'Imprimiendo PNGs: \n',True)
        for i in range(0,16):
            if self.hab_canal[i]=='1':
                nombrepng = self.nombre_canal[i]+"_"+hora_string+".png"
                mensaje_lbl(self.Lbl_Mensajes,'\n'+nombrepng,False)
                nombrepng = self.directorio+"/"+nombrepng
                self.trCanal[i].plot(type='dayplot',outfile=nombrepng,dpi=200,size=(2400,1800),linewidth=0.2,show=False)

    
    def Salir_(self):
        # Cierra la ventana principal (dispara closeEvent)
        self.close()
        # Por si hay diálogos abiertos (QMessageBox, etc.)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.closeAllWindows()

        
 
    def closeEvent(self, event):
        """Este método maneja el evento de cierre cuando se hace clic en la 'X'."""
        print("Cerrando la aplicación desde la ventana.")
        event.accept()  # Acepta el evento de cierre y cierra la ventana


if __name__ == '__main__': #Condicional que comprueba si ha sido ejecutado o importado
    # Crear la aplicación
    #print("Iniciando la aplicación...")  # Mensaje de depuración
    app = QtWidgets.QApplication(sys.argv)
    
    #print("Instanciando la ventana...")  # Mensaje de depuración
    # Crear la ventana principal
    window = MyApp()
    window.show()  # Mostrar la ventana
    
    #print("Ejecutando el ciclo de eventos...")  # Mensaje de depuración
    # Ejecutar el bucle de eventos
    app.exec_()

