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

from PyQt5.QtCore import QThreadPool
from lectura_datos import CargarDatosRunnable


import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QDialog,QCheckBox,QSpinBox,
    QLabel, QDateTimeEdit, QComboBox, QMessageBox, QCalendarWidget
)
from PyQt5 import uic
from obspy import UTCDateTime, read
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from metodos_gestion import obtener_directorios, parametros_estaciones
from metodos_rsa import extraccion_
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer
class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.pool_trabajo = QThreadPool()
        
        self.setWindowTitle("Visor de MSEED por Día con Paginación")

        # Variables de control
        self.archivo = None
        self.directorio_registros = None
        self.archivos_mseed = []
        self.datos_por_estacion = {}  # {codigo_estacion: {datos}}
        self.centro_inicial = None
        self.centro_actual = None
        self.rango_extraccion = 12 * 60
        self.rango_visualizacion = 6 * 60
        self.paso_desplazamiento = 1 * 60
        self.estaciones_por_pagina = 5
        self.indice_pagina = 0
        #self.directorio_trabajo = 'G:\Mi unidad\DIA'
        self.directorio_trabajo = 'C:\DIA'
        self.tiempos = []  # ✅ Lista para guardar los tiempos marcados
        self.lineas_rojas = []  # ✅ Lista para guardar las líneas dibujadas

        # Carga parámetros inicial
        self.parametros = parametros_estaciones()
        self.estaciones = self.parametros['CODIGO']
        self.componentes = self.parametros['COMPONENTE']
        self.hab_grafico=self.parametros['HAB_GRAFICO']
        self.estaciones_con_datos = []

        # Widgets de control
        self.calendario = QCalendarWidget()
        self.calendario.setFixedWidth(250)
        self.calendario.clicked.connect(self.seleccionar_fecha)


        self.botonCortar = QPushButton("Cortar señal")
        self.botonCortar.clicked.connect(self.cortar_senal)

        self.botonFiltrar = QPushButton("Filtrar señal")
        self.botonFiltrar.clicked.connect(self.filtrar_senal)

        self.comboHoras = QComboBox()
        self.comboHoras.setFixedWidth(200)
        self.comboHoras.currentIndexChanged.connect(self.cargar_datos)

        self.botonSiguienteEstaciones = QPushButton("Siguientes Estaciones")
        self.botonSiguienteEstaciones.clicked.connect(self.mostrar_siguientes_estaciones)

        self.botonAvanzar = QPushButton("Avanzar +1 min")
        self.botonAvanzar.clicked.connect(self.avanzar_ventana)

        self.botonRetroceder = QPushButton("Retroceder -1 min")
        self.botonRetroceder.clicked.connect(self.retroceder_ventana)
        self.botonEstaciones = QPushButton("Estaciones")
        self.botonEstaciones.clicked.connect(self.abrir_dialogo_estaciones)


        # ComboBox para tipo de evento
        self.comboTipoEvento = QComboBox()
        self.comboTipoEvento.setFixedWidth(200)
        lista_filtros = ["Ruido", "FF", "FC","TELESISMO","SISMO","INDEFINIDO","Evento_local","CONTROL","REVISION"]
        self.comboTipoEvento.addItems(lista_filtros)
        
        # Botón para guardar evento
        self.botonGuardarEvento = QPushButton("Guardar Evento")
        self.botonGuardarEvento.clicked.connect(self.guardar_evento)


        self.botonRecargar = QPushButton("Recargar señal")
        self.botonRecargar.clicked.connect(self.recargar_senal)

        self.botonSalir = QPushButton("Salir")
        self.botonSalir.clicked.connect(self.close)

        self.etiquetaArchivo = QLabel("Archivo: Ninguno")
        self.etiquetaPagina = QLabel("Página: 1")

        # Canvas Matplotlib + Toolbar
        self.figura = Figure(figsize=(10, 8))
        self.ejes = [self.figura.add_subplot(self.estaciones_por_pagina, 1, i + 1) for i in range(self.estaciones_por_pagina)]
        self.canvas = FigureCanvas(self.figura)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Layout de controles
        layoutControles = QVBoxLayout()
        layoutControles.addWidget(QLabel("Selecciona Fecha"))
        layoutControles.addWidget(self.calendario)
        layoutControles.addWidget(QLabel("Selecciona Hora (Centro de la ventana de tiempo)"))


        #layoutControles.addWidget(self.selectorHora)
        layoutControles.addWidget(QLabel("Selecciona Hora (Desde archivo de marcas)"))
        layoutControles.addWidget(self.comboHoras)

        layoutControles.addWidget(self.etiquetaArchivo)
        layoutControles.addWidget(self.etiquetaPagina)
        layoutControles.addWidget(self.botonRetroceder)
        layoutControles.addWidget(self.botonAvanzar)
        layoutControles.addWidget(self.botonSiguienteEstaciones)
        layoutControles.addWidget(self.botonRecargar)
        layoutControles.addWidget(self.botonCortar)
        layoutControles.addWidget(self.botonFiltrar)
        layoutControles.addWidget(self.botonEstaciones)
        layoutControles.addWidget(QLabel("Tipo de Evento"))
        layoutControles.addWidget(self.comboTipoEvento)
        layoutControles.addWidget(self.botonGuardarEvento)
        
        layoutControles.addWidget(self.botonSalir)


        layoutControles.addStretch()

        # Layout de gráficos
        layoutGrafico = QVBoxLayout()
        layoutGrafico.addWidget(self.toolbar)
        layoutGrafico.addWidget(self.canvas)

        # Layout general
        layoutPrincipal = QHBoxLayout()
        layoutPrincipal.addLayout(layoutControles)
        layoutPrincipal.addLayout(layoutGrafico)

        contenedor = QWidget()
        contenedor.setLayout(layoutPrincipal)
        self.setCentralWidget(contenedor)

        self.showMaximized()

        # ✅ Conexión de eventos de clic para el canvas
        self.canvas.mpl_connect("button_press_event", self.marcar_tiempo)
        self.linea_verde = None  # Línea vertical verde del evento seleccionado

    def recargar_senal(self):
        self.cargar_datos()

    def seleccionar_fecha(self):
        fecha = self.calendario.selectedDate()
        self.base_dia = UTCDateTime(fecha.year(), fecha.month(), fecha.day(), 0, 0, 0)
        self.archivo = os.path.join(self.directorio_trabajo,fecha.toString("yyMMdd") + "000000")
        self.directorios=obtener_directorios(self.archivo)
        self.etiquetaArchivo.setText(f"Archivo generado: {self.archivo}")


        self.comboHoras.clear()  # Iniciar vacío para notar el cambio
        self.marcas_originales = []  # Resetear lista de marcas
        self.cargar_horas_desde_json()
        self.linea_verde = None



    def cargar_horas_desde_json(self):
        self.comboHoras.blockSignals(True)  # ⛔ Evita que se dispare el evento durante la carga
        self.comboHoras.clear()
        self.comboHoras.addItem("")  # Agrega línea en blanco como primer ítem
        import json
        with open(self.directorios['archivo_marcas'], 'r') as f:
                marcas = json.load(f)
            
        self.marcas_originales = []  # Guardamos las UTCDateTime originales
            
        # Asumimos que son strings ISO o listas tipo ["2024-05-20T14:00:00", "2024-05-20T14:10:00"]
        for idx, marca in enumerate(marcas, start=1):
                if isinstance(marca, str):
                    hora = UTCDateTime(marca).time
                    texto_visible = f"Evento {idx}:   -   {hora.hour:02d}:{hora.minute:02d}:{hora.second:02d}"
                    self.comboHoras.addItem(texto_visible)
                    self.marcas_originales.append(marca)
                elif isinstance(marca, list) and marca:
                    hora = UTCDateTime(marca[0]).time
                    texto_visible = f"Evento {idx}: {hora.hour:02d}:{hora.minute:02d}:{hora.second:02d}"
                    self.comboHoras.addItem(texto_visible)
                    self.marcas_originales.append(marca[0])
        self.comboHoras.setCurrentIndex(0)  # Apunta a la línea en blanco
        self.comboHoras.blockSignals(False)

    def cortar_senal(self):
        if len(self.tiempos) != 2:
            QMessageBox.warning(self, "Advertencia", "Debes marcar dos líneas rojas para cortar la señal.")
            return

        inicio, fin = sorted(self.tiempos)
        for estacion in self.datos_por_estacion.values():
            mask = (estacion['tiempos'] >= inicio.matplotlib_date) & (estacion['tiempos'] <= fin.matplotlib_date)
            estacion['tiempos'] = estacion['tiempos'][mask]
            estacion['datos'] = estacion['datos'][mask]

        self.actualizar_grafico()


    def filtrar_senal(self):
        from obspy import Trace
        import numpy as np

        for numero_estacion in self.estaciones_eventos:
            if self.hab_grafico[numero_estacion] != '1':
                continue  # Solo graficamos las estaciones habilitadas

            codigo_estacion = self.parametros['CODIGO'][numero_estacion]

            indice = self.estaciones_eventos.index(numero_estacion)
            filtro_str = self.filtros_estaciones[indice]

            if filtro_str == '000000':
                continue  # No aplicar filtro si no está definido

            orden = int(filtro_str[0:2])
            freq_min = int(filtro_str[2:4])
            freq_max = int(filtro_str[4:6])

            if codigo_estacion not in self.datos_por_estacion:
                continue

            try:
                datos = self.datos_por_estacion[codigo_estacion]['datos']
                tiempos = self.datos_por_estacion[codigo_estacion]['tiempos']
                sampling_rate = self.datos_por_estacion[codigo_estacion].get('fs', None)
                # Calcular duración en segundos

                traza = Trace(data=datos.copy())
                traza.stats.starttime = UTCDateTime(0)
                traza.stats.sampling_rate = sampling_rate

                traza.filter("bandpass", freqmin=freq_min, freqmax=freq_max,
                             corners=orden, zerophase=True)

                if not np.isfinite(traza.data).all():
                    print(f"❌ Filtro produjo datos inválidos en {codigo_estacion}")
                    continue


                self.datos_por_estacion[codigo_estacion]['datos'] = traza.data.copy()

            except Exception as e:
                print(f"❌ Error al filtrar estación {codigo_estacion}: {e}")

        self.actualizar_grafico()


    def guardar_evento(self):
        if len(self.tiempos) != 2:
            QMessageBox.warning(self, "Advertencia", "Debes marcar dos tiempos (líneas rojas) para definir el evento.")
            return

        t_inicio, t_final = sorted(self.tiempos)
        t_inicio = UTCDateTime(int(t_inicio.timestamp))         # truncar hacia abajo
        t_final = UTCDateTime(int(t_final.timestamp) + 1)       # redondear hacia arriba

        t_inicio_rel = t_inicio - self.base_dia
        t_final_rel = t_final - self.base_dia

        # Índice del evento
        indice_evento = self.comboHoras.currentIndex()
        if indice_evento <= 0:
            QMessageBox.warning(self, "Advertencia", "Debes seleccionar un evento válido.")
            return

        # Número de evento es simplemente el índice
        n_evento = indice_evento

        # Obtener tipo de evento desde el ComboBox de tipo
        tipo_evento = self.comboTipoEvento.currentText()

        # Inhabilitar ese evento en el ComboBox
        self.comboHoras.setItemData(indice_evento, 0, role=0x0100)  # Qt.UserRole

 
        extraccion_(
            archivo=self.archivo,
            n_evento=n_evento,
            tipo_evento=tipo_evento,
            t_inicio=t_inicio_rel,
            t_final=t_final_rel,
            estaciones_eventos_total=self.estaciones_eventos_total,
            estaciones_eventos=self.estaciones_eventos,
            filtros=self.filtros_estaciones
        )

        # Limpiar datos primero
        self.datos_por_estacion.clear()
        self.estaciones_con_datos.clear()
        self.tiempos.clear()
        self.lineas_rojas.clear()
        self.linea_verde = None

        # 🔄 Limpieza visual mínima sin destruir el canvas
        self.figura.clear()
        self.canvas.draw()

    def reiniciar_canvas(self):
        if hasattr(self, "canvas"):
            self.canvas.setParent(None)
        if hasattr(self, "toolbar"):
            self.toolbar.setParent(None)

        from matplotlib.figure import Figure
        self.figura = Figure(figsize=(10, 8))
        self.ejes = [self.figura.add_subplot(self.estaciones_por_pagina, 1, i + 1) for i in range(self.estaciones_por_pagina)]
        self.canvas = FigureCanvas(self.figura)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout_grafico = self.centralWidget().layout().itemAt(1).layout()
        layout_grafico.addWidget(self.toolbar)
        layout_grafico.addWidget(self.canvas)

        self.evento_click = self.canvas.mpl_connect("button_press_event", self.marcar_tiempo)



    def cargar_datos(self):
        print("✅ Cargando Datos")
        indice_seleccionado = self.comboHoras.currentIndex()
        if indice_seleccionado <= 0:
            return

        self.tiempos.clear()
        self.lineas_rojas.clear()
        directorios = obtener_directorios(self.archivo)
        self.directorio_registros = os.path.join(self.directorio_trabajo, directorios['Directorio_registros'])

        self.archivos_mseed = [
            os.path.join(self.directorio_registros, f)
            for f in os.listdir(self.directorio_registros)
            if f.endswith(".mseed")
            ]

        self.estaciones_eventos = []
        self.filtros_estaciones = []
        for archivo_mseed in self.archivos_mseed:
            archivo = os.path.basename(archivo_mseed)
            indice = self.parametros['CODIGO'].index(archivo[0:4])
            self.estaciones_eventos.append(int(self.parametros['NUM_ESTACION'][indice]))
            self.filtros_estaciones.append('020110')

        self.estaciones_eventos = sorted(self.estaciones_eventos)
        self.estaciones_eventos_total = self.estaciones_eventos

        hora_iso = self.marcas_originales[indice_seleccionado - 1]
        self.centro_inicial = UTCDateTime(hora_iso)
        self.centro_actual = self.centro_inicial
        self.linea_verde = self.centro_inicial.matplotlib_date
        tiempo_inicio = self.centro_inicial - self.rango_extraccion
        tiempo_final = self.centro_inicial + self.rango_extraccion

        # Cargar en segundo plano
        print("LLamando a lectura de datos")
        tarea = CargarDatosRunnable(
            archivos_mseed=self.archivos_mseed,
            estaciones=self.estaciones,
            componentes=self.componentes,
            tiempo_inicio=tiempo_inicio,
            tiempo_final=tiempo_final
            )
    
        # Definimos directamente qué hacer al terminar
        #tarea.signals.terminado.connect(lambda datos: self.finalizar_carga_datos(datos))
        tarea.signals.terminado.connect(lambda datos: QTimer.singleShot(0, lambda: self.finalizar_carga_datos(datos)))

        tarea.signals.error.connect(lambda mensaje: QMessageBox.critical(self, "Error", mensaje))
        self.pool_trabajo.start(tarea)


    def actualizar_grafico(self):
        if not self.estaciones_con_datos:
            return

        # 🔹 Paso 1: Desconectar evento anterior si existe
        if hasattr(self, 'evento_click'):
            self.canvas.mpl_disconnect(self.evento_click)

        # 🔹 Paso 2: Limpiar figura
        self.figura.clear()
    
        # 🔹 Paso 3: Crear subplots de nuevo
        self.ejes = [self.figura.add_subplot(self.estaciones_por_pagina, 1, i + 1) for i in range(self.estaciones_por_pagina)]

        if self.estaciones_por_pagina == 1:
            self.ejes = [self.ejes]
    

        # 🔹 Paso 4: Obtener datos y graficar
        inicio = self.indice_pagina * self.estaciones_por_pagina
        fin = inicio + self.estaciones_por_pagina
        estaciones_pagina = self.estaciones_con_datos[inicio:fin]

        ventana_inicio = self.centro_actual - self.rango_visualizacion
        ventana_final = self.centro_actual + self.rango_visualizacion

        for idx in range(self.estaciones_por_pagina):
            eje_actual = self.ejes[idx]

            if idx < len(estaciones_pagina):
                codigo_estacion = estaciones_pagina[idx]
                estacion = self.datos_por_estacion[codigo_estacion]
                mask = (estacion['tiempos'] >= ventana_inicio.matplotlib_date) & (estacion['tiempos'] <= ventana_final.matplotlib_date)

                if np.any(mask):
                    tiempos_filtrados = estacion['tiempos'][mask]
                    datos_filtrados = estacion['datos'][mask]
                    eje_actual.plot_date(tiempos_filtrados, datos_filtrados, '-', color='blue')

                eje_actual.set_ylabel(codigo_estacion)
            else:
                eje_actual.set_ylabel("")

        self.ejes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.figura.autofmt_xdate()

        self.redibujar_lineas_rojas()

        if self.linea_verde is not None:
            for eje in self.ejes:
                eje.axvline(self.linea_verde, color='green', linestyle='--', linewidth=1.5)
        # 🔹 Paso 5: Redibujar la figura limpia
        self.canvas.draw()
        # 🔹 Paso 6: Volver a conectar el evento del clic
        self.evento_click = self.canvas.mpl_connect("button_press_event", self.marcar_tiempo)


    def redibujar_lineas_rojas(self):
        for linea in self.lineas_rojas:
            for eje in self.ejes:
                eje.axvline(linea, color='red', linestyle='--')

    def marcar_tiempo(self, event):
        if event.button != 3:  # Click derecho
            return

        if event.xdata is None:
            return

        x_click = event.xdata

        # Verificar si se hizo clic cerca de una línea existente para eliminarla
        tolerancia = (self.ejes[0].get_xlim()[1] - self.ejes[0].get_xlim()[0]) * 0.005
        for idx, tiempo in enumerate(self.tiempos):
            tiempo_plot = tiempo.matplotlib_date
            if abs(x_click - tiempo_plot) < tolerancia:
                # Eliminar la línea
                self.tiempos.pop(idx)
                self.lineas_rojas.pop(idx)
                self.actualizar_grafico()
                return

        # Si no hay línea cercana y hay menos de 2 marcas, agregar nueva línea
        if len(self.tiempos) < 2:
            tiempo_marcado = mdates.num2date(x_click)
            utc_marcado = UTCDateTime(tiempo_marcado)
            self.tiempos.append(utc_marcado)
            self.lineas_rojas.append(x_click)
            self.actualizar_grafico()

    def avanzar_ventana(self):
        if not self.centro_actual:
            return

        nuevo_centro = self.centro_actual + self.paso_desplazamiento
        limite_superior = self.centro_inicial + self.rango_extraccion

        if nuevo_centro + self.rango_visualizacion <= limite_superior:
            self.centro_actual = nuevo_centro
            self.actualizar_grafico()
        else:
            QMessageBox.information(self, "Límite alcanzado", "No se puede avanzar más allá del rango cargado.")

    def retroceder_ventana(self):
        if not self.centro_actual:
            return

        nuevo_centro = self.centro_actual - self.paso_desplazamiento
        limite_inferior = self.centro_inicial - self.rango_extraccion

        if nuevo_centro - self.rango_visualizacion >= limite_inferior:
            self.centro_actual = nuevo_centro
            self.actualizar_grafico()
        else:
            QMessageBox.information(self, "Límite alcanzado", "No se puede retroceder más allá del rango cargado.")

    def mostrar_siguientes_estaciones(self):
        total_paginas = (len(self.estaciones_con_datos) - 1) // self.estaciones_por_pagina + 1

        self.indice_pagina += 1
        if self.indice_pagina >= total_paginas:
            self.indice_pagina = 0

        self.etiquetaPagina.setText(f"Página: {self.indice_pagina + 1}")
        self.actualizar_grafico()

    def abrir_dialogo_estaciones(self):
        #estaciones_(self.hab_grafico,self.estaciones_eventos,self.filtros_estaciones,self).exec_()


        dialogo = estaciones_(
            hab_grafico=self.hab_grafico,
            estaciones_eventos=self.estaciones_eventos,
            filtros=self.filtros_estaciones,
            parent=self
            )
        dialogo.exec_()
        self.actualizar_grafico()


    def finalizar_carga_datos(self, datos_por_estacion):
        print("✅ Datos recibidos en hilo principal")
        self.datos_por_estacion = datos_por_estacion

        if not datos_por_estacion:
            QMessageBox.warning(self, "Advertencia", "No se encontraron datos válidos.")
            return

        self.estaciones_con_datos = [
            codigo for codigo in self.estaciones if codigo in datos_por_estacion
            ]   
        self.indice_pagina = 0
        self.etiquetaPagina.setText(f"Página: {self.indice_pagina + 1}")
        print("✅ Redibujando canvas...")
        self.reiniciar_canvas()
        self.actualizar_grafico()




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


        self.parent.estaciones_con_datos = [
            self.parametros['CODIGO'][num]
            for num in self.parent.estaciones_eventos
            if self.parent.hab_grafico[num] == '1'
        ]

    def Salir_(self):
        self.destroy()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())