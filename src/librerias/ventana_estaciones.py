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

from metodos_gestion import parametros_estaciones
import matplotlib.pyplot as plt
import numpy as np
from PyQt5 import uic
from PyQt5.QtWidgets import (QDialog,QLabel,QCheckBox,QComboBox,QLineEdit,QSpinBox,QPushButton)


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
        uic.loadUi("estaciones.ui",self)
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
    def Salir_(self):
        self.destroy()

