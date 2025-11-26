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


from metodos_gis_rsa import widget_grafico_mpl
from metodos_rsa import leer_mseed,parametros_estaciones,grafico_evento_int,archivos_fast,verificar_coincidencias
from metodos_rsa import copiar_archivos,lectura_archivo,escritura_archivo,guardar_informacion_diaria,guardar_intento,ordenar_y_eliminar_duplicados,insertar_evento_otras_redes,cargar_dia,cargar_evento
from metodos_gestion import obtener_directorios
from metodos_reportes_individuales import generar_reporte_sismo
#from metodos_reportes_individuales import insertar_evento_otras_redes
from PyQt5.QtWidgets import (QMainWindow,QMessageBox,QDialog,QLabel,QCheckBox,QPushButton,QComboBox,QSpinBox,QTextEdit,QVBoxLayout,QWidget)
from PyQt5 import uic
import matplotlib.pyplot as plt
from datetime import datetime
from PyQt5.QtCore import QDate
from PyQt5.QtCore import Qt,QTimer
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import pyqtSignal
import xml.etree.ElementTree as ET
from metodos_graficos_rsa import reporte_resumen_modos


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




def activar_hilo(self):
    """
    Activa el hilo de monitoreo cuando ya existen los archivos del Virtual.
    NO usa bucles bloqueantes — el inicio viene desde iniciar_espera_archivos_virtual().
    """
    archivo_monitoreo = archivos_fast(
        self.parent.evento_procesar[1],
        self.parent.directorio_trabajo,
        self.parent.responsable_evento
    )[2]

    if not os.path.exists(archivo_monitoreo):
        self.parent.ui.Lbl_submensajes.setText(
            f"El archivo {archivo_monitoreo} aún no existe."
        )
        return  # La espera ya se maneja fuera

    # Si existe, activar monitoreo
    self.parent.ui.Lbl_submensajes.setText("Monitorizando en virtual…")

    self.file_monitor = FileMonitorThread(
        archivo_monitoreo,
        self.parent.directorio_trabajo,
        self.parent.responsable_evento,
        self.procesamiento,
        self.parent.evento_procesar[1]
    )

    self.file_monitor.procesamiento_actualizado.connect(self.update_procesamiento)
    self.file_monitor.start()
    self.bandera_procesamiento = 1




    
def cargar_combo_eventos(self,text):
    self.sismos_procesar=[]
    self.ui.cmbx_eventos.clear()
    for i in range(0,len(self.eventos)):
        if self.eventos[i][2]==text:
            aux_sismo=(int(self.eventos[i][0]),self.eventos[i][1])#aux_sismo tiene el numero de evento del csv y todo el registro
            self.sismos_procesar.append(aux_sismo)
            self.ui.cmbx_eventos.addItem(self.eventos[i][1])
            print(self.eventos[i][1])
    self.preparar_evento('')


# ---------------------------------------------------------------
# HILO DE MONITOREO DE ARCHIVO - SEGURO PARA PyQt5
# ---------------------------------------------------------------
from PyQt5.QtCore import QThread
import os

