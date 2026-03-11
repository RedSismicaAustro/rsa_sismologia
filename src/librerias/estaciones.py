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
from PyQt5.QtWidgets import (QLabel, QCheckBox)
from PyQt5 import uic
from metodos_gestion import parametros_estaciones
datos_sismo={}
from PyQt5.QtWidgets import (QDialog,QSpinBox)
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

