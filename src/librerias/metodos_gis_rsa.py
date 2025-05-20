import geopandas as gpd
import pandas as pd
import os
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
from scipy.spatial import ConvexHull
import numpy as np
from metodos_rsa import lectura_archivo
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


def catalogo_gis(catalogo):
    """
    Genera un mapa con información de un catálogo sísmico.
    
    Argumentos:
        catalogo (list): Información en el formato de catálogo sísmico.
        indice (int): Índice del evento a graficar.

    Returns:
        None
    """
    file_path = './GIS/ecuador.shp'
    mapa_ec = gpd.read_file(file_path)
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    mapa_ec.plot(ax=ax, color='lightgrey')  # Cargar el mapa de Ecuador como fondo
    ax.axis([-81.5, -75, -5, 1.5])
    ax.set_title('SISMO', pad=20, fontdict={'fontsize': 16, 'color': '#4873ab'})
    ax.set_xlabel('Longitud')
    ax.set_ylabel('Latitud')
    colores = {'RSA': 'yellow', 'IGEPN': 'blue', 'USGS': 'black'}
    bordes = {'RSA': 'red', 'IGEPN': 'green', 'USGS': 'white'}
    for evento in catalogo:
        longitud = float(evento[8])
        latitud = float(evento[7])
        profundidad = evento[9]
        magnitud = evento[15]
        epicentro = evento[19]
        fuente = evento[17]
        ax.text(-81, -4.5, "Latitud: " + str(latitud), fontsize=8, color='black')
        ax.text(-81, -4.6, "Longitud: " + str(longitud), fontsize=8, color='black')
        ax.text(-81, -4.7, "Profundidad: " + str(profundidad), fontsize=8, color='black')
        ax.text(-81, -4.8, "Magnitud: " + str(magnitud), fontsize=8, color='black')
        ax.text(-81, -4.9, "Epicentro: " + epicentro, fontsize=8, color='black')
        ax.scatter(longitud, latitud, color=colores[fuente], linewidths=2, marker="o", edgecolor=bordes[fuente], s=100, label=fuente)
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())
    plt.show()

def catalogo_gis_(catalogo,indice):
    #catalogo, es la información en el formato de catálogo sismico que se va a graficar en el mapa
    #          con la posibilidad de que haya información de otras redes.
    contador=0
    ext=len(catalogo)
    if catalogo[0]!=[]:
        longitud=catalogo[0][8]
        latitud=catalogo[0][7]
        profundidad=catalogo[0][9]
        magnitud=catalogo[0][15]
        epicentro=catalogo[0][19]
    else:
        longitud=catalogo[1][8]
        latitud=catalogo[1][7]
        profundidad=catalogo[1][9]
        magnitud=catalogo[1][15]
        epicentro=catalogo[1][19]        
    file_path = '.\GIS\ecuador.shp'
    mapa_ec = gpd.read_file(file_path)
    # Control del tamaño de la figura del mapa
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    # Control del encuadre (área geográfica) del mapa
    ax.axis([-81.5, -75, -5, 1.5])
    # Control del título y los ejes
    ax.set_title('SISMO', 
             pad = 20, 
             fontdict={'fontsize':16, 'color': '#4873ab'})
    ax.set_xlabel('Longitud')
    ax.set_ylabel('Latitud')
    ax.text(-81,-4.5,"Latitud: "+str(latitud),fontsize=8,color='black')
    ax.text(-81,-4.6,"Longitud: "+str(longitud),fontsize=8,color='black')
    ax.text(-81,-4.7,"Profundidad: "+str(profundidad),fontsize=8,color='black')
    ax.text(-81,-4.8,"Magnitud: "+str(magnitud),fontsize=8,color='black')
    ax.text(-81,-4.9,"Epicentro "+epicentro,fontsize=8,color='black')
    ax.scatter(longitud,latitud,color='yellow',linewidths = 2,
            marker ="o",
            edgecolor ="red",
            s = 100)
    if ext>1:
        if catalogo[1][2]=='USGS':
            color_='black'
            ax.text(-80.68,-4.30,"USGS ",fontsize=6,color='black')
            ax.scatter(-80.75,-4.28,color="black",linewidths = 2, marker ="o",edgecolor ="black",s = 40)
        else:
            color_='red'
            ax.text(-80.68,-4.20,"IGEPN ",fontsize=6,color='black')
            ax.scatter(-80.75,-4.18,color="red",linewidths = 2,marker ="o", edgecolor ="red", s = 40)
        ax.scatter(catalogo[1][6],catalogo[1][5],color=color_,linewidths = 2,
            marker ="o",
            edgecolor = color_,
            s = 30)
        if ext>2:
            if catalogo[2][2]=='USGS':
                color_='black'
                ax.text(-80.68,-4.30,"USGS ",fontsize=6,color='black')
                ax.scatter(-80.75,-4.28,color="black",linewidths = 2, marker ="o",edgecolor ="black",s = 40)
            else:
                color_='red'
                ax.text(-80.68,-4.20,"IGEPN ",fontsize=6,color='black')
                ax.scatter(-80.75,-4.18,color="red",linewidths = 2,marker ="o", edgecolor ="red", s = 40)
            ax.scatter(catalogo[2][6],catalogo[2][5],color=color_,linewidths = 2,
                marker ="o",
                edgecolor = color_,
                s = 30)
    mapa_ec.plot(ax=ax,alpha=0.3,color="white",edgecolor="black",linewidth=0.4)
    return 



