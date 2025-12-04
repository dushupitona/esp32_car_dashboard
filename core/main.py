from machine import Pin
import time
import math
import st7789

from ili9341 import color565
from config import display_lilygo_config, display_ili9341_config


# Цвета для ILI9341
BLACK = color565(0, 0, 0)
GREEN = color565(0, 255, 0)
WHITE = color565(255, 255, 255)
RED   = color565(255, 0, 0)


class ESP32:
    def __init__(self):
        # Встроенный дисплей (просто включим подсветку, рисовать не обязательно)
        self.display1 = display_lilygo_config()
        self.display1.init()
        try:
            self.display1.backlight_on()
        except AttributeError:
            try:
                self.display1.backlight.on()
            except:
                pass

        # Внешний ILI9341 – тут будет тахометр
        self.display2 = display_ili9341_config()
        self.display2.clear(BLACK)

        # Логика "оборотов"
        self.value = 0          # 0..100 (проценты шкалы)
        self.prev_level = 0     # сколько сегментов горело раньше
        self.MAX_RPM = 8000     # максимальное значение по цифрам
        self.SEGMENTS = 12      # число зелёных сегментов

        # Флаг из прерывания кнопки
        self._left_pressed = False

        # Затухание
        self.DECAY_INTERVAL_MS = 200
        self.DECAY_STEP = 1
        self.last_decay_ms = time.ticks_ms()

        # Геометрия тахометра на внешнем дисплее (240x320, rotation=0)
        self.cx = 120          # центр X
        self.cy = 160          # центр Y
        self.radius_outer = 110
        self.radius_inner = 85

        # Кнопки
        self.left_btn = Pin(0, Pin.IN, Pin.PULL_UP)
        self.right_btn = Pin(35, Pin.IN)

        self.left_btn.irq(trigger=Pin.IRQ_FALLING, handler=self._left_irq)

        # Подсветка внешнего (если на GPIO25, как раньше)
        self.bl2 = Pin(25, Pin.OUT)
        self.bl2.on()

        # Рисуем фон на внешнем экране
        self.draw_background()
        # Первый апдейт шкалы/цифр
        self.update_gauge(force=True)

    # =============== IRQ ===============

    def _left_irq(self, pin):
        self._left_pressed = True

    # =============== Графика (ILI9341) ===============

    def draw_circle_outline(self, cx, cy, r, color):
        """Грубый контур круга (для рамки)."""
        step = 3
        for angle in range(0, 360, step):
            rad = math.radians(angle)
            x = int(cx + r * math.cos(rad))
            y = int(cy + r * math.sin(rad))
            # маленькая "точка" короткой линией
            self.display2.draw_line(x, y, x, y, color)

    def draw_segment(self, index, color):
        """
        Один сегмент «барграфа» слева.
        index: 0 (внизу) .. SEGMENTS-1 (наверху).
        """
        # дуга слева: от 225° (низ-слева) до 135° (верх-слева)
        start_angle = 225
        end_angle = 135
        total_span = start_angle - end_angle  # 90°

        if self.SEGMENTS > 1:
            step = total_span / (self.SEGMENTS - 1)
        else:
            step = 0

        angle_center = start_angle - index * step
        half_width = 4  # "толщина" сегмента по углу

        for ang in range(int(angle_center - half_width),
                         int(angle_center + half_width) + 1):
            rad = math.radians(ang)
            x1 = int(self.cx + self.radius_inner * math.cos(rad))
            y1 = int(self.cy + self.radius_inner * math.sin(rad))
            x2 = int(self.cx + self.radius_outer * math.cos(rad))
            y2 = int(self.cy + self.radius_outer * math.sin(rad))
            self.display2.draw_line(x1, y1, x2, y2, color)

    def fill_rect_fast(self, x, y, w, h, color):
        """Заполнение прямоугольника через draw_hline (если нет fill_rect)."""
        for yy in range(y, y + h):
            self.display2.draw_hline(x, yy, w, color)

    def draw_background(self):
        """Фон тахометра только один раз."""
        self.display2.clear(BLACK)

        # Внешняя рамка
        self.draw_circle_outline(self.cx, self.cy, self.radius_outer + 8, GREEN)

        # Надпись RPM снизу
        # draw_text8x8(x, y, text, fg, bg, rotation)
        text = "RPM"
        tw = len(text) * 8
        self.display2.draw_text8x8(self.cx - tw // 2,
                                   self.cy + 40,
                                   text,
                                   GREEN,
                                   BLACK,
                                   0)

    def update_gauge(self, force=False):
        """Обновляет сегменты и число (на внешнем экране)."""
        # сколько сегментов должно гореть
        level = int(self.value * self.SEGMENTS / 100)

        if force:
            # сначала погасим все
            for i in range(self.SEGMENTS):
                self.draw_segment(i, BLACK)
            # и зажжём нужные
            for i in range(level):
                self.draw_segment(i, GREEN)
        else:
            # включить новые
            if level > self.prev_level:
                for i in range(self.prev_level, level):
                    self.draw_segment(i, GREEN)
            # погасить лишние
            elif level < self.prev_level:
                for i in range(level, self.prev_level):
                    self.draw_segment(i, BLACK)

        self.prev_level = level

        # число по центру
        rpm = int(self.value * self.MAX_RPM / 100)
        s = "{:4d}".format(rpm)

        # зачистим область под цифрами
        box_w = 8 * 4 + 8   # 4 цифры + чуть отступа
        box_h = 16
        x0 = self.cx - box_w // 2
        y0 = self.cy - box_h // 2
        self.fill_rect_fast(x0, y0, box_w, box_h, BLACK)

        # вывод цифр
        self.display2.draw_text8x8(x0, y0, s, GREEN, BLACK, 0)

    # =============== Логика кнопки + затухание ===============

    def process_buttons(self):
        changed = False
        now = time.ticks_ms()

        # рост по нажатию
        if self._left_pressed:
            self._left_pressed = False
            if self.value < 100:
                self.value += 5
                if self.value > 100:
                    self.value = 100
                changed = True

        # затухание по времени
        if time.ticks_diff(now, self.last_decay_ms) >= self.DECAY_INTERVAL_MS:
            self.last_decay_ms = now
            if self.value > 0:
                self.value -= self.DECAY_STEP
                if self.value < 0:
                    self.value = 0
                changed = True

        if changed:
            self.update_gauge()


if __name__ == '__main__':
    esp = ESP32()

    while True:
        esp.process_buttons()
        time.sleep_ms(10)
