import sys
import numpy as np
from obspy import read
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class VentanaPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor de Archivos EVT - Kinemetrics")
        self.setGeometry(100, 100, 800, 600)

        # Layout
        layout = QVBoxLayout()

        # Botón para cargar archivo
        self.boton_cargar = QPushButton("Cargar archivo EVT")
        self.boton_cargar.clicked.connect(self.cargar_evt)
        layout.addWidget(self.boton_cargar)

        # Área de texto para mostrar metadatos
        self.texto_info = QTextEdit()
        self.texto_info.setReadOnly(True)
        layout.addWidget(self.texto_info)

        # Botón para salir
        self.boton_salir = QPushButton("Salir")
        self.boton_salir.clicked.connect(self.cerrar_aplicacion)
        layout.addWidget(self.boton_salir)

        # Área para gráfica
        self.figura = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figura)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def cargar_evt(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(self, "Selecciona un archivo EVT", "", "Archivos EVT (*.evt)")
        if not ruta_archivo:
            return

        try:
            st = read(ruta_archivo)
            tr = st[0]
            datos = tr.data

            tipo_dato = datos.dtype
            max_valor = np.max(np.abs(datos))

            info = f"📄 Archivo: {ruta_archivo}\n"
            info += f"📊 Tipo de datos: {tipo_dato}\n"
            info += f"📈 Valor absoluto máximo: {max_valor}\n\n"
            info += "📋 Metadatos:\n"

            for clave, valor in tr.stats.items():
                if isinstance(valor, dict):
                    info += f"\n🔸 {clave}:\n"
                    for subclave, subvalor in valor.items():
                        info += f"    {subclave}: {subvalor}\n"
                else:
                    info += f"{clave}: {valor}\n"

            self.texto_info.setText(info)

            self.graficar_traza(tr)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo EVT:\n{e}")

    def graficar_traza(self, traza):
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        ax.plot(traza.times(), traza.data, color='black')
        ax.set_title("Señal sísmica")
        ax.set_xlabel("Tiempo [s]")
        ax.set_ylabel("Amplitud")
        ax.grid(True)
        self.canvas.draw()

    def cerrar_aplicacion(self):
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())
