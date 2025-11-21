from machine import Pin, SPI
import st7789

import time

def display_lilygo_config(rotation=0, buffer_size=0, options=0):
    return st7789.ST7789(
        SPI(2, baudrate=40000000, sck=Pin(18), mosi=Pin(19), miso=None),
        135,
        240,
        reset=Pin(23, Pin.OUT),
        cs=Pin(5, Pin.OUT),
        dc=Pin(16, Pin.OUT),
        backlight=Pin(4, Pin.OUT),
        rotation=rotation,
        options=options,
        buffer_size=buffer_size
    )


class ESP32:
    def __init__(self, display_factory: callable):
        self.display1 = display_factory()
        self.display1.init()

        self.left_btn = Pin(0, Pin.IN)
        self.right_btn = Pin(35, Pin.IN)

        try:
            self.display1.backlight.on()
        except:
            pass

    def turn(self):
        self.display1.fill(st7789.RED)


if __name__ == '__main__':
    esp = ESP32(display_lilygo_config)

    esp.turn()

    while True:
        time.sleep(1)
