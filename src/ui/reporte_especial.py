
from metodos_rsa import escritura_archivo,lectura_archivo
from metodos_gestion import obtener_directorios,obtencion_hora
#from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import *
from reportlab.graphics import shapes
from reportlab.graphics.charts.textlabels import Label
from reportlab.lib.colors import *
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
import csv
from PyQt5 import uic, QtWidgets#Importamos módulo uic y Qtwidgets
from datetime import datetime, date, time, timedelta
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox,QFileDialog)
import obspy
from obspy import read
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import copy
import pandas as pd
import matplotlib.pyplot as plt


qtCreatorFile="reporteS_especiales.ui"# Nuestro archivo UI aquí.
Ui_MainWindow,QtBassClass=uic.loadUiType(qtCreatorFile)#El modulo ui carga


import re

def extraer_rango_niveles(data_nivel, datos):
    """
    Extrae los niveles del embalse desde las 00:00 del día del primer evento hasta las 23:00 del día del último evento.
    
    Args:
        data_nivel (pd.DataFrame): DataFrame que contiene los niveles del embalse tomados cada hora.
        datos (list): Lista de eventos con formato 'AAMMDD_hhmmss.sis' que indican el inicio y el final del período.

    Returns:
        pd.DataFrame: DataFrame filtrado con los niveles del embalse en el rango de tiempo definido por los eventos.
    """
    # Asegurarse de que la lista de eventos no esté vacía
    if not datos or len(datos) == 0:
        print("La lista 'datos' está vacía.")
        return pd.DataFrame()

    # Obtener la fecha del primer evento y ajustarla a las 00:00 del día
    primer_evento = datos[0][0].split('.')[0]  # Formato 'AAMMDD_hhmmss.sis'
    primer_evento = primer_evento.replace('_', '')
    fecha_inicio = obtencion_hora(primer_evento).datetime  # Convertir a datetime usando obtencion_hora
    fecha_inicio = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day, 0, 0, 0)  # Ajustar a 00:00

    # Obtener la fecha del último evento y ajustarla a las 23:00 del día
    ultimo_evento = datos[-1][0].split('.')[0]
    ultimo_evento = ultimo_evento.replace('_', '') 
    fecha_fin = obtencion_hora(ultimo_evento).datetime  # Convertir a datetime
    fecha_fin = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 0, 0)  # Ajustar a 23:00

    # Filtrar los niveles del embalse en el rango de fechas usando data_nivel
    df_nivel_filtrado = data_nivel.loc[fecha_inicio:fecha_fin].copy()

    # Añadir la columna 'referencia_tiempo' explícitamente
    df_nivel_filtrado['referencia_tiempo'] = df_nivel_filtrado.index

    return df_nivel_filtrado

def encontrar_limite(ruta_archivo):
  """
  Encuentra el límite entre un archivo y su directorio usando expresiones regulares.

  Args:
      ruta_archivo (str): La ruta completa del archivo.

  Returns:
      str: El nombre del archivo sin el directorio.
  """
  partes = re.split(r"[\\/]", ruta_archivo)
  directorio_trabajo=''
  for directorio in partes:
      directorio_trabajo=directorio_trabajo+directorio+'/'
      if directorio=='DIA':
          break
  return (directorio_trabajo,partes[-1])



