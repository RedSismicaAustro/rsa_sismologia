import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from obspy import read, UTCDateTime
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QPushButton, QTextEdit


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Visualizador de Archivos MiniSEED')
        self.setGeometry(100, 100, 800, 600)

        self.ruta_archivo = None
        self.st = None  # Archivo MiniSEED cargado

        # Botón para seleccionar archivo
        self.boton_seleccionar = QPushButton('Seleccionar archivo', self)
        self.boton_seleccionar.setGeometry(10, 10, 200, 30)
        self.boton_seleccionar.clicked.connect(self.seleccionar_archivo)

        # Botón para corregir el archivo
        self.boton_corregir = QPushButton('Corregir Archivo', self)
        self.boton_corregir.setGeometry(10, 50, 200, 30)
        self.boton_corregir.clicked.connect(self.corregir_archivo)

        # Botón para graficar
        self.boton_graficar = QPushButton('Graficar', self)
        self.boton_graficar.setGeometry(10, 90, 200, 30)
        self.boton_graficar.clicked.connect(self.graficar_archivo)

        # Botón para salir
        self.boton_salir = QPushButton('Salir', self)
        self.boton_salir.setGeometry(10, 130, 200, 30)
        self.boton_salir.clicked.connect(self.salir)

        # Cuadro de texto para mostrar información
        self.texto_stats = QTextEdit(self)
        self.texto_stats.setGeometry(10, 170, 780, 150)
        self.texto_stats.setReadOnly(True)

    def seleccionar_archivo(self):
        """Abre un cuadro de diálogo para seleccionar un archivo MiniSEED."""
        opciones = QFileDialog.Options()
        ruta_archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo MiniSEED", "", "Archivos MiniSEED (*.mseed)", options=opciones)
        
        if ruta_archivo:
            self.ruta_archivo = ruta_archivo

            self.st = read(self.ruta_archivo)
            self.actualizar_info_archivo()

    def actualizar_info_archivo(self):
        """Muestra los metadatos actualizados del archivo MiniSEED."""
        if not self.st:
            return
        
        stats = self.st[0].stats

        starttime = stats.starttime
        endtime = stats.endtime
        fecha_inicio = UTCDateTime(starttime.date)  # 00:00:00 del día
        fecha_fin = fecha_inicio + 86400 - 1  # 23:59:59 del mismo día

        mensaje = f"""Network: {stats.network}
Station: {stats.station}
Location: {stats.location}
Channel: {stats.channel}
Starttime: {starttime}
Endtime: {endtime}
Sampling Rate: {stats.sampling_rate}
Npts: {stats.npts}
Factor de calibración: {stats.calib}
"""
        print(stats)
        if starttime != fecha_inicio or endtime != fecha_fin:
            mensaje += "\n⚠️ El archivo NO cubre un día completo. Se recomienda corregirlo."

        self.texto_stats.setText(mensaje)

    def corregir_archivo(self):
        """Corrige el inicio y fin del archivo MiniSEED y lo guarda con un nuevo nombre."""
        if not self.st:
            QMessageBox.warning(self, 'Advertencia', 'No se ha cargado ningún archivo MiniSEED.')
            return

        self.st = self.ajustar_inicio_fin_trazas(self.st)
        nuevo_nombre = self.generar_nombre_archivo()
        nueva_ruta = os.path.join(os.path.dirname(self.ruta_archivo), nuevo_nombre)

        self.st.write(nueva_ruta, format="MSEED")  # Guardar el archivo corregido
        self.ruta_archivo = nueva_ruta  # Actualizar la ruta del archivo corregido

        QMessageBox.information(self, 'Corrección realizada', f'Archivo corregido y guardado como:\n{nuevo_nombre}')
        self.actualizar_info_archivo()  # Refrescar la información en la ventana

    def ajustar_inicio_fin_trazas(self, st):
        """Ajusta el inicio y fin de las trazas para que cubran un día completo."""
        for tr in st:
            starttime = tr.stats.starttime
            endtime = tr.stats.endtime
            fecha_inicio = UTCDateTime(starttime.date)  # 00:00:00
            fecha_fin = fecha_inicio + 86400 - 1  # 23:59:59

            # Rellenar el inicio si es necesario
            if starttime > fecha_inicio:
                tasa_muestreo = tr.stats.sampling_rate
                muestras_faltantes = int((starttime - fecha_inicio) * tasa_muestreo)
                tr.data = np.concatenate((np.zeros(muestras_faltantes, dtype=tr.data.dtype), tr.data))
                tr.stats.starttime = fecha_inicio
                tr.stats.npts = len(tr.data)

            # Rellenar el final si es necesario
            if endtime < fecha_fin:
                tasa_muestreo = tr.stats.sampling_rate
                muestras_faltantes = int((fecha_fin - endtime) * tasa_muestreo)
                tr.data = np.concatenate((tr.data, np.zeros(muestras_faltantes, dtype=tr.data.dtype)))
                tr.stats.npts = len(tr.data)

        return st

    def generar_nombre_archivo(self):
        """Genera un nombre de archivo en formato 'EEEE_AAAAMMDD_hhmmss.mseed'."""
        if not self.st:
            return "archivo_corregido.mseed"

        tr = self.st[0]
        estacion = tr.stats.station
        fecha = tr.stats.starttime.strftime("%Y%m%d_%H%M%S")
        return f"{estacion}_{fecha}.mseed"

    def graficar_archivo(self):
        """Grafica el archivo MiniSEED."""
        if not self.st:
            QMessageBox.warning(self, 'Advertencia', 'No se ha seleccionado ningún archivo MiniSEED.')
            return
        self.graficar_con_matplotlib(self.st)

    def graficar_con_matplotlib(self, st):
        """Genera gráficos con Matplotlib para 1 o más componentes."""
        fig, axs = plt.subplots(nrows=len(st), ncols=1, figsize=(10, 5 * len(st)), sharex=True)

        if len(st) == 1:
            axs = [axs]  # Convertimos axs en una lista para unificar el acceso

        for i, tr in enumerate(st):
            data = tr.data
            tiempos = [tr.stats.starttime + t for t in tr.times()]
            tiempos_formateados = [t.datetime for t in tiempos]

            axs[i].plot(tiempos_formateados, data, 'k')
            axs[i].set_ylabel('Amplitud')
            axs[i].set_title(f'Componente {tr.stats.channel}')
            axs[i].grid(True)

        axs[-1].set_xlabel('Hora (HH:MM:SS)')
        axs[-1].xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        plt.tight_layout()
        plt.show()

    def salir(self):
        """Cierra la aplicación."""
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())


