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
ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src','ui'))
# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)


from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QMessageBox, QCheckBox)
from PyQt5 import uic
from metodos_rsa import (obtencion_hora,leer_mseed,grafico_evento_int,lectura_archivo,
                         escritura_archivo,filtro_evento,extraer_dia)

from metodos_gestion import lectura_eventos,parametros_estaciones,obtener_directorios,VentanaProgreso
import struct
datos_sismo={}
import copy
from PyQt5.QtWidgets import (QDialog,QSpinBox)


from datetime import datetime
from PyQt5.QtCore import QDate
import csv
import os
datos_sismo={}
#import obspy.realtime #obspy.realtime.signal.offset
import os
import gc
#from obspy import read, UTCDateTime
from obspy import Stream
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer

import matplotlib.pyplot as plt





class Extraer_evento(QMainWindow):
    cerrado = pyqtSignal()  # señal que se emitire al cerrar
    def __init__(self, archivo, directorio_trabajo, responsable, periodo,parent=None):
        super().__init__(parent)
        print("Entrando a subprograma estraer eventos")

        self.directorio_trabajo = directorio_trabajo
        self.responsable=responsable
        self.archivo=archivo
        self.periodo=periodo
        self.setWindowTitle('Extraer Eventos')
        # Configurar el layout principal
        layout_principal = QHBoxLayout()
        # Panel izquierdo
        panel_izquierdo = QVBoxLayout()
        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        
        extrar_ui=os.path.join(ruta_ui,'Extraer.ui')
        uic.loadUi(extrar_ui, self)
        # Añadir la interfaz cargada al panel izquierdo
        panel_izquierdo.addWidget(self.centralWidget())  # Ahora centralWidget es la UI cargada
        layout_principal.addLayout(panel_izquierdo, 1)
        # Panel derecho (gráfico)
        panel_derecho = QVBoxLayout()
        self.visor = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.visor)
        panel_derecho.addWidget(self.canvas)
        layout_principal.addLayout(panel_derecho, 4)
        # Establecer el layout principal en el widget central
        widget_central = QWidget()
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)
        self.setWindowTitle("EXTRACCION DE EVENTOS")
        self.Btn_eventos.clicked.connect(self.cargar_eventos)
        self.Btn_filtrar.clicked.connect(self.filtrar_evento)
        #self.Btn_guardar.clicked.connect(self.testeo_botones)
        self.Btn_guardar.clicked.connect(self.guardar_evento)
        self.Btn_recargar.clicked.connect(self.recargar_evento)
        self.Btn_extraer_fijo.clicked.connect(self.cargar_eventos_fijo)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_pagina.clicked.connect(self.cambio_pagina)
        self.Btn_estaciones.clicked.connect(self.verificar_estaciones)
        self.btn_cortar.clicked.connect(self.cortar_evento)
        self.btn_m_6.clicked.connect(self.mas_6_minutos)
        self.btn_p_6.clicked.connect(self.menos_6_minutos)
        self.btn_p__.clicked.connect(self.mas_2_segundos)
        self.btn_p__1.clicked.connect(self.mas_10_segundos)
        self.btn_p__2.clicked.connect(self.mas_30_segundos)
        self.btn_m__.clicked.connect(self.menos_2_segundos)
        self.btn_m__1.clicked.connect(self.menos_10_segundos)
        self.btn_m__2.clicked.connect(self.menos_30_segundos)
        self.btn_m_3.clicked.connect(self.menos_3_minutos)
        self.btn_m_1.clicked.connect(self.menos_1_minutos)
        self.btn_m_0_5.clicked.connect(self.menos_0_5_minutos)
        self.btn_m_0_2.clicked.connect(self.menos_0_2_minutos)
        self.btn_p_3_0.clicked.connect(self.mas_3_minutos)
        self.btn_p_1_0.clicked.connect(self.mas_1_minutos)
        self.btn_p_0_5.clicked.connect(self.mas_0_5_minutos)
        self.btn_p_0_2.clicked.connect(self.mas_0_2_minutos)
        self.cmbx_eventos.activated[str].connect(self.lista_eventos) 
        self.sp_Box_finf.valueChanged.connect(self.lista_filtros)
        self.sp_Box_fsup.valueChanged.connect(self.lista_filtros)
        self.sp_Box_orden.valueChanged.connect(self.lista_filtros)
        for i in range(0,60):
            self.comboBox_minuto.addItem(str(i))
            self.comboBox_segundo.addItem(str(i))
            if i<24:
                self.comboBox_hora.addItem(str(i))
        lista_filtros = ["Ruido", "FF", "FC","TELESISMO","SISMO","INDEFINIDO","Evento_local","CONTROL"]
        self.Cmb_bx_tipo_evento.addItems(lista_filtros)
        self.parametros=parametros_estaciones()#(nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
        self.hab_grafico=self.parametros['HAB_GRAFICO']
        self.pagina=0
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.Abrir_archivo()
        self.estaciones_eventos=[]
        self.filtros_estaciones=[]
        self.bandera_marcas=1


