import sys
import os
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
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)



import math 
from metodos_rsa import extraccion_dato,num_reportes,leer_mseed,convertir_lista,guardar_seniales_csv
from metodos_rsa import correccion,lectura_archivo,escritura_archivo,espectro_respuesta,referencia_directorio_completa
from metodos_gestion import parametros_estaciones,obtencion_directorios,obtener_directorios
from metodos_gis_rsa import cobertura_red
import scipy.fft
import matplotlib.pyplot as plt
from PyQt5.QtCore import QTime,QDate,QDateTime
from datetime import datetime,  timedelta
from reportlab.lib import colors
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.textlabels import Label
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
from reportlab.graphics.shapes import Drawing, Rect,Circle,String,Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.rl_config import defaultPageSize
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.lib.colors import white
import numpy as np
import csv
import copy
import xml.etree.ElementTree as ET



IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19

NUMERO_ESTACIONES=101

IDX_LONGITUD_MINIMA,IDX_LATITUD_MINIMA,IDX_LONGITUD_MAXIMA,IDX_LATITUD_MAXIMA=0,1,2,3
IDX_POSICION_X,IDX_POSICION_Y,IDX_ANCHO,IDX_ALTO,=0,1,2,3

def marcar_tiempo(lienzo,x_,y_,tiempo_inicio,ancho,duracion,catNames):
    membrete=0
    intervalo=ancho/duracion   #Escala en el gráfico.
    pos_y=y_+50
    for k in range(0, int(duracion)):
        pos_x=x_+k*intervalo
        if k==0:
            fuente=6
            offset=8
            linea=10
            membrete=1
            texto=catNames[0]
            lienzo.line(pos_x,pos_y-linea,pos_x,pos_y)
            lienzo.setFont('Helvetica', fuente)
            lienzo.drawString(pos_x-10,y_+42-offset,texto)
        else:
            tiempo_=tiempo_inicio.second+k
            if tiempo_%10==0:  #Con esto solo se grafican las divisiones enteras o las decenas en este caso.
                texto=catNames[membrete]
                if len(texto)==2:
                    fuente=4
                    offset=2
                    linea=5
                else:
                    fuente=4
                    offset=6
                    linea=10
                pos_x=x_+k*intervalo#pos_x=x_+k*intervalo-10
                lienzo.line(pos_x,pos_y-linea,pos_x,pos_y)
                lienzo.setFont('Helvetica', fuente)
                lienzo.drawString(pos_x-offset,y_+42-offset,texto)
                membrete=membrete+1
    return lienzo

def obtener_marcas_tiempo(tr):
    #tr  es el stream que contiene el achivo mseed de la señal.
    #### Marcas de tiempo    Las unidades de tiempo son segundos
    duracion=tr[0].stats.endtime.timestamp-tr[0].stats.starttime.timestamp
    tiempo_inicio=tr[0].stats.starttime
    tiempo_inicial=tr[0].stats.starttime.time.second
    # Cálculo de las marcas de tiempo
    catNames=[]#Varible qu contiene las marcas de tiempo.
    for k in range(0, int(duracion)):
        if k==0:
            catNames.append(str(tiempo_inicio.time))
            #El primer valor es el tiempo inicial HH:MM:SS
        else:
            tiempo_real=tiempo_inicio+k#Formato HH:MM:SS
            tiempo_=tiempo_inicio.second+k #Formato en segundos.
            if tiempo_%60==0:
                formato_hora_minuto = tiempo_real.strftime("%H:%M")
                catNames.append(formato_hora_minuto)
                #El formato es de la forma HH:MM, cada paso por el segundo 60.
            else:
                if  tiempo_%10==0:
                    segundos = tiempo_real.second
                    segundos_2_digitos = "{:02d}".format(segundos)
                    catNames.append(segundos_2_digitos)
    return tiempo_inicio,tiempo_inicial,duracion, catNames



def encontrar_cadena(lista, cadena):
    for i, elemento in enumerate(lista):
        if elemento == cadena:
            return i  # Devuelve la ubicación de la cadena en la lista
    return -1  # La cadena no se encuentra en la lista



def responsables_tiempos_(lienzo,resumen_responsables):
            dibujo_chart = Drawing(400, 200)
            lista_resp=[]
            responsables =  os.path.join(ruta_proyecto,"datos", 'responsables.csv')
            responsables = os.path.abspath(responsables)


            with open(responsables,newline='') as f:
                datos=csv.reader(f,delimiter=';',quotechar=';')
                for r in datos:
                    lista_resp.append(r[0])
            resumen=[]
            resumen.append(['RESPONSABLE','HORA','TOT.','SIS.','FF','FC','Loc.','TEL.','IND.','Ruido','3 est','4 est','5 est','6 est','7 est','8 est'])#['RESPONSABLE','HORA','TOTAL','SISMOS','FF','FC','TEL.','Loc.','IND.','Ruido','3 est','4 est','5 est','6 est','7 est','8 est']
            for responsable in lista_resp:
                acumulado_responsable=[]
                for res_responsable in resumen_responsables:
                    if res_responsable[0]==responsable:
                        if acumulado_responsable==[]:
                            acumulado_responsable=res_responsable
                            if res_responsable[1]=='12H':
                                acumulado_responsable[1]='360'
                            else:
                                acumulado_responsable[1]='180'
                        else:
                            for i in range (1,len(acumulado_responsable)):
                                if i==1:
                                    if res_responsable[i]=='12H':
                                        acumulado_responsable[i]=str(int(acumulado_responsable[i])+360)
                                    else:
                                        acumulado_responsable[i]=str(int(acumulado_responsable[i])+180)
                                else:
                                    acumulado_responsable[i]=str(int(acumulado_responsable[i])+int(res_responsable[i]))
                if acumulado_responsable==[]:
                    acumulado_responsable=[responsable,'0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0']
                resumen.append(acumulado_responsable)
            dibujo_chart.add(String(180,155,'Resumen de tiempos invertidos:',fontSize=14))
            lista_resp=resumen
            aux=len(lista_resp)
            for i in range(0,aux):
                vector=lista_resp[i]
                if i!=0:
                    formula=round((int(vector[1])+int(vector[2])*60+int(vector[10])*300+int(vector[11])*600+int(vector[12])*1200)/3600,2)
                    formula=str(formula)
                vector=lista_resp[i][0:9]
                if i==0:
                    vector.append('T(horas)')
                else:
                    vector.append(formula)
                for j in range(0,len(vector)):
                    x_coor=105+j*40
                    y_coor=135-i*12
                    if j==0:
                        x_coor=45
                    if j!=1:
                        dibujo_chart.add(String(x_coor,y_coor,vector[j],fontSize=12))
            dibujo_chart.drawOn(lienzo, 15,400)
            return lienzo

def estadistica_(lienzo,resumen,fecha_ini,mapa_,bandera_dia):
        #Impresión del resumen diario de eventos procesados a travez de un chart de barras.
        dibujo_chart = Drawing(500, 200)
        data = [[],[]]
        nombres=[]
        maximo=0
        fecha=fecha_ini
        if mapa_<4 or bandera_dia==0: #Resumen como matriz
            sismos_procesados=int(resumen[1][1])
        else: #Reporte de periodo
            sismos_procesados=sum(resumen)#Resumen cono vector con los dos primeros valores 0
        tope=int(len(resumen)/35)+1
        contador_datos=0
        for i in range(2,len(resumen)):
            if mapa_<4:
                sismos_procesados=int(resumen[i][0])
                sismos_no_procesados=int(resumen[i][1])
            else:
                sismos_procesados=resumen[i]
                sismos_no_procesados=0
            data[0].append(sismos_procesados)
            data[1].append(sismos_no_procesados)
            fecha_ = QDate(fecha.year, fecha.month,fecha.day)
            if contador_datos==0:
                nombres.append(fecha_.toString('dd/MMM'))
            else:
                nombres.append(fecha_.toString(' '))
            contador_datos=contador_datos+1
            if contador_datos==tope:
                contador_datos=0
            fecha = fecha + timedelta(1)
            if((sismos_procesados+sismos_no_procesados)>maximo):
                maximo=sismos_procesados+sismos_no_procesados
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = maximo
        bc.height = 112
        bc.width = 500
        bc.data = data
        bc.strokeColor = colors.black
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = maximo+10
        bc.valueAxis.valueStep = 10
        bc.categoryAxis.labels.boxAnchor = 'ne'
        bc.categoryAxis.labels.dx = -8
        bc.categoryAxis.labels.angle = 90
        bc.categoryAxis.categoryNames = nombres
        bc.categoryAxis.style = 'stacked'
        bc.bars[0].fillColor = colors.darkgreen
        bc.bars[0].strokeWidth=0.01
        bc.bars[1].fillColor = colors.darkred
        bc.bars[1].strokeWidth=0.01
        if mapa_==2 or mapa_==4:
            pass
        else:
            dibujo_chart.add(bc)
            if mapa_<4:  #mapa_==0   Reporte general  Etuvo <3
                dibujo_chart.add(String(185,135,'Estadística de Registros Sísmicos',fontSize=14))
                dibujo_chart.add(Rect(450,125,6,6,fillColor=colors.darkred))
                dibujo_chart.add(String(457,125,'No Procesados (FF)',fontSize=10))
                dibujo_chart.add(Rect(450,115,6,6,fillColor=colors.darkgreen))
                dibujo_chart.add(String(457,115,'Procesados',fontSize=10))
            else:  #Reporte Filtrado de acuerdo al mapa
                 dibujo_chart.add(String(185,135,'Estadística de Registros Sísmicos Procesados',fontSize=14))
        dibujo_chart.drawOn(lienzo, 15,68)
        return lienzo

def dibujo_sismos_(lienzo,vector,coordenadas,tamanio,mapa_,bandera_dia,bandera_relleno):
    """
    Metodo para dibujar los sismos en el mapa
    lienzo:   donde se va dibujar
    vector:   donde se encuentran las coordenadas de los eventos
    coordenadas:  variable con las coordenadas del cuadrado en donde se grafica
    tamnio:tamaño del mapa
    mapa_:    mapa escogido
    bandera_dia:  bandera para saver si es reporte diario o de periodo
    """
    longitud_min=coordenadas[0]
    latitud_min=coordenadas[1]
    longitud_max=coordenadas[2]
    latitud_max=coordenadas[3]
    xpos=tamanio[0]
    ypos=tamanio[1]
    ancho=tamanio[2]
    alto=tamanio[3]
    dibujo_sismos = Drawing(ancho, alto)
    aux=len(vector)
    for i in range(0,aux):
        longitud=vector[i][1]
        latitud=vector[i][0]
        profundidad=abs(vector[i][2])
        magnitud=vector[i][3]
        filtro=(longitud<=longitud_max)and(longitud>=longitud_min)and(latitud<=latitud_max)and(latitud>=latitud_min)#Variable que indica si la localizacion está dentro del nmapa de despliegue
        if mapa_==2:#Reporte de Faclutad.
            color=colors.blue
        else: #Todos los otros reportes
            if profundidad>=40:
                if profundidad<=70:
                    color=colors.orange
                else:
                    color=colors.blue
            else:
                color=colors.red
        if filtro: #Si no está dentro del mapa no hace nada.
            if not(vector[i][4]):# Solo ubica los eventos de la RSA(valor 0), ignora los de otras redes(valor 1)
                x_cen=xpos+(longitud-longitud_min)*ancho/(longitud_max-longitud_min)#x_cen=(longitud+80)*200+xpos
                y_cen=ypos+(latitud-latitud_min)*alto/(latitud_max-latitud_min)#y_cen=(latitud+4)*200+ypos
                if mapa_==0: #No entiendo la variable
                    r=1*(magnitud)-2.5
                else:
                    r=2*(magnitud)-5
                char_=str(magnitud)+'/'+vector[i][5][7:9]+':'+vector[i][5][9:11]+':'+vector[i][5][11:13]
                if mapa_==3:# Es el mapa para fuentes.
                    if color!=colors.blue:
                        for k in range(1,10):
                            radio=0.05*k*(2**r)
                            opacidad=(0.1/k)#*(2**r)
                            dibujo_sismos.add(Circle(x_cen, y_cen,radio, fillColor='blue',strokeWidth = 0,fillOpacity=opacidad,strokeOpacity=opacidad))
                            #dibujo_sismos.add(Circle(x_cen, y_cen, radio, strokeWidth=0, fillColor=color, fillOpacity=0.7))
                else:
                    if bandera_relleno:
                        dibujo_sismos.add(Circle(x_cen, y_cen, r, strokeWidth=0, fillColor=color, fillOpacity=0.7))
                    else:
                        dibujo_sismos.add(Circle(x_cen, y_cen, r, strokeColor=color,strokeWidth = 0.2,fillColor=color,fillOpacity=0.))
                    

                if not(bandera_dia):
                    dibujo_sismos.add(String(x_cen+1,y_cen+1, char_, fontSize=4, fillColor=colors.red))
    dibujo_sismos.drawOn(lienzo, 0, 0)#dibujo_sismos.drawOn(c, xpos, ypos)
    return lienzo

