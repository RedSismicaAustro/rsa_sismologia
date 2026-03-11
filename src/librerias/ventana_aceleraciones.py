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

from PyQt5.QtWidgets import QDialog, QLabel, QCheckBox
from PyQt5 import uic
import matplotlib.pyplot as plt

from rsa_dominio import correccion
from rsa_io import leer_mseed

from metodos_graficos_rsa import impresion_reporte_acelerograma
from metodos_gestion import parametros_estaciones,obtener_directorios
class Subventana_aceleraciones(QDialog):
    def __init__(self, archivo, catalogo, evento):
        super().__init__()
        self.archivo = archivo
        self.evento = evento
        self.catalogo_escogido = catalogo
        self.parametros = parametros_estaciones()
        self.trCanal = leer_mseed(archivo, 1)
        self.hab_canal = self.parametros['HAB_CANAL']
        self.nombre_canal = self.parametros['CODIGO']
        self.numero_estaciones = len(self.hab_canal)
        QDialog.__init__(self)

        ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", "estaciones.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        self.ck_box_disp_canal = {}
        self.ck_box_hab_canal = {}
        self.lbl_nombre = {}
        self.lbl_codigo = {}

        nombre_canal_total_ = self.parametros['NOMBRE']
        nombre_canal = self.parametros['CODIGO']

        self.lbl_grafico = QLabel("PLOT", self)
        self.lbl_grafico.setGeometry(246, 20, 51, 16)

        self.estaciones_eventos = []
        for i in range(0, len(self.parametros['CODIGO'])):
            if self.trCanal[i] != []:
                self.estaciones_eventos.append(i)

        for i in range(0, len(self.estaciones_eventos)):
            canal_ = self.estaciones_eventos[i]
            self.lbl_nombre[i] = QLabel(nombre_canal_total_[canal_], self)
            self.lbl_nombre[i].setGeometry(15, i * 25 + 35, 150, 24)
            self.lbl_codigo[i] = QLabel(nombre_canal[canal_], self)
            self.lbl_codigo[i].setGeometry(150, i * 25 + 35, 150, 24)
            self.ck_box_hab_canal[i] = QCheckBox(self)
            self.ck_box_hab_canal[i].setGeometry(210, i * 25 + 35, 150, 24)
            self.ck_box_hab_canal[i].setChecked(False)

    def closeEvent(self, event):
        directorios_ = obtener_directorios(self.archivo)
        nombre_canal_ = self.parametros['CODIGO']
        directorio_acel = directorios_['Directorio_acelerogramas'] + '/'
        try:
            path = Path(directorio_acel)
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        for k in range(len(self.estaciones_eventos)):
            if self.ck_box_hab_canal[k].checkState() == 2:
                archivo_acel = (
                    directorio_acel
                    + nombre_canal_[self.estaciones_eventos[k]]
                    + "_"
                    + self.evento[1][0:-4]
                    + "_rep.pdf"
                )
                seniales = correccion(self.trCanal[self.estaciones_eventos[k]][2], 2 ** 18 / 980)
                trCanal = self.trCanal[self.estaciones_eventos[k]]
                impresion_reporte_acelerograma(
                    archivo_acel, trCanal, self.estaciones_eventos[k], self.catalogo_escogido, 0
                )
                fig, ax = plt.subplots(4)
                ax[0].plot(trCanal[0].data)
                ax[1].plot(seniales[0])
                ax[2].plot(seniales[1])
                ax[3].plot(seniales[2])
                plt.show()
