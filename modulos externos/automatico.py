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
from PyQt5.QtCore import QDate
import shutil
import struct
import numpy as np
from pathlib import Path
from metodos_rsa import loc_cabecera,imprimir_plt,conversion_mseed,leer_mseed
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




def Leer_binario_comun(directorio_trabajo, archivo_binario):#Depurado
    #directorio_trabajo Directorio del ..\DIA\   
    #archivo_binario    Archivo binario para la lectura, puede ser registro continuo o un evento .sis
        canal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]   # canal Variable  para la lectura desde el archivo binario
        linea = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] # linea Variable que permite restar el promedio del priemr segundo por canal y bajar el offset
        suma = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #Variable que permite restar el promedio del priemr segundo por canal y bajar el offset
        directorios=obtener_directorios(archivo_binario)
        
        archivo_abrir = open(archivo_binario,'rb')
        numero_segundo,configuracion,puntero=loc_cabecera(archivo_abrir)  #return(numero_segundo,configuracion,puntero-20)
        with open(directorios['archivo_estaciones'], 'a', newline='') as archivo_estaciones:
            escritor_csv_ = csv.writer(archivo_estaciones,delimiter=';')
            for datos_estaciones in configuracion:
                escritor_csv_.writerow(datos_estaciones)                       
        puntero=puntero-5   #Hay que averuiguar órque se resta -5
        archivo_abrir.close()
        archivo_abrir = open(archivo_binario,'rb')
        cabecera=archivo_abrir.read(puntero)
        archivo_abrir.close()
        archivo_grabar=directorio_trabajo+"cabecera_sismo"
        with open(archivo_grabar, "wb") as archivo:
            archivo.write(cabecera)
        archivo_abrir = open(archivo_binario,'rb')
        bandera=1
        print("Lectura de registro continuo\n\n en ejecución")
        contador=0      #Número de segundos
        contador_m=0      #Número de minutos
        bandera_linea = 0 #bandera que permite que sea restado el promedio del primer segundo a todo el registro
        while bandera:
            cabecera_0=archivo_abrir.read(4)
            if len(cabecera_0) == 0:
                bandera=0
            if cabecera_0 == b'\x08\x00\x05\x00':
                numero_segundo=archivo_abrir.read(5)
                cabecera_1=archivo_abrir.read(20)
                if cabecera_1 == b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00':
                    puntero_a=archivo_abrir.tell()
                    #print(puntero_a)
                    cuerpo_=archivo_abrir.read(2048)
                    if len(cuerpo_)<2048:
                        bandera=0
                        break
                    archivo_abrir.seek(puntero_a)
                    contador=contador+1# Va sumando todos los segundos, en un dìa son 86400
                    contador_m=contador_m+1
                    if contador_m==3600:
                        contador_m=0
                    for k in range(0, 64):
                        for m in range(0,16):
                            dato=struct.unpack("<h", archivo_abrir.read(2))
                            canal[m].append(dato[0]-linea[m])
                            if bandera_linea:
                                suma[m]=suma[m]+dato[0]
                    if bandera_linea:
                        bandera_linea = 0
                        for m in range(0,16):
                            linea[m]=int(suma[m]/64)
        archivo_abrir.close()
        huecos=86400-contador
        print("Lectura terminada, \n Segundos faltantes "+str(huecos))
        return canal,huecos




class MessageThread(QThread):
    message_signal = pyqtSignal(str)
    def __init__(self, message, parent=None):
        super(MessageThread, self).__init__(parent)
        self.message = message
    def run(self):
        while True:
            self.message_signal.emit(self.message)
            time.sleep(5)

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
        self.btn_graficos.clicked.connect(self.Generar_)
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
        self.thread = MessageThread("Inicio del programa ", self)
        self.thread.message_signal.connect(self.set_message)
        self.thread.start()
        self.thread = MessageThread("Escojer un día", self)
        aux=len(directorio_trabajo)
        self.directorio_trabajo=directorio_trabajo[0:aux-9]
        self.directorio_trabajo='G:/Mi unidad/DIA/'
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual
        self.dateEdit.setDate(d)
        self.dia=fecha.toString('yyMMdd')
        self.showDate(d)
        if os.path.exists('R:'):
            self.bandera_drive_r=1
            
        else:
            mostrar_advertencia(self)
            #QMessageBox.information(self, 'Advertencia', '¡Registro Continuo no conectado!')
            self.bandera_drive_r=0

    def set_message(self, message):
        self.Lbl_Mensajes.setText(message)

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
                    print("Copiando archivos ",archivo_origen,archivo_destino)
                    shutil.copy(archivo_origen,archivo_destino)
                    self.Lbl_Mensajes.setText('Archivo copiado\n   '+archivo_copiar)
        except FileNotFoundError:
            auxiliar=self.dia+'000000'
            lista_archivos.append(auxiliar)
