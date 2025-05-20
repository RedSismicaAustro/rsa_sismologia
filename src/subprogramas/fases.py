import os
import obspy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import ( QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QFileDialog,  QMessageBox)
from PyQt5.QtCore import QDate
from librerias.metodos_rsa import lectura_archivo
from librerias.metodos_sismicos import detectar_y_marcar_fases
from librerias.metodos_gestion import obtener_directorios,cargar_parametros
import json
from librerias.gestor_fases import GestorFases 
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5 import uic
class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Marcador de Fases Sísmicas")
        self.showMaximized()
        self.directorio_trabajo = "G:\\Mi unidad\\DIA"
        self.estaciones_por_pagina = 5
        self.pagina_actual = 0
        self.archivos_mseed = []
        self.fases_detectadas = {}
        self.gestor_fases = None
        self.mapa_estaciones = cargar_parametros()

        self.init_ui()

    def init_ui(self):
        layout_principal = QHBoxLayout()

        # Panel izquierdo
        panel_izquierdo = QVBoxLayout()


        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
        RAIZ_PROYECTO=os.path.join(RAIZ_PROYECTO, "..")
        ruta_ui =  os.path.join(RAIZ_PROYECTO, "ui", 'marcar_fases.ui')
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        # Añadir la interfaz cargada al panel izquierdo
        panel_izquierdo.addWidget(self.centralWidget())  # Ahora centralWidget es la UI cargada
        layout_principal.addLayout(panel_izquierdo, 1)

        # Panel derecho (gráfico)
        panel_derecho = QVBoxLayout()
        self.figura = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figura)
        panel_derecho.addWidget(self.canvas)

        layout_principal.addLayout(panel_derecho, 3)

        # Widget central
        widget_central = QWidget()
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)
        self.boton_directorio.clicked.connect(self.cambiar_directorio)
        self.date_edit.dateChanged.connect(self.cambio_de_fecha)
        self.date_edit.setDate(QDate.currentDate())
        self.combo_sis.currentIndexChanged.connect(self.cargar_evento)
        self.checkbox_filtro.stateChanged.connect(self.cargar_evento)
        self.boton_salir.clicked.connect(self.cerrar_ventana)
        self.lista_mseed.itemDoubleClicked.connect(self.seleccionar_grafico_mseed)
        self.boton_anterior.clicked.connect(self.anterior_pagina)
        self.boton_siguiente.clicked.connect(self.siguiente_pagina)
        
        # Inicializar la interfaz
        self.cambio_de_fecha()

    def cerrar_ventana(self):
        self.close()
        # Aquí puedes agregar lógica para volver al menú principal si es necesario

    def graficar_evento(self):
        self.figura.clear()
        self.axes = {}
        # Calcular el índice inicial y final para la paginación
        inicio = self.pagina_actual * self.estaciones_por_pagina
        fin = inicio + self.estaciones_por_pagina
        archivos_a_mostrar = self.archivos_mseed[inicio:fin]

        for i, archivo in enumerate(archivos_a_mostrar):
            archivo_mseed = os.path.join(self.directorios['Directorio_eventos'], archivo)
            st = obspy.read(archivo_mseed)
            nombre_corto = archivo.split('_')[0]
            if nombre_corto in self.mapa_estaciones:
                _, componente = self.mapa_estaciones[nombre_corto]
                indice_stream = int(componente) - 1  # Convertir a int y ajustar el índice según la descripción
                if 0 <= indice_stream < len(st):
                    tr = st[indice_stream]
                    color_linea = "lightgray"  # Color por defecto si no hay información de contribución
                    for fila in self.matriz_eventos:
                        if fila[1] == self.archivo_sis:
                            for info in fila[3:]:
                                if info.startswith(nombre_corto):
                                    filtro_aplicar = info
                                    A = int(filtro_aplicar[5])  # A
                                    if A == 1:  # Si la estación aporta al evento
                                        OO = int(filtro_aplicar[6:8])  # Orden del filtro
                                        II = float(filtro_aplicar[8:10])  # Frecuencia inferior
                                        SS = float(filtro_aplicar[10:12])  # Frecuencia superior
                                        # Aplicar filtro si está habilitado y el CheckBox está marcado
                                        if self.checkbox_filtro.isChecked():
                                            #tr.filter('bandpass', freqmin=II, freqmax=SS, corners=OO)
                                            pass
                                        color_linea = "blue"  # Azul si aporta

                    ax = self.figura.add_subplot(len(archivos_a_mostrar), 1, i+1)
                    ax.plot(tr.times(), tr.data, label=tr.id, color=color_linea)
                    ax.set_title(archivo)
                    ax.set_xlabel("Tiempo (s)")
                    ax.set_ylabel("Amplitud")
                    ax.legend()
                    # Almacenar el eje para uso posterior
                    self.axes[archivo] = ax
                    # Detectar y marcar fases solo si la línea es azul y no han sido detectadas antes
                    if archivo not in self.fases_detectadas:
                        fases = detectar_y_marcar_fases(tr)
                        self.fases_detectadas[archivo] = fases
                        pass
        self.figura.tight_layout()
        self.canvas.draw()
        # Actualizar la visualización
        self.canvas.draw()



    def cambiar_directorio(self):
        nuevo_directorio = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio de Trabajo", self.directorio_trabajo)
        if nuevo_directorio:
            self.directorio_trabajo = nuevo_directorio
            self.cambio_de_fecha()

    #Cambio de fecha, carga todo los archivos necesarios
    def cambio_de_fecha(self):
        self.fases_detectadas = {}  # Cada elemento será {'estacion': 'id_estacion', 'fases': {'P': [], 'S': [], 'Coda': []}}
        self.fecha_seleccionada = self.date_edit.date().toPyDate()
        fecha = self.date_edit.date()
        archivo=self.directorio_trabajo+'/'+fecha.toString('yyMMdd') + '000000'
        self.directorios=obtener_directorios(archivo)

        # Leer el archivo CSV para obtener información sobre los eventos
        self.matriz_eventos = lectura_archivo(self.directorios['archivo_csv'])
      
        try:
            archivos_sis = [f for f in os.listdir(self.directorios['Directorio_dia']) if f.endswith('.sis')]
            self.combo_sis.clear()
            self.combo_sis.addItems(archivos_sis)

            # Cargar y graficar el primer archivo .sis por defecto si existe alguno
            if archivos_sis:
                self.combo_sis.setCurrentIndex(0)
                self.cargar_evento()
            else:
                self.lista_mseed.clear()
                self.figura.clear()
                self.canvas.draw()
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"No se encontró el directorio: {self.directorios['Directorio_dia']}")
            self.combo_sis.clear()
            self.lista_mseed.clear()
            self.figura.clear()
            self.canvas.draw()

    def cargar_evento(self):
        self.archivo_sis = self.combo_sis.currentText()
        if not self.archivo_sis:
            return

        # Extraer hora del archivo .sis
        self.archivo_fas=self.directorios['archivo_csv']+'/'+self.archivo_sis[:-3]+'fas'
        self.archivo_json=self.archivo_fas[:-3]+'json'
        hora_sis = self.archivo_sis.split('_')[1].split('.')[0]
        patron_mseed = f"_{self.fecha_seleccionada.strftime('%Y%m%d')}_{hora_sis}.mseed"
        try:
            self.archivos_mseed = [f for f in os.listdir(self.directorios['Directorio_eventos']) if f.endswith(patron_mseed)]
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"No se encontró el directorio: {self.directorios['Directorio_eventos']}")
            self.archivos_mseed = []

        # Actualizar la lista de estaciones con nombres completos
        self.lista_mseed.clear()
        for archivo in self.archivos_mseed:
            nombre_corto = archivo.split('_')[0]
            if nombre_corto in self.mapa_estaciones:
                nombre_completo, componente = self.mapa_estaciones[nombre_corto]
                self.lista_mseed.addItem(f"{nombre_completo} ({archivo})")
            else:
                self.lista_mseed.addItem(archivo)
        # Graficar todos los archivos mseed
        self.graficar_evento()

    def seleccionar_grafico_mseed(self, item):
        texto_item = item.text()
        archivo_seleccionado = texto_item.split('(')[-1].split(')')[0].strip()
        fases_estacion=self.fases_detectadas[archivo_seleccionado]
        self.gestor_fases = GestorFases(fases_estacion)
        nueva_ventana = VentanaGrafico(self.directorios['Directorio_eventos'], archivo_seleccionado, self.date_edit.date().toPyDate(), self.fases_detectadas, self.gestor_fases, self)
        nueva_ventana.show()

    def anterior_pagina(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.graficar_evento()

    def siguiente_pagina(self):
        max_pagina = (len(self.archivos_mseed) - 1) // self.estaciones_por_pagina
        if self.pagina_actual < max_pagina:
            self.pagina_actual += 1
            self.graficar_evento()


    def guardar_evento(self):
        try:
            # Asegurarnos de que hay fases detectadas para guardar
            if not self.fases_detectadas:
                raise ValueError("No hay fases detectadas para guardar.")
        
            # Verificar que la ruta al archivo JSON está definida
            if not hasattr(self, 'archivo_json'):
                raise AttributeError("El atributo 'archivo_json' no está definido.")

            # Guardar las fases detectadas en el archivo JSON
            with open(self.archivo_json, 'w', encoding='utf-8') as archivo:
                json.dump(self.fases_detectadas, archivo, indent=4)

            print(f"Fases guardadas exitosamente en {self.archivo_json}.")
    
        except Exception as e:
            print(f"Error al guardar las fases: {e}")

class VentanaGrafico(QMainWindow):
    
    def __init__(self, directorio_eventos, archivo_seleccionado, fecha, fases_detectadas, gestor_fases, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Gráfico - {archivo_seleccionado}")
        self.setGeometry(150, 150, 800, 600)
        self.directorio_eventos = directorio_eventos
        self.archivo_seleccionado = archivo_seleccionado
        self.fecha = fecha
        self.fases_detectadas=fases_detectadas
        self.gestor_fases = gestor_fases
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.figura = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvas(self.figura)
        layout.addWidget(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        widget_central = QWidget()
        widget_central.setLayout(layout)
        self.setCentralWidget(widget_central)
        self.graficar_mseed()

    def graficar_mseed(self):
        self.figura.clear()
        ruta_completa = os.path.join(self.directorio_eventos, self.archivo_seleccionado)
        try:
            st = obspy.read(ruta_completa)
            ax = self.figura.add_subplot(111)
            tr = st[0]  # Suponemos que solo hay un trace en el stream
            self.id_estacion=tr.id
            self.fases_estacion = self.fases_detectadas[self.archivo_seleccionado]
            ax.plot(tr.times(), tr.data, label=self.id_estacion)
            ax.set_title(f"{self.id_estacion}")
            ax.set_xlabel("Tiempo (s)")
            ax.set_ylabel("Amplitud")
            ax.legend()

            # Dibujar las fases
            for fase, tiempos in self.fases_estacion.items():
                for tiempo in tiempos:
                    if tiempo > 0:  # Solo dibujamos si el tiempo no es 0
                        ax.axvline(tiempo, color=self.gestor_fases.colores[fase], linestyle='--', label=f'Fase {fase}')
            self.gestor_fases.inicializar_fases(ax)
            self.canvas.mpl_connect('button_press_event', lambda event: self.gestor_fases.al_presionar(event, ax, self.canvas))
            self.canvas.mpl_connect('button_release_event', self.gestor_fases.al_soltar)
            self.canvas.mpl_connect('motion_notify_event', lambda event: self.gestor_fases.al_mover(event, self.canvas))
            self.figura.tight_layout()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar el archivo {self.archivo_seleccionado}: {e}")


    def closeEvent(self, event):
        fases_actualizadas = self.gestor_fases.obtener_fases()
        if self.parent:
            self.parent.fases_detectadas[self.archivo_seleccionado] = fases_actualizadas
            self.parent.graficar_evento()
        super().closeEvent(event)