def proceso_gis(widget, procesamiento, archivo_estaciones):
    ax = widget.figure.add_subplot(111)
    widget.figure.clf()
    ax = widget.figure.add_subplot(111)
    gdf_1,estaciones = cobertura_red(archivo_estaciones, 50)
    gdf_2,estaciones = cobertura_red(archivo_estaciones, 150)
    ext = len(procesamiento)
    file_path = './GIS/ecuador.shp'
    mapa_ec = gpd.read_file(file_path)
    ax.axis([-81.5, -75, -5, 1.5])
    ax.set_title('SISMO', pad=20, fontdict={'fontsize': 16, 'color': '#4873ab'})
    longitud = 0
    latitud = 0
    profundidad = 0
    magnitud = 0
    rms = 'Intento fallido'
    for i in range(2, ext):
        if procesamiento[i][2] == "Fallido":
            continue
        longitud = float(procesamiento[i][5])
        latitud = float(procesamiento[i][4])
        profundidad = float(procesamiento[i][2])
        magnitud = float(procesamiento[i][3])
        rms = procesamiento[i][6]
        if i == ext - 1:
            ax.scatter(longitud, latitud, color='yellow', linewidths=2, marker="o", edgecolor="red", s=100)
        else:
            ax.scatter(longitud, latitud, color='black', s=40)
    
    point = Point(longitud, latitud)
    in_gdf_1 = gdf_1.contains(point).values[0]
    in_gdf_2 = gdf_2.contains(point).values[0]
    
    ax.set_xlabel('Longitud')
    ax.set_ylabel('Latitud')
    ax.text(-81, -4.5, "Latitud: " + str(latitud), fontsize=8, color='black')
    ax.text(-81, -4.6, "Longitud: " + str(longitud), fontsize=8, color='black')
    ax.text(-81, -4.7, "Profundidad: " + str(profundidad), fontsize=8, color='black')
    ax.text(-81, -4.8, "Magnitud: " + str(magnitud), fontsize=8, color='black')
    ax.text(-81, -4.9, "rms " + rms, fontsize=8, color='black')
    
    gdf_1.boundary.plot(ax=ax, color='blue')
    gdf_2.boundary.plot(ax=ax, color='green')
    
    mapa_ec.plot(ax=ax, alpha=0.3, color="white", edgecolor="black", linewidth=0.4)
    widget.canvas.draw()
    
    return (in_gdf_1, in_gdf_2)