# Loop para cada parte binaria
        lista_archivos.sort()
        print(lista_archivos)
        
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
            self.canal,huecos=Leer_binario_comun(self.directorio_trabajo, self.archivo_binario)
            self.Lbl_Mensajes.setText("Lectura terminada, \n Segundos faltantes "+str(huecos))
            print("Lectura terminada, \n Segundos faltantes "+str(huecos))
            self.Btn_Mseed()
#Unir Mseed
        for i in range(1,len(lista_archivos)):
            self.unir_mseed(lista_archivos[0],lista_archivos[i])

        if lista_archivos!=[]:
            self.archivo=self.directorio_trabajo+lista_archivos[0]
            self.fecha_=obtencion_hora(self.archivo)
            print(self.archivo)
            self.trCanal=leer_mseed(self.archivo,0)
            #self.generar_plt()
            self.imprimir_png()
            print("Terminado:")
        else:
            self.archivo=self.directorio_trabajo+self.dia+'000000'
            print("No hay registros para ese día..\nArchivo buscado: ", self.archivo)
 
    def inicializar_(self):
        self.canal_np = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]#canal_np
        self.trCanal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]] #trCanal
        self.linea = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] # linea Variable que permite restar el promedio del priemr segundo por canal y bajar el offset
        self.suma = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #Variable que permite restar el promedio del priemr segundo por canal y bajar el offset
        self.canal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]   # canal Variable  para la lectura desde el archivo binario

    def definir_dia(self):
        print("Dia: ",self.archivo)
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
            #print(nombreMseed,"\n",self.directorio_registros,"\n",self.nombre_canal[i],"\n",hora_string)
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
        self.Lbl_Mensajes.setText(mensaje)
        print(mensaje)

    def Leer_binario(self):#Depurado
        archivo_abrir = open(self.archivo_binario,'rb')
        numero_segundo=loc_cabecera(archivo_abrir)  #return(numero_segundo,configuracion,puntero-20)
        with open(self.estaciones, 'a', newline='') as archivo_estaciones:
            escritor_csv_ = csv.writer(archivo_estaciones,delimiter=';')
            for datos_estaciones in numero_segundo[1]:
                escritor_csv_.writerow(datos_estaciones)                       
        puntero=numero_segundo[2]-5
        archivo_abrir.close()
        archivo_abrir = open(self.archivo_binario,'rb')
        cabecera=archivo_abrir.read(puntero)
        archivo_abrir.close()
        archivo_grabar=self.directorio_trabajo+"cabecera_sismo"
        print(archivo_grabar)
        with open(archivo_grabar, "wb") as archivo:
            archivo.write(cabecera)
        archivo_abrir = open(self.archivo_binario,'rb')
        bandera=1
        self.Lbl_Mensajes.setText("Lectura de registro continuo\n\n en ejecución")
        print("Lectura de registro continuo\n\n en ejecución")
        contador=0      #Número de segundos
        contador_m=0      #Número de minutos
        bandera_linea = 0 #bandera que permite que sea restado el promedio del primer segundo a todo el registro
        while bandera:
            cabecera_0=archivo_abrir.read(4)
            if len(cabecera_0) == 0:
                bandera=0
            if cabecera_0 == b'\x08\x00\x05\x00':
                numero_segundo=archivo_abrir.read(5)
                cabecera_1=archivo_abrir.read(20)
                if cabecera_1 == b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00':
                    puntero_a=archivo_abrir.tell()
                    #print(puntero_a)
                    cuerpo_=archivo_abrir.read(2048)
                    if len(cuerpo_)<2048:
                        bandera=0
                        break
                    archivo_abrir.seek(puntero_a)
                    contador=contador+1# Va sumando todos los segundos, en un dìa son 86400
                    contador_m=contador_m+1
                    if contador_m==3600:
                        contador_m=0
                    for k in range(0, 64):
                        for m in range(0,16):
                            dato=struct.unpack("<h", archivo_abrir.read(2))
                            self.canal[m].append(dato[0]-self.linea[m])
                            if bandera_linea:
                                self.suma[m]=self.suma[m]+dato[0]
                    if bandera_linea:
                        bandera_linea = 0
                        for m in range(0,16):
                            self.linea[m]=int(self.suma[m]/64)
        archivo_abrir.close()
        huecos=86400-contador
        self.Lbl_Mensajes.setText("Lectura terminada, \n Segundos faltantes "+str(huecos))
        print("Lectura terminada, \n Segundos faltantes "+str(huecos))

    def Btn_Mseed(self):#Depurado  Aquì se genera las trazas de los mseed.
        self.canal_np = np.asarray(self.canal)
        self.Lbl_Mensajes.setText("Grabando Mseed... ")
        print("Grabando Mseed... ")
        self.trCanal=conversion_mseed(self.canal_np,self.hab_canal,self.nombre_canal,self.fecha_,self.directorio_registros)
        self.Lbl_Mensajes.setText("Grabación Mseed Terminada ")
        print("Grabación Mseed Terminada ")


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
                print("Uniendo archivo: ",nombreMseed_1,nombreMseed_2)
                st2 = obspy.read(nombreMseed_2)
                st1+=st2
                st1.merge(method=0,fill_value ='latest')
                st1.write(nombreMseed_1, format = 'MSEED', encoding = 'STEIM1', reclen = 512)
        
                try:
                    os.remove(nombreMseed_2)
                    print(f'Archivo "{nombreMseed_2}" borrado exitosamente.')
                except FileNotFoundError:
                    print(f'Error: El archivo "{nombreMseed_2}" no existe.')
                except PermissionError:
                    print(f'Error: Permiso denegado para borrar "{nombreMseed_2}".')
                except Exception as e:
                    print(f'Ocurrió un error: {e}')
        self.Lbl_Mensajes.setText("Archivos Unidos ")
        print("Archivos Unidos ")


    def Generar_(self):
        self.definir_dia()
        self.fecha_=obtencion_hora(self.archivo)
        print(self.archivo)
        self.trCanal=leer_mseed(self.archivo,0)
        #self.generar_plt()
        self.imprimir_png()
        print("Terminado")
        pass


    def generar_plt(self):
        hora_string=self.fecha_.strftime('%Y%m%d_%H%M%S')
        print(self.trCanal)
        for i in range(0,16):
            if self.hab_plt[i]=='1':
                nombreplt=self.directorio_trabajo+self.nombre_canal[i]+'_'+hora_string+".plt"
                self.Lbl_Mensajes.setText("Graficando datos...\n" + nombreplt)
                print("Graficando datos...\n" + nombreplt)
                archivo_plt=open(nombreplt,'w')
                print(self.trCanal[i],"\n",self.n_canales[i])
                if self.n_canales[i]=='1':
                    trCanal_1=self.trCanal[i][0]
                    imprimir_plt(archivo_plt,trCanal_1,int(self.gan_plt[i]),int(self.diez_plt[i]),int(self.bits_[i])) #metodo imprimir_plt(archivo,trCanal1,ganancia),archivo es donde se va almacenar, trCanal es la traza mseed y la ganancia es eso.
                if self.n_canales[i]=='3':
                    trCanal_1=self.trCanal[i][0]
                    imprimir_plt(archivo_plt,trCanal_1,int(self.gan_plt[i]),int(self.diez_plt[i]),int(self.bits_[i])) #metodo imprimir_plt(archivo,trCanal1,ganancia),archivo es donde se va almacenar, trCanal es la traza mseed y la ganancia es eso.
                archivo_plt.close

    def imprimir_png(self):
        hora_string=self.fecha_.strftime('%Y%m%d_%H%M%S')
        for i in range(0,16):
            if self.hab_canal[i]=='1':
                nombrepng = self.nombre_canal[i]+"_"+hora_string+".png"
                self.Lbl_Mensajes.setText('Imprimiendo \n'+nombrepng)
                print('Imprimiendo \n'+nombrepng)
                nombrepng = self.directorio+"/"+nombrepng
                self.trCanal[i].plot(type='dayplot',outfile=nombrepng,dpi=200,size=(2400,1800),linewidth=0.2)

    
    def Salir_(self):
            
        sys.stdout.flush()  # Si deseas asegurarte de que los buffers de salida se vacíen
        os._exit(0)  # Fuerza la salida inmediata del programa


        #QApplication.quit()  # Termina la aplicación de forma segura
        #self.close()  # Cierra la ventana principal

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