def caja_simbologia(lienzo,resumen,vector,ubicacion_caja,mapa_,bandera_dia,bandera_relleno):
    #Linezo    
    #resumen
    #vector
    #coodenadas
    #tamanio
    #mapa_
    #bandera_dia
    pos_x=ubicacion_caja[0]#pos_x=55
    pos_y=ubicacion_caja[1]#pos_y=234

    lienzo.setFont('Helvetica', 11)
    lienzo.drawString(pos_x+105,pos_y+50,"SIMBOLOGIA:")
    lienzo.setFont('Helvetica', 9)
    lienzo.drawString(pos_x+31,pos_y+48,"Magnitud(Md):")
    lienzo.drawString(pos_x+5,pos_y+38,"3.0 - 3.5 - 4.0 - 4.5 - 5.0")
    if mapa_==2:#Reporte a la Facultad
        lienzo.rect(pos_x+240,pos_y,200,64)
        lienzo.rect(pos_x,pos_y,240,64)
        lienzo.drawString(pos_x+105,pos_y+27,"Sismos procesados")
    else:
        lienzo.rect(pos_x+295,pos_y,215,64)
        lienzo.rect(pos_x,pos_y,295,64)
        lienzo.drawString(pos_x+105,pos_y+27,"Sismo superficial, < 40 km.")
        lienzo.drawString(pos_x+105,pos_y+16,"Sismo con profundidad media, de 40 a 70 Km.")
        lienzo.drawString(pos_x+105,pos_y+5,"Sismo profundo, > 70 Km.")
    lienzo.setFont('Helvetica', 11)
    if mapa_<4 or bandera_dia==0:  #Region Ecuador Facultad Fuentes o Reporte diario
        if len(resumen)<3 and mapa_!=3:#Revisar esto, se genera vector en el resumen con Fuentes
            promedio_sismos_localizados=round(resumen[1][1]/(len(resumen)-1),1)
            promedio_sismos_no_localizados=round(resumen[1][2]/(len(resumen)-1),1)
        else:
            promedio_sismos_localizados=round(resumen[1][1]/(len(resumen)-2),1)
            promedio_sismos_no_localizados=round(resumen[1][2]/(len(resumen)-2),1)
        promedio_total=round(promedio_sismos_localizados+promedio_sismos_no_localizados,1)
        if mapa_==2:
            lienzo.drawString(pos_x+280,pos_y+50,"Promedio diario de registros")
            lienzo.drawString(pos_x+250,pos_y+28,"Sismos localizados:    "+str(promedio_sismos_localizados)+" sismos/dia")
            lienzo.drawString(pos_x+250,pos_y+17,"Eventos sin localizar:  "+str(promedio_sismos_no_localizados)+" eventos/dia")
            lienzo.drawString(pos_x+250,pos_y+6,"Total:                         "+str(promedio_total)+" registros/dia")
        else:
            lienzo.drawString(pos_x+340,pos_y+50,"Promedio diario de registros")
            lienzo.drawString(pos_x+305,pos_y+28,"Sismos localizados:    "+str(promedio_sismos_localizados)+" sismos/dia")
            lienzo.drawString(pos_x+305,pos_y+17,"Eventos sin localizar:  "+str(promedio_sismos_no_localizados)+" eventos/dia")
            lienzo.drawString(pos_x+305,pos_y+6,"Total:                         "+str(promedio_total)+" registros/dia")


    else: #Reporte de periodo desde Austro en adelante.
        aux=sum(resumen)
        promedio_sismos_localizados=round(aux/(len(resumen)-2),1)
        lienzo.drawString(pos_x+340,pos_y+50,"Promedio diario de registros")
        lienzo.drawString(pos_x+305,pos_y+28,"Sismos localizados:    "+str(promedio_sismos_localizados)+" sismos/dia")
        lienzo.drawString(pos_x+305,pos_y+6,"Total:                         "+str(aux)+" sismos")
    dibujo_leyenda_sismos = Drawing(300, 60)
    color=[colors.blue,colors.orange,colors.red]
    for i in range(0,5):
        for j in range(0,3):
            if mapa_!=2:
                if mapa_==0:
                    if bandera_relleno:
                        dibujo_leyenda_sismos.add(Circle(i*21, j*12, (i+1)/2., strokeColor=color[j],strokeWidth = 0.2,fillColor=color[j],fillOpacity=0.7))#Dibuja los circulos a la mitad
                    else:
                        dibujo_leyenda_sismos.add(Circle(i*21, j*12, (i+1)/2., strokeColor=color[j],strokeWidth = 0.2,fillColor=color[j],fillOpacity=0.))
                else:
                    if bandera_relleno:
                        dibujo_leyenda_sismos.add(Circle(i*21, j*12, i+1, strokeColor=color[j],strokeWidth = 0.2,fillColor=color[j],fillOpacity=0.7))#Normales los circulos
                    else:
                        dibujo_leyenda_sismos.add(Circle(i*21, j*12, i+1, strokeColor=color[j],strokeWidth = 0.2,fillColor=color[j],fillOpacity=0.))
            else:
                if j==2:
                    dibujo_leyenda_sismos.add(Circle(i*21, j*12, i+1, strokeColor=colors.blue,strokeWidth = 0.2,fillColor=colors.blue,fillOpacity=0.7))#Pone todos azules para la Facultad.
    dibujo_leyenda_sismos.drawOn(lienzo,pos_x+ 9,pos_y+8)
    return lienzo


def formato(marca_agua,tamanio_hoja,titulo, subtitulo,formato_,lienzo): 
    #marca _agua     Localizacionde la marca de agua del logo de la rsa
    #tamanio_hoja    Tamaño de la hoja a imprimir.  No se esta usando
    #titulo          Titulo a imprimir
    #subtitulo       subtitulo a imprimir
    #formato_        Tipo de impresion, 0 reporte sísmico, 1 reporte acelerográfico, 2 reporte Facultad.
    #lienzo          Lienzo donde se imprime el informe
    #retorna:        Lienzo con mas detalles colocados n este método
    cabecera=os.path.join(ruta_proyecto, 'datos','cabecera.emf')
    pie=os.path.join(ruta_proyecto, 'datos','pie.emf')
    logoRSA=os.path.join(ruta_proyecto, 'datos','logoRSA.emf')
    cabecera_1=os.path.join(ruta_proyecto, 'datos','cabecera_1.emf')
    xpos= marca_agua[0]
    ypos= marca_agua[1]
    ancho=marca_agua[2]
    alto=marca_agua[3]
    PAGE_WIDTH  = defaultPageSize[0]#PAGE_WIDTH  = tamanio_hoja[0]#595.2755#
    PAGE_HEIGHT = defaultPageSize[1]# PAGE_HEIGHT = tamanio_hoja[1]#841.8897#
    if formato_==0:
        canvas.Canvas.setPageSize(lienzo, A4)
        lienzo.drawImage(cabecera, 56, 780, 500, 50)# posx, posy, ancho, alto
        lienzo.drawImage(pie, 456, 10, 140, 50)# posx, posy, ancho, alto
        lienzo.drawImage(logoRSA, xpos, ypos, ancho, alto)# posx, posy, ancho, alto=
        lienzo.setFont('Helvetica', 18)
        text_width = stringWidth(titulo,'Helvetica-Bold', 18)
        lienzo.drawString((PAGE_WIDTH - text_width) / 2.0,760,titulo)
        lienzo.setFont('Helvetica', 10)
        text_width = stringWidth(subtitulo,'Helvetica', 10)
        lienzo.drawString((PAGE_WIDTH - text_width) / 2.0,745,subtitulo)
    elif formato_==1:
        canvas.Canvas.setPageSize(lienzo, (landscape(A4)))
        lienzo.drawImage(cabecera_1, 56, 530,750, 50)# posx, posy, ancho, alto
        lienzo.drawImage(pie, 720, 17, 110, 30)# posx, posy, ancho, alto
        lienzo.drawImage(logoRSA, xpos, ypos, ancho, alto)# posx, posy, ancho, alto
        lienzo.setFont('Helvetica', 18)
        text_width = stringWidth(titulo,'Helvetica-Bold', 18)
        lienzo.drawString((PAGE_HEIGHT - text_width) / 2.0,500,titulo)#450
        lienzo.setFont('Helvetica', 11)
        text_width = stringWidth(subtitulo,'Helvetica', 11)
        lienzo.drawString((PAGE_HEIGHT - text_width) / 2.0,495,subtitulo)
    else:
        canvas.Canvas.setPageSize(lienzo, A4)
        lienzo.drawImage(cabecera, 61, 744, 474, 43)# posx, posy, ancho, alto
        lienzo.drawImage(pie, 426, 53, 109, 39)# posx, posy, ancho, alto
        lienzo.drawImage(logoRSA, xpos, ypos, ancho, alto)# posx, posy, ancho, alto
        lienzo.setFillColor('Black')
        lienzo.setFont('Helvetica-Bold', 20)
        lienzo.setFillColor('Gray')
        text_width = stringWidth(titulo,'Helvetica-Bold', 20)
        lienzo.drawString((PAGE_WIDTH - text_width) / 2.0,700,titulo)
        lienzo.setFont('Helvetica', 16)
        text_width = stringWidth(subtitulo,'Helvetica', 16)
        lienzo.drawString((PAGE_WIDTH - text_width) / 2.0,670,subtitulo)
        lienzo.setFillColor('Black')
    return lienzo

