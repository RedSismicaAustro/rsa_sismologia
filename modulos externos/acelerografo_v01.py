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


fecha_=0
t_inicio=0
t_final=0
from metodos_rsa import imprimir_plt,obtenerTraza,lectura_archivo,escritura_archivo
from metodos_gestion import parametros_estaciones,obtener_directorios
import obspy
import pathlib
from pathlib import Path
import os 
import sys
from PyQt5 import uic, QtWidgets#Importamos módulo uic y Qtwidgets
import matplotlib.pyplot as plt

import time
import struct
import numpy as np

from obspy import UTCDateTime, read, Trace, Stream
from matplotlib.ticker import MultipleLocator
import csv
from scipy import signal    
from PyQt5.QtWidgets import (QWidget,QApplication,QMainWindow,QMessageBox,QDialog,QFileDialog,QLabel,QCheckBox,QLineEdit,QSpinBox,QPushButton,QVBoxLayout)
import os,sys
from datetime import datetime
from PyQt5.QtCore import QDate




# Cargar la interfaz desde el archivo .ui directamente en esta instancia
ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", "acelerografos.ui")
ruta_ui = os.path.abspath(ruta_ui)


qtCreatorFile=ruta_ui# Nuestro archivo UI aquí.
Ui_MainWindow,QtBassClass=uic.loadUiType(qtCreatorFile)#El modulo ui carga




# Metodo para obtener una traza a partir de los datos
# Recibe los atributos que van en la cabecera del archivo miniSeed
# nombreRed: Codigo de la red que debe ser maximo 2 bytes
# nombreEstacion: Codigo de la estacion que debe ser maximo 5 bytes
# localizacion: Identificador de localizacion maximo 2 bytes
# nombreCanal: Identificador de canal maximo 3 bytes
# data: datos como enteros en un array numpy
# fsample: Frecuencia de muestreo
# calidad: Indicador de calidad de datos, 'D', 'R' o 'Q', D es calidad indeterminada
# Tiempo de inicio en el orden: anio, mes, dia, horas, minuto210618000000210618000000s, segundos, microsegundos


def nombre_mseed(nombre_,fecha_):
    anio_s=fecha_[1][0]
    mes_s=fecha_[1][1]
    dia_s=fecha_[1][2]
    hora_s=fecha_[1][3]
    minuto_s=fecha_[1][4]
    segundo_s=fecha_[1][5]
    fecha_string=anio_s+mes_s+dia_s        
    hora_string=hora_s+minuto_s+segundo_s
    fileName = nombre_+fecha_string+"_"+hora_string+".mseed" 
    return fileName
    

def conversion_mseed_digital(self,fileName,fecha_,data_np):
    # Nombre del archivo en funcion del tiempo de inicio
    anio=fecha_[0][0]
    mes=fecha_[0][1]
    dia=fecha_[0][2]
    horas=fecha_[0][3]
    minutos=fecha_[0][4]
    segundos=fecha_[0][5]
    nombre_=self.datos_estacion[2]
    # Una vez que se tiene los datos, llama al metodo para obtener la traza
    # Todos los parametros que recibe se detallan en el metodo (mas abajo)
    trazaCH1 = obtenerTraza(nombre_,1, data_np[0],(2000 + anio), mes, dia, horas, minutos, segundos, 0)
    trazaCH2 = obtenerTraza(nombre_,2, data_np[1],(2000 + anio), mes, dia, horas, minutos, segundos, 0)        
    trazaCH3 = obtenerTraza(nombre_,3, data_np[2],(2000 + anio), mes, dia, horas, minutos, segundos, 0)
    # Si se desea varias trazas, esto seria para cuando se tiene 3 canales
    stData = Stream(traces=[trazaCH1, trazaCH2, trazaCH3])
    # Guarda todas las trazas en un archivo en formato miniseed con codificacion
    # STEIM1 para disminuir el tamaño del archivo

    stData.write(fileName, format = 'MSEED', encoding = 'STEIM1', reclen = 512)
    
def verificacion_archivo(self,archivo):
#Metodo de verificación del archivo binario, donde se obtiene el tiempo de inicio para la construccion del mseed
    f = open(archivo, "rb")
    tramaDatos = np.fromfile(f, np.int8, 2506)
    hora = tramaDatos[2503]
    minuto = tramaDatos[2504]
    segundo = tramaDatos[2505]
    n_segundo=hora*3600+minuto*60+segundo
    anio=tramaDatos[2500]
    anio_s= str(anio)
    mes=tramaDatos[2501]
    mes_s=str(mes)
    if(mes<10):
        mes_s='0'+mes_s
    dia=tramaDatos[2502]
    dia_s=str(dia)
    if(dia<10):
        dia_s='0'+dia_s
    hora_s=str(hora)
    if(hora<10):
        hora_s='0'+hora_s
    minuto_s=str(minuto)
    if(minuto<10):
        minuto_s='0'+minuto_s
    segundo_s=str(segundo)
    if(segundo<10):
        segundo_s='0'+segundo_s
    fecha_=(anio,mes,dia,hora,minuto,segundo,n_segundo),(anio_s,mes_s,dia_s,hora_s,minuto_s,segundo_s)
    f.close
    return(fecha_)
    

