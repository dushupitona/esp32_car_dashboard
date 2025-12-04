import st7789
from ili9341 import Display, color565
from machine import Pin, SPI


# ---------- SPI для встроенного ST7789 (как раньше) ----------
spi_st = SPI(2, baudrate=40_000_000, sck=Pin(18), mosi=Pin(19), miso=None)

def display_lilygo_config(rotation=3):
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