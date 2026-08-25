import sys
import os
from pathlib import Path
from datetime import datetime

def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
if not ruta_proyecto:
    ruta_proyecto = os.path.abspath(os.path.join(ruta_librerias, '..', '..'))

ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog
)
from PyQt5 import uic, QtCore, QtWidgets
from PyQt5.QtCore import Qt, QDate, pyqtSignal

from metodos_rsa import lectura_archivo
from metodos_gestion import parametros_estaciones
from panel_estado import PanelEstadoJornada


class Inicio_proceso(QMainWindow):
    cerrado = pyqtSignal()
    inicializado = pyqtSignal(str, str, str, str)  # archivo, directorio_trabajo, responsable, periodo

    def __init__(self, directorio_trabajo, responsable, periodo, parent=None):
        super().__init__(parent)
        self.setWindowTitle('INICIALIZACIÓN DE DÍA - RSA')
        self.fue_inicializado = False

        # Configurar layout principal horizontal
        layout_principal = QHBoxLayout()

        # Cargar la interfaz desde inicio.ui
        ruta_ui = os.path.join(ruta_proyecto, "src", "ui", "inicio.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        # Extraer el widget central original de inicio.ui para montarlo a la izquierda
        widget_formulario = self.centralWidget()
        widget_formulario.setFixedWidth(280)

        # Asignar layout vertical al contenedor para acomodar cmbx_resposables_2
        layout_form = QVBoxLayout(widget_formulario)
        layout_form.setContentsMargins(2, 2, 2, 2)
        layout_form.addWidget(self.cmbx_resposables_2)

        # Estilo para el agrupador de parámetros de inicio
        self.cmbx_resposables_2.setTitle("PARÁMETROS DEL DÍA")
        self.cmbx_resposables_2.setStyleSheet("""
            QGroupBox#cmbx_resposables_2 {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
                font-weight: bold;
                color: #1a237e;
                border: 1px solid #b0bec5;
                border-radius: 6px;
                margin-top: 14px;
                padding-top: 12px;
                background-color: #fafafa;
            }
            QGroupBox#cmbx_resposables_2::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 6px;
                background-color: #fafafa;
            }
        """)

        layout_principal.addWidget(widget_formulario, 0)

        # Panel derecho: Dashboard Nativo de Estado de Jornada
        self.panel_estado = PanelEstadoJornada(self)
        layout_principal.addWidget(self.panel_estado, 1)

        # Establecer layout central contenedor definitivo
        widget_contenedor_total = QWidget(self)
        widget_contenedor_total.setLayout(layout_principal)
        self.setCentralWidget(widget_contenedor_total)

        # Conexión de botones de inicio.ui
        self.Btn_Iniciar.clicked.connect(self.Iniciar)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)

        # Cargar lista de responsables desde CSV
        ruta_csv_resp = os.path.join(ruta_proyecto, "datos", "responsables.csv")
        datos = lectura_archivo(ruta_csv_resp) or []
        lista_resp = [sublista[0] for sublista in datos if sublista]
        self.cmbx_resposables.clear()
        self.cmbx_resposables.addItems(lista_resp)

        # Obtener parámetros de estaciones
        self.parametros = parametros_estaciones()

        # Configurar variables recibidas
        self.directorio_trabajo = directorio_trabajo
        self.responsable = responsable
        self.periodo = periodo or "00:00 - 12:00"

        # Inicializar fecha y archivo por defecto con la fecha del sistema
        d = datetime.today()
        self.date = QDate(d.year, d.month, d.day)
        self.archivo = os.path.join(self.directorio_trabajo, self.date.toString('yyyyMMdd000000'))

        # Conectar señales de widgets
        self.dia.clicked[QtCore.QDate].connect(self.showDate)
        self.cmbx_periodo.currentTextChanged.connect(self.cambio_periodo)
        self.cmbx_resposables.currentTextChanged.connect(self.cambio_responsable)
        self.radioButton_diario.toggled.connect(self.seleccionar_diario)
        self.radioButton_periodo.toggled.connect(self.seleccionar_periodo)

        # Configurar selección inicial por defecto: Modo Diario con fecha actual
        self.dia.setSelectedDate(self.date)
        self.radioButton_diario.setChecked(True)
        self.seleccionar_diario(True)
        self.showDate(self.date)

    def seleccionar_diario(self, estado):
        if estado:
            self.dia.setEnabled(True)
            self.cmbx_periodo.blockSignals(True)
            self.cmbx_periodo.clear()
            self.cmbx_periodo.addItems(("00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00"))
            self.cmbx_periodo.setEnabled(True)
            self.cmbx_periodo.setCurrentIndex(0)
            self.cmbx_periodo.blockSignals(False)
            self.periodo = "00:00 - 12:00"
            self.desplegar_mensaje()

    def seleccionar_periodo(self, estado):
        if estado:
            self.dia.setEnabled(False)
            self.cmbx_periodo.blockSignals(True)
            self.cmbx_periodo.clear()
            self.cmbx_periodo.addItem("")
            self.cmbx_periodo.setEnabled(False)
            self.cmbx_periodo.setCurrentIndex(0)
            self.cmbx_periodo.blockSignals(False)
            self.periodo = ""
            self.desplegar_mensaje()

    def Iniciar(self):
        self.date = self.dia.selectedDate()
        self.archivo = os.path.join(self.directorio_trabajo, self.date.toString('yyyyMMdd000000'))
        self.responsable = self.cmbx_resposables.currentText()

        # Determinar período según el radio button activo
        if self.radioButton_diario.isChecked():
            self.periodo = self.cmbx_periodo.currentText() or "00:00 - 12:00"
        else:
            self.periodo = ""

        self.fue_inicializado = True
        self.inicializado.emit(self.archivo, self.directorio_trabajo, self.responsable, self.periodo)
        self.close()

    def seleccionar_drive(self):
        folderpath = QFileDialog.getExistingDirectory(self, 'Seleccionar Directorio Base DIA', self.directorio_trabajo)
        if folderpath:
            if not folderpath.endswith('/') and not folderpath.endswith('\\'):
                folderpath = folderpath + '/'
            self.directorio_trabajo = folderpath
            self.showDate(self.dia.selectedDate())

    def limpiar_estado(self):
        """Limpieza segura de referencias"""
        pass

    def closeEvent(self, event):
        """Si no fue inicializado por el botón, notifica cancelación"""
        if not self.fue_inicializado:
            self.cerrado.emit()
        self.limpiar_estado()
        super().closeEvent(event)

    def showDate(self, date):
        self.date = date
        self.archivo = os.path.join(self.directorio_trabajo, date.toString('yyyyMMdd000000'))
        if self.radioButton_diario.isChecked():
            self.periodo = self.cmbx_periodo.currentText() or "00:00 - 12:00"
        else:
            self.periodo = ""
        self.desplegar_mensaje()
        if hasattr(self, 'panel_estado'):
            self.panel_estado.actualizar_diagnostico(self.archivo, self.directorio_trabajo, self.parametros)

    def cambio_periodo(self, texto):
        if self.radioButton_diario.isChecked():
            self.periodo = texto
        else:
            self.periodo = ""
        self.desplegar_mensaje()

    def cambio_responsable(self, texto):
        self.responsable = texto
        self.desplegar_mensaje()

    def desplegar_mensaje(self):
        fecha_str = self.date.toString("yyyy/MM/dd") if hasattr(self, 'date') and self.date else datetime.today().strftime("%Y/%m/%d")
        if self.radioButton_periodo.isChecked() or self.periodo == '':
            mensaje = (
                "<b>MODO:</b> CONSOLIDADO POR PERÍODO<br>"
                "<b>DIRECTORIO:</b> " + str(self.directorio_trabajo) + "<br>"
                "<b>RESPONSABLE:</b> " + str(self.responsable) + "<br>"
                "<b>PERÍODO:</b> <i>Completo / Acumulado</i>"
            )
        else:
            mensaje = (
                "<b>DÍA:</b> " + fecha_str + "<br>"
                "<b>DIRECTORIO:</b> " + str(self.directorio_trabajo) + "<br>"
                "<b>RESPONSABLE:</b> " + str(self.responsable) + "<br>"
                "<b>TURNO:</b> " + str(self.periodo)
            )

        self.mensajes.setHtml(mensaje)


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ventana = Inicio_proceso('G:/Mi unidad/DIA/', 'RSA', '00:00 - 12:00')
    ventana.show()
    sys.exit(app.exec_())
