"""
impresion_reporte_sismo ok
impresion_reporte_acelerograma ok
cabecera_ ok
hoja_seniales_ ok

from rsa_reportes_pdf import impresion_reporte_sismo ,impresion_reporte_acelerograma,cabecera_,hoja_seniales_

"""

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



from rsa_io import lectura_archivo

from rsa_pdf_graficos import (mapa_configuracion,formato,mapa,grafico_cobertura,
                              imprimir_seniales,imprimir_acelerograma,obtener_marcas_tiempo,
                              marcar_tiempo,encontrar_cadena)

#from rsa_graficos_pdf import *
#from rsa_reportes_pdf import *
#from rsa_catalogo_pdf import *


from metodos_rsa import extraccion_dato,guardar_seniales_csv
from metodos_gestion import parametros_estaciones,obtener_directorios
from PyQt5.QtCore import QTime,QDate,QDateTime
from datetime import datetime,  timedelta
from reportlab.lib import colors
from reportlab.graphics.charts.textlabels import Label
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, Circle
import copy


IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19

NUMERO_ESTACIONES=101

IDX_LONGITUD_MINIMA,IDX_LATITUD_MINIMA,IDX_LONGITUD_MAXIMA,IDX_LATITUD_MAXIMA=0,1,2,3
IDX_POSICION_X,IDX_POSICION_Y,IDX_ANCHO,IDX_ALTO,=0,1,2,3

# =========================
#  MODOS DE REPORTE (1–7)
# =========================
MODO_PERIODO_FRANJAS          = 1   # M1 – Período por franjas (00–12, 12–18, 18–24) – Control interno
MODO_DIARIO_REVISION          = 2   # M2 – Diario de revisión (día/ad-hoc) con detalle y dummies locales
MODO_OFICIAL_DETALLADO        = 3   # M3 – Oficial detallado (solo catálogo) + página/resumen de responsables
MODO_OFICIAL_RESUMEN          = 4   # M4 – Oficial resumen (solo catálogo, sin detalle)
MODO_FACULTAD_RESUMEN         = 5   # M5 – Facultad/resumen (redes sociales), sin detalle
MODO_INSTITUCIONAL_DETALLADO  = 6   # M6 – Institucional detallado (solo catálogo), sin extras ni responsables
MODO_INSTITUCIONAL_RESUMEN    = 7   # M7 – Institucional, sin detalle

def impresion_reporte_sismo(lienzo_archivo, evento_generar, canales, trCanal,bandera_periodo,directorio_trabajo,mapa_escogido):#Bandera 1, imprime el perorte en una hoja, 0 saca el lienzo para sumar un reporte grande.
    # lienzo_archivo------- Nombre del lienzo para continuar graficando o el pdf del archivo pdf para empezar a graficar
    # evento_generar------ Datos del evento en el catalogo, contiene la información de la RSA. otras redes o de eventos no procesados.
    # canales------- Canales a graficar del reporte diario
    # trCanal------- Datos mseed del evento
    # bandera_periodo------- 1 es reporte de periodo , 0 es reporte diario.
    # directorio_trabajo------- Directorio de trabajo.

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
    evento=evento_generar[reporte][IDX_EVENTO]
    directorios=obtener_directorios(evento)
    archivo_procesamiento=os.path.join(directorio_trabajo, directorios['archivo_procesamiento'])
    existe_proc = os.path.exists(archivo_procesamiento)  # solo para el bloque de "intentos"
    hay_rsa = any(f and f[IDX_FUENTE]=='RSA' for f in evento_generar)
    forzar_sin_convergencia = (not hay_rsa) and existe_proc
    if forzar_sin_convergencia:
        idx_np = next((i for i,f in enumerate(evento_generar) if f and f[IDX_FUENTE]=='No procesado'), None)
        if idx_np is not None:
            reporte = idx_np
            evento = evento_generar[reporte][IDX_EVENTO]
            directorios = obtener_directorios(evento)
            archivo_procesamiento = os.path.join(directorio_trabajo, directorios['archivo_procesamiento'])
            existe_proc = os.path.exists(archivo_procesamiento)
    id_evento=evento_generar[reporte][IDX_INDICE]
    fuente=evento_generar[reporte][IDX_FUENTE]
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
    elif len(aux_)==2:
        observaciones_3=aux_[1]
    else:
        observaciones_3=''

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

   # === Cabecera de portada

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

    if mapa_escogido==1 and existe_proc:
        intentos=lectura_archivo(archivo_procesamiento)
        bandera_color=0
        for intento in intentos:
            if intento[2] in ('Inicio','Fallido','Prof.(km)'):
                continue
            if bandera_color==0:
                lienzo.setStrokeColor(colors.blue); radio=4; bandera_color=1
            else:
                lienzo.setStrokeColor(colors.black); radio=2
            latitud=float(intento[4]); longitud=float(intento[5])
            cx=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+xpos
            cy=alto*(latitud-latitud_min)/(latitud_max-latitud_min)+ypos
            lienzo.circle(cx,cy,radio)
    

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
        xpos=380 if (longitud<-79) else xpos+5
        
        tamanio=(xpos,ypos,ancho,alto)
        lienzo=mapa(lienzo,mapa_despliegue, tamanio, coordenadas,salto,0)#mapa(lienzo,imagen, tamanio, coordenadas,salto,bandera)

