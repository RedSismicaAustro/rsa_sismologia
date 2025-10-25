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
from PyQt5 import QtWidgets,QtCore
from metodos_rsa import (lectura_archivo)

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
from PyQt5.QtCore import pyqtSignal
 
class Inicio_proceso(QMainWindow):
    cerrado = pyqtSignal()  # señal que se emitire al cerrar
    inicializado = pyqtSignal(str, str, str,str)  # archivo, directorio_trabajo, responsable
    def __init__(self, directorio_trabajo, responsable, periodo,parent=None):
        super().__init__()
        self.setWindowTitle('Inizializacion de día')
        # Configurar el layout principal
        layout_principal = QHBoxLayout()
        # Panel izquierdo
        panel_izquierdo = QVBoxLayout()

        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src",  "ui", 'inicio.ui')
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
        self.setWindowTitle("INICIO DE DIA")

        self.Btn_Iniciar.clicked.connect(self.Iniciar)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)



        ruta_csv =  os.path.join(ruta_proyecto, "datos", "responsables.csv")
        ruta_csv = os.path.abspath(ruta_csv)
        datos=lectura_archivo(ruta_csv)
        lista_resp = [sublista[0] for sublista in datos]
        self.cmbx_resposables.addItems(lista_resp)

        horario=("00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00")
        self.cmbx_periodo.addItems(horario)

        self.parametros=parametros_estaciones()#(nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual
        self.dia.clicked[QtCore.QDate].connect(self.showDate)
        self.cmbx_periodo.currentTextChanged.connect(self.cambio_periodo)
        self.cmbx_resposables.currentTextChanged.connect(self.cambio_responsable)
        #self.directorio_trabajo='G:\Mi unidad\DIA\\' #self.directorio_trabajo=dir_trabajo[0:aux-9]
        self.directorio_trabajo=directorio_trabajo
        self.responsable=responsable
        self.periodo=periodo
        self.showDate(d)

        # Conectar las señales en el __init__ de tu ventana
        self.radioButton_diario.toggled.connect(self.seleccionar_diario)
        self.radioButton_periodo.toggled.connect(self.seleccionar_periodo)
        self.cmbx_periodo.setCurrentIndex(1)
        

    # Métodos asociados
    def seleccionar_diario(self, estado):
            if estado:
                self.dia.setEnabled(True)
                self.cmbx_periodo.clear()
                self.cmbx_periodo.addItems(("00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00"))
                self.cmbx_periodo.setEnabled(True)
                self.cmbx_periodo.setCurrentIndex(0)
                

    def seleccionar_periodo(self, estado):
            if estado:
                self.dia.setEnabled(False)
                self.cmbx_periodo.clear()
                self.cmbx_periodo.addItem(" ")
                self.cmbx_periodo.setEnabled(False)
                self.cmbx_periodo.setCurrentIndex(4)


    def Iniciar(self):
        # Actualizar fecha y archivo
        self.date = self.dia.selectedDate()
        self.archivo = os.path.join(self.directorio_trabajo, self.date.toString('yyyyMMdd000000'))

        # Obtener responsable
        self.responsable = self.cmbx_resposables.currentText()

        # Emitir señal con la información
        self.inicializado.emit(self.archivo, self.directorio_trabajo, self.responsable,self.periodo)

        # Opcional: cerrar ventana luego de iniciar
        self.close()


    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath
        self.showDate(self.date)

    def visor_limpiar_completo(self):
        """Antes de cada gráfico nuevo"""
        self.visor.clear()
        self.visor.clf()
        # AGREGAAR ESTO:
        plt.close(self.visor)  # Liberar figura de matplotlib completamente

    def limpiar_estado(self):
        """Limpia figuras, visores, hilos, timers, etc., antes de cerrar."""
        try:
            if hasattr(self, 'canvas') and self.canvas is not None:
                self.canvas.deleteLater()
                self.canvas = None

            if hasattr(self, 'visor') and self.visor is not None:
                self.visor.clf()
                self.visor = None

 
        except Exception as e:
            print(f"Error en limpieza de Inicio: {e}")


    def closeEvent(self, event):
        """
        Emite la señal de cerrado para notificar a la ventana principal y realiza limpieza si es necesario.
        """
        print("Cerrando inicio")
        self.visor_limpiar_completo()
        self.limpiar_estado()
        print(self.archivo, self.directorio_trabajo, self.responsable,self.periodo)
        self.inicializado.emit(self.archivo, self.directorio_trabajo, self.responsable,self.periodo)
        self.cerrado.emit()
        super().closeEvent(event)

    def showDate(self, date):#Es como inicializar el dìa
        self.date=date
        self.archivo=self.directorio_trabajo+date.toString('yyyyMMdd000000')
        self.desplegar_mensaje()

    def cambio_periodo(self, texto):
        # asignar el valor del combobox a self.periodo
        self.periodo = texto
        self.desplegar_mensaje()

    def cambio_responsable(self, texto):
        # asignar el valor del combobox a self.periodo
        self.responsable = texto
        self.desplegar_mensaje()        
            
    def desplegar_mensaje(self):
        
        if self.periodo=='':
            mensaje = (
                "<b>DIA:</b><br>" + " PERIODO " +
                "<br><b>DIRECTORIO DE TRABAJO:</b><br>" + str(self.directorio_trabajo)+
                "<br><b>RESPONSABLE:</b><br>" + str(self.responsable)+
                "<br><b>PERIODO:</b><br>" + str(self.periodo)
                )
            
        else:
            mensaje = (
                "<b>DIA:</b><br>" + self.date.toString("yyyy\\MM\\dd") +
                "<br><b>DIRECTORIO DE TRABAJO:</b><br>" + str(self.directorio_trabajo)+
                "<br><b>RESPONSABLE:</b><br>" + str(self.responsable)+
                "<br><b>PERIODO:</b><br>" + str(self.periodo)
                )

        self.mensajes.setHtml(mensaje)
        
        

