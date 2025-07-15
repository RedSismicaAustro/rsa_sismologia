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


from metodos_gis_rsa import widget_grafico_mpl
from metodos_rsa import obtencion_hora,leer_mseed,parametros_estaciones,grafico_evento_int,archivos_fast,verificar_coincidencias
from metodos_rsa import copiar_archivos,lectura_archivo,escritura_archivo,guardar_informacion_diaria,guardar_intento,ordenar_y_eliminar_duplicados,insertar_evento_otras_redes,cargar_dia,cargar_evento
from metodos_gestion import obtener_directorios
from metodos_reportes_individuales import generar_reporte_sismo
#from metodos_reportes_individuales import insertar_evento_otras_redes
from PyQt5.QtWidgets import (QApplication,QMainWindow,QMessageBox,QDialog,QLabel,QCheckBox,QPushButton,QComboBox,QSpinBox,QTextEdit,QVBoxLayout,QWidget)
from PyQt5 import uic, QtWidgets#Importamos módulo uic y Qtwidgets
import matplotlib.pyplot as plt
from datetime import datetime,timedelta
from PyQt5.QtCore import QDate
from PyQt5.QtCore import Qt,QTimer
import time
import threading
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

def activar_hilo(self):
        #archivo_monitoreo=self.parent.archivos_procesamiento_virtual[2]
        while not(self.bandera_procesamiento):
            archivo_monitoreo=archivos_fast(self.parent.evento_procesar[1],self.parent.directorio_trabajo,self.parent.responsable_evento)[2]
            if not(os.path.exists(archivo_monitoreo)):
                mensaje='Evento ' + archivo_monitoreo + " no encontrado\n Hay que ejecutar ProcesoV2"
                self.parent.Lbl_submensajes.setText(mensaje)
                #QMessageBox.information(self, "AVISO", mensaje)
                time.sleep(5)
                mensaje=''
                self.parent.Lbl_submensajes.setText(mensaje)
                time.sleep(5)
            else:
                self.bandera_procesamiento=1
                break
        # Crea una instancia de FileMonitor y pasa el programa principal y los parámetros
        if self.bandera_procesamiento:
            mensaje='Monitorizando en virtual'
            self.file_monitor = FileMonitor(
                archivo_monitoreo,
                lambda procesamiento: self.update_procesamiento(procesamiento),
                (self.parent.evento_procesar[1], self.parent.directorio_trabajo, self.parent.responsable_evento, self),
                self.procesamiento
            )
            self.file_monitor.start()
        else:
            mensaje='Sin Monitorizar,\ntrabajando en la estructura\nde datos'
        self.parent.Lbl_Mensajes.setText(mensaje)
    
def cargar_combo_eventos(self,text):
    self.sismos_procesar=[]
    self.cmbx_eventos.clear()
    if self.eventos_reporte!=None:
        eventos_reporte=int(self.eventos_reporte[-1:][0][0])
    else:
        eventos_reporte=0
    for i in range(0,len(self.eventos)):
                if self.eventos[i][2]==text:
                    aux_sismo=(int(self.eventos[i][0]),self.eventos[i][1])#aux_sismo tiene el numero de evento del csv y todo el registro
                    self.sismos_procesar.append(aux_sismo)
                    self.cmbx_eventos.addItem(self.eventos[i][1])
    self.preparar_evento('')
    

class FileMonitor:
    def __init__(self, file_path, update_callback, callback_params, procesamiento):
        self.file_path = file_path
        self.update_callback = update_callback
        self.callback_params = callback_params
        self.procesamiento = procesamiento
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._monitor_file)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def _monitor_file(self):
        last_modified_time = os.path.getmtime(self.file_path)
        while not self._stop_event.is_set():
            current_modified_time = os.path.getmtime(self.file_path)
            if current_modified_time != last_modified_time:
                print(f'Archivo modificado: {time.ctime(current_modified_time)}')
                last_modified_time = current_modified_time
                archivo_csv, directorio, responsables, main_program = self.callback_params
                self.update_callback(guardar_intento(archivo_csv,directorio,responsables,main_program.procesamiento))
            time.sleep(1)

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
        