class FileMonitorThread(QThread):
    """
    Hilo que monitorea un archivo en segundo plano.
    Si el archivo cambia (fecha de modificación distinta),
    se guarda automáticamente la información del procesamiento
    y se emite una señal con el nuevo contenido para que la GUI se actualice.
    """

    procesamiento_actualizado = pyqtSignal(list)  # Señal Qt -> emite el procesamiento actualizado

    def __init__(self, file_path, directorio, responsable, procesamiento, archivo_evento, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.directorios = directorio
        self.responsable = responsable
        self.procesamiento = procesamiento
        self.archivo_evento = archivo_evento

    def run(self):
        """Método principal del hilo: monitorea el archivo cada segundo."""
        if not os.path.exists(self.file_path):
            print("Archivo no encontrado:", self.file_path)
            return

        try:
            last_modified_time = os.path.getmtime(self.file_path)
        except Exception as e:
            print("Error inicial en monitoreo:", e)
            return

        # Bucle de monitoreo
        while not self.isInterruptionRequested():
            try:
                current_modified_time = os.path.getmtime(self.file_path)
                if current_modified_time != last_modified_time:
                    last_modified_time = current_modified_time

                    # Guardar la información actualizada (mantiene la lógica original)
                    from metodos_rsa import guardar_intento
                    nuevo_procesamiento = guardar_intento(
                        self.archivo_evento,
                        self.directorios,
                        self.responsable,
                        self.procesamiento
                    )

                    # Emite el resultado hacia la interfaz de forma segura
                    self.procesamiento_actualizado.emit(nuevo_procesamiento)
                    print(f"Archivo modificado: {time.ctime(current_modified_time)}")

            except Exception as e:
                print("Error en FileMonitorThread:", e)

            time.sleep(1)



def verificar_drives_virtuales(responsable_evento):
    print("entrando a verificar drives virtuales", responsable_evento)
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

        # -------------------------------------------------
        # CREACIÓN DE LOS 3 PANELES: IZQ – CENTRAL – DER
        # -------------------------------------------------
        from PyQt5 import uic
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
        
        layout_principal = QHBoxLayout(self)

        # === PANEL IZQUIERDO: carga del UI ===
        self.panel_izquierdo = QWidget(self)
        layout_izq = QVBoxLayout(self.panel_izquierdo)
        layout_izq.setContentsMargins(0, 0, 0, 0)


        ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'ui', 'Proceso.ui'))
        self.ui = uic.loadUi(ruta_ui)
        layout_izq.addWidget(self.ui)

        layout_principal.addWidget(self.panel_izquierdo, 1)

        # === PANEL CENTRAL (vacío por ahora) ===
        self.panel_central = QWidget(self)
        self.layout_central = QVBoxLayout(self.panel_central)
        # Alinear arriba e izquierda
        self.layout_central.setAlignment(Qt.AlignTop | Qt.AlignLeft)


        self.layout_central.setContentsMargins(0, 0, 0, 0)
        layout_principal.addWidget(self.panel_central, 1)

        # === PANEL DERECHO (mapa GIS) ===
        self.panel_derecho = QWidget(self)
        layout_der = QVBoxLayout(self.panel_derecho)
        layout_der.setContentsMargins(0, 0, 0, 0)

        self.widget_mapa = widget_grafico_mpl(self)
        layout_der.addWidget(self.widget_mapa)

        layout_principal.addWidget(self.panel_derecho, 2)

        # ==================================================
        #   VARIABLE DE CONTROL DEL PANEL CENTRAL
        # ==================================================
        self.widget_central_activo = None   # aquí guardaremos estaciones_()

        # --------------------------------------------------------
        # Establecer layout principal como central del QMainWindow
        # --------------------------------------------------------
        self.setLayout(layout_principal)

        self.directorio_trabajo = directorio_trabajo
        self.archivo=archivo
        self.responsable=responsable
        self.horario=horario
        self.visor = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.visor)
        self.setWindowTitle("PROCESAMIENTO")
        self.ui.Btn_eventos.clicked.connect(self.guardar_evento)
        self.ui.Btn_Salir.clicked.connect(self.Salir_)
        self.ui.Btn_procesar.clicked.connect(self.procesar_)
        self.ui.Btn_reportar.clicked.connect(self.reportar_)
        self.ui.Btn_insertar.clicked.connect(self.insertar_)
        
        self.ui.Cmb_bx_tipo_evento.activated[str].connect(self.cambio_evento)
        self.ui.cmbx_t_evento.activated[str].connect(self.cargar_tipo_evento)
        self.ui.cmbx_eventos.activated[str].connect(self.preparar_evento)
        self.parametros=parametros_estaciones()
        self.pagina=0
        self.registro_tiempo=0
        self.ui.Lbl_directorio.setText(self.directorio_trabajo)
        self.canales_habilitados=[]
        for i in range(0,101):
            if self.parametros['HAB_CANAL'][i]=='1':
                self.canales_habilitados.append(i)
        self.numero_estaciones=len(self.canales_habilitados)
        self.lbl_directorio_trabajo=self.directorio_trabajo
        self.estaciones_eventos=[]
        self.bandera_marcas=1
        self.revision_procesamiento=False
        self.ui.grupo_carga.setEnabled(False)
 
        # Conectar las señales en el __init__ de tu ventana
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual

        # Extraer AAAAMMDD desde self.archivo (puede ser ruta completa)
        nombre_base = Path(self.archivo).stem          # -> "AAAAMMDD_hhmmss"
        cadena_fecha = nombre_base.split('_', 1)[0]    # -> "AAAAMMDD"

        # Construir QDate del archivo
        anio = int(cadena_fecha[0:4])
        mes  = int(cadena_fecha[4:6])
        dia  = int(cadena_fecha[6:8])
        qdate_archivo = QDate(anio, mes, dia)

        # Comparación con d
        son_iguales     = (qdate_archivo == d)

        # Ejemplos de uso:
        if son_iguales:
            self.ui.radioButton_inicial.setChecked(True)
        else:
            self.ui.radioButton_revision.setChecked(True)
        self.ui.radioButton_inicial.toggled.connect(self.seleccionar_inicial)
        self.ui.radioButton_revision.toggled.connect(self.seleccionar_revision)
        self.Abrir_archivo()
        # Variables de control para el estado del procesamiento
        self.procesamiento = []      # vacío cuando no hay evento activo
        self.en_estaciones = False   # indica si el usuario está dentro de estaciones_()
        # --- Al iniciar el procesamiento ---
        self.actualizar_mapa_desde_procesamiento(self.procesamiento)


    def limpiar_panel_central(self):
        if self.widget_central_activo is not None:
            self.widget_central_activo.setParent(None)
            self.widget_central_activo.deleteLater()
            self.widget_central_activo = None



    def incrustar_estaciones(self):
        """
        Limpia el panel central e incrusta estaciones_ como widget,
        sin bloquear la interfaz mientras espera los archivos del virtual.
        """
        from PyQt5.QtCore import QTimer
        from PyQt5.QtWidgets import QSizePolicy

        # 1. limpiar panel central
        self.limpiar_panel_central()

        # 2. crear widget estaciones_ como WIDGET (no QDialog)
        self.widget_central_activo = estaciones_(
            self.estaciones_eventos,
            self.filtros_estaciones,
            self.responsable_evento,
            parent=self
        )

        # 3. añadir al panel central
        self.layout_central.addWidget(self.widget_central_activo)
        self.widget_central_activo.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Fixed
            )


        # 4. iniciar el proceso de espera → activación
        #self.widget_central_activo.iniciar_espera_archivos_virtual()

    def iniciar_espera_archivos_virtual(self):
        """
        Espera NO BLOQUEANTE hasta que existan los archivos del virtual.
        Cuando aparecen:
            - inicia hilo de monitoreo sobre el .fas (virtual)
            - y desde el hilo se va actualizando el procesamiento (_proc en real).
        """
        from PyQt5.QtCore import QTimer

        archivo = self.evento_procesar[1]
        self.ui.Lbl_submensajes.setText("Esperando archivos del Virtual…")

        def verificar():
            # 1) Verificar que los drives del virtual existan
            if not verificar_drives_virtuales(self.responsable_evento):
                # Sigue esperando hasta que conecten el virtual
                QTimer.singleShot(800, verificar)
                return

            # 2) Obtener rutas de archivos en el virtual
            archivos_v = archivos_fast(
                archivo,
                self.directorio_trabajo,
                self.responsable_evento
            )
            # Asumo que archivos_v[2] es el .fas que genera ProcesoV2
            archivo_monitoreo = archivos_v[2]

            # 3) Si todavía no existe el .fas, seguir esperando
            if not os.path.exists(archivo_monitoreo):
                QTimer.singleShot(800, verificar)
                return

            # 4) Cuando ya existe, arrancar el hilo
            self.ui.Lbl_submensajes.setText("Archivos del Virtual encontrados, iniciando monitoreo…")
            self.iniciar_monitor_virtual()

        verificar()


    def iniciar_monitor_virtual(self):
        """
        Inicia el hilo de monitoreo del archivo .fas en el Virtual.
        El hilo llamará a guardar_intento(), que leerá el .fas (virtual)
        y actualizará el archivo de procesamiento en el directorio real.
        """
        archivo = self.evento_procesar[1]

        # Archivos en el Virtual (responsable_evento)
        archivos_v = archivos_fast(
            archivo,
            self.directorio_trabajo,
            self.responsable_evento
        )
        archivo_monitoreo = archivos_v[2]   # normalmente el .fas

        # Crear hilo
        self.file_monitor = FileMonitorThread(
            archivo_monitoreo,
            self.directorios,        # diccionario de directorios, no solo la ruta
            self.responsable_evento,
            self.procesamiento,
            archivo,
            parent=self
        )
        self.file_monitor.procesamiento_actualizado.connect(self.actualizar_procesamiento)
        self.file_monitor.start()



    def actualizar_procesamiento(self, nuevo):
        """
        Recibe el procesamiento actualizado desde el hilo.
        Guarda el archivo de procesamiento y refresca el mapa embebido.
        """
        self.procesamiento = nuevo

        # Guardar al vuelo en el archivo de procesamiento REAL
        ruta = self.directorios['archivo_procesamiento']
        escritura_archivo(ruta, nuevo)

        # Refrescar el mapa en el panel derecho
        self.actualizar_mapa_desde_procesamiento(nuevo)


   
    # Métodos asociados
    def seleccionar_inicial(self, estado):
        if estado:
            pass
                

    def seleccionar_revision(self, estado):
        if estado:
            pass

    def actualizar_mapa_desde_procesamiento(self, procesamiento):
        """
        Redibuja el mapa embebido del panel derecho con el procesamiento recibido.
        Si 'procesamiento' es vacío, muestra solo estaciones/contexto (estado base).
        No abre ventanas ni cambia el foco.
        """
        try:
            self.procesamiento = procesamiento

            # --- Guardia: evento vacío -> dibujar base y salir ---
            if not procesamiento:
                self.widget_mapa.plot([], self.directorios['archivo_estaciones'])
                if hasattr(self, "Lbl_submensajes"):
                    self.ui.Lbl_submensajes.setText("Mapa listo — sin evento seleccionado.")
                return
            # --- Fin guardia ---

            bandera = self.widget_mapa.plot(
                procesamiento,
                self.directorios['archivo_estaciones']
            )

            if isinstance(bandera, (list, tuple)) and len(bandera) >= 2:
                if bandera[0]:
                    mensaje = 'Procesar con 6 fases mínimo,\n (Con 5 en la parte superior)'
                elif bandera[1]:
                    mensaje = 'Procesar con fases claras'
                else:
                    mensaje = 'No Procesar'
                if hasattr(self, "Lbl_submensajes"):
                    self.ui.Lbl_submensajes.setText(mensaje)

        except Exception as e:
            print("Error al actualizar mapa desde el padre:", e)
            if hasattr(self, "Lbl_submensajes"):
                self.ui.Lbl_submensajes.setText("Error al actualizar mapa (ver consola).")


    def limpiar_estado(self):
        """Limpia figuras, visores, hilos, timers, etc., antes de cerrar."""
        try:
            if hasattr(self, 'canvas'):
                self.canvas.deleteLater()
                self.canvas = None
            if hasattr(self, 'visor'):
                self.visor.clf()
                self.visor = None
            # Limpieza de listas, buffers o datos
            if hasattr(self, 'stLeido'):
                del self.stLeido
            if hasattr(self, 'lista_eventos'):
                self.lista_eventos.clear()
        except Exception as e:
            print(f"Error en limpieza de Extraer_evento: {e}")

    def cambiar_coeficientes_(self):
        self.cambio_coeficientes_filtro = Cambio_Coeficientes_Filtro(self.canales_habilitados)
        
    def Abrir_archivo(self):  #Depurado
        self.ui.Cmb_bx_tipo_evento.clear()
        lista_filtros = ["Ruido", "FF", "FC","TELESISMO","SISMO","INDEFINIDO","Evento_local",'CONTROL','REVISION','TODOS']
        self.ui.Cmb_bx_tipo_evento.addItems(lista_filtros)
        self.ui.cmbx_t_evento.addItems(lista_filtros)
        self.ui.cmbx_t_evento.setCurrentText('SISMO')
        self.directorios=obtener_directorios(self.archivo)
        self.ui.grupo_carga.setEnabled(True)
        #Cargar día
        self.eventos_reporte,self.catalogo,self.eventos,\
        vector,self.evento_canales,\
        root,self.responsables,self.resumen=cargar_dia(self.directorios)
        cargar_combo_eventos(self,'SISMO')
        self.archivo_estaciones=self.directorios['archivo_estaciones']
        self.ck_box_hab_canal={}
        self.lbl_nombre={}
        self.lbl_codigo={}
        self.ck_box_hab_canal = [0 for x in range(16)]


    def guardar_evento(self):
        print("Guardar evento")
        escritura_archivo(self.directorios['archivo_csv'],self.eventos)
        escritura_archivo(self.directorios['archivo_reporte'],self.eventos_reporte)
        escritura_archivo(self.directorios['archivo_catalogo'],self.catalogo)

    def preparar_evento(self, text):
        self.evento_procesar=''
        for i,evento in enumerate(self.eventos):
            if evento[1]==self.ui.cmbx_eventos.currentText():
                self.indice_evento_procesar=i
                self.evento_procesar=evento
                self.parametro=evento[0]+"  "+evento[1]+"  "+evento[2]
                break
        aux=int(self.evento_procesar[1][-10:-4])

        if aux<120000:
            indice_hora=1
        elif aux<180000:
            indice_hora=2
        elif aux<240000:
            indice_hora=3
        horario=["00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00"]
        self.responsable_evento=self.responsables[indice_hora][0]
        self.ui.Cmb_bx_tipo_evento.setCurrentText(self.evento_procesar[2])
        self.ui.txt_responsables.setText(self.responsable_evento)
        self.ui.txt_horario.setText(horario[indice_hora])
        self.estaciones_eventos=[]
        self.filtros_estaciones=[]
        for i in range(3,len(self.evento_procesar)):
            if self.evento_procesar[i]!='-':
                self.filtros_estaciones.append(self.evento_procesar[i][-6:])
                self.estaciones_eventos.append(i-3)
        self.indice, self.indice_local, self.indice_catalogo, self.archivo_escogido, \
        self.evento_reporte_escogido, self.canales, self.trCanal, self.archivo_reporte, \
        self.parametros['HAB_GRAFICO'],self.estaciones_eventos = cargar_evento(
            self.parametro,                          # Parámetro principal para cargar el evento
            self.eventos_reporte,                    # Lista de eventos disponibles
            self.catalogo,                           # Catálogo asociado
            self.eventos,                            # Datos específicos del evento
            self.evento_canales,                     # Canales del evento
            self.directorio_trabajo,                 # Directorio de trabajo
            self.directorios['Directorio_reportes']   # Directorio de reportes
            )
        self.estaciones_eventos_total=self.estaciones_eventos

    def cambio_evento(self, text):
        print('Cambio evento')
        message_box = QMessageBox(
            QMessageBox.Question,
            "¡Importante!",
            "  Va a cambiar el tipo evento\n",
            QMessageBox.Yes | QMessageBox.No ,
            self.window()
        )
        result = message_box.exec_()
        if result == QMessageBox.Yes:
            for i,evento in enumerate(self.eventos):
                if self.evento_procesar[1]==evento[1]:
                    self.eventos[i][2]=self.Cmb_bx_tipo_evento.currentText()
                    break
        escritura_archivo(self.directorios['archivo_csv'],self.eventos)
        self.catalogo,self.eventos_reporte=guardar_informacion_diaria(self.directorios['archivo_csv'],self.directorio_trabajo,self.catalogo,self.eventos)
        self.eventos_reporte,self.catalogo,self.eventos,\
        vector,self.evento_canales,\
        root,self.responsables,self.resumen=cargar_dia(self.directorios)
        

    def cargar_tipo_evento(self, text):
        cargar_combo_eventos(self,text)

    def procesar_(self,text):
        archivo=self.evento_procesar[1]
        self.archivo=os.path.join(self.directorios["Directorio_trabajo"],archivo[:8]+archivo[9:15])
        print("Archivo a procesar: ",self.archivo,self.responsable_evento)
        self.directorios=obtener_directorios(self.archivo)
        if self.evento_procesar[2]=='SISMO':
            
            self.bandera_virtual=verificar_drives_virtuales(self.responsable_evento)
            if not(self.bandera_virtual):
                msg = QMessageBox(QMessageBox.Information, "¡AVISO IMPORTANTE!", "Debe estar conectado el Virtual\n para ejecutar ProcesoV2")
                msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
                msg.exec_()
            else:
                self.archivos_procesamiento_virtual=archivos_fast(archivo,self.directorio_trabajo,self.responsable_evento)
                self.archivos_procesamiento_real=archivos_fast(archivo,self.directorio_trabajo,'')
                copiar_archivos(self.archivos_procesamiento_real,self.archivos_procesamiento_virtual)

        else:
            self.bandera_virtual=False
            msg = QMessageBox(QMessageBox.Information, "¡AVISO IMPORTANTE!", "Modificacion de aportes de estaciones y filtros")
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()
        self.archivo_procesar=self.directorios['Directorio_procesamiento']+'/'+archivo[:-4]+'_proc.csv'
        if os.path.exists(self.archivo_procesar):
            self.procesamiento=lectura_archivo(self.archivo_procesar)
        else:
            self.procesamiento=[[' ',"Fecha_Hora","Prof.(km)","Magn.","Lat.","Long.","rms"]]
            ahora = datetime.now()
            fecha_formateada = ahora.strftime("%Y-%m-%d %H:%M:%S")
            self.procesamiento.append(['0',fecha_formateada,"Inicio"," "," "," "," "])
        try:
            path = Path(self.directorios['Directorio_procesamiento'])
            path.mkdir(parents=True)
        except FileExistsError:
            pass


        self.en_estaciones = True
        # Abrir la ventana estaciones_
        self.incrustar_estaciones()

        # --- Al cerrar estaciones_: volver al mapa vacío ---
        self.en_estaciones = False
        self.procesamiento = []
        self.actualizar_mapa_desde_procesamiento(self.procesamiento)


    def reportar_(self):
        generar_reporte_sismo(self.catalogo, self.evento_reporte_escogido, self.canales, self.trCanal, self.archivo_reporte)

    def insertar_(self,text):
        reporte_(self).exec_()
        self.catalogo,self.eventos_reporte=guardar_informacion_diaria(self.directorios['archivo_csv'],self.directorio_trabajo,self.catalogo,self.eventos)
        self.catalogo=ordenar_y_eliminar_duplicados(self.catalogo,0)
        self.guardar_evento()
        

    def Salir_(self):
        """
        Genera/abre un reporte temporal y controla el flujo según:
          - radioButton_inicial / radioButton_revision / checkBox_detalles
          - bandera self.revision_procesamiento (definida como False en otra instancia)

        Comportamiento:
          * inicial: checkBox_detalles siempre marcado y deshabilitado.
          * revision: checkBox_detalles habilitado (usuario decide).
          * checkBox_detalles desmarcado: salir sin hacer nada.
          * primera vez (revision_procesamiento=False): genera/abre PDF, muestra aviso notorio y retorna sin cerrar.
          * segunda vez (revision_procesamiento=True): ejecuta flujo original (confirmación para borrar y cerrar).
        """
        print("Saliendo sin procesamiento", self.horario)

        # --- 1) Reglas de interfaz: radio buttons y checkbox de detalles ---
        if self.ui.radioButton_inicial.isChecked():
            # En modo inicial: obligar detalles activados y bloquear el checkbox
            self.ui.checkBox_detalles.setChecked(True)
            self.ui.checkBox_detalles.setEnabled(False)
        elif self.ui.radioButton_revision.isChecked():
            # En modo revisión: permitir al usuario marcar/desmarcar detalles
            self.ui.checkBox_detalles.setEnabled(True)
        # Si no desea detalles, no hay nada que hacer
        if not self.ui.checkBox_detalles.isChecked():
            self.close()

        # --- 3) Rutas y fecha ---
        archivo_reporte_temporal = os.path.join(
            self.directorios['Directorio_base'],
            Path(self.archivo).name[:-6] + '_' + self.horario[:2]+ '_' + self.horario[8:10]+ '_' + self.responsable + '.pdf'
        )
        nombre = Path(self.archivo).stem  # AAAAMMDD_hhmmss
        fecha = QDate(int(nombre[0:4]), int(nombre[4:6]), int(nombre[6:8]))
        # --- 4) Cargar datos del día y preparar arbol XML ---
        self.eventos_reporte, self.catalogo, self.eventos, \
        self.vector, self.evento_canales, \
        self.root, self.responsables, self.resumen = cargar_dia(self.directorios)
        escritura_archivo(self.directorios['archivo_responsables'], self.responsables)
        tree = ET.ElementTree(self.root)
        self.estaciones_eventos = []

        # --- 2) Preparación de banderas (conserva tu lógica) ---
        resumen_responsables=self.responsables[0]
        if self.horario == '00:00 - 12:00':
            resumen_responsables.append(self.responsables[1])
        elif self.horario == '12:00 - 18:00':
            resumen_responsables.append(self.responsables[2])
        else:
            resumen_responsables.append(self.responsables[3])

        # --- 6) Control por bandera de revisión ---
        if not self.revision_procesamiento:
            # --- 5) Generar el PDF temporal SIEMPRE que detalles esté marcado ---
            subtitulo_reporte="Reporte temporal"
            mapa_resumen=1
            tipo_mapa=0
            resumen_responsables=0
            bandera_relleno=True
            modo_reporte=MODO_PERIODO_FRANJAS
            bandera_firma=False
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
                bandera_relleno
                )

            os.startfile(archivo_reporte_temporal)            
    # Primera pasada: activar bandera, avisar y NO cerrar
            self.revision_procesamiento = True
            # Mensaje MUY notorio en el label con ruta del archivo
            mensaje_html = (
                f"<span style='font-size:14pt; font-weight:700; color:#B00020;'>"
                f"¡Revise el archivo!</span><br>"
                f"<span style='font-size:12pt;'>{archivo_reporte_temporal}</span>"
            )
            self.ui.Lbl_submensajes.setText(mensaje_html)
            return
        else:
            self.ui.Lbl_submensajes.setText("")
        
        # --- 7) Segunda pasada: flujo original con confirmación de borrado y cierre ---
        aux = "Se revisó archivo reporte\n" + archivo_reporte_temporal
        message_box = QMessageBox(
            QMessageBox.Question,
            "¡Importante!",
            aux, QMessageBox.Yes | QMessageBox.No,
            self.window()
        )
        result = message_box.exec_()

        if result == QMessageBox.Yes:
            # Intentar borrar (hasta 3 intentos por archivo en uso)
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
        # Cierre de la ventana en la segunda pasada
        self.close()


    def closeEvent(self, event):
        """
        Emite la señal de cerrado para notificar a la ventana principal y realiza limpieza si es necesario.
        """
        self.limpiar_estado()
        self.cerrado.emit()
        super().closeEvent(event)



