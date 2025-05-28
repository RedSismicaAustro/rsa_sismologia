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
ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)


from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QDialog, QCheckBox, QSpinBox, QLabel, QComboBox, QMessageBox, QCalendarWidget
)
from PyQt5 import uic
from obspy import UTCDateTime, read
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from metodos_gestion import obtener_directorios, parametros_estaciones



class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor de MSEED por Día con Paginación")
        # Variables
        self.archivo = None
        self.directorio_trabajo = 'G:/Mi unidad/DIA'
        self.directorio_registros = None
        self.archivos_mseed = []
        self.datos_por_estacion = {}
        self.centro_inicial = None
        self.centro_actual = None
        self.rango_extraccion = 12 * 60
        self.rango_visualizacion = 6 * 60
        self.paso_desplazamiento = 1 * 60
        self.estaciones_por_pagina = 5
        self.indice_pagina = 0
        self.tiempos = []
        self.lineas_rojas = []
        self.linea_verde = None

        # Parametros iniciales
        self.parametros = parametros_estaciones()
        self.estaciones = self.parametros['CODIGO']
        self.componentes = self.parametros['COMPONENTE']
        self.estaciones_con_datos = []
        self.estaciones_eventos = []
        self.estaciones_eventos_total = []
        self.filtros_estaciones = []

        # Widgets
        self.calendario = QCalendarWidget()
        self.calendario.setFixedWidth(250)
        self.calendario.clicked.connect(self.seleccionar_fecha)

        self.comboHoras = QComboBox()
        self.comboHoras.setFixedWidth(200)
        self.comboHoras.currentIndexChanged.connect(self.cargar_datos)

        self.botonRetroceder = QPushButton("Retroceder -1 min")
        self.botonRetroceder.clicked.connect(self.retroceder_ventana)

        self.botonAvanzar = QPushButton("Avanzar +1 min")
        self.botonAvanzar.clicked.connect(self.avanzar_ventana)

        self.botonSiguienteEstaciones = QPushButton("Siguientes Estaciones")
        self.botonSiguienteEstaciones.clicked.connect(self.mostrar_siguientes_estaciones)

        self.botonCortar = QPushButton("Cortar señal")
        self.botonCortar.clicked.connect(self.cortar_senal)

        self.botonFiltrar = QPushButton("Filtrar señal (1–10 Hz)")
        self.botonFiltrar.clicked.connect(self.filtrar_senal)

        self.botonEstaciones = QPushButton("Estaciones")
        self.botonEstaciones.clicked.connect(self.abrir_dialogo_estaciones)

        self.botonSalir = QPushButton("Salir")
        self.botonSalir.clicked.connect(self.close)

        self.etiquetaArchivo = QLabel("Archivo: Ninguno")
        self.etiquetaPagina = QLabel("Página: 1")

        self.figura, self.ejes = plt.subplots(self.estaciones_por_pagina, 1, figsize=(10, 8), sharex=True)
        self.canvas = FigureCanvas(self.figura)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layoutControles = QVBoxLayout()
        layoutControles.addWidget(QLabel("Selecciona Fecha"))
        layoutControles.addWidget(self.calendario)
        layoutControles.addWidget(QLabel("Selecciona Hora (Desde archivo de marcas)"))
        layoutControles.addWidget(self.comboHoras)
        layoutControles.addWidget(self.etiquetaArchivo)
        layoutControles.addWidget(self.etiquetaPagina)
        layoutControles.addWidget(self.botonRetroceder)
        layoutControles.addWidget(self.botonAvanzar)
        layoutControles.addWidget(self.botonSiguienteEstaciones)
        layoutControles.addWidget(self.botonCortar)
        layoutControles.addWidget(self.botonFiltrar)
        layoutControles.addWidget(self.botonEstaciones)
        layoutControles.addWidget(self.botonSalir)
        layoutControles.addStretch()

        layoutGrafico = QVBoxLayout()
        layoutGrafico.addWidget(self.toolbar)
        layoutGrafico.addWidget(self.canvas)

        layoutPrincipal = QHBoxLayout()
        layoutPrincipal.addLayout(layoutControles)
        layoutPrincipal.addLayout(layoutGrafico)

        contenedor = QWidget()
        contenedor.setLayout(layoutPrincipal)
        self.setCentralWidget(contenedor)
        self.showMaximized()
        self.canvas.mpl_connect("button_press_event", self.marcar_tiempo)


    def seleccionar_fecha(self):
        fecha = self.calendario.selectedDate()
        self.archivo = os.path.join(self.directorio_trabajo, fecha.toString("yyMMdd") + "000000")
        self.directorios = obtener_directorios(self.archivo)
        self.etiquetaArchivo.setText(f"Archivo generado: {self.archivo}")
        self.comboHoras.clear()
        self.marcas_originales = []
        self.linea_verde = None
        self.cargar_horas_desde_json()

    def cargar_horas_desde_json(self):
        self.comboHoras.blockSignals(True)
        self.comboHoras.clear()
        self.comboHoras.addItem("")
        import json
        with open(self.directorios['archivo_marcas'], 'r') as f:
            marcas = json.load(f)

        for idx, marca in enumerate(marcas, start=1):
            if isinstance(marca, str):
                hora = UTCDateTime(marca).time
                texto_visible = f"Evento {idx}:   -   {hora.hour:02d}:{hora.minute:02d}:{hora.second:02d}"
                self.comboHoras.addItem(texto_visible)
                self.marcas_originales.append(marca)
            elif isinstance(marca, list) and marca:
                hora = UTCDateTime(marca[0]).time
                texto_visible = f"Evento {idx}:   -   {hora.hour:02d}:{hora.minute:02d}:{hora.second:02d}"
                self.comboHoras.addItem(texto_visible)
                self.marcas_originales.append(marca[0])
        self.comboHoras.setCurrentIndex(0)
        self.comboHoras.blockSignals(False)

    def cargar_datos(self):
        indice = self.comboHoras.currentIndex()
        if indice <= 0:
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
            codigo = archivo[0:4]
            indice_estacion=self.estaciones.index(codigo)
            self.estaciones_eventos.append(indice_estacion)
            self.filtros_estaciones.append("000000")
        self.estaciones_eventos=sorted(self.estaciones_eventos)
        self.estaciones_eventos_total = self.estaciones_eventos.copy()
        hora_iso = self.marcas_originales[indice - 1]
        self.centro_inicial = UTCDateTime(hora_iso)
        self.centro_actual = self.centro_inicial
        self.linea_verde = self.centro_inicial.matplotlib_date

        tiempo_inicio = self.centro_inicial - self.rango_extraccion
        tiempo_final = self.centro_inicial + self.rango_extraccion
        self.datos_por_estacion.clear()

        for archivo in self.archivos_mseed:
            nombre = os.path.basename(archivo)
            codigo = nombre.split('_')[0]
            if codigo in self.estaciones:
                idx = self.estaciones.index(codigo)
                componente = int(self.componentes[idx]) - 1
                st = read(archivo, starttime=tiempo_inicio, endtime=tiempo_final)
                if len(st) > componente:
                    traza = st[componente]
                    tiempos = np.array(traza.times("matplotlib"))
                    datos = np.array(traza.data)
                    self.datos_por_estacion[codigo] = {
                        'codigo': codigo,
                        'tiempos': tiempos,
                        'datos': datos
                    }

        self.estaciones_con_datos = [
            codigo for codigo in self.estaciones_eventos
            if codigo in self.datos_por_estacion
        ]
        print(self.estaciones_con_datos)
        self.indice_pagina = 0
        self.etiquetaPagina.setText(f"Página: {self.indice_pagina + 1}")
        self.actualizar_grafico()

    def actualizar_grafico(self):
        if not self.estaciones_con_datos:
            return

        inicio = self.indice_pagina * self.estaciones_por_pagina
        fin = inicio + self.estaciones_por_pagina
        estaciones_pagina = self.estaciones_con_datos[inicio:fin]

        self.figura.clf()
        self.ejes = self.figura.subplots(self.estaciones_por_pagina, 1, sharex=True)
        if self.estaciones_por_pagina == 1:
            self.ejes = [self.ejes]

        ventana_inicio = self.centro_actual - self.rango_visualizacion
        ventana_final = self.centro_actual + self.rango_visualizacion

        for idx in range(self.estaciones_por_pagina):
            eje_actual = self.ejes[self.estaciones_por_pagina - idx - 1]
            if idx < len(estaciones_pagina):
                codigo = estaciones_pagina[idx]
                estacion = self.datos_por_estacion[codigo]
                mask = (estacion['tiempos'] >= ventana_inicio.matplotlib_date) & \
                       (estacion['tiempos'] <= ventana_final.matplotlib_date)
                if np.any(mask):
                    eje_actual.plot_date(estacion['tiempos'][mask], estacion['datos'][mask], '-', color='blue')
                eje_actual.set_ylabel(codigo)
            else:
                eje_actual.set_ylabel("")

        self.ejes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.figura.autofmt_xdate()
        self.redibujar_lineas_rojas()

        if self.linea_verde is not None:
            for eje in self.ejes:
                eje.axvline(self.linea_verde, color='green', linestyle='--', linewidth=1.5)
        self.canvas.draw()

    def redibujar_lineas_rojas(self):
        for linea in self.lineas_rojas:
            for eje in self.ejes:
                eje.axvline(linea, color='red', linestyle='--')

    def marcar_tiempo(self, event):
        if event.button != 3 or event.xdata is None:
            return

        x = event.xdata
        tolerancia = (self.ejes[0].get_xlim()[1] - self.ejes[0].get_xlim()[0]) * 0.005
        for i, t in enumerate(self.tiempos):
            if abs(x - t.matplotlib_date) < tolerancia:
                self.tiempos.pop(i)
                self.lineas_rojas.pop(i)
                self.actualizar_grafico()
                return

        if len(self.tiempos) < 2:
            utc = UTCDateTime(mdates.num2date(x))
            self.tiempos.append(utc)
            self.lineas_rojas.append(x)
            self.actualizar_grafico()

    def avanzar_ventana(self):
        nuevo = self.centro_actual + self.paso_desplazamiento
        if nuevo + self.rango_visualizacion <= self.centro_inicial + self.rango_extraccion:
            self.centro_actual = nuevo
            self.actualizar_grafico()

    def retroceder_ventana(self):
        nuevo = self.centro_actual - self.paso_desplazamiento
        if nuevo - self.rango_visualizacion >= self.centro_inicial - self.rango_extraccion:
            self.centro_actual = nuevo
            self.actualizar_grafico()

    def mostrar_siguientes_estaciones(self):
        total = (len(self.estaciones_con_datos) - 1) // self.estaciones_por_pagina + 1
        self.indice_pagina = (self.indice_pagina + 1) % total
        self.etiquetaPagina.setText(f"Página: {self.indice_pagina + 1}")
        self.actualizar_grafico()

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
        for codigo in self.estaciones_eventos:
            try:
                archivo = next(f for f in self.archivos_mseed if os.path.basename(f).startswith(str(codigo)))
                idx = self.estaciones_eventos_total.index(codigo)
                filtro = self.filtros_estaciones[idx]
                if filtro != '000000':
                    orden = int(filtro[0:2])
                    f_inf = int(filtro[2:4])
                    f_sup = int(filtro[4:6])
                    st = read(archivo, starttime=self.centro_actual - self.rango_extraccion,
                              endtime=self.centro_actual + self.rango_extraccion)
                    componente = int(self.componentes[self.estaciones.index(codigo)]) - 1
                    if len(st) > componente:
                        traza = st[componente]
                        traza.filter("bandpass", freqmin=f_inf, freqmax=f_sup, corners=orden, zerophase=True)
                        self.datos_por_estacion[codigo]['tiempos'] = np.array(traza.times("matplotlib"))
                        self.datos_por_estacion[codigo]['datos'] = np.array(traza.data)
            except Exception as e:
                print(f"Error al filtrar {codigo}: {e}")
        self.actualizar_grafico()

    def abrir_dialogo_estaciones(self):
        dialogo = estaciones_(
            hab_grafico={codigo: '1' for codigo in self.estaciones_eventos},
            estaciones_eventos=self.estaciones_eventos.copy(),
            filtros=self.filtros_estaciones.copy(),
            parent=self
        )
        dialogo.exec_()
        self.actualizar_grafico()

