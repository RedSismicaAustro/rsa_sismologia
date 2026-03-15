import sys
import os
from pathlib import Path
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
# %%
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

from rsa_io import leer_mseed,lectura_archivo,escritura_archivo,copiar_archivos
from rsa_procesamiento import archivos_fast,guardar_intento,guardar_informacion_diaria,ordenar_y_eliminar_duplicados
from metodos_gis_rsa import widget_grafico_mpl
from metodos_rsa import parametros_estaciones,grafico_evento_int,insertar_evento_otras_redes,cargar_dia,cargar_evento
from metodos_gestion import obtener_directorios
from metodos_reportes_individuales import generar_reporte_sismo
from rsa_pdf_catalogo import reporte_resumen_modos


#from metodos_reportes_individuales import insertar_evento_otras_redes
from PyQt5.QtWidgets import (QMessageBox,QDialog,QLabel,QCheckBox,QPushButton,QComboBox,QSpinBox,QTextEdit,QVBoxLayout,QWidget,QRadioButton)
from PyQt5 import uic
from datetime import datetime
from PyQt5.QtCore import QDate
from PyQt5.QtCore import Qt,QTimer
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import pyqtSignal
import xml.etree.ElementTree as ET


from PyQt5.QtWidgets import  QHBoxLayout

# =========================
#  MODOS DE REPORTE (1–7)
# =========================
MODO_PERIODO_FRANJAS          = 1   # M1 – Período por franjas (00–12, 12–18, 18–24) – Control interno
MODO_DIARIO_REVISION          = 2   # M2 – Diario de revisión (día/ad-hoc) con detalle y dummies locales
MODO_OFICIAL_DETALLADO        = 3   # M3 – Oficial detallado (solo catálogo) + página/resumen de responsables
MODO_OFICIAL_RESUMEN          = 4   # M4 – Oficial resumen (solo catálogo, sin detalle)
MODO_FACULTAD_RESUMEN         = 5   # M5 – Facultad resumen (Facultad/redes), sin detalle
MODO_INSTITUCIONAL_DETALLADO  = 6   # M6 – Institucional detallado (solo catálogo), sin extras ni responsables
MODO_INSTITUCIONAL_RESUMEN    = 7   # M7 – Institucional, sin detalle

def cargar_combo_eventos(self,text):
    self.sismos_procesar=[]
    self.ui.cmbx_eventos.clear()
    for i in range(0,len(self.eventos)):
        if self.eventos[i][2]==text:
            aux_sismo=(int(self.eventos[i][0]),self.eventos[i][1])#aux_sismo tiene el numero de evento del csv y todo el registro
            self.sismos_procesar.append(aux_sismo)
            self.ui.cmbx_eventos.addItem(self.eventos[i][1])
    self.preparar_evento('')


# ---------------------------------------------------------------
# HILO DE MONITOREO DE ARCHIVO - SEGURO PARA PyQt5
# ---------------------------------------------------------------
from PyQt5.QtCore import QThread
import os

class FileMonitorThread(QThread):

    archivo_cambiado = pyqtSignal()

    def __init__(self, lista_archivos, parent=None):
        super().__init__(parent)
        # lista_archivos es la lista completa devuelta por archivos_fast()
        self.lista_archivos = lista_archivos[:]   # copia por seguridad

    def sleep_interruptible(self, seconds):
        for _ in range(int(seconds * 10)):
            if self.isInterruptionRequested():
                return True
            time.sleep(0.1)
        return False

    def run(self):
        """
        Monitorea TODOS los archivos FAST.
        Detecta creación o modificación.
        """

        # Diccionario con tiempos iniciales
        tiempos = {}

        # Inicializar tiempos (solo para archivos existentes)
        for ruta in self.lista_archivos:
            if os.path.exists(ruta):
                try:
                    tiempos[ruta] = os.path.getmtime(ruta)
                except:
                    tiempos[ruta] = 0

        print("HILO: run() iniciado. Monitoreando archivos:", self.lista_archivos)

        while not self.isInterruptionRequested():

            cambio_detectado = False

            for ruta in self.lista_archivos:

                # Archivo recién creado
                if not os.path.exists(ruta):
                    continue

                try:
                    t_mod = os.path.getmtime(ruta)
                except:
                    continue

                # Archivo nuevo que no estaba en tiempos
                if ruta not in tiempos:
                    tiempos[ruta] = t_mod
                    cambio_detectado = True

                # Archivo existente modificado
                elif t_mod != tiempos[ruta]:
                    tiempos[ruta] = t_mod
                    cambio_detectado = True

            # Si hubo cambios → emitir señal
            if cambio_detectado:
                print("HILO: cambio detectado en alguno de los FAST")
                self.archivo_cambiado.emit()

            # Espera interruptible
            if self.sleep_interruptible(1):
                return




def verificar_drives_virtuales(responsable_evento):
    responsables = os.path.abspath(os.path.join(ruta_proyecto,'datos','responsables.csv'))
    responsables=lectura_archivo(responsables)
   
    for responsable in responsables:
        if responsable[0]==responsable_evento:
            lista_drives=responsable[1:]
    for drive in lista_drives:
        if os.path.isdir(drive):
            pass
        else:
            return False
    return True


# ============================
#  EN PROCESAR_EVENTO (QMainWindow o QWidget)
# ============================