#Dibujo de la ubicacion en el mapa pequeño
        dibujo = Drawing(5,5)
        dibujo.add(Circle(0,0,3,strokeColor = colors.red,strokeWidth = 2,fillOpacity=0))
        coor_y=alto*(latitud-latitud_min)/(latitud_max-latitud_min)+ypos+3 #coor_y=140*(latitud+5.5)/7+ypos+3  #coor_y=alto*(latitud-latitud_min)/(latitud_max-latitud_min)+ypos

        #if(longitud<-79):
        #    coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+380 #coor_x=140*(longitud+82)/7+380  #coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+xpos
        #else:
        #    coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+xpos+5 #coor_x=140*(longitud+82)/7+xpos+5
        coor_x=ancho*(longitud-longitud_min)/(longitud_max-longitud_min)+(380 if (longitud<-79) else xpos+5)
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

    nombre_componentes=diccionario_componentes[parametros["CANAL"][estacion]]
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



def hoja_seniales_(directorio_trabajo,lienzo,evento_catalogo,evento_generar,evento,pagina,trCanal,raiz,mapa_,detalle,bandera_primera_hoja):
#evento_catalogo:  Evento completo tomado del catalogo
#estaciones_informe: Ver la posiblidad de cargar aqui con mapa configuracion
# evento:    informacion del evento enele formato obtenido de AAMMDD_hhmmss.csv
#pagina:   Informacion en 1 o = de que estestacion se tiene que imprimir
    codigo_evento=('','Nombre','Longitud','Latitd','altura','Ganancia','Filtro','Dist. epicentral: ','    Azimut:','  ain: ','    p-sec: ',' tpcal: ','  p-res: ','  s-sec: ',  's-res: ','  Disparo: ','  Marc.s: ','  t_coda: ')
    unidades_evento=('','','°','°','mts ','dB','Hz.','Km ',' °',' ain',' s ',' tpcal',' s ',' s ',  ' s ',' ','  ',' s')
    datos_estaciones=parametros_estaciones()
    datos_estaciones['CODIGO'][2]='CHAI'
    archivo=evento_catalogo[IDX_EVENTO]
    # En evento _generar se tiene los datos a desplegarse en el reporte, sean de la RSA como de otras redes.
    directorios=obtener_directorios(archivo)
    responsables=lectura_archivo(directorio_trabajo+directorios['archivo_responsables'])
    hora_evento = int(archivo.split('_')[1].split('.')[0])
    if hora_evento<120000:
        indice_responsable=1
    elif hora_evento<180000:
        indice_responsable=2
    else:
        indice_responsable=3
    responsable_evento=responsables[indice_responsable][0]        

# ==== XML (para RMS y marcas)
    evento_trabajo = raiz.find(f"./Evento[id_evento='{evento_catalogo[IDX_INDICE]}']")#
    # Convertir el elemento a una cadena XML
    valor_rms = evento_trabajo.findtext("rms") if evento_trabajo is not None else "__"
    estaciones_vector,estaciones_proceso = [],[]

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

    # ==== PORTADA (mapa y cabecera) solo si corresponde
    if bandera_primera_hoja:
        # (a) ¿existe alguna fila con índice real?
        hay_indice_real = any(
            fila and len(fila) > IDX_INDICE and fila[IDX_INDICE] != '00000000000000'
            for fila in evento_generar
            )
        # (b) ¿hay intentos de procesamiento en disco?
        archivo_proc = os.path.join(directorio_trabajo, directorios['archivo_procesamiento'])
        hay_intentos = os.path.exists(archivo_proc)

        # Imprime portada si: hay datos reales  o  hubo intentos (mostrar "¡Sin convergencia!")
        if hay_indice_real or hay_intentos:
            lienzo = impresion_reporte_sismo(lienzo, evento_generar, pagina, trCanal, 1, directorio_trabajo, mapa_)
            lienzo.showPage()


    ### INFORMACION SOBRE LAS SEÑALES
    lienzo.setFont('Helvetica', 12)
    lienzo.drawString(0,850,"Señales")
    tamanio=(500,800)  #Se define el tamaño del grafico de las señales
    eventos_dia=lectura_archivo(directorio_trabajo+directorios['archivo_csv'])
    trCanal_copia = copy.deepcopy(trCanal)
    trCanal_copia_filtrada = copy.deepcopy(trCanal)
    for dato in eventos_dia:
        bandera_seleccion=(dato[2] in ('SISMO','FF','FC'))
        if dato[1]==archivo:
            for i in range(0,NUMERO_ESTACIONES):
                if bandera_seleccion:
                    if trCanal[i]!=[]:
                        tiempo_inicio,tiempo_inicial,duracion, catNames=obtener_marcas_tiempo(trCanal[i])
                        estacion=trCanal[i][0].stats.station
                        estacion_completa=dato[i+3]
                        try:
                            grado_=int(estacion_completa[6:8])
                            freqmin_=int(estacion_completa[8:10])
                            freqmax_=int(estacion_completa[10:12])
                        except ValueError:
                            grado_=0
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
        #texto3=''        
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




