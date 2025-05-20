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




import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMessageBox, QToolBar, QLabel, QVBoxLayout, QWidget,QGridLayout,QComboBox,QFileDialog,QPushButton
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QTimer, QDateTime,QTime
from PyQt5 import QtWidgets
from subprogramas.fases import VentanaPrincipal as FasesVentana  # Usando la clase para integrar
from subprogramas.extraer_integrado import Extraer_evento
from subprogramas.marcar_eventos import Marcar_evento
from datetime import datetime, timedelta
from metodos_rsa import lectura_archivo
from metodos_gestion import obtener_directorios
import subprocess
import csv

class EstadoProcesamientoSismico(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Colocar la ventana en la esquina superior izquierda y maximizarla
        self.move(0, 0)
        self.showMaximized()

        # Etiqueta para mostrar la fecha y hora actual
        self.lbl_fecha_hora = QLabel()
        self.lbl_fecha_hora.setAlignment(Qt.AlignCenter)
        self.lbl_fecha_hora.setStyleSheet("font-size: 24pt; font-weight: bold;")
        layout.addWidget(self.lbl_fecha_hora)
        
        # Grid para mostrar los indicadores de estado
        self.grid_estado = QGridLayout()
        layout.addLayout(self.grid_estado)

        # Inicializar la cuadrícula de estado
        self.inicializar_grid_estado()

        # Configurar temporizadores
        self.timer_reloj = QTimer(self)
        self.timer_reloj.timeout.connect(self.actualizar_reloj)
        self.timer_reloj.start(1000)  # Actualizar cada segundo

        self.timer_estado = QTimer(self)
        self.timer_estado.timeout.connect(self.actualizar_estado)
        self.timer_estado.start(60000)  # Actualizar cada minuto

        # Actualizar el estado inicial
        self.actualizar_estado()

    def inicializar_grid_estado(self):
        etiquetas = ['00H-12H', '12H-18H', '18H-24H', 'DIARIO', 'ESTACIONES']
        for col, etiqueta in enumerate(etiquetas):
            self.grid_estado.addWidget(QLabel(etiqueta), 0, col + 1, alignment=Qt.AlignCenter)

        for row in range(3):
            fecha = (datetime.now() - timedelta(days=2-row)).strftime('%d/%m/%Y')
            self.grid_estado.addWidget(QLabel(fecha), row + 1, 0, alignment=Qt.AlignRight)

    def actualizar_reloj(self):
        fecha_hora_actual = QDateTime.currentDateTime().toString('dd/MM/yyyy HH:mm:ss')
        self.lbl_fecha_hora.setText(fecha_hora_actual)

    def actualizar_estado(self):
        for row in range(3):
            fecha = datetime.now() - timedelta(days=2-row)
            fecha_str = fecha.strftime('%y%m%d000000')
            self.directorio_trabajo='G:/Mi unidad/DIA/'
            directorios = obtener_directorios(fecha_str)
            archivo_csv=self.directorio_trabajo+directorios['archivo_csv']
            archivo_sis = [fila[1] for fila in lectura_archivo(archivo_csv)]
            archivo_fas = [elemento[:-3] + "fas" if elemento.endswith("sis") else elemento for elemento in archivo_sis]

            periodos = [
                ('000000', '115959'),
                ('120000', '175959'),
                ('180000', '235959')
            ]

            for col, (inicio, fin) in enumerate(periodos):
                archivo_periodo = f"{fecha_str[:8]}{inicio}.sis"
                estado = os.path.exists(os.path.join(directorios['Directorio_dia'], archivo_periodo)) and \
                         os.path.exists(os.path.join(directorios['Directorio_dia'], archivo_fas))
                self.actualizar_celda_estado(row + 1, col + 1, estado)

            # Verificar DIARIO
            archivo_diario = f"{fecha_str[2:8]}000000_rep.pdf"
            estado_diario = os.path.exists(os.path.join(directorios['Directorio_dia'], archivo_diario))
            self.actualizar_celda_estado(row + 1, 4, estado_diario)

            # Verificar ESTACIONES
            
            archivo_estaciones = f"{fecha_str[2:8]}000000_est.csv"
            estado_estaciones = os.path.exists(os.path.join(directorios['Directorio_dia'], archivo_estaciones))
            self.actualizar_celda_estado(row + 1, 5, estado_estaciones)

    def actualizar_celda_estado(self, row, col, estado):
        # Verifica si ya existe un widget en la posición
        item = self.grid_estado.itemAtPosition(row, col)
    
        if item is None:  # Si no hay widget en la celda, creamos uno nuevo
            widget = QLabel()
            self.grid_estado.addWidget(widget, row, col)
        else:
            widget = item.widget()

        # Configura el tamaño y el color del widget según el estado
        widget.setFixedSize(30, 30)
        widget.setStyleSheet(f"background-color: {'green' if estado else 'red'}; border: 1px solid black;")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for row in range(1, 4):
            for col in range(1, 6):
                widget = self.grid_estado.itemAtPosition(row, col).widget()
                if widget:
                    color = QColor(widget.styleSheet().split(':')[1].split(';')[0].strip())
                    painter.setBrush(QBrush(color))
                    painter.drawRect(widget.geometry())

# Función para leer el archivo CSV delimitado por ;
def obtener_responsables(ruta_csv):
    try:
        ruta_completa = os.path.join(os.path.dirname(__file__), ruta_csv)
        
        with open(ruta_completa, newline='', encoding='utf-8') as archivo:
            lector_csv = csv.reader(archivo, delimiter=';')  # Leer con delimitador ;
            responsables = [fila[0] for fila in lector_csv if fila]  # Tomar solo la primera columna
        return responsables
    except FileNotFoundError:
        QMessageBox.critical(None, "Error", f"No se encontró el archivo: {ruta_csv}")
        return []
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Error al leer el archivo CSV: {e}")
        return []


# Clase para la ventana secundaria
class VentanaSecundaria(QWidget):
    def __init__(self, parent, ruta_csv):
        super().__init__()
        self.setWindowTitle("Seleccionar Responsable y Directorio")
        self.setGeometry(100, 100, 500, 400)

        # Guardar referencia al padre (VentanaPrincipal)
        self.parent = parent

        # Layout principal
        layout = QVBoxLayout()

        # Etiqueta del reloj
        self.reloj = QLabel("")
        self.reloj.setFont(QFont("Arial", 14, QFont.Bold))  # Mismo tamaño que el responsable y directorio
        self.reloj.setAlignment(Qt.AlignLeft)  # Alineada a la izquierda
        layout.addWidget(self.reloj)

        # Iniciar el reloj en tiempo real
        self.iniciar_reloj()

        # Leer datos del archivo CSV
        self.responsables = obtener_responsables(ruta_csv)

        # Inicializar la variable 'responsable' con el primer valor del CSV
        self.parent.usuario = self.responsables[0] if self.responsables else "No disponible"

        # Etiqueta para mostrar la información seleccionada (tamaño de letra más grande)
        self.etiqueta_informacion = QLabel(f"Responsable: {self.parent.usuario}\nDirectorio: {self.parent.directorio_trabajo}")
        self.etiqueta_informacion.setFont(QFont("Arial", 14, QFont.Bold))
        self.etiqueta_informacion.setAlignment(Qt.AlignLeft)  # Alineada a la izquierda
        layout.addWidget(self.etiqueta_informacion)

        # Etiqueta: Selecciona un responsable
        etiqueta_responsable = QLabel("Selecciona un responsable:")
        etiqueta_responsable.setFont(QFont("Arial", 10))
        etiqueta_responsable.setAlignment(Qt.AlignLeft)  # Alineada a la izquierda
        layout.addWidget(etiqueta_responsable)

        # Lista desplegable (QComboBox)
        self.combo_responsables = QComboBox()
        self.combo_responsables.addItems(self.responsables)
        self.combo_responsables.setCurrentIndex(0)  # Seleccionar el primer valor por defecto
        self.combo_responsables.setFixedWidth(200)  # Reducir el tamaño de la lista desplegable
        layout.addWidget(self.combo_responsables, alignment=Qt.AlignCenter)  # Centrada

        # Botón para seleccionar un directorio
        boton_seleccionar_directorio = QPushButton("Seleccionar Directorio")
        boton_seleccionar_directorio.setFixedWidth(200)  # Ancho ajustado
        layout.addWidget(boton_seleccionar_directorio, alignment=Qt.AlignCenter)
        boton_seleccionar_directorio.clicked.connect(self.seleccionar_directorio)

        # Botón para salir
        boton_salir = QPushButton("Salir")
        boton_salir.setFixedWidth(200)  # Ancho ajustado
        layout.addWidget(boton_salir, alignment=Qt.AlignCenter)
        boton_salir.clicked.connect(self.cerrar_ventana)

        # Configurar el layout
        self.setLayout(layout)

    def iniciar_reloj(self):
        """Inicia el reloj que se actualiza cada segundo."""
        timer = QTimer(self)
        timer.timeout.connect(self.actualizar_reloj)
        timer.start(1000)  # Actualizar cada segundo
        self.actualizar_reloj()  # Actualización inicial

    def actualizar_reloj(self):
        """Actualiza la etiqueta del reloj con la hora actual."""
        hora_actual = QTime.currentTime().toString("hh:mm:ss")
        self.reloj.setText(f"Hora actual: {hora_actual}")

    def actualizar_informacion(self):
        """Actualiza la etiqueta con el responsable seleccionado y el directorio actual."""
        self.parent.usuario = self.combo_responsables.currentText()
        texto = f"Responsable: {self.parent.usuario}\nDirectorio: {self.parent.directorio_trabajo}"
        self.etiqueta_informacion.setText(texto)

    def seleccionar_directorio(self):
        """Permite seleccionar un directorio y muestra la información en la etiqueta."""
        directorio = QFileDialog.getExistingDirectory(self, "Selecciona un directorio de trabajo")
        if directorio:
            self.parent.directorio_trabajo = directorio  # Actualizar el directorio actual en el padre
            texto = f"Responsable: {self.parent.usuario}\nDirectorio: {self.parent.directorio_trabajo}"
            self.etiqueta_informacion.setText(texto)
            QMessageBox.information(self, "Directorio Seleccionado", f"Directorio seleccionado: {directorio}")
        else:
            QMessageBox.warning(self, "Sin Selección", "No seleccionaste ningún directorio.")

    def cerrar_ventana(self):
        """Cierra la ventana secundaria."""
        self.close()


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana principal
        self.setWindowTitle('PROCESAMIENTO INTEGRADO')
        self.setWindowIcon(QIcon('logo rsa.png'))  # Establecer ícono de la ventana
        self.showMaximized()  # Mostrar la ventana maximizada inicialmente
        self.init_ui()
        self.directorio_trabajo='G:/Mi unidad/DIA/'
        self.usuario='RSA'
        self.periodo='00H-12H'
        
        # Ruta del archivo CSV
        self.RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
        self.RAIZ_PROYECTO=os.path.join(self.RAIZ_PROYECTO, "..")
        ruta_csv =  os.path.join(self.RAIZ_PROYECTO, "datos", "responsables.csv")
        ruta_csv = os.path.abspath(ruta_csv)
        # Crear y mostrar la ventana secundaria al iniciar
        self.ventana_secundaria = VentanaSecundaria(self, ruta_csv)  # Pasar self como referencia al padre
        self.ventana_secundaria.show()
        
        
    def init_ui(self):
        # Crear barra de menú
        self.barra_menu = self.menuBar()
        
        ##########################################################################################
        #  Menú uno: Configuración
        ##########################################################################################
        # Crear menú Configuración
        self.menu_configuracion = self.barra_menu.addMenu('Configuración')


        # Crear acción Directorio de trabajoi
        self.accion_seleccionar_drive = QAction('Directorio trabajo', self)
        self.accion_seleccionar_drive.triggered.connect(self.seleccionar_drive)
        self.menu_configuracion.addAction(self.accion_seleccionar_drive)


        # Crear acción Estaciones
        self.accion_estaciones = QAction('Estaciones', self)
        self.accion_estaciones.triggered.connect(self.estaciones)
        self.menu_configuracion.addAction(self.accion_estaciones)

        # Crear acción Enlaces Digitales
        self.accion_digitales = QAction('Enlaces digitales', self)
        self.accion_digitales.triggered.connect(self.enlaces_digitales)
        self.menu_configuracion.addAction(self.accion_digitales)

        # Ingresar estaciones
        self.accion_ingresar_datos_rg = QAction('Ingresar registro contínuo', self)
        self.accion_ingresar_datos_rg.triggered.connect(self.ingresar_datos_estacion_rg)
        self.menu_configuracion.addAction(self.accion_ingresar_datos_rg)

        # Ingresar eventos de disparo
        self.accion_ingresar_datos_ev = QAction('Ingresar eventos de estaciones', self)
        self.accion_ingresar_datos_ev.triggered.connect(self.ingresar_datos_estacion_ev)
        self.menu_configuracion.addAction(self.accion_ingresar_datos_ev)


        # Crear acción Salir
        self.accion_salir = QAction('Salir', self)
        self.accion_salir.triggered.connect(self.salir)
        self.menu_configuracion.addAction(self.accion_salir)

        ##########################################################################################
        #  Menú dos: procesamiento
        ##########################################################################################

        # Crear menú Procesamiento
        self.menu_procesamiento = self.barra_menu.addMenu('Procesamiento')

        # Crear acción marcar eventos
        self.accion_marcar = QAction('Marcar', self)
        self.accion_marcar.triggered.connect(self.marcar_eventos)
        self.menu_procesamiento.addAction(self.accion_marcar)

        # Crear acción extraer
        self.accion_extraer = QAction('Extraer', self)
        self.accion_extraer.triggered.connect(self.extraer_eventos)
        self.menu_procesamiento.addAction(self.accion_extraer)

        # Crear acción Procesamiento
        self.accion_reextraer = QAction('Procesamiento', self)
        self.accion_reextraer.triggered.connect(self.procesamiento)
        self.menu_procesamiento.addAction(self.accion_reextraer)


        # Crear acción Fases
        self.accion_fases = QAction('Fases', self)
        self.accion_fases.triggered.connect(self.mostrar_fases)
        self.menu_procesamiento.addAction(self.accion_fases)


        # Crear acción Procesamiento 2
        self.accion_reextraer = QAction('Reextraccion', self)
        self.accion_reextraer.triggered.connect(self.reextracion)
        self.menu_procesamiento.addAction(self.accion_reextraer)


        ##########################################################################################
        #  Menú tres: Informes
        ##########################################################################################


        # Crear menú Informes
        self.menu_informes = self.barra_menu.addMenu('Informes')

        # Crear acción infomre diario
        self.accion_reporte_diario = QAction('Reporte diario', self)
        self.accion_reporte_diario.triggered.connect(self.reporte_diario)
        self.menu_informes.addAction(self.accion_reporte_diario)

        # Crear acción informe periodo
        self.accion_reporte_periodo = QAction('Reporte periodo', self)
        self.accion_reporte_periodo.triggered.connect(self.reporte_periodo)
        self.menu_informes.addAction(self.accion_reporte_periodo)

        # Crear acción informe periodo
        self.accion_reporte_enjambre = QAction('Enjambre sísmico', self)
        self.accion_reporte_periodo.triggered.connect(self.reporte_enjambre)
        self.menu_informes.addAction(self.accion_reporte_enjambre)

 
        # Crear acción shapes
        self.accion_shapes = QAction('Shapes', self)
        self.accion_shapes.triggered.connect(self.creacion_shapes)
        self.menu_informes.addAction(self.accion_shapes)

        ##########################################################################################
        #  Menú cuatro: Ayuda
        ##########################################################################################


        # Crear menú Ayuda
        self.menu_ayuda = self.barra_menu.addMenu('Ayuda')

        # Crear acción Acerca de
        self.accion_acerca_de = QAction('Acerca de', self)
        self.accion_acerca_de.triggered.connect(self.acerca_de)
        self.menu_ayuda.addAction(self.accion_acerca_de)

        # Configurar etiqueta de título
        self.barra_herramientas = QToolBar('Barra Principal')
        self.addToolBar(Qt.TopToolBarArea, self.barra_herramientas)

        # Agregar un logo más grande en la barra de herramientas
        self.etiqueta_logo = QLabel()
        self.logo_pixmap = QPixmap('logo rsa.png').scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.etiqueta_logo.setPixmap(self.logo_pixmap)
        self.barra_herramientas.addWidget(self.etiqueta_logo)

        # Agregar un título a la barra de herramientas
        self.etiqueta_titulo = QLabel('PROCESAMIENTO INTEGRADO')
        self.etiqueta_titulo.setFont(QFont('Arial', 16))
        self.barra_herramientas.addWidget(self.etiqueta_titulo)

        # Ajustar el tamaño de la barra de herramientas
        self.barra_herramientas.setIconSize(self.logo_pixmap.size())
        self.barra_herramientas.setMovable(False)

        # Widget central
        self.widget_central = QWidget(self)
        self.setCentralWidget(self.widget_central)
        self.layout_principal = QVBoxLayout(self.widget_central)

        # Agregar el componente de estado de procesamiento sísmico
        #self.estado_sismico = EstadoProcesamientoSismico()
        #self.layout_principal.addWidget(self.estado_sismico)

        ##########################################################################################
        #  Menú uno: Configuración
        ##########################################################################################

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath

 


    def estaciones(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Configuración', 'Configuración de estaciones.')
        self.habilitar_menus()

    def enlaces_digitales(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Configuración', 'Configuración de enlaces digitales.')
        self.habilitar_menus()

    def ingresar_datos_estacion_rg(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Configuración', 'Ingresar datos de estación en registro continuo')
        self.habilitar_menus()

    def ingresar_datos_estacion_ev(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Configuración', 'Ingresar datos de estación en eventos')
        self.habilitar_menus()

    def salir(self):
        self.close()

        ##########################################################################################
        #  Menú dos: procesamiento
        ##########################################################################################


    def mostrar_fases(self):
        # Deshabilitar menús al ejecutar esta acción
        self.deshabilitar_menus()

        # Integrar la funcionalidad de Fases en la ventana principal
        self.fases_ventana = FasesVentana()
        self.setCentralWidget(self.fases_ventana)
        self.fases_ventana.showMaximized()

        # Actualizar el título después de haber cambiado el widget central
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO  -  MARCAR FASES SISMICAS')

        # Conectar el evento de cierre de la ventana de fases para restaurar el título y habilitar los menús
        self.fases_ventana.closeEvent = self.restaurar_estado_sismico

    def marcar_eventos(self):
        # Deshabilitar menús al ejecutar esta acción
        self.deshabilitar_menus()
        # Integrar la funcionalidad de Marcar Eventos en la ventana principal
        self.marcar_evento = Marcar_evento(self.directorio_trabajo)
        self.setCentralWidget(self.marcar_evento)
        self.marcar_evento.showMaximized()
        # Actualizar el título después de haber cambiado el widget central
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO  -  MARCAR EVENTOS EN REGISTRO CONTINUO')
        # Conectar el evento de cierre de la ventana de fases para restaurar el título y habilitar los menús
        self.marcar_evento.closeEvent =  self.restaurar_estado_sismico

    def procesamiento(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Procesamiento', 'Procesamiento')
        self.habilitar_menus()

    def extraer_eventos(self):
        # Deshabilitar menús al ejecutar esta acción
        self.deshabilitar_menus()
        
        # Integrar la funcionalidad de Extraer Eventos en la ventana principal
        self.extraer_eventos = Extraer_evento()
        #self.setCentralWidget(self.extraer_eventos)
        self.extraer_eventos.show()
        self.extraer_eventos.showMaximized()

        # Actualizar el título después de haber cambiado el widget central
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO  -  EXTRACCIÓN DE EVENTOS')

        # Conectar el evento de cierre de la ventana de fases para restaurar el título y habilitar los menús
        self.extraer_eventos.closeEvent = self.restaurar_estado_sismico

    def reextracion(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Procesamiento', 'Reextraccion')
        self.habilitar_menus()

        ##########################################################################################
        #  Menú tres: Informes
        ##########################################################################################


    def reporte_diario(self):
        self.deshabilitar_menus()

        # Método que se ejecuta cuando se selecciona la acción en el menú
        try:
            # Lanza el script Python externo
            subprocess.Popen(['python', 'reporte_diario.py'])
            print("Script ejecutado con éxito.")
        except Exception as e:
            print(f"Error al intentar ejecutar el script: {e}")

        self.habilitar_menus()

    def reporte_periodo(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Informe', 'Reporte Periodo.')
        self.habilitar_menus()

    def reporte_enjambre(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Informe', 'Reporte Enjambre.')
        self.habilitar_menus()


    def creacion_shapes(self):
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Informe', 'Cracion de Shapes')
        self.habilitar_menus()


        ##########################################################################################
        #  Menú cuatro: Ayuda
        ##########################################################################################


    def acerca_de(self):
        QMessageBox.information(self, 'Acerca de', 'Esta es una aplicación de ejemplo de PyQt5.')


        ##########################################################################################
        #  Metodos generales
        ##########################################################################################

    def actualizar_titulo(self, texto):
        self.setWindowTitle(texto)
        texto=texto+'   Directorio por defecto: '+self.directorio_trabajo+'   Usuario: '+self.usuario+'  Periodo: '+self.periodo
        self.etiqueta_titulo.setText(texto)
        self.update()

    def restaurar_estado_sismico(self, event):
        # Restaurar la pantalla principal de EstadoProcesamientoSismico
        #self.setCentralWidget(self.estado_sismico)
        #self.estado_sismico.move(0, 0)
        #self.estado_sismico.showMaximized()
        # Restaurar el título original
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO')
        # Habilitar todos los elementos del menú.
        self.habilitar_menus()
        event.accept()

    def habilitar_menus(self):
        self.menu_configuracion.setEnabled(True)
        self.menu_procesamiento.setEnabled(True)

    def deshabilitar_menus(self):
        # Deshabilitar todos los elementos del menú excepto Ayuda.
        self.menu_configuracion.setEnabled(False)
        self.menu_procesamiento.setEnabled(False)



    def paintEvent(self, event):
        painter = QPainter(self)
        pixmap = QPixmap('logo ucuenca.png')  # Ruta de la imagen de fondo

        # Obtener el tamaño de la ventana y de la imagen
        tamano_ventana = self.size()
        tamano_pixmap = pixmap.size()

        # Calcular la posición central para dibujar la imagen
        x = (tamano_ventana.width() - tamano_pixmap.width()) // 2
        y = (tamano_ventana.height() - tamano_pixmap.height()) // 2

        # Establecer la transparencia
        painter.setOpacity(0.2)  # Ajustar el nivel de opacidad a un valor deseado

        # Dibujar la imagen en el centro de la ventana
        painter.drawPixmap(x, y, pixmap)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()

    # Mostrar la ventana maximizada
    ventana.showMaximized()

    sys.exit(app.exec_())