class Procesar_evento(QWidget):  
    cerrado = pyqtSignal()

    def __init__(self, archivo, directorio_trabajo, responsable, horario, parent=None):
        super().__init__(parent)

        # -----------------------------
        # 1) ESTADO BÁSICO DEL OBJETO
        # -----------------------------
        print( "Procesando evento ",archivo,"\n", directorio_trabajo, responsable, horario) 
        self.archivo = archivo                        # Ruta o nombre AAAAMMDD_hhmmss.sis
        self.directorio_trabajo = directorio_trabajo  # Directorio ..\DIA\
        self.responsable = responsable                # Responsable global
        self.horario = horario                        # Texto "00:00 - 12:00", etc.
        self.parametros = parametros_estaciones()     # Parámetros de estaciones
        self.pagina = 0
        self.registro_tiempo = 0
        self.canales_habilitados = []
        self.numero_estaciones = 0
        self.lbl_directorio_trabajo = self.directorio_trabajo
        self.estaciones_eventos = []
        self.estaciones_eventos_total = []
        self.filtros_estaciones = []
        self.bandera_marcas = 1
        self.revision_procesamiento = False
        self.en_estaciones = False

        # Variables de procesamiento
        self.procesamiento = []          # Lista de filas del archivo *_proc.csv
        self.evento_procesar = ''        # Fila seleccionada de self.eventos
        self.indice_evento_procesar = -1
        self.eventos = []
        self.eventos_reporte = []
        self.catalogo = []
        self.evento_canales = []
        self.responsables = []
        self.resumen = []
        self.vector = []
        self.root = None
        self.archivo_estaciones = ''
        self.directorios = {}
        self.archivos_procesamiento_real = []
        self.archivos_procesamiento_virtual = []
        self.responsable_evento = ''
        self.archivo_reporte = ''
        self.trCanal = None

        # Control del mapa y redibujado diferido
        self.widget_central_activo = None

        # Control del hilo de monitoreo
        self.file_monitor = None

        # -----------------------------
        # 2) CREACIÓN DE LOS PANELES
        # -----------------------------
        layout_principal = QHBoxLayout(self)

        # PANEL IZQUIERDO: UI principal
        self.panel_izquierdo = QWidget(self)
        layout_izq = QVBoxLayout(self.panel_izquierdo)
        layout_izq.setContentsMargins(0, 0, 0, 0)

        ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'ui', 'Proceso.ui'))
        self.ui = uic.loadUi(ruta_ui)
        layout_izq.addWidget(self.ui)
        layout_principal.addWidget(self.panel_izquierdo, 1)

        # PANEL CENTRAL: para incrustar estaciones_
        self.panel_central = QWidget(self)
        self.layout_central = QVBoxLayout(self.panel_central)
        self.layout_central.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.layout_central.setContentsMargins(0, 0, 0, 0)
        layout_principal.addWidget(self.panel_central, 1)

        # PANEL DERECHO: mapa GIS embebido
        self.panel_derecho = QWidget(self)
        layout_der = QVBoxLayout(self.panel_derecho)
        layout_der.setContentsMargins(0, 0, 0, 0)
        self.widget_mapa = widget_grafico_mpl(self)
        layout_der.addWidget(self.widget_mapa)
        layout_principal.addWidget(self.panel_derecho, 2)

        # Visor matplotlib "propio" (por compatibilidad con código existente)
        self.visor = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.visor)

        # -----------------------------
        # 3) CONFIGURACIÓN INICIAL GUI
        # -----------------------------
        self.setLayout(layout_principal)
        self.setWindowTitle("PROCESAMIENTO")
        self.ui.Lbl_directorio.setText(self.directorio_trabajo)
        self.ui.grupo_carga.setEnabled(False)

        # Botones
        self.ui.Btn_eventos.clicked.connect(self.guardar_evento)
        self.ui.Btn_Salir.clicked.connect(self.Salir_)
        self.ui.Btn_procesar.clicked.connect(self.procesar_)
        self.ui.Btn_reportar.clicked.connect(self.reportar_)
        self.ui.Btn_insertar.clicked.connect(self.insertar_)

        # Combos
        self.ui.Cmb_bx_tipo_evento.activated[str].connect(self.cambio_evento)
        self.ui.cmbx_t_evento.activated[str].connect(self.cargar_tipo_evento)
        self.ui.cmbx_eventos.activated[str].connect(self.preparar_evento)

        # Radio buttons y modo inicial/revisión
        d = datetime.today()
        d_qt = QDate(d.year, d.month, d.day)

        nombre_base = Path(self.archivo).stem          # AAAAMMDD_hhmmss
        cadena_fecha = nombre_base.split('_', 1)[0]    # AAAAMMDD
        anio = int(cadena_fecha[0:4])
        mes = int(cadena_fecha[4:6])
        dia = int(cadena_fecha[6:8])
        qdate_archivo = QDate(anio, mes, dia)

        if qdate_archivo == d_qt:
            self.ui.radioButton_inicial.setChecked(True)
        else:
            self.ui.radioButton_revision.setChecked(True)

        self.ui.radioButton_inicial.toggled.connect(self.seleccionar_inicial)
        self.ui.radioButton_revision.toggled.connect(self.seleccionar_revision)

        # Cargar parámetros de estaciones habilitadas
        self.canales_habilitados = []
        for i in range(0, 101):
            if self.parametros['HAB_CANAL'][i] == '1':
                self.canales_habilitados.append(i)
        self.numero_estaciones = len(self.canales_habilitados)

        # -----------------------------
        # 4) CARGA DEL DÍA Y EVENTOS
        # -----------------------------
        self.Abrir_archivo()  # Carga self.directorios, día, catálogo, etc.

        # Estado inicial del mapa
        self.actualizar_mapa([])

    def activar_hilo(self):
        """
        Activa el hilo de monitoreo de TODOS los archivos FAST del evento.
        Este método se llama al final de procesar_().
        """

        # Solo para eventos tipo SISMO
        if self.evento_procesar[2] != "SISMO":
            self.ui.Lbl_submensajes.setText("Evento no es SISMO — monitoreo no requerido.")
            return

        # Verificar disponibilidad del Virtual
        if not verificar_drives_virtuales(self.responsable_evento):
            self.ui.Lbl_submensajes.setText("El Virtual no está conectado — monitoreo deshabilitado.")
            return

        # Obtener TODAS las rutas desde archivos_fast
        try:
            lista_fast = archivos_fast(
                self.evento_procesar[1],
                self.directorio_trabajo,
                self.responsable_evento
                )
        except Exception as e:
            print("Error al obtener archivos FAST:", e)
            self.ui.Lbl_submensajes.setText("Error al obtener archivos FAST")
            return

        # El .fas sigue siendo el archivo principal
        archivo_monitoreo = lista_fast[2]

        # Si el FAST principal aún no existe → esperar
        if not os.path.exists(archivo_monitoreo):
            self.ui.Lbl_submensajes.setText(
                f"Esperando archivo del Virtual…\n{archivo_monitoreo}"
                )
            return

        # Iniciar monitoreo
        self.ui.Lbl_submensajes.setText("Monitorizando archivos FAST…")

        # Detener hilo anterior si existe
        if hasattr(self, "file_monitor") and self.file_monitor is not None:
            try:
                self.file_monitor.requestInterruption()
                self.file_monitor.wait()
            except:
                pass

        # Crear el hilo monitoreando TODA la lista
        self.file_monitor = FileMonitorThread(lista_fast, parent=self)
        self.file_monitor.archivo_cambiado.connect(self.recalcular_procesamiento)

        print("HILO: iniciado. Monitoreando lista FAST:", lista_fast)

        # Arrancar hilo
        self.file_monitor.start()




    def _estaciones_piden_actualizar_mapa(self):
        """
        estaciones_ solicita actualización de ubicación.
        Redibuja usando el procesamiento actual.
        """
        self.actualizar_mapa(self.procesamiento)


    def _estaciones_devuelven_cambios(self, habilitados, filtros_nuevos):
        """
        estaciones_ envía estaciones habilitadas y nuevos filtros.

        Aquí solo actualizamos estructuras internas.
        El guardado en archivos se hace cuando el usuario guarda evento.
        """
        try:
            # 1. Actualizar lista de estaciones habilitadas
            self.estaciones_eventos = habilitados[:]  # lista de índices reales

            # 2. Actualizar los filtros modificados
            self.filtros_estaciones = filtros_nuevos[:]  # lista "OOffss"

            # 3. Actualizar las estructuras del evento en memoria
            idx_evento = self.indice_evento_procesar

            for i, canal_real in enumerate(self.estaciones_eventos_total):
                aux_cadena = self.eventos[idx_evento][canal_real + 3]

                # Valor habilitado
                hab = '1' if canal_real in habilitados else '0'

                # filtro concatenado
                filtro = filtros_nuevos[i]

                # nueva cadena final
                nueva = aux_cadena[:5] + hab + filtro

                self.eventos[idx_evento][canal_real + 3] = nueva

            # 4. Señal discreta en pantalla
            self.ui.Lbl_submensajes.setText("Cambios almacenados (no guardados en disco aún).")
            escritura_archivo(self.directorios['archivo_csv'], self.eventos) 
        except Exception as e:
            print("Error en _estaciones_devuelven_cambios:", e)

    def _estaciones_cerraron(self):
        """
        estaciones_ se cerró correctamente.
        Aquí ya NO se verifica si los archivos están en uso, porque
        esa validación se hace en closeEvent() de estaciones_.
        """

        print("Cierre de estaciones_: iniciando limpieza...")

        # 1) Detener hilo
        try:
            if hasattr(self, "file_monitor") and self.file_monitor is not None and self.file_monitor.isRunning():
                self.file_monitor.requestInterruption()
                self.file_monitor.wait()
                print("Hilo detenido.")
        except Exception as e:
            print("Error deteniendo hilo:", e)

        self.file_monitor = None

        # 2) Detener timer de verificación
        try:
            if hasattr(self, "timer_verificar") and self.timer_verificar.isActive():
                self.timer_verificar.stop()
                print("Timer verificar detenido.")
        except Exception as e:
            print("Error deteniendo timer_verificar:", e)

        # 3) Guardar procesamiento final
        try:
            escritura_archivo(self.directorios["archivo_procesamiento"], self.procesamiento)
            print("Procesamiento final guardado.")
        except Exception as e:
            print("Error guardando procesamiento final:", e)

        # 4) Copiar y borrar archivos del Virtual (ya verificado antes)
        if self.evento_procesar and self.evento_procesar[2] == 'SISMO':

            try:
                copiar_archivos(
                    self.archivos_procesamiento_virtual,
                    self.archivos_procesamiento_real
                )
                print("Copiado Virtual → Real.")
            except Exception as e:
                print("Error copiando Virtual → Real:", e)

            try:
                for ruta in self.archivos_procesamiento_virtual:
                    if os.path.exists(ruta):
                        os.remove(ruta)
                print("Archivos del Virtual eliminados.")
            except Exception as e:
                print("Error limpiando Virtual:", e)

        # 5) Resetear mapa
        try:
            self.actualizar_mapa([])
            print("Mapa reseteado.")
        except Exception as e:
            print("Error reseteando mapa:", e)

        # 6) Limpiar panel
        try:
            self.limpiar_panel_central()
        except Exception as e:
            print("Error limpiando panel central:", e)

        # 7) Recargar evento
        try:
            self.preparar_evento(self.ui.cmbx_eventos.currentText())
            print("Evento recargado.")
        except Exception as e:
            print("Error recargando evento:", e)

        # 8) Estado interno
        self.en_estaciones = False
        self.bandera_procesamiento = 0
        self.ui.grupo_carga.setEnabled(True)
        print("Cierre finalizado.")

    def limpiar_panel_central(self):
        """
        Elimina cualquier widget incrustado en el panel central.
        """
        if self.widget_central_activo is not None:
            self.widget_central_activo.setParent(None)
            self.widget_central_activo.deleteLater()
            self.widget_central_activo = None

    def incrustar_estaciones(self):
        """
        Incrusta estaciones_ en el panel central y conecta sus señales.
        """
        from PyQt5.QtWidgets import QSizePolicy
        self.ui.grupo_carga.setEnabled(False)
        # limpiar panel central
        self.limpiar_panel_central()

        # crear instancia
        self.widget_central_activo = estaciones_(
            self.estaciones_eventos,
            self.filtros_estaciones,
            self.responsable_evento,
            parent=self
            )

        # conectar señales de estaciones_
        self.widget_central_activo.senal_actualizar_mapa.connect(
            self._estaciones_piden_actualizar_mapa
            )
        self.widget_central_activo.senal_cambios_estaciones.connect(
            self._estaciones_devuelven_cambios
            )
        self.widget_central_activo.senal_cerrar.connect(
            self._estaciones_cerraron
            )
        self.widget_central_activo.senal_cambio_vista.connect(
            self.invertir_mapa_seniales
            )


        # incrustar widget
        self.layout_central.addWidget(self.widget_central_activo)
        self.widget_central_activo.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed
            )

        # En este punto NO se actualiza el mapa,
        # estaciones_ lo pedirá vía señal.



    def invertir_mapa_seniales(self, modo):
        # Limpia el panel derecho
        for i in reversed(range(self.panel_derecho.layout().count())):
            w = self.panel_derecho.layout().itemAt(i).widget()
            if w:
                w.setParent(None)

        if modo == "mapa":
            # Insertar nuevamente el widget_mapa
            self.panel_derecho.layout().addWidget(self.widget_mapa)
            self.actualizar_mapa(self.procesamiento)

        else:  # "senales"
            # Crear visor para señales
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

            fig = Figure(figsize=(8,4), dpi=100)
            canvas = FigureCanvas(fig)

            # Graficar inmediatamente
            try:
                arch = self.evento_procesar[1]
                arch = os.path.join(self.directorio_trabajo, arch[:8] + arch[9:15])
                trc = leer_mseed(arch, 1)
                t0 = trc[self.estaciones_eventos[0]][0].stats.starttime
                t1 = trc[self.estaciones_eventos[0]][0].stats.endtime
                grafico_evento_int(fig, trc, t0, t1, self.estaciones_eventos,
                               self.parametros['HAB_GRAFICO'], 0, 0)
            except:
                pass

            self.panel_derecho.layout().addWidget(canvas)



    # ==========================================================
    #  BLOQUE: MANEJO DE VIRTUAL + HILO MONITOR
    # ==========================================================

    def iniciar_espera_archivos_virtual(self):
        """
        Espera NO BLOQUEANTE hasta que existan los archivos del Virtual.
        Cuando aparecen:
            - se detiene el timer de verificación
            - inicia el hilo de monitoreo sobre el .fas (virtual)
        """

        # Archivo base del evento
        archivo = self.evento_procesar[1]
        self.ui.Lbl_submensajes.setText("Esperando archivos del Virtual…")

        # Crear un solo QTimer controlable
        self.timer_verificar = QTimer(self)
        self.timer_verificar.setInterval(800)

        def verificar():
            # 1) Verificar que existan los drives del virtual
            if not verificar_drives_virtuales(self.responsable_evento):
                return  # seguir verificando en el próximo ciclo

            # 2) Obtener rutas Virtual (archivos FAST)
            archivos_v = archivos_fast(
                archivo,
                self.directorio_trabajo,
                self.responsable_evento
            )
            archivo_monitoreo = archivos_v[2]  # Ruta del archivo .fas

            # 3) Esperar a que exista el archivo .fas
            if not os.path.exists(archivo_monitoreo):
                return  # seguir verificando

            # 4) Archivos listos → Detener timer y arrancar hilo
            self.timer_verificar.stop()
            self.ui.Lbl_submensajes.setText(
                "Archivos del Virtual encontrados, iniciando monitoreo…"
            )
            self.iniciar_monitor_virtual()

        # Conectar el método verificar al timer
        self.timer_verificar.timeout.connect(verificar)

        # Iniciar verificación cíclica
        self.timer_verificar.start()

    def iniciar_monitor_virtual(self):
        """
        Inicia el hilo de monitoreo del archivo .fas en el Virtual.
        El hilo llamará a guardar_intento(), y este actualizará el archivo de
        procesamiento en el directorio real.
        """
        if not self.evento_procesar:
            return

        archivo = self.evento_procesar[1]
        archivos_v = archivos_fast(
            archivo,
            self.directorio_trabajo,
            self.responsable_evento
        )
        archivo_monitoreo = archivos_v[2]   # normalmente el .fas

        # Asegurar diccionario de directorios
        if not self.directorios:
            self.directorios = obtener_directorios(self.archivo)

        # Detener hilo anterior si estaba activo
        self.detener_monitor_virtual()


        self.file_monitor = FileMonitorThread(archivo_monitoreo, parent=self)
        self.file_monitor.archivo_cambiado.connect(self.recalcular_procesamiento)
        self.file_monitor.start()


    def detener_monitor_virtual(self):
        """
        Detiene el hilo de monitoreo, si está activo.
        """
        if self.file_monitor is not None and self.file_monitor.isRunning():
            self.file_monitor.requestInterruption()
            self.file_monitor.wait()
            self.file_monitor = None



    def recalcular_procesamiento(self):
        """
        Llamado cuando el hilo detecta un cambio en el archivo .fas.
        Aquí se recalcula TODO el procesamiento.
        """
        try:
            # guardar_intento(archivo,directorio,responsables,procesamiento):
            nuevo_proc = guardar_intento(
                self.evento_procesar[1],
                self.directorio_trabajo,
                self.responsable_evento,
                self.procesamiento
            )

            # Guardar archivo *_proc.csv*
            escritura_archivo(self.directorios["archivo_procesamiento"], nuevo_proc)

            # Actualizar memoria
            self.procesamiento = nuevo_proc

            # Redibujar mapa
            self.actualizar_mapa(nuevo_proc)

            print("GUI: procesamiento actualizado y mapa redibujado.")

        except Exception as e:
            print("Error en recalcular_procesamiento:", e)
            self.ui.Lbl_submensajes.setText("Error al actualizar procesamiento.")


    def seleccionar_inicial(self, estado):
        """
        Modo inicial seleccionado.
        (De momento no altera lógica interna, pero se deja para extensiones).
        """
        if estado:
            # Aquí podrías activar banderas específicas de modo inicial
            pass

    def seleccionar_revision(self, estado):
        """
        Modo revisión seleccionado.
        """
        if estado:
            # Aquí podrías activar banderas específicas de modo revisión
            pass

    def actualizar_mapa(self, procesamiento):
        """
        Redibuja inmediatamente usando los datos del procesamiento.
        """
        print("Este metodo siempre debe ejecutarse desde la primera vez")
        try:
            if not procesamiento:
                self.widget_mapa.plot([], self.directorios['archivo_estaciones'])
                self.ui.Lbl_submensajes.setText("Mapa listo — sin intento aún.")
                return

            bandera = self.widget_mapa.plot(
                procesamiento,
                self.directorios['archivo_estaciones']
            )

            # Manejo de textos
            if isinstance(bandera, (list, tuple)):
                if bandera[0]:
                    self.ui.Lbl_submensajes.setText("Procesar con 6 fases mínimo.")
                elif bandera[1]:
                    self.ui.Lbl_submensajes.setText("Procesar con fases claras.")
                else:
                    self.ui.Lbl_submensajes.setText("No Procesar.")

        except Exception as e:
            print("Error al redibujar mapa:", e)
            self.ui.Lbl_submensajes.setText("Error al dibujar mapa.")

    def limpiar_estado(self):
        """
        Limpia figuras, visores y referencias básicas antes de cerrar.
        """
        try:
            self.detener_monitor_virtual()

            if hasattr(self, 'canvas') and self.canvas is not None:
                self.canvas.deleteLater()
                self.canvas = None
            if hasattr(self, 'visor') and self.visor is not None:
                self.visor.clf()
                self.visor = None

            if hasattr(self, 'lista_eventos'):
                self.lista_eventos.clear()
        except Exception as e:
            print(f"Error en limpieza de Procesar_evento: {e}")

    def cambiar_coeficientes_(self):
        """
        Abre la ventana de cambio de coeficientes de filtro.
        """
        self.cambio_coeficientes_filtro = Cambio_Coeficientes_Filtro(self.canales_habilitados)

    # ==========================================================
    #  BLOQUE: CARGA DEL DÍA Y EVENTOS
    # ==========================================================

    def Abrir_archivo(self):
        """
        Carga el día, inicializa combos y estructuras básicas.
        """
        # Combos de tipos de evento
        self.ui.Cmb_bx_tipo_evento.clear()
        lista_filtros = ["Ruido", "FF", "FC", "TELESISMO", "SISMO",
                         "INDEFINIDO", "Evento_local", "CONTROL", "REVISION", "TODOS"]
        self.ui.Cmb_bx_tipo_evento.addItems(lista_filtros)
        self.ui.cmbx_t_evento.addItems(lista_filtros)
        self.ui.cmbx_t_evento.setCurrentText('SISMO')

        # Cargar directorios del día
        self.directorios = obtener_directorios(self.archivo)
        self.ui.grupo_carga.setEnabled(True)

        # Cargar día completo
        (self.eventos_reporte,
         self.catalogo,
         self.eventos,
         self.vector,
         self.evento_canales,
         self.root,
         self.responsables,
         self.resumen) = cargar_dia(self.directorios)

        # Cargar lista de eventos de tipo "SISMO" en el combo
        cargar_combo_eventos(self, 'SISMO')

        self.archivo_estaciones = self.directorios['archivo_estaciones']
        self.ck_box_hab_canal = {}
        self.lbl_nombre = {}
        self.lbl_codigo = {}
        self.ck_box_hab_canal = [0 for _ in range(16)]

    def guardar_evento(self):
        """
        Guarda en disco los CSV principales del día.
        """
        escritura_archivo(self.directorios['archivo_csv'], self.eventos)
        escritura_archivo(self.directorios['archivo_reporte'], self.eventos_reporte)
        escritura_archivo(self.directorios['archivo_catalogo'], self.catalogo)

    def preparar_evento(self, text):
        """
        Escoge el evento actual desde el combo y prepara estructuras internas
        de estaciones, filtros y archivo de procesamiento.
        """
        self.evento_procesar = ''
        for i, evento in enumerate(self.eventos):
            if evento[1] == self.ui.cmbx_eventos.currentText():
                self.indice_evento_procesar = i
                self.evento_procesar = evento
                self.parametro = evento[0] + "  " + evento[1] + "  " + evento[2]
                break
        if not self.evento_procesar:
            return

        aux = int(self.evento_procesar[1][-10:-4])
        if aux < 120000:
            indice_hora = 0
        elif aux < 180000:
            indice_hora = 1
        else:
            indice_hora = 2

        horario = ["00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00"]
        self.responsable_evento = self.responsables[indice_hora+1][0]
        self.ui.Cmb_bx_tipo_evento.setCurrentText(self.evento_procesar[2])
        self.ui.txt_responsables.setText(self.responsable_evento)
        self.ui.txt_horario.setText(horario[indice_hora])

        # Estaciones y filtros asociados al evento
        self.estaciones_eventos = []
        self.filtros_estaciones = []
        for i in range(3, len(self.evento_procesar)):
            if self.evento_procesar[i] != '-':
                self.filtros_estaciones.append(self.evento_procesar[i][-6:])
                self.estaciones_eventos.append(i - 3)
        (self.indice,
         self.indice_local,
         self.indice_catalogo,
         self.archivo_escogido,
         self.evento_reporte_escogido,
         self.canales,
         self.trCanal,
         self.archivo_reporte,
         self.parametros['HAB_GRAFICO'],
         self.estaciones_eventos) = cargar_evento(
            self.parametro,
            self.eventos_reporte,
            self.catalogo,
            self.eventos,
            self.evento_canales,
            self.directorio_trabajo,
            self.directorios['Directorio_reportes']
        )
        self.estaciones_eventos_total = self.estaciones_eventos

        # Cada vez que se prepara evento, limpiar procesamiento actual y mapa
        self.procesamiento = []
        self.actualizar_mapa(self.procesamiento)

    def cambio_evento(self, text):
        """
        Cambia el tipo de evento del registro actual.
        """
        message_box = QMessageBox(
            QMessageBox.Question,
            "¡Importante!",
            "  Va a cambiar el tipo evento\n",
            QMessageBox.Yes | QMessageBox.No,
            self.window()
        )
        result = message_box.exec_()
        if result == QMessageBox.Yes:
            for i, evento in enumerate(self.eventos):
                if self.evento_procesar and self.evento_procesar[1] == evento[1]:
                    self.eventos[i][2] = self.ui.Cmb_bx_tipo_evento.currentText()
                    break

        escritura_archivo(self.directorios['archivo_csv'], self.eventos)
        (self.catalogo,
         self.eventos_reporte) = guardar_informacion_diaria(
            self.directorios['archivo_csv'],
            self.directorio_trabajo,
            self.catalogo,
            self.eventos
        )
        (self.eventos_reporte,
         self.catalogo,
         self.eventos,
         self.vector,
         self.evento_canales,
         self.root,
         self.responsables,
         self.resumen) = cargar_dia(self.directorios)

    def cargar_tipo_evento(self, text):
        """
        Carga en el combo de eventos solo los de un cierto tipo.
        """
        cargar_combo_eventos(self, text)

    # ==========================================================
    #  BLOQUE: PROCESAMIENTO DEL EVENTO
    # ==========================================================
    def procesar_(self, text):
        """
        Prepara archivos de procesamiento y abre la ventana de estaciones.
        Maneja la copia de archivos virtual/real solo cuando es SISMO.
        """

        if not self.evento_procesar:
            return

        archivo = self.evento_procesar[1]

        # Construcción ruta base del evento
        self.archivo = os.path.join(
            self.directorios["Directorio_trabajo"],
            archivo[:8] + archivo[9:15]
        )

        # Cargar estructura de directorios del día
        self.directorios = obtener_directorios(self.archivo)

        # ==============================================================
        # (1) Cargar archivo de procesamiento EXISTENTE (si lo hay)
        # ==============================================================


        # Asegurar que el directorio de procesamiento existe
        try:
            Path(self.directorios['Directorio_procesamiento']).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        if os.path.exists(self.directorios["archivo_procesamiento"]):
            # Cargar procesamiento histórico
            print("Evento procesado")
            self.procesamiento = lectura_archivo(self.directorios["archivo_procesamiento"])
            self.procesamiento = guardar_intento(
                self.evento_procesar[1],
                self.directorio_trabajo,
                self.responsable_evento,
                self.procesamiento
                )
            
        else:
            # Crear procesamiento inicial
            print("Evento nuevo")
            self.procesamiento = [
                [' ', "Fecha_Hora", "Prof.(km)", "Magn.", "Lat.", "Long.", "rms"]
            ]
            ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.procesamiento.append(['0', ahora, "Inicio", " ", " ", " ", " "])

            # Guardar archivo inicial
            escritura_archivo(self.directorios["archivo_procesamiento"], self.procesamiento)
        # ==============================================================
        # (2) ACTUALIZAR MAPA INMEDIATAMENTE (ANTES DE ACTIVAR HILO)
        # ==============================================================
        print("Archivo de procesamiento:",self.procesamiento)
        self.actualizar_mapa(self.procesamiento)

        # ==============================================================
        # (3) Manejo Virtual SOLO si es SISMO
        # ==============================================================

        if self.evento_procesar[2] == 'SISMO':

            # Verificar conexión del Virtual
            self.bandera_virtual = verificar_drives_virtuales(self.responsable_evento)

            if not self.bandera_virtual:
                msg = QMessageBox(
                    QMessageBox.Information,
                    "¡AVISO IMPORTANTE!",
                    "Debe estar conectado el Virtual\n para ejecutar ProcesoV2"
                )
                msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
                msg.exec_()

            else:
                # Rutas Virtual y Real
                self.archivos_procesamiento_virtual = archivos_fast(
                    archivo,
                    self.directorio_trabajo,
                    self.responsable_evento
                )
                self.archivos_procesamiento_real = archivos_fast(
                    archivo,
                    self.directorio_trabajo,
                    ''
                )

                # Copiar archivos desde Real hacia Virtual
                copiar_archivos(
                    self.archivos_procesamiento_real,
                    self.archivos_procesamiento_virtual
                )

                # ==================================================
                # (4) Activar hilo SOLO DESPUÉS DE DIBUJAR MAPA
                # ==================================================
                self.activar_hilo()

        else:
            # Evento NO SISMO → solo mensaje
            self.bandera_virtual = False
            msg = QMessageBox(
                QMessageBox.Information,
                "¡AVISO IMPORTANTE!",
                "Modificacion de aportes de estaciones y filtros"
            )
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()

        # ==============================================================
        # (5) Finalmente abrir estaciones_ dentro del panel central
        # ==============================================================

        self.en_estaciones = True
        self.incrustar_estaciones()


    # ==========================================================
    #  BLOQUE: REPORTES E INSERCIÓN
    # ==========================================================

    def reportar_(self):
        """
        Genera el reporte individual del sismo actual.
        """
        if not self.catalogo or not self.evento_reporte_escogido:
            return
        generar_reporte_sismo(
            self.catalogo,
            self.evento_reporte_escogido,
            self.canales,
            self.trCanal,
            self.archivo_reporte
        )

    def insertar_(self, text):
        """
        Abre el diálogo de inserción de eventos de otras redes.
        """
        reporte_(self).exec_()
        (self.catalogo,
         self.eventos_reporte) = guardar_informacion_diaria(
            self.directorios['archivo_csv'],
            self.directorio_trabajo,
            self.catalogo,
            self.eventos
        )
        self.catalogo = ordenar_y_eliminar_duplicados(self.catalogo, 0)
        self.guardar_evento()

    # ==========================================================
    #  BLOQUE: SALIDA Y CIERRE
    # ==========================================================

    def Salir_(self):
        """
        Genera un reporte temporal para revisión y controla el flujo de salida.
        Mantiene la lógica original, pero sin tocar closeEvent.
        """
        print("Saliendo sin procesamiento", self.horario)

        # Reglas de interfaz: radio buttons y checkbox de detalles
        if self.ui.radioButton_inicial.isChecked():
            self.ui.checkBox_detalles.setChecked(True)
            self.ui.checkBox_detalles.setEnabled(False)
        elif self.ui.radioButton_revision.isChecked():
            self.ui.checkBox_detalles.setEnabled(True)

        if not self.ui.checkBox_detalles.isChecked():
            self.close()
            return

        archivo_reporte_temporal = os.path.join(
            self.directorios['Directorio_base'],
            Path(self.archivo).name[:-6] + '_' +
            self.horario[:2] + '_' +
            self.horario[8:10] + '_' +
            self.responsable + '.pdf'
        )

        nombre = Path(self.archivo).stem
        fecha = QDate(int(nombre[0:4]), int(nombre[4:6]), int(nombre[6:8]))

        # Recargar datos del día
        (self.eventos_reporte,
         self.catalogo,
         self.eventos,
         self.vector,
         self.evento_canales,
         self.root,
         self.responsables,
         self.resumen) = cargar_dia(self.directorios)

        escritura_archivo(self.directorios['archivo_responsables'], self.responsables)
        tree = ET.ElementTree(self.root)
        self.estaciones_eventos = []

        resumen_responsables = self.responsables[0]
        if self.horario == '00:00 - 12:00':
            resumen_responsables.append(self.responsables[1])
        elif self.horario == '12:00 - 18:00':
            resumen_responsables.append(self.responsables[2])
        else:
            resumen_responsables.append(self.responsables[3])

        if not self.revision_procesamiento:
            subtitulo_reporte = "Reporte temporal"
            mapa_resumen = 1
            tipo_mapa = 0
            resumen_responsables = 0
            bandera_relleno = True
            modo_reporte = MODO_PERIODO_FRANJAS
            bandera_firma = False

            reporte_resumen_modos(
                archivo_reporte_temporal,
                subtitulo_reporte,
                fecha,
                fecha,
                self.catalogo,
                self.resumen,
                mapa_resumen,
                tipo_mapa,
                modo_reporte,
                self.estaciones_eventos,
                self.directorio_trabajo,
                tree,
                resumen_responsables,
                self.eventos_reporte,
                bandera_firma,
                bandera_relleno,
                self.horario
            )

            os.startfile(archivo_reporte_temporal)
            self.revision_procesamiento = True
            mensaje_html = (
                f"<span style='font-size:14pt; font-weight:700; color:#B00020;'>"
                f"¡Revise el archivo!</span><br>"
                f"<span style='font-size:12pt;'>{archivo_reporte_temporal}</span>"
            )
            self.ui.Lbl_submensajes.setText(mensaje_html)
            return
        else:
            self.ui.Lbl_submensajes.setText("")

        aux = "Se revisó archivo reporte\n" + archivo_reporte_temporal
        message_box = QMessageBox(
            QMessageBox.Question,
            "¡Importante!",
            aux,
            QMessageBox.Yes | QMessageBox.No,
            self.window()
        )
        result = message_box.exec_()

        if result == QMessageBox.Yes:
            for _ in range(3):
                try:
                    os.remove(archivo_reporte_temporal)
                    break
                except PermissionError:
                    mensaje = " Archivo " + archivo_reporte_temporal + " en uso\nCiérrelo"
                    QMessageBox.information(self, "AVISO", mensaje)
        else:
            self.revision_procesamiento = False
            return

        self.close()

    def closeEvent(self, event):
        """
        Cierre limpio:
          - Detiene hilo de monitoreo
          - Limpia panel central
          - Limpia estado gráfico
          - Emite señal de cerrado
        Sin operaciones pesadas de IO ni aperturas de ventanas.
        """
        self.detener_monitor_virtual()
        self.limpiar_panel_central()
        self.limpiar_estado()
        self.cerrado.emit()
        super().closeEvent(event)