def lectura_archivo_digital(self,archivo): #Depurado
    datos=[[],[],[]]
    bandera =1
    contador=0
    avance=0
    #numpy.fromfile(file, dtype=float, count=- 1, sep='', offset=0, *, like=None)
                  #file: Path a archivo a abrir
                  #dtype: Tipo de dato: 
                  #count: int, nùmero de datos a leer (-1 implica el archivo entero)
                  # sep: str. Separador entre elementos si el archivo es un archivo de texto. 
                        # El separador vacío (“”) significa que el archivo debe tratarse como binario. 
                        # Los espacios ("") en el separador coinciden con cero o más caracteres de espacio
                        # en blanco. Un separador que consta solo de espacios debe coincidir con al menos un espacio en blanco.
                  #offset:int es el nùmero de datos offset ( a ser no leidos) por defecot es 0
                  #like: tipo de arreglo.
    f = open(archivo, "rb")
    while bandera:
        tramaDatos = np.fromfile(f, np.int8, 2506)
        contador=contador+1
        if(len(tramaDatos)==2506):
            hora = tramaDatos[2503]
            minuto = tramaDatos[2504]
            segundo = tramaDatos[2505]
            n_segundo=hora*3600+minuto*60+segundo
        else:
            bandera=0
            break
        if(contador==864):
            contador=0
            avance=avance+1
            print(avance,'%')
            self.Lbl_Mensajes.setText('avance'+str(avance)+" %")
        for j in range(0,3):
            for i in range(0,250):
                dato_1=tramaDatos[i*10+j*3+1]
                dato_2=tramaDatos[i*10+j*3+2]
                dato_3=tramaDatos[i*10+j*3+3]
                xValue = ((dato_1 << 12) & 0xFF000) + ((dato_2 << 4) & 0xFF0) + ((dato_3 >> 4) & 0xF)
                if (xValue  >= 0x80000):
                    xValue  = xValue & 0x7FFFF  #Se descarta el bit 20 que indica el signo (1=negativo)
                    xValue = -1 * (((~xValue) + 1) & 0x7FFFF)
                datos[j].append(int(xValue))
    f.close
    datos_np = np.asarray(datos)        
    return (datos_np)  

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):#Constructor de la clase
        QtWidgets.QMainWindow.__init__(self)#Constructor
        Ui_MainWindow.__init__(self)#Constructor
        self.setWindowTitle("PROCESAMIENTO SISMICO")
        self.setupUi(self)# Método Constructor de la ventana
        self.Btn_Iniciar.clicked.connect(self.Iniciar)
        self.Btn_unir.clicked.connect(self.Unir_archivo)
        self.Btn_graficar.clicked.connect(self.Graficar_archivo)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual
        self.dateEdit.setDate(d)    #Conficuración de los datos de fecha en el DataEdit
        self.dateEdit.dateChanged.connect(self.showDate)
        self.directorio_trabajo='G:\Mi unidad\DIA\\'
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.directorio_binario=self.directorio_trabajo+"Datos Estaciones/"
        self.Lbl_directorio_2.setText(self.directorio_binario)
        self.showDate(d)
        self.definir_dia()
        archivo=os.path.join(ruta_proyecto,'datos',"digitales.csv")
        self.est_digitales_=lectura_archivo(archivo)
        self.estaciones_=parametros_estaciones()
        self.estacion_habilitada=self.estaciones_['HAB_CANAL']
        self.plt_habilitado=self.estaciones_['HAB_PLT']
        self.nombre_estacion=self.estaciones_['NOMBRE']
        self.codigo_estacion=self.estaciones_['CODIGO']
        self.ganancia=list(map(float, self.estaciones_['GAN_PLT']))#Transforma al tipo de variable dada por el primer argumento la lista del segundo argumento.
        self.diezmado=list(map(int, self.estaciones_['DIEZMADO_PLT']))
        self.factor_mult=list(map(float, self.estaciones_['FACTOR_MUL']))
        self.canal_=list(map(int, self.estaciones_['COMPONENTE']))

    def seleccionar_drive(self):#Selecciona la ubicación del directorio /dia/ para grabar la información
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.directorio_binario=self.directorio_trabajo+"Datos Estaciones/"
        if os.path.exists(self.directorio_binario):
            pass
        else:
            folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'SELECCIONAR DIRECTORIO _DATOS ESTACIONES_')
            if folderpath[-1]=='/':
                folderpath=folderpath
            else:
                folderpath=folderpath+'/'
            self.directorio_binario=folderpath
        self.Lbl_directorio_2.setText(self.directorio_binario)

    def Iniciar(self):
        self.definir_dia()
        
        dir_aux = os.listdir(self.directorio_binario) #Obtiene todos los archivos en el directorio de ubicación de los binarios.

        for estacion_digital in self.est_digitales_: #Busqueda desde todas las estaciones digitales.
            
            if estacion_digital[2]=='0' or estacion_digital[2]=='Habilitado':#Solo trabaja con las estaciones habilitadas.
                continue
            numero_estacion=int(estacion_digital[1])
            

            if self.estacion_habilitada[numero_estacion]!='1':
                print("Estacion ", self.nombre_estacion[numero_estacion],", ",self.codigo_estacion[numero_estacion]," no habilitada" )
                continue
            else:
                print("Estacion ", self.nombre_estacion[numero_estacion],", ",self.codigo_estacion[numero_estacion],"  habilitada" )
            print("Procesando ", estacion_digital[0])
            bandera=1
            if estacion_digital[0] in dir_aux: #Está la estación digital el rirectorio de ubicación (Están en subdirectorios con elnombre "digital" de las estaciones)
                arch_aux = os.listdir(self.directorio_binario+estacion_digital[0])#Carga todos los archivos en el subdirecrorio de la estación especificada

                #self.lista_archivos_dat=[]
                self.lista_archivos_mseed=[]
                dia_=self.archivo[-12:-6]#Especifica el día (en el directorio están todos los archivos binarios de muchos días)

