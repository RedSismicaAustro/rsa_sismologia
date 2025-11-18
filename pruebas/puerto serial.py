import serial
try:
    ser = serial.Serial("COM4", 9600, timeout=1)
    print("Abierto OK")
    ser.close()
except Exception as e:
    print("ERROR:", e)