def mapa(lienzo,imagen, tamanio, coordenadas,salto,bandera):
    # Metodo que dibuja um mapa del tamaño dada por la variable tamanio dentro de las coordenadas geográficas dadas por la variable corrdenadas, que dibuja las coordenadas 
    # o no de acuerdo a la variable bandera con una escala dada por la variable salto.  Las unidades geográficas están en grados.
    #Lienzo  ------ Imagen de trabajo
    #imagen  ------ Imagen, mas concretamente el mapa, que será dibujado en el lienzo
    #tamanio ------ Tamaño de la imagen, cuatro variables en el sigueinte orden: xpos, ypos, ancho , alto 
    #coordenadas--- Coordenadas límite del mapa o imagen, cuatro variables en el siguiente orden: latitud mínima, longitud minima, latitd maxima, longitud máxima
    #salto -------- Salto de las marcas en el mapa
    #bandera ------ Variable que indica si son dibujados o no las masrcas geográficas en el mapa.
    marca_x=[]
    marca_y=[]
    xpos= tamanio[0]
    ypos= tamanio[1]
    ancho=tamanio[2]
    alto=tamanio[3]
    latitud_min=coordenadas[0]
    longitud_min=coordenadas[1]
    latitud_max=coordenadas[2]
    longitud_max=coordenadas[3]
    lienzo.drawImage(imagen, xpos, ypos, ancho, alto)# posx, posy, ancho, alto
    numero_x=round((latitud_max-latitud_min)/salto,0)
    numero_y=round((longitud_max-longitud_min)/salto,0)
    for i in range(0,int(numero_x)+1):
        valor=round(i*salto+latitud_min,1)
        if salto > 0.2:
            if (valor-int(valor))==0:
                marca_x.append(str(valor))
            else:
                marca_x.append(" ")
        else:
            marca_x.append(str(valor))
    for i in range(0,int(numero_y)+1):
        valor=round(i*salto+longitud_min,1)
        if salto > 0.2:
            if (valor-int(valor))==0:
                marca_y.append(str(valor))
            else:
                marca_y.append(" ")
        else:
            marca_y.append(str(valor))
    intervalo_x=ancho/(len(marca_x)-1)
    intervalo_y=alto/(len(marca_y)-1)
    if bandera :
        d=Drawing(10,10)
        lab=Label()
        lab.angle=90
        lab.setText('Latitud')
        d.add(lab)
        d.drawOn(lienzo, xpos-34,ypos+alto/2-5)
        d=Drawing(10,10)
        lab=Label()
        lab.setText('Longitud')
        d.add(lab)
        d.drawOn(lienzo, xpos+ancho/2-10,ypos-20)        
        lienzo.setFont('Helvetica', 8)
        for i in range(0,len(marca_x)):
        #marcas horizontales
            lienzo.line(xpos+intervalo_x*i,ypos-5,xpos+intervalo_x*i,ypos)
            lienzo.line(xpos+intervalo_x*i,ypos+alto,xpos+intervalo_x*i,ypos+alto+5)
        #Texto Horizontal
            lienzo.drawString(xpos+intervalo_x*i-14,ypos-15,marca_x[i])
            lienzo.drawString(xpos+intervalo_x*i-14,ypos+alto+7,marca_x[i])
        for i in range(0,len(marca_y)):
        #marcas verticales
            lienzo.line(xpos-5,ypos+i*intervalo_y,xpos,ypos+i*intervalo_y)
            lienzo.line(xpos+ancho,ypos+i*intervalo_y,xpos+ancho+5,ypos+i*intervalo_y)
        #Texto Vertical
            lienzo.drawString(xpos-28,ypos+intervalo_y*i-4,marca_y[i])
            lienzo.drawString(xpos+ancho+6,ypos+intervalo_y*i-4,marca_y[i])            
    lienzo.rect(xpos,ypos,ancho,alto) #c.rect(50,200,300,60)
    return lienzo


def reporte_resumen(archivo_pdf, subtitulo,fecha_ini,fecha_fin, catalogo,resumen,mapa_,detalle,banderas,estaciones,directorio,arbol,resumen_responsables,eventos,bandera_relleno):
    # Mètodo que genera el reporte de resumen en pdf, pudiendo ser de un día o un período entero sin restricción del tiempo
    #
    #
    # archivo_pdf ---es el nombre en extención pdf del archivo ejemplo archivo.pdf
    # subtítulo -----variable string que define el subtítulo a imprimir
    # fecha_ini----- inicio del period del reporte
    # fecha_fin------ fecha de fin del reporte, si es diario, este valor es el mismo que fecha_ini
    # catalogo ------catalogo correspodiente al dia o al periodo                             .
    # resumen -------resumen del día o período, tiene dos formatos, el primero es:
    #                [['DIA', 'SISMO', 'FF', 'FC', 'TELESISMOS', 'Evento_local', 'INDEFINIDO', 'Ruido'],
    #                 ['Total:', 36, 44, 42, 15, 20, 44, 19],
    #                 ['2', '3', '2', '0', '1', '13', '6'],
    #                                   .
    #                                   .
    #                                   .
    #                 ['6', '7', '3', '0', '3', '2', '0']]
    #               
    #
    #                el sigueintes  es:
    #               [0 0 2...6]  donde los dos primeros valores son 0 y los sigueintes son el numero total de eventos procesados por día.
    # mapa_----------Varible para escoger el mapa dado por el archivo mapa.csv
    # detalle -------Tipo de mapa    0, 1 y 2 con basico, intermnedio y detallado respectivamente
    # banderas-------
    #                bandera_dia---variable booleanaque habilita o deshabilita el cuadro resumen, permite usar el mismo método para hacer el reporte diario o el de período 
    #                              en el reporte   0  no aparecen el cuadro reesumen ni las horas  1 aparece todo
    #                bandera_reporte
    #                bandera_firma
    #                
    # estaciones---- estaciones involucradas en le reporte diario, si es período este tiene valor de 0
    # directorio---- direcorio base donde se tomará la información de los días del reporte, usado en periodo.
    # arbol--------- base de datos en xml del periodo de reporte
    # resumen_responsables----
    # eventos_dia    Todos los eventos generados en el día.
    #print("Reporte resumen:\n")
    print('Resumen:',resumen)
    bandera_dia=banderas[0]
    bandera_reporte=banderas[1]
    bandera_firma=banderas[2]
    raiz=arbol.getroot()
    datos_estaciones=parametros_estaciones()
    #numero_estacion=datos_estaciones[21]
    tipo_canal=datos_estaciones['SENSOR']
    #nombre_estacion=datos_estaciones[0]
    codigo_estacion=datos_estaciones['CODIGO']
    codigo_estacion[2]='CHAI'
    vector=[] #Vartible que contiene la informacion de la ubicación para graficarla en el mapa resumen:[Coordenada en x,Coordenada en y,Profundidad,Magnitud,red,ruta].red tiene valores de 0 o 1
    for i in range(1,len(catalogo)):
        if catalogo[i]!=[]:
            x=float(catalogo[i][IDX_LATITUD])#Coordenada en x
            y=float(catalogo[i][IDX_LONGITUD])#Coordenada en y
            p=-1*float(catalogo[i][IDX_PROFUNDIDAD])#Profundidad
            mag=float(catalogo[i][IDX_MAGNITUD])#Magnitud
            ruta=catalogo[i][IDX_EVENTO]
            if(catalogo[i][IDX_FUENTE]=="RSA"):
                vector.append([x,y,p,mag,0,ruta])#El penultimo es una bandera, 0=RSA,1 es otras redes
            else:
                vector.append([x,y,p,mag,1,ruta])
    marca_agua=(200, 100, 200, 95)
    xpos=90
    ypos=325
    ancho=400
    alto=400
    tamanio=(xpos,ypos,ancho,alto)
    datos=mapa_configuracion(mapa_,detalle)
    mapa_despliegue=datos[0]
    coordenadas=datos[1]##Longitud mínima, Latitud mínima, Longitud máxima, Latitud máxima
    salto=datos[2]
    estaciones_informe=datos[4]
    titulo_hoja=datos[3]
    bandera_marca=1 #1 imprima marcas, 0 no imprima marcas
    titulo="SISMICIDAD REGIONAL REGISTRADA"
    tamanio_hoja=A4
    maximos_reporte=[]
    lienzo = canvas.Canvas(archivo_pdf,pagesize=A4)
    if not(mapa_==2 or mapa_==4):
        lienzo=formato(marca_agua,tamanio_hoja,titulo,subtitulo,0,lienzo)
        pos_x=55
        pos_y=234

    else:
        tamanio=(81,216,432,432)#xpos,ypos,ancho,alto
        marca_agua=(261, 66, 79, 36)#xpos,ypos,ancho,alto
        lienzo=formato(marca_agua,tamanio_hoja,titulo,subtitulo,2,lienzo)
        pos_x=85
        pos_y=109
    lienzo=mapa(lienzo,mapa_despliegue,tamanio,coordenadas,salto,bandera_marca)
    lienzo=dibujo_sismos_(lienzo,vector,coordenadas,tamanio,mapa_,bandera_dia,bandera_relleno)
    ubicacion_caja=(pos_x,pos_y)
    lienzo=caja_simbologia(lienzo,resumen,vector,ubicacion_caja,mapa_,bandera_dia,bandera_relleno)

        
    ####################################################################
    ####################################################################
    #        REPORTE DE PERIODO
    ####################################################################
    ####################################################################

    ####################################################################
    ####### MAPA RESUMEN
    ####################################################################
        ################################################################
        ##### REPORTE DE PERIODO
        ################################################################
    if bandera_dia:
        #Impresión del resumen diario de eventos procesados a travez de un chart de barras.
        lienzo=estadistica_(lienzo,resumen,fecha_ini,mapa_,bandera_dia)
        ####################################################
        ####SOLO PARA CONTROL INTENO mapa_=1
        ####################################################
        if mapa_==1:
            ####################################################
            ####HORAS LABORADAS
            ####################################################
            #print("Internos:")
            lienzo.showPage()
            lienzo=responsables_tiempos_(lienzo,resumen_responsables)
            ##################################################################
            ####INCREMENTO DEL CALATOLO PARA EVENTOS PROCESADOS SIN EXITO.
            ##################################################################
            if bandera_reporte:
                for evento_dia in eventos:
                    directorios=obtener_directorios(evento_dia[1])
                    archivo_procesamiento=directorio+directorios['archivo_procesamiento']
                    if os.path.exists(archivo_procesamiento):
                        lectura=lectura_archivo(archivo_procesamiento)
                        if len(lectura)==1:
                            #os.remove(archivo_procesamiento)
                            continue
                        evento_buscado=int(evento_dia[1][:6]+evento_dia[1][7:-4])
                        aux=['00000000000000', '2025', '1', '1', '0', '0', '0', '-2.00', '-79.00', '0', 'rms', 'e-x', 'e-y', 'e-0', 'e-z', '0', ' ', 'No procesado', evento_dia[1],' , , ']
                        tamanio_catalogo=len(catalogo)
                        indice=1
                        for i in range(indice,tamanio_catalogo):
                            evento_analizado=int(catalogo[i][IDX_EVENTO][:6]+catalogo[i][IDX_EVENTO][7:-4])
                            if evento_buscado==evento_analizado:
                                break
                            if evento_analizado>evento_buscado:
                                catalogo.insert(i,aux)
                                break
        ####################################################################
        ####### LISTA RESUMEN DE EVENTOS
        ####################################################################
        if not(mapa_==2 or mapa_==4):
            contador1=0
            #             Id año mes día hora min seg lat long prof Mag Fuente Ubicación
            loc_centrada=(73,107,122,140,153, 171,190,220, 245,271, 295, 320,  360)
            localizacion=(46,105,126,142,158, 173,188,212, 239,268, 293, 322,  350)
            marca_agua=(120, 450, 400, 200)
            for evento_catalogo in catalogo:
                if evento_catalogo==[]:
                    continue
                if  evento_catalogo[19]==' ':
                    continue
                if contador1==80:
                    contador1=0
                contador1=contador1+1
                contador2=0
                if contador1==1:
                    lienzo.showPage()
                    lienzo=formato(marca_agua,tamanio_hoja,titulo_hoja,subtitulo,0,lienzo)#0 Portrait  1 Landscape
                    lienzo.setFont('Helvetica', 7)
                if  evento_catalogo[IDX_MAGNITUD]!= 'Mag':
                    if  float(evento_catalogo[IDX_MAGNITUD])>4:
                        lienzo.setFillColor(colors.blue)
                    else:
                        lienzo.setFillColor(colors.black)
                for i in (0,1,2,3,4,5,6,7,8,9,15,17,19):
                    texto=evento_catalogo[i]
                    if contador1==1:
                        lienzo.drawString(loc_centrada[contador2],740-contador1*8,catalogo[0][i])
                    else:
                        if contador2>5 and contador2<9:
                            texto=str(round(float(texto),2))
                        if contador2==10:
                            texto=texto+evento_catalogo[i+1]
                        lienzo.drawString(localizacion[contador2],740-contador1*8,texto)
                    contador2=contador2+1
            archivo_revision=archivo_pdf[:-8]+'revision.csv'
            aux='Tarea 1: Aplicar filtros'

            #####################################################################
            # Generacion del archivo de revisón con los reponsables
            #####################################################################
            
            lista_eventos_revision=[['Tarea 1: Aplicar filtros'],['Tarea 2: Cambiar parámeros de filtros'],
                                    ['Tarea 3: Muy ruidosa para marcar fases'],['Tarea 4: Tiempos de coda similares o iguales en estaciones muy distintas.'],
                                    ['Tarea 5: Muy ruidosa para marcar tiempos de coda'],['Tarea 6: Señal aportante no considerada'],
                                    ['Tarea 7: Tiempo de coda mal marcada'],['Tarea 8: Fase mal marcada'],['Tarea 9: Otra'],
                                     ['Evento','Responsable','Tarea','Especificacion(8: Otra)','Causas','Resuelto','Detalle resolución']]
            for evento_catalogo in catalogo:
                aux=[]
                if evento_catalogo==[]:
                    continue
                if evento_catalogo[0][-1] !='0':
                    continue
                evento_sismico=evento_catalogo[IDX_EVENTO]
                aux.append(evento_sismico)
                hora_evento=int(evento_sismico[-10:-4])
                indice_hora=int(hora_evento/60000)
                if indice_hora==0:
                    indice_hora=1
                archivo=referencia_directorio_completa(evento_sismico)
                directorios=obtener_directorios(archivo)
                archivo_responsable=directorios['archivo_responsables']
                responsables_dia=lectura_archivo(archivo_responsable)

                # Validar antes de usar
                if not responsables_dia or not isinstance(responsables_dia, list) or indice_hora >= len(responsables_dia):
                    aux.append("RSA")  
                else:
                    aux.append(responsables_dia[indice_hora][0])

                lista_eventos_revision.append(aux)
            escritura_archivo(archivo_revision,lista_eventos_revision)
            if contador1>50:
                lienzo.showPage()
                lienzo=formato(marca_agua,tamanio_hoja,titulo_hoja,subtitulo,0,lienzo)#0 Portrait  1 Landscape
                contador1=0
            lienzo.setFont('Helvetica', 10)
            x=100
            y=740-(contador1+20)*8
            if bandera_firma:
                lienzo.drawString(x,y,"Ing. Remigio Guevara ")
            lienzo.drawString(x,y-10,"Red Sísmica del Austro")
        lienzo.showPage()
        ####################################################################
        ####### DETALLE DE EVENTOS
        ####################################################################
        if bandera_reporte and not(mapa_==2 or mapa_==4):  #Esta bandera habilita o no el detalle del reporte, está en el IDE del program reporte eventos.
            print("Se imprime detalle de reporte")

            maximos_reporte=imprimir_catalogo(catalogo,arbol,lienzo,directorio,estaciones_informe,tipo_canal,mapa_,raiz,detalle)
        else:
            print("No se imprime detalle de reporte")

        ####################################################################
        #########   REPORTE DIARIO
        ####################################################################
    else:   
        print("Reporte diario")
        archivo=referencia_directorio_completa(archivo_pdf)
        directorios=obtener_directorios(archivo)
        #Impresión del resumen dea actividades por responsable de procesamiento.
        dibujo_chart = Drawing(400, 200)
        dibujo_chart.add(String(180,155,'Resumen de tiempos responsables:',fontSize=14))
        lista_resp=lectura_archivo(directorios['archivo_responsables'])
        aux=len(lista_resp)
        reportes_sismos=num_reportes(directorios['Directorio_reportes'])
        reportes_acelerogramas=num_reportes(directorios['Directorio_acelerogramas'])
        revision=(360,180,180)
        for i in range(0,aux):
            eventos_reportados=reportes_sismos[i-1]+reportes_acelerogramas[i-1]
            vector=lista_resp[i]
            if i!=0:
                formula=(revision[i-1]+int(vector[2])*60+int(vector[10])*300+int(vector[11])*600+int(vector[12])*1200+eventos_reportados*300)/60
            vector=lista_resp[i][0:9]
            if i==0:
                vector.append("REP.")
                vector.append("t (min)")
            else:
                vector.append(str(eventos_reportados))
                vector.append(str(formula))
            for j in range(0,len(vector)):
                x_coor=105+j*40
                y_coor=135-i*12
                if j==0:
                    x_coor=45
                dibujo_chart.add(String(x_coor,y_coor,vector[j],fontSize=12))
        dibujo_chart.drawOn(lienzo, 15,56)

        #Aqui sería de colocar el reporte en detalle de los eventos diarios, para revisión , guardados en un vector.
        catalogo_dia=[]

        for evento_dia in eventos:
            aux=[]
            if evento_dia[2]=='FF' or evento_dia[2]=='FC':
                aux=['00000000000000', '2025', '1', '1', '0', '0', '0', '-2.00', '-79.00', '0', 'rms', 'e-x', 'e-y', 'e-0', 'e-z', '0', ' ', 'No', evento_dia[1],' , , ']
            
            for catalogo_individual in catalogo:
                if catalogo_individual[IDX_EVENTO]==evento_dia[1]:
                    aux=catalogo_individual
                    catalogo_dia.append(aux)
                    aux=[]

            if aux!=[]:
                catalogo_dia.append(aux)
        print("Es solo reporte diario!!!!!!!!")
        lienzo.showPage()
        maximos_reporte=imprimir_catalogo(catalogo_dia,arbol,lienzo,directorio,estaciones_informe,tipo_canal,mapa_,raiz,detalle)
    lienzo.save()
    return maximos_reporte

