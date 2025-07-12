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

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from metodos_rsa import leer_mseed,grafico_evento_int,calidad_estacion,cargar_evento,cargar_dia
from metodos_rsa import insertar_evento_otras_redes,Guardar_dia
from metodos_graficos_rsa import reporte_resumen
from metodos_gestion import parametros_estaciones,obtener_directorios
from metodos_reportes_individuales import generar_reporte_sismo,generar_reporte_acelerograma
import csv
import matplotlib.pyplot as plt
import numpy as np
from PyQt5 import uic, QtWidgets,QtCore#Importamos módulo uic y Qtwidgets
from PyQt5.QtWidgets import (QMainWindow,QMessageBox,QDialog,QFileDialog,QLabel,QCheckBox,QComboBox,QLineEdit,QSpinBox,QPushButton)
from datetime import datetime 
from PyQt5.QtCore import QDate
import xml.etree.ElementTree as ET




#qtCreatorFile="reporte.ui"# Nuestro archivo UI aquí.
#Ui_MainWindow,QtBassClass=uic.loadUiType(qtCreatorFile)#El modulo ui carga
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

def filtro_evento(stLeido,freqmin_,freqmax_,grado_,t_inicio,t_final,estaciones_eventos,hab_grafico,bandera_marcas,pagina):
    #parametros=(nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
    #stLeido es l atraza donde se encuetra el Mseed de la estaciòn
    #tiempo_s es la referencia de tiempo, +7m -7m para el despliegue
    #freqmin_frecuencia minima del filtro a implementar.  
    #freqmax_frecuencia màxima del filtro a implementar. 
    #grado_ grado del filtro a implementar.
    #(nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
    num_canal=len(estaciones_eventos)
    for i in range(0, num_canal):
        canal_= estaciones_eventos[i]
        stLeido[canal_].filter("bandpass",freqmin=freqmin_,freqmax=freqmax_,corners=grado_)
    aux=t_final-t_inicio
    plt.close()
    grafico_evento_int(stLeido,0,aux,estaciones_eventos,hab_grafico,bandera_marcas,pagina)

