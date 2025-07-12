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

archivos_cambios=['archivo_csv',    #Cambio de nombre y contenido
           'archivo_reporte',       #Cambio de nombre y contenido
           'archivo_catalogo',      #Cambio de nombre y contenido
           'archivo_auxiliar',      #Cambio de nombre y contenido
           'archivo_resumen',       #Cambio de nombre
           'archivo_responsables',  #Cambio de nombre
           'archivo_tiempos',       #Cambio de nombre 
           'archivo_marcas',        #Cambio de nombre 
           'archivo_procesamiento', #Cambio de nombre
           'archivo_comportamiento',#Cambio de nombre
           'archivo_reporte_dia',   #Cambio de nombre
           'archivo_estaciones',    #Cambio de nombre
           'archivo_xml'            #Cambio de nombre y contenido
            ]


directorios_cambios=['Directorio_dia']       #Cambio de nombre y contenido


columna_cambiar=[1,1,18,1]







import re
import xml.etree.ElementTree as ET


def actualizar_rutas_en_archivo_xml(archivo_xml,
                                    prefijo: str = "20") -> None:
    """
    Lee un archivo XML y antepone '20' al texto de cada etiqueta <ruta>
    que esté en formato AAMMDD_hhmmss.sis.  Si la ruta ya es del tipo
    AAAAMMDD_hhmmss.sis (año de 4 dígitos) no se modifica.

    Parámetros
    ----------
    archivo_xml : str | pathlib.Path
        Ruta del XML a procesar.
    prefijo : str, opcional
        Texto que se antepondrá (por defecto '20').

    Retorna
    -------
    None
    """
    # ------------------------------------------------------------------ #
    ruta_xml = Path(archivo_xml).expanduser().resolve()
    if not ruta_xml.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_xml}")

    with ruta_xml.open(encoding="utf-8") as f_xml:
        contenido = f_xml.read()

    try:
        raiz = ET.fromstring(contenido)
    except ET.ParseError as exc:
        raise ValueError(f"XML mal formado en {ruta_xml}: {exc}") from exc

    # -------- patrones para 6 dígitos y 8 dígitos --------------------- #
    patron_6d = re.compile(r"^\d{6}_\d{6}\.sis$", re.IGNORECASE)
    patron_8d = re.compile(r"^\d{8}_\d{6}\.sis$", re.IGNORECASE)

    total_modificadas = 0
    for etiqueta_ruta in raiz.iter("ruta"):
        texto = etiqueta_ruta.text or ""
        if patron_8d.match(texto):
            # Formato AAAAMMDD_hhmmss.sis → no hacer nada
            continue
        if patron_6d.match(texto) and not texto.startswith(prefijo):
            etiqueta_ruta.text = f"{prefijo}{texto}"
            total_modificadas += 1

    # ------------------- indentado para legibilidad ------------------- #
    def _indentar(elem: ET.Element, nivel: int = 0) -> None:
        salto = "\n" + ("    " * nivel)
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = salto + "    "
            for subelem in elem:
                _indentar(subelem, nivel + 1)
            if not subelem.tail or not subelem.tail.strip():
                subelem.tail = salto
        if nivel and (not elem.tail or not elem.tail.strip()):
            elem.tail = salto

    _indentar(raiz)

    # --------------------- sobrescribir archivo ----------------------- #
    with ruta_xml.open("w", encoding="utf-8") as f_out:
        f_out.write(ET.tostring(raiz, encoding="unicode"))

    print(f"Se actualizaron {total_modificadas} etiquetas <ruta> en {ruta_xml}.")


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
        self.btn_salir.clicked.connect(self.salir)

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
            nombre_largo = fecha_actual.strftime("%Y%m%d000000")
            self.archivo=os.path.join(self.directorio_trabajo, nombre_corto)
            self.archivo_largo=os.path.join(self.directorio_trabajo, nombre_largo)
            directorios = obtener_directorios(self.archivo)
            directorios_largo=obtener_directorios(self.archivo_largo)
            for i,archivo_cambiar in enumerate(archivos_cambios):
                if not os.path.isfile(directorios[archivo_cambiar]):
                    continue
                os.rename(directorios[archivo_cambiar],directorios_largo[archivo_cambiar])
                if i<4:
                    variables=lectura_archivo(directorios_largo[archivo_cambiar])
                    for variable in variables:
                        if variable[columna_cambiar[i]][-3:]=='sis':
                            if variable[columna_cambiar[i]][:4]!=directorios['anio']:
                                variable[columna_cambiar[i]]=directorios['anio'][:2]+variable[columna_cambiar[i]]
                    escritura_archivo(directorios_largo[archivo_cambiar],variables)
            actualizar_rutas_en_archivo_xml(directorios_largo[archivo_cambiar])
            for directorio_cambiar in directorios_cambios:
                archivos = sorted(f for f in os.listdir(directorios[directorio_cambiar]) if f.lower().endswith((".sis", ".fas")))
                for archivo in archivos:
                    if archivo[:4]!=directorios['anio']:
                        archivo_nuevo=directorios['anio']+archivo[2:]
                        os.rename(os.path.join(directorios[directorio_cambiar], archivo),os.path.join(directorios[directorio_cambiar], archivo_nuevo))
            fecha_actual += timedelta(days=1)

        QMessageBox.information(self, "Proceso completado",
                                f"Se han procesado {total_archivos_procesados} archivos.")

    def salir(self):
        self.close()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())