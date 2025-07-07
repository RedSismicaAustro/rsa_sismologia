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

# Funciones del proyecto
from metodos_rsa import lectura_archivo, escritura_archivo
from metodos_gestion import obtener_directorios


from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QDateEdit, QFileDialog, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import QDate

import glob
from datetime import datetime, timedelta

archivos_cambios=['archivo_csv',            #Cambio de nombre y contenido
           'archivo_reporte',       #Cambio de nombre y contenido
           'archivo_catalogo',      #Cambio de nombre y contenido
           'archivo_xml',           #Cambio de nombre y contenido
           'archivo_auxiliar',      #Cambio de nombre y contenido
           'archivo_resumen',       #Cambio de nombre
           'archivo_responsables',  #Cambio de nombre
           'archivo_tiempos',       #Cambio de nombre 
           'archivo_marcas',        #Cambio de nombre 
           'archivo_procesamiento', #Cambio de nombre
           'archivo_comportamiento',#Cambio de nombre
           'archivo_reporte_dia'    #Cambio de nombre
          ]

class VentanaPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Renombrar y guardar archivos de sismos")
        self.setMinimumWidth(450)

        self.directorio_trabajo = "G:\Mi unidad\DIA"  # Directorio de trabajo actual

        self.layout = QVBoxLayout(self)

        self.lbl_inicio = QLabel("Fecha de inicio (AAAA-MM-DD):")
        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setDate(QDate.currentDate().addDays(-7))

        self.lbl_fin = QLabel("Fecha de fin (AAAA-MM-DD):")
        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)
        self.fecha_fin.setDate(QDate.currentDate())
        aux="Directorio de trabajo: "+self.directorio_trabajo
        self.lbl_directorio = QLabel(aux)
        self.btn_cambiar_directorio = QPushButton("Cambiar directorio")
        self.btn_cambiar_directorio.clicked.connect(self.seleccionar_directorio_trabajo)

        self.btn_procesar = QPushButton("Procesar archivos")
        self.btn_procesar.clicked.connect(self.procesar_archivos)

        self.btn_salir = QPushButton("Salir")
        self.btn_salir.clicked.connect(QApplication.quit)

        # Layout horizontal para botones inferiores
        self.botones_secundarios = QHBoxLayout()
        self.botones_secundarios.addWidget(self.btn_cambiar_directorio)
        self.botones_secundarios.addWidget(self.btn_salir)

        # Añadir widgets al layout principal
        self.layout.addWidget(self.lbl_inicio)
        self.layout.addWidget(self.fecha_inicio)
        self.layout.addWidget(self.lbl_fin)
        self.layout.addWidget(self.fecha_fin)
        self.layout.addWidget(self.lbl_directorio)
        self.layout.addLayout(self.botones_secundarios)
        self.layout.addWidget(self.btn_procesar)

    def seleccionar_directorio_trabajo(self):
        folderpath = QFileDialog.getExistingDirectory(self, 'Selecciona el directorio de trabajo')
        if folderpath:
            if not folderpath.endswith('/'):
                folderpath += '/'
            self.directorio_trabajo = folderpath
            self.lbl_directorio.setText(f"Directorio de trabajo: {self.directorio_trabajo}")

    def procesar_archivos(self):
        if not self.directorio_trabajo:
            QMessageBox.warning(self, "Error", "Debe seleccionar primero un directorio de trabajo.")
            return

        fecha_ini = self.fecha_inicio.date().toPyDate()
        fecha_fin = self.fecha_fin.date().toPyDate()

        if fecha_ini > fecha_fin:
            QMessageBox.warning(self, "Error", "La fecha de inicio debe ser anterior a la de fin.")
            return

        total_archivos_procesados = 0
        fecha_actual = fecha_ini

        while fecha_actual <= fecha_fin:
            nombre_corto = fecha_actual.strftime("%y%m%d000000")
            self.archivo=os.path.join(self.directorio_trabajo, nombre_corto)
            print(self.archivo)
            directorios = obtener_directorios(self.archivo)
            for archivo_cambiar in archivos_cambios:
                print(directorios[archivo_cambiar])
                #nuevo_nombre = nombre_archivo.replace(nombre_corto, nombre_largo, 1)
                #nueva_ruta = os.path.join(subdirectorio_dia, nuevo_nombre)
                #escritura_archivo(nueva_ruta, datos)
 
            fecha_actual += timedelta(days=1)

        QMessageBox.information(self, "Proceso completado",
                                f"Se han procesado {total_archivos_procesados} archivos.")


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())