class widget_grafico_mpl(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot(self, procesamiento, archivo_estaciones):
        return proceso_gis(self, procesamiento, archivo_estaciones)






def proceso_gis_(procesamiento,archivo_estaciones):
    #catalogo, es la información en el formato de catálogo sismico que se va a graficar en el mapa
    #          con la posibilidad de que haya información de otras redes.
    plt.clf()
    gdf_1,estaciones = cobertura_red(archivo_estaciones,50)
    gdf_2,estaciones = cobertura_red(archivo_estaciones,150)
    ext=len(procesamiento)
    file_path = '.\GIS\ecuador.shp'
    mapa_ec = gpd.read_file(file_path)
    # Control del tamaño de la figura del mapa
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    # Control del encuadre (área geográfica) del mapa
    ax.axis([-81.5, -75, -5, 1.5])
    # Control del título y los ejes
    ax.set_title('SISMO', 
             pad = 20, 
             fontdict={'fontsize':16, 'color': '#4873ab'})
    longitud=0
    latitud=0
    profundidad=0
    magnitud=0
    rms='Intento fallido'
    for i in range(2,ext):
        if procesamiento[i][2]=="Intento fallido:  No hay convergencia":
            continue
        longitud=float(procesamiento[i][5])
        latitud=float(procesamiento[i][4])
        profundidad=float(procesamiento[i][2])
        magnitud=float(procesamiento[i][3])
        rms=procesamiento[i][6]
        if i==ext-1:
            ax.scatter(longitud,latitud,color='yellow',linewidths = 2, marker ="o",edgecolor ="red",s = 100)
        else:
            ax.scatter(longitud,latitud,color='black',s = 40)
    point = Point(longitud, latitud)
    in_gdf_1 = gdf_1.contains(point).values[0]
    in_gdf_2 = gdf_2.contains(point).values[0]
    ax.set_xlabel('Longitud')
    ax.set_ylabel('Latitud')
    ax.text(-81,-4.5,"Latitud: "+str(latitud),fontsize=8,color='black')
    ax.text(-81,-4.6,"Longitud: "+str(longitud),fontsize=8,color='black')
    ax.text(-81,-4.7,"Profundidad: "+str(profundidad),fontsize=8,color='black')
    ax.text(-81,-4.8,"Magnitud: "+str(magnitud),fontsize=8,color='black')
    ax.text(-81,-4.9,"rms "+rms,fontsize=8,color='black')

    gdf_1.boundary.plot(ax=ax, color='blue')
    gdf_2.boundary.plot(ax=ax, color='green')

    mapa_ec.plot(ax=ax,alpha=0.3,color="white",edgecolor="black",linewidth=0.4)
    plt.interactive(True)
    return (in_gdf_1,in_gdf_2)

def graficar_catalogo_gis(catalogo):

  """
  Grafica un catálogo sísmico en un mapa GIS de Ecuador.

  Parámetros:
    catalogo: lista de listas con información de los eventos sísmicos.

  Retorno:
    None. Se genera un mapa GIS con los puntos de los eventos sísmicos.
  """

  # Carga del shapefile de Ecuador
  file_path = '.\GIS\ecuador.shp'
  mapa_ec = gpd.read_file(file_path)

  # Control del tamaño de la figura del mapa
  fig, ax = plt.subplots(1, 1, figsize=(8, 8))

  # Control del encuadre (área geográfica) del mapa
  ax.axis([-81.5, -75, -5, 1.5])

  # Control del título y los ejes
  ax.set_title('SISMO',
                pad=20,
                fontdict={'fontsize': 16, 'color': '#4873ab'})
  ax.set_xlabel('Longitud')
  ax.set_ylabel('Latitud')

  # Extracción de la información de los eventos
  eventos = []
  for evento in catalogo[1:]:
    profundidad = float(evento[2])
    magnitud = float(evento[3])
    latitud = float(evento[4])
    longitud = float(evento[5])
    rms = float(evento[6])

    # Creación del diccionario con la información del evento
    evento_dict = {

        "profundidad": profundidad,
        "magnitud": magnitud,
        "latitud": latitud,
        "longitud": longitud,
        "rms": rms,
    }
    eventos.append(evento_dict)

  # Graficar los puntos de los eventos
  for evento in eventos:
    magnitud = evento["magnitud"]
    if magnitud < 4:
        color = "green"
    elif magnitud < 6:
        color = "yellow"
    else:
        color = "red"
    ax.scatter(evento["longitud"], evento["latitud"], color=color, s=magnitud*10)

  # Agregar leyenda
  leyenda_colores = {
    "green": "Magnitud < 4",
    "yellow": "4 <= Magnitud < 6",
    "red": "Magnitud >= 6",
  }
  for color, label in leyenda_colores.items():
    ax.plot([], [], color=color, marker="o", label=label)
  ax.legend(loc="best")

  # Mostrar el mapa
  plt.show()


def cobertura_red(archivo,distancia):
    #archivo   -----  Archivo con las estaciones del día.
    #distancia  ----  distancoa en kilometros
    
    bandera=0
    if not os.path.exists(archivo):
        archivo="estaciones.csv"
        bandera=1
        
    estaciones_completa=lectura_archivo(archivo)
# Lista de estaciones
    estaciones=[]
    for estacion in estaciones_completa:
        if estacion[1]=='1':
            longitud=int(estacion[3])/10000.
            latitud=int(estacion[4])/10000.
            xxx=(estacion[2],longitud, latitud)
            estaciones.append(xxx)
    # Extraer las coordenadas
    coords = np.array([[estacion[1], estacion[2]] for estacion in estaciones])
    # Calcular el polígono convexo usando ConvexHull
    hull = ConvexHull(coords)
    hull_points = coords[hull.vertices]
    # Crear el polígono convexo
    polygon = Polygon(hull_points)
    offset_polygon = polygon.buffer(distancia/110.)
    # Crear un GeoDataFrame con el polígono
    gdf = gpd.GeoDataFrame(index=[0], crs="EPSG:4326", geometry=[offset_polygon])
    return gdf,coords

