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

# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)



from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QMessageBox, QCheckBox)
from PyQt5 import uic
from PyQt5 import QtWidgets
from metodos_rsa import (obtencion_hora,leer_mseed,grafico_evento_int,
                         filtro_evento,extraccion_, diagnostico_memoria)

from metodos_gestion import lectura_eventos,parametros_estaciones,obtener_directorios

datos_sismo={}

from PyQt5.QtWidgets import (QDialog,QSpinBox)

import matplotlib.pyplot as plt
from datetime import datetime
from PyQt5.QtCore import QDate
import csv
#import obspy.realtime #obspy.realtime.signal.offset
import copy

#from obspy import read, UTCDateTime
import gc
import psutil
from obspy.core.trace import Trace
    
class Extraer_evento(QMainWindow):
    def __init__(self, directorio_trabajo, usuario, parent=None):
        super().__init__()
        self.setWindowTitle('Extraer Eventos')
        # Configurar el layout principal
        layout_principal = QHBoxLayout()
        # Panel izquierdo
        panel_izquierdo = QVBoxLayout()


        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src",  "ui", 'Extraer.ui')
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        # Añadir la interfaz cargada al panel izquierdo
        panel_izquierdo.addWidget(self.centralWidget())  # Ahora centralWidget es la UI cargada
        layout_principal.addLayout(panel_izquierdo, 1)
        # Panel derecho (gráfico)
        panel_derecho = QVBoxLayout()
        self.visor = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.visor)
        self.canvas.setParent(self)# Importante para que Qt lo maneje bien
        panel_derecho.addWidget(self.canvas)
        layout_principal.addLayout(panel_derecho, 4)
        # Establecer el layout principal en el widget central
        widget_central = QWidget()
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)
        self.setWindowTitle("EXTRACCION DE EVENTOS")
        self.btn_abrir.clicked.connect(self.Abrir_archivo)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.Btn_eventos.clicked.connect(self.cargar_eventos)
        self.Btn_filtrar.clicked.connect(self.filtrar_evento)
        self.Btn_guardar.clicked.connect(self.guardar_evento)
        self.Btn_recargar.clicked.connect(self.recargar_evento)
        self.Btn_extraer_fijo.clicked.connect(self.cargar_eventos_fijo)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_pagina.clicked.connect(self.cambio_pagina)
        self.Btn_estaciones.clicked.connect(self.verificar_estaciones)
        self.btn_cortar.clicked.connect(self.cortar_evento)
        self.btn_m_6.clicked.connect(self.mas_6_minutos)
        self.btn_p_6.clicked.connect(self.menos_6_minutos)
        self.btn_p__.clicked.connect(self.mas_2_segundos)
        self.btn_p__1.clicked.connect(self.mas_10_segundos)
        self.btn_p__2.clicked.connect(self.mas_30_segundos)
        self.btn_m__.clicked.connect(self.menos_2_segundos)
        self.btn_m__1.clicked.connect(self.menos_10_segundos)
        self.btn_m__2.clicked.connect(self.menos_30_segundos)
        self.btn_m_3.clicked.connect(self.menos_3_minutos)
        self.btn_m_1.clicked.connect(self.menos_1_minutos)
        self.btn_m_0_5.clicked.connect(self.menos_0_5_minutos)
        self.btn_m_0_2.clicked.connect(self.menos_0_2_minutos)
        self.btn_p_3_0.clicked.connect(self.mas_3_minutos)
        self.btn_p_1_0.clicked.connect(self.mas_1_minutos)
        self.btn_p_0_5.clicked.connect(self.mas_0_5_minutos)
        self.btn_p_0_2.clicked.connect(self.mas_0_2_minutos)
        self.cmbx_eventos.activated[str].connect(self.lista_eventos) 
        self.cmbx_resp_1.activated[str].connect(self.habilitacion_) 
        self.sp_Box_finf.valueChanged.connect(self.lista_filtros)
        self.sp_Box_fsup.valueChanged.connect(self.lista_filtros)
        self.sp_Box_orden.valueChanged.connect(self.lista_filtros)
        for i in range(0,60):
            self.comboBox_minuto.addItem(str(i))
            self.comboBox_segundo.addItem(str(i))
            if i<24:
                self.comboBox_hora.addItem(str(i))
        lista_filtros = ["Ruido", "FF", "FC","TELESISMO","SISMO","INDEFINIDO","Evento_local","CONTROL","REVISION"]
        self.Cmb_bx_tipo_evento.addItems(lista_filtros)
        horario=["00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00"]
        self.cmbx_horario.addItems(horario)
        lista_resp=[]

        RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
        RAIZ_PROYECTO=os.path.join(RAIZ_PROYECTO, "..","..")
        ruta_csv =  os.path.join(RAIZ_PROYECTO, "datos", "responsables.csv")
        ruta_csv = os.path.abspath(ruta_csv)

        with open(ruta_csv ,newline='') as f:
            datos=csv.reader(f,delimiter=';',quotechar=';')
            for r in datos:
                lista_resp.append(r[0])
        self.cmbx_resp_1.addItems(lista_resp)
        self.parametros=parametros_estaciones()#(nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
        self.hab_grafico=self.parametros['HAB_GRAFICO']
        self.pagina=0
        self.registro_tiempo=0
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual
        self.dateEdit.setDate(d)    #Conficuración de los datos de fecha en el DataEdit
        self.dateEdit.dateChanged.connect(self.showDate)
        self.directorio_trabajo='G:\Mi unidad\DIA\\' #self.directorio_trabajo=dir_trabajo[0:aux-9]
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.showDate(d)

    def limpiar_visor(self):
        """Limpieza profunda del visor para evitar saturación de memoria."""
        if hasattr(self, 'visor'):
            for ax in list(self.visor.axes):
                self.visor.delaxes(ax)
            self.visor.clf()
            gc.collect()
            self.canvas.draw_idle()
            diagnostico_memoria("Después de limpiar visor")



    def habilitacion_(self, event):
        indice=self.cmbx_resp_1.currentIndex()
        if indice!=0:
            self.btn_abrir.setEnabled(True)
        else:
            self.btn_abrir.setEnabled(False)

    def showDate(self, date):#Es como inicializar el dìa
        self.date=date
        self.archivo=self.directorio_trabajo+date.toString('yyMMdd000000')
        self.estaciones_eventos=[]
        self.filtros_estaciones=[]
        self.bandera_marcas=1
        self.cmbx_eventos.clear()
        self.grupo_evento.setEnabled(False)
        self.grupo_hora_especifica.setEnabled(False)
        self.grupo_carga.setEnabled(False)

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.showDate(self.date)

