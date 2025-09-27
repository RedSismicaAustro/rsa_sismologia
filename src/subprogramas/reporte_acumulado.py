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



from metodos_graficos_rsa import reporte_resumen
from metodos_rsa import lectura_resumen,parametros_estaciones,escritura_archivo,lectura_archivo,correccion,cargar_dia,obtener_datos_reporte,extraer_hasta_directorio
from metodos_gestion import obtener_directorios
#from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import *
from reportlab.graphics import shapes
from reportlab.graphics.charts.textlabels import Label
from reportlab.lib.colors import *
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
import csv
from PyQt5 import uic, QtWidgets#Importamos módulo uic y Qtwidgets
from datetime import datetime, date, time, timedelta
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox,QFileDialog)
import obspy
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import copy
#import time
from obspy import read
import numpy as np
import calendar
import os
from PyQt5.QtCore import pyqtSignal
IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19

NUMERO_ESTACIONES=101

IDX_LONGITUD_MINIMA,IDX_LATITUD_MINIMA,IDX_LONGITUD_MAXIMA,IDX_LATITUD_MAXIMA=0,1,2,3
IDX_POSICION_X,IDX_POSICION_Y,IDX_ANCHO,IDX_ALTO,=0,1,2,3

###################################
#archivo es el nombre del archivo con el que se grabará el archivo pdf
#titulo es lo que aparecerácomo primera línea del pdf
#vector es la variable que contiene la información sísmica.
#resumen
#bandera_dia variable que habilita o no la impresión del reporte diario de eventos (esto es para deshabilitar en el reporte diario)



class VentanaEstaciones(QtWidgets.QDialog):
    def __init__(self, parametros, parent=None):
        super(VentanaEstaciones, self).__init__(parent)
        self.setWindowTitle("Selector de Estaciones")
        self.parametros = parametros
        self.resize(600, 400)

        self.layout_principal = QtWidgets.QVBoxLayout(self)

        # Filtros por tipo de sensor
        self.filtro_sismicos = QtWidgets.QCheckBox("SISMICOS")
        self.filtro_acelerograficos = QtWidgets.QCheckBox("ACELEROGRAFICOS")
        self.filtro_sismicos.setChecked(True)
        self.filtro_acelerograficos.setChecked(True)

        filtro_layout = QtWidgets.QHBoxLayout()
        filtro_layout.addWidget(self.filtro_sismicos)
        filtro_layout.addWidget(self.filtro_acelerograficos)
        self.layout_principal.addLayout(filtro_layout)

        # Área de scroll para checkboxes de estaciones
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QtWidgets.QWidget()
        self.layout_estaciones = QtWidgets.QVBoxLayout(self.scroll_widget)

        self.scroll_area.setWidget(self.scroll_widget)
        self.layout_principal.addWidget(self.scroll_area)

        # Botón de marcar/desmarcar
        self.btn_toggle_seleccion = QtWidgets.QPushButton("Marcar/Desmarcar todos")
        self.layout_principal.addWidget(self.btn_toggle_seleccion)

        # Botones de acción
        botones_layout = QtWidgets.QHBoxLayout()
        self.btn_ejecutar = QtWidgets.QPushButton("Ejecutar")
        self.btn_salir = QtWidgets.QPushButton("Salir")
        botones_layout.addWidget(self.btn_ejecutar)
        botones_layout.addWidget(self.btn_salir)
        self.layout_principal.addLayout(botones_layout)

        # Conexiones
        self.filtro_sismicos.stateChanged.connect(self.actualizar_estaciones)
        self.filtro_acelerograficos.stateChanged.connect(self.actualizar_estaciones)
        self.btn_toggle_seleccion.clicked.connect(self.toggle_todos)
        self.btn_salir.clicked.connect(self.close)

        self.checkboxes_estaciones = []
        self.actualizar_estaciones()

    def actualizar_estaciones(self):
        # Limpiar layout
        for i in reversed(range(self.layout_estaciones.count())):
            widget = self.layout_estaciones.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.checkboxes_estaciones.clear()

        for i in range(len(self.parametros['HAB_CANAL'])):
            if self.parametros['HAB_CANAL'][i] == "1":
                sensor = self.parametros['SENSOR'][i]
                mostrar = False
                if sensor == "SISMICO" and self.filtro_sismicos.isChecked():
                    mostrar = True
                elif sensor == "ACELEROGRAFICO" and self.filtro_acelerograficos.isChecked():
                    mostrar = True
                if mostrar:
                    nombre = self.parametros['NOMBRE'][i]
                    codigo = self.parametros['CODIGO'][i]
                    tipo = self.parametros['SENSOR'][i]
                    checkbox = QtWidgets.QCheckBox(f"{codigo} - {nombre} ({tipo})")
                    checkbox.setProperty("indice", i)
                    self.layout_estaciones.addWidget(checkbox)
                    self.checkboxes_estaciones.append(checkbox)

    def toggle_todos(self):
        """Marca o desmarca todos los checkboxes filtrados"""
        if not self.checkboxes_estaciones:
            return

        # Verificar si hay alguno desmarcado
        alguno_sin_marcar = any(not cb.isChecked() for cb in self.checkboxes_estaciones)
        for cb in self.checkboxes_estaciones:
            cb.setChecked(alguno_sin_marcar)

    def obtener_estaciones_seleccionadas(self):
        """Devuelve los índices de estaciones seleccionadas"""
        seleccionadas = []
        for cb in self.checkboxes_estaciones:
            if cb.isChecked():
                seleccionadas.append(cb.property("indice"))
        return seleccionadas