def impresion_reporte_sismo(lienzo_archivo, evento_generar, canales, trCanal,bandera_periodo,directorio_trabajo,mapa_escogido):#Bandera 1, imprime el perorte en una hoja, 0 saca el lienzo para sumar un reporte grande.
    # lienzo_archivo------- Nombre del lienzo para continuar graficando o el pdf del archivo pdf para empezar a graficar
    # evento_generar------ Datos del evento en el catalogo, contiene la información de la RSA. otras redes o de eventos no procesados.
    # canales------- Canales a graficar del reporte diario
    # trCanal------- Datos mseed del evento
    # bandera_periodo------- 1 es reporte de periodo , 0 es reporte diario.
    # directorio_trabajo------- Directorio de trabajo.
    #print("Impresion reporte sismo")
    ancho=450#Hay que sacar la proporción adecuada para la ubicación de los eventos. original 350, 3.5 grados
    alto=450#Hay que sacar la proporción adecuada para la ubicación de los eventos. original 350, 3.5 grados
    xpos=(A4[0]-ancho)/2
    ypos=75
    titulo=""
    subtitulo="Las estaciones sismográficas de la Red Sísmica del Austro han registrado el siguiente evento sísmico."
    marca_agua=(120, 550, 400, 200)
    tamanio=(xpos,ypos,ancho,alto)
    reporte=0
    mensaje_1="IGEPN: No reportado"
    mensaje_2=""
    numero_redes=len(evento_generar)
    if evento_generar[0]==[]:
        reporte=1
        if evento_generar[1][IDX_FUENTE]=="IGEPN" :
            mensaje_1="Datos tomados del IGEPN: "
            mensaje_2=""
            if numero_redes==3:
                mensaje_2="Reporte USGS: Mag: "+str(evento_generar[2][IDX_MAGNITUD])+evento_generar[2][IDX_UNIDAD_MAG]+"  Prof: "+str(evento_generar[2][IDX_PROFUNDIDAD])+"  Lat: "+str(evento_generar[2][IDX_LATITUD])+"  Long: "+str(evento_generar[2][IDX_LONGITUD])
        else:
            if numero_redes==3:
                mensaje_1="Datos tomados de la USGS: "
                reporte=2
    else: 
        if numero_redes>1:
            mensaje_1="Reporte IGEPN: Mag: "+str(evento_generar[1][IDX_MAGNITUD])+evento_generar[1][IDX_UNIDAD_MAG]+"  Prof: "+str(evento_generar[1][IDX_PROFUNDIDAD])+"  Lat: "+str(evento_generar[1][IDX_LATITUD])+"  Long: "+str(evento_generar[1][IDX_LONGITUD])
        if numero_redes>2:
            mensaje_2="Reporte USGS: Mag: "+str(evento_generar[2][IDX_MAGNITUD])+evento_generar[2][IDX_UNIDAD_MAG]+"  Prof: "+str(evento_generar[2][IDX_PROFUNDIDAD])+"  Lat: "+str(evento_generar[2][IDX_LATITUD])+"  Long: "+str(evento_generar[2][IDX_LONGITUD])
    id_evento=evento_generar[reporte][IDX_INDICE]
    fuente=evento_generar[reporte][IDX_FUENTE]
    evento=evento_generar[reporte][IDX_EVENTO]
    anio=int(evento_generar[reporte][IDX_ANIO])
    mes=int(evento_generar[reporte][IDX_MES])
    dia=int(evento_generar[reporte][IDX_DIA])
    hora=int(evento_generar[reporte][IDX_HORA])
    minuto=int(evento_generar[reporte][IDX_MINUTO])
    segundo=float(evento_generar[reporte][IDX_SEGUNDO])#Es  el segundo real del evento guardado en los archivos fasthypo
    latitud=float(evento_generar[reporte][IDX_LATITUD])   
    longitud=float(evento_generar[reporte][IDX_LONGITUD])
    profundidad=float(evento_generar[reporte][IDX_PROFUNDIDAD])
    magnitud=float(evento_generar[reporte][IDX_MAGNITUD])
    fecha = QDate(anio, mes, dia)
    hora_ = QTime(hora, minuto, int(segundo))  # Asegúrate de que 'segundo' sea entero
    date_UTM = QDateTime(fecha, hora_)# obtención del año , mes y día en forma individual
    date_UTM_alt=QDateTime(fecha, hora_)#date_UTM_alt=datetime(anio,mes,dia,hora,minuto,segundo)
    date_UTM_alt=date_UTM_alt.toPyDateTime()
    d=date_UTM_alt-timedelta(hours=5)
    date_local=QDateTime(d.year,d.month,d.day,d.hour,d.minute,d.second)
    aux_=extraccion_dato(evento_generar[reporte][IDX_LUGAR],",")
    observaciones_2=" con epicentro "+aux_[0]+","
    if len(aux_)==3:
        observaciones_3=aux_[1]+", "+aux_[2]
    else:
        observaciones_3=aux_[1]
    if profundidad<40:
        observaciones_1=" Sismo superficial,"
    elif profundidad<70:
        observaciones_1=" Sismo de mediana profundidad,"
    else:
        observaciones_1=" Sismo profundo,"
      
    if longitud<0:
        longitud_s="Longitud: "+str(-longitud)+" ° O"
    else:
        longitud_s="Longitud: "+str(longitud)+" ° O"
    if latitud<0:
        latitud_s="Latitud: "+str(-latitud)+" ° S"
    else:
        latitud_s="Latitud: "+str(latitud)+" °N"
    fecha_ev_UTM=date_UTM.toString('dd')+' de '+date_UTM.toString('MMMM')+' de '+date_UTM.toString('yyyy')+' (tiempo UTC) '
    hora_ev_UTM=date_UTM.toString('hh:mm:ss')+' (UTC) '
    fecha_ev_local=date_local.toString('dd')+' de '+date_local.toString('MMMM')+' de '+date_local.toString('yyyy')+' (tiempo local) '
    hora_ev_local=date_local.toString('hh:mm:ss')+' (Local) '