class Cambio_Coeficientes_Filtro(QWidget):
    def __init__(self,canales_habilitados):
        super().__init__()
        self.setWindowTitle("Cambio de coeficientes")
        self.setGeometry(100, 100, 400, 600)
        self.parametros=parametros_estaciones()
        self.ck_box_hab_canal={}
        self.lbl_nombre={}
        self.lbl_codigo={}
        self.ck_box_hab_canal = {}
        self.ck_box_filtro = {}
        self.lbl_grafico_0=QLabel("ESTACIONL",self)
        self.lbl_grafico_0.setGeometry(40, 20, 61, 16)  #setGeometry(x, y, width, height)
        self.lbl_grafico_1=QLabel("CÓDIGO",self)
        self.lbl_grafico_1.setGeometry(138, 20, 50, 16)
        self.lbl_grafico_4=QLabel("FILTRO",self)
        self.lbl_grafico_4.setGeometry(204, 20, 51, 16)
        self.lbl_grafico_5=QLabel("ORDEN",self)
        self.lbl_grafico_5.setGeometry(252, 20, 51, 16)
        self.lbl_grafico_6=QLabel("f inf.",self)
        self.lbl_grafico_6.setGeometry(295, 20, 51, 16)
        self.lbl_grafico_7=QLabel("f sup.",self)
        self.lbl_grafico_7.setGeometry(334, 20, 51, 16)
        self.spbox_fil_orden={}
        self.spbox_fil_finf={}
        self.spbox_fil_fsup={}
        self.spbox_canal={}
        self.canales_habilitados=canales_habilitados
        self.numero_estaciones=len(canales_habilitados)
        for i in range(0, self.numero_estaciones):
            canal_=int(self.canales_habilitados[i])
            val_orden=2
            val_inf=1
            val_sup=10
            self.lbl_nombre[i]=QLabel(self.parametros['NOMBRE'][canal_],self)
            self.lbl_nombre[i].setGeometry(15, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.lbl_codigo[i]=QLabel(self.parametros['CODIGO'][canal_],self)
            self.lbl_codigo[i].setGeometry(150, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.ck_box_filtro[i]=QCheckBox(self)
            self.ck_box_filtro[i].setGeometry(208, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.ck_box_filtro[i].setChecked(False)
            self.spbox_fil_orden[i]=QSpinBox(self)
            self.spbox_fil_orden[i].setGeometry(252, i*25+35, 40, 24)
            self.spbox_fil_orden[i].setRange(1, 10)
            self.spbox_fil_orden[i].setValue(val_orden)
            self.spbox_fil_finf[i]=QSpinBox(self)
            self.spbox_fil_finf[i].setGeometry(294, i*25+35, 40, 24)
            self.spbox_fil_finf[i].setRange(1, 10)
            self.spbox_fil_finf[i].setValue(val_inf)
            self.spbox_fil_fsup[i]=QSpinBox(self)
            self.spbox_fil_fsup[i].setGeometry(334, i*25+35, 40, 24)
            self.spbox_fil_fsup[i].setRange(5, 20)
            self.spbox_fil_fsup[i].setValue(val_sup)        
        self.show()

class estaciones_(QWidget):
    """
    Widget de edición de estaciones, filtros y graficado.
    Sin manejo de archivos pesados ni hilos.

    Envía al padre:
        - cambios de filtros
        - cambios de habilitación
        - solicitud de actualización de ubicación
    """

    # Señales hacia Procesar_evento
    senal_cerrar = pyqtSignal()
    #senal_recalcular_procesamiento = pyqtSignal()
    senal_actualizar_mapa = pyqtSignal()
    senal_cambios_estaciones = pyqtSignal(list, list)  # (indices habilitados, filtros)
    senal_cambio_vista = pyqtSignal(str)   # "mapa" o "senales"

    def __init__(self, estaciones_eventos, filtros, responsable, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ESTACIONES")
        self.parent = parent
        self.parametros = parametros_estaciones()
        self.estaciones_eventos = estaciones_eventos[:]        # lista de índices de estaciones (0..N)
        self.filtros = filtros[:]                              # lista de strings “OOffss” por estación
        self.responsable = responsable
        self.numero_estaciones = len(self.estaciones_eventos)

        self.setFixedSize(600, 600)

        # Estructuras internas
        self.ck_box_hab_canal = {}
        self.lbl_nombre = {}
        self.lbl_codigo = {}
        self.ck_box_filtro = {}
        self.spbox_fil_orden = {}
        self.spbox_fil_finf = {}
        self.spbox_fil_fsup = {}
        self.spbox_canal = {}

        # --------------------------------------------------------
        #  MAQUETADO
        # --------------------------------------------------------
        self._crear_cabeceras()
        self._crear_tabla_estaciones()
        self._crear_botones_accion()

        # Control de mapa inicial
        QTimer.singleShot(200, self._emitir_ubicacion_inicial)

    # ===============================================================
    #  CREAR CABECERAS
    # ===============================================================

    def _crear_cabeceras(self):
        QLabel("ESTACIÓN", self).setGeometry(20, 20, 80, 16)
        QLabel("CÓDIGO", self).setGeometry(130, 20, 80, 16)
        QLabel("HAB", self).setGeometry(210, 20, 40, 16)
        QLabel("CANAL", self).setGeometry(250, 20, 50, 16)
        QLabel("FILTRO", self).setGeometry(315, 20, 50, 16)
        QLabel("ORD", self).setGeometry(370, 20, 40, 16)
        QLabel("f inf", self).setGeometry(415, 20, 45, 16)
        QLabel("f sup", self).setGeometry(455, 20, 45, 16)

    # ===============================================================
    #  TABLA DE ESTACIONES
    # ===============================================================

    def _crear_tabla_estaciones(self):
        """
        Crea los widgets para cada estación (labels, checkbox, spinboxes).
        """
        for fila in range(self.numero_estaciones):
            canal_real = int(self.estaciones_eventos[fila])
            nombre = self.parametros['NOMBRE'][canal_real]
            codigo = self.parametros['CODIGO'][canal_real]
            dato = self.parent.evento_procesar[canal_real + 3]

            # Nombre
            self.lbl_nombre[fila] = QLabel(nombre, self)
            self.lbl_nombre[fila].setGeometry(15, fila * 25 + 45, 150, 20)

            # Código
            self.lbl_codigo[fila] = QLabel(codigo, self)
            self.lbl_codigo[fila].setGeometry(150, fila * 25 + 45, 80, 20)

            # Habilitación
            self.ck_box_hab_canal[fila] = QCheckBox(self)
            self.ck_box_hab_canal[fila].setGeometry(210, fila * 25 + 45, 20, 20)
            self.ck_box_hab_canal[fila].setChecked(dato[5:6] == '1')

            # Canal físico (1,2,3)
            self.spbox_canal[fila] = QSpinBox(self)
            self.spbox_canal[fila].setGeometry(250, fila * 25 + 45, 40, 20)
            self.spbox_canal[fila].setRange(1, 3)
            self.spbox_canal[fila].setValue(int(dato[4:5]))

            # Filtro
            orden = int(self.filtros[fila][0:2])
            finf = int(self.filtros[fila][2:4])
            fsup = int(self.filtros[fila][4:6])

            self.ck_box_filtro[fila] = QCheckBox(self)
            self.ck_box_filtro[fila].setGeometry(320, fila * 25 + 45, 20, 20)
            self.ck_box_filtro[fila].setChecked(orden != 0)

            # Orden
            self.spbox_fil_orden[fila] = QSpinBox(self)
            self.spbox_fil_orden[fila].setGeometry(365, fila * 25 + 45, 40, 20)
            self.spbox_fil_orden[fila].setRange(1, 10)
            self.spbox_fil_orden[fila].setValue(orden if orden else 2)

            # Frecuencia inferior
            self.spbox_fil_finf[fila] = QSpinBox(self)
            self.spbox_fil_finf[fila].setGeometry(410, fila * 25 + 45, 40, 20)
            self.spbox_fil_finf[fila].setRange(1, 10)
            self.spbox_fil_finf[fila].setValue(finf if orden else 1)

            # Frecuencia superior
            self.spbox_fil_fsup[fila] = QSpinBox(self)
            self.spbox_fil_fsup[fila].setGeometry(455, fila * 25 + 45, 40, 20)
            self.spbox_fil_fsup[fila].setRange(5, 20)
            self.spbox_fil_fsup[fila].setValue(fsup if orden else 10)

    # ===============================================================
    #  BOTONES
    # ===============================================================

    def _crear_botones_accion(self):
        # Graficar
        self.Btn_graficar = QPushButton("Señales", self)
        self.Btn_graficar.setGeometry(235, 500, 70, 25)
        self.Btn_graficar.clicked.connect(self.Graficar_)


        # Salir
        self.Btn_salir = QPushButton("Salir", self)
        self.Btn_salir.setGeometry(500, 500, 70, 25)
        self.Btn_salir.clicked.connect(self.close)
        
        # ----------- OPCIONES DE VISTA -----------
        self.radio_mapa = QRadioButton("Mapa", self)
        self.radio_mapa.setGeometry(20, 500, 80, 25)
        self.radio_mapa.setChecked(True)
        self.radio_mapa.toggled.connect(lambda estado: 
                                        estado and self.senal_cambio_vista.emit("mapa")
                                        )

        self.radio_senales = QRadioButton("Señales", self)
        self.radio_senales.setGeometry(100, 500, 80, 25)
        self.radio_senales.toggled.connect(lambda estado: 
                                           estado and self.senal_cambio_vista.emit("senales")
                                           )
        

    # ===============================================================
    #  UBICACIÓN / MAPA
    # ===============================================================

    def _emitir_ubicacion_inicial(self):
        """Se usa cuando aparece la ventana por primera vez."""
        self.senal_actualizar_mapa.emit()

    def _emitir_ubicacion(self):
        """Llama al padre para actualizar mapa."""
        self.senal_actualizar_mapa.emit()

    # ===============================================================
    #  GRAFICAR SEÑALES
    # ===============================================================

    def Graficar_(self):

        try:
            archivo = self.parent.evento_procesar[1]
            archivo = os.path.join(
                self.parent.directorio_trabajo,
                archivo[:8] + archivo[9:15]
            )

            trc = leer_mseed(archivo, 1)
            self.trCanal = trc

            t0 = trc[self.estaciones_eventos[0]][0].stats.starttime
            t1 = trc[self.estaciones_eventos[0]][0].stats.endtime

            grafico_evento_int(
                self.parent.visor,
                trc,
                t0,
                t1,
                self.estaciones_eventos,
                self.parametros['HAB_GRAFICO'],
                0,
                0
            )
        except Exception as e:
            print("Error en graficar:", e)

    # ===============================================================
    #  SALIDA Y GUARDADO DE CAMBIOS
    # ===============================================================

    def _recopilar_cambios(self):
        """
        Devuelve:
         - lista de estaciones habilitadas
         - lista de filtros concatenados
        """
        habilitados = []
        filtros_nuevos = []

        for i in range(self.numero_estaciones):
            canal_real = int(self.estaciones_eventos[i])

            # habilitación
            if self.ck_box_hab_canal[i].isChecked():
                habilitados.append(canal_real)

            # filtro
            if self.ck_box_filtro[i].isChecked():
                orden = self.spbox_fil_orden[i].value()
                fi = self.spbox_fil_finf[i].value()
                fs = self.spbox_fil_fsup[i].value()
                filtros_nuevos.append(f"{orden:02}{fi:02}{fs:02}")
            else:
                filtros_nuevos.append("000000")

        return habilitados, filtros_nuevos

    def closeEvent(self, event):
        """
        Antes de cerrar estaciones_ verificamos si los archivos del Virtual
        están en uso. Si lo están → NO se cierra y NO se emite senal_cerrar.
        """

        archivos_bloqueados = []

        for ruta in self.parent.archivos_procesamiento_virtual:
            if not os.path.exists(ruta):
                continue

            # Detectar bloqueo (ProcesoV2)
            try:
                os.rename(ruta, ruta)
            except Exception:
                archivos_bloqueados.append(ruta)

        if archivos_bloqueados:
            lista = "\n".join(archivos_bloqueados)
            msg = QMessageBox(
                QMessageBox.Warning,
                "Archivo en uso",
                "Los siguientes archivos están abiertos en ProcesoV2 "
                "y deben cerrarse antes de continuar:\n\n" + lista
            )
            msg.exec_()
            event.ignore()   # NO cerrar
            return           # NO emitir señales

        # Si NO están ocupados → permitir cierre y emitir señal
        try:
            habil, filtros = self._recopilar_cambios()
            self.senal_cambios_estaciones.emit(habil, filtros)
            self.senal_cerrar.emit()
        except Exception as e:
            print("Error en closeEvent estaciones_:", e)

        super().closeEvent(event)


class reporte_(QDialog):
    def __init__(self, parent=None):
        super(reporte_,self).__init__()
        super().__init__(parent)
        self.parent=parent
        QDialog.__init__(self)
        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", "secundaria.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)
        self.lbl_grafico_0=QLabel("Página principal",self)
        self.lbl_grafico_0.setGeometry(30, 20, 141, 21)  #setGeometry(x, y, width, height)
        self.lbl_grafico_1=QLabel("Página secundaria",self)
        self.lbl_grafico_1.setGeometry(30, 164, 141, 21)
        self.lbl_grafico_2=QLabel("RED",self)
        self.lbl_grafico_2.setGeometry(300, 90, 51, 40)
        self.lbl_grafico_3=QLabel("TIPO DE MAGNITUD",self)
        self.lbl_grafico_3.setGeometry(220, 130, 100, 40)
        self.textEdit=QTextEdit(self)
        self.textEdit.setGeometry(30, 44, 151, 121)
        self.textEdit_2=QTextEdit(self)
        self.textEdit_2.setGeometry(30, 190, 151, 31)
        self.Btn_limpiar = QPushButton("Limpiar/Iniciar", self)
        self.Btn_limpiar.setGeometry(360, 50, 111, 31)
        self.Btn_limpiar.setEnabled(True)
        self.Btn_limpiar.clicked.connect(self.Limpiar_)
        self.Btn_limpiar.clearFocus()
        self.cmbx_red = QComboBox( self)
        self.cmbx_red.setGeometry(360, 100, 111, 21)
        self.cmbx_tipo_mag = QComboBox( self)
        self.cmbx_tipo_mag.setGeometry(360, 140, 111, 21)
        lista_filtros = [" ","IGEPN", "USGS", "Otras redes"]
        self.cmbx_red.addItems(lista_filtros)
        lista_filtros = [" ","M", "MLv", "Md","Mc","Mw","Mb"]
        self.cmbx_tipo_mag.addItems(lista_filtros)       
        self.Btn_insertar = QPushButton("Insertar", self)
        self.Btn_insertar.setGeometry(360, 180, 111, 31)
        self.Btn_insertar.setEnabled(True)
        self.Btn_insertar.clicked.connect(self.Insertar_)
        self.Btn_insertar.clearFocus()
        #self.evento_reporte_escogido=self.parent.evento_reporte_escogido
        #self.indice=self.parent.indice_evento_procesar

    def closeEvent(self, event):
        escritura_archivo(self.parent.directorios['archivo_reporte'],self.parent.eventos_reporte)
        escritura_archivo(self.parent.directorios['archivo_catalogo'],self.parent.catalogo)

    def Limpiar_(self):
        self.textEdit.clear()
        self.textEdit_2.clear()
        self.cmbx_red.setCurrentIndex(0)
        self.cmbx_tipo_mag.setCurrentIndex(0)
        self.textEdit.clear()
        self.textEdit_2.clear()
        self.cmbx_red.setCurrentIndex(0)
        self.cmbx_tipo_mag.setCurrentIndex(0)

    def Insertar_(self):
        red_=self.cmbx_red.currentIndex()
        magnitud_=self.cmbx_tipo_mag.currentIndex()
        tipo_magnitud=self.cmbx_tipo_mag.currentText()
        texto=self.textEdit.toPlainText()
        texto2=self.textEdit_2.toPlainText()
        self.parent.catalogo,self.parent.eventos_reporte=insertar_evento_otras_redes(
            self.parent.catalogo,
            self.parent.indice_catalogo,
            self.parent.eventos_reporte,
            red_,
            magnitud_,
            tipo_magnitud,
            texto,
            texto2,
            self.parent.evento_reporte_escogido,
            self.parent.indice,
            self.parent.indice_local
            )
        self.textEdit.clear()
        self.textEdit_2.clear()
        self.cmbx_red.setCurrentIndex(0)
        self.cmbx_tipo_mag.setCurrentIndex(0)
