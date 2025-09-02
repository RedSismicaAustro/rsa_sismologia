# -*- coding: utf-8 -*-
"""
Estructura de directorios → Texto (simple, sin hilos, PyQt5)
Requisitos: pip install PyQt5
"""

import sys, os
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QPlainTextEdit, QMessageBox
)

class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Estructura de directorios → TXT (simple)")
        self.resize(900, 650)

        # ---- UI básica ----
        contenedor = QWidget(self)
        layout = QVBoxLayout(contenedor)

        fila_ruta = QHBoxLayout()
        fila_ruta.addWidget(QLabel("Directorio inicial:"))
        self.edt_ruta = QLineEdit()
        # Por tu contexto suelo usar C:\DIA; si no existe, dejo el HOME
        ruta_defecto = Path(r"C:\DIA")
        self.edt_ruta.setText(str(ruta_defecto if ruta_defecto.exists() else Path.home()))
        btn_examinar = QPushButton("Examinar…")
        btn_examinar.clicked.connect(self.examinar_directorio)
        fila_ruta.addWidget(self.edt_ruta, 1)
        fila_ruta.addWidget(btn_examinar)

        fila_botones = QHBoxLayout()
        btn_escanear = QPushButton("Escanear")
        btn_escanear.clicked.connect(self.escanear)
        btn_guardar = QPushButton("Guardar TXT…")
        btn_guardar.clicked.connect(self.guardar_txt)
        fila_botones.addWidget(btn_escanear)
        fila_botones.addStretch()
        fila_botones.addWidget(btn_guardar)

        self.salida = QPlainTextEdit()
        self.salida.setReadOnly(True)
        self.salida.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.salida.setPlaceholderText("Aquí se mostrará la estructura del directorio en formato de árbol…")

        layout.addLayout(fila_ruta)
        layout.addLayout(fila_botones)
        layout.addWidget(self.salida, 1)
        self.setCentralWidget(contenedor)

    def examinar_directorio(self):
        ruta = QFileDialog.getExistingDirectory(self, "Selecciona el directorio inicial", self.edt_ruta.text())
        if ruta:
            self.edt_ruta.setText(ruta)

    def escanear(self):
        ruta_texto = self.edt_ruta.text().strip()
        ruta = Path(ruta_texto)
        if not ruta.exists() or not ruta.is_dir():
            QMessageBox.critical(self, "Ruta inválida", "La ruta no existe o no es un directorio.")
            return

        # ÚNICA FUNCIÓN LARGA: recorre todo y construye el árbol
        def construir_estructura_arbol(ruta_raiz: Path) -> str:
            """
            Recorre el árbol de directorios desde ruta_raiz y devuelve un texto
            con formato de árbol usando ├──, └── y │. Maneja excepciones de permisos
            sin detener el proceso, y evita seguir enlaces simbólicos para no crear bucles.
            """
            lineas = []
            encabezado = f"{ruta_raiz.resolve()}/"
            lineas.append(encabezado)
            lineas.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lineas.append("")

            # Usaremos una pila para recorrido en profundidad (iterativo),
            # almacenando (path, prefijo, listado_hecho).
            # listado_hecho= False -> aún no listamos hijos; True -> ya listados.
            pila = [(ruta_raiz, "", False)]

            while pila:
                ruta_actual, prefijo, listado_hecho = pila.pop()

                # Listar contenido del directorio actual una única vez
                if not listado_hecho:
                    try:
                        dirs, files = [], []
                        with os.scandir(ruta_actual) as it:
                            for entrada in it:
                                # ignoramos enlaces simbólicos para evitar ciclos
                                try:
                                    if entrada.is_dir(follow_symlinks=False):
                                        dirs.append(entrada)
                                    else:
                                        files.append(entrada)
                                except Exception:
                                    # Si no podemos determinar el tipo, lo omitimos
                                    continue
                        # orden alfabético, insensible a mayúsculas
                        clave = lambda e: e.name.lower()
                        dirs.sort(key=clave)
                        files.sort(key=clave)

                        # Para dibujar bien los ramales, procesamos en orden natural
                        hijos = [(True, d) for d in dirs] + [(False, f) for f in files]

                        # Empujamos un marcador para no volver a listar esta carpeta
                        # (no vamos a imprimir la carpeta actual aquí; la impresión
                        # se hace al subir el item desde el padre).
                        # En la raíz sí queremos listar sus hijos directamente.
                        # Insertamos hijos en la pila en orden inverso para que salgan en orden.
                        for i in range(len(hijos) - 1, -1, -1):
                            es_dir, entrada = hijos[i]
                            es_ultimo = (i == len(hijos) - 1)
                            ramal = "└── " if es_ultimo else "├── "
                            if es_dir:
                                lineas.append(f"{prefijo}{ramal}{entrada.name}/")
                                prefijo_hijo = prefijo + ("    " if es_ultimo else "│   ")
                                pila.append((Path(entrada.path), prefijo_hijo, False))
                            else:
                                lineas.append(f"{prefijo}{ramal}{entrada.name}")
                    except PermissionError:
                        lineas.append(f"{prefijo}└── [Permiso denegado]")
                    except FileNotFoundError:
                        lineas.append(f"{prefijo}└── [No encontrado]")
                    except OSError as e:
                        lineas.append(f"{prefijo}└── [Error: {e}]")

            return "\n".join(lineas)

        texto = construir_estructura_arbol(ruta)
        self.salida.setPlainText(texto)

    def guardar_txt(self):
        contenido = self.salida.toPlainText()
        if not contenido.strip():
            QMessageBox.information(self, "Sin contenido", "No hay texto para guardar. Escanea primero.")
            return
        nombre, _ = QFileDialog.getSaveFileName(
            self, "Guardar estructura como...", f"estructura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Archivo de texto (*.txt)"
        )
        if not nombre:
            return
        try:
            with open(nombre, "w", encoding="utf-8", newline="\n") as f:
                f.write(contenido)
            QMessageBox.information(self, "Guardado", f"Se guardó:\n{nombre}")
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar el archivo:\n{e}")

def main():
    app = QApplication(sys.argv)
    v = VentanaPrincipal()
    v.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