# Mapa principal donde aparece la ubicación del sismo.
    for mapa_ in range(3,-1,-1):#0 Region 1 Ecuador, 2 Austro   3 Elecaustro
        detalle=0   #0 sin detalle, 1 basico    2 Detalle
        datos=mapa_configuracion(mapa_,detalle)
        mapa_despliegue=datos[0]
        coordenadas=datos[1]
        salto=datos[2]
        longitud_min=coordenadas[IDX_LONGITUD_MINIMA]
        latitud_min=coordenadas[IDX_LATITUD_MINIMA]
        longitud_max=coordenadas[IDX_LONGITUD_MAXIMA]
        latitud_max=coordenadas[IDX_LATITUD_MAXIMA]
        if (longitud>longitud_min and longitud<longitud_max) and (latitud>latitud_min and latitud<latitud_max):
            break

    tamanio_hoja=(595.2755,841.8897)
    if bandera_periodo:
        lienzo=lienzo_archivo
    else:
        lienzo = canvas.Canvas(lienzo_archivo,pagesize=A4)
    lienzo=formato(marca_agua,tamanio_hoja,titulo,subtitulo,0,lienzo)

    lienzo=mapa(lienzo,mapa_despliegue, tamanio, coordenadas,salto,1)
    if mapa_escogido==1:#Solo dibuja la cobertura para manejo interno.
        lienzo=grafico_cobertura(lienzo,evento,coordenadas,tamanio,directorio_trabajo)

    lienzo.setFillColor('Black')
    lienzo.setStrokeColor(colors.black)    
    

    if id_evento=='00000000000000':
        if fuente=='No procesado':
            lienzo.setFont('Helvetica', 30)
            lienzo.drawString(200,630,'¡Sin convergencia!')
    else:
        lienzo.setFont('Helvetica', 11)
        lienzo.drawString(70,730,'Fecha:')
        lienzo.drawString(105,730,fecha_ev_UTM)
        lienzo.drawString(105,715,fecha_ev_local)
        lienzo.drawString(70,695,'Hora:')
        lienzo.drawString(105,695,hora_ev_UTM)
        lienzo.drawString(105,680,hora_ev_local)
        lienzo.drawString(70,660,'Localización:')
        lienzo.drawString(135,660,latitud_s)
        lienzo.drawString(135,645,longitud_s)
        lienzo.drawString(70,625,'Profundidad:')
        lienzo.drawString(135,625,str(profundidad)+' Km.')
        lienzo.drawString(70,605,'Magnitud:')
        lienzo.drawString(135,605,str(magnitud)+' Md')
        lienzo.drawString(280,695,'Observaciones:')
        lienzo.drawString(360,695,observaciones_1)
        lienzo.drawString(360,685,observaciones_2)
        lienzo.drawString(360,675,observaciones_3)
        lienzo.drawString(70,585,mensaje_1)
        lienzo.drawString(70,565,mensaje_2)
#Graficos de las señales
        tamanio=(105,180)  #Se define el tamaño del grafico de las señales
        dibujo_seniales=imprimir_seniales(tamanio,canales,trCanal,[],1,0)
        if(longitud<-79):
            dibujo_seniales.drawOn(lienzo, xpos+340, ypos+150)
        else:
            dibujo_seniales.drawOn(lienzo, xpos+5, ypos+150)

#Dibujo de la ubicacion en el mapa grande circulos concentricos
        coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+xpos #coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+xpos
        coor_y=alto*(latitud-latitud_min)/(latitud_max-latitud_min)+ypos #coor_y=alto*(latitud-latitud_min)/(latitud_max-latitud_min)+ypos   
        lienzo.drawString(coor_x-15,coor_y-30,str(evento_generar[reporte][IDX_MAGNITUD])+evento_generar[reporte][IDX_UNIDAD_MAG])
        dibujo_sismo = Drawing(10,10)
        for valores in [(11,0.005),(8.5,0.2),(6,0.8 ),(3.5,1.4),(1,0.5)]:
            dibujo_sismo.add(Circle(0,0,valores[0],strokeColor = colors.red,strokeWidth = valores[1],fillOpacity=0))
        dibujo_sismo.drawOn(lienzo, coor_x, coor_y)

#Dibujo de los intentos en procesamiento

    if mapa_escogido==1:
            directorios=obtener_directorios(evento)
            archivo_procesamiento=directorio_trabajo+directorios['archivo_procesamiento']
            if os.path.exists(archivo_procesamiento):
                intentos=lectura_archivo(archivo_procesamiento)
                bandera_color=0
                for intento in intentos:
                    if bandera_color==0:
                        lienzo.setStrokeColor(colors.blue)
                        radio=4
                    else:
                        lienzo.setStrokeColor(colors.black)
                        radio=2
                    
                    if intento[2]=='Inicio' or intento[2]=='Fallido' or intento[2]== 'Prof.(km)':
                        pass
                    else:
                        if bandera_color==0:
                            lienzo.setStrokeColor(colors.blue)
                            radio=4
                            bandera_color=1
                        else:
                            lienzo.setStrokeColor(colors.black)
                            radio=2
                        
                        latitud=float(intento[4])   
                        longitud=float(intento[5])
                        coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+xpos 
                        coor_y=alto*(latitud-latitud_min)/(latitud_max-latitud_min)+ypos 
                        lienzo.circle(coor_x,coor_y,radio)
#Grafico del mapa pequeño del Ecuador en la parte inferior del reporte.
    if mapa_>1:
        datos=mapa_configuracion(1,0)# 1 Ecuador 0 Sin detalle
        mapa_despliegue=datos[0]
        coordenadas=datos[1]
        salto=datos[2]
        longitud_min=coordenadas[IDX_LONGITUD_MINIMA]
        latitud_min=coordenadas[IDX_LATITUD_MINIMA]
        longitud_max=coordenadas[IDX_LONGITUD_MAXIMA]
        latitud_max=coordenadas[IDX_LATITUD_MAXIMA]
        ancho=140
        alto=140
        ypos=ypos+3
        if(longitud<-79):
            xpos=380 #Izquierda
        else:
            xpos=xpos+5 #Derecha
        tamanio=(xpos,ypos,ancho,alto)
        lienzo=mapa(lienzo,mapa_despliegue, tamanio, coordenadas,salto,0)#mapa(lienzo,imagen, tamanio, coordenadas,salto,bandera)

#Dibujo de la ubicacion en el mapa pequeño
        dibujo = Drawing(5,5)
        dibujo.add(Circle(0,0,3,strokeColor = colors.red,strokeWidth = 2,fillOpacity=0))
        coor_y=alto*(latitud-latitud_min)/(latitud_max-latitud_min)+ypos+3 #coor_y=140*(latitud+5.5)/7+ypos+3  #coor_y=alto*(latitud-latitud_min)/(latitud_max-latitud_min)+ypos
        if(longitud<-79):
            coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+380 #coor_x=140*(longitud+82)/7+380  #coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+xpos
        else:
            coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+xpos+5 #coor_x=140*(longitud+82)/7+xpos+5
        dibujo.drawOn(lienzo, coor_x, coor_y)


    if bandera_periodo:
        return lienzo
    else:
        ###Aqui la impresin de todo sobre los procesos
        lienzo.save()

def impresion_reporte_acelerograma(archivo,trcanal,estacion,datos_sismo,bandera):
    # archivo------- Nombre del pdf del archivo del reporte diario
    # trCanal------- Datos mseed del evento de la estacion correspondiente
    # estacion------ Estacion a graficar del reporte diario
    # datos_sismo--- Catalogo escogido
    # bandera------- 1 es reporte de periodo , 0 es reporte diario.
    maximos=[estacion]
    seniales_ascii=[]
    parametros=parametros_estaciones()
    segundo_real=float(datos_sismo[IDX_SEGUNDO])
    fecha_hora = datetime(int(datos_sismo[IDX_ANIO]),int( datos_sismo[IDX_MES]), int(datos_sismo[IDX_DIA]), int(datos_sismo[IDX_HORA]), int(datos_sismo[IDX_MINUTO]), int(segundo_real), int((segundo_real - int(segundo_real)) * 100))
    latitud=str(datos_sismo[IDX_LATITUD])
    longitud=str(datos_sismo[IDX_LONGITUD])
    profundidad=str(datos_sismo[IDX_PROFUNDIDAD])
    magnitud=str(datos_sismo[IDX_MAGNITUD])+" "+str(datos_sismo[IDX_UNIDAD_MAG])
    fuente=str(datos_sismo[IDX_FUENTE])
    dist_ep=str(round(111*((float(parametros['LATITUD'][estacion])-float(datos_sismo[IDX_LATITUD]))**2+(float(parametros['LONGITUD'][estacion])-float(datos_sismo[IDX_LONGITUD]))**2)**(0.5),2))
    factor=float(parametros['FACTOR_MUL'][estacion]) #Es el factor de multiplicacion para convertirlos en punto flotante.
    lugar=str(datos_sismo[IDX_LUGAR])
    cadena_fecha_hora = fecha_hora.strftime("%Y/%m/%d   %H:%M:%S.%f")
    linea_1="Estacion:"+parametros['NOMBRE'][estacion]+"      Ubicación: Lat:"+parametros['LATITUD'][estacion]+"°  Long:"+parametros['LONGITUD'][estacion]+"°  Alt(msnm):"+parametros['ALTITUD'][estacion]
    if bandera:
        lienzo=archivo
    else:
        lienzo = canvas.Canvas(archivo,pagesize=A4)
        linea_1=linea_1+"    Archivo: "+archivo[-26:-8]+".mseed"+"    Archivo reporte: "+archivo[-21:-3]+"pdf"
    if lugar=="Evento Local o de maniobra":
        linea_3="Datos del :       Fecha             Hora                  Ubicacion:   "
        linea_4="  Evento       "  +cadena_fecha_hora[:-4]+"             "+lugar
    else:
        linea_3="Datos del :       Fecha             Hora        Ubicacion:   Lat.(°)   Long.(°) Prof(Km)     Magn.(U)     -Fuente-    Distancia Epicentral:    Lugar:"
        linea_4="  Evento       "  +cadena_fecha_hora[:-4]+"                      "+latitud+"     "+longitud+"       "+profundidad+"          "+magnitud
        linea_4=linea_4+"         "+fuente+"           "+dist_ep+"                  "+lugar
    marca_agua=(200, 120, 500, 250)
    tamanio_hoja=A4
    
    diccionario_componentes = {
    "XYZ": ("X", "Y", "Z"),
    "LTV": ("LONGITUDINAL", "TRANSVERSAL", "VERTICAL"),
    "ENZ": ("ESTE", "NORTE", "Z" ),
    "TRV": ("TANGENCIAL", "RADIAL", "VERTICAL")
}

    nombre_componentes=diccionario_componentes[parametros["CANAL"]]
    for componente in range(0,3):
#####################################################################
#  Aqui se debe cambiar para corregir el error de los acelerogaramas.       
        
        dato=nombre_componentes[componente]
        dato = dato.ljust(14)

#
#####################################################################

        linea_2="Componente:" + dato 
        lienzo=formato(marca_agua,tamanio_hoja,"","",1,lienzo)
        lienzo.setFont('Helvetica', 10)
        lienzo.drawString(40,520,linea_1)
        lienzo.drawString(40,505,linea_2)
        lienzo.drawString(40,490,linea_3)
        lienzo.drawString(40,475,linea_4)
        tamanio=(400,120)  #Se define el tamaño del grafico de las señales
        drawing,maximo,senial_ascii=imprimir_acelerograma(tamanio,trcanal,componente,factor,bandera)
        seniales_ascii.append(dato)
        seniales_ascii.append(senial_ascii)
        maximos.append(maximo)
        drawing.drawOn(lienzo, 0, 0)
        
        tiempo_inicio,tiempo_inicial,duracion, catNames=obtener_marcas_tiempo(trcanal)
        for k in range(0,3):
            lienzo=marcar_tiempo(lienzo,80,290-k*tamanio[1]*1.2,tiempo_inicio,tamanio[0],duracion,catNames)
        lienzo.showPage()
    canvas.Canvas.setPageSize(lienzo, A4)
    if bandera:
        return lienzo,maximos
    else:
        archivo_csv=archivo[:-3]+'csv'
        guardar_seniales_csv(archivo_csv, seniales_ascii,trcanal[0].stats)
        lienzo.save()