class Reporte(QMainWindow):
    cerrado = pyqtSignal()  # señal que se emitire al cerrar
    def __init__(self, archivo, directorio_trabajo, responsable, periodo, parent=None):#Constructor de la clase
        super(Reporte,self).__init__(parent)
        QMainWindow.__init__(self)
        #Carga la configuración del archivo .ui en el objeto

        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", "reporte_mensual.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)
        self.Btn_abrir.clicked.connect(self.Abrir_archivo)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_guardar.clicked.connect(self.Guardar_)
        self.Btn_cargar_catalogo.clicked.connect(self.cargar_catalogo_guardado)
        self.btn_estaciones.clicked.connect(self.estaciones)
        self.btn_periodo.clicked.connect(self.periodo)
        self.btn_mes.clicked.connect(self.mes_)
        self.btn_anio.clicked.connect(self.anio_)
        self.btn_semana.clicked.connect(self.semana_)
        self.btn_selector_estaciones.clicked.connect(self.abrir_ventana_estaciones)
        self.estaciones_habilitadas=[]
        self.nombre_estaciones_habilitadas=[]
        self.btn_periodo_cat.clicked.connect(self.acumular_solo_catalogo)
        lista_estaciones=[]
        self.parametros=parametros_estaciones()
        for i in range (0,101):
            if self.parametros['HAB_CANAL'][i]=='1':
                lista_estaciones.append(self.parametros['NOMBRE'][i])
                self.estaciones_habilitadas.append(i)
                self.nombre_estaciones_habilitadas.append(self.parametros['CODIGO'][i])
        self.Cmb_bx_estacion.addItems(lista_estaciones)    
        self.inicializar_variables()

        lista_filtros = ["Ruido", "FF", "FC","TELESISMO","SISMO","INDEFINIDO","Evento_local",'CONTROL',"TODOS"]
        self.Cmb_bx_tipo_evento.addItems(lista_filtros)
        lista_anio=[]
        for i in range(1995,2050):
            lista_anio.append(str(i))
        lista_semana=[]
        for i in range(1,54):
            auxiliar=str(i)
            if i<10:
                auxiliar="0"+auxiliar
            lista_semana.append(auxiliar)
        self.comboBox_semana.addItems(lista_semana)
        lista_mes=["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        self.comboBox_mes.addItems(lista_mes)
        self.comboBox_anio.addItems(lista_anio)

        archivo =  os.path.join(ruta_proyecto,"datos", "mapas",'mapas.csv')
        archivo = os.path.abspath(archivo)

        with open(archivo,newline='') as mapas_csv:
            lista_mapas=csv.reader(mapas_csv,delimiter=';',quotechar=';')
            mapa=[]
            self.coordenadas=[]
            for x in lista_mapas:
                if x[0]!='nombre':
                    mapa.append(x[0])
                    self.coordenadas.append(x[1:7])
        self.cmbx_zona.addItems(mapa)
        self.cmbx_zona.setCurrentIndex(1)
        tipo_mapa=("1.Básico","1.Medio","3.Físico","4.Nidos","5.Fallas","6.Combinados")
        self.cmbx_mapa.addItems(tipo_mapa)
        magnitudes=("todos","2.5","3.0","3.5","4.0","4.5","5.0","5.5","6.0","6.5")
        self.cmbx_magnitud.addItems(magnitudes)
        estaciones_n=("todos","4","5","6","7")
        self.cmbx_n_estaciones.addItems(estaciones_n)
        profundidades=("Todos","Superficiales","Medios","Profundos","Sup. y Medios","Medios y prof.")
        self.cmbx_profundidad.addItems(profundidades)
        self.hoy=datetime.today()              #obtención de la fecha y hora actual
        d_ini = QDate(self.hoy.year, self.hoy.month,self.hoy.day-7)# obtención del año , mes y día en forma individual
        d_fin = QDate(self.hoy.year, self.hoy.month,self.hoy.day)# obtención del año , mes y día en forma individual
        self.dateEdit_ini.setDate(d_ini)    #Conficuración de los datos de fecha en el DataEdit
        self.dateEdit_fin.setDate(d_fin)
        semana = self.hoy.strftime("%U")
        hoy = QDate.currentDate()
        self.dateEdit_ini_cat.setDate(QDate(2000, 1, 1))
        self.dateEdit_fin_cat.setDate(QDate(hoy.year(), hoy.month(), 1))

        self.comboBox_semana.setCurrentIndex(int(semana)-1)
        self.comboBox_anio.setCurrentIndex(int(self.hoy.year)-1995)
        self.comboBox_mes.setCurrentIndex(int(self.hoy.month)-1)
        self.directorio_trabajo="G:/Mi unidad/DIA/"
        self.lbl_directorio.setText(self.directorio_trabajo)
        self.cmbx_zona.currentIndexChanged.connect(self.Cargar_catalogo)
        self.cmbx_mapa.currentIndexChanged.connect(self.Cargar_catalogo)
        self.cmbx_magnitud.currentIndexChanged.connect(self.Cargar_catalogo)
        self.cmbx_n_estaciones.currentIndexChanged.connect(self.Cargar_catalogo)


    def inicializar_variables(self):
        self.eventos=[]
        self.eventos_reporte=[["Nº","Fecha; Hora (UTC)","Evento","Magn.","Prof.(km)","Lat.","Long.","Ubicación"]]
        self.catalogo=[["Id","año","mes","día","hora","min","seg","lat","long","prof","rms","e-x","e-y","e-0","e-z","Mag","Tipo Mag","Fuente","ruta","Ubicación"]]
        self.reporte_total=[["RESPONSABLE","HORA","TOTAL","SISMO","FF","FC","TELESISMOS","Evento_local","INDEFINIDO","Ruido","3 est","4 est","5 est","6 est","7 est","8 est"]]
        self.resumen=[["DIA","SISMO","FF","FC","TELESISMO","Evento Local","INDEFINIDO","Ruido"]]
        # Cargar el primer archivo XML

        ruta_ =  os.path.join(ruta_proyecto,"datos", 'archivo.xml')
        archivo = os.path.abspath(ruta_)

        self.arbol = ET.parse(archivo)
        self.raiz = self.arbol.getroot()

    def Abrir_archivo(self):  #Depurado
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath
        self.lbl_directorio.setText(self.directorio_trabajo)
        
    def Guardar_(self):
        self.filtros()
        if self.periodo_reporte[0:9]=='Período: ':
            #Por periodo
            nombre_=self.periodo_reporte[9:]
            nombre_ = nombre_.replace('/', '_')
            nombre_="/"+nombre_
        else:
            #semanal
            nombre_="/"+self.periodo_reporte[:10]
        directorio_=self.directorio_reporte+"/"+self.cmbx_zona.currentText()+"/"
        try:
            path = Path(directorio_)
            path.mkdir(parents=True)
        except FileExistsError:
            pass    
        self.lbl_dir_archivo.setText(directorio_)
        self.archivo_dat_men=directorio_+nombre_+"_rep.csv"
        self.archivo_reportes_total=directorio_+nombre_+"_rep_total.csv"
        self.archivo_cat_men=directorio_+nombre_+"_cat.csv"
        self.archivo_res_men=directorio_+nombre_+"_res.csv"
        self.archivo_responsables_=directorio_+nombre_+"_responsables.csv"#Archivo con el numero total de eventos por responsable
        self.archivo_est_men=directorio_+nombre_+"_est.csv"#Archivo con los resumenes
        self.archivo_1_pdf=directorio_+nombre_+"_pdf1.pdf"
        self.archivo_2_pdf=directorio_+nombre_+"_pdf2.pdf"
        self.archivo_3_pdf=directorio_+nombre_+"_pdf3.pdf"#Archivo de informe en pdf
        self.archivo_pro=directorio_+nombre_+"__rsa_pro.csv"
        self.archivo_med=directorio_+nombre_+"__rsa_med.csv"
        self.archivo_sup=directorio_+nombre_+"__rsa_sup.csv"
        self.archivo_or_pro=directorio_+nombre_+"__otr_pro.csv"
        self.archivo_or_med=directorio_+nombre_+"__otr_med.csv"
        self.archivo_or_sup=directorio_+nombre_+"__otr_sup.csv"
        self.archivo_xml_escritura=directorio_+nombre_+".xml"
        self.archivo_resumen_acelerografos=directorio_+nombre_+"_aceleraciones.csv"
        self.archivo_resumen_acelerografos_base=directorio_+nombre_+"_aceleraciones_base.csv"
        self.archivo_eventos_acelerografos=directorio_+nombre_+"_cat_aceleraciones.csv"
        even_rsa_sup=[["LAT","LONG","Prof.","Mag."]]
        even_rsa_int=[["LAT","LONG","Prof.","Mag."]]
        even_rsa_prof=[["LAT","LONG","Prof.","Mag."]]
        even_otr_sup=[["LAT","LONG","Prof.","Mag."]]
        even_otr_int=[["LAT","LONG","Prof.","Mag."]]
        even_otr_prof=[["LAT","LONG","Prof.","Mag."]]
        #evento_total=[]
        with open(self.archivo_cat_men, 'w', newline='') as archivo_grabar_2:
            escritor_csv_2 = csv.writer(archivo_grabar_2,delimiter=';')
            for i in range(0,len(self.catalogo)):
                if(len(self.catalogo[i])>0):
                    escritor_csv_2.writerow(self.catalogo[i])
        with open(self.archivo_dat_men, 'w', newline='') as archivo_grabar:
                escritor_csv = csv.writer(archivo_grabar,delimiter=';')
                for i in range(0,len(self.eventos_reporte)):
                    escritor_csv.writerow(self.eventos_reporte[i])
        with open(self.archivo_reportes_total, 'w', newline='') as archivo_grabar:
                escritor_csv = csv.writer(archivo_grabar,delimiter=';')
                for i in range(0,len(self.reporte_total)):
                    escritor_csv.writerow(self.reporte_total[i])
        cont_sismos=0
        cont_FF=0
        cont_FC=0
        cont_ind=0
        cont_tel=0
        cont_ev=0
        cont_ruido=0
        for i in range(0,len(self.eventos_reporte)):
            if(self.eventos_reporte[i][2]=="SISMO"):
                cont_sismos=cont_sismos+1
            if(self.eventos_reporte[i][2]=="FF"):
                cont_FF=cont_FF+1
            if(self.eventos_reporte[i][2]=="FC"):
                cont_FC=cont_FC+1
            if(self.eventos_reporte[i][2]=="TELESISMO"):
                cont_tel=cont_tel+1
            if(self.eventos_reporte[i][2]=="Evento_local"or self.eventos_reporte[i][2]=="CONTROL"):
                cont_ev=cont_ev+1
            if(self.eventos_reporte[i][2]=="Ruido"):
                cont_ruido=cont_ruido+1
            if(self.eventos_reporte[i][2]=="INDEFINIDO"):
                cont_ind=cont_ind+1
        if self.cmbx_zona.currentIndex()<4:# self.cmbx_zona.currentIndex()==0
            self.resumen.insert(1,["Total:",cont_sismos,cont_FF,cont_FC,cont_tel,cont_ev,cont_ind,cont_ruido])

##############################################################################################        
        #etapa de clasificacion de self.eventos_reporte

        #Evento total, tupla que contiene tuplas por día con la informacioón de los sismos[latitud, longitud, profundidad, magnitud,red], red:0 RSA, 1 otra red
##############################################################################################
        for i in range(1,len(self.catalogo)):  #-1 decia antes de cambiarlo
            x=float(self.catalogo[i][IDX_LATITUD])#Coordenada en x
            y=float(self.catalogo[i][IDX_LONGITUD])#Coordenada en y
            p=-1*float(self.catalogo[i][IDX_PROFUNDIDAD])#Profundidad
            mag=float(self.catalogo[i][IDX_MAGNITUD])#Magnitud
            #num=self.catalogo[i][18]
            evento_=[x,y,p,mag]

            if(p>-40):
                if(self.catalogo[i][IDX_FUENTE]=="RSA"):
                    even_rsa_sup.append(evento_)
                else:
                    even_otr_sup.append(evento_)
            else:
                if(p>-70):
                    if(self.catalogo[i][IDX_FUENTE]=="RSA"):
                        even_rsa_int.append(evento_)
                    else:
                        even_otr_int.append(evento_)
                else:
                    if(self.catalogo[i][IDX_FUENTE]=="RSA"):
                        even_rsa_prof.append(evento_)
                    else:
                        even_otr_prof.append(evento_)

#################################################################################
#               Reporte en pdf                   
#################################################################################

        if self.ck_box_reporte.checkState()==2:
            bandera_reporte=1
        else:
            bandera_reporte=0
        if self.ck_box_firma.checkState()==2:
            bandera_firma=1
        else:
            bandera_firma=0        
        banderas=(1,bandera_reporte,bandera_firma)
        bandera_relleno=self.ck_box_relleno.isChecked()

        #             reporte_resumen(archivo,              subtitulo,           fecha_ini,      fecha_fin,      catalogo,      resumen,          mapa_,                          detalle,                  banderas,estaciones,     directorio          ,arbol,    resumen responsables) 
        acelerogramas=reporte_resumen(self.archivo_1_pdf,
                                      self.periodo_reporte,
                                      self.fecha_ini,
                                      self.fecha_fin, 
                                      self.catalogo,
                                      self.resumen,
                                      self.cmbx_zona.currentIndex(),
                                      self.cmbx_mapa.currentIndex(),     
                                      banderas,       
                                      0      ,  
                                      self.directorio_trabajo,
                                      self.arbol,
                                      self.reporte_total,
                                      self.eventos,
                                      bandera_relleno)
        registro1=[]
        registro2=[]
        xxx=['Evento','Estación','Canal 0'  ,''        ,''         ,'Canal 1'  ,''        ,''         ,'Canal 2'  ,''         ,'']
        registro1.append(xxx)
        registro2.append(xxx)
        xxx=[''      ,''        ,'Acel. max','Vel. max','Desp. max','Acel. max','Vel. max','Desp. max','Acel. max','Vel. max','Desp. max']
        registro1.append(xxx)
        registro2.append(xxx)
        for evento in acelerogramas:
            linea=[]
            linea.append(evento[0])
            
            for i, estacion in enumerate(evento[1]):
                if i==0:
                    codigo_estacion=self.parametros['CODIGO'][estacion]
                    linea.append(codigo_estacion)
                else:
                    for k in range (1,4):
                        linea.append(str(estacion[k]))
            registro1.append(linea)
            if linea[1]=='CHAB':
                registro2.append(linea)
        escritura_archivo(self.archivo_resumen_acelerografos,registro1)
        escritura_archivo(self.archivo_resumen_acelerografos_base,registro2)
        xxx=['Id','año',	'mes',	'día',	'hora',	'min',	'seg',	'lat',	'long',	'prof',	'Mag',	'Fuente',	'ruta']
        catalogo_acelerometros=[]
        catalogo_acelerometros.append(xxx)
        for evento in registro2:
            for catalogo in self.catalogo:
                if evento[0]==catalogo[18]:
                    xxx=[catalogo[0],catalogo[1],catalogo[2],catalogo[3],catalogo[4],catalogo[5],catalogo[6],catalogo[7],catalogo[8],catalogo[9],catalogo[15]+catalogo[16],catalogo[17],catalogo[18]]
                    catalogo_acelerometros.append(xxx)
        escritura_archivo(self.archivo_eventos_acelerografos,catalogo_acelerometros)
            

        if self.cmbx_zona.currentIndex()<4:#self.cmbx_zona.currentIndex()==0
    
#################################################################################
#               Escritura del archivo resumen                    
#################################################################################
            with open(self.archivo_res_men, 'w', newline='') as archivo_grabar:
                escritor_csv = csv.writer(archivo_grabar,delimiter=';')
                for i in range(0,len(self.resumen)):
                    if(i>1):
                        self.resumen[i].insert(0,i-1)
                    escritor_csv.writerow(self.resumen[i])

#################################################################################
#               Escritura del archivo eventos RSA superficial                    
#################################################################################                 

            with open(self.archivo_sup, 'w', newline='') as archivo_grabar:#archivo_pro,archivo_med,archivo_sup,archivo_or_pro,archivo_or_med,archivo_or_sup
                escritor_csv = csv.writer(archivo_grabar,delimiter=',')
                for i in range(0,len(even_rsa_sup)):
                    escritor_csv.writerow(even_rsa_sup[i])

#################################################################################
#               Escritura del archivo eventos RSA intermedios                    
#################################################################################

            with open(self.archivo_med, 'w', newline='') as archivo_grabar:#archivo_pro,archivo_med,archivo_sup,archivo_or_pro,archivo_or_med,archivo_or_sup
                escritor_csv = csv.writer(archivo_grabar,delimiter=',')
                for i in range(0,len(even_rsa_int)):
                    escritor_csv.writerow(even_rsa_int[i])         

#################################################################################
#               Escritura del archivo eventos RSA profundos                    
#################################################################################
                    
            with open(self.archivo_pro, 'w', newline='') as archivo_grabar:#archivo_pro,archivo_med,archivo_sup,archivo_or_pro,archivo_or_med,archivo_or_sup
                escritor_csv = csv.writer(archivo_grabar,delimiter=',')
                for i in range(0,len(even_rsa_prof)):
                    escritor_csv.writerow(even_rsa_prof[i])         

#################################################################################
#               Escritura del archivo eventos otras redes superficial                    
#################################################################################

            with open(self.archivo_or_sup, 'w', newline='') as archivo_grabar:#archivo_pro,archivo_med,archivo_sup,archivo_or_pro,archivo_or_med,archivo_or_sup
                escritor_csv = csv.writer(archivo_grabar,delimiter=',')
                for i in range(0,len(even_otr_sup)):
                    escritor_csv.writerow(even_otr_sup[i])

#################################################################################
#               Escritura del archivo eventos otras redes intermedio                    
#################################################################################

            with open(self.archivo_or_med, 'w', newline='') as archivo_grabar:#archivo_pro,archivo_med,archivo_sup,archivo_or_pro,archivo_or_med,archivo_or_sup
                escritor_csv = csv.writer(archivo_grabar,delimiter=',')
                for i in range(0,len(even_otr_int)):
                    escritor_csv.writerow(even_otr_int[i])         

#################################################################################
#               Escritura del archivo eventos otras redes profundo                    
#################################################################################
                    
            with open(self.archivo_or_pro, 'w', newline='') as archivo_grabar:#archivo_pro,archivo_med,archivo_sup,archivo_or_pro,archivo_or_med,archivo_or_sup
                escritor_csv = csv.writer(archivo_grabar,delimiter=',')
                for i in range(0,len(even_otr_prof)):
                    escritor_csv.writerow(even_otr_prof[i])


#################################################################################
#               Escritura del archivo eventos XML                    
#################################################################################


        # Guardar el archivo resultante
        self.nuevo_arbol.write(self.archivo_xml_escritura)
        QMessageBox.information(self,self.tr("Aviso"),self.tr("¡Archivo Guardado"))  
        self.inicializar_variables()
        self.Btn_guardar.setEnabled(False)

           
    def anio_(self):
        anio=int(self.comboBox_anio.currentText())
        self.fecha_ini=datetime(anio,1,1)
        self.fecha_fin=datetime(anio,12,31)
        self.periodo_reporte, self.directorio_reporte,self.archivo_reporte=obtener_datos_reporte(self.fecha_ini,self.fecha_fin,self.directorio_trabajo,self.cmbx_zona.currentText())
        self.recopilacion(self.fecha_ini,self.fecha_fin)
        self.Btn_guardar.setEnabled(True)

    def mes_(self):
        anio=int(self.comboBox_anio.currentText())
        mes=self.comboBox_mes.currentIndex()+1
        self.fecha_ini=datetime(anio,mes,1)
        self.fecha_fin=datetime(anio,mes,calendar.monthrange(anio, mes)[1])
        
        self.periodo_reporte, self.directorio_reporte,self.archivo_reporte=obtener_datos_reporte(self.fecha_ini,self.fecha_fin,self.directorio_trabajo,self.cmbx_zona.currentText())
        self.recopilacion(self.fecha_ini,self.fecha_fin)
        self.Btn_guardar.setEnabled(True)

    def semana_(self):
        anio=int(self.comboBox_anio.currentText())
        semana=int(self.comboBox_semana.currentText())
        self.fecha_ini = datetime.strptime(f'{anio}-W{semana}-1', '%G-W%V-%u')#.replace(hour=0, minute=0, second=0)
        self.fecha_fin = self.fecha_ini + timedelta(days=6)
        self.periodo_reporte, self.directorio_reporte,self.archivo_reporte=obtener_datos_reporte(self.fecha_ini,self.fecha_fin,self.directorio_trabajo,self.cmbx_zona.currentText())
        self.recopilacion(self.fecha_ini,self.fecha_fin)
        self.Btn_guardar.setEnabled(True)

    def periodo(self):
        self.fecha_ini=self.dateEdit_ini.date().toPyDate() #Transforma el QdataEdit en formato date de python
        self.fecha_ini=datetime.combine(self.fecha_ini, time(0,0,0))#Transforma los datos tipo date a tipo datetime
        self.fecha_fin=self.dateEdit_fin.date().toPyDate()
        self.fecha_fin=datetime.combine(self.fecha_fin, time(0,0,0))#Transforma los datos tipo date a tipo datetime
        self.periodo_reporte, self.directorio_reporte,self.archivo_reporte=obtener_datos_reporte(self.fecha_ini,self.fecha_fin,self.directorio_trabajo,self.cmbx_zona.currentText())
        self.recopilacion(self.fecha_ini,self.fecha_fin)
        self.Btn_guardar.setEnabled(True)

    def estaciones(self):
        print('¡¡Recopilando informacion!!')
        self.eventos=[]
        self.fecha_ini=self.dateEdit_ini.date().toPyDate() #Transforma el QdataEdit en formato date de python
        self.fecha_ini=datetime.combine(self.fecha_ini, time(0,0,0))#Transforma los datos tipo date a tipo datetime
        self.fecha_fin=self.dateEdit_fin.date().toPyDate()
        self.fecha_fin=datetime.combine(self.fecha_fin, time(0,0,0))#Transforma los datos tipo date a tipo datetime
        self.periodo_reporte, self.directorio_reporte,self.archivo_reporte=obtener_datos_reporte(self.fecha_ini,self.fecha_fin,self.directorio_trabajo,self.cmbx_zona.currentText())
        self.recopilacion(self.fecha_ini,self.fecha_fin)
        eventos_escogidos=[]
        for eventos in self.eventos:
            
            #archivo=eventos[1][:6]+eventos[1][7:-4]
            #fecha_hora = obtencion_hora(archivo)
            #fecha_formateada = fecha_hora.strftime("%d/%m/%Y %H:%M:%S")
            aux=[]
            bandera_reporte=0
            if self.Cmb_bx_tipo_evento.currentText()=='TODOS':
                bandera_reporte=1
            else:
                if eventos[2]==self.Cmb_bx_tipo_evento.currentText():
                    print("Evento:",eventos[1],':',eventos[2])
                    aux.append(eventos[1])
                    bandera_reporte=1
            if  bandera_reporte:
                estacion_=self.Cmb_bx_estacion.currentText()
                indice_=self.parametros['NOMBRE'].index(estacion_)
                nombre_canal=self.parametros['CODIGO'][indice_]
                for i in range(0,len(self.catalogo)):
                    if eventos[1]==self.catalogo[i][IDX_EVENTO] :
                        directorio=obtener_directorios(eventos[1])['Directorio_eventos']
                        nombre_mseed=self.directorio_trabajo+directorio+'/'+nombre_canal+'_20'+eventos[1][:-3]+'mseed'
                        if len(eventos[indice_+3])<6:
                            bandera=0
                        else:
                            if eventos[indice_+3][5]=='1':
                                bandera=1
                            else:
                                bandera=0
                        if os.path.exists(nombre_mseed) and bandera:
                            aux.append(eventos[1])
                            aux.append(self.catalogo[i][IDX_LATITUD])
                            aux.append(self.catalogo[i][IDX_LONGITUD])
                            aux.append(self.catalogo[i][IDX_MAGNITUD])
                            aux.append(self.catalogo[i][IDX_FUENTE])
                            aux.append(self.catalogo[i][IDX_LUGAR])
                            st = read(nombre_mseed)
                            factor=float(self.parametros['FACTOR_MUL'][indice_])
                            canales=len(st)
                            for j in range(0,canales):
                                seniales=correccion(st[j],factor)
                                maximo=max(abs(max(seniales[0])),abs(min(seniales[0])))
                                aux.append(str(maximo))
                            #break
                        else:
                            print('No existe o no marcado')
            if aux!=[]:
                eventos_escogidos.append(aux)

                          
        directorio_=self.directorio_reporte+"/otros/"
        try:
            path = Path(directorio_)
            path.mkdir(parents=True)
        except FileExistsError:
            pass    
        aux_nombre=self.nombre_estaciones_habilitadas[self.Cmb_bx_estacion.currentIndex()]
        nombre_=directorio_+aux_nombre+'_'+self.Cmb_bx_tipo_evento.currentText()+'_rep.csv'
        escritura_archivo(nombre_,eventos_escogidos)
        print('Guardando en   ',nombre_)
        print('¡¡Terminado!!')



    def recopilacion(self,fecha_inicio,fecha_fin):
#####################################################################################################################################################################################################        
#Carga los datos de los archivos diarios de catálogo (AAMMddhhmmss_cat.csv), datos(AAMMddhhmmss_dat.csv) y resumen(AAMMddhhmmss_res.csv)
# las tuplas self.catalogo, self.eventos_reporte y self.resumen tienen cabeceras que indican el tipo de variable, self.resumen tine una cabecera adicional correspondiente a la sumatoria de las variables.
#
###################################   
#self.catalogo   datos a partir de la posición 1
# 0  1   2   3    4   5   6   7    8   9   10   11 12  13  14  15     16      17    18     19    
#Id;año;mes;día;hora;min;seg;lat;long;prof;rms;e-x;e-y;e-0;e-z;Mag;Tipo Mag;Fuente;ruta;Ubicación
###################################
#self.eventos_reporte    datos a partir de la posición 1
# 0    1       2          3      4       5      6    7       8   
#Nº;"Fecha; Hora (UTC)";Evento;Magn.;Prof.(km);Lat.;Long.;Ubicación
###################################
#self.resumen    datos a partir de la posición 2
#  0     1   2  3     4          5           6        7  
# DIA;SISMO;FF;FC;TELESISMO;Evento Local;INDEFINIDO;Ruido
#Total:;     ;  ;  ;         ;            ;          ;     
        fecha=fecha_inicio
        while fecha <= fecha_fin:#while fecha < fecha_fin:
            fecha_ = QDate(fecha.year, fecha.month,fecha.day)
            archivo=os.path.join(self.directorio_trabajo,fecha_.toString('yyyyMMdd000000'))
            self.directorios=obtener_directorios(archivo)
            if os.path.exists(self.directorios['Directorio_base']):
                eventos_reporte,catalogo,\
                eventos,vector,canales_eventos_dia,\
                self.root,self.responsable,resumen=cargar_dia(self.directorios['archivo_csv'])
                self.eventos=self.eventos+eventos
                self.catalogo=self.catalogo+catalogo[1:]
                self.eventos_reporte=self.eventos_reporte+eventos_reporte[1:]
                self.resumen=self.resumen+lectura_resumen(self.directorios['archivo_resumen'])
                self.reporte_total=self.reporte_total+lectura_resumen(self.directorios['archivo_responsables'])
                # Cargar el segundo archivo XML
                tree2 = ET.parse(self.directorios['archivo_xml'])
                raiz2 = tree2.getroot()
                # Agregar los elementos del segundo archivo al primer archivo
                for child in raiz2:
                    self.raiz.append(child)    
            fecha = fecha + timedelta(1)  # Suma a fecha actual 1 día
        self.Respaldar_catalogo()


    def filtros(self):
        # Crear un nuevo árbol XML para almacenar los eventos filtrados
        self.nuevo_arbol = ET.ElementTree(ET.Element('sismo'))
        if True:#if self.cmbx_zona.currentIndex()>2:#If True:  # Para poder filtrar todo.
        # Definir los rangos de valores
        # Crear un nuevo árbol de elementos para almacenar los eventos filtrados
            coord_=self.coordenadas[self.cmbx_zona.currentIndex()]
            lat2 = float(coord_[1])
            lat1 = float(coord_[0])
            long2 = float(coord_[3])
            long1 = float(coord_[2])
            estaciones=coord_[5].split()
            eventos_filtrados = []
            try:
                mag_=float(self.cmbx_magnitud.currentText())
            except ValueError:
                mag_=0.0
            try:
                n_est_=float(self.cmbx_n_estaciones.currentText())
            except ValueError:
                n_est_=0.0
            eventos_filtrados.append(self.catalogo[0])
            n_eventos=len(self.catalogo)
###########FIltro del catálogo, son los eventos dentro del marco mas los eventos de IGEPN

            
            prof_filtro={'Todos':[0.0,1000.0],      #Todos los eventos
           'Superficiales':[0.0,40.0],              #Solo superficiales
           'Medios':[40.0,70.0],                    #Solo medios
           'Profundos':[70.0,1000.0],               #Solo profundos
           'Sup. y Medios':[0.0,70.0],              #Superficiales y medios
           'Medios y prof.':[70.0,1000.0]}          #Medios y profundos.
            profundidades_filtro=prof_filtro[self.cmbx_profundidad.currentText()]
            prof_min=profundidades_filtro[0]
            prof_max=profundidades_filtro[1]
            print("Magnitud:",mag_,"Estaciones:",n_est_,"Profundidades:",profundidades_filtro)
            for i in range(1, n_eventos):
                latitud = float(self.catalogo[i][IDX_LATITUD])
                longitud = float(self.catalogo[i][IDX_LONGITUD])
                profundidad=float(self.catalogo[i][IDX_PROFUNDIDAD])
                magnitud=float(self.catalogo[i][IDX_MAGNITUD])
                if lat1 <= latitud <= lat2 and long1 <= longitud <= long2:
                    if prof_min <= profundidad <= prof_max:
                        if mag_<=magnitud:
                            eventos_filtrados.append(self.catalogo[i])
                else:
                    
                    if self.catalogo[i][17]!='RSA':
                        #resultado = [sublista for sublista in self.eventos if sublista[2] == valor_a_buscar]
                        directorios=obtener_directorios(self.catalogo[i][18])
                        for estacion in estaciones:
                            evento_mseed=self.directorio_trabajo+'/'+directorios['Directorio_eventos']+'/'+self.parametros['CODIGO'][int(estacion)]+directorios['sufijo_mseed']
                            print(evento_mseed)
                        eventos_filtrados.append(self.catalogo[i])


            self.catalogo=eventos_filtrados
            numero_dias=self.fecha_fin-self.fecha_ini
            #valor_inicial= int(self.fecha_ini.strftime("%Y%m%d"))
            #valor_final= int(self.fecha_fin.strftime("%Y%m%d"))
            if self.cmbx_zona.currentIndex()>3:# MNATIENE LA VARIABLE self.resumen cuando 
                self.resumen=[]

############Inicializacion del resumen
                for i in range(0,numero_dias.days+3):
                    self.resumen.append(0)# Truco, para que coja como vector y no como entero
                for evento in self.catalogo:
                    if evento[IDX_INDICE]!='Id' and evento[IDX_FUENTE]=='RSA':
                        fecha_it=datetime(int(evento[IDX_INDICE][0:4]),int(evento[IDX_INDICE][4:6]),int(evento[IDX_INDICE][6:8]))
                        contador=fecha_it-self.fecha_ini
                        self.resumen[contador.days+2]=self.resumen[contador.days+2]+1
            numero_registros = 0
            for evento in self.raiz.findall('.//Evento'):
                # Obtener los valores de longitud y latitud
                longitud = float(evento.find('longitud').text)
                latitud = float(evento.find('latitud').text)
                magnitud = float(evento.find('magnitud').text)
                registros = list(evento.iterfind("estaciones/estacion"))
                numero_registros = len(registros)
                if long1 <= longitud <= long2 and lat1 <= latitud <= lat2 and magnitud>=mag_ and numero_registros>=n_est_:
        # Crear un nuevo elemento de evento y copiar todos los atributos
                    nuevo_evento = ET.SubElement(self.nuevo_arbol.getroot(), 'Evento')
                    for child in evento:
                        nuevo_evento.append(child)
                    self.nuevo_arbol.getroot().append(nuevo_evento)
        else:
            self.nuevo_arbol=self.arbol


    def Cargar_catalogo(self):
        self.catalogo=copy.deepcopy(self.catalogo_respaldo)
        self.eventos_reporte=copy.deepcopy(self.eventos_reporte_respaldo)
        self.resumen=copy.deepcopy(self.resumen_respaldo)
        self.reporte_total=copy.deepcopy(self.reporte_total_respaldo)
        self.arbol=self.arbol_respaldo
        self.Btn_guardar.setEnabled(True)


    def Respaldar_catalogo(self):
        self.catalogo_respaldo= copy.deepcopy(self.catalogo)
        self.eventos_reporte_respaldo=copy.deepcopy(self.eventos_reporte)
        self.resumen_respaldo=copy.deepcopy(self.resumen)
        self.arbol_respaldo=copy.deepcopy(self.arbol)
        self.reporte_total_respaldo=copy.deepcopy(self.reporte_total)


    def cargar_catalogo_guardado(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Selecciona la carpeta del catálogo (debe terminar en 'Ecuador')")
        if not carpeta:
            return

        if Path(carpeta).name != "Ecuador":
            QMessageBox.critical(self, "Carga no permitida", "Solo puedes cargar catálogos desde una carpeta que se llame exactamente 'Ecuador'.")
            return

        try:
            self.directorio_trabajo=extraer_hasta_directorio(carpeta, 'DIA')
            self.lbl_directorio.setText(self.directorio_trabajo)

            lista_archivos = os.listdir(carpeta)
            base = None

            for archivo in lista_archivos:
                if archivo.endswith("_cat.csv"):
                    base = archivo[:-8]  # Quitar '_cat.csv'
                    break

            if not base:
                QMessageBox.warning(self, "Error", "No se encontró ningún archivo *_cat.csv en la carpeta.")
                return

            # Determinar el rango de fechas según el nombre del archivo
            try:
                if " a " in base:
                    # Formato: 01_01_2001 a 31_12_2024
                    fecha_str_ini, _, fecha_str_fin = base.partition(" a ")
                    self.fecha_ini = datetime.strptime(fecha_str_ini, "%d_%m_%Y")
                    self.fecha_fin = datetime.strptime(fecha_str_fin, "%d_%m_%Y")
                elif base.isdigit() and len(base) == 4:
                    # Formato: 2010
                    anio = int(base)
                    self.fecha_ini = datetime(anio, 1, 1)
                    self.fecha_fin = datetime(anio, 12, 31)
                else:
                    # Intentar parsear formato tipo "Enero del 2025"
                    meses = {
                        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
                        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
                    }
                    base_minus = base.lower()
                    for mes_nombre, mes_num in meses.items():
                        if mes_nombre in base_minus:
                            anio = int(''.join(filter(str.isdigit, base_minus)))
                            self.fecha_ini = datetime(anio, mes_num, 1)
                            ultimo_dia = calendar.monthrange(anio, mes_num)[1]
                            self.fecha_fin = datetime(anio, mes_num, ultimo_dia)
                            break
                    else:
                        raise ValueError(f"No se pudo interpretar la fecha desde el nombre del archivo: {base}")
            except Exception as e:
                raise ValueError(f"No se pudieron extraer fechas del nombre base '{base}': {e}")

            # Selección de zona 'Ecuador' en el combo
            index_ecuador = self.cmbx_zona.findText("Ecuador")
            if index_ecuador != -1:
                self.cmbx_zona.setCurrentIndex(index_ecuador)
            else:
                QMessageBox.warning(self, "Aviso", "No se encontró 'Ecuador' en la lista de zonas.")
                return

            self.periodo_reporte, self.directorio_reporte, self.archivo_reporte = obtener_datos_reporte(
                self.fecha_ini, self.fecha_fin, self.directorio_trabajo, "Ecuador"
            )

            # Cargar archivos asociados
            self.catalogo = lectura_archivo(os.path.join(carpeta, base + "_cat.csv"))
            self.eventos_reporte = lectura_archivo(os.path.join(carpeta, base + "_rep.csv"))
            self.resumen = lectura_archivo(os.path.join(carpeta, base + "_res.csv"))
            self.reporte_total = lectura_archivo(os.path.join(carpeta, base + "_rep_total.csv"))
            self.arbol = ET.parse(os.path.join(carpeta, base + ".xml"))
            self.raiz = self.arbol.getroot()
            self.Respaldar_catalogo()
            self.dateEdit_ini.setDate(QDate(self.fecha_ini.year, self.fecha_ini.month, self.fecha_ini.day))
            self.dateEdit_fin.setDate(QDate(self.fecha_fin.year, self.fecha_fin.month, self.fecha_fin.day))
            self.Btn_guardar.setEnabled(True)
            QMessageBox.information(
                self,
                "Catálogo cargado",
                f"Catálogo cargado correctamente para el periodo:\n{self.periodo_reporte}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el catálogo:\n{str(e)}")


    def acumular_solo_catalogo(self):
        if not self.ck_box_historico.isChecked():
            return  # Si no está activado el checkbox, no se ejecuta nada

        try:
            # Obtener fechas del usuario desde los widgets
            fecha_ini = self.dateEdit_ini_cat.date().toPyDate()
            fecha_fin = self.dateEdit_fin_cat.date().toPyDate()

            # Inicializar catálogo con la cabecera estándar
            self.catalogo = [["Id", "año", "mes", "día", "hora", "min", "seg", "lat", "long", "prof", "rms",
                              "e-x", "e-y", "e-0", "e-z", "Mag", "Tipo Mag", "Fuente", "ruta", "Ubicación"]]

            anios_procesados = set()
            fecha_actual = fecha_ini

            while fecha_actual <= fecha_fin:
                anio = fecha_actual.strftime("%Y")

                # Si ya se procesó este año, continuar
                if anio in anios_procesados:
                    fecha_actual += timedelta(days=1)
                    continue

                # Buscar si existe el archivo resumen anual: DIA/AAAA/reportes/Ecuador/AAAA_cat.csv
                archivo_anual = os.path.join(
                    self.directorio_trabajo, anio, "reportes", "Ecuador", f"{anio}_cat.csv"
                )

                if os.path.isfile(archivo_anual):
                    try:
                        datos = lectura_archivo(archivo_anual)
                        if datos and datos[0][0] == "Id":
                            self.catalogo.extend(datos[1:])  # Ignorar cabecera
                        else:
                            self.catalogo.extend(datos)
                        print(f"✓ Se cargó archivo anual: {archivo_anual}")
                    except Exception as e:
                        print(f"Error leyendo {archivo_anual}: {e}")

                    # Marcar año como procesado y saltar al siguiente
                    anios_procesados.add(anio)
                    fecha_actual = datetime(int(anio) + 1, 1, 1)
                    continue

                # Si no existe archivo resumen, intentar día por día
                mes = fecha_actual.strftime("%Y_%m")
                dia = fecha_actual.strftime("%Y_%m_%d")
                nombre_archivo = fecha_actual.strftime("%y%m%d") + "000000_cat.csv"
                ruta_archivo = os.path.join(
                    self.directorio_trabajo, anio, mes, dia, nombre_archivo
                )

                if os.path.isfile(ruta_archivo):
                    try:
                        datos = lectura_archivo(ruta_archivo)
                        if datos and datos[0][0] == "Id":
                            self.catalogo.extend(datos[1:])
                        else:
                            self.catalogo.extend(datos)
                    except Exception as e:
                        print(f"Error al leer archivo {ruta_archivo}: {e}")
                else:
                    print(f"Archivo no encontrado: {ruta_archivo}")

                fecha_actual += timedelta(days=1)

            # Respaldar los datos cargados
            self.Respaldar_catalogo()

            # Mostrar mensaje
            QMessageBox.information(
                self,
                "Catálogo histórico acumulado",
                f"Se acumularon eventos desde {fecha_ini.strftime('%d/%m/%Y')} hasta {fecha_fin.strftime('%d/%m/%Y')}.\n"
                f"Total de eventos cargados: {len(self.catalogo) - 1}"
            )

            # Habilitar botón para exportar
            self.Btn_guardar.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Ocurrió un error al acumular el catálogo:\n{str(e)}"
            )

    def abrir_ventana_estaciones(self):
        self.ventana_estaciones = VentanaEstaciones(self.parametros)
        self.ventana_estaciones.btn_ejecutar.clicked.connect(self.ejecutar_con_estaciones)
        self.ventana_estaciones.exec_()



    def ejecutar_con_estaciones(self):
        self.estaciones_seleccionadas = self.ventana_estaciones.obtener_estaciones_seleccionadas()
        self.ventana_estaciones.close()

        self.reporte = []

        for evento_catalogo in self.catalogo[1:]:  # Omitimos cabecera
            evento_id = evento_catalogo[IDX_EVENTO]  # Ej: "240505_153312.sis"
            evento_sin_extension = evento_id[:-4]  # "240505_153312"
            evento_sin_guion = evento_sin_extension.replace("_", "")  # "240505153312"

            ruta_evento = os.path.join(self.directorio_trabajo, evento_sin_guion)
            directorios = obtener_directorios(ruta_evento)

            self.eventos = lectura_archivo(directorios['archivo_csv'])
            print(directorios['archivo_csv'])

            for evento in self.eventos[1:]:
                if evento[1] == evento_id:
                    linea_evento = [evento_id]
                    for idx_estacion in self.estaciones_seleccionadas:
                        if evento[idx_estacion + 3] != "-":
                            codigo = self.parametros['CODIGO'][idx_estacion]
                            nombre_mseed = codigo + directorios['sufijo_mseed']
                            linea_evento.append(nombre_mseed)
                    if len(linea_evento) > 1:
                        self.reporte.append(linea_evento)
                    break  # Ya encontramos el evento
                        
        # Mostrar resultado final
        print("📄 Contenido de self.reporte:")
        for linea in self.reporte:
            print(linea)




    def Salir_(self):
        print('Saliendo desde boton:')
        self.close()

    def limpiar_estado(self):
        """Limpia figuras, visores, hilos, timers, etc., antes de cerrar."""
        try:
            if hasattr(self, 'canvas'):
                self.canvas.deleteLater()
                self.canvas = None
            if hasattr(self, 'visor'):
                self.visor.clf()
                self.visor = None
            # Limpieza de listas, buffers o datos
            if hasattr(self, 'stLeido'):
                del self.stLeido
            if hasattr(self, 'lista_eventos'):
                self.lista_eventos.clear()
        except Exception as e:
            print(f"Error en limpieza de Reporte_diario: {e}")


    def closeEvent(self, event):
        """
        Emite la señal de cerrado para notificar a la ventana principal y realiza limpieza.
        """
        print("Saliendo de Reporte  - closeEvent ejecutado")
    
        # Limpiar estado antes de emitir señal
        self.limpiar_estado()
        
        # Emitir señal una sola vez
        self.cerrado.emit()
    
        # Aceptar el evento de cierre
        event.accept()
    
        print("closeEvent completado - señal cerrado emitida")




        
