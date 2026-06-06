# esp32/drivers/sensor_adc.py

from machine import ADC, Pin

class SensorADC:
    def __init__(self, pin=32):
        self.adc = ADC(Pin(pin))
        self.adc.atten(ADC.ATTN_11DB)   # rango hasta aproximadamente 3.3 V
        self.adc.width(ADC.WIDTH_12BIT) # 0–4095

    def leer_adc(self):
        return self.adc.read()
