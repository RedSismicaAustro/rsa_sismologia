from machine import I2C, Pin

class BusI2C:
    def __init__(self, scl=22, sda=21, freq=100_000):
        self.i2c = I2C(
            0,
            scl=Pin(scl),
            sda=Pin(sda),
            freq=freq
        )

    def scan(self):
        return self.i2c.scan()

    def read(self, addr, nbytes):
        return self.i2c.readfrom(addr, nbytes)

    def write(self, addr, data):
        self.i2c.writeto(addr, data)

    def write_read(self, addr, wdata, nbytes):
        self.i2c.writeto(addr, wdata)
        return self.i2c.readfrom(addr, nbytes)
