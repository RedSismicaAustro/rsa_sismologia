"""
marcar_impresiones ok
imprimir_catalogo ok
_filtrar_catalogo_oficial_sin_dummies ok
_construir_catalogo_diario_para_detalle ok
responsables_tiempos_ ok
responsables_tiempos___ ok
reporte_resumen_modos ok
reporte_resumen_modos__ ok
normalizar_layout_por_institucional ok
normalizar_layout_por_institucional__ ok
derivar_banderas_desde_modo ok


from rsa_reportes_pdf import impresion_reporte_sismo ,impresion_reporte_acelerograma,cabecera_,reporte_resumen_modos,normalizar_layout_por_institucional,derivar_banderas_desde_modo,hoja_seniales_


from rsa_catalogo_pdf import marcar_impresiones,imprimir_catalogo,_filtrar_catalogo_oficial_sin_dummies,_construir_catalogo_diario_para_detalle,estadistica_,responsables_tiempos_,responsables_tiempos___,

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

from rsa_io import leer_mseed
from rsa_dominio import convertir_lista
from rsa_pdf_reportes import impresion_reporte_acelerograma,hoja_seniales_

#from rsa_graficos_pdf import *
#from rsa_reportes_pdf import *
#from rsa_catalogo_pdf import *

from rsa_pdf_graficos import (mapa_configuracion,formato,mapa,
                              dibujo_sismos_,caja_simbologia,estadistica_)


from metodos_gestion import parametros_estaciones,obtener_directorios

from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, String
from reportlab.pdfgen import canvas
import csv
from reportlab.lib.pagesizes import A4

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
    # estaciones_informe -   estaciones que conformen los informes
    # tipo_canal         -   Tipo de canal
    # mapa_              -   Mapa al cual se va a imprimri
    # raiz               -   base de datos XML
    # detalle            -   Averiguar que no me acuerdo
    maximos_reporte=[]
    indice=0
    while indice<len(catalogo): #Trabaja sobre el catalogo sísmico generado, incluyendo los reportes de otras redes.
        ####################################################################
        #### SISMOGRAMAS
        ####################################################################
        
        if catalogo[indice]==[] or catalogo[indice][IDX_EVENTO]=='ruta' :
            indice=indice+1
            continue
        print("Graficando:  ",catalogo[indice][IDX_EVENTO])
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


# ======================================================================================
# 3) Auxiliar: limpiar catálogo para oficiales (excluir dummies "No procesado" del M1)
# ======================================================================================
def _filtrar_catalogo_oficial_sin_dummies(catalogo: list) -> list:
    """
    Devuelve el catálogo sin filas dummy 'No procesado' (id '00000000000000').
    Asume cabecera en catalogo[0].
    """
    if not catalogo:
        return catalogo
    filtrado = [catalogo[0]]
    for fila in catalogo[1:]:
        if not fila:
            continue
        # En tu dummy: fila[0] = '00000000000000'
        if str(fila[0]).strip() == '00000000000000':
            continue
        filtrado.append(fila)
    return filtrado


# ======================================================================================
# 4) Auxiliar: construir catalogo_dia (M2) con dummies locales si corresponde
# ======================================================================================

def _construir_catalogo_diario_para_detalle(catalogo: list, eventos: list) -> list:
    """
    Reproduce tu lógica: para cada 'evento_dia' arma las coincidencias en el catálogo,
    priorizando RSA. Si no hay coincidencias y el evento es FF/FC/INDEFINIDO, agrega dummy local.
    """
    catalogo_dia = []
    if not catalogo or not eventos:
        return catalogo_dia

    # Indices usados repetidamente
    # Asumo constantes ya definidas en tu módulo:
    # IDX_EVENTO, IDX_FUENTE
    for evento_dia in eventos:
        if not evento_dia or len(evento_dia) < 3:
            continue

        evento_id = evento_dia[1]
        tipo_ev   = evento_dia[2]
        dummy = []
        if tipo_ev in ('FF', 'FC', 'INDEFINIDO'):
            # dummy local (NO contamina el catálogo maestro)
            dummy = ['00000000000000', '2025', '1', '1', '0', '0', '0',
                     '-2.00', '-79.00', '0', 'rms', 'e-x', 'e-y', 'e-0', 'e-z',
                     '0', ' ', 'No procesado', evento_id, ' , , ']

        coincidencias = []
        for fila in catalogo:
            if fila and fila[IDX_EVENTO] == evento_id:
                coincidencias.append(fila)

        if coincidencias:
            # Prioriza RSA primero, luego otras redes
            coincidencias.sort(key=lambda f: 0 if f[IDX_FUENTE] == 'RSA' else 1)
            catalogo_dia.extend(coincidencias)
        else:
            if dummy:
                catalogo_dia.append(dummy)

    return catalogo_dia


def responsables_tiempos_(lienzo, resumen_responsables, modo_reporte):
    """
    Renderiza el cuadro de tiempos por responsable según el modo:

      - M1 (1) / M2 (2): por cortes 12H/18H/24H, muestra T(min) por fila.
      - M3 (3) / M4 (4): agregado por responsable, muestra T(horas).
      - M5 (5) / M6 (6) / M7 (7): no imprime nada.

    Estructura esperada en 'resumen_responsables' (una fila por responsable y corte):
      [RESP, CORTE(12H|18H|24H), TOT, SIS, FF, FC, Loc, TEL, IND, Ruido, c3, c4, c5, c6, c7, c8]
    """

    # ===== Robustez de entrada =====
    try:
        _ = iter(resumen_responsables)
    except Exception:
        return lienzo
    if not resumen_responsables:
        return lienzo

    # Modos institucionales no imprimen tiempos
    if modo_reporte in (5, 6, 7):
        return lienzo

    # ===== Único helper: minutos de trabajo a partir de contadores =====
    def calcular_minutos(valores_):
        """
        Política histórica (conservadora):
          T(min) = TOT*60 + c3*300 + c4*600 + c5*1200
        Índices dentro de valores_ (long. 14 esperada):
          0:TOT, 1:SIS, 2:FF, 3:FC, 4:Loc, 5:TEL, 6:IND, 7:Ruido, 8:c3, 9:c4, 10:c5, 11:c6, 12:c7, 13:c8
        """
        try:
            tot = int(valores_[0])
            c3  = int(valores_[8])  if len(valores_) > 8  else 0
            c4  = int(valores_[9])  if len(valores_) > 9  else 0
            c5  = int(valores_[10]) if len(valores_) > 10 else 0
        except Exception:
            return 0
        return tot*1 + c3*5 + c4*10 + c5*20

    # ===== Normalización mínima de filas a 16 columnas =====
    filas_norm = []
    for fila in resumen_responsables:
        base = list(fila)[:16] + ['0'] * max(0, 16 - len(fila))
        nombre = str(base[0]) if base[0] is not None else ''
        corte  = str(base[1]).upper() if isinstance(base[1], str) else str(base[1])
        # vectores numéricos (conversión segura a int)
        vals = []
        for v in base[2:16]:
            try:
                vals.append(int(v))
            except Exception:
                vals.append(0)
        filas_norm.append((nombre, corte, vals))  # (RESP, CORTE, [14 valores])

    # ===== M1/M2: por cortes 12H/18H/24H, en minutos =====
    if modo_reporte in (1, 2):
        # Orden 12H→18H→24H
        orden_corte = {'12H': 0, '18H': 1, '24H': 2}
        filas_norm.sort(key=lambda r: (r[0], orden_corte.get(r[1], 99)))

        dibujo = Drawing(460, 180)
        dibujo.add(String(160, 155, 'Resumen de tiempos responsables:', fontSize=14))

        cabecera = ['RESPONSABLE', 'HORA', 'TOT.', 'SIS.', 'FF', 'FC', 'Loc.', 'TEL.', 'IND.', 'T(min)']
        xcols    = [45, 140, 205, 245, 275, 305, 335, 365, 395, 430]
        for j, txt in enumerate(cabecera):
            dibujo.add(String(xcols[j], 140, txt, fontSize=12))

        y = 128
        for nombre, corte, vals in filas_norm:
            tmin = calcular_minutos(vals)
            datos = [nombre, corte, vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], round(tmin, 1)]
            for j, item in enumerate(datos):
                dibujo.add(String(xcols[j], y, str(item), fontSize=12))
            y -= 12
            # Paginación simple
            if y < 20:
                dibujo.drawOn(lienzo, 15, 56)
                lienzo.showPage()
                dibujo = Drawing(460, 180)
                dibujo.add(String(160, 155, 'Resumen de tiempos responsables:', fontSize=14))
                for j, txt in enumerate(cabecera):
                    dibujo.add(String(xcols[j], 140, txt, fontSize=12))
                y = 128

        dibujo.drawOn(lienzo, 15, 56)
        return lienzo

    # ===== M3/M4: agregado por responsable, en horas =====
    if modo_reporte in (3, 4):
        # Agregar por responsable
        acumulado_por_resp = {}  # resp -> ([sumas 14], minutos_totales)
        for nombre, corte, vals in filas_norm:
            tmin = calcular_minutos(vals)
            if nombre not in acumulado_por_resp:
                acumulado_por_resp[nombre] = ([0]*14, 0)
            sumas, tprev = acumulado_por_resp[nombre]
            acumulado_por_resp[nombre] = ([s+a for s, a in zip(sumas, vals)], tprev + tmin)

        dibujo = Drawing(520, 200)
        dibujo.add(String(160, 175, 'Resumen de tiempos invertidos:', fontSize=14))

        cabecera = ['RESPONSABLE', 'TOT.', 'SIS.', 'FF', 'FC', 'Loc.', 'TEL.', 'IND.', 'T(horas)']
        xcols    = [45, 205, 245, 275, 305, 335, 365, 395, 455]
        for j, txt in enumerate(cabecera):
            dibujo.add(String(xcols[j], 160, txt, fontSize=12))

        y = 148
        for nombre in sorted(acumulado_por_resp.keys()):
            vals_sum, tmin = acumulado_por_resp[nombre]
            thoras = round(tmin / 60.0, 2)
            datos = [nombre, vals_sum[0], vals_sum[1], vals_sum[2], vals_sum[3], vals_sum[4], vals_sum[5], vals_sum[6], thoras]
            for j, item in enumerate(datos):
                dibujo.add(String(xcols[j], y, str(item), fontSize=12))
            y -= 12
            # Paginación simple
            if y < 20:
                dibujo.drawOn(lienzo, 15, 400)
                lienzo.showPage()
                dibujo = Drawing(520, 200)
                dibujo.add(String(160, 175, 'Resumen de tiempos invertidos:', fontSize=14))
                for j, txt in enumerate(cabecera):
                    dibujo.add(String(xcols[j], 160, txt, fontSize=12))
                y = 148

        dibujo.drawOn(lienzo, 15, 400)
        return lienzo

    # Cualquier otro caso: no imprime
    return lienzo



# ==========================================================================================
# 5) NUEVA FUNCIÓN: reporte_resumen_modos (núcleo gobernado por 'modo_reporte')
#    - Reemplaza a tu 'reporte_resumen' actual (puedes renombrarla si lo prefieres).
#    - Firma explícita con 'modo_reporte', 'bandera_firma' y 'bandera_relleno' externos.
# ==========================================================================================

def reporte_resumen_modos(
    archivo_pdf: str,
    subtitulo_reporte: str,
    fecha_ini, fecha_fin,
    catalogo: list,
    resumen: list,
    mapa_: int,
    tipo_mapa: int,
    modo_reporte: int,
    estaciones,
    directorio: str,
    arbol,
    resumen_responsables: list,
    eventos: list,
    bandera_firma: bool,
    bandera_relleno: bool,
    horario: str = ""
):

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
    # tipo_mapa -------Tipo de mapa    0, 1 y 2 con basico, intermnedio y detallado respectivamente
    # banderas-------
    #                es_periodo     ---     bandera que habilita o deshabilita el cuadro resumen, permite usar el mismo método para hacer el reporte diario o el de período 
    #                                       en el reporte   0  no aparecen el cuadro reesumen ni las horas  1 aparece todo
    #                con_detalles   ---     bandera que permite la impresion de los detalles de los reportes. ()
    #                bandera_firma  ---     bandera que habilita o no la impresion para la firma (Nombre del responsable)
    #                
    # estaciones---- estaciones involucradas en le reporte diario, si es período este tiene valor de 0
    # directorio---- direcorio base donde se tomará la información de los días del reporte, usado en periodo.
    # arbol--------- base de datos en xml del periodo de reporte
    # resumen_responsables----
    # eventos        Todos los eventos generados en el día.
    # bandera_relleno Permite el rellono o no de los circulos de los eventos para cierto tipo de reportes.    
    
     
    print("archivo_pdf:", archivo_pdf,
          "\nSubtitulo:", subtitulo_reporte,
          "\nModo:", modo_reporte)

    # 1) BANDERAS POR MODO
    banderas = derivar_banderas_desde_modo(modo_reporte)

    # 2) MAPA
    datos_mapa      = mapa_configuracion(mapa_, tipo_mapa)
    mapa_despliegue = datos_mapa[0]
    coordenadas     = datos_mapa[1]
    salto           = datos_mapa[2]
    titulo_hoja     = datos_mapa[3]
    estaciones_info = datos_mapa[4]

    # 3) LAYOUT FÍSICO (parche correcto usando tipo_institucional)
    layout = normalizar_layout_por_institucional(banderas['tipo_institucional'])
    tamanio    = layout['tamanio']
    marca_agua = layout['marca_agua']
    pos_x, pos_y = layout['pos_caja']
    tipo_formato = banderas.get('formato_portada', 0)

    # 4) VECTOR DE EVENTOS
    vector = []
    if catalogo:
        for fila in catalogo[1:]:
            if not fila:
                continue
            try:
                lat = float(fila[IDX_LATITUD])
                lon = float(fila[IDX_LONGITUD])
                prf = -1.0 * float(fila[IDX_PROFUNDIDAD])
                mag = float(fila[IDX_MAGNITUD])
            except:
                continue

            ruta = fila[IDX_EVENTO]
            red = 0 if fila[IDX_FUENTE] == "RSA" else 1
            vector.append([lat, lon, prf, mag, red, ruta])

    # 5) CREAR LIENZO + PORTADA
    lienzo = canvas.Canvas(archivo_pdf, pagesize=A4)
    titulo_portada = "SISMICIDAD REGIONAL REGISTRADA"

    lienzo = formato(marca_agua, A4, titulo_portada, subtitulo_reporte, tipo_formato, lienzo)
    lienzo = mapa(lienzo, mapa_despliegue, tamanio, coordenadas, salto, 1)
    lienzo = dibujo_sismos_(lienzo, vector, coordenadas, tamanio, mapa_, banderas['es_periodo'], bandera_relleno)
    lienzo = caja_simbologia(lienzo, resumen, vector, (pos_x, pos_y), mapa_, banderas['es_periodo'], bandera_relleno)

    # ========================================================
    #                RAMA PERIODO
    # ========================================================
    if banderas['es_periodo']:

        lienzo = estadistica_(lienzo, resumen, fecha_ini, mapa_, banderas['es_periodo'])

        if banderas['incluir_responsables']:
            lienzo.showPage()
            lienzo = responsables_tiempos_(lienzo, resumen_responsables, modo_reporte)

        if banderas['insertar_no_procesado'] and banderas['imprimir_detalle']:
            catalogo_extendido = catalogo.copy()

            for evento_dia in eventos:
                if not evento_dia or evento_dia[1] == "Fecha; Hora (UTC)":
                    continue

##########################################################


                evento_id = evento_dia[1]

                try:
                    hora_evento = int(evento_id[9:11])
                except Exception:
                    continue

                hora_ini = 0
                hora_fin = 24

                if horario == "00:00 - 12:00":
                    hora_ini, hora_fin = 0, 12
                elif horario == "12:00 - 18:00":
                    hora_ini, hora_fin = 12, 18
                elif horario == "18:00 - 24:00":
                    hora_ini, hora_fin = 18, 24

                if not (hora_ini <= hora_evento < hora_fin):
                    continue





####################################################


                tipo_evento = evento_dia[2]

                if tipo_evento == "Ruido":
                    continue

                evento_id = evento_dia[1]

                # Verificar si ya existe en el catálogo
                existe = False
                for fila in catalogo_extendido[1:]:
                    if fila[IDX_EVENTO] == evento_id:
                        existe = True
                        break

                if existe:
                    continue

                try:
                    ev_num = int(evento_id.replace("_", "")[:-4])
                except Exception:
                    continue

                dummy = ['00000000000000','2025','1','1','0','0','0',
                         '-2.00','-79.00','0','rms','e-x','e-y','e-0','e-z',
                         '0',' ',tipo_evento,evento_id,' , , ']

                insertado = False
                for i in range(1, len(catalogo_extendido)):
                    try:
                        actual = int(catalogo_extendido[i][IDX_EVENTO].replace("_","")[:-4])
                    except Exception:
                        continue

                    if actual >= ev_num:
                        catalogo_extendido.insert(i, dummy)
                        insertado = True
                        break

                if not insertado:
                    catalogo_extendido.append(dummy)

            catalogo = catalogo_extendido


        if banderas['mostrar_tabla_resumen']:

            contador_linea = 0
            loc_centrada = (73,107,122,140,153,171,190,220,245,271,295,320,360)
            localizacion = (46,105,126,142,158,173,188,212,239,268,293,322,350)
            marca_agua_tabla = (120,450,400,200)

            for evento_catalogo in catalogo:
                if not evento_catalogo:
                    continue
                if evento_catalogo[19] == ' ':
                    continue

                if contador_linea == 80:
                    contador_linea = 0
                contador_linea += 1
                contador_col = 0

                if contador_linea == 1:
                    lienzo.showPage()
                    lienzo = formato(marca_agua_tabla, A4, titulo_hoja, subtitulo_reporte, 0, lienzo)
                    lienzo.setFont('Helvetica', 7)

                try:
                    magv = float(evento_catalogo[IDX_MAGNITUD])
                    lienzo.setFillColor(colors.blue if magv > 4 else colors.black)
                except:
                    lienzo.setFillColor(colors.black)

                for idx in (0,1,2,3,4,5,6,7,8,9,15,17,19):
                    texto = evento_catalogo[idx]
                    if contador_linea == 1:
                        lienzo.drawString(loc_centrada[contador_col], 740 - contador_linea*8, catalogo[0][idx])
                    else:
                        if 5 < contador_col < 9:
                            try:
                                texto = str(round(float(texto),2))
                            except:
                                pass
                        if contador_col == 10:
                            texto = texto + evento_catalogo[idx+1]
                        lienzo.drawString(localizacion[contador_col], 740 - contador_linea*8, texto)
                    contador_col += 1

            if contador_linea > 50:
                lienzo.showPage()
                lienzo = formato(marca_agua_tabla, A4, titulo_hoja, subtitulo_reporte, 0, lienzo)

            lienzo.setFont('Helvetica', 10)
            x, y = 100, 740 - (contador_linea + 20)*8

            if modo_reporte in (MODO_INSTITUCIONAL_DETALLADO, MODO_INSTITUCIONAL_RESUMEN) and bandera_firma:
                lienzo.drawString(x, y, "Ing. Remigio Guevara")

            lienzo.drawString(x, y-10, "Red Sísmica del Austro")

        lienzo.showPage()

        if banderas['imprimir_detalle']:
            if banderas['solo_catalogo_oficial']:
                catalogo_para_detalle = _filtrar_catalogo_oficial_sin_dummies(catalogo)
            else:
                catalogo_para_detalle = catalogo

            mapa_detalle = mapa_ if banderas['extras_tecnicos'] else 0

            maximos_reporte = imprimir_catalogo(
                catalogo_para_detalle, arbol, lienzo, directorio,
                estaciones_info, parametros_estaciones()['SENSOR'],
                mapa_detalle, arbol.getroot(), tipo_mapa
            )
        else:
            maximos_reporte = []

    # ========================================================
    #                RAMA DIARIA (M2)
    # ========================================================
    else:

        lienzo = responsables_tiempos_(lienzo, resumen_responsables, modo_reporte)

        catalogo_dia = _construir_catalogo_diario_para_detalle(catalogo, eventos)

        lienzo.showPage()

        maximos_reporte = imprimir_catalogo(
            catalogo_dia, arbol, lienzo, directorio,
            estaciones_info, parametros_estaciones()['SENSOR'],
            mapa_, arbol.getroot(), tipo_mapa
        )

    lienzo.save()
    return maximos_reporte


# ============================================================
# 2) Layout compacto vs general (solo posiciones y tamaños)
# ============================================================
def normalizar_layout_por_institucional(tipo_institucional: str):
    """
    Devuelve el layout físico (tamaño del mapa, marca de agua y posición de la
    caja de simbología) según el tipo de institución:

    - FACULTAD  → formato especial (tipo_formato = 2)
    - GADS / ELECAUSTRO / OTRO → formato general
    - NO-INST → formato general
    """

    # Formato general
    layout_general = {
        'tipo_formato': 0,
        'tamanio':      (90, 325, 400, 400),
        'marca_agua':   (200, 100, 200, 95),
        'pos_caja':     (55, 234),
    }

    # Formato Facultad (solo M5)
    layout_facultad = {
        'tipo_formato': 2,
        'tamanio':      (81, 216, 432, 432),
        'marca_agua':   (261, 66, 79, 36),
        'pos_caja':     (85, 109),
    }

    if tipo_institucional == "FACULTAD":
        return layout_facultad

    return layout_general



def normalizar_layout_por_institucional__(es_institucional: bool) -> dict:
    """
    Define posiciones físicas para el mapa, marca de agua y caja de simbología.
    No toca coordenadas de AOI ni estilo (eso viene de mapa_configuracion).
    """
    if not es_institucional:
        # Layout GENERAL (el que usas cuando antes mapa_ != 2/4)
        return {
            'tipo_formato': 0,
            'tamanio': (90, 325, 400, 400),       # xpos, ypos, ancho, alto
            'marca_agua': (200, 100, 200, 95),    # xpos, ypos, ancho, alto
            'pos_caja': (55, 234),                # leyenda/simbología
        }
    else:
        # Layout INSTITUCIONAL (el que usabas para 2/4)
        return {
            'tipo_formato': 2,
            'tamanio': (81, 216, 432, 432),
            'marca_agua': (261, 66, 79, 36),
            'pos_caja': (85, 109),
        }



# =============================================================================
# Derivación de banderas por modo
#  - Diferencias clave solicitadas:
#    * M3 (Oficial detallado): extras_técnicos = True, cobertura/estaciones = True
#      y **AHORA incluye resumen/página de responsables**.
#    * M6 (Institucional detallado): SIN extras y **SIN responsables**.
# =============================================================================
def derivar_banderas_desde_modo(modo_reporte: int):
    """
    Traduce el modo numérico (1–7) a las banderas que gobiernan:
        - Contenido del reporte
        - Inclusión de responsables
        - Inclusión de tabla resumen
        - Inserción de eventos no procesados
        - Impresión de detalle
        - Catálogo oficial
        - Extras técnicos
        - Tipo institucional (FACULTAD / GADS / OTRO / NO-INSTITUCIONAL)
        - Formato de portada (0 general, 2 facultad)
    """

    # Base general para todos
    banderas = {
        'es_periodo': False,
        'imprimir_detalle': False,
        'incluir_responsables': False,
        'insertar_no_procesado': False,
        'mostrar_tabla_resumen': False,
        'solo_catalogo_oficial': False,
        'extras_tecnicos': False,
        'tipo_institucional': "NO-INST",
        'formato_portada': 0,
    }

    # ========================
    #  MODO 1: PERIODO FRANJAS    M1 – Período por franjas (00–12, 12–18, 18–24) – Control interno
    # ========================
    if modo_reporte == MODO_PERIODO_FRANJAS:
        banderas.update({
            'es_periodo': True,
            'incluir_responsables': True,
            'imprimir_detalle': True,
            'insertar_no_procesado': True,
            'mostrar_tabla_resumen': True,
            'solo_catalogo_oficial': False,
            'extras_tecnicos': True,
            'tipo_institucional': "NO-INST",
            'formato_portada': 0,
        })
        return banderas

    # ========================
    #  MODO 2: DIARIO REVISIÓN    M2 – Diario de revisión (día/ad-hoc) con detalle y dummies locales
    # ========================
    if modo_reporte == MODO_DIARIO_REVISION:
        banderas.update({
            'es_periodo': False,
            'incluir_responsables': True,
            'imprimir_detalle': True,
            'insertar_no_procesado': False,
            'mostrar_tabla_resumen': False,
            'solo_catalogo_oficial': False,
            'extras_tecnicos': True,
            'tipo_institucional': "NO-INST",
            'formato_portada': 0,
        })
        return banderas

    # ========================
    #  MODO 3: OFICIAL DETALLADO    M3 – Oficial detallado (solo catálogo) + página/resumen de responsables
    # ========================
    if modo_reporte == MODO_OFICIAL_DETALLADO:
        banderas.update({
            'es_periodo': True,
            'incluir_responsables': True,
            'imprimir_detalle': True,
            'insertar_no_procesado': False,
            'mostrar_tabla_resumen': True,
            'solo_catalogo_oficial': True,
            'extras_tecnicos': True,
            'tipo_institucional': "NO-INST",
            'formato_portada': 0,
        })
        return banderas

    # ========================
    #  MODO 4: OFICIAL RESUMEN   M4 – Oficial resumen (solo catálogo, sin detalle)
    # ========================
    if modo_reporte == MODO_OFICIAL_RESUMEN:
        banderas.update({
            'es_periodo': True,
            'incluir_responsables': True,
            'imprimir_detalle': False,
            'insertar_no_procesado': False,
            'mostrar_tabla_resumen': True,
            'solo_catalogo_oficial': True,
            'extras_tecnicos': False,
            'tipo_institucional': "NO-INST",
            'formato_portada': 0,
        })
        return banderas



    # ========================
    #  MODO 5: FACULTAD RESUMEN  M5 – Facultad/resumen (redes sociales), sin detalle
    # ========================
    if modo_reporte == MODO_FACULTAD_RESUMEN:
        banderas.update({
            'es_periodo': True,
            'incluir_responsables': False,
            'imprimir_detalle': False,
            'insertar_no_procesado': False,
            'mostrar_tabla_resumen': True,
            'solo_catalogo_oficial': True,
            'extras_tecnicos': False,
            'tipo_institucional': "FACULTAD",
            'formato_portada': 2,
        })
        return banderas

    # ==============================
    #  MODO 6: INSTITUCIONAL DETALLADO   M6 – Institucional detallado (solo catálogo), sin extras ni responsables
    # ==============================
    if modo_reporte == MODO_INSTITUCIONAL_DETALLADO:
        banderas.update({
            'es_periodo': True,
            'incluir_responsables': False,
            'imprimir_detalle': True,
            'insertar_no_procesado': False,
            'mostrar_tabla_resumen': True,
            'solo_catalogo_oficial': True,
            'extras_tecnicos': False,
            'tipo_institucional': "GADS",   # representación institucional
            'formato_portada': 0,
        })
        return banderas

    # ==============================
    #  MODO 7: INSTITUCIONAL RESUMEN   M7 – Institucional, sin detalle
    # ==============================
    if modo_reporte == MODO_INSTITUCIONAL_RESUMEN:
        banderas.update({
            'es_periodo': True,
            'incluir_responsables': False,
            'imprimir_detalle': False,
            'insertar_no_procesado': False,
            'mostrar_tabla_resumen': True,
            'solo_catalogo_oficial': True,
            'extras_tecnicos': False,
            'tipo_institucional': "GADS",
            'formato_portada': 0,
        })
        return banderas

    return banderas






