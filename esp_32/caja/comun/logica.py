# comun/logica.py
# Aquí van funciones que se puedan ejecutar tanto en PC como en el ESP32.

def calcular_promedio(valores):
    """Devuelve el promedio de una lista."""
    if not valores:
        return 0
    return sum(valores) / len(valores)


def clasificar_valor(valor, umbral):
    """Clasifica el valor como 'OK' o 'ALTO' según un umbral."""
    return "ALTO" if valor > umbral else "OK"
