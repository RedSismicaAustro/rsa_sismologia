import sys, os
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

from datetime import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QPlainTextEdit, QMessageBox
)

from metodos_rsa import lectura_archivo,copiar_archivos
from metodos_gestion import obtener_directorios
import xml.etree.ElementTree as ET
import shutil
from datetime import timedelta

class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Búsqueda de SISMOS y extracción de P y S")
        self.resize(900, 650)

        # ----- Estado interno -----
        self.ruta_archivo_origen: Path | None = None
        self.directorio_destino: Path | None = None

        # ---- UI básica ----
        contenedor = QWidget(self)
        layout = QVBoxLayout(contenedor)

        fila_ruta = QHBoxLayout()
        fila_ruta.addWidget(QLabel("Directorio inicial:"))
        self.edt_ruta = QLineEdit()
        # Por tu contexto sueles usar C:\DIA; si no existe, dejo el HOME
        ruta_defecto = Path(r"C:\DIA")
        self.edt_ruta.setText(str(ruta_defecto if ruta_defecto.exists() else Path.home()))
        btn_examinar = QPushButton("Cargar…")
        btn_examinar.clicked.connect(self.cargar_archivo)
        fila_ruta.addWidget(self.edt_ruta, 1)
        fila_ruta.addWidget(btn_examinar)

        fila_botones = QHBoxLayout()
        btn_escanear = QPushButton("Procesar")
        btn_escanear.clicked.connect(self.procesar)
        btn_guardar = QPushButton("Destino…")
        btn_guardar.clicked.connect(self.definir_destino)
        fila_botones.addWidget(btn_escanear)
        fila_botones.addStretch()
        fila_botones.addWidget(btn_guardar)

        self.salida = QPlainTextEdit()
        self.salida.setReadOnly(True)
        self.salida.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.salida.setPlaceholderText("Aquí se mostrarán los resultados")
        self._actualizar_encabezado_salida()

        layout.addLayout(fila_ruta)
        layout.addLayout(fila_botones)
        layout.addWidget(self.salida, 1)
        self.setCentralWidget(contenedor)

    # ---------------- LÓGICA ----------------

    def cargar_archivo(self):
        """
        Abre un diálogo para seleccionar únicamente archivos que terminen en '_cat.csv'.
        Actualiza el encabezado en el panel de salida.
        """
        directorio_inicial = Path(self.edt_ruta.text()).expanduser()
        if not directorio_inicial.exists():
            directorio_inicial = Path.home()

        # Filtro: solo *_cat.csv (y permite ver CSV por si acaso).
        filtros = "Catálogos (*.csv);;Solo _cat (*.csv)"
        # Nota: Usamos el patrón con comodín en el caption (Qt lo aplica en la UI),
        # y filtramos de nuevo por sufijo exacto para garantizar *_cat.csv.
        ruta_str, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona un archivo *_cat.csv",
            str(directorio_inicial),
            "CSV de catálogo (*_cat.csv);;CSV (*.csv);;Todos (*.*)"
        )

        if not ruta_str:
            return  # usuario canceló

        ruta_sel = Path(ruta_str)
        # Verificación estricta: termina en '_cat.csv'
        if not (ruta_sel.suffix.lower() == ".csv" and ruta_sel.name.endswith("_cat.csv")):
            QMessageBox.warning(
                self, "Archivo no válido",
                "Debe seleccionar un archivo que termine en '_cat.csv'."
            )
            return

        self.ruta_archivo_origen = ruta_sel
        # Ajusta el campo de directorio inicial para próximas aperturas
        self.edt_ruta.setText(str(ruta_sel.parent))
        self._actualizar_encabezado_salida()

        # --- Leer archivo origen en variable self.catalogo ---
        self.catalogo = lectura_archivo(self.ruta_archivo_origen)
        # Generar nueva variable con los valores de la columna 18 (índice 17) filtrados por 'RSA'
        self.sismos = [fila[18] for fila in self.catalogo if len(fila) > 18 and 'RSA' in fila[17]]
        # Guardar la cantidad en self.numero_sismos
        self.numero_sismos = len(self.sismos)
        self._actualizar_encabezado_salida()
        self.directorio_trabajo = extraer_hasta_directorio(str(self.ruta_archivo_origen), "DIA")
        nombre_sin_cat = self.ruta_archivo_origen.stem.replace("_cat", "")
        ruta_xml = self.ruta_archivo_origen.with_name(nombre_sin_cat + ".xml")

        # Parsear y guardar en self.archivo_xml
        self.archivo_xml = ET.parse(ruta_xml).getroot()

        


    def obtener_evento_por_sis(self, nombre_sis: str):
        """
        Busca en self.archivo_xml el <Evento> cuyo <ruta> coincida con nombre_sis (ej: '20250825_041601.sis').
        Devuelve un dict con:
        - metadatos del evento (id_evento, anio, mes, etc.)
          - 'estaciones': lista de dicts con la info de cada <estacion>.
      Retorna None si no se encuentra.
        """

        if not hasattr(self, "archivo_xml") or self.archivo_xml is None:
            QMessageBox.warning(self, "XML no cargado", "No se ha cargado el archivo XML en self.archivo_xml.")
            return None

        raiz = self.archivo_xml  # Element raíz

        evento = None
        for nodo_evento in raiz.findall(".//Evento"):
            ruta_txt = (nodo_evento.findtext("ruta") or "").strip()
            if Path(ruta_txt).name == nombre_sis:
                evento = nodo_evento
                break

        if evento is None:
            return None

        def txt(tag):
            v = evento.findtext(tag)
            return v.strip() if v is not None else None

        # --- Metadatos del evento ---
        info = {
            "ruta": txt("ruta"),
            "id_evento": txt("id_evento"),
            "anio": txt("anio"),
            "mes": txt("mes"),
            "dia": txt("dia"),
            "hora": txt("hora"),
            "minuto": txt("minuto"),
            "segundo": txt("segundo"),
            "latitud": txt("latitud"),
            "longitud": txt("longitud"),
            "profundidad": txt("profundidad"),
            "rms": txt("rms"),
            "e_x": txt("e_x"),
            "e_y": txt("e_y"),
            "e_0": txt("e_0"),
            "e_z": txt("e_z"),
            "magnitud": txt("magnitud"),
            "tipo_magnitud": txt("tipo_magnitud"),
            "fuente": txt("fuente"),
            "ubicacion": txt("ubicacion"),
        }

        # --- Estaciones ---
        estaciones = []
        nodo_estaciones = evento.find("estaciones")
        if nodo_estaciones is not None:
            for nodo_est in nodo_estaciones.findall("estacion"):
                est = {}
                for hijo in list(nodo_est):
                    etiqueta = hijo.tag
                    valor = hijo.text.strip() if hijo.text else ""
                    est[etiqueta] = valor
                estaciones.append(est)

        info["estaciones"] = estaciones
        return info





    def definir_destino(self):
        """
        Abre un diálogo para seleccionar un directorio de destino.
        Actualiza el encabezado en el panel de salida.
        """
        directorio_inicial = Path(self.edt_ruta.text()).expanduser()
        if not directorio_inicial.exists():
            directorio_inicial = Path.home()

        ruta_dir = QFileDialog.getExistingDirectory(
            self,
            "Selecciona el directorio destino",
            str(directorio_inicial),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if not ruta_dir:
            return  # usuario canceló

        self.directorio_destino = Path(ruta_dir)
        self._actualizar_encabezado_salida()

    def procesar(self):
        """
        Aquí irá la lógica de procesamiento. Por ahora solo valida que
        existan origen y destino, y demuestra cómo agregar texto sin
        alterar el encabezado fijo.
        """
        if self.ruta_archivo_origen is None:
            QMessageBox.information(self, "Falta origen", "Seleccione primero el archivo *_cat.csv.")
            return
        if self.directorio_destino is None:
            QMessageBox.information(self, "Falta destino", "Seleccione primero el directorio destino.")
            return

        # --- Ejemplo de salida adicional sin tocar el encabezado ---
        self._append_resultado("Iniciando procesamiento de ejemplo…")
        self.lista_mseed_eventos=[]
        for sismo in self.sismos:
            self.archivo=os.path.join(self.directorio_trabajo,Path(sismo).stem.replace("_", ""))
            directorio=obtener_directorios(self.archivo)
            self._append_resultado("Procesando evento "+sismo)
            sufijo = str(directorio["sufijo_mseed"]).strip()
            vector_mseed = sorted(
                str(p) for p in Path(directorio["Directorio_eventos"]).glob("*.mseed")
                if p.name.endswith(sufijo)
            )
            self.lista_mseed_eventos.append(vector_mseed)

        archivo_csv=[]
        contador_fases=0
        for lista_dia in self.lista_mseed_eventos:
            for archivo_origen in lista_dia:
                nombre_archivo = Path(archivo_origen).name
                dt_evento = datetime.strptime(Path(nombre_archivo).stem.split("_", 1)[1], "%Y%m%d_%H%M%S")
                directorio_test=archivo_destino=os.path.join(self.directorio_destino,"test")
                directorio_wave=archivo_destino=os.path.join(self.directorio_destino,"waveforms")
                try:
                    path = Path(directorio_test)
                    path.mkdir(parents=True)
                except FileExistsError:
                    pass

                try:
                    path = Path(directorio_wave)
                    path.mkdir(parents=True)
                except FileExistsError:
                    pass
                archivo_destino=os.path.join(directorio_test,nombre_archivo)
                shutil.copyfile(archivo_origen,archivo_destino)
                estacion_objetivo = nombre_archivo[:4]  # primeros 4 caracteres = nombre de estación
                sismo_objetivo = f"{Path(sismo).stem}.sis"   # asegura AAAAMMDD_hhmmss.sis a partir de 'sismo'
                print(nombre_archivo)
                bandera=0
                info_evt = self.obtener_evento_por_sis(sismo_objetivo)
                if info_evt:
                    print("  Estación:",estacion_objetivo)
                    for est in info_evt["estaciones"]:
                        
                        if est.get("nombre") == estacion_objetivo:
                            filename=f"event_{contador_fases:04d}_P.mseed"
                            contador_fases=contador_fases+1
                            tiempo_p=float(est['p-sec'])

                            if tiempo_p > 60:
                                dt_evento_p=dt_evento+timedelta(minutes=1)
                                dt_evento_p=dt_evento.replace(second=tiempo_p-60)
                            else:
                                dt_evento_p=dt_evento.replace(second=tiempo_p)
                            aux=(filename,sismo_objetivo,'P',estacion_objetivo,dt_evento,dt_evento,dt_evento_p,'Frec','codigo_canal', est['p-sec'])
                            print(aux)
                            if est['marc.s'] != '':
                                filename=f"event_{contador_fases:04d}_S.mseed"
                                tiempo_s=float(est['marc.s'])
                                if tiempo_p > 60:
                                    dt_evento_s=dt_evento+timedelta(minutes=1)
                                    dt_evento_s=dt_evento.replace(second=tiempo_p-60)
                                else:
                                    dt_evento_s=dt_evento.replace(second=tiempo_s)
                                aux=(filename,sismo_objetivo,'S',estacion_objetivo,dt_evento,dt_evento,dt_evento_s,'Frec','codigo_canal', est['p-sec'])
                                print(aux)
                            if est['t_cod.']!='':
                                   tiempo_c=int(est['t_cod.'])
                            
                            bandera=1
                    if not bandera:
                        filename=f"noise_{contador_fases:04d}.mseed"
                        aux=(filename,sismo_objetivo,'N',estacion_objetivo,dt_evento,dt_evento,'NA','Frec','codigo_canal', 'NA')
            
            
        # Aquí podrás añadir tu lógica real y escribir resultados progresivos:
        # self._append_resultado("Leyendo catálogo…")
        # self._append_resultado("Generando archivos…")
        # self._append_resultado("Proceso finalizado.")

    # ---------------- UTILIDADES DE SALIDA ----------------

    def _actualizar_encabezado_salida(self):
        """
        Inserta/actualiza las tres primeras líneas fijas de la salida:
        1) Origen: <archivo _cat.csv>
        2) Destino: <directorio>
        3) Eventos: <cantidad>
        Manteniendo cualquier contenido adicional por debajo.
        """
        texto_actual = self.salida.toPlainText()
        lineas = texto_actual.splitlines()

        # Identificar si ya existía un encabezado (Origen/Destino/Eventos)
        resto = []
        if len(lineas) >= 3 and lineas[0].startswith("Origen:") and lineas[1].startswith("Destino:") and lineas[2].startswith("Eventos:"):
            resto = lineas[3:]
        elif len(lineas) >= 2 and lineas[0].startswith("Origen:") and lineas[1].startswith("Destino:"):
            resto = lineas[2:]
        else:
            resto = lineas

        origen_str = str(self.ruta_archivo_origen) if self.ruta_archivo_origen else "(sin seleccionar)"
        destino_str = str(self.directorio_destino) if self.directorio_destino else "(sin seleccionar)"
        eventos_str = str(self.numero_sismos) if hasattr(self, 'numero_sismos') else "(sin calcular)"

        encabezado = [f"Origen: {origen_str}", f"Destino: {destino_str}", f"Eventos: {eventos_str}", ""]
        nuevo_texto = "\n".join(encabezado + resto)
        self.salida.setPlainText(nuevo_texto)
        self.salida.moveCursor(self.salida.textCursor().End)
        # Coloca el cursor al final para que nuevas adiciones vayan abajo
        self.salida.moveCursor(self.salida.textCursor().End)

    def _append_resultado(self, mensaje: str):
        """
        Agrega texto debajo del encabezado fijo (sin reescribirlo).
        """
        # Obtenemos el texto actual y añadimos el nuevo mensaje
        texto_actual = self.salida.toPlainText()
        if not texto_actual.endswith("\n"):
            texto_actual += "\n"
        texto_actual += f"{mensaje}\n"
        self.salida.setPlainText(texto_actual)
        self.salida.moveCursor(self.salida.textCursor().End)

def main():
    app = QApplication(sys.argv)
    v = VentanaPrincipal()
    v.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
