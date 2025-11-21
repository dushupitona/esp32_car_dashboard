from machine import Pin, SPI
import st7789
import time

TFA = 40
BFA = 40

def config(rotation=0, buffer_size=0, options=0):
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
        buffer_size= buffer_size)

tft = config()

if __name__ == '__main__':
    # обязательно инициализировать дисплей
    tft.init()

    # включение подсветки
    try:
        tft.backlight.on()
    except:
        pass

    # экран должен стать зелёным
    tft.text(st7789.GREEN)

    while True:
        time.sleep(1)