def graficar_nivel_y_caudal_con_filtro(df_final, df_filtrado):
    """
    Grafica los niveles del embalse, los caudales y los datos filtrados en función del tiempo utilizando subplots.
    
    Args:
        df_final (pd.DataFrame): DataFrame que contiene las columnas 'nivel_embalse', 'amplitud' y 'referencia_tiempo'.
        df_filtrado (pd.DataFrame): DataFrame filtrado para un rango específico de fechas.
    """
    # Verifica que el DataFrame contenga las columnas necesarias
    if 'nivel_embalse' not in df_final.columns or 'amplitud' not in df_final.columns or 'referencia_tiempo' not in df_final.columns:
        print("Error: Las columnas 'nivel_embalse', 'amplitud' o 'referencia_tiempo' no están presentes en el DataFrame.")
        return
    print(df_final, df_filtrado)
    
    # Asegurarse de que 'referencia_tiempo' sea el índice en ambos DataFrames
    if df_final.index.name != 'referencia_tiempo':
        df_final.set_index('referencia_tiempo', inplace=True)

    if df_filtrado.index.name != 'referencia_tiempo':
        df_filtrado.set_index('referencia_tiempo', inplace=True)

    # Crear los subplots: uno para nivel y caudal, otro para los datos filtrados
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8))

    # Graficar el nivel del embalse en el eje Y izquierdo
    ax1.plot(df_final.index, df_final['nivel_embalse'], label='Nivel del Embalse', color='b', linestyle='-')
    ax1.set_ylabel('Nivel del Embalse (m)', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.grid(True)

    # Graficar el caudal en el eje Y derecho
    ax2.plot(df_final.index, df_final['amplitud'], label='Caudal', color='r', linestyle='-')
    ax2.set_ylabel('Caudal (m³/s)', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.grid(True)

    # Título y leyenda del primer subplot
    ax1.set_title('Nivel del Embalse')
    ax2.set_title('Caudales')

    # Subplot 2: Graficar los datos filtrados en el tercer subplot
    ax3.plot(df_filtrado['referencia_tiempo'], df_filtrado['nivel'], label='Nivel del Embalse', color='g', linestyle='-')
    ax3.set_xlabel('Tiempo')
    ax3.set_ylabel('Nivel del embalse (m)', color='g')
    ax3.tick_params(axis='y', labelcolor='g')
    ax3.grid(True)

    # Ajustar el diseño para evitar solapamientos
    fig.tight_layout()

    # Mostrar el gráfico
    plt.show()


def caudales(archivo):
    datos = lectura_archivo(archivo)
    auxiliar = encontrar_limite(archivo)
    nombre_archivo = auxiliar[1]
    directorio_trabajo = auxiliar[0]

    # Archivo de niveles de agua
    archivo_niveles = 'G:/Mi unidad/Convenio ELECAUSTRO/niveles/niveles csv/Chanlud/niveles.csv'
    datos_niv = lectura_archivo(archivo_niveles)

    # Procesar datos de nivel, asegurándonos de crear un DataFrame correctamente
    nivel = []
    referencia_tiempo_nivel = []
    for dato in datos_niv:
        fecha_hora_dt = datetime.strptime(dato[1], "%m/%d/%Y %H:%M:%S")  # Asegúrate de que el índice de tiempo esté bien formateado
        referencia_tiempo_nivel.append(fecha_hora_dt)
        nivel_aux = float(dato[2])
        nivel.append(nivel_aux)

    # Crear el DataFrame para los niveles
    data_nivel = pd.DataFrame({'nivel': nivel, 'referencia_tiempo': referencia_tiempo_nivel})
    data_nivel.set_index('referencia_tiempo', inplace=True)  # Fijar la columna 'referencia_tiempo' como índice

    print('Caudal:')  
    bandera_dia = 1
    marca = 1
    valor_anterior = 0
    dia_anterior = 0
    amplitud_caudal = []
    referencia_tiempo_caudal = []
    niveles_embalse = []  # Lista para almacenar los niveles de embalse

    for evento in datos:
        directorios = obtener_directorios(evento[0])
        archivo_estaciones = directorio_trabajo + directorios['Directorio_base'] + '/' + evento[0][:-11] + '000000_est.csv'
        datos_estaciones = lectura_archivo(archivo_estaciones)
        archivo = evento[0][:6] + evento[0][7:-4]
        
        # Obtener la fecha-hora con `obspy.UTCDateTime` y convertirla a `datetime`
        fecha_hora_obspy = obtencion_hora(archivo)
        fecha_hora = fecha_hora_obspy.datetime  # Conversión de UTCDateTime a datetime
        fecha_hora = pd.Timestamp(fecha_hora)   # Convertir a pandas.Timestamp para garantizar compatibilidad
        
        dia = fecha_hora.day
        fecha_formateada = fecha_hora.strftime("%d/%m/%Y %H:%M:%S")
        
        #if dia == dia_anterior:
            #bandera_dia = 0
        #else:
            #bandera_dia = 1
#        bandera_dia = 1
#        enlace_estacion = float(datos_estaciones[1][53])  # Estación base de medición en Chanlud
#        if enlace_estacion == 100.:
#            marca = 0
#        else:
#            marca = 1
        marca = 0

        
        dia_anterior = fecha_hora - timedelta(days=1)
        anio_ = dia_anterior.year
        mes_ = dia_anterior.month
        dia_ = dia_anterior.day
        formato_final = f"{anio_:02d}{mes_:02d}{dia_:02d}_000000.sis"
        formato_final = formato_final[2:]
        directorios = obtener_directorios(formato_final)
        archivo_estaciones = directorio_trabajo + directorios['Directorio_base'] + '/' + formato_final[:-11] + '000000_est.csv'
#        datos_estaciones = lectura_archivo(archivo_estaciones)
#        enlace_estacion_anterior = float(datos_estaciones[1][53])

#        if enlace_estacion_anterior != 100. and bandera_dia:
#            marca = 1
#            valor_anterior = 0

        if marca:
            pass
        else:
            if valor_anterior != 0:
                tiempo = fecha_hora - valor_anterior
                caudal = 3500000. / tiempo.total_seconds()
                
                # Buscar el nivel de embalse más cercano o anterior a la fecha_hora
                nivel_embalse = data_nivel.loc[:fecha_hora].iloc[-1]['nivel'] if not data_nivel.loc[:fecha_hora].empty else None
                
                # Agregar valores a las listas
                referencia_tiempo_caudal.append(fecha_hora)
                amplitud_caudal.append(caudal)
                niveles_embalse.append(nivel_embalse)  # Añadir el nivel de embalse
                
                print(f"{fecha_formateada}; {caudal}; {nivel_embalse}")
        
        valor_anterior = fecha_hora
        dia_anterior = dia

    # Construir el DataFrame final con los valores de caudal, referencia de tiempo y nivel de embalse
    data = {
        'amplitud': amplitud_caudal,
        'referencia_tiempo': referencia_tiempo_caudal,
        'nivel_embalse': niveles_embalse
    }

    df_final = pd.DataFrame(data)
    df_nivel_filtrado = extraer_rango_niveles(data_nivel, datos)
    graficar_nivel_y_caudal_con_filtro(df_final, df_nivel_filtrado)



def inclinacion(archivo):
    datos=lectura_archivo(archivo)
    auxiliar = encontrar_limite(archivo)
    nombre_archivo = auxiliar[1]
    directorio_trabajo=auxiliar[0]
    estacion=nombre_archivo[:4]
    tipo=nombre_archivo[5:-8]
    print('Inclinacion:')
    for dato in datos:
        directorios=obtencion_directorios(dato[0])
        archivo_mseed=directorio_trabajo+directorios[2]+'/'+estacion+'_20'+dato[0][:-3]+'mseed'
        stLeido = read(archivo_mseed)
        componentes=len(stLeido)

        for i in range(0,componentes):
            promedio=0
            for valor in stLeido[i]:
                promedio += valor
            promedio=promedio/(len(stLeido[i]))
            print('Componente ',i,':',promedio)
        input('Enter:')
        

def graficos(archivo):
    pass
def filtros(archivo):
    pass


class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):#Constructor de la clase
        QtWidgets.QMainWindow.__init__(self)#Constructor
        Ui_MainWindow.__init__(self)#Constructor
        self.setupUi(self)# Método Constructor de la ventana
        self.btn_abrir.clicked.connect(self.Abrir_archivo)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.directorio_trabajo="G:/Mi unidad/DIA/"
        lista_=('CAUDALES','INCLINACION','GRAFICOS','FILTROS')
        self.cmbx_tipo.addItems(lista_)

    def Abrir_archivo(self):
        options = QFileDialog.Options()
        file_path = QFileDialog.getOpenFileName()[0]
        if file_path:
            archivo = file_path

        if self.cmbx_tipo.currentIndex()==0:
            caudales(archivo)
        elif self.cmbx_tipo.currentIndex()==1:
            inclinacion(archivo)
        elif self.cmbx_tipo.currentIndex()==2:
            graficos(archivo)
        elif self.cmbx_tipo.currentIndex()==3:
            filtros(archivo)

    def Guardar_(self):
        pass

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath[-1]=='/':
            folderpath=folderpath
        else:
            folderpath=folderpath+'/'
        self.directorio_trabajo=folderpath

           
    def Salir_(self):
        window.destroy()       


if __name__ == '__main__': #Condicional que comprueba si ha sido ejecutado o importado
    app = QtWidgets.QApplication(sys.argv)#Creamos app y le pasamos una lista de argumentos vacíos
    #Borramos todo el resto del código y ahora vamos a instanciar nuestra clase MainWindow:
    window = MyApp()
    window.show()#Muestra la ventana:
    app.exec_() #Usamos app.exec_() para crear el bucle de ejecución

