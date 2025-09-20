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
import matplotlib
matplotlib.use('Qt5Agg')  # Alternativamente: 'Qt5Agg' si necesitas interactividad
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMessageBox, QToolBar, QLabel, QVBoxLayout, QWidget,QGridLayout,QComboBox,QFileDialog,QPushButton
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QTimer, QDateTime,QTime
from PyQt5 import QtWidgets
from subprogramas.fases import VentanaPrincipal as FasesVentana  # Usando la clase para integrar
from subprogramas.extraer_integrado import Extraer_evento
from subprogramas.marcar_eventos import Marcar_evento
from subprogramas.procesamiento_integrado import Procesar_evento,verificar_drives_virtuales,FileMonitor,cargar_combo_eventos,activar_hilo

from subprogramas.inicio import Inicio_proceso
from datetime import datetime, timedelta
from metodos_rsa import lectura_archivo,extraer_dia
from metodos_gestion import obtener_directorios
import subprocess
import csv



class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana principal
        self.setWindowTitle('PROCESAMIENTO INTEGRADO')
        self.setWindowIcon(QIcon('logo rsa.png'))  # Establecer ícono de la ventana
        self.showMaximized()  # Mostrar la ventana maximizada inicialmente
        self.directorio_trabajo='G:/Mi unidad/DIA/'
        self.responsable='RSA'
        self.periodo='00H-12H'
        self.archivo=os.path.join(self.directorio_trabajo,datetime.today().strftime("%Y%m%d") + "000000")
        self.construccion_menu()
        # Ruta del archivo CSV
        self.RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
        self.RAIZ_PROYECTO=os.path.join(self.RAIZ_PROYECTO, "..")
        ruta_csv =  os.path.join(self.RAIZ_PROYECTO, "datos", "responsables.csv")
        ruta_csv = os.path.abspath(ruta_csv)
        self.variables_permitidas=self.__dict__.keys()


    def _al_destruir_central(self, *args):
        # Asegura un central limpio y re-habilita menús
        self.setCentralWidget(QWidget(self))  # central vacío "placeholder"
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO', False)
        self.habilitar_menus()

        
    def recibir_datos_inicio(self, archivo, directorio_trabajo, responsable,periodo):
        self.archivo = archivo
        self.directorio_trabajo = directorio_trabajo
        self.responsable = responsable
        self.periodo = periodo


    def cargar_widget_central(self, widget, titulo,bandera_titulo):
        anterior = self.centralWidget()
        if anterior:
            anterior.deleteLater()
        self.setCentralWidget(widget)
        self.actualizar_titulo(titulo,bandera_titulo)
        widget.showMaximized()
        widget.destroyed.connect(self._al_destruir_central)

    def limpiar_variables_temporales(self):
        """
        Elimina atributos temporales y limpia el widget central y su contenido gráfico
        de forma segura. Usa takeCentralWidget() para desacoplar el widget central.
        """
        from PyQt5.QtWidgets import QWidget
        try:
            # 1) Desacoplar el widget central de forma segura
            widget_central = self.takeCentralWidget()  # devuelve el widget y deja el central en None

            if widget_central is not None and isinstance(widget_central, QWidget):
                # 2) Verificar que el objeto no esté ya destruido (opcional pero útil en PyQt5)
                try:
                    # sip.isdeleted solo existe en PyQt5; si usas PySide2, usa shiboken2.isValid
                    import sip
                    if sip.isdeleted(widget_central):
                        widget_central = None
                except Exception:
                    # si sip no está disponible, seguimos sin esa comprobación
                    pass

                if widget_central is not None:
                    # 3) Si el widget tiene limpieza interna (gráficos, timers, señales), invócala
                    if hasattr(widget_central, 'limpiar_estado'):
                        try:
                            widget_central.limpiar_estado()
                        except Exception as e:
                            print(f"Error al limpiar el estado interno del widget central: {e}")

                    # 4) Asegurar desconexión de señales propias del widget si procede
                    # (ejemplo) if hasattr(widget_central, 'desconectar_senales'): widget_central.desconectar_senales()

                    # 5) Programar destrucción segura
                    try:
                        widget_central.deleteLater()
                    except Exception as e:
                        print(f"Error al programar borrado del widget central: {e}")

           # 6) Limpieza de atributos temporales controlada
           #    Define un conjunto de atributos que NUNCA se deben borrar.
           #    Asegúrate de incluir variables_permitidas y todo lo que sea esencial para tu ventana.
            esenciales = {
                'self.archivo','self.directorio_trabajo','self.responsables','self.periodo',
                'variables_permitidas', 'menuBar', 'statusBar',  # ejemplos
                # agrega aquí tus atributos críticos del QMainWindow
            }

            # Si ya manejas una lista blanca en self.variables_permitidas, unifícala:
            if hasattr(self, 'variables_permitidas') and isinstance(self.variables_permitidas, (set, list, tuple)):
                esenciales.update(self.variables_permitidas)

            # Opcional: define un prefijo para identificar temporales (más seguro).
            prefijo_temporal = 'tmp_'  # ajusta si usas otra convención

            for nombre_atributo in list(self.__dict__.keys()):
                if nombre_atributo in esenciales:
                    continue
                # Evita borrar métodos enlazados u objetos críticos
                valor = getattr(self, nombre_atributo)
                # Regla: borra solo si tú mismo creaste el atributo como temporal (por prefijo)
                # o si lo incluiste explícitamente en una lista de temporales.
                es_temporal_por_prefijo = isinstance(nombre_atributo, str) and nombre_atributo.startswith(prefijo_temporal)
                es_temporal_por_lista = hasattr(self, 'lista_temporales') and isinstance(getattr(self, 'lista_temporales'), (set, list, tuple)) and nombre_atributo in self.lista_temporales

                if es_temporal_por_prefijo or es_temporal_por_lista:
                    try:
                        # Si son objetos Qt, intenta desconectar señales/timers antes
                        # (agrega aquí tu propia lógica si corresponde)
                        delattr(self, nombre_atributo)
                    except Exception as e:
                        print(f"No se pudo eliminar el atributo {nombre_atributo}: {e}")
        except Exception as e:
            # Este except te permitirá ver si el crash proviene de otro punto
            print(f"Error en limpieza de Extraer_evento: {e}")


    def construccion_menu(self):
        # Crear barra de menú
        self.barra_menu = self.menuBar()
 
        
        ##########################################################################################
        #  Menú uno: Inicio
        ##########################################################################################
        # Crear menú Configuración
        self.menu_inicio = self.barra_menu.addMenu('Inicio')

        # Crear acción Directorio de trabajo
        self.accion_inicializar_dia = QAction('Inicializacion de dia', self)
        self.accion_inicializar_dia.triggered.connect(self.inicializar_dia)
        self.menu_inicio.addAction(self.accion_inicializar_dia)

        # Crear acción Salir
        self.accion_salir = QAction('Salir', self)
        self.accion_salir.triggered.connect(self.salir)
        self.menu_inicio.addAction(self.accion_salir)
 
 
        ##########################################################################################
        #  Menú dos: Configuración
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


        ##########################################################################################
        #  Menú tres: procesamiento
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
        #  Menú cuatro: Otras redes
        ##########################################################################################


        # Crear menú Otras redes
        self.menu_otras_redes = self.barra_menu.addMenu('Otras redes')

        # Crear acción IGEPN
        self.accion_ingresar_IGEPN = QAction('IGEPN', self)
        self.accion_ingresar_IGEPN.triggered.connect(self.ingresar_IGEPN)
        self.menu_otras_redes.addAction(self.accion_ingresar_IGEPN)

        # Crear acción USGS
        self.accion_ingresar_USGS = QAction('USGS', self)
        self.accion_ingresar_USGS.triggered.connect(self.ingresar_USGS)
        self.menu_otras_redes.addAction(self.accion_ingresar_USGS)



        ##########################################################################################
        #  Menú cinco: Informes
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
        #  Menú seis: Ayuda
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
        self.etiqueta_titulo.setFont(QFont('Arial', 12))
        self.barra_herramientas.addWidget(self.etiqueta_titulo)

        # Ajustar el tamaño de la barra de herramientas
        self.barra_herramientas.setIconSize(self.logo_pixmap.size())
        self.barra_herramientas.setMovable(False)

        # Widget central
        self.widget_central = QWidget(self)
        self.setCentralWidget(self.widget_central)
        self.layout_principal = QVBoxLayout(self.widget_central)

        self.deshabilitar_menus()


        # Agregar el componente de estado de procesamiento sísmico
        #self.estado_sismico = EstadoProcesamientoSismico()
        #self.layout_principal.addWidget(self.estado_sismico)


        ##########################################################################################
        #  Menú uno: Inicio
        ##########################################################################################


    def inicializar_dia(self):
        self.limpiar_variables_temporales()
        self.inicio_proceso = Inicio_proceso(self.directorio_trabajo, self.responsable,self.periodo)
        # Conectar señales
        self.inicio_proceso.inicializado.connect(self.recibir_datos_inicio)
        #self.inicio_proceso.cerrado.connect(self.restaurar_estado_sismico)        
        self.cargar_widget_central(self.inicio_proceso, 'PROCESAMIENTO INTEGRADO  -  INICIALIZADO',True)
        self.habilitar_menus()


    def salir(self):
        if self.accion_inicializar_dia.isVisible():
            self.close()
        else:
            print("Saliendo a menu inicio")
            self.deshabilitar_menus()
            self.limpiar_variables_temporales()
            self.actualizar_titulo('PROCESAMIENTO INTEGRADO',False)

            
        ##########################################################################################
        #  Menú dos: Configuración
        ##########################################################################################

    def seleccionar_drive(self):
        self.limpiar_variables_temporales()
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath

    def estaciones(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Configuración', 'Configuración de estaciones.')
        self.habilitar_menus()

    def enlaces_digitales(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Configuración', 'Configuración de enlaces digitales.')
        self.habilitar_menus()

    def ingresar_datos_estacion_rg(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Configuración', 'Ingresar datos de estación en registro continuo')
        self.habilitar_menus()

    def ingresar_datos_estacion_ev(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Configuración', 'Ingresar datos de estación en eventos')
        self.habilitar_menus()

        ##########################################################################################
        #  Menú tres: procesamiento
        ##########################################################################################


    def mostrar_fases(self):
        # Deshabilitar menús al ejecutar esta acción
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()

        # Integrar la funcionalidad de Fases en la ventana principal
        self.fases_ventana = FasesVentana()
        self.setCentralWidget(self.fases_ventana)
        self.fases_ventana.showMaximized()

        # Actualizar el título después de haber cambiado el widget central
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO  -  MARCAR FASES SISMICAS',True)

        # Conectar el evento de cierre de la ventana de fases para restaurar el título y habilitar los menús
        self.fases_ventana.destroyed.connect(self._al_destruir_central)


    def marcar_eventos(self):
        # Deshabilitar menús al ejecutar esta acción
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        # Integrar la funcionalidad de Marcar Eventos en la ventana principal
        print("Marcar eventos 1")
        self.vista_marcar_eventos = Marcar_evento(self.archivo, self.directorio_trabajo, self.responsable, self.periodo)
        print("Marcar eventos 2")
        self.cargar_widget_central(self.vista_marcar_eventos, 'PROCESAMIENTO INTEGRADO  -  MARCAR EVENTOS EN REGISTRO CONTINUO',True)


    def procesamiento(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        self.procesar_eventos = Procesar_evento(self.archivo, self.directorio_trabajo, self.responsable, self.periodo)
        self.cargar_widget_central(self.procesar_eventos, 'PROCESAMIENTO INTEGRADO  -  PROCESAMIENTO DE EVENTOS',True)

    def extraer_eventos(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        self.extraer_eventos=Extraer_evento(self.archivo, self.directorio_trabajo, self.responsable, self.periodo)
        self.cargar_widget_central(self.extraer_eventos, 'PROCESAMIENTO INTEGRADO  -  EXTRACCIÓN DE EVENTOS',True)


    def reextracion(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        extraer_dia(self.archivo,self.responsable,True)
        self.habilitar_menus()


        ##########################################################################################
        #  Menú cuatro : Otras redes
        ##########################################################################################

    def ingresar_IGEPN(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Otras redes', 'Ingresar IGEPN')
        self.habilitar_menus()


    def ingresar_USGS(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Otras redes', 'Ingresar USGS')
        self.habilitar_menus()


        ##########################################################################################
        #  Menú cinco: Informes
        ##########################################################################################

    def reporte_diario(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()

        # Método que se ejecuta cuando se selecciona la acción en el menú
        try:
            # Lanza el script Python externo
            subprocess.Popen(['python', 'reporte_diario.py'])
        except Exception as e:
            print(f"Error al intentar ejecutar el script: {e}")

        self.habilitar_menus()

    def reporte_periodo(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Informe', 'Reporte Periodo.')
        self.habilitar_menus()

    def reporte_enjambre(self):
        self.limpiar_variables_temporales()
        self.deshabilitar_menus()
        QMessageBox.information(self, 'Informe', 'Reporte Enjambre.')
        self.habilitar_menus()


    def creacion_shapes(self):
        self.limpiar_variables_temporales()
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


    def actualizar_titulo(self, texto,bandera_titulo):
        self.setWindowTitle(texto)
        if bandera_titulo:
            texto='Directorio: '+self.directorio_trabajo+'\nDia: '+self.archivo+'\nPeriodo: '+self.periodo+'\nUsuario: '+self.responsable
            self.etiqueta_titulo.setText(texto)
        else:
            self.etiqueta_titulo.setText('')

    def habilitar_menus(self):
        self.menu_configuracion.setEnabled(True)
        self.menu_procesamiento.setEnabled(True)
        self.menu_otras_redes.setEnabled(True)
        self.menu_informes.setEnabled(True)
        self.menu_ayuda.setEnabled(True)
        self.accion_inicializar_dia.setVisible(False)

    def deshabilitar_menus(self):
        # Deshabilitar todos los elementos del menú excepto Ayuda.
        self.menu_configuracion.setEnabled(False)
        self.menu_procesamiento.setEnabled(False)
        self.menu_otras_redes.setEnabled(False)
        self.menu_informes.setEnabled(False)
        self.menu_ayuda.setEnabled(False)
        self.accion_inicializar_dia.setVisible(True)

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