class MyApp(QMainWindow):
    def __init__(self,parent=None):#Constructor de la clase
        super(MyApp,self).__init__(parent)
        QMainWindow.__init__(self)
        #Carga la configuración del archivo .ui en el objeto

        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", 'reporte.ui')
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        #QtWidgets.QMainWindow.__init__(self)#Constructor
        #Ui_MainWindow.__init__(self)#Constructor
        self.visor = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.visor)

        self.eventos_reporte=[[0,"Fecha; Hora (UTC)","Evento","Magn.","Prof.(km)","Lat.","Long.","Ubicación"]]
        self.catalogo=[["Id","año","mes","día","hora","min","seg","lat","long","prof","rms","e-x","e-y","e-0","e-z","Mag","Tipo Mag","Fuente","ruta","Ubicación"]]
        self.eventos=[]
        self.evento_canales=[]
        #self.setupUi(self)# Método Constructor de la ventana
        self.Btn_abrir.clicked.connect(self.Abrir_archivo)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_guardar.clicked.connect(self.Guardar_)
        self.Btn_modificar.clicked.connect(self.Modificar_)
        self.Btn_acelerograma.clicked.connect(self.Acelerograma_) 
        self.Btn_generar.clicked.connect(self.Generar_reporte_sismo)
        self.Btn_insertar.clicked.connect(self.Insertar_evento)
        self.Btn_graficar.clicked.connect(self.Graficar_)
        self.Btn_estacion.clicked.connect(self.estacion_calidad)
        self.Btn_limpiar.clicked.connect(self.reiniciar_evento)
        self.Btn_pagina.clicked.connect(self.cambio_pagina)
        self.Btn_filtrar.clicked.connect(self.filtrar_evento)
        self.cmbx_evento_escogido.currentIndexChanged.connect(self.Cargar_evento)
        lista_filtros = [" ","Ruido", "FF", "FC","TELESISMO","SISMO","INDEFINIDO","Evento_local",'CONTROL']
        self.cmbx_evento.addItems(lista_filtros)
        lista_filtros = [" ","IGEPN", "USGS", "Otras redes"]
        self.cmbx_red.addItems(lista_filtros)
        lista_filtros = [" ","M", "MLv", "Md","Mc","Mw","Mb"]
        self.cmbx_tipo_mag.addItems(lista_filtros)       
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual
        self.calendarWidget.clicked[QtCore.QDate].connect(self.showDate)
        self.directorio_trabajo='G:\Mi unidad\DIA\\'#self.directorio_trabajo=dir_trabajo[0:aux-9]
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.parametros=parametros_estaciones()#(nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
        self.numero_canal_=self.parametros['NUM_ESTACION']
        self.nombre_canal_total_=self.parametros['NOMBRE']
        self.nombre_canal=self.parametros['CODIGO']
        self.tipo_canal_=self.parametros['SENSOR']
        self.n_canales_=self.parametros['CANALES']
        self.hab_canal=self.parametros['HAB_CANAL']
        self.hab_grafico=self.parametros['HAB_GRAFICO']
        self.pagina=0
        self.estaciones_eventos=[]

    def reiniciar_estado_dia(self):
        """
        Reinicia todas las variables internas relacionadas con el procesamiento del día,
        manteniendo únicamente el directorio de trabajo. No modifica el estado visual de la interfaz.
        """
        self.eventos_reporte = [["0", "Fecha; Hora (UTC)", "Evento", "Magn.", "Prof.(km)", "Lat.", "Long.", "Ubicación"]]
        self.catalogo = [["Id", "año", "mes", "día", "hora", "min", "seg", "lat", "long", "prof", "rms", "e-x", "e-y", "e-0", "e-z", "Mag", "Tipo Mag", "Fuente", "ruta", "Ubicación"]]
        self.eventos = []
        self.vector = []
        self.evento_canales = []
        self.indice = 0
        self.pagina = 0
        self.archivo = ""
        self.archivo_escogido = ""
        self.archivo_reporte = ""
        self.root = None
        self.resumen = None
        self.responsables = None
        self.estaciones_eventos = []
        self.trCanal = [[] for _ in range(100)]

        
    def closeEvent(self, event):
        print("Cerrando programa")


    def iniciar_variables(self):
        self.eventos_reporte=[['0',"Fecha; Hora (UTC)","Evento","Magn.","Prof.(km)","Lat.","Long.","Ubicación"]]
        self.catalogo=[["Id","año","mes","día","hora","min","seg","lat","long","prof","rms","e-x","e-y","e-0","e-z","Mag","Tipo Mag","Fuente","ruta","Ubicación"]]
        self.eventos=[]
        self.vector=[]
        self.evento_canales=[]
        self.Btn_graficar.setEnabled(False)
        self.Btn_pagina.setEnabled(False)
        self.cmbx_evento.setEnabled(False)
        self.Btn_modificar.setEnabled(False)
        self.Btn_acelerograma.setEnabled(False)
        self.cmbx_evento_escogido.clear()
        self.indice=0

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath
        self.Lbl_directorio.setText(self.directorio_trabajo)


    def showDate(self, date):
        print("Cambio de dia")
        self.reiniciar_estado_dia()
        self.bandera_evento=1
        self.date=date
        self.fecha_ini=date
        self.archivo=self.directorio_trabajo+date.toString('yyyyMMdd000000')
        self.directorios=obtener_directorios(self.archivo)#return(directorio,directorio_dia,directorio_eventos,directorio_registros)
        self.dia_reporte='      del '+date.toString('d')+' de '+ date.toString('MMMM')+' de '+date.toString('yyyy')
        if os.path.exists(self.directorios['archivo_csv']):
            self.cargar_dia()
        else:
             QMessageBox.information(self,self.tr("Advertencia"),self.tr("Archivo csv no encontrado Show Date"))

    def Abrir_archivo(self):  #Depurado
        archivo__ = QFileDialog.getOpenFileName(
            parent=self,
            caption='Seleccione un archivo csv',
            directory=os.getcwd(),
        )
        self.directorios['archivo_csv'] =archivo__[0]
        if os.path.exists(self.directorios['archivo_csv']):
            self.cargar_dia()
        else:
             QMessageBox.information(self,self.tr("Advertencia"),self.tr("Archivo csv no encontrado Abrir Archivo"))

    def cargar_dia(self):
        self.eventos_reporte,self.catalogo,self.eventos, \
        self.vector,self.evento_canales, \
        self.root,self.responsables,self.resumen=cargar_dia(self.directorios['archivo_csv'])
        self.Btn_graficar.setEnabled(False)
        self.Btn_pagina.setEnabled(False)
        self.cmbx_evento.setEnabled(False)
        self.Btn_modificar.setEnabled(False)
        self.Btn_acelerograma.setEnabled(False)
        self.cmbx_evento_escogido.clear()
        self.indice=0 
        if os.path.exists(self.directorios['archivo_reporte']):        
            QMessageBox.information(self,self.tr("Día procesado"),self.tr("Se montará la información encontrada")) 
        self.cmbx_evento_escogido.setEnabled(False)
        self.cmbx_evento_escogido.clear()
        for x in self.eventos_reporte:
            if x[0]!='0':
                self.cmbx_evento_escogido.addItem(str(x[0])+"  "+str(x[1])+"  "+str(x[2]))
        self.cmbx_evento_escogido.setEnabled(True)  
        self.Btn_limpiar.setEnabled(True) 
        #self.lbl_responsable_1.setText(responsable[0])
        #self.lbl_responsable_2.setText(responsable[1])
        #self.lbl_responsable_3.setText(responsable[2])
        self.cmbx_evento_escogido.setEnabled(True)
        self.cmbx_evento.setEnabled(True)
        self.Btn_modificar.setEnabled(True)
        self.Btn_acelerograma.setEnabled(True)
        self.Btn_guardar.setEnabled(True)


    def Guardar_(self):
        Guardar_dia(self.eventos_reporte,self.catalogo,self.eventos,self.root,self.responsables,self.resumen,self.directorios)
        tree = ET.ElementTree(self.root)
        reporte_resumen(self.directorios['archivo_reporte_dia'], self.dia_reporte,self.fecha_ini,self.fecha_ini,self.catalogo,self.resumen,    1,       0,         (0,0,0),      self.estaciones_eventos,self.directorio_trabajo,tree,0,self.eventos_reporte,1)
        QMessageBox.information(self,self.tr("Aviso"),self.tr("¡Archivos Guardados!")) 

    def estacion_calidad(self):
        self.enlace=[]
        self.comportamiento=[]
        self.detalle=[]
        tr_canal=leer_mseed(self.archivo,0)
        evaluacion=calidad_estacion(tr_canal)
        estaciones_(evaluacion,self.directorios['archivo_csv'],self).exec_()
        with open(self.archivo_comportamiento, 'w', newline='') as archivo_grabar:
                escritor_csv = csv.writer(archivo_grabar,delimiter=';')
                escritor_csv.writerow(self.parametros['CODIGO'])
                escritor_csv.writerow(self.enlace)
                escritor_csv.writerow(self.comportamiento)
                escritor_csv.writerow(self.detalle)

    def reiniciar_evento(self):
        if self.bandera_evento==1:
            self.Cargar_evento()
        else:
            if self.evento_escogido[0][2]=='SISMO':
                self.Btn_generar.setEnabled(True)
            else:
                self.Btn_generar.setEnabled(False)
            if self.evento_escogido[0][2]=='Ruido':
                self.Btn_graficar.setEnabled(False)
                self.Btn_pagina.setEnabled(False)
            else:
                self.Btn_graficar.setEnabled(True)
                self.Btn_pagina.setEnabled(True)
            self.textEdit.setEnabled(True)
            self.textEdit_2.setEnabled(True)
            self.cmbx_red.setEnabled(True)
            self.cmbx_tipo_mag.setEnabled(True)
            self.Btn_insertar.setEnabled(True)
            self.textEdit.clear()
            self.textEdit_2.clear()
            self.cmbx_red.setCurrentIndex(0)
            self.cmbx_tipo_mag.setCurrentIndex(0)

    def Cargar_evento(self):
        lista_=[" ","Ruido","FF","FC","TELESISMO","SISMO","INDEFINIDO","Evento_local",'CONTROL']
        parametro=self.cmbx_evento_escogido.currentText()
        self.bandera_evento=0 
        self.indice, self.indice_local, self.indice_catalogo, self.archivo_escogido, \
        self.evento_escogido, self.canales, self.trCanal, self.archivo_reporte, \
        self.parametros['HAB_GRAFICO'],self.estaciones_eventos= cargar_evento(
            parametro,              # Parámetro principal para cargar el evento
            self.eventos_reporte,           # Lista de eventos disponibles
            self.catalogo,          # Catálogo asociado
            self.eventos,            # Datos específicos del evento
            self.evento_canales,    # Canales del evento
            self.directorio_trabajo,# Directorio de trabajo
            self.directorios['Directorio_reportes'] # Directorio de reportes
            )
        dato_escogido=self.eventos[self.indice_local-1] #evento desde el formato simple del día, solo número de evento y tipo
        self.cmbx_evento.setCurrentIndex(lista_.index(dato_escogido[2]))
        anio_s_ev=dato_escogido[1][0:2]
        self.label_1.setText(anio_s_ev)
        mes_s_ev=dato_escogido[1][2:4]
        self.label_2.setText(mes_s_ev)
        dia_s_ev=dato_escogido[1][4:6]
        self.label_3.setText(dia_s_ev)
        hora_s_ev=dato_escogido[1][7:9]
        self.label_4.setText(hora_s_ev)
        minuto_s_ev=dato_escogido[1][9:11]
        self.label_5.setText(minuto_s_ev)
        segundo_s_ev=dato_escogido[1][11:13]
        self.label_6.setText(segundo_s_ev)
        self.Btn_generar.setEnabled(True)
        if self.evento_escogido[0][2]=='Ruido':
            self.Btn_graficar.setEnabled(False)
            self.Btn_pagina.setEnabled(False)
        else:
            self.Btn_graficar.setEnabled(True)
            self.Btn_pagina.setEnabled(True)
        self.textEdit.setEnabled(True)
        self.textEdit_2.setEnabled(True)
        self.cmbx_red.setEnabled(True)
        self.cmbx_tipo_mag.setEnabled(True)
        self.Btn_insertar.setEnabled(True)

    def Insertar_evento(self):
        red_=self.cmbx_red.currentIndex()
        magnitud_=self.cmbx_tipo_mag.currentIndex()
        tipo_magnitud=self.cmbx_tipo_mag.currentText()
        texto=self.textEdit.toPlainText()
        texto2=self.textEdit_2.toPlainText()
        print(texto,texto2)
        self.catalogo,self.eventos_reporte=insertar_evento_otras_redes(
            self.catalogo,
            self.indice_catalogo,
            self.eventos_reporte,
            red_,
            magnitud_,
            tipo_magnitud,
            texto,
            texto2,
            self.evento_escogido,
            self.indice,
            self.indice_local
            )
        self.textEdit.clear()
        self.textEdit.setEnabled(False)
        self.textEdit_2.clear()
        self.textEdit_2.setEnabled(False)
        self.cmbx_red.setEnabled(False)
        self.cmbx_red.setCurrentIndex(0)
        self.cmbx_tipo_mag.setEnabled(False)
        self.cmbx_tipo_mag.setCurrentIndex(0)
        self.Btn_insertar.setEnabled(False)
        self.Btn_generar.setEnabled(True)

    def Generar_reporte_sismo(self):
        print(self.archivo_reporte)
        generar_reporte_sismo(self.catalogo, self.evento_escogido, self.canales, self.trCanal, self.archivo_reporte,self.directorio_trabajo)
    
    def Graficar_(self):
        plt.close()
        t_inicio=self.trCanal[self.estaciones_eventos[0]][0].stats.starttime
        t_final=self.trCanal[self.estaciones_eventos[0]][0].stats.endtime
        grafico_evento_int(self.trCanal,t_inicio,t_final,self.estaciones_eventos,self.parametros['HAB_GRAFICO'],0,0) #El ultimo parametro es la página, hay que gestionarla para que se despleigue
        
    def cambio_pagina(self):
        plt.close()
        self.pagina=self.pagina+1
        auxiliar=self.pagina*6
        if auxiliar > len(self.estaciones_eventos):
            self.pagina=0
        t_inicio=self.trCanal[self.estaciones_eventos[0]][0].stats.starttime
        t_final=self.trCanal[self.estaciones_eventos[0]][0].stats.endtime
        grafico_evento_int(self.trCanal,t_inicio,t_final,self.estaciones_eventos,self.parametros['HAB_GRAFICO'],0,self.pagina)

    def Modificar_(self):
        self.eventos_reporte[self.indice][2]=self.cmbx_evento.currentText()
        self.eventos_reporte[self.indice][3]=""

    def Acelerograma_(self):
        generar_reporte_acelerograma(self.eventos_reporte,self.indice,self.catalogo,self.evento_escogido,self.archivo_escogido)
        

    def filtrar_evento(self):
        b=self.sp_Box_finf.value()|self.sp_Box_fsup.value()|self.sp_Box_orden.value()
        if b != 0:
            plt.close()
            for i in range(0,100):
                if self.trCanal[i]!=[]:
                    t_inicio=self.trCanal[i][0].stats.starttime
                    t_final=self.trCanal[i][0].stats.endtime
                    break
            filtro_evento(self.trCanal,self.sp_Box_finf.value(),self.sp_Box_fsup.value(),self.sp_Box_orden.value(),t_inicio,t_final,self.estaciones_eventos,self.parametros['HAB_GRAFICO'],0,self.pagina)

    def Salir_(self):
        print("Saliendo completamente del programa.")
        plt.close('all')  # Cierra cualquier ventana de matplotlib abierta
        QtWidgets.QApplication.quit()  # Detiene el event loop y cierra la app correctamente
        os._exit(0)  # Fuerza la salida total del proceso, liberando toda la memoria (como último recurso)