def imprimir_acelerograma(tamanio,trcanal,componente,factor,bandera):
    #tamanio--------- Tamaño del grafico
    #trcanal--------- achivo mseed con la informacion de la estacion 
    #componente------ Componente del acelerograma
    #factor---------- Ganancia para obtener los datos reales del acelerograma, diferenciado en entre estaciones de registro continuo en entero y los ETNA en punto flotante
    #bandera--------- Variable para mostrar o no el grafico en matplotlib de la señal, es para diferenciar un informe detallado o no.  Solo en reportes individuales de acelerogramas.
    ancho=tamanio[0]
    alto=tamanio[1]
    tiempo_inicio,tiempo_inicial,duracion, catNames=obtener_marcas_tiempo(trcanal)
    titulo_=(("Aceleración:   cm/s²      Aceleracion máxima:"," cm/s²"),("Velocidad:  cm/s        Velocidad  máxima:"," cm/s"),("Desplazamiento:   cm     Desplazamiento  máximo:"," cm"))
    drawing = Drawing(ancho,alto)
    N=trcanal[0].stats.npts
    muestreo=trcanal[0].stats.sampling_rate
    # Crear etiquetas de tiempo
    #for i in range(0, int(duracion/10)):
        #catNames.append(str(i*10))
    # Procesar componente específica
    senial_ascii=[]
    for i in range(componente,componente+1):
        # Corrección de señales
        seniales=correccion(trcanal[i],factor)# [aceleración, velocidad, desplazamiento]
        aceleracion=seniales[0]
        senial_ascii.append(aceleracion)
        N=len(aceleracion)
        # Cálculo del espectro de aceleración
        f_max=30
        delta=trcanal[0].stats.delta
        delta_f=1/(N*delta)
        N_valores=int(.1/delta_f)
        N_max=int(N//(muestreo/f_max))
        frec_= [i*delta_f for i in range(N_max)]
        frec_log=[math.log10(val) for val in frec_[N_valores:]]
        y_f = scipy.fft.fft(aceleracion)
        y_f_=(1./N)*2* np.abs(y_f[:N_max]).astype(float)

        if not(bandera):
            # Cálculo del espectro de respuesta
            dt=trcanal[i].stats.delta# Paso temporal del registro (s)
            T, Spa, Spv, Sd, Sa, Sv=espectro_respuesta(aceleracion,dt,1,'')

            fig, ax = plt.subplots()
            ax.set_xscale('log')
            ax.plot(frec_,y_f_)
            ax.set_xlim([0.1, f_max])
            plt.show()
#Inica el grafico en el chart
        label = String(640, 253, 'Frecuencia(Hz)', fontSize=10)
        drawing.add(label)
        label = String(600, 453, 'ESPECTRO DE ACELERACIÓN', fontSize=12) #440
        drawing.add(label)
        label = Label()
        label.setOrigin(495, 380)#340
        label.angle = 90
        label.boxAnchor = 'ne'
        label.setText('Aceleración cm/s²')
        drawing.add(label)
        # Agregar espectro de aceleración al gráfico
        coorx=545
        coory=275
        r = Rect(coorx,  coory, 280, 170,strokeWidth = 1,fillColor=white,fillOpacity=0.6)
        drawing.add(r)
        lp = LinePlot()
        lp.x = coorx
        lp.y = coory
        lp.height = 170
        lp.width = 280
        lp.data = [list(zip(frec_log,y_f_[N_valores:]))]
        lp.lines[0].strokeWidth = 1
        lp.lines[0].symbol = None
        lp.lines[0].strokeColor = colors.blue
        #lp.xValueAxis.setTitle = 'Frecuencia (Hz)'
        #lp.yValueAxis.setTitle = 'Aceleracion (cm/s²)'
        lp.xValueAxis.valueSteps = [-1,-0.699,-0.523,-0.368,-0.301,-0.222,-0.155,-0.097,-0.046,0,0.301,0.477,0.602,0.699,0.778,0.845,0.903,0.954, 1.0,1.301]
        lp.xValueAxis.labelTextFormat = [".1","","","","","","","","","1","","","","","","","","","10",""]#lambda x: str(round(10**x,0))
        lp.xValueAxis.valueMin = -1 # valor mínimo del eje X
        lp.xValueAxis.valueMax = 1.5 # valor máximo del eje X
        lp.yValueAxis.valueMin = 0 # valor mínimo del eje Y
        lp.yValueAxis.valueMax = max(1.2*y_f_) # valor máximo del eje Y
        drawing.add(lp)

        if not(bandera):
            # Agregar espectro de respuesta

            label = String(645, 35, 'Periodo (s)', fontSize=10)
            drawing.add(label)
            label = String(615, 235, 'ESPECTRO DE RESPUESTA', fontSize=12) 
            drawing.add(label)
            label = String(690, 220, 'Factor de Amortiguamiento del 5%', fontSize=9) 
            drawing.add(label)

            label = Label()
            label.setOrigin(500, 190)
            label.angle = 90
            label.boxAnchor = 'ne'
            label.setText('Aceleración (g)')
            drawing.add(label)

        
            coory_espectro = coory - 215  # Espacio adicional para el espectro de respuesta  190
            r_respuesta = Rect(
                coorx, coory_espectro, 280, 170, strokeWidth=1, fillColor=white, fillOpacity=0.6
            )   
            drawing.add(r_respuesta)
            lp_respuesta = LinePlot()
            lp_respuesta.x = coorx
            lp_respuesta.y = coory_espectro
            lp_respuesta.height = 170
            lp_respuesta.width = 280
            lp_respuesta.data = [list(zip(T, Spa))]
            lp_respuesta.lines[0].strokeWidth = 1
            lp_respuesta.lines[0].strokeColor = colors.blue
            lp_respuesta.yValueAxis.valueMax = max(1.1*Spa) # valor máximo del eje Y
            drawing.add(lp_respuesta)

        # Graficar aceleración, velocidad y desplazamiento    
        maximos_componentes=[componente]
        
        for j in range(0,3):
            coorx=80
            coory=340-j*alto*1.2
            r = Rect(coorx,  coory, ancho, alto,strokeWidth = 1,fillColor=white,fillOpacity=0.6)
            drawing.add(r)
            maximo=max(abs(max(seniales[j])),abs(min(seniales[j])))#maximo=max(abs(max(datos[0])),abs(min(datos[0])))
            maximos_componentes.append(maximo)
            max_value=1.1*maximo
            min_value = -max_value
            lab = Label()
            lab.setOrigin(250, coory+alto+6)
            lab.setText(titulo_[j][0]+str(round(maximo,5))+titulo_[j][1])
            lab.dx = 0
            lab.dy = 0
            drawing.add(lab)
            lc = HorizontalLineChart()
            lc.x = coorx
            lc.y =coory
            lc.height = alto
            lc.width = ancho
            lc.data = [seniales[j]]
            lc.joinedLines = 1
            lc.categoryAxis.categoryNames = catNames
            lc.categoryAxis.visible = 0 #Hace invisible el eje x
            lc.valueAxis.visible = 1   #Hace invisible el eje y
            lc.categoryAxis.labels.boxAnchor = 'n'
            lc.valueAxis.valueMin = min_value
            lc.valueAxis.valueMax = max_value
            lc.valueAxis.valueStep = escalado(maximo)
            lc.lines[0].strokeColor = colors.blue
            lc.lines[0].strokeWidth = 0.5
            drawing.add(lc)
            #marcar_tiempo(lienzo,x_,y_,tiempo_inicio,duracion,catNames)
    return drawing,maximos_componentes,senial_ascii   

def mapa_configuracion(mapa_numero, detalle):
    #mapa_numero: numero de mapa para el reporte dado en el archivo mapas.csv  
    #detalle:     Tio de detalla, de basico a detalles
    #retorna:     (nombre_mapa,coordenadas,salto,mapa_escogido[0],estaciones_informe)
    #               nombre_mapa -------- archivo que contiene el mapa a cargar en formato emf
    #               coordenadas -------- coordenadas geograficas del mapa
    #               salto       -------- variable para el escalamiento del mapa
    #               mapa_escogido[0] --- nombre del mapa escogido
    #               estaciones_informe - Estaciones involucradas en el informe.
    archivo = os.path.abspath(os.path.join(ruta_proyecto, 'datos','mapas','mapas.csv'))

    with open(archivo,newline='') as mapas_csv:
        lista_mapas=csv.reader(mapas_csv,delimiter=';',quotechar=';')
        mapa=[]
        for x in lista_mapas:
            if x[0]!='nombre':
                mapa.append(x)
        mapa_escogido=mapa[mapa_numero]
        nombre_mapa=os.path.join(ruta_datos, 'mapas',mapa_escogido[0]+'_'+str(detalle)+'.emf')
        coordenadas=(float(mapa_escogido[3]),float(mapa_escogido[1]),float(mapa_escogido[4]),float(mapa_escogido[2]))#Longitud mínima, Latitud mínima, Longitud máxima, Latitud máxima
        salto=float(mapa_escogido[5])
        estaciones_informe=mapa_escogido[6].split(' ')
        return(nombre_mapa,coordenadas,salto,mapa_escogido[0],estaciones_informe)

def escalado(numero):
    escala=1/(10**int(math.log10(1/numero)))
    if escala<1:
        escala=escala/10
    if numero<escala:
        escala=escala/10
    if numero/escala<2:
        escala=escala/2
    if numero/escala>5:
        escala=escala*2
    return escala
        

def cabecera_(catalogo_escogido):
#Genera la cabecera del reporte pdf
    tamanio=A4#tamanio=(595, 842)
    drawing = Drawing(tamanio)
    latitud=catalogo_escogido[IDX_LATITUD]
    longitud=catalogo_escogido[IDX_LONGITUD]
    profundidad=catalogo_escogido[IDX_PROFUNDIDAD]
    magnitud=catalogo_escogido[IDX_MAGNITUD]
    fecha=catalogo_escogido[IDX_INDICE][:10]
    hora=catalogo_escogido[IDX_INDICE][10:]
    lab0 = Label()
    lab0.setOrigin(500,820)
    lab0.fontSize=20
    lab0.fontName='Helvetica-Bold'
    lab0.boxAnchor = 'ne'
    lab0.textAnchor='middle'
    lab0.setText('RED SÍSMICA DEL AUSTRO'+'\n'+'REGISTRO SISMICO'
                +'\n'+'FECHA: '+fecha+'                 '+'HORA:'+hora)
    drawing.add(lab0)
    lab1 = Label()
    lab1.setOrigin(541,750)
    lab1.fontSize=13
    lab1.fontName='Helvetica-Bold'
    lab1.boxAnchor = 'ne'
    lab1.textAnchor='start'
    lab1.setText('Localización: Lat:'+str(latitud)+'  Long:'+str(longitud)
                +'  Prof.(km):'+str(profundidad)+'  Mag.(Md):'+magnitud)
    drawing.add(lab1)
    return

def imprimir_seniales(tamanio,canales,trcanal,evento,bandera_seniales,bandera_zoom):
# tamanio------------ el tamaño de las señales
# canales------------ cuales canales se imprimiran en forma de una lista de 1 y 0, denominado eventos basico
# trcanal------------ señales mseed a imprimir
# bandera_seniales--- si está en 1 imprime las señales solas para el reporte general, y si es cero los detalles de los informes
# evento------------- Evento completo a desplegar
# bandera_zoom------- si está en 1 imprime el zoom de las señales 

    parametros=parametros_estaciones()
    ancho=tamanio[0]
    alto=tamanio[1]
    dibujo = Drawing(ancho,alto)
    if bandera_seniales:
        r = Rect(0, 0, ancho, alto,strokeWidth = 0.5,fillColor=white,fillOpacity=0.6)    
        dibujo.add(r)
        lab = Label()
        lab.setOrigin(ancho/2, alto-10)
        lab.setText("SEÑALES")
        dibujo.add(lab)
    datos_np = [0] * 101
    #####Obtension de los datos para graficar
    for i in range(0, 101):
        if trcanal[i]!=[] and trcanal[i][0]!=' ':#Es igual a ' ' cuando es la copia del mseed 
            trcanal[i].detrend(type='linear') #Correccion de linea de base

            datos_np[i]=trcanal[i][0].data
    contador=0
    #canales[6]=0#No se que hace esto.
    for i in range (0,NUMERO_ESTACIONES):
        if canales[i]!=0 and trcanal[i]!=[]:
            color_senial=colors.blue
            if trcanal[i][0]==' ':  #CUANDO ES COPIA PARA QUE GENERE EL ESAPACIO EN BLANCO
                contador=contador+1
                continue
            #####Obtension de la referencia de tiempo
            t_inicio=trcanal[i][0].stats.starttime #obtencion de la referencia del tiempo
            duracion=trcanal[i][0].stats.endtime.timestamp-trcanal[i][0].stats.starttime.timestamp
            ######Generacion de las marcas de tiempo para dibujar, esto en catNames
            catNames=[]               
            for j in range(0, int(duracion),10):
                tiempo=t_inicio+timedelta(seconds=j)
                catNames.append(str(tiempo.time.second))
            if not(bandera_seniales):   #######Informe
                x_=0
                y_=alto-(contador+1.8)*(int(alto/6))
                alto_=int(alto/10)
                ancho_=ancho
                if bandera_zoom:
                    alto_=int(alto/20)
                    linea=Line(x_+ancho_/2, y_, x_+ancho_/2, y_+alto_,strokeColor=colors.red,strokeWidth = 0.5)
                r = Rect(x_,y_,ancho_,alto_,strokeWidth = 1,fillColor=white,strokeColor=colors.black,fillOpacity=0.8)
                dibujo.add(r)
                if bandera_zoom:
                    dibujo.add(linea)
            else:                       #######Reporte diario
                x_=0
                y_=alto-(contador+1.8)*(int(alto/6))
                alto_=int(alto/7)
                ancho_=ancho
            datos=[]
            xx=datos_np[i].flatten().tolist()
            datos.append(xx)#Aqui pondría escalameinto a travez del parametro FACTOR_MIL(11) del archivo estaciones.
            max_value = max(datos[0])
            min_value = min(datos[0])
            grafico = HorizontalLineChart()
            grafico.x = x_
            grafico.y = y_
            grafico.height = alto_
            grafico.width = ancho_
            grafico.data = datos
            grafico.joinedLines = 1
            grafico.strokeWidth=0.25
            grafico.categoryAxis.categoryNames = catNames
            grafico.categoryAxis.labels.boxAnchor = 'n'
            grafico.valueAxis.valueMin = min_value
            grafico.valueAxis.valueMax = max_value
            grafico.categoryAxis.visible = 0 
            grafico.valueAxis.visible = 0   
            grafico.lines[0].strokeWidth = 0.5
            if len(evento)==104:
                if int(evento[i+3][5])==0:
                    color_senial=colors.grey
            grafico.lines[0].strokeColor = color_senial
            dibujo.add(grafico)
            lab = Label()
            if bandera_seniales: #Diario
                lab.fontSize=8
                lab.strokeColor = colors.blue
                lab.setOrigin(85, alto-(contador+1.1)*(int(alto/6)))
                lab.setText(parametros['CODIGO'][i])
                dibujo.add(lab)    
            else:
                pass
            contador=contador+1
    return dibujo



def marcar_impresiones(lista_eventos,estaciones_informe,tipo_canal,mapa_):
    #Metodo que obtiene que estaciones se tienen que imprimir en los informes.
    # lista_eventos       lista de estaciones del evento marcado, a partir de la posicion 3
    # estaciones_informe  estaciones van en el informe
    # tipo_canal          tipo de estación, SISMICA O ACELEROGRAFICA
    # eventos_basico      Valor de retorno, lista con marcas de 1 con las señales a imprimir
    eventos_basico=[]
    for k in range(3,len(lista_eventos)):
        var_1=True if lista_eventos[k]!='-' else False  #Marca las estaciones que no esten con "-"
        var_2=True if str(k-3) in estaciones_informe  else False #Marca las estaciones dentro del informe
        if estaciones_informe==['', '']:  #Hay casos en los que se presenta esta forma
            var_2=True
        var_3=True if tipo_canal[k-3]=='ACELEROGRAFICO'  else False  #Marca las estaciones acelerograficas dentro en el archivo base.
        resultado_=(var_1 & ~var_2 & var_3) | (var_1 & var_2 & ~var_3) | (var_1 & var_2 & var_3)
        if resultado_:
            if len(lista_eventos[k])>4:
                if lista_eventos[k][5]=='1':
                    eventos_basico.append(1)
                else:
                    if mapa_==1 and tipo_canal[k-3]=='SISMICO':
                        eventos_basico.append(1)
                    else:
                        eventos_basico.append(0)
            else:
                eventos_basico.append(1)
        else:
            eventos_basico.append(0)
    return eventos_basico

def imprimir_catalogo(catalogo,arbol,lienzo,directorio,estaciones_informe,tipo_canal,mapa_,raiz,detalle):
    #########################################################################################
    #Método que imprime el catalogo completo sea de un día como de un periodo.
    #########################################################################################
    # catalogo           -   Catalogo a imprimir del mismo formato convencional de catalogo
    # arbol              -   Arbol xml de todo el reporte, aqui está toda la información de la base de datos. 
    # lienzo             -   Lienzo, o archivo pdf donde se imprime los diferentes graficos
    # directorio         -   Directorio de trabajo ..\DIA\
    # estaciones_infomre -   estaciones que conformen los informes
    # tipo_canal         -   Tipo de canal
    # mapa_              -   Mapa al cual se va a imprimri
    # raiz               -   base de datos XML
    # detalle            -   Averiguar que no me acuerdo
    #print("Impreimir_catalogo")
    maximos_reporte=[]
    indice=1
    
    while indice<len(catalogo): #Trabaja sobre el catalogo sísmico generado, incluyendo los reportes de otras redes.
        ####################################################################
        #### SISMOGRAMAS
        ####################################################################
        print("Graficando:  ",catalogo[indice][IDX_EVENTO])
        if catalogo[indice]==[]:
            indice=indice+1
            continue
        lienzo.drawString(50,850,'EVENTO: '+catalogo[indice][IDX_EVENTO])
        evento_catalogo=catalogo[indice]  #Variable que tiene la información principal del evento a imprimir, no importa la fuente ni si es reportado o no.
        ayuda=0
        evento_generar=[]   #Uno o mas vectores que tienen los datos para imprimir, sea la RSA, otras redes o los reportados.  Es para montar la información en un solo reporte
        if catalogo[indice][IDX_FUENTE]!='RSA':
            evento_generar.append([])#Si no es de la red, se incrementa un vacio en el generador de de eventos, esto para LA USGS o La IGPEN o los no reportados
            ayuda=1
        evento_generar.append(catalogo[indice])#EL evento a generar se toma del catalogo sísmico.
        evento_catalogo_sis=catalogo[indice][IDX_EVENTO]
        indice_evento=indice
        for j in range(indice+1, len(catalogo)):
            if catalogo[j]==[]:
                continue
            if evento_catalogo_sis==catalogo[j][IDX_EVENTO]:
                evento_generar.append(catalogo[j])
        indice=indice+len(evento_generar)-ayuda
        # En evento _generar se tiene los datos a desplegarse en el reporte, sean de la RSA como de otras redes.
        directorios=obtener_directorios(evento_catalogo_sis)
        archivo_csv=directorio+'/'+directorios['archivo_csv']
        with open(archivo_csv,newline='') as f:
            eventos_dia=csv.reader(f,delimiter=';',quotechar=';')
            for evento in eventos_dia:
                if evento[1]==evento_catalogo_sis:
                    
                    if mapa_==1:
                        #eventos_a_graficar - > marca todas las estaciones con señales mseed
                        eventos_a_graficar=[]
                        for i  in range(0,NUMERO_ESTACIONES):
                            if evento[i+3]!='-':
                                eventos_a_graficar.append(1)
                            else:
                                eventos_a_graficar.append(0)
                    else:
                        #eventos_a_graficar - > marca las estaciones habilitadas en el punto de interés                        
                        eventos_a_graficar=marcar_impresiones(evento,estaciones_informe,tipo_canal,mapa_)
                    break
        
        trCanal=leer_mseed(directorio+directorios['archivo_referencia'],1)
        contador=0
        n=len(eventos_a_graficar)
        pagina_0 = [0] * n
        pagina_1=[]
        paginamiento_estaciones=[]     #paginamiento_estaciones ----- > Variable para poder graficar de 5 en 5 las hojas del pdf.
        for i in range(0,len(eventos_a_graficar)):
            contador=contador+eventos_a_graficar[i]
            pagina_1.append(eventos_a_graficar[i])
            if contador==5:
                contador=0
                pagina_1=pagina_1+pagina_0[i+1:]
                paginamiento_estaciones.append(pagina_1)
                pagina_1=pagina_0[:i+1]
        paginamiento_estaciones.append(pagina_1)
        
        for i in range(0,len(paginamiento_estaciones)):
            pagina=paginamiento_estaciones[i]
            if i==0:
                bandera_primera_hoja=1
            else:
                bandera_primera_hoja=0
            
            
            lienzo=hoja_seniales_(directorio,lienzo,evento_catalogo,evento_generar,evento,pagina,trCanal,raiz,mapa_,detalle,bandera_primera_hoja)
        ####################################################################
        #### ACELEROGRAMAS
        ####################################################################
        eventos_a_graficar=marcar_impresiones(evento,estaciones_informe,tipo_canal,mapa_)
        for i in range(0,len(eventos_a_graficar)):
            catalogo_=convertir_lista(catalogo[indice_evento])
            if trCanal[i]!=[] and tipo_canal[i]=='ACELEROGRAFICO' and eventos_a_graficar[i]:
                lienzo,maximos=impresion_reporte_acelerograma(lienzo,trCanal[i],i,catalogo_,1)#lienzo,maximos
                if maximos!=[]:
                    xxx=[catalogo[indice_evento][IDX_EVENTO]]
                    xxx.append(maximos)
                maximos_reporte.append(xxx)            
    print("Maximos reporte:",maximos_reporte)
    return maximos_reporte


def hoja_seniales_(directorio_trabajo,lienzo,evento_catalogo,evento_generar,evento,pagina,trCanal,raiz,mapa_,detalle,bandera_primera_hoja):
#evento_catalogo:  Evento completo tomado del catalogo
#estaciones_informe: Ver la posiblidad de cargar aqui con mapa configuracion
# evento:    informacion del evento enele formato obtenido de AAMMDD_hhmmss.csv
#pagina:   Informacion en 1 o = de que estestacion se tiene que imprimir
    #print("Hoja señales")
    codigo_evento=('','Nombre','Longitud','Latitd','altura','Ganancia','Filtro','Dist. epicentral: ','    Azimut:','  ain: ','    p-sec: ',' tpcal: ','  p-res: ','  s-sec: ',  's-res: ','  Disparo: ','  Marc.s: ','  t_coda: ')
    unidades_evento=('','','°','°','mts ','dB','Hz.','Km ',' °',' ain',' s ',' tpcal',' s ',' s ',  ' s ',' ','  ',' s')
    datos_estaciones=parametros_estaciones()
    datos_estaciones['CODIGO'][2]='CHAI'
    archivo=evento_catalogo[IDX_EVENTO]
    # En evento _generar se tiene los datos a desplegarse en el reporte, sean de la RSA como de otras redes.
    directorios=obtener_directorios(archivo)
    responsables=lectura_archivo(directorio_trabajo+directorios['archivo_responsables'])
    hora_evento=int(archivo[7:13])
    if hora_evento<120000:
        indice_responsable=1
    elif hora_evento<180000:
        indice_responsable=2
    else:
        indice_responsable=3
    responsable_evento=responsables[indice_responsable][0]        

### SEÑALES
    evento_trabajo = raiz.find(f"./Evento[id_evento='{evento_catalogo[IDX_INDICE]}']")#
    # Convertir el elemento a una cadena XML
    if evento_trabajo!=None:
        valor_rms= evento_trabajo.findtext("rms")
    else:
        valor_rms="__"
    estaciones_vector = []
    estaciones_proceso = []
    if evento_trabajo!=None:
        for estacion in evento_trabajo.iter("estacion"):
            estacion_vector=[]
            for element in estacion.iter():
                estacion_vector.append(element.text)
            estaciones_vector.append(estacion_vector)
            estaciones_proceso.append(estacion_vector[1])


#######################################################################
#Impresion del reporte primera hoja
#######################################################################
    if bandera_primera_hoja and evento_catalogo[IDX_INDICE]!='Id':
        impresion_reporte_sismo(lienzo,evento_generar, pagina,trCanal,1,directorio_trabajo,mapa_)
        lienzo.showPage()
    ### INFORMACION SOBRE LAS SEÑALES
    lienzo.setFont('Helvetica', 12)
    lienzo.drawString(0,850,"Señales")
    tamanio=(500,800)  #Se define el tamaño del grafico de las señales
    eventos_dia=lectura_archivo(directorio_trabajo+directorios['archivo_csv'])
    trCanal_copia = copy.deepcopy(trCanal)
    trCanal_copia_filtrada = copy.deepcopy(trCanal)
    for dato in eventos_dia:
        bandera_seleccion=(dato[2]=='SISMO' or dato[2]=='FF' or dato[2]=='FC')
        if dato[1]==archivo:
            for i in range(0,NUMERO_ESTACIONES):
                if bandera_seleccion:
                    if trCanal[i]!=[]:
                        tiempo_inicio,tiempo_inicial,duracion, catNames=obtener_marcas_tiempo(trCanal[i])
                        estacion=trCanal[i][0].stats.station
                        estacion_completa=dato[i+3]
                        grado_=int(estacion_completa[6:8])
                        freqmin_=int(estacion_completa[8:10])
                        freqmax_=int(estacion_completa[10:12])
                        if grado_!=0:
                                trCanal[i][0].filter("bandpass",freqmin=freqmin_,freqmax=freqmax_,corners=grado_)
                                trCanal_copia_filtrada[i][0].filter("bandpass",freqmin=freqmin_,freqmax=freqmax_,corners=grado_)
                        else:
                                trCanal_copia_filtrada[i]=[]
                                trCanal_copia_filtrada[i].append(' ')
##########################################################################################
#
#Hay que eliminar cuando se tenga la estacion digital CHAN en el campamento base de Chanlud y pasar CHAI a una localizacion fuera de las 16 primeras que esté libre.
#
##########################################################################################
                        if estacion =='CHAN':
                            estacion ='CHAI'
                        try:
                            posicion = estaciones_proceso.index(estacion)
                            fase_p=float(estaciones_vector[posicion][10])
                            
                            if fase_p<tiempo_inicial:
                                tiempo_inicial=tiempo_inicial-60
                            tiempo_p=round(fase_p-tiempo_inicial,2)
                            variacion=int(duracion/40)
                            if tiempo_p < variacion:
                                variacion=tiempo_p
                            tiempo_1=tiempo_p-variacion
                            tiempo_2=tiempo_p+variacion
                            trCanal_copia[i].trim(tiempo_inicio+tiempo_1,tiempo_inicio+tiempo_2)
                            if trCanal_copia_filtrada[i][0]!=' ':
                                trCanal_copia_filtrada[i].trim(tiempo_inicio+tiempo_1,tiempo_inicio+tiempo_2)
                        except ValueError:
                            trCanal_copia[i]=[]
                            trCanal_copia[i].append(' ')
                            trCanal_copia_filtrada[i]=[]
                            trCanal_copia_filtrada[i].append(' ')
                            
                else:
                    trCanal_copia[i]=[]
                    trCanal_copia[i].append(' ')
                    trCanal_copia_filtrada[i]=[]
                    trCanal_copia_filtrada[i].append(' ')
                
######################################################################
######################################################################
#Impresión de las señales, hoja 2 en adelante
######################################################################
###################################################################### 
    drawing=imprimir_seniales(tamanio,pagina,trCanal,evento,0,0)
    drawing.drawOn(lienzo, 50, 50)

######################################################################
#sOLO PARA MANEJO INTERNO DE LA RSA, CON mapa_=1
######################################################################

    if mapa_==1:
######################################################################
#Impresión de las señales zoom
######################################################################
        texto3=''        
        tamanio_=(90,800)
        drawing=imprimir_seniales(tamanio_,pagina,trCanal_copia,evento,0,1)
        drawing.drawOn(lienzo, 460, 90)
        drawing=imprimir_seniales(tamanio_,pagina,trCanal_copia_filtrada,evento,0,1)
        drawing.drawOn(lienzo, 460, 50)

######################################################################
#Texto de cabecera
######################################################################
        texto_adicional= "Evento: "+evento[1]+"   Tipo: "+evento[2]+'  Responsable: '+responsable_evento+'              RMS: '+valor_rms
        lienzo.drawString(20,800,texto_adicional)
######################################################################
#Cabecera de las señales; datos de la estacion en el evento
######################################################################
    contador=0
    for i in range(0,len(pagina)):
        alto=800
        x_=50
        lienzo.setFont('Helvetica', 8)
        if pagina[i] and trCanal[i]!=[]:
            y_=alto-(contador+1.8)*(int(alto/6))
            texto='    Canal '+evento[i+3][4]
            if evento[i+3][6:8]=='00':
                            texto=texto+'   Sin filtro'
            else:
                            texto=texto+'             Filtro  <-> Orden: '+evento[i+3][6:8]+'    f inf: '+evento[i+3][8:10]+' Hz    f sup: '+evento[i+3][10:12]+' Hz'
            lienzo.drawString(x_+10,y_+152,'ESTACION: '+datos_estaciones['NOMBRE'][i]+texto)
            texto1='CODIGO: '+datos_estaciones['CODIGO'][i]+'             LONGITUD:'+datos_estaciones['LONGITUD'][i]+'°    LATITUD:'+datos_estaciones['LATITUD'][i]+'°    ALTURA:'+datos_estaciones['ALTITUD'][i]+'mts'
            texto2=''
            texto3=''
            ubicacion = encontrar_cadena(estaciones_proceso, datos_estaciones['CODIGO'][i])
            tiempo_inicio,tiempo_inicial,duracion, catNames=obtener_marcas_tiempo(trCanal[i])
            if ubicacion != -1:
                fase_p=float(estaciones_vector[ubicacion][10])
                fase_s=float(estaciones_vector[ubicacion][13])
                coda_=estaciones_vector[ubicacion][17]
                try:
                    coda_=float(coda_)
                except ValueError:
                    coda_=0
                if fase_p<tiempo_inicial:
                    tiempo_inicial=tiempo_inicial-60
                tiempo_p=fase_p-tiempo_inicial
                tiempo_s=fase_s-tiempo_inicial
                tiempo_c=tiempo_p+coda_
                valores=(7,8,10,13,15,16,17)
                for j in valores:
                    texto2=texto2+codigo_evento[j]+estaciones_vector[ubicacion][j]+unidades_evento[j]
                texto3=''
                try:
                    tiempo_p_s=round(float(estaciones_vector[ubicacion][13])-float(estaciones_vector[ubicacion][10]),2)
                    if tiempo_p_s>0:
                        texto3="Tiempo P-S:"+str(tiempo_p_s)+"s"
                    else:
                        texto3="Tiempo P-S: No hay marca S"
                except ValueError:
                    texto3=''

#####################################################
##### Dibujo de las lineas de fases
#####################################################
                if mapa_==1:
                    lienzo.setStrokeColor(colors.red)
                    y_start = y_+130
                    y_end = y_+50
                    lienzo.setLineWidth(0.5)
                    x_position = (x_)+tamanio[0]*tiempo_p/duracion  # Cambia esta posición para ajustar la ubicación de la línea vertical
                    lienzo.line(x_position, y_start, x_position, y_end)
                    if fase_s!=0:
                        x_position = (x_)+tamanio[0]*tiempo_s/duracion  # Cambia esta posición para ajustar la ubicación de la línea vertical
                        lienzo.line(x_position, y_start, x_position, y_end)
                    if coda_!=0:
                        x_position = (x_)+tamanio[0]*tiempo_c/duracion  # Cambia esta posición para ajustar la ubicación de la línea vertical
                        lienzo.line(x_position, y_start, x_position, y_end)
                    lienzo.setStrokeColor(colors.black)
                    lienzo.setLineWidth(1)
            else:
                texto2='Estacion no procesada'
            lienzo.drawString(x_+300,y_+120,texto3)
            lienzo.drawString(x_+10,y_+136,texto2)
            lienzo.drawString(x_+10,y_+144,texto1)
            lienzo=marcar_tiempo(lienzo,x_,y_,tiempo_inicio,tamanio[0],duracion,catNames)
            contador=contador+1
    lienzo.showPage()
    return lienzo

def grafico_cobertura(lienzo,evento,coordenadas,tamanio,directorio_trabajo):
    # Función de transformación de coordenadas geográficas a las coordenadas del lienzolienzo
    def transformar_coordenadas(coordenadas,tamanio,lon, lat):
        """ Convierte coordenadas geográficas en coordenadas del lienzo """
        x_escala = (lon - coordenadas[IDX_LONGITUD_MINIMA]) / (coordenadas[IDX_LONGITUD_MAXIMA]- coordenadas[IDX_LONGITUD_MINIMA])
        y_escala = (lat - coordenadas[IDX_LATITUD_MINIMA]) / (coordenadas[IDX_LATITUD_MAXIMA] - coordenadas[IDX_LATITUD_MINIMA])

        x_canvas = tamanio[IDX_POSICION_X] + x_escala * tamanio[IDX_ANCHO]
        y_canvas = tamanio[IDX_POSICION_Y] + y_escala * tamanio[IDX_ALTO]  

        return x_canvas, y_canvas


    def dibujo_poligono(lienzo, distancia, color):
        
        # Obtener el polígono de cobertura como un objeto de GeoPandas
        poligono,estaciones = cobertura_red(archivo_estaciones, distancia)  

        if poligono is None or poligono.empty:
            return lienzo  # Si no hay datos, no se grafica nada

        # Extraer coordenadas del polígono
        geometria = poligono.geometry.iloc[0]  # Extraer la primera (y única) geometría
        if geometria.geom_type != 'Polygon':
            return lienzo  # Si no es un polígono, no continuamos

        # Obtener los vértices del polígono
        vertices = list(geometria.exterior.coords)

        # Transformar todos los puntos del polígono a coordenadas del lienzo
        puntos_transformados = [transformar_coordenadas(coordenadas,tamanio,lon, lat) for lon, lat in vertices]

        # Dibujar el polígono con la API de paths en ReportLab
        path = lienzo.beginPath()
        path.moveTo(*puntos_transformados[0])  # Mover al primer punto

        for punto in puntos_transformados[1:]:  # Dibujar líneas a los otros puntos
            path.lineTo(*punto)
        path.close()  # Cerrar el polígono
        lienzo.setStrokeColor(color)
        lienzo.setLineWidth(1)
        lienzo.drawPath(path, stroke=1, fill=0)  # Dibuja el polígono sin relleno
        lienzo.setStrokeColor(colors.black)
        return lienzo,estaciones
    # Obtener directorios y archivo de estaciones
    directorios = obtener_directorios(evento)
    archivo_estaciones = directorio_trabajo + directorios['archivo_estaciones'] 

 
    lienzo,estaciones =dibujo_poligono(lienzo, 150, colors.greenyellow)
    lienzo,estaciones =dibujo_poligono(lienzo, 50,colors.red)
    

    # **Dibujar las estaciones como puntos rojos**
    lienzo.setFillColor(colors.blue)
    radio_punto = 3  # Tamaño del punto

    for estacion in estaciones:
        x_geo, y_geo = estacion  # Extraer coordenadas
        x_canvas, y_canvas = transformar_coordenadas(coordenadas,tamanio,x_geo, y_geo)  # Convertir a lienzo
        lienzo.circle(x_canvas, y_canvas, radio_punto, stroke=1, fill=1)  # Dibujar punto
    lienzo.setStrokeColor(colors.black)
    return lienzo




