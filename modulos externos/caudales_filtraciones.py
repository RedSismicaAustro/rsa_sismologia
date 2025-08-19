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



from PyQt5.QtWidgets import (QMessageBox, QFileDialog)
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QDate
from obspy import read, UTCDateTime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

from metodos_gestion import obtener_directorios
from metodos_rsa import lectura_archivo, extraccion, escritura_archivo,obtencion_hora,ordenar_y_eliminar_duplicados


# Cargar la interfaz desde el archivo .ui directamente en esta instancia
ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", "caudales.ui")
qtCreatorFile = os.path.abspath(ruta_ui)

Ui_MainWindow,QtBassClass=uic.loadUiType(qtCreatorFile)#El modulo ui carga


class Caudales(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        QtWidgets.QMainWindow.__init__(self)#Constructor
        Ui_MainWindow.__init__(self)#Constructor
        self.setupUi(self)# Método Constructor de la ventana
        self.setWindowTitle("CAUDALES    --")
        self.setGeometry(200, 150, 600, 500)
        hoy = QDate.currentDate()
        semana_atras = hoy.addDays(-7)
        self.selector_fecha_inicio.setDate(semana_atras)
        self.selector_fecha_fin.setDate(hoy)
        self.selector_fecha_grafico.setDate(hoy)
        self.selector_fecha_grafico.dateChanged.connect(self.cargar_componentes_fecha)
        self.combo_diezmado.addItems(["1", "2", "5", "8", "10"])
        self.combo_diezmado.setCurrentText("10")
        self.combo_traza.setFixedWidth(200)
        self.Lbl_directorio.setText("Directorio de trabajo: G:/Mi unidad/DIA/")
        # === Formulario de configuración ===
        self.boton_cargar_eventos_control.clicked.connect(self.cargar_eventos_control)
        self.boton_directorio.clicked.connect(self.seleccionar_directorio_trabajo)
        self.boton_graficar.clicked.connect(self.desplegar_grafico)
        self.boton_guardar_marcas.clicked.connect(self.guardar_marcas)
        self.boton_graficar_caudales.clicked.connect(self.graficar_caudales)
        self.boton_salir.clicked.connect(self.close)
        # === Variables internas ===
        self.directorio_trabajo = "G:/Mi unidad/DIA/"
        self.stream = None
        self.archivo = ""
        self.archivo_mseed = ""
        self.directorios = {}
        self.traza_id = ""
        self.marcas_usuario = []
        self.tr_segmento = None
        self.caudales = []
        self.cargar_componentes_fecha()

    def seleccionar_directorio_trabajo(self):
        folderpath = QFileDialog.getExistingDirectory(self, 'Selecciona el directorio de trabajo')
        if folderpath:
            if not folderpath.endswith('/'):
                folderpath += '/'
            self.directorio_trabajo = folderpath
            self.Lbl_directorio.setText(f"Directorio de trabajo: {self.directorio_trabajo}")
            

    def cargar_componentes_fecha(self):
        fecha = self.selector_fecha_grafico.date()
        self.archivo_mseed = f"CHA2_{fecha.toString('yyyyMMdd')}_000000.mseed"
        self.archivo = os.path.join(self.directorio_trabajo, fecha.toString("yyyyMMdd") + "000000")
        self.directorios = obtener_directorios(self.archivo)
        ruta_archivo = os.path.join(self.directorios['Directorio_registros'], self.archivo_mseed)
        if os.path.isfile(ruta_archivo):
            self.stream = read(ruta_archivo)
            self.cargar_componentes(self.stream)
            
        else:
            print(ruta_archivo,"  no existe")
            self.stream=None
        
        archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
        if os.path.isfile(archivo_caudales):
            self.caudales = lectura_archivo(archivo_caudales)
            self.recalcular_caudales()  # ✅ Recalcula siempre los caudales, incluso si la bandera es 0 o 1
            escritura_archivo(archivo_caudales, self.caudales)
        else:
            self.caudales = []



    def recalcular_caudales(self):
        """
        Recalcula los valores de caudal para todos los eventos en self.caudales.
        El valor se recalcula como 3500000 / segundos entre eventos consecutivos.
        La bandera original (columna 3) se conserva.
        """
        try:
            # Ordenamos los eventos por nombre
            eventos_ordenados = sorted(self.caudales, key=lambda fila: fila[0])
            nuevos_caudales = []
            for i, fila in enumerate(eventos_ordenados):
                
                if len(fila[0])==17:
                    fila[1]='20'+fila[1]
                evento = fila[0]
                bandera = fila[2] if len(fila) > 2 else "0"
                try:
                    dt_evento = datetime.strptime(evento.replace(".sis", ""), "%Y%m%d_%H%M%S")
                    if i > 0:
                        evento_anterior = eventos_ordenados[i - 1][0]
                        dt_anterior = datetime.strptime(evento_anterior.replace(".sis", ""), "%Y%m%d_%H%M%S")
                        segundos = int((dt_evento - dt_anterior).total_seconds())
                        caudal = int(3500000 / segundos) if segundos > 0 else 0
                    else:
                        caudal = 0
                    nuevos_caudales.append([evento, str(caudal), bandera])
                except Exception as e:
                    print(f"[ERROR] Fallo al procesar evento '{evento}': {e}")
                    nuevos_caudales.append([evento, "0", bandera])  # Al menos conservamos el evento
            self.caudales = nuevos_caudales
        except Exception as e:
            print(f"[ERROR] Error general al recalcular caudales: {e}")

    def cargar_componentes(self, stream):
        self.combo_traza.clear()
        traza_vertical_index = -1
        for i, traza in enumerate(stream):
            self.combo_traza.addItem(traza.id)
            if traza.id.endswith("Z") or traza.id.endswith("ENV"):
                traza_vertical_index = i
        self.combo_traza.setCurrentIndex(traza_vertical_index if traza_vertical_index != -1 else 0)


    def desplegar_grafico(self):
        if not self.stream:
            QMessageBox.warning(self, "Archivo no cargado", "Debes seleccionar una fecha válida.")
            return

        plt.close('all')
        self.marcas_usuario.clear()
        self.traza_id = self.combo_traza.currentText()
        tr = self.stream.select(id=self.traza_id)[0]

        fecha_grafico = self.selector_fecha_grafico.date().toPyDate()
        hora_inicio = datetime(fecha_grafico.year, fecha_grafico.month, fecha_grafico.day)
        hora_fin = hora_inicio + timedelta(days=1)

        self.tr_segmento = tr.copy()
        factor_diezmado = int(self.combo_diezmado.currentText())
        if factor_diezmado > 1:
            self.tr_segmento.decimate(factor_diezmado, no_filter=True)

        fig, ax = plt.subplots()
        tiempo = self.tr_segmento.times("matplotlib")
        datos = self.tr_segmento.data
        ax.plot(tiempo, datos, label=f"{self.tr_segmento.id} (x{factor_diezmado})")

        # === Eventos CONTROL del día gráfico ===
        eventos_control_dia = []
        self.eventos = lectura_archivo(self.directorios['archivo_csv'])
        for evento in self.eventos:
            if evento[2] == "CONTROL":
                eventos_control_dia.append(evento[1])
        for evento in eventos_control_dia:
            try:
                fila = next((f for f in self.caudales if f[0] == evento and f[2] == "1"), None)
                if not fila:
                    color_linea='red'
                else:
                    color_linea='green'
                dt_evento = datetime.strptime(evento.replace(".sis", ""), "%Y%m%d_%H%M%S")
                tiempo_relativo = mdates.date2num(dt_evento)
                ax.axvline(x=tiempo_relativo, color='green', linestyle=':', linewidth=1)
                ax.text(tiempo_relativo, max(datos) * 0.95, evento, rotation=90,
                        fontsize=7, verticalalignment='bottom', color=color_linea)
            except Exception as e:
                print(f"Error al graficar evento CONTROL del día: {evento} → {e}")

        ax.set_title(f"{self.traza_id} | {hora_inicio.strftime('%Y-%m-%d')}")
        ax.set_xlabel("Hora (UTC)")
        ax.set_ylabel("Amplitud")
        ax.legend()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        fig.autofmt_xdate()

        def on_right_click(event):
            if event.inaxes and event.button == 3:
                tiempo_click = event.xdata
                tolerancia = 1 / 1440
                limite_x = ax.get_xlim()
                limite_y = ax.get_ylim()
                for marca in self.marcas_usuario:
                    if abs(marca - tiempo_click) < tolerancia:
                        self.marcas_usuario.remove(marca)
                        break
                else:
                    if len(self.marcas_usuario) < 2:
                        self.marcas_usuario.append(tiempo_click)
                for line in ax.lines[1:]:
                    line.remove()
                for marca in self.marcas_usuario:
                    ax.axvline(marca, color='red', linestyle='--', linewidth=1)
                ax.set_xlim(limite_x)
                ax.set_ylim(limite_y)
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect('button_press_event', on_right_click)
        plt.show()

    def guardar_marcas(self):
        if len(self.marcas_usuario) != 2:
            QMessageBox.warning(self, "Error", "Debes seleccionar exactamente 2 marcas.")
            return
        marcas_ordenadas = sorted(self.marcas_usuario)
        marca_dt_inicio = mdates.num2date(marcas_ordenadas[0]).replace(tzinfo=None)
        marca_dt_fin = mdates.num2date(marcas_ordenadas[1]).replace(tzinfo=None)
        tiempo_inicio = int((marca_dt_inicio - datetime(marca_dt_inicio.year, marca_dt_inicio.month, marca_dt_inicio.day)).total_seconds())
        tiempo_fin = int((marca_dt_fin - datetime(marca_dt_fin.year, marca_dt_fin.month, marca_dt_fin.day)).total_seconds())
        
#########################################
#########################################
        eventos_auxiliar=lectura_archivo(self.directorios['archivo_auxiliar'])        
        tiempo = obtencion_hora(self.archivo)
        n_evento = 0
        tipo_evento = 'CONTROL'
        fecha_real = tiempo +tiempo_inicio  # Usado solo para generar nombre
        nombre_sis = fecha_real.strftime('%Y%m%d_%H%M%S.sis')
        ahora = datetime.now()
        estaciones="CHA231000000"
        evento_auxiliar=(n_evento,nombre_sis,tipo_evento,ahora, tiempo_inicio, tiempo_fin,'RSA',estaciones,'Caudales')
        eventos_auxiliar.append(evento_auxiliar)
        escritura_archivo(self.directorios['archivo_auxiliar'],eventos_auxiliar)
 
########################################
########################################

        solo_eventos = [fila[1] for fila in self.eventos]
        for i,evento_auxiliar in enumerate(eventos_auxiliar):
            evento=extraccion(evento_auxiliar,solo_eventos,self.archivo,False)
            if evento!=None:
                self.eventos.append(evento)
        self.eventos=ordenar_y_eliminar_duplicados(self.eventos,1,False)
        escritura_archivo(self.directorios['archivo_csv'],self.eventos)
        self.marcas_usuario.clear()
        self.cargar_componentes_fecha()
        self.desplegar_grafico()

    def graficar_caudales(self):
        if not self.caudales:
            QMessageBox.warning(self, "Sin datos", "No hay datos de caudales cargados.")
            return

        fechas = []
        valores = []

        fecha_inicio = self.selector_fecha_inicio.date().toPyDate()
        fecha_fin = self.selector_fecha_fin.date().toPyDate()


        for fila in self.caudales:
            try:
                if fila[2] != "1":
                    continue  # Ignora eventos con bandera diferente de 1

                fecha_evento = datetime.strptime(fila[0].replace(".sis", ""), "%Y%m%d_%H%M%S")

                # ✅ Nuevo filtro por rango de fechas
                if not (fecha_inicio <= fecha_evento.date() <= fecha_fin):
                    continue


                valor = int(fila[1])
                fechas.append(fecha_evento)
                valores.append(valor)
            except Exception as e:
                print(f"Error procesando fila de caudal: {fila}, {e}")

        if not fechas or not valores:
            QMessageBox.warning(self, "Sin datos válidos", "No se pudo generar la gráfica por datos inválidos.")
            return

        fig, ax = plt.subplots()
        ax.plot(fechas, valores, linestyle='-', color='blue', label='Caudales (s)')
        ax.set_title("Serie de Caudales")
        ax.set_xlabel("Fecha del Evento")
        ax.set_ylabel("Tiempo (s)")
        ax.grid(True)
        ax.legend()
        ax.set_ylim(bottom=0)
        fig.autofmt_xdate()
        plt.show()


    def cargar_eventos_control(self):
        # Paso 1: cargar caudales existentes
        archivo_csv = os.path.join(self.directorio_trabajo, "caudales.csv")
        if os.path.isfile(archivo_csv):
            try:
                self.caudales = lectura_archivo(archivo_csv)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo cargar caudales.csv: {str(e)}")
                return
        else:
            self.caudales = []

        caudales_dict = {fila[0]: fila for fila in self.caudales}

        fecha_ini = self.selector_fecha_inicio.date().toPyDate()
        fecha_fin = self.selector_fecha_fin.date().toPyDate()
        eventos_control = []
        eventos_control_nuevos = []
        fecha_actual = fecha_ini

        # Paso 2: buscar eventos CONTROL nuevos
        while fecha_actual <= fecha_fin:
            nombre_archivo = fecha_actual.strftime("%Y%m%d") + "000000"
            try:
                directorios_dia = obtener_directorios(os.path.join(self.directorio_trabajo, nombre_archivo))
                archivo_csv_eventos = os.path.join(self.directorio_trabajo, directorios_dia['archivo_csv'])
                if os.path.isfile(archivo_csv_eventos):
                    lista_eventos = lectura_archivo(archivo_csv_eventos)
                    for fila in lista_eventos:
                        if len(fila) > 2 and fila[2].strip().upper() == "CONTROL":
                            eventos_control.append(fila[1])
            except Exception as e:
                print(f"No se pudo procesar el día {fecha_actual}: {e}")
            fecha_actual += timedelta(days=1)

        eventos_control = sorted(set(eventos_control))
        evento_inicio = None

        for evento in eventos_control:
            if evento in caudales_dict:
                continue  # Ya está en el archivo

            try:
                dt_actual = datetime.strptime(evento.replace(".sis", ""), "%Y%m%d_%H%M%S")
                if evento_inicio:
                    dt_inicio = datetime.strptime(evento_inicio.replace(".sis", ""), "%Y%m%d_%H%M%S")
                    segundos = int((dt_actual - dt_inicio).total_seconds())
                else:
                    segundos = 0  # Este valor será recalculado luego

                nueva_fila = [evento, str(segundos), "1"]
                eventos_control_nuevos.append(nueva_fila)
                evento_inicio = evento
            except Exception as e:
                print(f"Error procesando evento {evento}: {e}")

        self.caudales.extend(eventos_control_nuevos)

        # ✅ Recalcular todos los caudales
        self.recalcular_caudales()

        # Paso 3: Guardado automático
        try:
            escritura_archivo(archivo_csv, self.caudales)
            QMessageBox.information(
                self,
                "Carga y guardado exitoso",
                f"Se agregaron {len(eventos_control_nuevos)} nuevos eventos y se guardaron en caudales.csv."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar caudales: {str(e)}")



    def closeEvent(self, event):
        try:
            ruta_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
            escritura_archivo(ruta_caudales, self.caudales)
            print("[INFO] caudales.csv guardado correctamente.")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar caudales.csv al cerrar: {e}")
        event.accept()  # Cierra la ventana normalmente




if __name__ == '__main__': #Condicional que comprueba si ha sido ejecutado o importado
    app = QtWidgets.QApplication(sys.argv)#Creamos app y le pasamos una lista de argumentos vacíos
    #Borramos todo el resto del código y ahora vamos a instanciar nuestra clase MainWindow:
    window = Caudales()
    window.show()#Muestra la ventana:
    app.exec_() #Usamos app.exec_() para crear el bucle de ejecución

