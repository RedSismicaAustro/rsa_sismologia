import sys
import numpy as np
from obspy import read, UTCDateTime
from obspy.core import Stream
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QMessageBox, QTextEdit
)

def completar_inicio_a_medianoche(stream: Stream) -> Stream:
    st_completo = Stream()
    for tr in stream:
        inicio_dia = UTCDateTime(tr.stats.starttime.date)
        if tr.stats.starttime > inicio_dia:
            npts_faltantes = int((tr.stats.starttime - inicio_dia) * tr.stats.sampling_rate)
            datos_relleno = np.zeros(npts_faltantes, dtype=tr.data.dtype)
            tr_relleno = tr.copy()
            tr_relleno.stats.starttime = inicio_dia
            tr_relleno.data = datos_relleno
            st_completo += tr_relleno
        st_completo += tr
    return st_completo.merge(method=1)

def cambiar_nombres_a_xyz(stream: Stream) -> Stream:
    nuevo_stream = Stream()
    n = len(stream)

    # Asignación condicional según el número de trazas
    if n == 1:
        letras_xyz = ['Z']
    else:
        letras_xyz = ['X', 'Y', 'Z'] * ((n + 2) // 3)

    for i, tr in enumerate(stream):
        nuevo_tr = tr.copy()
        if len(nuevo_tr.stats.channel) == 3:
            nuevo_tr.stats.channel = nuevo_tr.stats.channel[:2] + letras_xyz[i]
        nuevo_stream += nuevo_tr

    return nuevo_stream


def describir_stats_completos(stream: Stream, titulo: str) -> str:
    descripcion = [f"{titulo}"]
    for i, tr in enumerate(stream):
        descripcion.append(f"\nTrace {i+1}:")
        for k, v in sorted(tr.stats.items()):
            descripcion.append(f"  {k}: {v}")
    return "\n".join(descripcion)

class LectorMseed(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lector y Modificador de MiniSEED")
        self.resize(800, 600)
        self.layout = QVBoxLayout()

        self.boton_cargar = QPushButton("Cargar MiniSEED")
        self.boton_cargar.clicked.connect(self.leer_y_modificar_mseed)
        self.layout.addWidget(self.boton_cargar)

        self.texto_info = QTextEdit()
        self.texto_info.setReadOnly(True)
        self.layout.addWidget(self.texto_info)

        self.boton_salir = QPushButton("Salir")
        self.boton_salir.clicked.connect(self.close)
        self.layout.addWidget(self.boton_salir)

        self.setLayout(self.layout)

    def leer_y_modificar_mseed(self):
        archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo MiniSEED", "", "MiniSEED (*.mseed)")
        if not archivo:
            return

        try:
            st_original = read(archivo)
            descripcion_antes = describir_stats_completos(st_original, "🟡 ANTES DE MODIFICAR")

            st_modificado = completar_inicio_a_medianoche(st_original)
            st_modificado = cambiar_nombres_a_xyz(st_modificado)
            descripcion_despues = describir_stats_completos(st_modificado, "🟢 DESPUÉS DE MODIFICAR")

            st_modificado.write(archivo, format="MSEED")  # Sobrescribe archivo original

            self.texto_info.setPlainText(f"{descripcion_antes}\n\n{descripcion_despues}")
            QMessageBox.information(self, "Éxito", "Archivo modificado y guardado exitosamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo procesar el archivo:\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = LectorMseed()
    ventana.show()
    sys.exit(app.exec_())
