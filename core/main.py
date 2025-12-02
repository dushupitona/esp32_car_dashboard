from machine import Pin
import time
import st7789
from ili9341 import Display, color565

from config import display_ili9341_config, display_lilygo_config

# 🔤 импорт шрифта (ПОДСТАВЬ свой, если имя другое)
import vga1_16x32 as font   # или: from fonts.bitmap import vga1_16x32 as font


class ESP32:
    def __init__(self):
        self.display1 = display_lilygo_config()   # встроенный ST7789
        self.display2 = display_ili9341_config()  # внешний ILI9341

        self.display1.init()

        # счетчик нажатий
        self.left_count = 0

        # флажок из прерывания
        self._left_pressed = False

        # кнопки
        self.left_btn = Pin(0, Pin.IN, Pin.PULL_UP)
        self.right_btn = Pin(35, Pin.IN)

        # IRQ на левую кнопку
        self.left_btn.irq(trigger=Pin.IRQ_FALLING, handler=self._left_irq)

        # подсветка встроенного
        try:
            self.display1.backlight_on()
        except AttributeError:
            try:
                self.display1.backlight.on()
            except:
                pass

        # подсветка внешнего
        self.bl2 = Pin(25, Pin.OUT)
        self.bl2.on()

        # первый вывод счётчика
        self.draw_counter()

    # ==================== IRQ ====================

    def _left_irq(self, pin):
        self._left_pressed = True

    # ==================== Логика ====================

    def draw_counter(self):
        self.display1.fill(st7789.BLACK)
        text = "Count: {}".format(self.left_count)

        # сигнатура: text(font, s, x, y, fg, bg)
        self.display1.text(font, text, 10, 10, st7789.WHITE, st7789.BLACK)

    def process_buttons(self):
        if self._left_pressed:
            self._left_pressed = False
            self.left_count += 1
            self.draw_counter()

    def test(self):
        self.display1.fill(st7789.BLACK)
        self.display2.clear(color565(0, 255, 0))


if __name__ == '__main__':
    esp = ESP32()
    esp.test()

    while True:
        esp.process_buttons()
        time.sleep_ms(10)
