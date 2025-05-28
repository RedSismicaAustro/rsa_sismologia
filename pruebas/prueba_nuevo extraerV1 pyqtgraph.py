import sys
import os
from pathlib import Path

def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))





if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)



from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QComboBox, QMessageBox, QCalendarWidget
)
from PyQt5.QtCore import QThreadPool, Qt, QTimer
from obspy import UTCDateTime
import numpy as np
import pyqtgraph as pg
from lectura_datos import CargarDatosRunnable
from metodos_gestion import obtener_directorios, parametros_estaciones




class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor de MSEED con PyQtGraph")
        self.pool_trabajo = QThreadPool()

        self.directorio_trabajo = 'C:/DIA'
        self.rango_extraccion = 12 * 60
        self.rango_visualizacion = 6 * 60
        self.paso_desplazamiento = 60
        self.estaciones_por_pagina = 5
        self.indice_pagina = 0
        self.tiempos = []
        self.lineas_rojas = []
        self.linea_verde = None

        self.parametros = parametros_estaciones()
        self.estaciones = self.parametros['CODIGO']
        self.componentes = self.parametros['COMPONENTE']
        self.hab_grafico = self.parametros['HAB_GRAFICO']
        self.datos_por_estacion = {}
        self.estaciones_con_datos = []

        self.archivo = None
        self.archivos_mseed = []
        self.directorio_registros = None
        self.centro_inicial = None
        self.centro_actual = None

        # UI
        self.calendario = QCalendarWidget()
        self.calendario.clicked.connect(self.seleccionar_fecha)
        self.comboHoras = QComboBox()
        self.comboHoras.setFixedWidth(200)
        self.comboHoras.currentIndexChanged.connect(self.cargar_datos)
        self.botonAvanzar = QPushButton("Avanzar +1 min")
        self.botonAvanzar.clicked.connect(self.avanzar_ventana)
        self.botonRetroceder = QPushButton("Retroceder -1 min")
        self.botonRetroceder.clicked.connect(self.retroceder_ventana)
        self.botonSiguienteEstaciones = QPushButton("Siguientes Estaciones")
        self.botonSiguienteEstaciones.clicked.connect(self.mostrar_siguientes_estaciones)
        self.etiquetaArchivo = QLabel("Archivo: Ninguno")
        self.etiquetaPagina = QLabel("Página: 1")

        # Gráfico PyQtGraph
        self.widget_pg = pg.GraphicsLayoutWidget()
        self.widget_pg.setBackground('w')
        self.plots_pg = []
        self.lineas_rojas_pg = []
        self.linea_verde_pg = None

        # Layouts
        layoutControles = QVBoxLayout()
        layoutControles.addWidget(QLabel("Selecciona Fecha"))
        layoutControles.addWidget(self.calendario)
        layoutControles.addWidget(QLabel("Selecciona Hora"))
        layoutControles.addWidget(self.comboHoras)
        layoutControles.addWidget(self.etiquetaArchivo)
        layoutControles.addWidget(self.etiquetaPagina)
        layoutControles.addWidget(self.botonRetroceder)
        layoutControles.addWidget(self.botonAvanzar)
        layoutControles.addWidget(self.botonSiguienteEstaciones)
        layoutControles.addStretch()

        layoutGrafico = QVBoxLayout()
        layoutGrafico.addWidget(self.widget_pg)

        layoutPrincipal = QHBoxLayout()
        layoutPrincipal.addLayout(layoutControles)
        layoutPrincipal.addLayout(layoutGrafico)

        contenedor = QWidget()
        contenedor.setLayout(layoutPrincipal)
        self.setCentralWidget(contenedor)
        self.showMaximized()

        self.widget_pg.scene().sigMouseClicked.connect(self.marcar_tiempo_pg)

    def seleccionar_fecha(self):
        fecha = self.calendario.selectedDate()
        self.base_dia = UTCDateTime(fecha.year(), fecha.month(), fecha.day(), 0, 0, 0)
        self.archivo = os.path.join(self.directorio_trabajo, fecha.toString("yyMMdd") + "000000")
        self.directorios = obtener_directorios(self.archivo)
        self.etiquetaArchivo.setText(f"Archivo generado: {self.archivo}")

        self.comboHoras.clear()
        self.tiempos.clear()
        self.lineas_rojas.clear()
        self.linea_verde = None

        import json
        self.marcas_originales = []
        with open(self.directorios['archivo_marcas'], 'r') as f:
            marcas = json.load(f)
        for idx, marca in enumerate(marcas, start=1):
            if isinstance(marca, str):
                hora = UTCDateTime(marca).time
                texto_visible = f"Evento {idx}: {hora.hour:02d}:{hora.minute:02d}:{hora.second:02d}"
                self.comboHoras.addItem(texto_visible)
                self.marcas_originales.append(marca)

    def cargar_datos(self):
        idx = self.comboHoras.currentIndex()
        if idx < 0 or not self.marcas_originales:
            return

        self.tiempos.clear()
        self.lineas_rojas.clear()
        self.indice_pagina = 0

        self.directorio_registros = os.path.join(self.directorio_trabajo, self.directorios['Directorio_registros'])
        self.archivos_mseed = [
            os.path.join(self.directorio_registros, f)
            for f in os.listdir(self.directorio_registros)
            if f.endswith(".mseed")
        ]

        self.estaciones_eventos = []
        self.filtros_estaciones = []
        for archivo_mseed in self.archivos_mseed:
            archivo = os.path.basename(archivo_mseed)
            codigo = archivo[:4]
            if codigo in self.estaciones:
                indice = self.estaciones.index(codigo)
                self.estaciones_eventos.append(indice)
                self.filtros_estaciones.append('020110')

        self.estaciones_eventos_total = self.estaciones_eventos.copy()
        hora_iso = self.marcas_originales[idx]
        self.centro_inicial = UTCDateTime(hora_iso)
        self.centro_actual = self.centro_inicial
        self.linea_verde = self.centro_inicial.matplotlib_date

        tiempo_inicio = self.centro_inicial - self.rango_extraccion
        tiempo_final = self.centro_inicial + self.rango_extraccion

        tarea = CargarDatosRunnable(
            archivos_mseed=self.archivos_mseed,
            estaciones=self.estaciones,
            componentes=self.componentes,
            tiempo_inicio=tiempo_inicio,
            tiempo_final=tiempo_final
        )
        tarea.signals.terminado.connect(lambda datos: QTimer.singleShot(0, lambda: self.finalizar_carga_datos(datos)))
        tarea.signals.error.connect(lambda mensaje: QMessageBox.critical(self, "Error", mensaje))
        self.pool_trabajo.start(tarea)

    def finalizar_carga_datos(self, datos_por_estacion):
        self.datos_por_estacion = datos_por_estacion
        self.estaciones_con_datos = [
            cod for cod in self.estaciones if cod in datos_por_estacion and self.hab_grafico[self.estaciones.index(cod)] == '1'
        ]
        self.etiquetaPagina.setText(f"Página: {self.indice_pagina + 1}")
        self.actualizar_grafico()

    def actualizar_grafico(self):
        if not self.estaciones_con_datos:
            return

        self.widget_pg.clear()
        self.plots_pg = []
        self.lineas_rojas_pg = []

        inicio = self.indice_pagina * self.estaciones_por_pagina
        fin = inicio + self.estaciones_por_pagina
        estaciones_pagina = self.estaciones_con_datos[inicio:fin]

        ventana_inicio = self.centro_actual - self.rango_visualizacion
        ventana_final = self.centro_actual + self.rango_visualizacion

        for idx in range(self.estaciones_por_pagina):
            if idx < len(estaciones_pagina):
                codigo = estaciones_pagina[idx]
                datos_estacion = self.datos_por_estacion[codigo]

                tiempos = datos_estacion['tiempos']
                datos = datos_estacion['datos']
                mask = (tiempos >= ventana_inicio.matplotlib_date) & (tiempos <= ventana_final.matplotlib_date)

                if not np.any(mask):
                    continue

                tiempo_filtrado = tiempos[mask]
                datos_filtrados = datos[mask]

                p = self.widget_pg.addPlot(row=idx, col=0)
                p.plot(tiempo_filtrado, datos_filtrados, pen=pg.mkPen('b', width=1))
                p.showGrid(x=True, y=True)
                p.setLabel('left', codigo)
                self.plots_pg.append(p)

                if self.linea_verde:
                    linea_verde = pg.InfiniteLine(pos=self.linea_verde, angle=90, pen=pg.mkPen('g', width=1.5, style=Qt.DashLine))
                    p.addItem(linea_verde)

                for x in self.lineas_rojas:
                    linea_roja = pg.InfiniteLine(pos=x, angle=90, pen=pg.mkPen('r', style=Qt.DashLine))
                    p.addItem(linea_roja)

    def marcar_tiempo_pg(self, event):
        if event.button() != Qt.RightButton:
            return

        escena_pos = event.scenePos()
        for p in self.plots_pg:
            vb = p.getViewBox()
            if vb.sceneBoundingRect().contains(escena_pos):
                mouse_point = vb.mapSceneToView(escena_pos)
                x = mouse_point.x()

                tolerancia = (vb.viewRange()[0][1] - vb.viewRange()[0][0]) * 0.005
                for i, t in enumerate(self.tiempos):
                    if abs(x - t.matplotlib_date) < tolerancia:
                        self.tiempos.pop(i)
                        self.lineas_rojas.pop(i)
                        self.actualizar_grafico()
                        return

                if len(self.tiempos) < 2:
                    tiempo = pg.datetime.datetime.fromtimestamp(x * 86400)  # matplotlib date to seconds
                    utc = UTCDateTime(tiempo)
                    self.tiempos.append(utc)
                    self.lineas_rojas.append(x)
                    self.actualizar_grafico()
                break

    def avanzar_ventana(self):
        nuevo_centro = self.centro_actual + self.paso_desplazamiento
        if nuevo_centro + self.rango_visualizacion <= self.centro_inicial + self.rango_extraccion:
            self.centro_actual = nuevo_centro
            self.actualizar_grafico()

    def retroceder_ventana(self):
        nuevo_centro = self.centro_actual - self.paso_desplazamiento
        if nuevo_centro - self.rango_visualizacion >= self.centro_inicial - self.rango_extraccion:
            self.centro_actual = nuevo_centro
            self.actualizar_grafico()

    def mostrar_siguientes_estaciones(self):
        total_paginas = (len(self.estaciones_con_datos) - 1) // self.estaciones_por_pagina + 1
        self.indice_pagina = (self.indice_pagina + 1) % total_paginas
        self.etiquetaPagina.setText(f"Página: {self.indice_pagina + 1}")
        self.actualizar_grafico()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())