class estaciones_(QDialog):
    def __init__(self, evaluacion,archivo,parent=None):
        super(estaciones_,self).__init__()
        self.parent=parent
        self.parametros=parametros_estaciones() ##parametros son los parametros de las estaciones (nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
        self.numero_estaciones=len(self.parametros['NOMBRE'])
        self.archivo=archivo
        self.evaluacion=evaluacion[0]
        self.tr_Canal=evaluacion[1]
        self.hab_canal=self.parametros['HAB_CANAL']
        self.setFixedSize(410, 420)
        QDialog.__init__(self)

        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", "estaciones.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        self.ck_box_disp_canal={}
        self.ck_box_hab_canal={}
        self.ck_box_comentario={}
        self.lbl_nombre={}
        self.lbl_codigo={}
        self.ck_box_hab_canal = [0 for x in range(16)]
        self.ck_box_disp_canal = [0 for x in range(16)]
        self.cmb_box_comentario = [0 for x in range(16)]
        self.lnedit_eval_canal = [0 for x in range(16)]#QLineEdit
        self.sp_box_canal = [0 for x in range(16)]#QSpinBox
        self.lbl_comportamiento={}
        nombre_canal_total_=self.parametros['NOMBRE']
        nombre_canal=self.parametros['CODIGO']
        self.lbl_grafico=QLabel("PLOT",self)
        self.lbl_grafico.setGeometry(246, 20, 51, 16)  #setGeometry(x, y, width, height)
        self.lbl_grafico=QLabel("EVALUAC.",self)
        self.lbl_grafico.setGeometry(300, 18, 51, 16)  #setGeometry(x, y, width, height)
        self.lbl_grafico=QLabel("ENLACE",self)
        self.lbl_grafico.setGeometry(370, 18, 51, 16)  #setGeometry(x, y, width, height)
        self.lbl_grafico=QLabel("COMP.",self)
        self.lbl_grafico.setGeometry(430, 18, 51, 16)  #setGeometry(x, y, width, height)
        self.lbl_grafico=QLabel("DET.",self)
        self.lbl_grafico.setGeometry(500, 18, 51, 16)  #setGeometry(x, y, width, height)
        k=0
        self.indice_estaciones=[]
        for i in range(0,self.numero_estaciones):
            self.parent.comportamiento.append(0)
            self.parent.detalle.append(0)
            self.parent.enlace.append(0)
            if self.evaluacion[i]!=-1:
                self.lbl_nombre[k]=QLabel(nombre_canal_total_[i],self)
                self.lbl_nombre[k].setGeometry(15, k*25+35, 150, 24)  #setGeometry(x, y, width, height)
                self.lbl_codigo[k]=QLabel(nombre_canal[i],self)
                self.lbl_codigo[k].setGeometry(150, k*25+35, 150, 24)  #setGeometry(x, y, width, height)
                self.ck_box_disp_canal[k]=QCheckBox(self)
                self.ck_box_disp_canal[k].setGeometry(257, k*25+35, 50, 24)  #setGeometry(x, y, width, height)
                self.lnedit_eval_canal[k]=QLineEdit(self)
                self.lnedit_eval_canal[k].setGeometry(300, k*25+35, 40, 24)  #setGeometry(x, y, width, height)
                self.lnedit_eval_canal[k].setText(str(self.evaluacion[i]))#Se carga el valor de la evalaucion
                self.sp_box_canal[k]=QSpinBox(self)
                self.sp_box_canal[k].setGeometry(365, k*25+35, 50, 24)  #setGeometry(x, y, width, height)
                self.parent.enlace[i]=100
                self.parent.comportamiento[i]=self.evaluacion[i]
                self.sp_box_canal[k].setRange(0,100)#El maximo valor del sp box es 100
                self.sp_box_canal[k].setSingleStep(10)
                self.sp_box_canal[k].setValue(self.parent.enlace[i])#Se carga el valor del enlace con 100%
                self.lbl_comportamiento[k]=QLabel(self)
                self.lbl_comportamiento[k].setGeometry(430, k*25+35, 150, 24)  #setGeometry(x, y, width, height)
                self.lbl_comportamiento[k].setText(str(self.parent.comportamiento[i]))
                self.cmb_box_comentario[k]=QComboBox(self)
                self.cmb_box_comentario[k].setGeometry(470, k*25+35, 100, 24)  #setGeometry(x, y, width, height)
                lista_detalle = ["1. OK", "2. Enlace caido", "3. Mantenimiento","4. Causa 1","5. Causa 2","6. Otro"]
                self.cmb_box_comentario[k].addItems(lista_detalle)
                self.indice_estaciones.append(i)
                k=k+1
        self.indice=0    
        self.btn_Graficar=QPushButton("Graficar",self)
        self.btn_Graficar.setGeometry(210, 450, 80, 24)  #setGeometry(x, y, width, height)
        self.btn_Graficar.clicked.connect(self.graficar)
        self.btn_Calcular=QPushButton("Calcular",self)
        self.btn_Calcular.setGeometry(310, 450, 80, 24)  #setGeometry(x, y, width, height)
        self.btn_Calcular.clicked.connect(self.calcular)
    
    def graficar(self):
        nombre_canal_total_=self.parametros['NOMBRE']
        nivel_ruido_=self.parametros['RUIDO']
        dia_="20"+self.archivo[-16:-14]+"/"+self.archivo[-14:-12]+"/"+self.archivo[-12:-10]
        for i in range(0,len(self.indice_estaciones)):
            if self.ck_box_disp_canal[i].checkState()==2:
                muestras=len(self.tr_Canal[i])
                x_1 = np.linspace(0,24,muestras)
                fig, ax = plt.subplots()
                titulo=nombre_canal_total_[self.indice_estaciones[i]]+"   "+dia_+"\n"
                titulo=titulo+"Evaluación: "+str(self.evaluacion[self.indice_estaciones[i]])+"       Enlace: "+str(self.parent.enlace[self.indice_estaciones[i]])+"\nComportamiento: "+str(self.parent.comportamiento[self.indice_estaciones[i]])
                ax.set_title(titulo)#, loc=alineacion, fontdict=fuente
                ax.plot(x_1,self.tr_Canal[i])
                ax.axhline(y = nivel_ruido_[self.indice_estaciones[i]], color = 'r')                
                #ax.text(0,0,texto, fontsize=10, color='black')
                plt.show()

    def calcular(self):
        for i in range(0,len(self.indice_estaciones)):
            enlace=int(self.sp_box_canal[i].value())
            comp=round(100*(self.evaluacion[self.indice_estaciones[i]])/enlace,1)
            detalle_=self.cmb_box_comentario[i].currentIndex()
            self.parent.enlace[self.indice_estaciones[i]]=enlace
            self.parent.comportamiento[self.indice_estaciones[i]]=comp
            self.parent.detalle[self.indice_estaciones[i]]=detalle_
            self.lbl_comportamiento[i].setText(str(comp))

    def closeEvent(self, event):
        self.calcular()
        event.accept()

    def Salir_(self):
        self.destroy()


if __name__ == '__main__': #Condicional que comprueba si ha sido ejecutado o importado
    app = QtWidgets.QApplication(sys.argv)#Creamos app y le pasamos una lista de argumentos vacíos
    #Borramos todo el resto del código y ahora vamos a instanciar nuestra clase MainWindow:
    window = MyApp()
    window.show()#Muestra la ventana:
    app.exec_() #Usamos app.exec_() para crear el bucle de ejecución