class estaciones_(QDialog):
    def __init__(self, hab_grafico, estaciones_eventos, filtros, parent=None):
        super(estaciones_, self).__init__()
        self.parent = parent
        self.parametros = parametros_estaciones()
        self.estaciones_eventos = estaciones_eventos
        print(self.estaciones_eventos)
        self.filtros = filtros
        self.numero_estaciones = len(self.estaciones_eventos)
        self.hab_grafico = hab_grafico

        self.setFixedSize(500, 480)
        ruta_ui = os.path.join(ruta_proyecto, "src", "ui", "secundaria.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        self.ck_box_hab_canal = {}
        self.lbl_nombre = {}
        self.lbl_codigo = {}
        self.ck_box_filtro = {}
        self.spbox_fil_orden = {}
        self.spbox_fil_finf = {}
        self.spbox_fil_fsup = {}
        self.spbox_canal = {}

        nombre_canal_total = self.parametros['NOMBRE']
        nombre_canal = self.parametros['CODIGO']
        componente_canal = self.parametros['COMPONENTE']

        for i in range(self.numero_estaciones):
            canal_ = self.estaciones_eventos[i]
            self.lbl_nombre[i] = QLabel(nombre_canal_total[canal_], self)
            self.lbl_nombre[i].setGeometry(15, i * 25 + 35, 130, 24)

            self.lbl_codigo[i] = QLabel(nombre_canal[canal_], self)
            self.lbl_codigo[i].setGeometry(150, i * 25 + 35, 50, 24)

            self.ck_box_hab_canal[i] = QCheckBox(self)
            self.ck_box_hab_canal[i].setGeometry(208, i * 25 + 35, 20, 24)
            self.ck_box_hab_canal[i].setChecked(self.hab_grafico.get(canal_, '1') == '1')

            self.spbox_canal[i] = QSpinBox(self)
            self.spbox_canal[i].setGeometry(250, i * 25 + 35, 40, 24)
            self.spbox_canal[i].setRange(1, 3)
            self.spbox_canal[i].setValue(int(componente_canal[canal_]))

            idx = self.parent.estaciones_eventos_total.index(canal_)
            orden = int(self.filtros[idx][0:2])
            f_inf = int(self.filtros[idx][2:4])
            f_sup = int(self.filtros[idx][4:6])

            self.ck_box_filtro[i] = QCheckBox(self)
            self.ck_box_filtro[i].setGeometry(316, i * 25 + 35, 20, 24)
            self.ck_box_filtro[i].setChecked(orden > 0)

            self.spbox_fil_orden[i] = QSpinBox(self)
            self.spbox_fil_orden[i].setGeometry(360, i * 25 + 35, 40, 24)
            self.spbox_fil_orden[i].setRange(1, 10)
            self.spbox_fil_orden[i].setValue(orden or 2)

            self.spbox_fil_finf[i] = QSpinBox(self)
            self.spbox_fil_finf[i].setGeometry(402, i * 25 + 35, 40, 24)
            self.spbox_fil_finf[i].setRange(1, 10)
            self.spbox_fil_finf[i].setValue(f_inf or 1)

            self.spbox_fil_fsup[i] = QSpinBox(self)
            self.spbox_fil_fsup[i].setGeometry(442, i * 25 + 35, 40, 24)
            self.spbox_fil_fsup[i].setRange(5, 20)
            self.spbox_fil_fsup[i].setValue(f_sup or 10)

        # Checkbox para marcar todos
        self.lbl_todos = QLabel("PLOT TODOS", self)
        self.lbl_todos.setGeometry(140, 435, 150, 24)
        self.ck_box_todos = QCheckBox(self)
        self.ck_box_todos.setGeometry(210, 437, 20, 24)
        self.ck_box_todos.setChecked(True)

        self.lbl_filtros = QLabel("FILTRO TODOS", self)
        self.lbl_filtros.setGeometry(131, 455, 150, 24)
        self.ck_box_filtros = QCheckBox(self)
        self.ck_box_filtros.setGeometry(210, 457, 20, 24)
        self.ck_box_filtros.setChecked(False)

        self.ck_box_todos.toggled.connect(self.validar)
        self.ck_box_filtros.toggled.connect(self.validar_filtros)

    def validar(self):
        estado = self.ck_box_todos.checkState() == 2
        for i in range(self.numero_estaciones):
            self.ck_box_hab_canal[i].setChecked(estado)

    def validar_filtros(self):
        activar = self.ck_box_filtros.checkState() == 2
        for i in range(self.numero_estaciones):
            if self.ck_box_hab_canal[i].checkState() == 2:
                self.ck_box_filtro[i].setChecked(activar)

    def closeEvent(self, event):
        nuevas_estaciones = []
        for i in range(self.numero_estaciones):
            canal_ = self.estaciones_eventos[i]
            idx = self.parent.estaciones_eventos_total.index(canal_)
            if self.ck_box_hab_canal[i].isChecked():
                nuevas_estaciones.append(canal_)

            if self.ck_box_filtro[i].isChecked():
                orden = self.spbox_fil_orden[i].value()
                f_inf = self.spbox_fil_finf[i].value()
                f_sup = self.spbox_fil_fsup[i].value()
                self.parent.filtros_estaciones[idx] = f"{orden:02}{f_inf:02}{f_sup:02}"
            else:
                self.parent.filtros_estaciones[idx] = "000000"

        self.parent.estaciones_eventos = nuevas_estaciones


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())