class MyApp(QMainWindow):
    def __init__(self,parent=None):#Constructor de la clase
        super(MyApp,self).__init__(parent)
        QMainWindow.__init__(self) #Constructor
        #Carga la configuración del archivo .ui en el objeto
        ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src','ui',"Proceso.ui"))
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui,self)

        self.visor = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.visor)

        self.setWindowTitle("PROCESAMIENTO")
        self.btn_abrir.clicked.connect(self.Abrir_archivo)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.Btn_eventos.clicked.connect(self.guardar_evento)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_procesar.clicked.connect(self.procesar_)
        self.Btn_reportar.clicked.connect(self.reportar_)
        self.Btn_insertar.clicked.connect(self.insertar_)
        self.Btn_renombrar.clicked.connect(self.renombrar_)
        self.Btn_coeficientes.clicked.connect(self.cambiar_coeficientes_)
        self.cmbx_eventos.activated[str].connect(self.preparar_evento) 
        self.Cmb_bx_tipo_evento.activated[str].connect(self.cambio_evento)
        self.cmbx_t_evento.activated[str].connect(self.cargar_tipo_evento)
        self.parametros=parametros_estaciones()
        self.pagina=0
        self.registro_tiempo=0
        d=datetime.today()              #obtención de la fecha y hora actual
        d = QDate(d.year, d.month,d.day)# obtención del año , mes y día en forma individual
        self.dateEdit.setDate(d)    #Conficuración de los datos de fecha en el DataEdit
        self.dateEdit.dateChanged.connect(self.showDate)
        self.directorio_trabajo='G:\Mi unidad\DIA\\' #self.directorio_trabajo=dir_trabajo[0:aux-9]
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.showDate(d)
        self.canales_habilitados=[]
        for i in range(0,101):
            if self.parametros['HAB_CANAL'][i]=='1':
                self.canales_habilitados.append(i)
        self.numero_estaciones=len(self.canales_habilitados)
        self.lbl_directorio_trabajo=self.directorio_trabajo

    
    def closeEvent(self, event):
        print("Cerrar_archivo")
        
    def cambiar_coeficientes_(self):
        self.cambio_coeficientes_filtro = Cambio_Coeficientes_Filtro(self.canales_habilitados)
        
            
    
    def showDate(self, date):#Es como inicializar el dìa
        self.date=date
        self.archivo=self.directorio_trabajo+date.toString('yyyyMMdd000000')
        self.estaciones_eventos=[]
        self.bandera_marcas=1
        self.cmbx_eventos.clear()
        self.grupo_carga.setEnabled(False)

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath
        self.Lbl_directorio.setText(self.directorio_trabajo)

        self.showDate(self.date)

    def Abrir_archivo(self):  #Depurado
        print("Abrir_archivo")
        self.cmbx_eventos.clear()
        self.Cmb_bx_tipo_evento.clear()
        lista_filtros = ["Ruido", "FF", "FC","TELESISMO","SISMO","INDEFINIDO","Evento_local",'CONTROL','REVISION','TODOS']
        self.Cmb_bx_tipo_evento.addItems(lista_filtros)
        self.cmbx_t_evento.addItems(lista_filtros)
        self.cmbx_t_evento.setCurrentText('SISMO')
        self.directorio=obtener_directorios(self.archivo)
        self.grupo_carga.setEnabled(True)
        #Cargar día
        print(self.directorio['archivo_csv'])
        self.eventos_reporte,self.catalogo,self.eventos,\
        vector,self.evento_canales,\
        root,self.responsables,self.resumen=cargar_dia(self.directorio['archivo_csv'])

        cargar_combo_eventos(self,'SISMO')
        self.archivo_estaciones=self.directorio['archivo_estaciones']
        self.ck_box_hab_canal={}
        self.lbl_nombre={}
        self.lbl_codigo={}
        self.ck_box_hab_canal = [0 for x in range(16)]


    def guardar_evento(self):
        print("Guardar evento")
        escritura_archivo(self.directorio['archivo_csv'],self.eventos)
        escritura_archivo(self.directorio['archivo_reporte'],self.eventos_reporte)
        escritura_archivo(self.directorio['archivo_catalogo'],self.catalogo)

    def preparar_evento(self, text):
        print("Preparar evento:")
        for i,evento in enumerate(self.eventos):
            if evento[1]==self.cmbx_eventos.currentText():
                self.indice_evento_procesar=i
                self.evento_procesar=evento
                self.parametro=evento[0]+"  "+evento[1]+"  "+evento[2]
                break
        verificar_coincidencias(self.eventos, self.evento_procesar)
        aux=int(self.evento_procesar[1][-10:-4])
        if aux<120000:
            indice_hora=1
        elif aux<180000:
            indice_hora=2
        elif aux<240000:
            indice_hora=3
        horario=['',"00:00 - 12:00", "12:00 - 18:00", "18:00 - 24:00"]
        self.responsable_evento=self.responsables[indice_hora][0]
        self.Cmb_bx_tipo_evento.setCurrentText(self.evento_procesar[2])
        self.txt_responsables.setText(self.responsable_evento)
        self.txt_horario.setText(horario[indice_hora])
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
            self.directorio['Directorio_reportes']   # Directorio de reportes
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
        escritura_archivo(self.directorio['archivo_csv'],self.eventos)
        self.catalogo,self.eventos_reporte=guardar_informacion_diaria(self.directorio['archivo_csv'],self.directorio_trabajo,self.catalogo,self.eventos)
        self.eventos_reporte,self.catalogo,self.eventos,\
        vector,self.evento_canales,\
        root,self.responsables,self.resumen=cargar_dia(self.directorio['archivo_csv'])
        

    def cargar_tipo_evento(self, text):
        cargar_combo_eventos(self,text)

    def procesar_(self,text):
        archivo=self.evento_procesar[1]
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
        self.archivo_procesar=self.directorio['Directorio_procesamiento']+'/'+archivo[:-4]+'_proc'+'.csv'
        if os.path.exists(self.archivo_procesar):
            self.procesamiento=lectura_archivo(self.archivo_procesar)
        else:
            self.procesamiento=[[' ',"Fecha_Hora","Prof.(km)","Magn.","Lat.","Long.","rms"]]
            ahora = datetime.now()
            fecha_formateada = ahora.strftime("%Y-%m-%d %H:%M:%S")
            self.procesamiento.append(['0',fecha_formateada,"Inicio"," "," "," "," "])
        try:
            path = Path(self.directorio['Directorio_procesamiento'])
            path.mkdir(parents=True)
        except FileExistsError:
            pass
        estaciones_(self.estaciones_eventos,self.filtros_estaciones,self.responsable_evento,self).exec_()

    def reportar_(self):
        #print('Reportar')
        generar_reporte_sismo(self.catalogo, self.evento_reporte_escogido, self.canales, self.trCanal, self.archivo_reporte)

    def insertar_(self,text):
        #print('Insertar de otas redes')
        reporte_(self).exec_()
        self.catalogo,self.eventos_reporte=guardar_informacion_diaria(self.directorio['archivo_csv'],self.directorio_trabajo,self.catalogo,self.eventos)
        self.catalogo=ordenar_y_eliminar_duplicados(self.catalogo,0)
        self.guardar_evento()
        


    def renombrar_(self,text):
        #print("Renombrar:")
        message_box = QMessageBox(
            QMessageBox.Question,
            "¡Importante!",
            "  Va a renombrar el evento\nretándole 1 minuto",
            QMessageBox.Yes | QMessageBox.No ,
            self.window()
        )
        result = message_box.exec_()
        if result == QMessageBox.Yes:
            archivo=self.evento_procesar[1]
            archivos_origen=archivos_fast(archivo,self.directorio_trabajo,'')
            hora=obtencion_hora(archivo[:6]+archivo[7:13])
            fecha_hora = hora
            fecha_hora_menos_un_minuto = fecha_hora - timedelta(minutes=1)
            formato_fecha_hora = "%y%m%d_%H%M%S.sis"
            indice_catalogo="%Y%m%d%H%M%00"
            archivo_modificado = fecha_hora_menos_un_minuto.strftime(formato_fecha_hora)
            archivos_destino=archivos_fast(archivo_modificado,self.directorio_trabajo,'')
            archivos_destino[2]= archivos_destino[2][:-12]+archivo_modificado[-15:-11]+archivo_modificado[-10:-6]+'.rsa'
            archivos_destino[3]= archivos_destino[2][:-12]+'Phase'+archivo_modificado[-13:-11]+archivo_modificado[-10:-9]+'.'+archivo_modificado[-9:-6]
            archivos_destino[4]= archivos_destino[2][:-12]+archivo_modificado[-15:-11]+archivo_modificado[-10:-8]+'.'+archivo_modificado[-8:-6]+'L'
            archivos_destino[5]= archivos_destino[2][:-12]+archivo_modificado[-15:-11]+archivo_modificado[-10:-8]+'.'+archivo_modificado[-8:-6]+'P'
            archivos_destino[6]= archivos_destino[2][:-12]+archivo_modificado[-15:-11]+archivo_modificado[-10:-8]+'.'+archivo_modificado[-8:-6]+'S'
            self.eventos[self.indice_evento_procesar][1]=archivo_modificado
            for i,buscado in enumerate(self.eventos_reporte):
                if buscado[1]==archivo:
                    self.eventos_reporte[i][1]=archivo_modificado
                    break
            for i,buscado in enumerate(self.catalogo):
                if buscado==[]:
                    continue
                if buscado[18]==archivo:
                    self.catalogo[i][18]=archivo_modificado
                    self.catalogo[i][0]=indice_catalogo
                    break
            estaciones=[]
            for i in range(0,101):
                if self.eventos[self.indice_evento_procesar][i+3]!='-':
                    estaciones.append(self.eventos[self.indice_evento_procesar][i+3][:4])
            for estacion in estaciones:
                archivo_mseed_origen=self.directorio['Directorio_eventos']+'/'+estacion+'_20'+archivo[:-3]+'mseed'
                archivo_mseed_destino=self.directorio['Directorio_eventos']+'/'+estacion+'_20'+archivo_modificado[:-3]+'mseed'
                os.rename(archivo_mseed_origen,archivo_mseed_destino)
            for i in range(0,7):
                os.rename(archivos_origen[i], archivos_destino[i])
            escritura_archivo(self.directorio['archivo_csv'],self.eventos)
            escritura_archivo(self.directorio['archivo_reporte'],self.eventos_reporte)
            escritura_archivo(self.directorio['archivo_catalogo'],self.catalogo)
            #self.guardar_evento()

    def Salir_(self):
        self.close()



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