############################################################
# Médtodo que carga la lista de eventos generados en el archivo puntos.csv
# en el directorio del día procesado.
# EL método lectura_eventos(archivo) da como resultado la lista
    def Abrir_archivo(self):  #Depurado
        directorio_=obtener_directorios(self.archivo)
        self.directorio=directorio_['Directorio_base']
        self.directorio_dia=directorio_['Directorio_dia']
        self.directorio_eventos=directorio_['Directorio_eventos']
        self.directorio_registros=directorio_['Directorio_registros']
        self.fecha_=obtencion_hora(self.archivo) 
        resultado=lectura_eventos(self.archivo)
        mensaje=resultado[0]
        hora_sismo=resultado[1]
        if hora_sismo!=0:
            for i in range(0,len(hora_sismo)):
                h=hora_sismo[i]/(64*3600)
                h_s=str(int(h))
                if int(h)<10:
                    h_s="0"+h_s
                m=(h-int(h))*60
                m_s=str(int(m))
                if int(m)<10:
                    m_s="0"+m_s
                s=int((m-int(m))*60)
                s_s=str(s)
                if s<10:
                    s_s="0"+s_s
                self.cmbx_eventos.addItem("Marca " +str(i+1)+":   "+h_s+":"+m_s+":"+s_s)
            self.grupo_carga.setEnabled(True)
            self.grupo_hora_especifica.setEnabled(True)
            self.grupo_evento.setEnabled(False)
            self.Lbl_Mensajes.setText("Actual: Marca 1. ")               
        self.Lbl_Mensajes_2.setText(mensaje)



    def guardar_evento(self):
        print(f"Guardando evento: {self.archivo}")

        # 🔄 Limpieza del visor antes de guardar
        try:
            print(">> Limpiando visor")
            self.limpiar_visor()
        except Exception as e:
            print("[ERROR] Fallo al limpiar visor:", e)

        # 🧼 Liberar estructuras grandes manualmente
        try:
            print(">> Liberando estructuras internas")
            if hasattr(self, 'trCanal'):
                self.trCanal = None
            if hasattr(self, 'lectura_mseed_dia'):
                self.lectura_mseed_dia = None
            gc.collect()
            diagnostico_memoria("Después de liberar memoria antes de guardar")
        except Exception as e:
            print("[ERROR] al liberar estructuras:", e)

        # ✅ Llamada segura a extraccion_
        try:
            print(">> Llamando a extraccion_()")
            extraccion_(
                self.archivo,
                self.cmbx_eventos.currentIndex() + 1,
                self.Cmb_bx_tipo_evento.currentText(),
                self.t_inicio,
                self.t_final,
                self.estaciones_eventos_total,
                self.estaciones_eventos,
                self.filtros_estaciones
            )
        except Exception as e:
            import traceback
            print("[ERROR] en extraccion_():", e)
            traceback.print_exc()
            QMessageBox.critical(self, "Error al guardar", f"Fallo en la extracción:\n{e}")
            return

        # 🧹 Limpiar visor de nuevo después del guardado
        try:
            self.limpiar_visor()
            diagnostico_memoria("Después de guardar evento")
            self.Lbl_Mensajes_2.setText("Último: Marca " + str(self.cmbx_eventos.currentIndex() + 1))
            self.grupo_evento.setEnabled(False)
        except Exception as e:
            print("[ERROR] al limpiar después de guardar:", e)

        # 🔁 Refrescar estructura de control
        try:
            self.trCanal = None
            self.lectura_mseed_dia = None
            gc.collect()
            diagnostico_memoria("Memoria tras limpieza final")
        except Exception as e:
            print("[ERROR] final al liberar memoria:", e)

        print("Evento guardado correctamente.")



 
    
    def lista_filtros(self, text):
        text="F inf ="+str(self.sp_Box_finf.value())+"F sup ="+str(self.sp_Box_fsup.value())+" orden ="+str(self.sp_Box_orden.value())
        self.Lbl_Mensajes_2.setText(text)

    def cargar_eventos(self):
        print(">> Iniciando carga de eventos")
        
        # Limpiar visor y estructuras anteriores
        self.limpiar_visor()
        self.trCanal = None
        self.lectura_mseed_dia = None
        gc.collect()
        diagnostico_memoria("Después de limpiar estructuras previas")

        # Estado de controles de la GUI
        self.grupo_evento.setEnabled(True)
        self.grupo_guardar.setEnabled(False)
        self.grupo_cortar.setEnabled(True)
        self.grupo_desplazar.setEnabled(False)

        self.bandera_marcas = 1
        self.estaciones_eventos = []
        self.filtros_estaciones = []

        # Verificar archivos mseed existentes
        for i in range(len(self.parametros['CODIGO'])):
            nombreMseed = os.path.join(
                self.directorio_registros,
                self.parametros['CODIGO'][i] + self.fecha_.strftime('_%Y%m%d_%H%M%S.mseed')
            )
            try:
                with open(nombreMseed, 'r'):
                    self.estaciones_eventos.append(self.parametros['NUM_ESTACION'][i])
                    self.filtros_estaciones.append('000000')
            except FileNotFoundError:
                pass

        self.estaciones_eventos_total = self.estaciones_eventos.copy()

        # Obtener tiempo del evento desde el CSV
        hora_sismo = lectura_eventos(self.archivo)[1]
        indice_evento = self.cmbx_eventos.currentIndex()

        tiempo_segundo = hora_sismo[indice_evento] / 64

        self.t_inicio = tiempo_segundo - 420
        self.t_final = tiempo_segundo + 420

        # Leer mseed completo
        print(">> Leyendo mseed desde archivo")
        self.lectura_mseed_dia = leer_mseed(self.archivo, 0)

        # ⚠️ Copia segura del Stream
        self.trCanal = self.lectura_mseed_dia.copy()

        # Determinar tiempo inicial del registro
        for i in range(min(101, len(self.trCanal))):
            traza = self.trCanal[i]
            if isinstance(traza, Trace) and hasattr(traza, 'data') and len(traza.data) > 0:
                self.registro_tiempo = i
                break
 

        # Graficar el evento
        print(">> Graficando evento en visor")
        grafico_evento_int(
            self.visor,
            self.canvas,
            self.trCanal,
            self.t_inicio,
            self.t_final,
            self.estaciones_eventos,
            self.hab_grafico,
            self.bandera_marcas,
            self.pagina
        )

        self.Lbl_Mensajes.setText(f"Actual: Evento {indice_evento + 1}")

        
    def cargar_eventos_fijo(self):
        # Limpia la figura antes de graficar un nuevo evento
        self.visor.clear()  # Agregar esta línea
        self.grupo_evento.setEnabled(True)
        self.grupo_guardar.setEnabled(False)
        self.grupo_cortar.setEnabled(True)
        self.grupo_desplazar.setEnabled(False)
        tiempo_segundo=self.comboBox_hora.currentIndex()*3600+self.comboBox_minuto.currentIndex()*60+self.comboBox_segundo.currentIndex()
        self.lectura_mseed_dia=leer_mseed(self.archivo,0)#leer_mseed(self.archivo,tipo):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        self.bandera_marcas=1
        self.estaciones_eventos=[]
        self.filtros_estaciones=[]
        for i in range(0, len(self.parametros['CODIGO'])):#Verifica todos los archivos MSEED de registro continuo encontrados en la base de datos.
            nombreMseed = self.directorio_registros+"/"+self.parametros['CODIGO'][i]+self.fecha_.strftime('_%Y%m%d_%H%M%S.mseed')
            try:
                auxiliar=open(nombreMseed,'r')
                auxiliar.close
                self.estaciones_eventos.append(self.parametros['NUM_ESTACION'][i])
                self.filtros_estaciones.append('000000')
            except FileNotFoundError:
                pass
        self.estaciones_eventos_total=self.estaciones_eventos
        self.limpiar_visor()
        self.t_inicio=tiempo_segundo-420
        self.t_final=tiempo_segundo+420
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        self.grupo_evento.setEnabled(True)       
    
    def lista_eventos(self, text):
        periodo=[(0,120000),(120000,180000),(180000,240000)]
        self.grupo_evento.setEnabled(False)
        #self.grupo_desplazar.setEnabled(False)
        hora_str=self.cmbx_eventos.currentText()[-8:]
        var_tiempo=int(hora_str[:2]+hora_str[3:5]+hora_str[6:8])
        index_periodo=self.cmbx_horario.currentIndex()
        minimo=periodo[index_periodo][0]
        maximo=periodo[index_periodo][1]
        if var_tiempo>minimo and var_tiempo<maximo:
            self.Btn_eventos.setEnabled(True)
        else:
            self.Btn_eventos.setEnabled(False)
            QMessageBox.information(self, 'Advertencia', 'Periodo incorrecto.')

    def cambio_pagina(self):
        self.limpiar_visor()
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        self.pagina=self.pagina+1
        auxiliar=self.pagina*6
        if auxiliar > len(self.estaciones_eventos):
            self.pagina=0
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_6_minutos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        #tiempo_segundo=hora_sismo[a]/64
        self.limpiar_visor()
        self.t_inicio=self.t_inicio+360
        self.t_final=self.t_final+360
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def menos_6_minutos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        #tiempo_segundo=hora_sismo[a]/64
        self.limpiar_visor()
        self.t_inicio=self.t_inicio-360
        self.t_final=self.t_final-360
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_2_segundos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        #tiempo_segundo=hora_sismo[a]/64
        self.limpiar_visor()
        self.t_inicio=self.t_inicio+2
        self.t_final=self.t_final+2
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_10_segundos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        #tiempo_segundo=hora_sismo[a]/64
        self.limpiar_visor()
        self.t_inicio=self.t_inicio+10
        self.t_final=self.t_final+10
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def mas_30_segundos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        #tiempo_segundo=hora_sismo[a]/64
        self.limpiar_visor()
        self.t_inicio=self.t_inicio+30
        self.t_final=self.t_final+30
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def menos_2_segundos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        #tiempo_segundo=hora_sismo[a]/64
        self.limpiar_visor()
        self.t_inicio=self.t_inicio-2
        self.t_final=self.t_final-2
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def menos_10_segundos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        #tiempo_segundo=hora_sismo[a]/64
        self.limpiar_visor()
        self.t_inicio=self.t_inicio-10
        self.t_final=self.t_final-10
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def menos_30_segundos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        #tiempo_segundo=hora_sismo[a]/64
        self.limpiar_visor()
        self.t_inicio=self.t_inicio-30
        self.t_final=self.t_final-30
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def cortar_evento(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        self.limpiar_visor()
        self.bandera_marcas=0
        self.t_inicio=self.t_inicio+410
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        self.grupo_cortar.setEnabled(False)
        self.grupo_desplazar.setEnabled(True)
        self.grupo_guardar.setEnabled(True)

    def menos_3_minutos(self):
        self.limpiar_visor()
        self.t_final=self.t_final-180
        aux=self.t_final-self.t_inicio
        grafico_evento_int(self.visor,self.canvas,self.trCanal,0,aux,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def menos_1_minutos(self):
        self.limpiar_visor()
        self.t_final=self.t_final-60
        aux=self.t_final-self.t_inicio
        grafico_evento_int(self.visor,self.canvas,self.trCanal,0,aux,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def menos_0_5_minutos(self):
        self.limpiar_visor()
        self.t_final=self.t_final-30
        aux=self.t_final-self.t_inicio
        grafico_evento_int(self.visor,self.canvas,self.trCanal,0,aux,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
    
    def menos_0_2_minutos(self):
        self.limpiar_visor()
        self.t_final=self.t_final-10
        aux=self.t_final-self.t_inicio
        grafico_evento_int(self.visor,self.canvas,self.trCanal,0,aux,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_3_minutos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        self.limpiar_visor()
        self.t_final=self.t_final+180
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_1_minutos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        self.limpiar_visor()
        self.t_final=self.t_final+60
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def mas_0_5_minutos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        self.limpiar_visor()
        self.t_final=self.t_final+30
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
    
    def mas_0_2_minutos(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        self.limpiar_visor()
        self.t_final=self.t_final+10
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def filtrar_evento(self):
        b=self.sp_Box_finf.value()|self.sp_Box_fsup.value()|self.sp_Box_orden.value()
        if b != 0:
            self.limpiar_visor()
            #self.Btn_estaciones.enabled()
            filtro_evento(self.canvas, self.visor, self.trCanal,
              self.sp_Box_finf.value(), self.sp_Box_fsup.value(), self.sp_Box_orden.value(),
              self.t_inicio, self.t_final,
              self.estaciones_eventos, self.hab_grafico,
              self.bandera_marcas, self.pagina,
              self.filtros_estaciones, self.estaciones_eventos_total,
              self.Btn_estaciones.isEnabled())

    def recargar_evento(self):
        self.trCanal=copy.deepcopy(self.lectura_mseed_dia)
        self.limpiar_visor()
        grafico_evento_int(self.visor,self.canvas,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)        

    def verificar_estaciones(self):
        estaciones_(self.hab_grafico,self.estaciones_eventos,self.filtros_estaciones,self).exec_()
        
    def Salir_(self):
        
        message_box = QMessageBox(
            QMessageBox.Question,
            "¡Importante!",
            "  ¿Guardar informe?\nSolo guardar definitivo\n  de 12H, 18H o 24H",
            QMessageBox.Yes | QMessageBox.No ,
            self.window()
        )
        result = message_box.exec_()
        if result == QMessageBox.Yes:
            directorio_=obtener_directorios(self.archivo)#(directorio,directorio_dia,directorio_eventos,directorio_registros)
            directorio=directorio_['Directorio_base']
            aux=len(directorio)
            b=directorio[aux-8:aux-6]+directorio[aux-5:aux-3]+directorio[aux-2:aux]
            nombre_archivo=directorio+"/"+b+"_aux.csv"
            if os.path.exists(nombre_archivo):
                pass
            else:
                nombre_archivo=directorio+"/"+b+"000000.csv"

            archivo_guardar=directorio+"/reportes/"+b+"_tiempos.csv"
            if os.path.exists(archivo_guardar):
                pass


            with open(nombre_archivo,newline='') as lista_csv:
                lista_eventos=csv.reader(lista_csv,delimiter=';',quotechar=';')
                cont_sismo=[0,0,0]
                cont_indefinido=[0,0,0]
                cont_FC=[0,0,0]
                cont_FF=[0,0,0]
                cont_ruido=[0,0,0]
                cont_local=[0,0,0]
                cont_tele=[0,0,0]
                hora_=[12,18,24]
                for evento_ in lista_eventos:
                    h=int(evento_[1][7:9])
                    if h<12:
                        if evento_[2] == 'SISMO':
                            cont_sismo[0]=cont_sismo[0]+1
                        elif evento_[2] == 'FF':
                            cont_FF[0]=cont_FF[0]+1
                        elif evento_[2] == 'FC':
                            cont_FC[0]=cont_FC[0]+1
                        elif evento_[2] == 'INDEFINIDO':
                            cont_indefinido[0]=cont_indefinido[0]+1
                        elif evento_[2] == 'TELESISMO':
                            cont_tele[0]=cont_tele[0]+1
                        elif evento_[2] == 'Evento_local' or evento_[2] == 'CONTROL':
                            cont_local[0]=cont_local[0]+1
                        else:
                            cont_ruido[0]=cont_ruido[0]+1
                    elif h<18 and h>11:
                        if evento_[2] == 'SISMO':
                            cont_sismo[1]=cont_sismo[1]+1
                        elif evento_[2] == 'FF':
                            cont_FF[1]=cont_FF[1]+1
                        elif evento_[2] == 'FC':
                            cont_FC[1]=cont_FC[1]+1
                        elif evento_[2] == 'INDEFINIDO':
                            cont_indefinido[1]=cont_indefinido[1]+1
                        elif evento_[2] == 'TELESISMO':
                            cont_tele[1]=cont_tele[1]+1
                        elif evento_[2] == 'Evento_local'or evento_[2] == 'CONTROL':
                            cont_local[1]=cont_local[1]+1
                        else:
                            cont_ruido[1]=cont_ruido[1]+1
                    else:
                        if evento_[2] == 'SISMO':
                            cont_sismo[2]=cont_sismo[2]+1
                        elif evento_[2] == 'FF':
                            cont_FF[2]=cont_FF[2]+1
                        elif evento_[2] == 'FC':
                            cont_FC[2]=cont_FC[2]+1
                        elif evento_[2] == 'INDEFINIDO':
                            cont_indefinido[2]=cont_indefinido[2]+1
                        elif evento_[2] == 'TELESISMO':
                            cont_tele[2]=cont_tele[2]+1
                        elif evento_[2] == 'Evento_local'or evento_[2] == 'CONTROL':
                            cont_local[2]=cont_local[2]+1
                        else:
                            cont_ruido[2]=cont_ruido[2]+1
            archivo_dato=open(archivo_guardar,'a')            
            for i in (0,1,2):
                total=cont_sismo[i]+cont_FF[i]+cont_FC[i]+cont_indefinido[i]+cont_tele[i]+cont_local[i]+cont_ruido[i]
                if(total!=0):
                    archivo_dato.write(self.cmbx_resp_1.currentText()+";"+str(hora_[i])+"H;"+str(total)+";"+str(cont_sismo[i])+";"+str(cont_FF[i])+";"+str(cont_FC[i])+";"+str(cont_indefinido[i])+";"+str(cont_tele[i])+";"+str(cont_local[i])+";"+str(cont_ruido[i])+'\n')
            archivo_dato.close        
        self.close()


class estaciones_(QDialog):
    def __init__(self, hab_grafico,estaciones_eventos,filtros,parent=None):
        super(estaciones_,self).__init__()
        super().__init__(parent)
        self.parent=parent
        self.parametros=parametros_estaciones()#parametros son los parametros de las estaciones (nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
        self.estaciones_eventos=estaciones_eventos
        self.filtros=filtros
        self.numero_estaciones=len(self.estaciones_eventos)
        self.hab_grafico=hab_grafico
        self.setFixedSize(410, 420)
        QDialog.__init__(self)

        ruta_ui =  os.path.join(ruta_proyecto,"src",  "ui", "secundaria.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        self.ck_box_hab_canal={}
        self.lbl_nombre={}
        self.lbl_codigo={}
        self.ck_box_hab_canal = {}
        self.ck_box_filtro = {}
        nombre_canal_total_=self.parametros['NOMBRE']
        nombre_canal=self.parametros['CODIGO']
        componente_canal=self.parametros['COMPONENTE']


        self.lbl_grafico_0=QLabel("ESTACIONL",self)
        self.lbl_grafico_0.setGeometry(40, 20, 61, 16)  #setGeometry(x, y, width, height)
        self.lbl_grafico_1=QLabel("CÓDIGO",self)
        self.lbl_grafico_1.setGeometry(138, 20, 50, 16)
        self.lbl_grafico_2=QLabel("PLOT",self)
        self.lbl_grafico_2.setGeometry(204, 20, 51, 16)
        self.lbl_grafico_3=QLabel("CANAL",self)
        self.lbl_grafico_3.setGeometry(250, 20, 51, 16)
        self.lbl_grafico_4=QLabel("FILTRO",self)
        self.lbl_grafico_4.setGeometry(312, 20, 51, 16)
        self.lbl_grafico_5=QLabel("ORDEN",self)
        self.lbl_grafico_5.setGeometry(360, 20, 51, 16)
        self.lbl_grafico_6=QLabel("f inf.",self)
        self.lbl_grafico_6.setGeometry(403, 20, 51, 16)
        self.lbl_grafico_7=QLabel("f sup.",self)
        self.lbl_grafico_7.setGeometry(442, 20, 51, 16)

        self.spbox_fil_orden={}
        self.spbox_fil_finf={}
        self.spbox_fil_fsup={}
        self.spbox_canal={}
        lista_estaciones=[]
        for i in range(0, self.numero_estaciones):
            canal_=self.estaciones_eventos[i]
            lista_estaciones.append(nombre_canal_total_[canal_])
            self.lbl_nombre[i]=QLabel(nombre_canal_total_[canal_],self)
            self.lbl_nombre[i].setGeometry(15, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.lbl_codigo[i]=QLabel(nombre_canal[canal_],self)
            self.lbl_codigo[i].setGeometry(150, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.ck_box_hab_canal[i]=QCheckBox(self)
            self.ck_box_hab_canal[i].setGeometry(208, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.ck_box_hab_canal[i].setChecked(True)

            self.spbox_canal[i]=QSpinBox(self)
            self.spbox_canal[i].setGeometry(250, i*25+35, 40, 24)            
            self.spbox_canal[i].setRange(1, 3)
            self.spbox_canal[i].setValue(int(componente_canal[canal_]))
            estacion_i=self.estaciones_eventos[i]
            indice=self.parent.estaciones_eventos_total.index(estacion_i)
            orden=int(self.filtros[indice][0:2])
            f_inf=int(self.filtros[indice][2:4])
            f_sup=int(self.filtros[indice][4:6])
            self.ck_box_filtro[i]=QCheckBox(self)
            self.ck_box_filtro[i].setGeometry(316, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            if orden:
                val_orden=orden
                val_inf=f_inf
                val_sup=f_sup
                self.ck_box_filtro[i].setChecked(True)
            else:
                val_orden=2
                val_inf=1
                val_sup=10
                self.ck_box_filtro[i].setChecked(False)
            self.spbox_fil_orden[i]=QSpinBox(self)
            self.spbox_fil_orden[i].setGeometry(360, i*25+35, 40, 24)
            self.spbox_fil_orden[i].setRange(1, 10)
            self.spbox_fil_orden[i].setValue(val_orden)
            self.spbox_fil_finf[i]=QSpinBox(self)
            self.spbox_fil_finf[i].setGeometry(402, i*25+35, 40, 24)
            self.spbox_fil_finf[i].setRange(1, 10)
            self.spbox_fil_finf[i].setValue(val_inf)
            self.spbox_fil_fsup[i]=QSpinBox(self)
            self.spbox_fil_fsup[i].setGeometry(442, i*25+35, 40, 24)
            self.spbox_fil_fsup[i].setRange(5, 20)
            self.spbox_fil_fsup[i].setValue(val_sup)

            if self.hab_grafico[canal_]=='1':
                self.ck_box_hab_canal[i].setChecked(True)
        self.lbl_todos=QLabel("PLOT TODOS",self)
        self.lbl_todos.setGeometry(140, 435, 150, 24)  #setGeometry(x, y, width, height)
        self.ck_box_todos=QCheckBox(self)
        self.ck_box_todos.setGeometry(210, 437, 150, 24)  #setGeometry(x, y, width, height)
        self.ck_box_todos.setChecked(True)

        self.lbl_filtros=QLabel("FILTRO TODOS",self)
        self.lbl_filtros.setGeometry(131, 455, 150, 24)  #setGeometry(x, y, width, height)
        self.ck_box_filtros=QCheckBox(self)
        self.ck_box_filtros.setGeometry(210, 457, 150, 24)  #setGeometry(x, y, width, height)
        self.ck_box_filtros.setChecked(False)

        self.ck_box_todos.toggled.connect(self.validar)
        self.ck_box_filtros.toggled.connect(self.validar_filtros)


    def validar(self):
        if self.ck_box_todos.checkState()==2:
            for i in range(0, self.numero_estaciones):
                self.ck_box_hab_canal[i].setChecked(True)
        else:
            for i in range(0, self.numero_estaciones):
                self.ck_box_hab_canal[i].setChecked(False)

    def validar_filtros(self):
        if self.ck_box_filtros.checkState()==2:
            for i in range(0, self.numero_estaciones):
                if self.ck_box_hab_canal[i].checkState()==2:
                    self.ck_box_filtro[i].setChecked(True)
        else:
            for i in range(0, self.numero_estaciones):
                self.ck_box_filtro[i].setChecked(False)


    def closeEvent(self, event):
        auxiliar=[]
        for i in range(0, self.numero_estaciones):
            canal_=self.estaciones_eventos[i]
            estacion_i=self.estaciones_eventos[i]
            indice=self.parent.estaciones_eventos_total.index(estacion_i)
            if self.ck_box_hab_canal[i].checkState()==2:
                auxiliar.append(canal_)
            if self.ck_box_filtro[i].checkState()==2:
                orden_i=self.spbox_fil_orden[i].value()
                finf_i=self.spbox_fil_finf[i].value()
                fsup_i=self.spbox_fil_fsup[i].value()
                string_concatenado = f"{orden_i:02}{finf_i:02}{fsup_i:02}"
                self.parent.filtros_estaciones[indice]=string_concatenado
            else:
                self.parent.filtros_estaciones[indice]='000000'
        self.parent.estaciones_eventos=auxiliar
        self.parent.filtros_estaciones=self.filtros
        for i in range(0, self.numero_estaciones):
            canal_=self.estaciones_eventos[i]
            self.parent.componente_canal=str(self.spbox_canal[i])
            if self.ck_box_hab_canal[i].checkState()==2:
                self.parent.hab_grafico[canal_]='1'
            else:
                self.parent.hab_grafico[canal_]='0'
    def Salir_(self):
        self.destroy()


