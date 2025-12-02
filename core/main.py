from machine import Pin
import time
import math
import st7789
from ili9341 import Display, color565

from config import display_ili9341_config, display_lilygo_config
import vga1_16x32 as font


class ESP32:
    def __init__(self):
        self.display1 = display_lilygo_config()   # встроенный ST7789
        self.display2 = display_ili9341_config()  # внешний ILI9341

        self.display1.init()

        # значение "скорости"
        self.left_count = 0

        # флажок из прерывания
        self._left_pressed = False

        # кнопки
        self.left_btn = Pin(0, Pin.IN, Pin.PULL_UP)
        self.right_btn = Pin(35, Pin.IN)

        self.left_btn.irq(trigger=Pin.IRQ_FALLING, handler=self._left_irq)

        try:
            self.display1.backlight_on()
        except AttributeError:
            try:
                self.display1.backlight.on()
            except:
                pass

        self.bl2 = Pin(25, Pin.OUT)
        self.bl2.on()

        self.draw_speedometer()

    # ==================== IRQ ====================

    def _left_irq(self, pin):
        self._left_pressed = True

    # ==================== Спидометр ====================

    def draw_arc(self, cx, cy, r, color):
        """Рисование дуги (нижняя половина круга)."""
        for angle in range(0, 181, 2):  # шаг 2° для скорости
            rad = math.radians(angle)
            x = int(cx + r * math.cos(rad))
            y = int(cy + r * math.sin(rad))
            self.display1.pixel(x, y, color)

    def draw_needle(self, cx, cy, r, value, color):
        """Стрелка спидометра – value от 0 до 100."""
        # mapped value → 0…180°
        angle = (value / 100) * 180
        rad = math.radians(angle)

        x = int(cx + r * math.cos(rad))
        y = int(cy + r * math.sin(rad))

        # простая линия (луч)
        self.display1.line(cx, cy, x, y, color)

    def draw_speedometer(self):
        self.display1.fill(st7789.BLACK)

        cx = 120   # центр X (для 240×135 дисплея Lilygo)
        cy = 110   # центр Y
        radius = 90

        # дуга спидометра
        self.draw_arc(cx, cy, radius, st7789.BLUE)

        # стрелка
        self.draw_needle(cx, cy, radius - 10, self.left_count, st7789.RED)

        # текстовое значение
        text = "{}".format(self.left_count)
        self.display1.text(font, text, cx - 30, 10, st7789.WHITE, st7789.BLACK)

    # ==================== Кнопки ====================

    def process_buttons(self):
        if self._left_pressed:
            self._left_pressed = False
            if self.left_count < 100:
                self.left_count += 1
            self.draw_speedometer()

    # ==================== Внешний экран ====================

    def test(self):
        self.display1.fill(st7789.BLACK)
        self.display2.clear(color565(0, 255, 0))


if __name__ == '__main__':
    esp = ESP32()
    esp.test()

    while True:
        esp.process_buttons()
        time.sleep_ms(10)
