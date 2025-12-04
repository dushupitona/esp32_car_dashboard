from machine import Pin
import time
import math
import st7789
from ili9341 import Display, color565

from config import display_ili9341_config, display_lilygo_config
import vga1_16x32 as font


class ESP32:
    def __init__(self):
        # дисплеи
        self.display1 = display_lilygo_config()   # встроенный ST7789
        self.display2 = display_ili9341_config()  # внешний ILI9341

        self.display1.init()

        # "скорость"
        self.left_count = 0           # текущее значение (0–100)
        self.prev_left_count = 0      # предыдущее значение стрелки

        # флажок из прерывания
        self._left_pressed = False

        # параметры затухания скорости
        self.DECAY_INTERVAL_MS = 200   # как часто падает скорость (мс)
        self.DECAY_STEP = 1            # на сколько уменьшаем
        self.last_decay_ms = time.ticks_ms()

        # геометрия спидометра
        self.cx = 120   # центр X (для 240x135)
        self.cy = 110   # центр Y
        self.radius = 90

        # кнопки
        self.left_btn = Pin(0, Pin.IN, Pin.PULL_UP)
        self.right_btn = Pin(35, Pin.IN)

        self.left_btn.irq(trigger=Pin.IRQ_FALLING, handler=self._left_irq)

        # подсветка встроенного
        try:
            self.display1.backlight_on()
        except AttributeError:
            try:
                self.display1.backlight.on()
            except:
                pass

        # подсветка внешнего дисплея
        self.bl2 = Pin(25, Pin.OUT)
        self.bl2.on()

        # один раз рисуем фон спидометра (дуга и т.п.)
        self.draw_speedometer_background()
        # один раз рисуем начальное состояние стрелки/цифр
        self.draw_speedometer()

    # ==================== IRQ ====================

    def _left_irq(self, pin):
        self._left_pressed = True

    # ==================== Графика спидометра ====================

    def draw_arc(self, cx, cy, r, color):
        """Рисование дуги (нижняя половина круга)."""
        for angle in range(180, 361, 2):
            rad = math.radians(angle)
            x = int(cx + r * math.cos(rad))
            y = int(cy + r * math.sin(rad))
            self.display1.pixel(x, y, color)

    def draw_needle(self, cx, cy, r, value, color):
        """Стрелка слева направо (от 180° до 360°). value от 0 до 100."""
        angle = 180 + (value / 100) * 180   # 180° → 360°
        rad = math.radians(angle)
        x = int(cx + r * math.cos(rad))
        y = int(cy + r * math.sin(rad))
        self.display1.line(cx, cy, x, y, color)

    def draw_speedometer_background(self):
        """Рисуем статический фон один раз (дуга и прочее)."""
        self.display1.fill(st7789.BLACK)

        # дуга
        self.draw_arc(self.cx, self.cy, self.radius, st7789.BLUE)

        # здесь можно добавить засечки, подписи и т.д.
        # например, надпись "km/h"
        self.display1.text(
            font,
            "km/h",
            self.cx - 40,
            50,
            st7789.WHITE,
            st7789.BLACK
        )

    def draw_speedometer(self):
        """Обновляем только стрелку и цифры, дугу не трогаем."""
        # стереть старую стрелку (цветом фона)
        self.draw_needle(self.cx, self.cy, self.radius - 10,
                         self.prev_left_count, st7789.BLACK)

        # нарисовать новую стрелку
        self.draw_needle(self.cx, self.cy, self.radius - 10,
                         self.left_count, st7789.RED)
        self.prev_left_count = self.left_count

        # перерисовать числовое значение
        text = "{}".format(self.left_count)
        # зачистить область под цифрами
        self.display1.fill_rect(self.cx - 40, 10, 80, 40, st7789.BLACK)
        self.display1.text(
            font,
            text,
            self.cx - 30,
            10,
            st7789.WHITE,
            st7789.BLACK
        )

    # ==================== Логика кнопки + затухание ====================

    def process_buttons(self):
        changed = False
        now = time.ticks_ms()

        # рост "скорости" по нажатию
        if self._left_pressed:
            self._left_pressed = False
            if self.left_count < 100:
                self.left_count += 3
                if self.left_count > 100:
                    self.left_count = 100
                changed = True

        # падение "скорости" по времени
        if time.ticks_diff(now, self.last_decay_ms) >= self.DECAY_INTERVAL_MS:
            self.last_decay_ms = now
            if self.left_count > 0:
                self.left_count -= self.DECAY_STEP
                if self.left_count < 0:
                    self.left_count = 0
                changed = True

        # перерисовываем только если значение изменилось
        if changed:
            self.draw_speedometer()

    # ==================== Внешний экран (опционально) ====================

    def test(self):
        self.display1.fill(st7789.BLACK)
        self.display2.clear(color565(0, 255, 0))


if __name__ == '__main__':
    esp = ESP32()

    # если test() заливает всё чёрным/зелёным, НЕ вызывай его здесь,
    # иначе он затрёт спидометр:
    # esp.test()

    while True:
        esp.process_buttons()
        time.sleep_ms(5)
