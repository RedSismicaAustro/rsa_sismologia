import xml.etree.ElementTree as ET

# Valor de <ruta> que deseas buscar
evento_buscar = "250211_034035.sis"  # Cambia esto por el valor que buscas

def buscar_evento(evento_buscar,raiz):
    # Buscar el Evento que coincida con el valor de <ruta>
    evento_encontrado = None
    for evento in raiz.findall(".//Evento"):
        ruta = evento.findtext("ruta")
        if ruta == evento_buscar:
            evento_encontrado = evento
            break

    # Si se encontró el evento, extraer <rms> y <azm> de las estaciones
    if evento_encontrado is not None:
        # Obtener el valor de <rms>
        rms = evento_encontrado.findtext("rms")
        print(f"Valor de <rms>: {rms}")

        # Obtener los valores de <azm> de todas las estaciones
        estaciones = evento_encontrado.find("estaciones")
        if estaciones is not None:
            for estacion in estaciones.findall("estacion"):
                nombre = estacion.findtext("nombre")
                azm = estacion.findtext("azm")
                print(f"Estación: {nombre}, Valor de <azm>: {azm}")
    else:
        print(f"No se encontró ningún evento con <ruta> = {evento_buscar}")