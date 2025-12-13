# pc/test_logica.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from comun.logica import calcular_promedio, clasificar_valor

datos = [1200, 1500, 1800, 1000, 900]

promedio = calcular_promedio(datos)
clasif = clasificar_valor(promedio, umbral=1500)

print("Promedio:", promedio)
print("Clasificación:", clasif)

