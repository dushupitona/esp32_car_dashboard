from machine import Pin, SPI
import time
import st7789
from ili9341 import Display, color565


# ---------- SPI для встроенного ST7789 (как раньше) ----------
spi_st = SPI(2, baudrate=40_000_000, sck=Pin(18), mosi=Pin(19), miso=None)

def display_lilygo_config(rotation=1):
    return st7789.ST7789(
        spi_st,
        135,
        240,
        reset=Pin(23, Pin.OUT),
        cs=Pin(5, Pin.OUT),
        dc=Pin(16, Pin.OUT),
        backlight=Pin(4, Pin.OUT),
        rotation=rotation
    )


# ---------- SPI1 для внешнего 2.8" ILI9341 ----------
spi_ili = SPI(
    1,
    baudrate=40_000_000,
    sck=Pin(33),   # SCK второго дисплея
    mosi=Pin(13),  # MOSI второго дисплея
    miso=None      # можно добавить Pin(12), если нужен MISO
)

def display_ili9341_config(rotation=0):
    return Display(
        spi_ili,
        cs=Pin(2, Pin.OUT),     # CS
        dc=Pin(15, Pin.OUT),    # DC / RS
        rst=Pin(27, Pin.OUT),   # RST
        width=240,
        height=320,
        rotation=rotation,
        bgr=True
    )


class ESP32:
    def __init__(self):
        self.display1 = display_lilygo_config()
        self.display2 = display_ili9341_config()

        # ST7789 нужно отдельно инициализировать
        self.display1.init()
        # ILI9341 инициализируется внутри __init__ класса Display

        # кнопки
        self.left_btn = Pin(0, Pin.IN)
        self.right_btn = Pin(35, Pin.IN)

        # подсветка встроенного
        try:
            self.display1.backlight_on()
        except AttributeError:
            try:
                self.display1.backlight.on()
            except:
                pass

        # подсветка внешнего дисплея на GPIO25
        self.bl2 = Pin(25, Pin.OUT)
        self.bl2.on()

    def test(self):
        # встроенный ST7789
        self.display1.fill(st7789.RED)

        # внешний ILI9341
        self.display2.clear(color565(0, 255, 0))  # зелёный фон


if __name__ == '__main__':
    esp = ESP32()
    esp.test()

    while True:
        time.sleep(1)
