import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QVBoxLayout, QMessageBox
)
from obspy import read


class VentanaPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cambiar letra final de canales a X, Y, Z")
        self.setGeometry(100, 100, 350, 120)

        self.boton_abrir = QPushButton("Seleccionar archivo .mseed", self)
        self.boton_salir = QPushButton("Salir", self)

        self.boton_abrir.clicked.connect(self.seleccionar_archivo)
        self.boton_salir.clicked.connect(self.cerrar_aplicacion)

        layout = QVBoxLayout()
        layout.addWidget(self.boton_abrir)
        layout.addWidget(self.boton_salir)

        self.setLayout(layout)

    def seleccionar_archivo(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo MiniSEED", "", "MiniSEED Files (*.mseed);;Todos los archivos (*)"
        )
        if ruta_archivo:
            try:
                self.modificar_canales(ruta_archivo)
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Canales modificados correctamente y archivo sobrescrito:\n{ruta_archivo}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo modificar el archivo:\n{str(e)}")

    def modificar_canales(self, ruta_archivo):


        stream = read(ruta_archivo)
        print(stream)
        sufijos_nuevos = ["X", "Y", "Z"]
        for i, traza in enumerate(stream):
            canal_original = traza.stats.channel
            if len(canal_original) != 3:
                raise ValueError(f"El canal '{canal_original}' no tiene 3 letras.")
            prefijo = canal_original[:2]
            nuevo_canal = prefijo + sufijos_nuevos[i % 3]
            traza.stats.channel = nuevo_canal
        print(stream)
        stream.write(ruta_archivo, format="MSEED")  # Sobrescribe el archivo original

    def cerrar_aplicacion(self):
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())