class ventana_grafico(QMainWindow):
    def __init__(self, procesamiento, archivo_estaciones, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mapa GIS")
        self.setGeometry(100, 100, 800, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.widget_grafico = widget_grafico_mpl(self)
        self.layout.addWidget(self.widget_grafico)
        self.widget_grafico.plot(procesamiento, archivo_estaciones)
        self.bandera = self.widget_grafico.plot(procesamiento, archivo_estaciones)
    
    def get_bandera(self):
        return self.bandera

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
    senal_procesamiento_cambiado = pyqtSignal(list)
    def __init__(self, estaciones_eventos,filtros,responsable,parent=None):
        super(estaciones_,self).__init__(parent)
        self.setWindowTitle("ESTACIONES")
        self.parent=parent
        self.parametros=parametros_estaciones()
        self.estaciones_eventos=estaciones_eventos
        self.filtros=filtros
        self.responsable=responsable
        self.numero_estaciones=len(self.estaciones_eventos)
        self.setFixedSize(600, 600)
 
# Widgets gráficos
        self.widget_grafico = widget_grafico_mpl(self)

        self.ck_box_hab_canal={}
        self.lbl_nombre={}
        self.lbl_codigo={}
        self.ck_box_hab_canal = {}
        self.ck_box_filtro = {}
        self.lbl_grafico_0=QLabel("ESTACIONL",self)
        self.lbl_grafico_0.setGeometry(40, 20, 61, 16)  #setGeometry(x, y, width, height)
        self.lbl_grafico_1=QLabel("CÓDIGO",self)
        self.lbl_grafico_1.setGeometry(138, 20, 50, 16)
        self.lbl_grafico_2=QLabel("HAB",self)
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
        self.procesamiento=self.parent.procesamiento
        lista_estaciones=[]
        for i in range(0, self.numero_estaciones):
            canal_=int(self.estaciones_eventos[i])
            lista_estaciones.append(self.parametros['NOMBRE'][canal_])
            dato=self.parent.evento_procesar[canal_+3]
            self.lbl_nombre[i]=QLabel(self.parametros['NOMBRE'][canal_],self)
            self.lbl_nombre[i].setGeometry(15, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.lbl_codigo[i]=QLabel(self.parametros['CODIGO'][canal_],self)
            self.lbl_codigo[i].setGeometry(150, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.ck_box_hab_canal[i]=QCheckBox(self)
            self.ck_box_hab_canal[i].setGeometry(208, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            if dato[5:6]=='1':
                self.ck_box_hab_canal[i].setChecked(True)
            else:
                self.ck_box_hab_canal[i].setChecked(False)
            self.spbox_canal[i]=QSpinBox(self)
            self.spbox_canal[i].setGeometry(250, i*25+35, 40, 24)            
            self.spbox_canal[i].setRange(1, 3)
            self.spbox_canal[i].setValue(int(dato[4:5]))
            estacion_i=int(self.estaciones_eventos[i])
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
        self.Btn_graficar = QPushButton("Señales", self)
        self.Btn_graficar.setGeometry(240, 470, 50, 24)  #setGeometry(x, y, width, height)
        self.Btn_graficar.setEnabled(True)
        self.Btn_graficar.clicked.connect(self.Graficar_)
        self.Btn_graficar.clearFocus()
        self.Btn_ubicacion = QPushButton("Ubicación", self)
        self.Btn_ubicacion.setGeometry(340, 470, 60, 24)  #setGeometry(x, y, width, height)
        self.Btn_ubicacion.setEnabled(True)
        self.Btn_ubicacion.clicked.connect(self.Ubicacion_)
        self.Btn_ubicacion.clearFocus()

        self.Btn_salir_procesamiento = QPushButton("Salir", self)
        self.Btn_salir_procesamiento.setGeometry(500, 470, 60, 24)

        self.Btn_salir_procesamiento.clicked.connect(self.solicitar_cierre)
        self.Btn_salir_procesamiento.setVisible(True)
        
        self.mapa_inicial_enviado = False  # control para primer dibujado

        self.bandera_procesamiento=0

    def solicitar_cierre(self):
        """
        El usuario presiona el botón SALIR.
        Aquí se llama a close(), lo que ejecuta closeEvent() normalmente.
        Después, el padre eliminará el widget del panel central.
        """
        self.close()   # --> Esto SI ejecuta closeEvent()


    def showEvent(self, event):
        ############# Hilo monitor de cambio de archivo#################        
        super().showEvent(event)
        if self.parent.evento_procesar[2]=='SISMO':
            self.parent.bandera_virtual=verificar_drives_virtuales(self.responsable)

            if self.parent.bandera_virtual:

                padre = self.window()   # devuelve la ventana Procesar_evento
                QTimer.singleShot(300, lambda: padre.iniciar_espera_archivos_virtual())
                guardar_intento(self.parent.evento_procesar[1],self.parent.directorio_trabajo,self.parent.responsable_evento,self.procesamiento)
            else:
                if os.path.exists(self.parent.archivos_procesamiento_real[1]):
                    mensaje=" encontrado\nRevisión y modificacion de tipo de evento"
                    QMessageBox.information(self, "AVISO", 'Evento ' + self.parent.archivos_procesamiento_real[1] + mensaje)
                else:
                    mensaje='Evento ' +self.parent.archivos_procesamiento_real[1]+" no encontrado\nNo está conectado el Virtual"
                    QMessageBox.information(self, "AVISO", mensaje)
                    self.accept()

        # --- Dibujado inicial del mapa embebido (una sola vez) ---
        try:
            if not self.mapa_inicial_enviado and hasattr(self, 'procesamiento') and self.procesamiento:
                self.Ubicacion_()  # usa el mismo flujo que en las actualizaciones
                self.mapa_inicial_enviado = True
        except Exception as e:
            print("Error al emitir mapa inicial:", e)





    def update_procesamiento(self, procesamiento):
        """
        Se ejecuta en el hilo principal cada vez que el monitor detecta un cambio.
        Política:
        - Actualiza self.procesamiento
        - Crea/guarda inmediatamente el archivo de procesamiento (solo ese)
        - Dispara el dibujado (como si se pulsara 'Ubicación'), sin abrir ventanas
        - Sin modales ni cambio de foco
        """
        try:
            # 1) Actualiza en memoria
            self.procesamiento = procesamiento

            # 2) Guardar archivo de procesamiento (primera vez incluida)
            ruta_proc = self.parent.directorios['archivo_procesamiento']
            os.makedirs(os.path.dirname(ruta_proc), exist_ok=True)
            escritura_archivo(ruta_proc, self.procesamiento)

            # 3) Mensaje discreto si falta coda
            if self.procesamiento and len(self.procesamiento[-1]) > 3:
                if self.procesamiento[-1][2] != 'Fallido' and self.procesamiento[-1][3] == '0.0':
                    self.parent.ui.Lbl_submensajes.setText("No se ha marcado el tiempo de coda")

            # 4) Simular "aplastar Ubicación": dibuja en el panel derecho embebido
            self.Ubicacion_()

        except Exception as e:
            print("Error en update_procesamiento:", e)
            self.parent.ui.Lbl_submensajes.setText("Error al guardar/actualizar (ver consola).")

 
    def closeEvent(self, event):
        archivo=self.parent.evento_procesar[1]
        print("Copiando desde virtual a real")
        archivos_1=archivos_fast(archivo,self.parent.directorio_trabajo,self.parent.responsable_evento)
        archivos_2=verificar_coincidencias(self.parent.eventos,self.parent.evento_procesar[1],archivos_fast(archivo,self.parent.directorio_trabajo,''))
        copiar_archivos(archivos_1,archivos_2)
        for archivo_borrar in archivos_1:
            if os.path.exists(archivo_borrar):
                try:
                    os.remove(archivo_borrar)
                except PermissionError:
                    QMessageBox.information(self, "Archivos abiertos", "Cierre el archivo en el Proceso V2.")
                    event.ignore()
        auxiliar=[]



        # ---------------------------------------------------------------
        # Detener el hilo de monitoreo de forma segura
        # ---------------------------------------------------------------
        if hasattr(self, 'file_monitor') and self.file_monitor.isRunning():
            self.file_monitor.requestInterruption()  # pide detener el hilo
            self.file_monitor.wait()                 # espera a que termine correctamente
            self.bandera_procesamiento = 0
            self.parent.ui.Lbl_Mensajes.setText("Seguimiento terminado")
            self.parent.ui.Lbl_submensajes.setText("")
        # ---------------------------------------------------------------

        self.parent.estaciones_eventos=auxiliar
        self.parent.filtros_estaciones=self.filtros
        self.parent.procesamiento=self.procesamiento
        for i in range(0, self.numero_estaciones):
            canal_=int(self.estaciones_eventos[i])
            indice_evento=self.parent.indice_evento_procesar
            estacion_i=int(self.estaciones_eventos[i])
            indice_estacion=self.parent.estaciones_eventos_total.index(estacion_i)
            self.parent.componente_canal=str(self.spbox_canal[i])
            cadena=self.parent.eventos[indice_evento][canal_+3]
            if self.ck_box_hab_canal[i].checkState()==2:
                auxiliar.append(canal_)
            if self.ck_box_filtro[i].checkState()==2:
                orden_i=self.spbox_fil_orden[i].value()
                finf_i=self.spbox_fil_finf[i].value()
                fsup_i=self.spbox_fil_fsup[i].value()
                string_concatenado = f"{orden_i:02}{finf_i:02}{fsup_i:02}"
            else:
                string_concatenado='000000'
            if self.ck_box_hab_canal[i].checkState()==2:
                valor='1'
            else:
                valor='0'
            self.parent.eventos[indice_evento][canal_+3]=cadena[:5]+valor+string_concatenado
            self.parent.filtros_estaciones[indice_estacion]=string_concatenado
        guardar_intento(self.parent.evento_procesar[1],self.parent.directorio_trabajo,self.parent.responsable_evento,self.procesamiento)
        escritura_archivo(self.parent.directorios['archivo_csv'],self.parent.eventos) #Guarda los cambios.
        escritura_archivo(self.parent.directorios['archivo_procesamiento'],self.procesamiento) #Guarda los cambios.
        escritura_archivo(self.parent.directorios['archivo_reporte'],self.parent.eventos_reporte)
        escritura_archivo(self.parent.directorios['archivo_catalogo'],self.parent.catalogo)
        print("Saliendo de estaciones en close")

        if hasattr(self.parent, "limpiar_panel_central"):
            self.parent.limpiar_panel_central()




    def Salir_(self):
        self.close()


    def Graficar_(self):
        print("Entró a graficar")
        archivo=self.parent.evento_procesar[1]
        archivo=os.path.join(self.parent.directorio_trabajo,archivo[:8]+archivo[9:15])
        self.trCanal=leer_mseed(archivo,1)
        t_inicio=self.trCanal[self.estaciones_eventos[0]][0].stats.starttime
        t_final=self.trCanal[self.estaciones_eventos[0]][0].stats.endtime
        grafico_evento_int(self.visor,self.trCanal,t_inicio,t_final,self.estaciones_eventos,self.parametros['HAB_GRAFICO'],0,0) #El ultimo parametro es la página, hay que gestionarla para que se despleigue


    def Ubicacion_(self):
        """
        Dispara el dibujado de la ubicación en el panel derecho embebido
        de la ventana padre. No abre ventanas nuevas.
        """
        try:
            print("Entró a ubicación")
            # Delegamos el dibujado al padre, que tiene el widget del mapa embebido
            if hasattr(self.parent, "actualizar_mapa_desde_procesamiento"):
                self.parent.actualizar_mapa_desde_procesamiento(self.procesamiento)
            else:
                print("Advertencia: el padre no tiene 'actualizar_mapa_desde_procesamiento'.")

        except Exception as e:
            print("Error en Ubicacion_:", e)
            if hasattr(self.parent, "Lbl_submensajes"):
                self.parent.ui.Lbl_submensajes.setText("Error al actualizar ubicación (ver consola).")


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
