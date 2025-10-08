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

def Leer_binario_comun(directorio_trabajo, archivo_binario, barra_progreso,Lbl_Mensajes):

    """
    Lee un binario (registro continuo o evento .sis) con 16 canales a 64 sps, int16 LE.
    Muestra e incorpora los 5 caracteres (bytes) de 'numero_segundo' en el flujo de lectura.
    """

    bytes_por_segundo = 2075  # Diferencia entre marcas observada (1176 → 3251)

    # ------------------- Estructuras de almacenamiento ------------------- #
    canal = [[] for _ in range(16)]
    linea = [0]*16
    suma  = [0]*16
    segundos_leidos = []  # Lista para registrar los 5 bytes de cada segundo

    # ------------------- Lectura de cabecera ----------------------------- #
    directorios = obtener_directorios(archivo_binario)
    archivo_analogico=os.path.join(directorio_trabajo,"analogico.csv")
    referencias=[]
    contador_segundos=0
    referencias.append(['Archivo', 'puntero','segundo_m','contador_s'])
    if os.path.exists(archivo_analogico):
        referencias=lectura_archivo(archivo_analogico)
        if referencias[1][0]!=archivo_binario:
            referencias[1]=[archivo_binario,'0','00000',str(contador_segundos)]
            escritura_archivo(archivo_analogico,referencias)
    else:
        referencias.append([archivo_binario,'0','00000',str(contador_segundos)])
        escritura_archivo(archivo_analogico,referencias)
    f = open(archivo_binario, 'rb')
    
    numero_segundo, configuracion, puntero = loc_cabecera(f)
    texto_segundo = str(numero_segundo)
    print(referencias,texto_segundo)
    with open(directorios['archivo_estaciones'], 'a', newline='') as archivo_estaciones:
        escritor_csv_ = csv.writer(archivo_estaciones, delimiter=';')
        for fila in configuracion:
            escritor_csv_.writerow(fila)
    puntero = puntero - 5
    f.seek(0)
    cabecera = f.read(puntero)
    ruta_cabecera = os.path.join(directorio_trabajo, "cabecera_sismo")
    with open(ruta_cabecera, "wb") as fout:
        fout.write(cabecera)
    # ------------------- Estimación de segundos -------------------------- #
    tamano_archivo = os.path.getsize(archivo_binario)
    segundos_estimados = (max(0, (tamano_archivo - max(0, puntero))) // bytes_por_segundo)-int(referencias[1][3])
    
    mensaje_lbl(Lbl_Mensajes, f"Segundos estimados: {segundos_estimados}",True)
 
    if barra_progreso is not None:
        barra_progreso.setRange(0, int(segundos_estimados))
        barra_progreso.setValue(0)
        QCoreApplication.processEvents()
    puntero=int(referencias[1][1])
    contador_segundos=int(referencias[1][3])
    f.seek(puntero-4) #Es el inicio del segundo menos 4 por el formato de datos b'\x08\x00\x05\x00'
    contador = 0
    contador_m = 0
    bandera_linea = 1
    bandera_colgado=0
    mensaje_lbl(Lbl_Mensajes, "Leyendo archivo binario",False)
    try:
        while True:
            
            puntero_marcas=f.tell()
            cabecera_0 = f.read(4)
            if len(cabecera_0) == 0:
                break
            if cabecera_0 == b'\x08\x00\x05\x00':
                numero_segundo = f.read(5)      # <<< 5 bytes del número de segundo
                texto_segundo = numero_segundo.decode('ascii', errors='ignore')
                segundos_leidos.append(numero_segundo)  # Guardamos los 5 bytes
                cabecera_1 = f.read(20)
                if cabecera_1 == b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00':
                    puntero_a = f.tell()
                    cuerpo_ = f.read(2048)
                    if len(cuerpo_) < 2048:
                        break
                    f.seek(puntero_a)
                    contador += 1
                    contador_m += 1
                    if contador_m == 3600:
                        contador_m = 0
                    # Procesamiento de los 16 canales × 64 muestras
                    for k in range(64):
                        for m in range(16):
                            dato = struct.unpack("<h", f.read(2))[0]
                            if bandera_linea:
                                suma[m] += dato
                                canal[m].append(dato)
                            else:
                                canal[m].append(dato - linea[m])
                    # Corrección del primer segundo (offset DC)
                    if bandera_linea:
                        for m in range(16):
                            linea[m] = int(suma[m]/64)
                            inicio = len(canal[m]) - 64
                            for i in range(inicio, inicio + 64):
                                canal[m][i] -= linea[m]
                        bandera_linea = 0
                    if barra_progreso is not None:
                        barra_progreso.setValue(min(contador, int(segundos_estimados)))
                        QCoreApplication.processEvents()
                    contador_segundos=contador_segundos+1
                else:
                    continue
            else:
                
                if bandera_colgado==0:
                    
                    bandera_colgado=1
                    for ii in range(0,2048):
                        
                        f.seek(puntero_marcas+ii)
                        cabecera_0 = f.read(4)
                        if cabecera_0 == b'\x08\x00\x05\x00':
                                puntero_marcas=puntero_marcas+ii
                                bandera_colgado=0
                          
                continue
            
        referencias[1]=[archivo_binario,str(puntero_marcas),texto_segundo,str(contador_segundos)]
        escritura_archivo(archivo_analogico,referencias)
    finally:
        f.close()

    # ------------------- Finalización ------------------------------------ #
    huecos = 86400 - contador
    mensaje_lbl(Lbl_Mensajes, f"Lectura terminada,\nSegundos leídos: {contador}\nSegundos faltantes: {huecos}",True)
    barra_progreso.setValue(min(contador, int(segundos_estimados)))
    QCoreApplication.processEvents()

    # ------------------- Retorno ---------------------------------------- #
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

