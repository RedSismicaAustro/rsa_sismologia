from machine import Pin
from time import sleep_ms

dt = Pin(4, Pin.IN)
sck = Pin(33, Pin.OUT)

sck.value(0)
sleep_ms(1000)

while True:
    print("DT:", dt.value(), "SCK:", sck.value())
    sleep_ms(500)