class estaciones_(QDialog):
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
        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", "secundaria.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)
# Widgets gráficos
        self.widget_grafico = widget_grafico_mpl(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.widget_grafico)
        self.setLayout(layout)
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
        self.bandera_procesamiento=0

    def showEvent(self, event):
        ############# Hilo monitor de cambio de archivo#################        
        super().showEvent(event)
        if self.parent.evento_procesar[2]=='SISMO':
            self.parent.bandera_virtual=verificar_drives_virtuales(self.responsable)

            if self.parent.bandera_virtual:
                QTimer.singleShot(1000, lambda: activar_hilo(self))
                guardar_intento(self.parent.evento_procesar[1],self.parent.directorio_trabajo,self.parent.responsable_evento,self.procesamiento)
            else:
                if os.path.exists(self.parent.archivos_procesamiento_real[1]):
                    mensaje=" encontrado\nRevisión y modificacion de tipo de evento"
                    QMessageBox.information(self, "AVISO", 'Evento ' + self.parent.archivos_procesamiento_real[1] + mensaje)
                else:
                    mensaje='Evento ' +self.parent.archivos_procesamiento_real[1]+" no encontrado\nNo está conectado el Virtual"
                    QMessageBox.information(self, "AVISO", mensaje)
                    self.accept()

    def update_procesamiento(self, procesamiento):
        self.procesamiento = procesamiento
        if self.procesamiento[-1][2]!='Fallido':
            if self.procesamiento[-1][3]=='0.0':
                self.parent.Lbl_submensajes.setText("No se ha marcado el tiempo de coda")

    def closeEvent(self, event):
        archivo=self.parent.evento_procesar[1]
        archivos_1=archivos_fast(archivo,self.parent.directorio_trabajo,self.parent.responsable_evento)
        archivos_2=archivos_fast(archivo,self.parent.directorio_trabajo,'')
        copiar_archivos(archivos_1,archivos_2)
        for archivo_borrar in archivos_1:
            if os.path.exists(archivo_borrar):
                try:
                    os.remove(archivo_borrar)
                except PermissionError:
                    QMessageBox.information(self, "Archivos abiertos", "Cierre el archivo en el Proceso V2.")
                    event.ignore()
        auxiliar=[]
        ############# Hilo monitor de cambio de archivo#################
        if self.bandera_procesamiento:
            self.file_monitor.stop()
            self.bandera_procesamiento=0
            self.parent.Lbl_Mensajes.setText("Seguimiento terminado")
            self.parent.Lbl_submensajes.setText("")
        ################################################################
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
        escritura_archivo(self.parent.directorio['archivo_csv'],self.parent.eventos) #Guarda los cambios.
        escritura_archivo(self.parent.directorio['archivo_procesamiento'],self.procesamiento) #Guarda los cambios.
        escritura_archivo(self.parent.directorio['archivo_reporte'],self.parent.eventos_reporte)
        escritura_archivo(self.parent.directorio['archivo_catalogo'],self.parent.catalogo)
        print("Saliendo de estaciones en close")

    def Salir_(self):
        print("Saliendo de estaciones en salir")
        self.destroy()

    def Graficar_(self):
        print("Entró a graficar")
        plt.close()
        archivo=self.parent.evento_procesar[1]
        archivo=self.parent.directorio_trabajo+'/'+archivo[:6]+archivo[7:13]
        self.trCanal=leer_mseed(archivo,1)
        t_inicio=self.trCanal[self.estaciones_eventos[0]][0].stats.starttime
        t_final=self.trCanal[self.estaciones_eventos[0]][0].stats.endtime
        grafico_evento_int(self.visor,self.trCanal,t_inicio,t_final,self.estaciones_eventos,self.parametros['HAB_GRAFICO'],0,0) #El ultimo parametro es la página, hay que gestionarla para que se despleigue


    def Ubicacion_(self):
        print("Entró a ubicación")
        self.grafico_window = ventana_grafico(self.procesamiento, self.parent.directorio['archivo_estaciones'], self)
        self.grafico_window.show()
        bandera = self.grafico_window.get_bandera()
        if bandera[0]:
            mensaje = 'Procesar con 6 fases mínimo,\n (Con 5 en la parte superior)'
        elif bandera[1]:
            mensaje = 'Procesar con fases claras'
        else:
            mensaje = 'No Procesar'
        self.parent.Lbl_submensajes.setText(mensaje)

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
        escritura_archivo(self.parent.directorio['archivo_reporte'],self.parent.eventos_reporte)
        escritura_archivo(self.parent.directorio['archivo_catalogo'],self.parent.catalogo)

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



#Instanciar para iniciar una aplicacion
app = QApplication(sys.argv)
#crear un objeto de la clase
window=MyApp()
#Mostrar ventana
window.show()
#ejecutar la aplicación
app.exec_()