#################Busca en todos los archivos binarios de la estacion digital
                for arch_ in arch_aux:
                    if estacion_digital[0]!='OBSID':
                        if arch_[7:13]==dia_:
                            self.lista_archivos_mseed.append(self.directorio_binario+estacion_digital[0]+'/'+arch_)
                    else:
                        if(arch_[2:])==dia_:###########
                            directorio_mseed=self.directorio_binario+estacion_digital[0]+'/20'+arch_[2:]
                            XXX_ = os.listdir(directorio_mseed)
                            arch_aux_obsid=sorted(XXX_)
                            lista_canal=('EHN','EHE','EHZ')
                            lista_=[[],[],[]]
                            for arch_obsid in arch_aux_obsid:
                                if arch_obsid[8:11] in lista_canal:
                                    indice = lista_canal.index(arch_obsid[8:11])
                                    lista_[indice].append(arch_obsid)
                            st=Stream()
                            for i in range(0,len(lista_[0])):
                                stream_resultante=Stream()
                                for j in range(0,3):
                                    archivo_0=read(directorio_mseed+'/'+lista_[j][i])
                                    stream_resultante.append(archivo_0[0])
                                st=st+stream_resultante
                                st.merge(method=0,fill_value ='latest')
                            nombre_= self.directorio_binario+estacion_digital[0]+'/OBSD_20'+dia_+'_000000.mseed'
                            st.write(nombre_, format = 'MSEED', encoding = 'STEIM1', reclen = 512)
                            self.lista_archivos_mseed.append(nombre_)

            else:
                bandera=0
            if self.lista_archivos_mseed==[]:
                bandera=0
            if bandera:
                print("Terminación de conversión.\nSe procedrá a unir los archivos")

                archivos_unir = sorted(self.lista_archivos_mseed)
                
                archivo_unido=self.directorio_registros+'/'+archivos_unir[0][-26:-12]+"000000.mseed"
                if os.path.exists(archivo_unido):
                    os.remove(archivo_unido)
                for i in range(0,len(archivos_unir)):
                    if archivo_unido!=archivos_unir[i]:
                        archivo_unido=self.unir_mseed(archivo_unido,archivos_unir[i])
                ganancia=self.ganancia[numero_estacion]
                diezmado=self.diezmado[numero_estacion]
                factor_mult=self.factor_mult[numero_estacion]
                canal_=self.canal_[numero_estacion]
                print("Ganancia: ",ganancia,"  Diezmado: ",diezmado,"  factor_mult_: ",factor_mult,"  Canal: ",canal_)
                canal_=canal_-1
                trCanal_1 = obspy.read(archivo_unido)
                #archivo_plt=self.directorio_trabajo+archivo_unido[-27:-22]+'_'+archivo_unido[-19:-6]+".plt"
                #archivo_plt=open(archivo_plt,'w')
                #if self.plt_habilitado[numero_estacion]=='1':
                    #imprimir_plt(archivo_plt,trCanal_1[canal_],ganancia,diezmado,factor_mult)
                    #archivo_plt.close
                nombrepng = self.directorio+"/"+archivo_unido[-26:-5]+".png"
                trCanal_1[canal_].plot(type='dayplot',outfile=nombrepng,dpi=200,size=(2400,1800),linewidth=0.2)
            else:
                  print("Estacion ",estacion_digital[0]," no tiene registros para este día.")
                
        print("¡¡Estaciones digitales Terminadas!!")
        
    def showDate(self, date):#Es como inicializar el dìa
        self.date=date
        self.archivo=self.directorio_trabajo+date.toString('yyMMdd000000')


    def Abrir_archivo(self):  #Depurado
        self.archivo=self.directorio_trabajo+self.archivo_binario[-17:-11]+'000000' 
        self.definir_dia()
        if os.path.exists(self.archivo_binario):

            #aux=len(self.archivo_binario)
            nombre_= self.directorio_binario+self.datos_estacion[2]+'_20'  #nombre_= self.directorio_registros+self.archivo_binario[aux-23:aux-20]+self.archivo_binario[aux-19]+'_20'
            fecha_=verificacion_archivo(self, self.archivo_binario)
            n_mseed=nombre_mseed(nombre_,fecha_)
            self.lista_archivos_mseed.append(n_mseed)
            aux_mseed=n_mseed[-26:len(n_mseed)]
            arch_mseed = os.listdir(self.directorio_registros)
            if aux_mseed in arch_mseed:
                pass
            else:
                self.Lbl_Mensajes.setText(self.archivo_binario)
                datos_np=lectura_archivo_digital(self, self.archivo_binario)
                self.Lbl_Mensajes.setText(n_mseed)
                conversion_mseed_digital(self,n_mseed,fecha_,datos_np)
        else:
            QMessageBox.information(self,self.tr("Advertencia"),self.tr("Archivo no encontrado"))    
        
    def unir_mseed(self,archivo_1,archivo_2):
        print("Uniendo ",archivo_1," y ",archivo_2)
        if os.path.exists(archivo_1):
            st1 = obspy.read(archivo_1)
        else:
            st1 = obspy.read(archivo_2)
        st2 = obspy.read(archivo_2)
        st1+=st2
        st1.merge(method=0,fill_value ='latest')
        st1.write(archivo_1, format = 'MSEED', encoding = 'STEIM1', reclen = 512)
        return archivo_1

    def Unir_archivo(self):
        archivo__ = QFileDialog.getOpenFileName(
            parent=self,
            caption='Archivo 1:',
            directory=os.getcwd(),
        )
        archivo_1=archivo__[0]
        archivo__ = QFileDialog.getOpenFileName(
            parent=self,
            caption='Archivo 1:',
            directory=os.getcwd(),
        )
        archivo_2=archivo__[0]
        st1 = obspy.read(archivo_1)
        st2 = obspy.read(archivo_2)
        st1[0]+=st2[0]
        st1[1]+=st2[1]
        st1[2]+=st2[2]
        st1.merge(method=1,fill_value ='latest')
        st1[0].data=st1[0].data.filled()
        st1[1].data=st1[1].data.filled()
        st1[2].data=st1[2].data.filled()
        st1.write('Prueba.mseed', format = 'MSEED', encoding = 'STEIM1', reclen = 512)

    def Graficar_archivo(self):
        archivo__ = QFileDialog.getOpenFileName(
            parent=self,
            caption='Archivo 1:',
            directory=os.getcwd(),
        )
        archivo_1=archivo__[0]

        st1 = obspy.read(archivo_1)
        st1.plot()
        input()
        return

    def definir_dia(self):
        self.directorios_=obtener_directorios(self.archivo)
        self.directorio=self.directorios_['Directorio_base']
        self.directorio_dia=self.directorios_['Directorio_dia']
        self.directorio_registros=self.directorios_['Directorio_registros']
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
            path = Path(self.directorio_registros)
            path.mkdir(parents=True)
        except FileExistsError:
            pass

if __name__ == '__main__': #Condicional que comprueba si ha sido ejecutado o importado
    app = QtWidgets.QApplication(sys.argv)#Creamos app y le pasamos una lista de argumentos vacíos
    #Borramos todo el resto del código y ahora vamos a instanciar nuestra clase MainWindow:
    window = MyApp()
    window.show()#Muestra la ventana:
    app.exec_() #Usamos app.exec_() para crear el bucle de ejecución







