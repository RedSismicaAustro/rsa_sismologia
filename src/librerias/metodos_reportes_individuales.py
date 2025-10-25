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
# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)


from metodos_gis_rsa import catalogo_gis
from metodos_graficos_rsa import impresion_reporte_sismo
from PyQt5.QtWidgets import QMessageBox
from ventana_aceleraciones import Subventana_aceleraciones
def generar_reporte_sismo(catalogo, evento_escogido, canales, tr_canal, archivo_rep,directorio_trabajo):
    """
    Genera un reporte de sismo basado en un evento escogido del catálogo.

    Args:
        catalogo (list): Lista con los registros del catálogo del período.
        evento_escogido (list): Lista con el evento seleccionado.
        canales (list): Lista de canales asociados al evento.
        tr_canal (list): Datos relacionados con los canales.
        archivo_rep (str): Nombre del archivo del reporte.
    """
    # Seleccionar los registros del catálogo relacionados con el evento escogido
    print(evento_escogido)
    print(catalogo)

    catalogo_escogido = [
        registro for registro in catalogo if registro[18] == evento_escogido[0][1]
    ]

    if not catalogo_escogido:
        QMessageBox.information(None, "Aviso", "No hay información del evento en el catálogo")
        return

    # Llama a una función externa que maneja el catálogo GIS (si aplica)
    catalogo_gis(catalogo_escogido)

    # Crear una ventana de confirmación para generar el reporte
    message_box = QMessageBox()
    message_box.setIcon(QMessageBox.Question)
    message_box.setWindowTitle("Reporte")
    message_box.setText("¿Generar el reporte del evento?")
    message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    
    result = message_box.exec_()

    if result == QMessageBox.Yes:
        # Llama a la función que genera el reporte del sismo
        impresion_reporte_sismo(archivo_rep, catalogo_escogido, canales, tr_canal, 0,directorio_trabajo,1)
        QMessageBox.information(None, "Aviso", "Reporte generado\n"+archivo_rep)
    else:
        QMessageBox.information(None, "Aviso", "Reporte no generado")
    return

def generar_reporte_acelerograma(eventos,indice,catalogo,evento_escogido,archivo_escogido):
    """
    Genera un reporte de sismo basado en un evento escogido del catálogo.

    Args:
        catalogo (list): Lista con los registros del catálogo del período.
        evento_escogido (list): Lista con el evento seleccionado.
        canales (list): Lista de canales asociados al evento.
        tr_canal (list): Datos relacionados con los canales.
        archivo_rep (str): Nombre del archivo del reporte.
    """
    # Seleccionar los registros del catálogo relacionados con el evento escogido
    catalogo_escogido = [
        registro for registro in catalogo if registro[18] == evento_escogido[0][1]
    ]

    if not catalogo_escogido:
        QMessageBox.information(None, "Aviso", "No hay información del evento en el catálogo")
        return

    if eventos[indice][2] in ['Evento_local', 'CONTROL']:
        fecha = "20" + eventos[indice][1][0:6] + eventos[indice][1][7:13]
        mensaje = (
            fecha,
            int(fecha[:4]),
            int(fecha[4:6]),
            int(fecha[6:8]),
            int(fecha[8:10]),
            int(fecha[10:12]),
            int(fecha[12:14]),
            0, 0, "", "", "", "", "", "", "", "", "RSA", "", "Evento Local o de maniobra"
        )
        Subventana_aceleraciones(archivo_escogido, mensaje, eventos[indice]).exec_()
    else:
        catalogo_data = catalogo_escogido[0] if catalogo_escogido[0] else catalogo_escogido[1]
        Subventana_aceleraciones(archivo_escogido, catalogo_data, eventos[indice]).exec_()
