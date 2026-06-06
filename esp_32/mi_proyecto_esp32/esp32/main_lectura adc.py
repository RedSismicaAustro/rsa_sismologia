from time import sleep
from sensor_adc import SensorADC
from logica import calcular_promedio, clasificar_valor

print("Iniciando sistema ESP32...")

sensor = SensorADC(pin=32)

while True:
    valor = sensor.leer_adc()
    promedio = calcular_promedio([valor])
    estado = clasificar_valor(promedio,0.5)
    print(f"{valor},{estado}")
    sleep(1)
