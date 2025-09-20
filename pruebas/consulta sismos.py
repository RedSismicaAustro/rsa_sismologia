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
    QLabel, QLineEdit, QPushButton, QFileDialog, QPlainTextEdit, QMessageBox, QProgressBar
)
from metodos_rsa import lectura_archivo,escritura_archivo
from metodos_gestion import obtener_directorios,parametros_estaciones
import xml.etree.ElementTree as ET
import shutil
from datetime import timedelta
from obspy import UTCDateTime, read, Trace, Stream
def ajuste_tiempo(tiempo,marca,offset,ancho):
        marca_ent=int(marca)
        marca_fracc=int((marca %1)*1000000)
        if marca >= 60:
            tiempo=tiempo+timedelta(minutes=1)
            tiempo=tiempo.replace(second=marca_ent-60)
            tiempo=tiempo.replace(microsecond=marca_fracc)
        else:
            tiempo=tiempo.replace(second=marca_ent)
            tiempo=tiempo.replace(microsecond=marca_fracc)

        tiempo_str=tiempo.strftime("%Y-%m-%dT%H:%M:%S.") + f"{tiempo.microsecond//1000:03d}Z"
        tiempo_ini=tiempo-timedelta(seconds=(offset+ancho/2))
        tiempo_ini_str=tiempo_ini.strftime("%Y-%m-%dT%H:%M:%S.") + f"{tiempo_ini.microsecond//1000:03d}Z"
        tiempo_fin=tiempo-timedelta(seconds=(offset-ancho/2))
        tiempo_fin_str=tiempo_fin.strftime("%Y-%m-%dT%H:%M:%S.") + f"{tiempo_fin.microsecond//1000:03d}Z"
        tiempo_ini=UTCDateTime(tiempo_ini)
        tiempo_fin=UTCDateTime(tiempo_fin)
        return tiempo_ini,tiempo_fin,tiempo_str,tiempo_ini_str,tiempo_fin_str

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
        self.salida.setMinimumHeight(220)
        self._actualizar_encabezado_salida()



        # Barra de progreso + botón Salir al pie
        pie = QHBoxLayout()
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setTextVisible(True)
        self.barra_progreso.setMinimum(0)
        self.barra_progreso.setValue(0)

        btn_salir = QPushButton("Salir")
        btn_salir.clicked.connect(self.close)

        pie.addWidget(self.barra_progreso, 1)
        pie.addStretch()
        pie.addWidget(btn_salir)

        layout.addLayout(fila_ruta)
        layout.addLayout(fila_botones)

        layout.addWidget(self.salida, 1)
        layout.addLayout(pie)
        self.setCentralWidget(contenedor)
        self.parametros=parametros_estaciones()

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

 
    def obtener_evento_por_sis(self, nombre_sis: str, ruta_xml: str):
        """
        Busca en ruta_xml el <Evento> cuyo <ruta> coincida con nombre_sis (ej: '20250825_041601.sis').
        Devuelve un dict con:
            - metadatos del evento (id_evento, anio, mes, etc.)
            - 'estaciones': lista de dicts con la info de cada <estacion>.
            Retorna None si no se encuentra.
        """
        try:
            raiz = ET.parse(ruta_xml).getroot()
        except Exception as e:
            QMessageBox.warning(self, "Error XML", f"No se pudo leer el archivo XML:\n{ruta_xml}\n{e}")
            return None

        evento = None
        for nodo_evento in raiz.findall(".//Evento"):
            ruta_txt = (nodo_evento.findtext("ruta") or "").strip()
            if Path(ruta_txt).name == nombre_sis:
                    evento = nodo_evento
                    break
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


        # Inicializar archivo de log de incidencias
        self.ruta_log = os.path.join(self.directorio_destino, "log_extraccion.txt")
        with open(self.ruta_log, "w", encoding="utf-8") as f:
            f.write(f"LOG de extracción - {datetime.now().isoformat(sep=' ', timespec='seconds')}\n")



        self.lista_mseed_eventos=[]

        self._append_resultado("Recopilando Sismos…")
        # Fase 1: progreso por sismo
        total_sismos = len(self.sismos)
        self.barra_progreso.setRange(0, max(total_sismos, 1))
        self.barra_progreso.setValue(0)
        progreso = 0
        for sismo in self.sismos:
            self.archivo=os.path.join(self.directorio_trabajo,Path(sismo).stem.replace("_", ""))
            directorio=obtener_directorios(self.archivo)
            sufijo = str(directorio["sufijo_mseed"]).strip()
            vector_mseed = sorted(
                str(p) for p in Path(directorio["Directorio_eventos"]).glob("*.mseed")
                if p.name.endswith(sufijo)
            )
            self.lista_mseed_eventos.append(vector_mseed)
            progreso += 1
            self.barra_progreso.setValue(progreso)
            QApplication.processEvents()
        archivo_eventos_csv=os.path.join(self.directorio_destino,'test.csv')
        archivo_fases_csv=os.path.join(self.directorio_destino,'waveforms.csv')
        aux=('mseed','T-ini','T-fin','Muestreo','Canales','T-P','Pond T-P','T-S','Pond T-S')
        lista_eventos=[]
        lista_eventos.append(aux)
        aux=('fase','evento','Tipo','Canal','T-ini','T-fin','T-pick','Muestreo','Canales','Ponderacion')
        lista_fases=[]
        lista_fases.append(aux)
        contador_fases_p=0
        contador_fases_s=0
        contador_ruido=0
        self._append_resultado("Extrayendo eventos por canal…")
        # Fase 2: progreso por archivo mseed
        total_archivos = sum(len(lst) for lst in self.lista_mseed_eventos)
        self.barra_progreso.setRange(0, max(total_archivos, 1))
        self.barra_progreso.setValue(0)
        progreso = 0

        for lista_dia in self.lista_mseed_eventos:
            for archivo_origen in lista_dia:
                nombre_archivo = Path(archivo_origen).name
                dt_evento = datetime.strptime(Path(nombre_archivo).stem.split("_", 1)[1], "%Y%m%d_%H%M%S")
                directorio_test=os.path.join(self.directorio_destino,"test")
                directorio_wave=os.path.join(self.directorio_destino,"waveforms")
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
                for i,estacion in enumerate(self.parametros['CODIGO']):
                    if estacion==estacion_objetivo:
                        codigo_canal=self.parametros['CANAL'][i]
                sismo_objetivo = f"{Path(nombre_archivo).stem}.sis"[5:]   # asegura AAAAMMDD_hhmmss.sis a partir de 'sismo'
                archivo=os.path.join(self.directorio_trabajo,Path(sismo_objetivo).stem.replace("_", ""))
                directorio=obtener_directorios(archivo)
                archivo = Path(archivo_origen).name[:13]+'_000000.mseed'
                archivo_reg_continuo=os.path.join(directorio["Directorio_registros"],archivo)
                st=read(archivo_origen)
                info_evt = self.obtener_evento_por_sis(sismo_objetivo,directorio["archivo_xml"])
                ponderacion_p='NA'
                ponderacion_s='NA'
                dt_evento_s_str='NA'
                dt_evento_p_str='NA'
                if info_evt:
                    for est in info_evt["estaciones"]:
                        if est.get("nombre") == estacion_objetivo:
                            filename=f"event_{contador_fases_p:04d}_P.mseed"
                            tiempo_p=float(est['p-sec'])
                            try:
                                ponderacion_p=est['Disp.'][-1]
                            except IndexError:
                                print(est['Disp.'])
                            dt_evento_p_ini,dt_evento_p_fin,dt_evento_p_str,dt_evento_p_ini_str,dt_evento_p_fin_str=ajuste_tiempo(dt_evento,tiempo_p,0,6)
                            aux=(filename,sismo_objetivo,'P',estacion_objetivo,dt_evento_p_ini_str,dt_evento_p_fin_str,dt_evento_p_str,st[0].stats.sampling_rate,codigo_canal, ponderacion_p)
                            contador_fases_p=contador_fases_p+1
                            lista_fases.append(aux)
                            st_fase = read(archivo_reg_continuo, format="MSEED",
                                           starttime=dt_evento_p_ini, endtime=dt_evento_p_fin, nearest_sample=False)
                            nombre_archivo_ = os.path.join(directorio_wave, filename)
                            self._guardar_stream_seguro(
                                st_fase, nombre_archivo_,
                                f"P estacion={estacion_objetivo} evento={sismo_objetivo}",
                                formato='MSEED', encoding='STEIM1', reclen=512
                            )
                            filename=f"noise_{contador_ruido:04d}.mseed"
                            dt_ruido_ini,dt_ruido_fin,dt_ruido_str,dt_ruido_ini_str,dt_ruido_fin_str=ajuste_tiempo(dt_evento,tiempo_p,10,6)
                            aux=(filename,sismo_objetivo,'N',estacion_objetivo,dt_ruido_ini_str,dt_ruido_fin_str,'NA',st[0].stats.sampling_rate,codigo_canal, 'NA')
                            contador_ruido=contador_ruido+1
                            lista_fases.append(aux)
                            st_fase = read(archivo_reg_continuo, starttime=dt_ruido_ini, endtime=dt_ruido_fin)
                            nombre_archivo_ = os.path.join(directorio_wave, filename)
                            self._guardar_stream_seguro(
                                st_fase, nombre_archivo_,
                                f"NOISE estacion={estacion_objetivo} evento={sismo_objetivo}"
                            )
                            if est['marc.s'] != '':
                                filename=f"event_{contador_fases_s:04d}_S.mseed"
                                tiempo_s=float(est['s-sec'])
                                ponderacion_s=est['marc.s'][-1]
                                dt_evento_s_ini,dt_evento_s_fin,dt_evento_s_str,dt_evento_s_ini_str,dt_evento_s_fin_str=ajuste_tiempo(dt_evento,tiempo_s,0,6)
                                aux=(filename,sismo_objetivo,'S',estacion_objetivo,dt_evento_s_ini_str,dt_evento_s_fin_str,dt_evento_s_str,st[0].stats.sampling_rate,codigo_canal, ponderacion_s)
                                st_fase=read(archivo_reg_continuo,starttime=dt_evento_s_ini,endtime=dt_evento_s_fin)
                                st_fase = read(archivo_reg_continuo, starttime=dt_evento_s_ini, endtime=dt_evento_s_fin)
                                nombre_archivo_ = os.path.join(directorio_wave, filename)
                                self._guardar_stream_seguro(
                                    st_fase, nombre_archivo_,
                                    f"S estacion={estacion_objetivo} evento={sismo_objetivo}"
                                )
                                contador_fases_s=contador_fases_s+1
                                lista_fases.append(aux)
                aux=(nombre_archivo,st[0].stats.starttime.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                     st[0].stats.endtime.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                     st[0].stats.sampling_rate,len(st),dt_evento_p_str,ponderacion_p,
                     dt_evento_s_str,ponderacion_s)
                lista_eventos.append(aux)

                progreso += 1
                self.barra_progreso.setValue(progreso)
                QApplication.processEvents()


        escritura_archivo(archivo_eventos_csv,lista_eventos)
        escritura_archivo(archivo_fases_csv,lista_fases)

        # Mensaje final en el panel y completar barra
        self._append_resultado("Proceso finalizado ✅")
        self.barra_progreso.setValue(self.barra_progreso.maximum())


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



    def _log_incidencia(self, mensaje: str):
        """Anexa una línea al log si está configurado."""
        if not hasattr(self, "ruta_log") or self.ruta_log is None:
            return
        with open(self.ruta_log, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(sep=' ', timespec='seconds')}] {mensaje}\n")

    def _guardar_stream_seguro(self, st, ruta_salida, contexto, formato="MSEED", **kwargs) -> bool:
        """
        Intenta escribir un Stream. Si está vacío o hay error, lo registra en el log.
        Retorna True si escribió, False en caso contrario.
        """
        try:
            if (not st) or (st.count() == 0) or all(tr.stats.npts == 0 for tr in st):
                self._log_incidencia(f"STREAM VACÍO: {contexto} -> {ruta_salida}")
                return False
            Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
            st.write(ruta_salida, format=formato, **kwargs)
            return True
        except Exception as e:
            self._log_incidencia(f"ERROR ESCRITURA: {contexto} -> {ruta_salida} | {e}")
            return False





def main():
    app = QApplication(sys.argv)
    v = VentanaPrincipal()
    v.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
