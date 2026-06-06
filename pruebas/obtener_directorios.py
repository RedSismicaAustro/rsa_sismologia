import sys
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QLabel
)
from treelib import Tree


CONFIG_FILE = "config.json"


class GeneradorReporte(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generador de Reporte de Estructura")
        self.setGeometry(100, 100, 500, 250)

        self.directorio_analizar = None
        self.carpeta_destino = None

        self.cargar_configuracion()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label_directorio = QLabel(f"📂 Directorio a analizar: {self.directorio_analizar or 'No seleccionado'}")
        self.label_salida = QLabel(f"💾 Carpeta de destino: {self.carpeta_destino or 'No seleccionada'}")

        btn_seleccionar_directorio = QPushButton("Seleccionar directorio a analizar")
        btn_seleccionar_directorio.clicked.connect(self.seleccionar_directorio)

        btn_seleccionar_destino = QPushButton("Seleccionar carpeta de destino del reporte")
        btn_seleccionar_destino.clicked.connect(self.seleccionar_carpeta_destino)

        btn_generar = QPushButton("Generar reporte")
        btn_generar.clicked.connect(self.generar_reporte)

        btn_salir = QPushButton("Salir")
        btn_salir.clicked.connect(self.close)

        layout.addWidget(self.label_directorio)
        layout.addWidget(btn_seleccionar_directorio)
        layout.addWidget(self.label_salida)
        layout.addWidget(btn_seleccionar_destino)
        layout.addWidget(btn_generar)
        layout.addWidget(btn_salir)

        self.setLayout(layout)

    def cargar_configuracion(self):
        if Path(CONFIG_FILE).exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.directorio_analizar = Path(config.get("ultima_fuente")) if config.get("ultima_fuente") else None
                    self.carpeta_destino = Path(config.get("ultimo_destino")) if config.get("ultimo_destino") else None
                    print("[INFO] Configuración cargada desde config.json")
            except Exception as e:
                print(f"[WARN] No se pudo cargar configuración previa: {e}")

    def guardar_configuracion(self):
        config = {
            "ultima_fuente": str(self.directorio_analizar) if self.directorio_analizar else "",
            "ultimo_destino": str(self.carpeta_destino) if self.carpeta_destino else ""
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print("[INFO] Configuración guardada.")
        except Exception as e:
            print(f"[WARN] No se pudo guardar configuración: {e}")

    def seleccionar_directorio(self):
        ruta = QFileDialog.getExistingDirectory(self, "Seleccionar directorio a analizar")
        if ruta:
            self.directorio_analizar = Path(ruta)
            self.label_directorio.setText(f"📂 Directorio a analizar: {self.directorio_analizar}")
            print(f"[INFO] Directorio seleccionado: {self.directorio_analizar}")
            self.guardar_configuracion()

    def seleccionar_carpeta_destino(self):
        ruta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para guardar el reporte")
        if ruta:
            self.carpeta_destino = Path(ruta)
            self.label_salida.setText(f"💾 Carpeta de destino: {self.carpeta_destino}")
            print(f"[INFO] Carpeta destino: {self.carpeta_destino}")
            self.guardar_configuracion()

    def generar_reporte(self):
        if not self.directorio_analizar or not self.carpeta_destino:
            QMessageBox.warning(self, "Faltan datos", "Debe seleccionar ambas rutas antes de generar el reporte.")
            return

        nombre_directorio = self.directorio_analizar.name
        archivo_txt = self.carpeta_destino / f"reporte_estructura_{nombre_directorio}.txt"
        archivo_json = self.carpeta_destino / f"estructura_{nombre_directorio}.json"

        print(f"[INFO] Generando archivos:")
        print(f"   ↳ TXT: {archivo_txt}")
        print(f"   ↳ JSON: {archivo_json}")

        try:
            arbol = Tree()
            estructura = {}

            arbol.create_node(tag=self.directorio_analizar.name, identifier=str(self.directorio_analizar))
            estructura[self.directorio_analizar.name] = {}

            def agregar_nodos(directorio, id_padre, diccionario_actual):
                for elemento in sorted(directorio.iterdir()):
                    id_nodo = str(elemento)
                    arbol.create_node(tag=elemento.name, identifier=id_nodo, parent=id_padre)

                    if elemento.is_dir():
                        diccionario_actual[elemento.name] = {}
                        agregar_nodos(elemento, id_nodo, diccionario_actual[elemento.name])
                    else:
                        diccionario_actual[elemento.name] = None  # Es un archivo

            agregar_nodos(
                self.directorio_analizar,
                str(self.directorio_analizar),
                estructura[self.directorio_analizar.name]
            )

            # Guardar estructura visual en TXT
            with open(archivo_txt, "w", encoding="utf-8") as f:
                f.write(str(arbol))

            print("[INFO] Árbol guardado en .txt")

            # Guardar estructura jerárquica en JSON
            with open(archivo_json, "w", encoding="utf-8") as f_json:
                json.dump(estructura, f_json, indent=4, ensure_ascii=False)

            print("[INFO] Estructura guardada en .json")

            QMessageBox.information(
                self, "Reportes generados",
                f"✅ Reportes guardados en:\n{archivo_txt.name}\n{archivo_json.name}"
            )

        except Exception as e:
            print(f"[ERROR] {e}")
            QMessageBox.critical(self, "Error", f"Ocurrió un error:\n{e}")


# Ejecutar
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = GeneradorReporte()
    ventana.show()
    sys.exit(app.exec_())
