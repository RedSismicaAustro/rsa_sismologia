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
matplotlib.use('Qt5Agg')
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMessageBox, QToolBar, QLabel, QVBoxLayout, QWidget,QGridLayout,QComboBox,QFileDialog,QPushButton
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QTimer, QDateTime,QTime
from PyQt5 import QtWidgets
from subprogramas.fases import VentanaPrincipal as FasesVentana
from subprogramas.extraer_integrado import Extraer_evento
from subprogramas.marcar_eventos import Marcar_evento
from subprogramas.procesamiento_integrado import Procesar_evento,verificar_drives_virtuales,FileMonitor,cargar_combo_eventos,activar_hilo
from subprogramas.reporte_diario import Reporte_diario
from subprogramas.reporte_acumulado import Reporte_periodo
from subprogramas.inicio import Inicio_proceso
from subprogramas.otras_redes import Otras_redes
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
        self.setWindowIcon(QIcon('logo rsa.png'))
        self.showMaximized()
        self.directorio_trabajo='G:/Mi unidad/DIA/'
        self.responsable='RSA'
        self.periodo='' #'00H-12H'
        self.archivo=os.path.join(self.directorio_trabajo,datetime.today().strftime("%Y%m%d") + "000000")
        
        # Estado de inicialización
        self.datos_inicializados = False
        self.widget_activo = None
        
        self.construccion_menu()
        
        # Ruta del archivo CSV
        self.RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
        self.RAIZ_PROYECTO=os.path.join(self.RAIZ_PROYECTO, "..")
        ruta_csv =  os.path.join(self.RAIZ_PROYECTO, "datos", "responsables.csv")
        ruta_csv = os.path.abspath(ruta_csv)
        self.variables_permitidas=self.__dict__.keys()
        
        # Configuración inicial
        self.configurar_estado_inicial()

    def configurar_estado_inicial(self):
        """Configura el estado inicial limpio de la aplicación"""
        self.datos_inicializados = False
        self.widget_activo = None
        
        # Limpiar cualquier widget central anterior
        self.setCentralWidget(QWidget(self))
        
        # Configurar menús para estado inicial
        self.deshabilitar_menus()
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO', False)

    def recibir_datos_inicio(self, archivo, directorio_trabajo, responsable,periodo):
        """Recibe datos pero no los procesa hasta completar_inicializacion"""
        self.archivo = archivo
        self.directorio_trabajo = directorio_trabajo
        self.responsable = responsable
        self.periodo = periodo



    def cargar_widget_inicializacion(self, widget):
        """Carga específicamente el widget de inicialización"""
        # Limpiar widget anterior
        self.limpiar_widget_actual()
        
        # Establecer como widget activo
        self.widget_activo = widget
        self.setCentralWidget(widget)
        #widget.showMaximized()
        
        # Configurar estado durante inicialización
        self.deshabilitar_menus()
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO - INICIALIZANDO DÍA', False)

    def completar_inicializacion(self, archivo, directorio_trabajo, responsable, periodo):
        """Se ejecuta cuando la inicialización es exitosa"""
        print("=== COMPLETANDO INICIALIZACIÓN ===")
        
        # 1. Guardar datos de inicialización
        self.archivo = archivo
        self.directorio_trabajo = directorio_trabajo
        self.responsable = responsable
        self.periodo = periodo
        
        # 2. Marcar como inicializado
        self.datos_inicializados = True
        
        # 3. Limpiar widget de inicialización
        self.limpiar_widget_inicializacion()
        
        # 4. Configurar estado post-inicialización
        self.establecer_estado_trabajo()
        
        print("Inicialización completada exitosamente")

    def cancelar_inicializacion(self):
        """Se ejecuta si la inicialización se cancela"""
        print("=== CANCELANDO INICIALIZACIÓN ===")
        
        # Limpiar widget de inicialización
        self.limpiar_widget_inicializacion()
        
        # Volver al estado inicial
        self.configurar_estado_inicial()

    def limpiar_widget_inicializacion(self):
        """Limpia específicamente el widget de inicialización"""
        if hasattr(self, 'inicio_proceso') and self.inicio_proceso:
            try:
                # Desconectar señales
                self.inicio_proceso.inicializado.disconnect()
                self.inicio_proceso.cerrado.disconnect()
            except:
                pass
            
            # Limpiar referencia
            self.inicio_proceso = None
        
        # Limpiar widget activo
        self.widget_activo = None

    def establecer_estado_trabajo(self):
        """Establece el estado base para trabajar con menús"""
        # Widget central vacío pero funcional
        self.setCentralWidget(QWidget(self))
        
        # Habilitar menús de trabajo
        self.habilitar_menus()
        
        # Título con información del día inicializado
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO', True)
        
        print("Estado de trabajo establecido - Menús disponibles")

    def cargar_widget_menu(self, widget, titulo, mostrar_detalles=True):
        """Método específico para cargar widgets de menús después de inicialización"""
        if not self.datos_inicializados:
            QMessageBox.warning(self, 'Advertencia', 
                              'Debe completar la inicialización del día primero.')
            return False
        
        print(f"=== CARGANDO MENÚ: {widget.__class__.__name__} ===")
        
        # 1. Limpiar widget anterior
        self.limpiar_widget_actual()
        
        # 2. Establecer nuevo widget activo
        self.widget_activo = widget
        self.setCentralWidget(widget)
        
        # 3. Configurar estado del menú
        self.deshabilitar_menus()
        self.actualizar_titulo(titulo, mostrar_detalles)
        
        # 4. Mostrar widget
        #widget.showMaximized()
        
        # 5. Conectar señal de cierre - MÉTODO DIRECTO
        def on_widget_closed():
            print(f"DEBUG: Widget {widget.__class__.__name__} se está cerrando")
            QTimer.singleShot(0, self.volver_estado_trabajo)
        
        widget.destroyed.connect(on_widget_closed)
        
        if hasattr(widget, 'cerrado'):
            print(f"DEBUG: Conectando señal 'cerrado' de {widget.__class__.__name__}")
            widget.cerrado.connect(on_widget_closed)
        
        print(f"Menú {widget.__class__.__name__} cargado exitosamente")
        return True

    def limpiar_widget_actual(self):
        """Limpia el widget actualmente activo"""
        if self.widget_activo:
            try:
                # Desconectar todas las señales del widget actual
                self.widget_activo.destroyed.disconnect()
            except:
                pass
            
            # Si tiene método de limpieza, ejecutarlo
            if hasattr(self.widget_activo, 'limpiar_estado'):
                try:
                    self.widget_activo.limpiar_estado()
                except Exception as e:
                    print(f"Error en limpieza del widget: {e}")
            
            # Programar destrucción
            self.widget_activo.deleteLater()
            self.widget_activo = None

    def notificar_cierre_subprograma(self):
        """Método que los subprogramas pueden llamar directamente para notificar su cierre"""
        print("DEBUG: notificar_cierre_subprograma llamado directamente")
        QTimer.singleShot(0, self.volver_estado_trabajo)

    def volver_estado_trabajo(self):
        """Regresa al estado de trabajo después de cerrar un menú - RELANZA ESTADO COMPLETO"""
        print("=== REGRESANDO A ESTADO DE TRABAJO - RELANZANDO ESTADO ===")
        
        # Limpiar referencia del widget
        self.widget_activo = None
        
        # Establecer widget central limpio
        self.setCentralWidget(QWidget(self))
        
        # RELANZAR COMPLETAMENTE EL ESTADO DE TRABAJO
        if self.datos_inicializados:
            print("RELANZANDO establecer_estado_trabajo()...")
            self.establecer_estado_trabajo()  # Esto ejecuta todo el proceso completo
            print("ESTADO DE TRABAJO COMPLETAMENTE RELANZADO")
        else:
            self.configurar_estado_inicial()
            
        # Forzar actualización inmediata
        self.repaint()
        QApplication.processEvents()

    def limpiar_estado_completo(self):
        """Limpia completamente el estado de la aplicación"""
        print("Limpiando estado completo...")
        
        # Limpiar widget actual
        self.limpiar_widget_actual()
        
        # Limpiar widget de inicialización si existe
        self.limpiar_widget_inicializacion()
        
        # Limpiar variables temporales
        self.limpiar_variables_temporales()
        
        # Resetear estado
        self.datos_inicializados = False
        self.widget_activo = None

    def limpiar_variables_temporales(self):
        """Elimina atributos temporales de forma segura"""
        try:
            # Define atributos esenciales que NUNCA se deben borrar
            esenciales = {
                'archivo', 'directorio_trabajo', 'responsable', 'periodo',
                'datos_inicializados', 'widget_activo', 'variables_permitidas',
                'menuBar', 'statusBar', 'barra_menu', 'menu_inicio', 'menu_configuracion',
                'menu_procesamiento',  'menu_informes','menu_otros_informes' ,'menu_ayuda',
                'accion_inicializar_dia', 'accion_salir', 'barra_herramientas',
                'etiqueta_logo', 'etiqueta_titulo', 'widget_central', 'layout_principal',
                'logo_pixmap', 'RAIZ_PROYECTO'
            }
            
            # Unir con variables permitidas existentes
            if hasattr(self, 'variables_permitidas'):
                esenciales.update(self.variables_permitidas)
            
            # Eliminar solo variables temporales (por prefijo)
            prefijo_temporal = 'tmp_'
            for nombre_atributo in list(self.__dict__.keys()):
                if (isinstance(nombre_atributo, str) and 
                    nombre_atributo.startswith(prefijo_temporal) and 
                    nombre_atributo not in esenciales):
                    try:
                        delattr(self, nombre_atributo)
                    except Exception as e:
                        print(f"No se pudo eliminar el atributo {nombre_atributo}: {e}")
                        
        except Exception as e:
            print(f"Error en limpieza de variables temporales: {e}")

    def salir(self):
        """Lógica de salida mejorada"""
        if self.accion_inicializar_dia.isVisible():
            # Estado inicial: cerrar aplicación
            self.close()
        else:
            # Estado trabajando: volver al estado inicial
            print("=== SALIENDO A MENÚ INICIO ===")
            self.limpiar_estado_completo()
            self.configurar_estado_inicial()

    def construccion_menu(self):
        # Crear barra de menú
        self.barra_menu = self.menuBar()

        ##########################################################################################
        #  Menú uno: Inicio
        ##########################################################################################
        self.menu_inicio = self.barra_menu.addMenu('Inicio')

        self.accion_inicializar_dia = QAction('Inicializacion de dia', self)
        self.accion_inicializar_dia.triggered.connect(self.inicializar_dia)
        self.menu_inicio.addAction(self.accion_inicializar_dia)

        self.accion_salir = QAction('Salir', self)
        self.accion_salir.triggered.connect(self.salir)
        self.menu_inicio.addAction(self.accion_salir)

        ##########################################################################################
        #  Menú dos: Configuración
        ##########################################################################################
        self.menu_configuracion = self.barra_menu.addMenu('Configuración')

        self.accion_estaciones = QAction('Estaciones', self)
        self.accion_estaciones.triggered.connect(self.estaciones)
        self.menu_configuracion.addAction(self.accion_estaciones)

        self.accion_digitales = QAction('Enlaces digitales', self)
        self.accion_digitales.triggered.connect(self.enlaces_digitales)
        self.menu_configuracion.addAction(self.accion_digitales)

        self.accion_ingresar_datos_rg = QAction('Ingresar registro contínuo', self)
        self.accion_ingresar_datos_rg.triggered.connect(self.ingresar_datos_estacion_rg)
        self.menu_configuracion.addAction(self.accion_ingresar_datos_rg)

        self.accion_ingresar_datos_ev = QAction('Ingresar eventos de estaciones', self)
        self.accion_ingresar_datos_ev.triggered.connect(self.ingresar_datos_estacion_ev)
        self.menu_configuracion.addAction(self.accion_ingresar_datos_ev)

        self.accion_ingresar_IGEPN = QAction('Datos IGEPN', self)
        self.accion_ingresar_IGEPN.triggered.connect(self.ingresar_IGEPN)
        self.menu_configuracion.addAction(self.accion_ingresar_IGEPN)

        self.accion_ingresar_USGS = QAction('Datos USGS', self)
        self.accion_ingresar_USGS.triggered.connect(self.ingresar_USGS)
        self.menu_configuracion.addAction(self.accion_ingresar_USGS)


        ##########################################################################################
        #  Menú tres: Informes
        ##########################################################################################
        self.menu_informes = self.barra_menu.addMenu('Informes')

        self.accion_reporte_periodo = QAction('Reporte periodo', self)
        self.accion_reporte_periodo.triggered.connect(self.reporte_periodo)
        self.menu_informes.addAction(self.accion_reporte_periodo)

        self.accion_reporte_enjambre = QAction('Enjambre sísmico', self)
        self.accion_reporte_enjambre.triggered.connect(self.reporte_enjambre)
        self.menu_informes.addAction(self.accion_reporte_enjambre)

        self.accion_shapes = QAction('Shapes', self)
        self.accion_shapes.triggered.connect(self.creacion_shapes)
        self.menu_informes.addAction(self.accion_shapes)

        ##########################################################################################
        #  Menú cuatro: procesamiento
        ##########################################################################################
        self.menu_procesamiento = self.barra_menu.addMenu('Procesamiento')

        self.accion_marcar = QAction('Marcar', self)
        self.accion_marcar.triggered.connect(self.marcar_eventos)
        self.menu_procesamiento.addAction(self.accion_marcar)

        self.accion_extraer = QAction('Extraer', self)
        self.accion_extraer.triggered.connect(self.extraer_eventos)
        self.menu_procesamiento.addAction(self.accion_extraer)

        self.accion_reextraer = QAction('Procesamiento', self)
        self.accion_reextraer.triggered.connect(self.procesamiento)
        self.menu_procesamiento.addAction(self.accion_reextraer)

        self.accion_fases = QAction('Fases', self)
        self.accion_fases.triggered.connect(self.mostrar_fases)
        self.menu_procesamiento.addAction(self.accion_fases)

        self.accion_reextraer = QAction('Reextraccion', self)
        self.accion_reextraer.triggered.connect(self.reextracion)
        self.menu_procesamiento.addAction(self.accion_reextraer)

        ##########################################################################################
        #  Menú cinco: Otros Informes
        ##########################################################################################
        self.menu_otros_informes = self.barra_menu.addMenu('Otros Informes')

        self.accion_reporte_diario = QAction('Reporte diario', self)
        self.accion_reporte_diario.triggered.connect(self.reporte_diario)
        self.menu_otros_informes.addAction(self.accion_reporte_diario)


        ##########################################################################################
        #  Menú seis: Ayuda
        ##########################################################################################
        self.menu_ayuda = self.barra_menu.addMenu('Ayuda')

        self.accion_acerca_de = QAction('Acerca de', self)
        self.accion_acerca_de.triggered.connect(self.acerca_de)
        self.menu_ayuda.addAction(self.accion_acerca_de)




        # Configurar barra de herramientas
        self.barra_herramientas = QToolBar('Barra Principal')
        self.addToolBar(Qt.TopToolBarArea, self.barra_herramientas)

        self.etiqueta_logo = QLabel()
        self.logo_pixmap = QPixmap('logo rsa.png').scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.etiqueta_logo.setPixmap(self.logo_pixmap)
        self.barra_herramientas.addWidget(self.etiqueta_logo)

        self.etiqueta_titulo = QLabel('PROCESAMIENTO INTEGRADO')
        self.etiqueta_titulo.setFont(QFont('Arial', 12))
        self.barra_herramientas.addWidget(self.etiqueta_titulo)

        self.barra_herramientas.setIconSize(self.logo_pixmap.size())
        self.barra_herramientas.setMovable(False)

        # Widget central inicial
        self.widget_central = QWidget(self)
        self.setCentralWidget(self.widget_central)
        self.layout_principal = QVBoxLayout(self.widget_central)

    # =================================================================
    # MÉTODOS ESPECÍFICOS PARA CADA MENÚ
    # =================================================================

    ##########################################################################################
    #  Menú uno: Inicio
    ##########################################################################################

    def inicializar_dia(self):
        """Proceso de inicialización que establece el estado base para todos los menús"""
        print("=== INICIANDO INICIALIZACIÓN DE DÍA ===")
        
        # 1. Limpiar estado anterior completamente
        self.limpiar_estado_completo()
        
        # 2. Crear widget de inicialización
        self.inicio_proceso = Inicio_proceso(
            self.directorio_trabajo, 
            self.responsable, 
            self.periodo
        )
        
        # 3. Conectar señales de inicialización
        self.inicio_proceso.inicializado.connect(self.completar_inicializacion)
        self.inicio_proceso.cerrado.connect(self.cancelar_inicializacion)
        
        # 4. Cargar widget de inicialización
        self.cargar_widget_inicializacion(self.inicio_proceso)
        
        print("Widget de inicialización cargado")


    ##########################################################################################
    #  Menú dos: Configuración
    ##########################################################################################


    def estaciones(self):
        QMessageBox.information(self, 'Configuración', 'Configuración de estaciones.')

    def enlaces_digitales(self):
        QMessageBox.information(self, 'Configuración', 'Configuración de enlaces digitales.')

    def ingresar_datos_estacion_rg(self):
        QMessageBox.information(self, 'Configuración', 'Ingresar datos de estación en registro continuo')

    def ingresar_datos_estacion_ev(self):
        QMessageBox.information(self, 'Configuración', 'Ingresar datos de estación en eventos')

    def ingresar_IGEPN(self):
        """Cargar menú de ingreso IGEPN"""
        print("Iniciando IGEPN...")
        
        widget_marcar = Otras_redes(
            self.archivo, 
            self.directorio_trabajo, 
            self.responsable, 
            self.periodo,'IGEPN',
            self  # Pasar referencia a la ventana principal
        )
        success = self.cargar_widget_menu(
            widget_marcar,
            'PROCESAMIENTO INTEGRADO - CARGAR DATOS DE IGEPN',
            True
        )
        if success:
            print("ingreso IGEPN cargado exitosamente")


    def ingresar_USGS(self):
        """Cargar menú de ingreso USGS"""
        print("Iniciando USGS...")
        
        widget_marcar = Otras_redes(
            self.archivo, 
            self.directorio_trabajo, 
            self.responsable, 
            self.periodo,'USGS',
            self  # Pasar referencia a la ventana principal
        )
        success = self.cargar_widget_menu(
            widget_marcar,
            'PROCESAMIENTO INTEGRADO - CARGAR DATOS DE IGEPN',
            True
        )
        if success:
            print("ingreso USGS cargado exitosamente")



    ##########################################################################################
    #  Menú tres: Informes
    ##########################################################################################


    def reporte_periodo(self):
        """Cargar menú Reporte Diario"""
        widget_procesar = Reporte_periodo(
            self.archivo,
            self.directorio_trabajo,
            self.responsable,
            self.periodo
        )
        
        self.cargar_widget_menu(
            widget_procesar,
            'PROCESAMIENTO INTEGRADO - REPORTES',
            True
        )

    def reporte_enjambre(self):
        QMessageBox.information(self, 'Informe', 'Reporte Enjambre.')

    def creacion_shapes(self):
        QMessageBox.information(self, 'Informe', 'Creacion de Shapes')


    ##########################################################################################
    #  Menú cuatro: procesamiento
    ##########################################################################################

    def marcar_eventos(self):
        """Cargar menú de marcar eventos"""
        print("Iniciando Marcar Eventos...")
        
        widget_marcar = Marcar_evento(
            self.archivo, 
            self.directorio_trabajo, 
            self.responsable, 
            self.periodo,
            self  # Pasar referencia a la ventana principal
        )
        success = self.cargar_widget_menu(
            widget_marcar,
            'PROCESAMIENTO INTEGRADO - MARCAR EVENTOS EN REGISTRO CONTINUO',
            True
        )
        if success:
            print("Marcar Eventos cargado exitosamente")

    def extraer_eventos(self):
        """Cargar menú de extraer eventos"""
        print("Iniciando Extraer Eventos...")
        widget_extraer = Extraer_evento(
            self.archivo,
            self.directorio_trabajo,
            self.responsable,
            self.periodo
        )
        
        success = self.cargar_widget_menu(
            widget_extraer,
            'PROCESAMIENTO INTEGRADO - EXTRACCIÓN DE EVENTOS',
            True
        )
        if success:
            print("Extraer Eventos cargado exitosamente")


    def procesamiento(self):
        """Cargar menú de procesamiento"""
        widget_procesar = Procesar_evento(
            self.archivo,
            self.directorio_trabajo,
            self.responsable,
            self.periodo
        )
        
        self.cargar_widget_menu(
            widget_procesar,
            'PROCESAMIENTO INTEGRADO - PROCESAMIENTO DE EVENTOS',
            True
        )

    def mostrar_fases(self):
        """Cargar menú de fases"""
        widget_fases = FasesVentana()
        
        self.cargar_widget_menu(
            widget_fases,
            'PROCESAMIENTO INTEGRADO - MARCAR FASES SISMICAS',
            True
        )

    def reextracion(self):
        """Reextracción directa"""
        if not self.datos_inicializados:
            QMessageBox.warning(self, 'Advertencia', 
                              'Debe completar la inicialización del día primero.')
            return
            
        self.deshabilitar_menus()
        extraer_dia(self.archivo, self.responsable, True)
        self.habilitar_menus()


    ##########################################################################################
    #  Menú tres: Otros Informes
    ##########################################################################################

    def reporte_diario(self):
        """Cargar menú Reporte Diario"""
        widget_procesar = Reporte_diario(
            self.archivo,
            self.directorio_trabajo,
            self.responsable,
            self.periodo
        )
        
        self.cargar_widget_menu(
            widget_procesar,
            'PROCESAMIENTO INTEGRADO - PROCESAMIENTO DE EVENTOS',
            True
        )




    ##########################################################################################
    #  Menú seis: Ayuda
    ##########################################################################################

    def acerca_de(self):
        QMessageBox.information(self, 'Acerca de', 'Esta es una aplicación de ejemplo de PyQt5.')







    ##########################################################################################
    #  Metodos de estado de menús
    ##########################################################################################

    def actualizar_titulo(self, texto, mostrar_detalles):
        """Actualiza el título de la ventana y etiqueta"""
        self.setWindowTitle(texto)
        
        if mostrar_detalles and self.datos_inicializados:
            if self.periodo!='':
                detalles = f'Directorio: {self.directorio_trabajo}\nDía: {self.archivo}\nPeriodo: {self.periodo}\nUsuario: {self.responsable}'
            else:
                detalles = f'Directorio: {self.directorio_trabajo}\nDía: PERIODO \nPeriodo: {self.periodo}\nUsuario: {self.responsable}'
            self.etiqueta_titulo.setText(detalles)
        elif mostrar_detalles and not self.datos_inicializados:
            # Si se solicitan detalles pero no hay inicialización, mostrar texto simple
            self.etiqueta_titulo.setText(texto)
        else:
            # Si no se solicitan detalles, limpiar la etiqueta
            self.etiqueta_titulo.setText(texto)

    def habilitar_menus(self):
        """Habilita menús en estado de trabajo"""
        if self.periodo=='':
            self.menu_configuracion.setEnabled(True)
            self.menu_informes.setEnabled(True) 
        else:
            self.menu_procesamiento.setEnabled(True)
            self.menu_otros_informes.setEnabled(True)
        self.accion_inicializar_dia.setVisible(False)

    def deshabilitar_menus(self):
        """Deshabilita menús (estado inicial o dentro de menú)"""
        self.menu_configuracion.setEnabled(False)
        self.menu_informes.setEnabled(False)
        self.menu_procesamiento.setEnabled(False)
        self.menu_otros_informes.setEnabled(False)
        self.accion_inicializar_dia.setVisible(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        pixmap = QPixmap('logo ucuenca.png')

        tamano_ventana = self.size()
        tamano_pixmap = pixmap.size()

        x = (tamano_ventana.width() - tamano_pixmap.width()) // 2
        y = (tamano_ventana.height() - tamano_pixmap.height()) // 2

        painter.setOpacity(0.2)
        painter.drawPixmap(x, y, pixmap)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.showMaximized()
    sys.exit(app.exec_())