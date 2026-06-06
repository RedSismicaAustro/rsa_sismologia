
import json

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

        # Guardamos el directorio realmente escaneado
        self.directorio_escaneado = ruta

        def construir_estructura_arbol(ruta_raiz: Path):
            lineas = []
            raiz_json = {
                "nombre": ruta_raiz.name,
                "tipo": "directorio",
                "contenido": []
            }

            lineas.append(f"{ruta_raiz.resolve()}/")
            lineas.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lineas.append("")

            def listar_entradas(directorio: Path):
                try:
                    with os.scandir(directorio) as it:
                        entradas = []
                        for e in it:
                            try:
                                if e.is_dir(follow_symlinks=False) or e.is_file(follow_symlinks=False):
                                    entradas.append(e)
                            except Exception:
                                continue
                    entradas.sort(key=lambda x: x.name.lower())
                    return entradas, None
                except Exception as e:
                    return [], e

            entradas_raiz, err = listar_entradas(ruta_raiz)
            if err is not None:
                lineas.append(f"└── [Error: {err}]")
                return "\n".join(lineas), raiz_json

            # Frame: (directorio, prefijo, nodo_json, entradas, indice)
            pila = [(ruta_raiz, "", raiz_json, entradas_raiz, 0)]

            while pila:
                directorio_actual, prefijo, nodo_json, entradas, i = pila.pop()

                if i >= len(entradas):
                    continue

                entrada = entradas[i]
                es_ultimo = (i == len(entradas) - 1)
                ramal = "└── " if es_ultimo else "├── "
                ruta_entrada = Path(entrada.path)

                # Re-apilamos el estado actual para continuar luego
                pila.append((directorio_actual, prefijo, nodo_json, entradas, i + 1))

                if entrada.is_dir(follow_symlinks=False):
                    lineas.append(f"{prefijo}{ramal}{entrada.name}/")

                    nodo_dir = {
                        "nombre": entrada.name,
                        "tipo": "directorio",
                        "contenido": []
                    }
                    nodo_json["contenido"].append(nodo_dir)

                    prefijo_hijo = prefijo + ("    " if es_ultimo else "│   ")
                    entradas_hijo, err_hijo = listar_entradas(ruta_entrada)

                    if err_hijo is not None:
                        lineas.append(f"{prefijo_hijo}└── [Error: {err_hijo}]")
                    else:
                        pila.append((ruta_entrada, prefijo_hijo, nodo_dir, entradas_hijo, 0))

                else:
                    try:
                        st = ruta_entrada.stat()
                        creado = datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                        modificado = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        creado = modificado = None

                    lineas.append(
                        f"{prefijo}{ramal}{entrada.name} "
                        f"(creado: {creado}, modificado: {modificado})"
                    )

                    nodo_json["contenido"].append({
                        "nombre": entrada.name,
                        "tipo": "archivo",
                        "creado": creado,
                        "modificado": modificado
                    })

            return "\n".join(lineas), raiz_json

        texto, self.estructura_json = construir_estructura_arbol(ruta)
        self.salida.setPlainText(texto)


    def guardar_txt(self):
        contenido = self.salida.toPlainText()

        if not contenido.strip():
            QMessageBox.information(self, "Sin contenido", "No hay texto para guardar. Escanea primero.")
            return

        if not hasattr(self, "directorio_escaneado"):
            QMessageBox.warning(self, "Sin escaneo", "No hay un directorio escaneado.")
            return

        directorio = self.directorio_escaneado
        nombre_base = directorio.name
        ruta_sugerida = str(directorio / f"{nombre_base}.txt")

        nombre, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar estructura como...",
            ruta_sugerida,
            "Archivo de texto (*.txt)"
        )

        if not nombre:
            return

        try:
            with open(nombre, "w", encoding="utf-8", newline="\n") as f:
                f.write(contenido)

            ruta_json = os.path.splitext(nombre)[0] + ".json"
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(self.estructura_json, f, indent=2, ensure_ascii=False)

            QMessageBox.information(
                self,
                "Guardado",
                f"Se guardaron:\n{nombre}\n{ruta_json}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al guardar",
                f"No se pudo guardar el archivo:\n{e}"
            )





def main():
    app = QApplication(sys.argv)
    v = VentanaPrincipal()
    v.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
