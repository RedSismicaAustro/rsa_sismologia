import sys
import os
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
plt.ioff()

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMessageBox, QToolBar,
    QLabel, QVBoxLayout, QWidget
)
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer

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
    ruta_proyecto = os.path.abspath(os.path.join(ruta_librerias, '..'))

ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

from subprogramas.fases import VentanaPrincipal as FasesVentana
from subprogramas.extraer_integrado import Extraer_evento
from subprogramas.marcar_eventos import Marcar_evento
from subprogramas.procesamiento_integrado import Procesar_evento
from subprogramas.reporte_diario import Reporte_diario
from subprogramas.reporte_acumulado import Reporte_periodo
from subprogramas.inicio import Inicio_proceso
from subprogramas.otras_redes import Otras_redes
from rsa_procesamiento import extraer_dia


def resolver_ruta_recurso(nombre_archivo, subdirectorio='datos'):
    """
    Busca de forma resiliente una imagen o recurso en las rutas canónicas del proyecto.
    """
    rutas_a_probar = [
        os.path.join(ruta_proyecto, subdirectorio, 'imagenes', nombre_archivo),
        os.path.join(ruta_proyecto, subdirectorio, nombre_archivo),
        os.path.join(ruta_proyecto, nombre_archivo),
        nombre_archivo
    ]
    for r in rutas_a_probar:
        if os.path.exists(r):
            return r
    return nombre_archivo


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana principal
        self.setWindowTitle('PROCESAMIENTO INTEGRADO - RSA')
        
        # Icono de ventana con el nuevo logo oficial RSA
        ruta_icono = resolver_ruta_recurso('logo rsa.png')
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))

        self.directorio_trabajo = 'G:/Mi unidad/DIA/'
        self.responsable = 'RSA'
        self.periodo = ''
        self.archivo = os.path.join(self.directorio_trabajo, datetime.today().strftime("%Y%m%d") + "000000")

        # Estado de inicialización y pila LIFO de estados de menú
        self.datos_inicializados = False
        self.widget_activo = None
        self.pila_estados = []

        # Construir menús y barra de herramientas
        self.construccion_menu()

        # Rutas del proyecto y variables protegidas
        self.RAIZ_PROYECTO = os.path.abspath(ruta_proyecto)
        self.variables_permitidas = self.__dict__.keys()

        # Configuración inicial limpia (Nivel 1, Estado A)
        self.configurar_estado_inicial()
        self.showMaximized()

    # =================================================================
    # GESTOR DE PILA LIFO DE ESTADOS DE NAVEGACIÓN
    # =================================================================

    def apilar_estado_actual(self):
        """Guarda una instantánea completa del estado antes de entrar a un subprograma"""
        snapshot = {
            'archivo': self.archivo,
            'directorio_trabajo': self.directorio_trabajo,
            'responsable': self.responsable,
            'periodo': self.periodo,
            'datos_inicializados': self.datos_inicializados,
            'titulo_ventana': self.windowTitle(),
            'texto_etiqueta': self.etiqueta_titulo.text(),
            'menu_configuracion': self.menu_configuracion.isEnabled(),
            'menu_informes': self.menu_informes.isEnabled(),
            'menu_procesamiento': self.menu_procesamiento.isEnabled(),
            'menu_otros_informes': self.menu_otros_informes.isEnabled(),
            'menu_ayuda': self.menu_ayuda.isEnabled(),
            'accion_inicializar': self.accion_inicializar_dia.isVisible()
        }
        self.pila_estados.append(snapshot)
        print(f"Estado apilado (LIFO). Total estados en pila: {len(self.pila_estados)}")

    def desapilar_y_restaurar_estado(self):
        """Recupera y restaura exactamente el último estado guardado (LIFO)"""
        if self.pila_estados:
            snapshot = self.pila_estados.pop()
            self.archivo = snapshot['archivo']
            self.directorio_trabajo = snapshot['directorio_trabajo']
            self.responsable = snapshot['responsable']
            self.periodo = snapshot['periodo']
            self.datos_inicializados = snapshot['datos_inicializados']
            self.setWindowTitle(snapshot['titulo_ventana'])
            self.etiqueta_titulo.setText(snapshot['texto_etiqueta'])
            self.menu_configuracion.setEnabled(snapshot['menu_configuracion'])
            self.menu_informes.setEnabled(snapshot['menu_informes'])
            self.menu_procesamiento.setEnabled(snapshot['menu_procesamiento'])
            self.menu_otros_informes.setEnabled(snapshot['menu_otros_informes'])
            self.menu_ayuda.setEnabled(snapshot['menu_ayuda'])
            self.menu_inicio.setEnabled(True)
            self.accion_inicializar_dia.setVisible(snapshot['accion_inicializar'])
            self.accion_salir.setVisible(True)
            print("Estado previo restaurado exitosamente desde pila LIFO.")
        else:
            if self.datos_inicializados:
                self.establecer_estado_trabajo()
            else:
                self.configurar_estado_inicial()

    # =================================================================
    # MÁQUINA DE ESTADOS Y CONTROL DE FLUJO
    # =================================================================

    def configurar_estado_inicial(self):
        """Configura el estado inicial limpio de la aplicación (Nivel 1, Estado A)"""
        self.datos_inicializados = False
        self.widget_activo = None
        self.pila_estados.clear()

        # Establecer widget central limpio
        self.setCentralWidget(QWidget(self))

        # Configurar menús para estado inicial
        self.deshabilitar_menus()
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO - RSA', False)

    def recibir_datos_inicio(self, archivo, directorio_trabajo, responsable, periodo):
        """Recibe datos de inicialización"""
        self.archivo = archivo
        self.directorio_trabajo = directorio_trabajo
        self.responsable = responsable
        self.periodo = periodo

    def cargar_widget_inicializacion(self, widget):
        """Carga específicamente el subprograma de inicialización de día impregnado en la ventana principal"""
        self.limpiar_widget_actual()
        self.widget_activo = widget
        self.setCentralWidget(widget)
        widget.showMaximized()

        self.deshabilitar_menus()
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO - INICIALIZANDO DÍA', False)

    def completar_inicializacion(self, archivo, directorio_trabajo, responsable, periodo):
        """Se ejecuta cuando la inicialización de día es completada con éxito (Pasa a Nivel 1, Estado B)"""
        self.archivo = archivo
        self.directorio_trabajo = directorio_trabajo
        self.responsable = responsable
        self.periodo = periodo

        self.datos_inicializados = True
        self.pila_estados.clear()
        self.limpiar_widget_inicializacion()
        self.establecer_estado_trabajo()

    def cancelar_inicializacion(self):
        """Se ejecuta si el usuario cancela la inicialización de día"""
        print("=== CANCELANDO INICIALIZACIÓN ===")
        self.limpiar_widget_inicializacion()
        self.configurar_estado_inicial()

    def limpiar_widget_inicializacion(self):
        """Limpia la referencia al subprograma de inicio"""
        if hasattr(self, 'inicio_proceso') and self.inicio_proceso:
            try:
                self.inicio_proceso.inicializado.disconnect()
                self.inicio_proceso.cerrado.disconnect()
            except Exception:
                pass
            self.inicio_proceso = None

        self.widget_activo = None

    def establecer_estado_trabajo(self):
        """Establece el estado base de trabajo (Nivel 1, Estado B) con menús habilitados y pantalla limpia"""
        self.limpiar_widget_actual()
        self.setCentralWidget(QWidget(self))
        self.habilitar_menus()
        self.actualizar_titulo('PROCESAMIENTO INTEGRADO - RSA', True)

    def cargar_widget_menu(self, widget, titulo, mostrar_detalles=True):
        """Carga e impregna exclusivamente la interfaz propia del subprograma en la ventana principal"""
        if not self.datos_inicializados:
            QMessageBox.warning(self, 'Advertencia', 'Debe completar la inicialización del día primero.')
            return False

        print(f"=== CARGANDO SUBPROGRAMA: {widget.__class__.__name__} ===")

        # 1. Apilar estado actual para restauración exacta al salir (LIFO)
        self.apilar_estado_actual()

        # 2. Limpiar widget anterior
        self.limpiar_widget_actual()

        # 3. Establecer nuevo widget activo como widget central de la ventana principal
        self.widget_activo = widget
        self.setCentralWidget(widget)

        # 4. Configurar estado del menú
        self.deshabilitar_menus()
        self.actualizar_titulo(titulo, mostrar_detalles)

        # 5. Mostrar widget maximizado impregnado en la ventana
        widget.showMaximized()

        # 5. Interceptar cierre del widget de forma universal (sin modificar el archivo del subprograma)
        metodo_close_original = widget.closeEvent
        def closeEvent_interceptado(event):
            try:
                metodo_close_original(event)
            except Exception:
                pass
            self.volver_estado_trabajo()
        widget.closeEvent = closeEvent_interceptado

        # 6. Conectar señales y botones de salida del .ui
        try:
            widget.destroyed.connect(self.volver_estado_trabajo)
        except Exception:
            pass

        if hasattr(widget, 'cerrado'):
            try:
                widget.cerrado.connect(self.volver_estado_trabajo)
            except Exception:
                pass

        for nombre_btn in ('boton_salir', 'Btn_salir', 'Btn_Salir', 'btn_salir', 'Boton_salir', 'Btn_cancelar', 'btn_cancelar', 'actionSalir'):
            if hasattr(widget, nombre_btn):
                btn = getattr(widget, nombre_btn)
                if hasattr(btn, 'clicked'):
                    try:
                        btn.clicked.connect(self.volver_estado_trabajo)
                    except Exception:
                        pass
                elif hasattr(btn, 'triggered'):
                    try:
                        btn.triggered.connect(self.volver_estado_trabajo)
                    except Exception:
                        pass

        print(f"Subprograma {widget.__class__.__name__} cargado exitosamente")
        return True

    def limpiar_widget_actual(self):
        """Limpia de forma segura el widget activo en el centro"""
        if self.widget_activo:
            if hasattr(self.widget_activo, 'limpiar_estado'):
                try:
                    self.widget_activo.limpiar_estado()
                except Exception as e:
                    print(f"Aviso al limpiar widget activo: {e}")

            if hasattr(self.widget_activo, 'disconnect_all_signals'):
                try:
                    self.widget_activo.disconnect_all_signals()
                except Exception:
                    pass

            for attr_name in list(self.widget_activo.__dict__.keys()):
                attr = getattr(self.widget_activo, attr_name)
                if hasattr(attr, 'disconnect'):
                    try:
                        attr.disconnect()
                    except Exception:
                        pass

            self.widget_activo.deleteLater()
            self.widget_activo = None

    def notificar_cierre_subprograma(self):
        """Notificación de cierre desde subprogramas"""
        QTimer.singleShot(0, self.volver_estado_trabajo)

    def volver_estado_trabajo(self):
        """Regresa al estado de trabajo previo tras cerrar un subprograma restaurando la pila LIFO"""
        print("=== RETOMANDO CONTROL EN VENTANA PRINCIPAL (LIFO) ===")
        self.limpiar_widget_actual()
        self.setCentralWidget(QWidget(self))
        self.desapilar_y_restaurar_estado()
        self.repaint()
        QApplication.processEvents()

    def limpiar_estado_completo(self):
        """Limpia completamente el estado de la aplicación"""
        self.limpiar_widget_actual()
        self.limpiar_widget_inicializacion()
        self.limpiar_variables_temporales()
        self.pila_estados.clear()

    def limpiar_variables_temporales(self):
        """Elimina variables que no estaban en el estado original"""
        variables_actuales = list(self.__dict__.keys())
        for var in variables_actuales:
            if var not in self.variables_permitidas:
                delattr(self, var)

    def construccion_menu(self):
        # Crear barra de menú
        self.barra_menu = self.menuBar()

        ##########################################################################################
        #  Menú uno: Inicio
        ##########################################################################################
        self.menu_inicio = self.barra_menu.addMenu('Inicio')

        self.accion_inicializar_dia = QAction('Inicialización de día', self)
        self.accion_inicializar_dia.triggered.connect(self.inicializar_dia)
        self.menu_inicio.addAction(self.accion_inicializar_dia)

        self.accion_salir = QAction('Salir', self)
        self.accion_salir.triggered.connect(self.accion_salir_ejecutar)
        self.menu_inicio.addAction(self.accion_salir)

        ##########################################################################################
        #  Menú dos: Configuración
        ##########################################################################################
        self.menu_configuracion = self.barra_menu.addMenu('Configuración')

        self.accion_estaciones = QAction('Estaciones', self)
        self.accion_estaciones.triggered.connect(self.estaciones)
        self.menu_configuracion.addAction(self.accion_estaciones)

        self.accion_enlaces = QAction('Enlaces digitales', self)
        self.accion_enlaces.triggered.connect(self.enlaces_digitales)
        self.menu_configuracion.addAction(self.accion_enlaces)

        self.menu_configuracion.addSeparator()

        self.accion_datos_estacion_rg = QAction('Ingresar datos de estación en registro continuo', self)
        self.accion_datos_estacion_rg.triggered.connect(self.ingresar_datos_estacion_rg)
        self.menu_configuracion.addAction(self.accion_datos_estacion_rg)

        self.accion_datos_estacion_ev = QAction('Ingresar eventos de estaciones acelerográficas', self)
        self.accion_datos_estacion_ev.triggered.connect(self.ingresar_datos_estacion_ev)
        self.menu_configuracion.addAction(self.accion_datos_estacion_ev)

        self.menu_configuracion.addSeparator()

        self.accion_igepn = QAction('Cargar datos de IGEPN', self)
        self.accion_igepn.triggered.connect(self.ingresar_IGEPN)
        self.menu_configuracion.addAction(self.accion_igepn)

        self.accion_usgs = QAction('Cargar datos de USGS', self)
        self.accion_usgs.triggered.connect(self.ingresar_USGS)
        self.menu_configuracion.addAction(self.accion_usgs)

        ##########################################################################################
        #  Menú tres: Informes
        ##########################################################################################
        self.menu_informes = self.barra_menu.addMenu('Informes')

        self.accion_reporte_periodo = QAction('Reporte periodo', self)
        self.accion_reporte_periodo.triggered.connect(self.reporte_periodo)
        self.menu_informes.addAction(self.accion_reporte_periodo)

        self.accion_reporte_enjambre = QAction('Reporte enjambre', self)
        self.accion_reporte_enjambre.triggered.connect(self.reporte_enjambre)
        self.menu_informes.addAction(self.accion_reporte_enjambre)

        self.accion_shapes = QAction('Generar Shapes', self)
        self.accion_shapes.triggered.connect(self.creacion_shapes)
        self.menu_informes.addAction(self.accion_shapes)

        ##########################################################################################
        #  Menú cuatro: Procesamiento
        ##########################################################################################
        self.menu_procesamiento = self.barra_menu.addMenu('Procesamiento')

        self.accion_marcar = QAction('Marcar', self)
        self.accion_marcar.triggered.connect(self.marcar_eventos)
        self.menu_procesamiento.addAction(self.accion_marcar)

        self.accion_extraer = QAction('Extraer', self)
        self.accion_extraer.triggered.connect(self.extraer_eventos)
        self.menu_procesamiento.addAction(self.accion_extraer)

        self.accion_procesamiento = QAction('Procesamiento', self)
        self.accion_procesamiento.triggered.connect(self.procesamiento)
        self.menu_procesamiento.addAction(self.accion_procesamiento)

        self.accion_fases = QAction('Fases', self)
        self.accion_fases.triggered.connect(self.mostrar_fases)
        self.menu_procesamiento.addAction(self.accion_fases)

        self.accion_reextraccion = QAction('Reextracción', self)
        self.accion_reextraccion.triggered.connect(self.reextracion)
        self.menu_procesamiento.addAction(self.accion_reextraccion)

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
        ruta_logo_banner = resolver_ruta_recurso('logo rsa.png')
        self.logo_pixmap = QPixmap(ruta_logo_banner).scaled(110, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.etiqueta_logo.setPixmap(self.logo_pixmap)
        self.barra_herramientas.addWidget(self.etiqueta_logo)

        self.etiqueta_titulo = QLabel('PROCESAMIENTO INTEGRADO')
        self.etiqueta_titulo.setFont(QFont('Arial', 12))
        self.barra_herramientas.addWidget(self.etiqueta_titulo)

        self.barra_herramientas.setIconSize(self.logo_pixmap.size())
        self.barra_herramientas.setMovable(False)

    # =================================================================
    # MÉTODOS ESPECÍFICOS PARA CADA MENÚ
    # =================================================================

    ##########################################################################################
    #  Menú uno: Inicio
    ##########################################################################################

    def inicializar_dia(self):
        """Proceso de inicialización que establece el estado base para todos los menús"""
        self.limpiar_estado_completo()
        self.inicio_proceso = Inicio_proceso(
            self.directorio_trabajo,
            self.responsable,
            self.periodo
        )
        self.inicio_proceso.inicializado.connect(self.completar_inicializacion)
        self.inicio_proceso.cerrado.connect(self.cancelar_inicializacion)
        self.cargar_widget_inicializacion(self.inicio_proceso)

    ##########################################################################################
    #  Menú dos: Configuración
    ##########################################################################################

    def estaciones(self):
        QMessageBox.information(self, 'Configuración', 'Configuración de estaciones sísmicas.')

    def enlaces_digitales(self):
        QMessageBox.information(self, 'Configuración', 'Configuración de enlaces digitales de telemetría.')

    def ingresar_datos_estacion_rg(self):
        QMessageBox.information(self, 'Configuración', 'Ingresar datos de estación en registro continuo.')

    def ingresar_datos_estacion_ev(self):
        QMessageBox.information(self, 'Configuración', 'Ingresar eventos de estaciones acelerográficas (EVT).')

    def ingresar_IGEPN(self):
        """Cargar menú de ingreso IGEPN"""
        print("Iniciando IGEPN...")
        widget_marcar = Otras_redes(
            self.archivo,
            self.directorio_trabajo,
            self.responsable,
            self.periodo,
            'IGEPN'
        )
        success = self.cargar_widget_menu(
            widget_marcar,
            'PROCESAMIENTO INTEGRADO - CARGAR DATOS DE IGEPN',
            True
        )
        if success:
            print("Ingreso IGEPN cargado exitosamente.")

    def ingresar_USGS(self):
        """Cargar menú de ingreso USGS"""
        print("Iniciando USGS...")
        widget_marcar = Otras_redes(
            self.archivo,
            self.directorio_trabajo,
            self.responsable,
            self.periodo,
            'USGS'
        )
        success = self.cargar_widget_menu(
            widget_marcar,
            'PROCESAMIENTO INTEGRADO - CARGAR DATOS DE USGS',
            True
        )
        if success:
            print("Ingreso USGS cargado exitosamente.")

    ##########################################################################################
    #  Menú tres: Informes
    ##########################################################################################

    def reporte_periodo(self):
        """Cargar menú Reporte Período / Acumulado"""
        widget_procesar = Reporte_periodo(
            self.archivo,
            self.directorio_trabajo,
            self.responsable,
            self.periodo
        )
        self.cargar_widget_menu(
            widget_procesar,
            'PROCESAMIENTO INTEGRADO - REPORTES POR PERÍODO',
            True
        )

    def reporte_enjambre(self):
        QMessageBox.information(self, 'Informe', 'Módulo de análisis de enjambres sísmicos.')

    def creacion_shapes(self):
        QMessageBox.information(self, 'Informe', 'Generación de Shapes GIS (.shp, .dbf, .prj).')

    ##########################################################################################
    #  Menú cuatro: Procesamiento
    ##########################################################################################

    def marcar_eventos(self):
        """Cargar menú de marcar eventos"""
        print("Iniciando Marcar Eventos...")
        widget_marcar = Marcar_evento(
            self.archivo,
            self.directorio_trabajo,
            self.responsable,
            self.periodo
        )
        success = self.cargar_widget_menu(
            widget_marcar,
            'PROCESAMIENTO INTEGRADO - MARCAR EVENTOS EN REGISTRO CONTINUO',
            True
        )
        if success:
            print("Marcar Eventos cargado exitosamente.")

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
            print("Extraer Eventos cargado exitosamente.")

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
            'PROCESAMIENTO INTEGRADO - MARCAR FASES SÍSMICAS',
            True
        )

    def reextracion(self):
        """Reextracción directa"""
        if not self.datos_inicializados:
            QMessageBox.warning(self, 'Advertencia', 'Debe completar la inicialización del día primero.')
            return

        self.deshabilitar_menus()
        extraer_dia(self.archivo, self.responsable, True)
        self.habilitar_menus()

    ##########################################################################################
    #  Menú cinco: Otros Informes
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
            'PROCESAMIENTO INTEGRADO - REPORTE DIARIO',
            True
        )

    ##########################################################################################
    #  Menú seis: Ayuda
    ##########################################################################################

    def acerca_de(self):
        mensaje = (
            "<h3>Red Sísmica de Alerta - RSA</h3>"
            "<p><b>PROCESAMIENTO INTEGRADO</b></p>"
            "<p>Sistema integral para adquisición, análisis, picado de fases, "
            "procesamiento sismológico y generación de reportes institucionales.</p>"
            "<p><i>Universidad de Cuenca — Red Sísmica del Austro</i></p>"
        )
        QMessageBox.about(self, 'Acerca de - RSA', mensaje)

    ##########################################################################################
    #  Métodos de estado de menús y salida
    ##########################################################################################

    def accion_salir_ejecutar(self):
        """
        Maneja la acción de Salir de forma jerárquica:
        - Si está en Estado B (Día inicializado): Regresa al Estado A (Inicial / No inicializado),
          deshabilitando los menús de procesamiento y volviendo a mostrar 'Inicialización de día'.
        - Si está en Estado A (Inicial / No inicializado): Cierra completamente la aplicación.
        """
        if self.datos_inicializados:
            print("=== REGRESANDO DE ESTADO B (TRABAJO) A ESTADO A (INICIAL) ===")
            self.limpiar_estado_completo()
            self.configurar_estado_inicial()
        else:
            print("=== CERRANDO APLICACIÓN DESDE ESTADO A ===")
            self.close()

    def actualizar_titulo(self, texto, mostrar_detalles):
        """Actualiza el título de la ventana y etiqueta superior con el estado activo"""
        self.setWindowTitle(texto)

        if mostrar_detalles and self.datos_inicializados:
            if self.periodo != '':
                detalles = f'Directorio: {self.directorio_trabajo}\nDía: {self.archivo}\nPeriodo: {self.periodo}\nUsuario: {self.responsable}'
            else:
                detalles = f'Directorio: {self.directorio_trabajo}\nDía: PERIODO \nPeriodo: Completo\nUsuario: {self.responsable}'
            self.etiqueta_titulo.setText(detalles)
        elif mostrar_detalles and not self.datos_inicializados:
            self.etiqueta_titulo.setText(texto)
        else:
            self.etiqueta_titulo.setText(texto)

    def habilitar_menus(self):
        """Habilita menús en estado de trabajo (Estado B) según el modo activo (Diario vs Período)"""
        self.menu_inicio.setEnabled(True)
        if self.periodo == '':
            # MODO PERÍODO / CONSOLIDADO
            self.menu_configuracion.setEnabled(True)
            self.menu_informes.setEnabled(True)
            self.menu_procesamiento.setEnabled(False)
            self.menu_otros_informes.setEnabled(False)
        else:
            # MODO DIARIO
            self.menu_procesamiento.setEnabled(True)
            self.menu_otros_informes.setEnabled(True)
            self.menu_configuracion.setEnabled(False)
            self.menu_informes.setEnabled(False)
        self.menu_ayuda.setEnabled(True)
        self.accion_inicializar_dia.setVisible(False)
        self.accion_salir.setVisible(True)

    def deshabilitar_menus(self):
        """Deshabilita menús (estado inicial o dentro de subprograma)"""
        self.menu_configuracion.setEnabled(False)
        self.menu_informes.setEnabled(False)
        self.menu_procesamiento.setEnabled(False)
        self.menu_otros_informes.setEnabled(False)
        if self.widget_activo is not None:
            self.menu_inicio.setEnabled(False)
        else:
            self.menu_inicio.setEnabled(True)
            self.accion_inicializar_dia.setVisible(True)
            self.accion_salir.setVisible(True)

    def paintEvent(self, event):
        # Solo dibujar la marca de agua cuando no hay ningún subprograma cargado
        if self.widget_activo is not None:
            return

        painter = QPainter(self)
        ruta_marca = resolver_ruta_recurso('logo rsa.png')
        if not os.path.exists(ruta_marca):
            ruta_marca = resolver_ruta_recurso('logo ucuenca.png')

        pixmap = QPixmap(ruta_marca)
        if not pixmap.isNull():
            tamano_ventana = self.size()
            
            # Escalar proporcionalmente (+50% de tamaño: ~68% de la ventana)
            ancho_deseado = int(tamano_ventana.width() * 0.68)
            alto_deseado = int(tamano_ventana.height() * 0.68)
            pixmap_escalado = pixmap.scaled(
                ancho_deseado, alto_deseado,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # Posicionar centrado en la zona de gráficos
            centro_graficos_x = int(tamano_ventana.width() * 0.60)
            x = centro_graficos_x - (pixmap_escalado.width() // 2)
            y = (tamano_ventana.height() - pixmap_escalado.height()) // 2

            painter.setOpacity(0.18)
            painter.drawPixmap(x, y, pixmap_escalado)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.showMaximized()
    sys.exit(app.exec_())
