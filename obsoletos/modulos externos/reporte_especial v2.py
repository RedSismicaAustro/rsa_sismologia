import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from metodos_rsa import lectura_archivo
from metodos_gestion import obtener_directorios, obtencion_hora
from obspy import read
from datetime import datetime, timedelta

qtCreatorFile = "reporteS_especiales.ui"  # Nuestro archivo UI aquí
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)


def graficar_nivel_y_caudal_con_filtro(df_final, df_filtrado, archivo_origen=None):
    """
    Grafica niveles y caudales, permitiendo eliminar puntos de caudal con clic derecho.
    Los puntos eliminados se marcan visualmente con una cruz negra ('x').
    """
    columnas_necesarias = {'nivel_embalse', 'amplitud'}
    if not columnas_necesarias.issubset(df_final.columns):
        print("Error: Las columnas necesarias no están presentes.")
        print("Columnas disponibles:", df_final.columns.tolist())
        return

    if df_final.index.name != 'referencia_tiempo':
        df_final.set_index('referencia_tiempo', inplace=True)

    if df_filtrado.index.name != 'referencia_tiempo':
        df_filtrado.set_index('referencia_tiempo', inplace=True)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8))

    ax1.plot(df_final.index, df_final['nivel_embalse'], label='Nivel del Embalse', color='b', linestyle='-')
    ax1.set_ylabel('Nivel del Embalse (m)', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_title('Nivel del Embalse')
    ax1.grid(True)

    linea_caudal, = ax2.plot(df_final.index, df_final['amplitud'], 'o-', label='Caudal', color='r')
    ax2.set_ylabel('Caudal (m³/s)', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.set_title('Caudales')
    ax2.grid(True)

    puntos_eliminados_x = []
    puntos_eliminados_y = []
    scatter_eliminados = ax2.plot([], [], 'x', color='black', label='Punto eliminado')[0]

    ax3.plot(df_filtrado.index, df_filtrado['nivel'], label='Nivel del Embalse', color='g', linestyle='-')
    ax3.set_xlabel('Tiempo')
    ax3.set_ylabel('Nivel del embalse (m)', color='g')
    ax3.tick_params(axis='y', labelcolor='g')
    ax3.grid(True)

    def on_click(event):
        if event.inaxes == ax2 and event.button == 3:
            xdata = df_final.index
            tiempo_clic = event.xdata
            tiempo_real = pd.to_datetime(mdates.num2date(tiempo_clic)).replace(tzinfo=None)

            if isinstance(xdata, pd.DatetimeIndex) and xdata.tz is not None:
                xdata = xdata.tz_localize(None)

            idx_cercano = xdata.get_indexer([tiempo_real], method='nearest')[0]
            tiempo_objetivo = xdata[idx_cercano]

            if tiempo_objetivo in df_final.index:
                y_valor = df_final.loc[tiempo_objetivo, 'amplitud']
                print(f"Eliminando punto en: {tiempo_objetivo} → Caudal: {y_valor}")
                puntos_eliminados_x.append(tiempo_objetivo)
                puntos_eliminados_y.append(y_valor)
                df_final.drop(index=tiempo_objetivo, inplace=True)
                linea_caudal.set_data(df_final.index, df_final['amplitud'])
                scatter_eliminados.set_data(puntos_eliminados_x, puntos_eliminados_y)
                ax2.relim()
                ax2.autoscale_view()
                fig.canvas.draw_idle()

    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.tight_layout()
    plt.show()
    return fig, df_final  # ✅ También devolvemos el DataFrame actualizado


class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MyApp, self).__init__()
        self.setupUi(self)

        self.btn_abrir.clicked.connect(self.Abrir_archivo)
        self.btn_graficos.clicked.connect(self.volver_a_graficar)
        self.btn_guardar.clicked.connect(self.guardar_datos_actualizados)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)

        self.directorio_trabajo = "G:/Mi unidad/DIA/"
        self.df_final_original = None
        self.df_filtrado = None
        self.archivo_actual = None
        self.figura_actual = None

        self.cmbx_tipo.addItems(('CAUDALES', 'INCLINACION', 'GRAFICOS', 'FILTROS'))

    def Abrir_archivo(self):
        file_path = QFileDialog.getOpenFileName()[0]
        if file_path:
            self.archivo_actual = file_path
            if self.cmbx_tipo.currentIndex() == 0:
                self.procesar_caudales(file_path)

    def procesar_caudales(self, archivo):
        datos = lectura_archivo(archivo)
        directorio_trabajo, nombre_archivo = os.path.split(archivo)
        self.directorio_trabajo = directorio_trabajo + '/'

        archivo_niveles = 'G:/Mi unidad/Convenio ELECAUSTRO/niveles/niveles csv/Chanlud/niveles.csv'
        datos_niv = lectura_archivo(archivo_niveles)

        nivel = []
        referencia_tiempo_nivel = []
        for dato in datos_niv:
            fecha_hora_dt = datetime.strptime(dato[1], "%m/%d/%Y %H:%M:%S")
            referencia_tiempo_nivel.append(fecha_hora_dt)
            nivel.append(float(dato[2]))

        data_nivel = pd.DataFrame({'nivel': nivel, 'referencia_tiempo': referencia_tiempo_nivel})
        data_nivel.set_index('referencia_tiempo', inplace=True)

        print('Caudal:')
        amplitud_caudal = []
        referencia_tiempo_caudal = []
        niveles_embalse = []
        valor_anterior = None

        for evento in datos:
            fecha_hora_obspy = obtencion_hora(evento[0].replace('_', '')[:-4])
            fecha_hora = pd.Timestamp(fecha_hora_obspy.datetime)

            if valor_anterior:
                tiempo = fecha_hora - valor_anterior
                caudal = 3500000. / tiempo.total_seconds()

                # ✅ Ajuste de caudal si es posterior al 20 de noviembre de 2024
                fecha_umbral = pd.Timestamp(2024, 11, 20)
                if fecha_hora >= fecha_umbral:
                    caudal *= 1.2


                nivel_embalse = data_nivel.loc[:fecha_hora].iloc[-1]['nivel'] if not data_nivel.loc[:fecha_hora].empty else None
                referencia_tiempo_caudal.append(fecha_hora)
                amplitud_caudal.append(caudal)
                niveles_embalse.append(nivel_embalse)
                print(f"{fecha_hora}; {caudal}; {nivel_embalse}")

            valor_anterior = fecha_hora

        data = {
            'amplitud': amplitud_caudal,
            'referencia_tiempo': referencia_tiempo_caudal,
            'nivel_embalse': niveles_embalse
        }

        df_final = pd.DataFrame(data)
        df_final.set_index('referencia_tiempo', inplace=True)

        self.df_filtrado = data_nivel.loc[df_final.index.min():df_final.index.max()].copy()
        self.df_filtrado['referencia_tiempo'] = self.df_filtrado.index

        self.figura_actual, self.df_final_original = graficar_nivel_y_caudal_con_filtro(
            df_final.copy(),
            self.df_filtrado.copy(),
            archivo_origen=archivo
        )

    def volver_a_graficar(self):
        if self.archivo_actual is None:
            QMessageBox.warning(self, "Archivo no cargado", "Debes cargar un archivo primero.")
            return

        ruta_directorio = os.path.dirname(self.archivo_actual)
        nombre_archivo = os.path.splitext(os.path.basename(self.archivo_actual))[0]
        ruta_modificado = os.path.join(ruta_directorio, nombre_archivo + '_caudal_modificado.csv')

        if not os.path.exists(ruta_modificado):
            QMessageBox.warning(self, "Archivo no encontrado",
                                "No se encontró el archivo modificado. Guarda primero los cambios.")
            return

        df = pd.read_csv(ruta_modificado, parse_dates=['referencia_tiempo'])
        df.set_index('referencia_tiempo', inplace=True)
        self.df_final_original = df

        if self.df_filtrado is None:
            QMessageBox.warning(self, "Faltan datos", "No se han cargado los niveles del embalse.")
            return

        if self.figura_actual:
            plt.close(self.figura_actual)
            self.figura_actual = None

        self.figura_actual, self.df_final_original = graficar_nivel_y_caudal_con_filtro(
            self.df_final_original.copy(),
            self.df_filtrado.copy(),
            self.archivo_actual
        )

    def guardar_datos_actualizados(self):
        if self.df_final_original is None or self.archivo_actual is None:
            QMessageBox.warning(self, "Datos faltantes", "No hay datos de caudal para guardar.")
            return

        try:
            df = self.df_final_original.copy()
            inicio_mes = pd.Timestamp(df.index.min().year, df.index.min().month, 1)
            tiempo_en_dias = (df.index - inicio_mes).total_seconds() / 86400.0

            # ✅ Reemplazar si ya existe
            if 'tiempo_en_dias' in df.columns:
                df['tiempo_en_dias'] = tiempo_en_dias
            else:
                df.insert(1, 'tiempo_en_dias', tiempo_en_dias)

            ruta_directorio = os.path.dirname(self.archivo_actual)
            nombre_archivo = os.path.splitext(os.path.basename(self.archivo_actual))[0]
            ruta_guardado = os.path.join(ruta_directorio, nombre_archivo + '_caudal_modificado.csv')

            df.to_csv(ruta_guardado, index=True)
            QMessageBox.information(self, "Guardado exitoso", f"Archivo guardado en:\n{ruta_guardado}")
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar el archivo:\n{str(e)}")

    def seleccionar_drive(self):
        folderpath = QFileDialog.getExistingDirectory(self, 'Selecciona el directorio de trabajo')
        if not folderpath.endswith('/'):
            folderpath += '/'
        self.directorio_trabajo = folderpath

    def Salir_(self):
        self.close()


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
