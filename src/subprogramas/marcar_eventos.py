
import numpy as np
from obspy import read
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout,QHBoxLayout, QScrollArea, QWidget 
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import uic
import os
import obspy

from librerias.metodos_rsa import parametros_estaciones
from librerias.metodos_gestion import obtener_directorios
from librerias.metodos_sismicos import diezmar_senal
import json
from PyQt5.QtCore import pyqtSignal
class CustomScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def wheelEvent(self, event):
        # Verificar si la tecla Shift está presionada
        if event.modifiers() == Qt.ShiftModifier:
            # Desplazamiento horizontal cuando Shift está presionado
            delta = event.angleDelta().y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
        else:
            # Desplazamiento vertical por defecto
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - event.angleDelta().y())


import gc

class Marcar_evento(QWidget):
    cerrado = pyqtSignal()  # señal que se emite al cerrar

    def __getattr__(self, name):
        """Delegación transparente de atributos y widgets hacia la interfaz cargada"""
        if 'ui' in self.__dict__ and hasattr(self.ui, name):
            return getattr(self.ui, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __init__(self, archivo, directorio_trabajo, responsable, periodo, parent=None):
        super().__init__(parent)
        print("Entrando a subprograma marcar eventos")

        self.directorio_trabajo = directorio_trabajo
        self.archivo = archivo
        self.responsable = responsable
        self.periodo = periodo
        self.setWindowTitle("MARCADO DE EVENTOS")

        self.archivos_mseed = []
        self.mapa_estaciones = parametros_estaciones()
        self.marcas = []

        # Configurar layout principal horizontal
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(5, 5, 5, 5)

        # Panel izquierdo: Cargar interfaz .ui directamente
        RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
        RAIZ_PROYECTO = os.path.join(RAIZ_PROYECTO, "..")
        ruta_ui = os.path.abspath(os.path.join(RAIZ_PROYECTO, "ui", 'marcar_eventos.ui'))
        self.ui = uic.loadUi(ruta_ui)
        self.ui.setFixedWidth(260)
        layout_principal.addWidget(self.ui)


        # Panel derecho: Visor en Scroll Area
        self.figura = Figure(figsize=(72, 6), dpi=100)
        self.canvas = FigureCanvas(self.figura)
        self.scroll_area = CustomScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout_principal.addWidget(self.scroll_area, 4)

        # Conectar los botones a funciones
        self.btn_anterior.clicked.connect(lambda: self.navegar_segmento(-1))
        self.btn_siguiente.clicked.connect(lambda: self.navegar_segmento(1))
        self.btn_increase_amp.clicked.connect(lambda: self.ajustar_amplitud(2.0))
        self.btn_decrease_amp.clicked.connect(lambda: self.ajustar_amplitud(0.5))
        self.boton_salir.clicked.connect(self.salir)
        self.lista_mseed.itemClicked.connect(self.seleccionar_grafico_mseed)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self.actualizar_hora)
        self.barra_horas.valueChanged.connect(self.cambiar_periodo_por_barra)

        self.stream = None
        self.segmento_actual = 0
        self.amplitude_factor = 1.0

        # Guardar el estado de la posición actual
        self.posicion_segmento_guardada = 0
        self.posicion_scroll_guardada = 0
        # Conectar el evento de clic del ratón
        self.canvas.mpl_connect('button_press_event', self.marcar_o_borrar_cruz)
        # Inicializar la interfaz
        self.cambio_de_fecha()


    def procesar_y_graficar(self):
        if not self.stream:
            return
        self.figura.clear()
        self.ax = self.figura.add_subplot(111)  # Save the axes as an attribute
        self.graficar_segmento()
        self.graficar_marcas()
        duracion_segmento = 2 * 3600  # 2 horas en segundos
        duracion_linea = 6 * 60  # 6 minutos en segundos
        self.inicio_segmento = self.stream[0].stats.starttime + self.segmento_actual * duracion_segmento
        # Calculamos el tiempo de finalización, considerando que puede ser menor al segmento completo
        fin_segmento = min(self.inicio_segmento + duracion_segmento, self.stream[0].stats.endtime)
        segmento = self.stream[0].slice(starttime=self.inicio_segmento, endtime=fin_segmento)
        segmento.detrend(type='constant')
        # Calculamos el número de líneas basado en la duración real del segmento
        duracion_segmento_real = fin_segmento - self.inicio_segmento
        num_lineas = int(duracion_segmento_real / duracion_linea)
        y_offset = 0
        for j in range(num_lineas):
            t_linea_inicio = self.inicio_segmento + j * duracion_linea
            t_linea_fin = t_linea_inicio + duracion_linea
            linea = segmento.slice(starttime=t_linea_inicio, endtime=t_linea_fin)
            tiempo = np.linspace(0, duracion_linea, len(linea.data)) / 60  # Tiempo en minutos
            self.ax.plot(tiempo, linea.data * self.amplitude_factor + y_offset, 'k-', linewidth=0.5)  # Línea continua más fina
            y_offset -= 2000  # Ajuste vertical entre líneas
        self.ax.set_xlim(0, 6)  # Eje X muestra 6 minutos en total
        self.ax.set_ylim(-2000 * num_lineas, 2000)
        self.ax.set_yticks([])
        self.ax.set_xticks([])  # Eliminar marcas de tiempo en el eje x
        self.ax.set_yticklabels([])  # Eliminar etiquetas del eje y
        for t in self.marcas:
            if t>self.inicio_segmento and t<fin_segmento:
                tiempo_relativo = (t - self.inicio_segmento)  # Convertir a minutos
                num_linea = int(tiempo_relativo / 360)
                x = (tiempo_relativo - (num_linea) * 360)/60
                y = -2000 * num_linea
                self.ax.plot(x, y, 'r+', markersize=30, mew=3, alpha=0.8)
        # Ajustar para ocupar todo el espacio
        self.figura.tight_layout(pad=0)
        # Calcular el ancho total de la figura en píxeles
        total_width = self.figura.get_figwidth() * self.figura.dpi
        # Fijar el tamaño del canvas usando el ancho total calculado
        self.canvas.setFixedSize(int(total_width), self.canvas.height())
        self.canvas.draw()
        # Ancho visible, definiendo cuánto mostrar a la vez (ejemplo: 1 minuto de los 6)
        visible_width = self.scroll_area.viewport().width()  # Match the viewport width
        # Establecer el paso de la barra de desplazamiento en base al ancho visible
        self.scroll_area.horizontalScrollBar().setPageStep(int(visible_width))
        # Establecer el rango de desplazamiento para cubrir todo el gráfico
        self.scroll_area.horizontalScrollBar().setRange(0, int(total_width - visible_width))
        # Restaurar la posición del scrollbar si se ha guardado
        self.scroll_area.horizontalScrollBar().setValue(self.posicion_scroll_guardada)
        # Actualizar el label_1 con el período de 2 horas actual
        start_hour = self.inicio_segmento.hour
        end_hour = (start_hour + 2) % 24
        self.label_1.setText(f"Período de {start_hour:02d}:00 a {end_hour:02d}:00")
        # Actualizar la barra de horas
        self.barra_horas.setValue(self.segmento_actual)
        self.actualizar_hora(0)  # Inicializar la hora

    def graficar_segmento(self):
        duracion_segmento = 2 * 3600
        duracion_linea = 6 * 60
        self.inicio_segmento = self.stream[0].stats.starttime + self.segmento_actual * duracion_segmento
        fin_segmento = self.inicio_segmento + duracion_segmento
        segmento = self.stream[0].slice(starttime=self.inicio_segmento, endtime=fin_segmento)
        segmento.detrend(type='constant')
        num_lineas = int(duracion_segmento / duracion_linea)
        y_offset = 0
        for j in range(num_lineas):
            t_linea_inicio = self.inicio_segmento + j * duracion_linea
            t_linea_fin = t_linea_inicio + duracion_linea
            linea = segmento.slice(starttime=t_linea_inicio, endtime=t_linea_fin)
            tiempo = np.linspace(0, duracion_linea, len(linea.data)) / 60
            self.ax.plot(tiempo, linea.data * self.amplitude_factor + y_offset, 'k-', linewidth=0.5)
            y_offset -= 2000
        self.ax.set_xlim(0, 6)
        self.ax.set_ylim(-2000 * num_lineas, 2000)
        self.ax.set_yticks([])
        self.ax.set_xticks([])
        self.ax.set_yticklabels([])

    def actualizar_hora(self, valor):
        total_width = self.figura.get_figwidth() * self.figura.dpi
        tiempo_total = 2 * 3600  # 2 horas en segundos
        tiempo_relativo = (valor / total_width) * tiempo_total
        tiempo_absoluto = self.inicio_segmento + tiempo_relativo
        self.label_1.setText(f"Período de {self.inicio_segmento.hour:02d}:00 a {(self.inicio_segmento.hour + 2) % 24:02d}:00")

 
    def marcar_o_borrar_cruz(self, event):
        if event.inaxes == self.ax:
            # Obtener las coordenadas del clic
            x = event.xdata  # Tiempo en minutos mostrado en el eje X
            y = event.ydata  # Valor del eje Y donde se hizo clic
            num_linea = round(y / -2000)  # Calcula el número de línea basado en el desplazamiento Y
            # Calcular el tiempo relativo a la duración total visible (6 minutos)
            tiempo_relativo = x * 60 + (num_linea) * 360  # Convertir minutos a segundos
            # Encuentra el tiempo absoluto desde el inicio del segmento
            tiempo_absoluto = self.inicio_segmento + tiempo_relativo
            # Buscar si ya existe una marca cercana a este punto
            for i, t in enumerate(self.marcas):
                # Calcular la diferencia de tiempo en segundos entre la marca guardada y el clic
                diferencia_tiempo = abs(t - tiempo_absoluto)
                if diferencia_tiempo < 2:  # Si la diferencia es menor a 2 segundos, borrar la marca
                    self.marcas.pop(i)
                    print(f"Cruz eliminada en: {t.isoformat()}")
                    # Borrar todas las líneas de cruces y redibujar desde self.marcas
                    self.borrar_y_redibujar_cruces()
                    return
            # Si no se encontró una marca para eliminar, agregar una nueva
            self.marcas.append(tiempo_absoluto)  # Guardar la nueva marca
            self.marcas.sort()
            print(f"Marca en: {tiempo_absoluto.isoformat()} (segundos: {tiempo_relativo}), Línea: {num_linea+1}")
            # Borrar todas las líneas de cruces y redibujar desde self.marcas
            self.borrar_y_redibujar_cruces()

    def borrar_y_redibujar_cruces(self):
        # Eliminar solo las cruces del gráfico
        #self.ax.lines = [line for line in self.ax.lines if line.get_marker() != '+']
        for line in self.ax.lines[:]:
            if line.get_marker() == '+':
                line.remove()
        
        # Graficar todas las marcas desde self.marcas
        self.graficar_marcas()
        # Redibujar el canvas
        self.canvas.draw()

    def graficar_marcas(self):
        for t in self.marcas:
            if self.inicio_segmento <= t < self.inicio_segmento + 2 * 3600:
                tiempo_relativo = (t - self.inicio_segmento)
                num_linea = int(tiempo_relativo / 360)
                x = (tiempo_relativo - num_linea * 360) / 60
                y = -2000 * num_linea
                self.ax.plot(x, y, 'r+', markersize=30, mew=3, alpha=0.8)

    def navegar_segmento(self, direccion):
        # Cambiar el segmento actual
        self.segmento_actual += direccion
        duracion_segmento = 2 * 3600  # 2 horas en segundos
        # Recalcular el número máximo de segmentos, incluyendo el segmento incompleto
        total_duracion = self.stream[0].stats.endtime - self.stream[0].stats.starttime
        max_segmentos = int(np.ceil(total_duracion / duracion_segmento))
        self.segmento_actual = max(0, min(self.segmento_actual, max_segmentos - 1))
        # Actualizar el valor del scrollbar
        self.barra_horas.setValue(self.segmento_actual)
        # Reiniciar la barra de desplazamiento
        self.scroll_area.horizontalScrollBar().setValue(0)
        # Guardar la posición actual del scroll
        self.posicion_scroll_guardada = self.scroll_area.horizontalScrollBar().value()
        # Guardar la posición actual del segmento
        self.posicion_segmento_guardada = self.segmento_actual
        self.procesar_y_graficar()

    def cambiar_periodo_por_barra(self, valor):
        # Cambiar el segmento actual en función del scrollbar
        self.segmento_actual = valor
        # Guardar la posición actual del scroll
        self.posicion_scroll_guardada = self.scroll_area.horizontalScrollBar().value()
        # Guardar la posición actual del segmento
        self.posicion_segmento_guardada = self.segmento_actual
        self.procesar_y_graficar()

    def ajustar_amplitud(self, factor):
        self.amplitude_factor *= factor
        self.procesar_y_graficar()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'stream') and self.stream:
            self.procesar_y_graficar()

    def cambio_de_fecha(self):
        # Guardar las marcas del día actual antes de cambiar de fecha

        # Actualizar la fecha seleccionada
        self.directorios = obtener_directorios(self.archivo)
        # Filtrar y listar archivos MSEED en el directorio
        if os.path.exists(self.directorios['Directorio_registros']):
            self.archivos_mseed = [f for f in os.listdir(self.directorios['Directorio_registros']) if f.endswith('mseed')]
        else:
            self.archivos_mseed =[]
        # Ordenar los archivos MSEED según el orden de las estaciones
        estaciones = self.mapa_estaciones['CODIGO']
        imprimir_plt = self.mapa_estaciones['HAB_CANAL']
        # Crear una lista para almacenar archivos MSEED junto con su posición de orden
        archivos_con_posicion = []
        for archivo in self.archivos_mseed:
            if archivo[:4] in estaciones:
                posicion = estaciones.index(archivo[:4])
                if imprimir_plt[posicion] == '1':
                    archivos_con_posicion.append((archivo, posicion))
        # Ordenar la lista de archivos MSEED por la posición de la estación
        archivos_con_posicion.sort(key=lambda x: x[1])
        # Limpiar la lista MSEED en la interfaz y agregar los archivos ordenados
        self.lista_mseed.clear()
        self.marcas=[]
        for archivo, _ in archivos_con_posicion:
            self.lista_mseed.addItem(archivo)
        # Si hay elementos en la lista, seleccionar el primero
        if self.lista_mseed.count() > 0:
            self.lista_mseed.setCurrentRow(0)
            self.seleccionar_grafico_mseed(self.lista_mseed.item(0))
        # Cargar marcas del nuevo día
        self.cargar_marcas()

 
    def seleccionar_grafico_mseed(self, item):
        # Solo guardar marcas si ya hay un archivo MSEED cargado y marcas presentes
        if hasattr(self, 'archivo_mseed') and self.marcas:
            self.guardar_marcas()  
        # Guardar la posición actual del scrollbar del canvas antes de cargar un nuevo archivo
        self.posicion_scroll_guardada = self.scroll_area.horizontalScrollBar().value()
        texto_item = item.text()
        # Cargar el nuevo archivo MSEED y su contenido
        self.archivo_mseed = self.directorios['Directorio_registros'] + '/' + texto_item

        try:
            self.stream = read(self.archivo_mseed)
        except Exception as e:
            print(f"Error al cargar el archivo MSEED: {e}")
            return

        # Extraer la última cadena después del último '\'
        nombre_archivo = os.path.basename(self.archivo_mseed)
        # Extraer la parte antes del primer guion bajo ('_')
        nombre_estacion = nombre_archivo.split('_')[0]
        posicion = self.mapa_estaciones['CODIGO'].index(nombre_estacion)
        factor_diezmado_plt = int(self.mapa_estaciones['DIEZMADO_PLT'][posicion])
        self.stream=diezmar_senal(self.stream,factor_diezmado_plt)
        # Restaurar el segmento y la posición del scrollbar
        self.segmento_actual = self.posicion_segmento_guardada
        # Cargar las marcas almacenadas
        self.cargar_marcas()
        # Procesar y graficar el segmento actual
        self.procesar_y_graficar()  # Asegúrate de que esta llamada recalcule todo necesario para el gráfico
        # Calcular el número máximo de segmentos después de cargar el gráfico
        max_segmentos = int(self.stream[0].stats.npts / (self.stream[0].stats.sampling_rate * 2 * 3600))
        self.barra_horas.setRange(0, max_segmentos - 1)
        # Restaurar la posición del scrollbar después de redibujar el gráfico
        self.scroll_area.horizontalScrollBar().setValue(self.posicion_scroll_guardada)
        # Aplicar las marcas al gráfico después de cargar y procesar el nuevo archivo
        self.graficar_marcas()


    def cargar_marcas(self):
        archivo_marcas = self.directorios['archivo_marcas']
        self.marcas = []
        if os.path.exists(archivo_marcas):
            with open(archivo_marcas, 'r') as f:
                self.marcas = [obspy.UTCDateTime(marca) for marca in json.load(f)]
            self.marcas.sort()

    def guardar_marcas(self):
        archivo_marcas = self.directorios['archivo_marcas']
        if not self.marcas:  # Evitar guardar si no hay marcas
            print('No hay marcas para guardar.')
            return    
        print('Guardado en  ',archivo_marcas)
        with open(archivo_marcas, 'w') as f:
            json.dump([marca.isoformat() for marca in self.marcas], f)
        print('\n\n Marcas Guardadas en archivo ',archivo_marcas,'\n',self.marcas)

    def salir(self):
        print('Saliendo desde boton:')
        self.guardar_marcas()
        self.close()

    def limpiar_estado(self):
        """Limpia figuras y buffers antes de cerrar."""
        try:
            if hasattr(self, 'figura') and self.figura is not None:
                self.figura.clf()
                self.figura = None
            if hasattr(self, 'stream'):
                self.stream = None
            if hasattr(self, 'stLeido'):
                self.stLeido = None
            if hasattr(self, 'lista_eventos'):
                self.lista_eventos.clear()
            gc.collect()
        except Exception as e:
            print(f"Aviso en limpieza de Marcar_evento: {e}")



    def closeEvent(self, event):
        """
        Emite la señal de cerrado para notificar a la ventana principal y realiza limpieza.
        """
        print("Saliendo de Marcar eventos - closeEvent ejecutado")
    
        # Limpiar estado antes de emitir señal
        self.limpiar_estado()
        
        # Emitir señal una sola vez
        self.cerrado.emit()
    
        # Aceptar el evento de cierre
        event.accept()
    
        print("closeEvent completado - señal cerrado emitida")