############################################################
# Médtodo que carga la lista de eventos generados en el archivo puntos.csv
# en el directorio del día procesado.
# EL método lectura_eventos(archivo) da como resultado la lista
    def Abrir_archivo(self):  #Depurado
        
        self.directorios=obtener_directorios(self.archivo)
        self.directorio=self.directorios['Directorio_base']
        self.directorio_dia=self.directorios['Directorio_dia']
        self.directorio_eventos=self.directorios['Directorio_eventos']
        self.directorio_registros=self.directorios['Directorio_registros']
        self.fecha_=obtencion_hora(self.archivo) 
        self.eventos_auxiliar=lectura_archivo(self.directorios['archivo_auxiliar'])
        resultado=lectura_eventos(self.archivo)
        mensaje=resultado[0]
        self.hora_sismos=resultado[1]
        if self.hora_sismos!=0:
            self.cargar_lista_eventos()
            self.grupo_carga.setEnabled(True)
            self.grupo_hora_especifica.setEnabled(True)
            self.grupo_evento.setEnabled(False)
            self.Lbl_Mensajes.setText("Actual: Marca 1. ")               
        self.Lbl_Mensajes_2.setText(mensaje)
        self.lectura_mseed_dia = self.filtrar_streams_invalidos(leer_mseed(self.archivo, 0))

    def cargar_lista_eventos(self):
            from PyQt5 import QtCore
            indice_actual = self.cmbx_eventos.currentIndex()
            self.cmbx_eventos.clear() 
            
            self.hora_sismos_extraidos = [
                 int(fila[8]) for fila in self.eventos_auxiliar
                 if len(fila) > 8 and fila[8] != 'Caudales'
                 ]   
            for i in range(0,len(self.hora_sismos)):
                h=self.hora_sismos[i]/(64*3600)
                h_s=str(int(h))
                if int(h)<10:
                    h_s="0"+h_s
                m=(h-int(h))*60
                m_s=str(int(m))
                if int(m)<10:
                    m_s="0"+m_s
                s=int((m-int(m))*60)
                s_s=str(s)
                if s<10:
                    s_s="0"+s_s
                etiqueta = "Marca " + str(i + 1) + ":   " + h_s + ":" + m_s + ":" + s_s
                self.cmbx_eventos.addItem(etiqueta)
                if self.hora_sismos[i] in self.hora_sismos_extraidos:
                    self.cmbx_eventos.setItemData(i, False, QtCore.Qt.UserRole - 1)
           
            self.cmbx_eventos.setCurrentIndex(indice_actual)

    def filtrar_streams_invalidos(self, lista_streams):
        """
        Filtra una lista de objetos Stream, conservando la estructura,
        y descartando aquellos que están vacíos, tienen NaN o son inválidos.

        :param lista_streams: Lista original de Streams o [].
        :return: Lista de la misma longitud con Streams válidos o [].
        """
        from obspy import Stream
        import numpy as np

        lista_filtrada = []
        for i, stream in enumerate(lista_streams):
            if isinstance(stream, Stream) and len(stream) > 0 and len(stream[0].data) > 0:
                try:
                    # Verificamos que los datos no tengan NaN
                    if not np.isnan(stream[0].data).any():
                        lista_filtrada.append(stream)
                    else:
                        print(f"[Descartado] Canal {i} con NaN en los datos")
                        lista_filtrada.append([])
                except Exception as e:
                    print(f"[Descartado] Canal {i} inválido: {e}")
                    lista_filtrada.append([])
            else:
                lista_filtrada.append([])  # Mantener estructura
        return lista_filtrada

    def copiar_stream_dia__(self):
        """Liberar completamente la memoria anterior antes de copiar"""
        print("Copiando el stream del dia")
    
        # PASO 1: Liberar streams individuales ANTES de eliminar la lista
        if hasattr(self, 'trCanal') and self.trCanal:
            for stream in self.trCanal:
                if isinstance(stream, Stream):
                    try:
                        stream.clear()  # Limpiar datos internos del stream
                    except:
                        pass
                del stream  # Eliminar referencia individual
            self.trCanal.clear()  # Limpiar lista
            del self.trCanal      # Eliminar lista
        # PASO 2: Forzar recolección DESPUÉS de eliminar referencias
        gc.collect()
        # PASO 3: Ahora crear nueva copia
        self.trCanal = []
        for idx, stream in enumerate(self.lectura_mseed_dia):
            if isinstance(stream, Stream):
                try:
                    copia = stream.copy()
                    self.trCanal.append(copia)
                except Exception as e:
                    print(f"⚠️ Error copiando stream en posición {idx}: {e}")
                    self.trCanal.append([])
            else:
                self.trCanal.append([])

    def guardar_evento(self):
        try:
            with open(self.directorios['archivo_auxiliar'], 'w', encoding='utf-8') as file:
                # escribir normalmente
                pass
        except PermissionError as e:
            print("Archivo ocupado:", e)
        except Exception as e:
            print("Otro error:", e)
        self.visor_limpiar_completo()
        bandera_ajuste=0
        if self.chkBx_ajuste.checkState()==2:
            bandera_ajuste=1
        n_evento = self.cmbx_eventos.currentIndex() + 1
        tipo_evento = self.Cmb_bx_tipo_evento.currentText()
        fecha_real = self.tiempo + self.t_inicio  # Usado solo para generar nombre
        nombre_sis = fecha_real.strftime('%Y%m%d_%H%M%S.sis')
        ahora = datetime.now()
        estaciones=""
        for i,n_estacion in enumerate(self.estaciones_eventos_total):
            indice=int(n_estacion)
            aporta="0"
            if n_estacion in self.estaciones_eventos:
                aporta="1"
            estacion=self.parametros['CODIGO'][indice]+self.parametros['COMPONENTE'][indice]+aporta+self.filtros_estaciones[i]+" "
            estaciones=estaciones+estacion
        evento_auxiliar=(n_evento,nombre_sis,tipo_evento,ahora, self.t_inicio, self.t_final,self.responsable,estaciones,self.hora_sismos[self.cmbx_eventos.currentIndex()])
        self.eventos_auxiliar.append(evento_auxiliar)
        escritura_archivo(self.directorios['archivo_auxiliar'],self.eventos_auxiliar)
        self.cargar_lista_eventos()
        self.Lbl_Mensajes_2.setText("Ultimo : Marca "+str(self.cmbx_eventos.currentIndex()+1))
        self.grupo_evento.setEnabled(False)
    
    def lista_filtros(self, text):
        text="F inf ="+str(self.sp_Box_finf.value())+"F sup ="+str(self.sp_Box_fsup.value())+" orden ="+str(self.sp_Box_orden.value())
        self.Lbl_Mensajes_2.setText(text)

    def cargar_eventos(self):
        self.grupo_evento.setEnabled(True)
        self.grupo_guardar.setEnabled(False)
        self.grupo_cortar.setEnabled(True)
        self.grupo_desplazar.setEnabled(False)
        self.bandera_marcas=1
        self.estaciones_eventos=[]
        self.filtros_estaciones=[]
        for i in range(0, len(self.parametros['CODIGO'])):#Verifica todos los archivos MSEED de registro continuo encontrados en la base de datos.
            nombreMseed = self.directorio_registros+"/"+self.parametros['CODIGO'][i]+self.fecha_.strftime('_%Y%m%d_%H%M%S.mseed')
            try:
                auxiliar=open(nombreMseed,'r')
                auxiliar.close
                self.estaciones_eventos.append(int(self.parametros['NUM_ESTACION'][i]))
                self.filtros_estaciones.append('000000')
            except FileNotFoundError:
                pass
        self.estaciones_eventos_total=self.estaciones_eventos
        hora_sismo=lectura_eventos(self.archivo)[1]
        a= self.cmbx_eventos.currentIndex()
        
        self.trCanal = [
                        stream.copy() if isinstance(stream, Stream) else []
                        for stream in self.lectura_mseed_dia
                        ]

        self.tiempo = obtencion_hora(self.archivo)
        hora=self.tiempo.hour
        minuto=self.tiempo.minute
        segundo=self.tiempo.second
        hora_inicio=(hora*3600+minuto*60+segundo)
        tiempo_segundo=(hora_sismo[a])/64-hora_inicio  #t=trCanal[0][0].stats.starttime
        self.t_inicio=tiempo_segundo-420
        self.t_final=tiempo_segundo+420
        #el metodo grafico_evento grafica el evento con los canales habilitados en trCanal(los 16 canales 
        #del registro contínuo, con t_inicio y t_final como límites)
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        self.Lbl_Mensajes.setText("Actual: Evento " + str(a+1)) #self.Lbl_Mensajes.setText("Evento " + str(a)+"    Hora:"+text)
        
    def cargar_eventos_fijo(self):
        # Limpia la figura antes de graficar un nuevo evento
        self.grupo_evento.setEnabled(True)
        self.grupo_guardar.setEnabled(False)
        self.grupo_cortar.setEnabled(True)
        self.grupo_desplazar.setEnabled(False)
        tiempo_segundo=self.comboBox_hora.currentIndex()*3600+self.comboBox_minuto.currentIndex()*60+self.comboBox_segundo.currentIndex()
        self.copiar_stream_dia()
        self.bandera_marcas=1
        self.estaciones_eventos=[]
        self.filtros_estaciones=[]
        for i in range(0, len(self.parametros['CODIGO'])):#Verifica todos los archivos MSEED de registro continuo encontrados en la base de datos.
            nombreMseed = self.directorio_registros+"/"+self.parametros['CODIGO'][i]+self.fecha_.strftime('_%Y%m%d_%H%M%S.mseed')
            try:
                auxiliar=open(nombreMseed,'r')
                auxiliar.close
                self.estaciones_eventos.append(int(self.parametros['NUM_ESTACION'][i]))
                self.filtros_estaciones.append('000000')
            except FileNotFoundError:
                pass
        self.estaciones_eventos_total=self.estaciones_eventos
        self.t_inicio=tiempo_segundo-420
        self.t_final=tiempo_segundo+420
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        self.grupo_evento.setEnabled(True)       
    
    def lista_eventos(self, text):
        periodo=[(0,120000),(120000,180000),(180000,240000)]
        diccionaio_periodo= {
            "00:00 - 12:00": 0,
            "12:00 - 18:00": 1,
            "18:00 - 24:00": 2
            }
        self.grupo_evento.setEnabled(False)
        #self.grupo_desplazar.setEnabled(False)
        hora_str=self.cmbx_eventos.currentText()[-8:]
        var_tiempo=int(hora_str[:2]+hora_str[3:5]+hora_str[6:8])
        index_periodo=diccionaio_periodo[self.periodo]
        minimo=periodo[index_periodo][0]
        maximo=periodo[index_periodo][1]
        if var_tiempo>minimo and var_tiempo<maximo:
            self.Btn_eventos.setEnabled(True)
        else:
            self.Btn_eventos.setEnabled(False)
            QMessageBox.information(self, 'Advertencia', 'Periodo incorrecto.')

    def cambio_pagina(self):
        self.copiar_stream_dia()
        self.pagina=self.pagina+1
        auxiliar=self.pagina*6
        if auxiliar > len(self.estaciones_eventos):
            self.pagina=0
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_6_minutos(self):
        self.copiar_stream_dia()
        self.t_inicio=self.t_inicio+360
        self.t_final=self.t_final+360
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def menos_6_minutos(self):
        self.copiar_stream_dia()
        self.t_inicio=self.t_inicio-360
        self.t_final=self.t_final-360
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_2_segundos(self):
        self.copiar_stream_dia()
        self.t_inicio=self.t_inicio+2
        self.t_final=self.t_final+2
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_10_segundos(self):
        self.copiar_stream_dia()
        self.t_inicio=self.t_inicio+10
        self.t_final=self.t_final+10
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def mas_30_segundos(self):
        self.copiar_stream_dia()
        self.t_inicio=self.t_inicio+30
        self.t_final=self.t_final+30
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def menos_2_segundos(self):
        self.copiar_stream_dia()
        self.t_inicio=self.t_inicio-2
        self.t_final=self.t_final-2
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def menos_10_segundos(self):
        self.copiar_stream_dia()
        self.t_inicio=self.t_inicio-10
        self.t_final=self.t_final-10
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def menos_30_segundos(self):
        self.copiar_stream_dia()
        self.t_inicio=self.t_inicio-30
        self.t_final=self.t_final-30
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def cortar_evento(self):
        self.copiar_stream_dia()
        self.bandera_marcas=0
        self.t_inicio=self.t_inicio+410
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        self.grupo_cortar.setEnabled(False)
        self.grupo_desplazar.setEnabled(True)
        self.grupo_guardar.setEnabled(True)

    def menos_3_minutos(self):
        self.t_final=self.t_final-180
        aux=self.t_final-self.t_inicio
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,0,aux,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def menos_1_minutos(self):
        self.t_final=self.t_final-60
        aux=self.t_final-self.t_inicio
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,0,aux,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def menos_0_5_minutos(self):
        self.t_final=self.t_final-30
        aux=self.t_final-self.t_inicio
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,0,aux,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
    
    def menos_0_2_minutos(self):
        self.t_final=self.t_final-10
        aux=self.t_final-self.t_inicio
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,0,aux,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_3_minutos(self):
        self.copiar_stream_dia()
        self.t_final=self.t_final+180
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def mas_1_minutos(self):
        self.copiar_stream_dia()
        self.t_final=self.t_final+60
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
        
    def mas_0_5_minutos(self):
        self.copiar_stream_dia()
        self.t_final=self.t_final+30
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)
    
    def mas_0_2_minutos(self):
        self.copiar_stream_dia()
        self.t_final=self.t_final+10
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)

    def filtrar_evento(self):
        b=self.sp_Box_finf.value()|self.sp_Box_fsup.value()|self.sp_Box_orden.value()
        if b != 0:
            #self.copiar_stream_dia()
            self.visor_limpiar_completo()
            filtro_evento(self.visor,self.trCanal,self.sp_Box_finf.value(),self.sp_Box_fsup.value(),self.sp_Box_orden.value(),self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina,self.filtros_estaciones,self.estaciones_eventos_total,self.Btn_estaciones.isEnabled())

    def recargar_evento(self):
        self.copiar_stream_dia()
        self.visor_limpiar_completo()
        grafico_evento_int(self.visor,self.trCanal,self.t_inicio,self.t_final,self.estaciones_eventos,self.hab_grafico,self.bandera_marcas,self.pagina)        

    def verificar_estaciones(self):
        estaciones_(self.hab_grafico,self.estaciones_eventos,self.filtros_estaciones,self).exec_()
        
    def Salir___(self):
        message_box = QMessageBox(
            QMessageBox.Question,
            "¡Importante!",
            "  ¿Guardar informe?\nSolo guardar definitivo\n  de 12H, 18H o 24H",
            QMessageBox.Yes | QMessageBox.No ,
            self.window()
        )
        result = message_box.exec_()
        if result == QMessageBox.Yes:
            extraer_dia(self.archivo,self.responsable,False)
        self.close()


    def visor_limpiar_completo__(self):
        """Antes de cada gráfico nuevo"""
        self.visor.clear()
        self.visor.clf()
        # AGREGAAR ESTO:
        import matplotlib.pyplot as plt
        plt.close(self.visor)  # Liberar figura de matplotlib completamente


    def visor_limpiar_completo___(self):
        """Limpieza completa antes de cada gráfico nuevo"""
        if hasattr(self, 'visor') and self.visor:
            # Limpiar todos los axes
            for ax in self.visor.get_axes():
                ax.clear()
        
            # Limpiar la figura completa
            self.visor.clear()
            self.visor.clf()
        
            # Liberar de matplotlib completamente
            import matplotlib.pyplot as plt
            plt.close(self.visor)
        
            # Forzar actualización del canvas
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.draw_idle()


    def limpiar_estado__(self):
        """Limpia figuras, visores, hilos, timers, etc., antes de cerrar."""
        try:
            # Limpiar streams primero (más pesados)
            if hasattr(self, 'trCanal') and self.trCanal:
                for stream in self.trCanal:
                    if isinstance(stream, Stream):
                        try:
                            stream.clear()
                        except:
                            pass
                    del stream
                self.trCanal.clear()
                del self.trCanal
            
            if hasattr(self, 'canvas'):
                self.canvas.deleteLater()
                self.canvas = None
            if hasattr(self, 'visor'):
                self.visor.clf()
                self.visor = None
            # Limpieza de listas, buffers o datos
            if hasattr(self, 'stLeido'):
                del self.stLeido
            if hasattr(self, 'lista_eventos'):
                self.lista_eventos.clear()
        except Exception as e:
            print(f"Error en limpieza de Extraer_evento: {e}")


    def closeEvent__(self, event):
        """
        Emite la señal de cerrado para notificar a la ventana principal y realiza limpieza si es necesario.
        """
        print("Saliendo de Extraer eventos")
        self.limpiar_estado()
        self.cerrado.emit()
        QTimer.singleShot(0, self.cerrado.emit)

    def limpiar_estado_completo(self):
        """
        Limpia completamente todos los recursos antes de cerrar la ventana.
        Libera memoria de streams, canvas, figuras y widgets.
        """
        print("🧹 Iniciando limpieza completa de recursos...")
        
        try:
            # 1. DETENER Y LIMPIAR TIMERS
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
                self.timer.deleteLater()
                self.timer = None
            
            # 2. LIMPIAR STREAMS DE OBSPY (Los más pesados)
            self._limpiar_streams()
            
            # 3. LIMPIAR CANVAS Y FIGURAS DE MATPLOTLIB
            self._limpiar_matplotlib()
            
            # 4. LIMPIAR LISTAS Y DATOS
            self._limpiar_datos()
            
            # 5. DESCONECTAR SIGNALS
            self._desconectar_signals()
            
            # 6. LIMPIAR WIDGETS DINÁMICOS
            self._limpiar_widgets_dinamicos()
            
            # 7. FORZAR RECOLECCIÓN DE BASURA
            gc.collect()
            
            print("✅ Limpieza completa finalizada")
            
        except Exception as e:
            print(f"❌ Error durante la limpieza: {e}")

    def _limpiar_streams(self):
        """Limpia todos los streams de ObsPy"""
        print("🔄 Liberando streams de ObsPy...")
        
        # Limpiar streams individuales del día
        if hasattr(self, 'lectura_mseed_dia') and self.lectura_mseed_dia:
            for i, stream in enumerate(self.lectura_mseed_dia):
                if isinstance(stream, Stream) and len(stream) > 0:
                    try:
                        stream.clear()
                        del stream
                    except Exception as e:
                        print(f"⚠️ Error limpiando stream día {i}: {e}")
            self.lectura_mseed_dia.clear()
            del self.lectura_mseed_dia
        
        # Limpiar streams de canales
        if hasattr(self, 'trCanal') and self.trCanal:
            for i, stream in enumerate(self.trCanal):
                if isinstance(stream, Stream) and len(stream) > 0:
                    try:
                        stream.clear()
                        del stream
                    except Exception as e:
                        print(f"⚠️ Error limpiando stream canal {i}: {e}")
            self.trCanal.clear()
            del self.trCanal
        
        # Limpiar otros streams si existen
        attrs_streams = ['stLeido', 'stream_filtrado', 'streams_eventos']
        for attr in attrs_streams:
            if hasattr(self, attr):
                stream_obj = getattr(self, attr)
                if isinstance(stream_obj, (list, Stream)):
                    try:
                        if isinstance(stream_obj, list):
                            for s in stream_obj:
                                if isinstance(s, Stream):
                                    s.clear()
                            stream_obj.clear()
                        else:
                            stream_obj.clear()
                        delattr(self, attr)
                    except Exception as e:
                        print(f"⚠️ Error limpiando {attr}: {e}")

    def _limpiar_matplotlib(self):
        """Limpia completamente matplotlib y canvas"""
        print("📊 Liberando recursos de matplotlib...")
        
        try:
            # Limpiar canvas
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.figure.clear()
                self.canvas.close()
                self.canvas.deleteLater()
                self.canvas = None
            
            # Limpiar figura principal
            if hasattr(self, 'visor') and self.visor:
                self.visor.clear()
                self.visor.clf()
                plt.close(self.visor)
                del self.visor
                self.visor = None
            
            # Cerrar todas las figuras restantes de matplotlib
            plt.close('all')
            
        except Exception as e:
            print(f"⚠️ Error limpiando matplotlib: {e}")

    def _limpiar_datos(self):
        """Limpia listas, diccionarios y datos en memoria"""
        print("💾 Liberando datos en memoria...")
        
        # Listas y diccionarios a limpiar
        attrs_listas = [
            'hora_sismos', 'hora_sismos_extraidos', 'eventos_auxiliar',
            'estaciones_eventos', 'estaciones_eventos_total', 'filtros_estaciones',
            'parametros', 'directorios'
        ]
        
        for attr in attrs_listas:
            if hasattr(self, attr):
                try:
                    obj = getattr(self, attr)
                    if isinstance(obj, (list, dict)):
                        if hasattr(obj, 'clear'):
                            obj.clear()
                    delattr(self, attr)
                except Exception as e:
                    print(f"⚠️ Error limpiando {attr}: {e}")
        
        # Variables globales si existen
        global datos_sismo
        if 'datos_sismo' in globals():
            datos_sismo.clear()

    def _desconectar_signals(self):
        """Desconecta todas las señales de PyQt5"""
        print("🔌 Desconectando señales...")
        
        try:
            # Lista de botones que pueden tener señales conectadas
            botones = [
                'Btn_eventos', 'Btn_filtrar', 'Btn_guardar', 'Btn_recargar',
                'Btn_extraer_fijo', 'Btn_Salir', 'Btn_pagina', 'Btn_estaciones',
                'btn_cortar', 'btn_m_6', 'btn_p_6', 'btn_p__', 'btn_p__1',
                'btn_p__2', 'btn_m__', 'btn_m__1', 'btn_m__2', 'btn_m_3',
                'btn_m_1', 'btn_m_0_5', 'btn_m_0_2', 'btn_p_3_0', 'btn_p_1_0',
                'btn_p_0_5', 'btn_p_0_2'
            ]
            
            for btn_name in botones:
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    if btn and hasattr(btn, 'disconnect'):
                        btn.disconnect()
            
            # ComboBoxes y SpinBoxes
            controles = ['cmbx_eventos', 'sp_Box_finf', 'sp_Box_fsup', 'sp_Box_orden']
            for ctrl_name in controles:
                if hasattr(self, ctrl_name):
                    ctrl = getattr(self, ctrl_name)
                    if ctrl and hasattr(ctrl, 'disconnect'):
                        ctrl.disconnect()
                        
        except Exception as e:
            print(f"⚠️ Error desconectando señales: {e}")

    def _limpiar_widgets_dinamicos(self):
        """Limpia widgets creados dinámicamente"""
        print("🎛️ Liberando widgets dinámicos...")
        
        try:
            # Limpiar grupos de widgets si existen
            grupos = ['grupo_carga', 'grupo_evento', 'grupo_guardar', 
                     'grupo_cortar', 'grupo_desplazar', 'grupo_hora_especifica']
            
            for grupo in grupos:
                if hasattr(self, grupo):
                    widget = getattr(self, grupo)
                    if widget:
                        widget.deleteLater()
            
        except Exception as e:
            print(f"⚠️ Error limpiando widgets: {e}")

    def Salir_mejorado(self):
        """Método de salida mejorado con limpieza completa"""
        print("🚪 Iniciando proceso de salida...")
        
        message_box = QMessageBox(
            QMessageBox.Question,
            "¡Importante!",
            "  ¿Guardar informe?\nSolo guardar definitivo\n  de 12H, 18H o 24H",
            QMessageBox.Yes | QMessageBox.No,
            self.window()
        )
        result = message_box.exec_()
        
        if result == QMessageBox.Yes:
            try:
                extraer_dia(self.archivo, self.responsable, False)
                print("📋 Informe guardado correctamente")
            except Exception as e:
                print(f"❌ Error guardando informe: {e}")
                QMessageBox.warning(self, "Error", f"No se pudo guardar el informe: {e}")
        
        # Realizar limpieza completa ANTES de cerrar
        self.limpiar_estado_completo()
        
        # Cerrar la ventana
        self.close()

    def closeEvent_mejorado(self, event):
        """
        Método closeEvent mejorado que garantiza limpieza completa
        """
        print("🏁 Ejecutando closeEvent...")
        
        try:
            # Realizar limpieza completa
            self.limpiar_estado_completo()
            
            # Emitir señal de cerrado
            if hasattr(self, 'cerrado'):
                self.cerrado.emit()
            
            # Aceptar el evento de cierre
            event.accept()
            
            print("✅ Ventana cerrada correctamente")
            
        except Exception as e:
            print(f"❌ Error durante el cierre: {e}")
            # Aún así aceptar el cierre para evitar ventana colgada
            event.accept()

    def visor_limpiar_completo(self):
        """Limpieza completa antes de cada gráfico nuevo"""
        if hasattr(self, 'visor') and self.visor:
            # Limpiar todos los axes
            try:
                for ax in self.visor.get_axes():
                    ax.clear()
            except:
                pass
            
            # Limpiar la figura completa
            self.visor.clear()
            self.visor.clf()
            
            # Liberar de matplotlib completamente
            import matplotlib.pyplot as plt
            plt.close(self.visor)
            
            # Forzar actualización del canvas
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.draw_idle()

    def copiar_stream_dia(self):
        """Copia streams del día con limpieza previa mejorada"""
        print("🔄 Copiando streams del día...")
        
        # PASO 1: Limpieza profunda de streams anteriores
        if hasattr(self, 'trCanal') and self.trCanal:
            for i, stream in enumerate(self.trCanal):
                if isinstance(stream, Stream) and len(stream) > 0:
                    try:
                        stream.clear()
                        del stream
                    except Exception as e:
                        print(f"⚠️ Error limpiando stream {i}: {e}")
            
            self.trCanal.clear()
            del self.trCanal
        
        # PASO 2: Forzar recolección inmediata
        gc.collect()
        
        # PASO 3: Crear nueva copia con manejo de errores
        self.trCanal = []
        
        for idx, stream in enumerate(self.lectura_mseed_dia):
            if isinstance(stream, Stream) and len(stream) > 0:
                try:
                    # Verificar que el stream tenga datos válidos
                    if len(stream[0].data) > 0:
                        copia = stream.copy()
                        self.trCanal.append(copia)
                    else:
                        print(f"⚠️ Stream {idx} sin datos")
                        self.trCanal.append([])
                except Exception as e:
                    print(f"❌ Error copiando stream {idx}: {e}")
                    self.trCanal.append([])
            else:
                self.trCanal.append([])
        
        print(f"✅ {len([s for s in self.trCanal if isinstance(s, Stream)])} streams copiados")

    def verificar_memoria(self):
        """Método de diagnóstico para verificar el estado de memoria"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memoria_mb = process.memory_info().rss / 1024 / 1024
            print(f"📊 Uso de memoria actual: {memoria_mb:.2f} MB")
            
            # Contar objetos matplotlib activos
            import matplotlib.pyplot as plt
            figuras_activas = len(plt.get_fignums())
            print(f"📈 Figuras matplotlib activas: {figuras_activas}")
            
            return memoria_mb, figuras_activas
        except ImportError:
            print("📊 psutil no disponible para diagnóstico de memoria")
            return None, None

    # REEMPLAZAR LOS MÉTODOS EXISTENTES CON ESTOS:
    
    def limpiar_estado(self):
        """Método que reemplaza al original - llama a la limpieza completa"""
        return self.limpiar_estado_completo()

    def Salir_(self):
        """Método que reemplaza al original - llama a la salida mejorada"""
        return self.Salir_mejorado()

    def closeEvent(self, event):
        """Método que reemplaza al original - llama al closeEvent mejorado"""
        return self.closeEvent_mejorado(event)




















class estaciones_(QDialog):

    def __init__(self, hab_grafico,estaciones_eventos,filtros,parent=None):
        super(estaciones_,self).__init__()
        super().__init__(parent)
        self.parent=parent
        self.parametros=parametros_estaciones()#parametros son los parametros de las estaciones (nombre_canal_total_,nombre_canal,tipo_canal_,n_canales_,hab_canal)
        self.estaciones_eventos=estaciones_eventos
        self.filtros=filtros
        self.numero_estaciones=len(self.estaciones_eventos)
        self.hab_grafico=hab_grafico
        self.setFixedSize(410, 420)
        QDialog.__init__(self)
        secundaria_ui=os.path.join(ruta_ui,"secundaria.ui")
        uic.loadUi(secundaria_ui,self)
        self.ck_box_hab_canal={}
        self.lbl_nombre={}
        self.lbl_codigo={}
        self.ck_box_hab_canal = {}
        self.ck_box_filtro = {}
        nombre_canal_total_=self.parametros['NOMBRE']
        nombre_canal=self.parametros['CODIGO']
        componente_canal=self.parametros['COMPONENTE']
        self.lbl_grafico_0=QLabel("ESTACIONL",self)
        self.lbl_grafico_0.setGeometry(40, 20, 61, 16)  #setGeometry(x, y, width, height)
        self.lbl_grafico_1=QLabel("CÓDIGO",self)
        self.lbl_grafico_1.setGeometry(138, 20, 50, 16)
        self.lbl_grafico_2=QLabel("PLOT",self)
        self.lbl_grafico_2.setGeometry(204, 20, 51, 16)
        self.lbl_grafico_3=QLabel("CANAL",self)
        self.lbl_grafico_3.setGeometry(250, 20, 51, 16)
        self.lbl_grafico_4=QLabel("FILTRO",self)
        self.lbl_grafico_4.setGeometry(312, 20, 51, 16)
        self.lbl_grafico_5=QLabel("ORDEN",self)
        self.lbl_grafico_5.setGeometry(360, 20, 51, 16)
        self.lbl_grafico_6=QLabel("f inf.",self)
        self.lbl_grafico_6.setGeometry(403, 20, 51, 16)
        self.lbl_grafico_7=QLabel("f sup.",self)
        self.lbl_grafico_7.setGeometry(442, 20, 51, 16)

        self.spbox_fil_orden={}
        self.spbox_fil_finf={}
        self.spbox_fil_fsup={}
        self.spbox_canal={}
        lista_estaciones=[]
        for i in range(0, self.numero_estaciones):
            canal_=int(self.estaciones_eventos[i])
            lista_estaciones.append(nombre_canal_total_[canal_])
            self.lbl_nombre[i]=QLabel(nombre_canal_total_[canal_],self)
            self.lbl_nombre[i].setGeometry(15, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.lbl_codigo[i]=QLabel(nombre_canal[canal_],self)
            self.lbl_codigo[i].setGeometry(150, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.ck_box_hab_canal[i]=QCheckBox(self)
            self.ck_box_hab_canal[i].setGeometry(208, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            self.ck_box_hab_canal[i].setChecked(True)

            self.spbox_canal[i]=QSpinBox(self)
            self.spbox_canal[i].setGeometry(250, i*25+35, 40, 24)            
            self.spbox_canal[i].setRange(1, 3)
            self.spbox_canal[i].setValue(int(componente_canal[canal_]))
            estacion_i=self.estaciones_eventos[i]
            indice=self.parent.estaciones_eventos_total.index(estacion_i)
            orden=int(self.filtros[indice][0:2])
            f_inf=int(self.filtros[indice][2:4])
            f_sup=int(self.filtros[indice][4:6])
            self.ck_box_filtro[i]=QCheckBox(self)
            self.ck_box_filtro[i].setGeometry(316, i*25+35, 150, 24)  #setGeometry(x, y, width, height)
            if orden:
                val_orden=orden
                val_inf=f_inf
                val_sup=f_sup
                self.ck_box_filtro[i].setChecked(True)
            else:
                val_orden=2
                val_inf=1
                val_sup=10
                self.ck_box_filtro[i].setChecked(False)
            self.spbox_fil_orden[i]=QSpinBox(self)
            self.spbox_fil_orden[i].setGeometry(360, i*25+35, 40, 24)
            self.spbox_fil_orden[i].setRange(1, 10)
            self.spbox_fil_orden[i].setValue(val_orden)
            self.spbox_fil_finf[i]=QSpinBox(self)
            self.spbox_fil_finf[i].setGeometry(402, i*25+35, 40, 24)
            self.spbox_fil_finf[i].setRange(1, 10)
            self.spbox_fil_finf[i].setValue(val_inf)
            self.spbox_fil_fsup[i]=QSpinBox(self)
            self.spbox_fil_fsup[i].setGeometry(442, i*25+35, 40, 24)
            self.spbox_fil_fsup[i].setRange(5, 20)
            self.spbox_fil_fsup[i].setValue(val_sup)

            if self.hab_grafico[canal_]=='1':
                self.ck_box_hab_canal[i].setChecked(True)
        self.lbl_todos=QLabel("PLOT TODOS",self)
        self.lbl_todos.setGeometry(140, 435, 150, 24)  #setGeometry(x, y, width, height)
        self.ck_box_todos=QCheckBox(self)
        self.ck_box_todos.setGeometry(210, 437, 150, 24)  #setGeometry(x, y, width, height)
        self.ck_box_todos.setChecked(True)

        self.lbl_filtros=QLabel("FILTRO TODOS",self)
        self.lbl_filtros.setGeometry(131, 455, 150, 24)  #setGeometry(x, y, width, height)
        self.ck_box_filtros=QCheckBox(self)
        self.ck_box_filtros.setGeometry(210, 457, 150, 24)  #setGeometry(x, y, width, height)
        self.ck_box_filtros.setChecked(False)

        self.ck_box_todos.toggled.connect(self.validar)
        self.ck_box_filtros.toggled.connect(self.validar_filtros)


    def validar(self):
        if self.ck_box_todos.checkState()==2:
            for i in range(0, self.numero_estaciones):
                self.ck_box_hab_canal[i].setChecked(True)
        else:
            for i in range(0, self.numero_estaciones):
                self.ck_box_hab_canal[i].setChecked(False)

    def validar_filtros(self):
        if self.ck_box_filtros.checkState()==2:
            for i in range(0, self.numero_estaciones):
                if self.ck_box_hab_canal[i].checkState()==2:
                    self.ck_box_filtro[i].setChecked(True)
        else:
            for i in range(0, self.numero_estaciones):
                self.ck_box_filtro[i].setChecked(False)


    def closeEvent(self, event):
        auxiliar=[]
        for i in range(0, self.numero_estaciones):
            canal_=int(self.estaciones_eventos[i])
            estacion_i=self.estaciones_eventos[i]
            indice=self.parent.estaciones_eventos_total.index(estacion_i)
            if self.ck_box_hab_canal[i].checkState()==2:
                auxiliar.append(canal_)
            if self.ck_box_filtro[i].checkState()==2:
                orden_i=self.spbox_fil_orden[i].value()
                finf_i=self.spbox_fil_finf[i].value()
                fsup_i=self.spbox_fil_fsup[i].value()
                string_concatenado = f"{orden_i:02}{finf_i:02}{fsup_i:02}"
                self.parent.filtros_estaciones[indice]=string_concatenado
            else:
                self.parent.filtros_estaciones[indice]='000000'
        self.parent.estaciones_eventos=auxiliar
        self.parent.filtros_estaciones=self.filtros
        for i in range(0, self.numero_estaciones):
            canal_=int(self.estaciones_eventos[i])
            self.parent.componente_canal=str(self.spbox_canal[i])
            if self.ck_box_hab_canal[i].checkState()==2:
                self.parent.hab_grafico[canal_]='1'
            else:
                self.parent.hab_grafico[canal_]='0'

    def Salir_(self):
        self.destroy()

