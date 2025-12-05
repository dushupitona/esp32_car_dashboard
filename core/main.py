from machine import Pin
import time
import math
import st7789

from ili9341 import color565
from config import display_lilygo_config, display_ili9341_config

# --- цвета для ILI9341 ---
BLACK = color565(0, 0, 0)
GREEN = color565(0, 255, 0)
WHITE = color565(255, 255, 255)

class OuterDisplay:
    def __init__(
        self,
        max_speed=200,
        max_rpm=8000,
        idle_rpm=800,
    ):
        # сам создаёт дисплей
        self.display = display_ili9341_config()   # 240x320, rotation=0
        self.display.clear(BLACK)

        # подсветка внешнего (если на GPIO25)
        self.bl2 = Pin(25, Pin.OUT)
        self.bl2.on()

        # параметры "физики"
        self.max_speed = max_speed
        self.max_rpm = max_rpm
        self.idle_rpm = idle_rpm

        # геометрия
        self.radius_outer = 70
        self.radius_inner = 50  # можно использовать для толщины стрелки, пока не нужен

        # центры двух приборов
        self.cx_speed = 120
        self.cy_speed = 80

        self.cx_rpm = 120
        self.cy_rpm = 240

        # предыдущие значения (для стирания стрелки)
        self.prev_speed_value = None
        self.prev_rpm_value = None

        # первый фон
        self.draw_background()

    # ---------- утилиты рисования ----------

    def clear(self):
        self.display.clear(BLACK)

    def draw_circle_outline(self, cx, cy, r, color):
        """Простая окружность по точкам."""
        for ang in range(0, 360, 3):
            rad = math.radians(ang)
            x = int(cx + r * math.cos(rad))
            y = int(cy + r * math.sin(rad))
            self.display.draw_line(x, y, x, y, color)

    def fill_rect_fast(self, x, y, w, h, color):
        """Заполняем прямоугольник горизонтальными линиями."""
        for yy in range(y, y + h):
            self.display.draw_hline(x, yy, w, color)

    def draw_one_background(self, cx, cy, label):
        # рамка
        self.draw_circle_outline(cx, cy, self.radius_outer + 8, GREEN)

        # подпись (RPM / KMH) СНИЗУ круга, по центру
        tw = len(label) * 8
        text_x = cx - tw // 2

        # нижняя точка круга
        text_y = cy + self.radius_outer + 12   # 12 пикселей ниже края круга

        self.display.draw_text8x8(
            text_x,
            text_y,
            label,
            GREEN,
            BLACK,
            rotate=90
        )

        # риски по окружности
        self.draw_ticks(cx, cy)

    def draw_ticks(self, cx, cy,
               num_major=13,   # крупные риски (0..12)
               num_minor=4,    # мелкие между крупными
               color=GREEN):
        """
        Рисуем риски по дуге 270° от 225° (снизу-слева) до 225+270 (снизу-справа).
        """
        start_angle = 225
        total_span = 270

        # --- крупные риски ---
        if num_major < 2:
            return

        step_major = total_span / (num_major - 1)

        for i in range(num_major):
            angle_deg = start_angle + i * step_major
            rad = math.radians(angle_deg)

            # крупные — длиннее
            inner_r = self.radius_outer - 16
            outer_r = self.radius_outer - 2

            x1 = int(cx + inner_r * math.cos(rad))
            y1 = int(cy + inner_r * math.sin(rad))
            x2 = int(cx + outer_r * math.cos(rad))
            y2 = int(cy + outer_r * math.sin(rad))

            self.display.draw_line(x1, y1, x2, y2, color)

            # --- мелкие риски между крупными ---
            if num_minor > 0 and i < num_major - 1:
                step_minor = step_major / (num_minor + 1)
                for j in range(1, num_minor + 1):
                    a_deg = angle_deg + j * step_minor
                    a_rad = math.radians(a_deg)

                    inner_m = self.radius_outer - 10
                    outer_m = self.radius_outer - 4

                    mx1 = int(cx + inner_m * math.cos(a_rad))
                    my1 = int(cy + inner_m * math.sin(a_rad))
                    mx2 = int(cx + outer_m * math.cos(a_rad))
                    my2 = int(cy + outer_m * math.sin(a_rad))

                    self.display.draw_line(mx1, my1, mx2, my2, color)



    def draw_background(self):
        self.display.clear(BLACK)
        # верхний прибор — скорость
        self.draw_one_background(self.cx_speed, self.cy_speed, "KM/H")
        # нижний прибор — обороты
        self.draw_one_background(self.cx_rpm, self.cy_rpm, "RPM")

    def draw_number_center(self, cx, cy, text):
        """Стираем прямоугольник в центре и пишем число."""
        w = len(text) * 8
        h = 8
        x0 = cx - w // 2
        y0 = cy - h // 2
        self.fill_rect_fast(x0 - 2, y0 - 2, w + 4, h + 4, BLACK)
        self.display.draw_text8x8(x0, y0, text, GREEN, BLACK, rotate=90)

    # ---------- математика приборов ----------

    def compute_rpm(self, speed_kmh):
        if speed_kmh <= 0:
            return 0
        ratio = speed_kmh / self.max_speed
        if ratio < 0:
            ratio = 0
        if ratio > 1:
            ratio = 1
        rpm = self.idle_rpm + ratio * (self.max_rpm - self.idle_rpm)
        return int(rpm)

    # ---------- стрелки ----------

    def _value_to_angle_deg(self, value, max_value):
        """
        Преобразуем значение (0..max_value) в угол стрелки,
        но направление инвертировано.
        """
        if max_value <= 0:
            return 225

        ratio = value / max_value
        ratio = max(0, min(1, ratio))

        start_angle = 225       # начальная точка
        total_span = 270        # полный ход

        # --- инвертированное направление ---
        angle = start_angle + ratio * total_span

        return angle


    def _draw_needle(self, cx, cy, value, max_value, color, prev_value_attr_name):

        prev_value = getattr(self, prev_value_attr_name)

        # если нет изменения — не перерисовываем
        if prev_value is not None and prev_value == value:
            return

        # длина стрелки (80% круга)
        needle_len = int(self.radius_outer * 0.8)

        # стереть старую
        if prev_value is not None:
            prev_angle_deg = self._value_to_angle_deg(prev_value, max_value)
            prev_rad = math.radians(prev_angle_deg)
            px = int(cx + needle_len * math.cos(prev_rad))
            py = int(cy + needle_len * math.sin(prev_rad))
            self.display.draw_line(cx, cy, px, py, BLACK)

        # нарисовать новую
        angle_deg = self._value_to_angle_deg(value, max_value)
        rad = math.radians(angle_deg)
        x = int(cx + needle_len * math.cos(rad))
        y = int(cy + needle_len * math.sin(rad))
        self.display.draw_line(cx, cy, x, y, color)

        setattr(self, prev_value_attr_name, value)



    # ---------- публичный метод: обновить по скорости ----------

    def update(self, speed_kmh, force=False):
        """
        Обновить оба прибора исходя из скорости.
        ESP32 просто зовёт .update(speed_kmh).
        """
        # ограничения
        if speed_kmh < 0:
            speed_kmh = 0
        if speed_kmh > self.max_speed:
            speed_kmh = self.max_speed

        # --- SPEED: стрелка + число ---
        self._draw_needle(self.cx_speed,
                          self.cy_speed,
                          speed_kmh,
                          self.max_speed,
                          GREEN,              # цвет стрелки скорости
                          "prev_speed_value")

        speed_str = "{:3d}".format(int(speed_kmh))
        self.draw_number_center(self.cx_speed, self.cy_speed, speed_str)

        # --- RPM: считаем из скорости, рисуем стрелку другим цветом ---
        rpm = self.compute_rpm(speed_kmh)
        if rpm < 0:
            rpm = 0
        if rpm > self.max_rpm:
            rpm = self.max_rpm

        self._draw_needle(self.cx_rpm,
                          self.cy_rpm,
                          rpm,
                          self.max_rpm,
                          WHITE,             # цвет стрелки оборотов
                          "prev_rpm_value")

        rpm_str = "{:4d}".format(rpm)
        self.draw_number_center(self.cx_rpm, self.cy_rpm, rpm_str)


class ESP32:
    def __init__(self, outer_display):
        # ---------- встроенный ST7789: только подсветка ----------
        self.display1 = display_lilygo_config()
        self.display1.init()
        try:
            self.display1.backlight_on()
        except AttributeError:
            try:
                self.display1.backlight.on()
            except:
                pass

        # внешний дисплей с приборами
        self.outer = outer_display

        # физические значения
        self.speed_kmh = 0

        # затухание
        self.DECAY_INTERVAL_MS = 200
        self.DECAY_STEP_KMH = 1
        self.last_decay_ms = time.ticks_ms()

        # флаг прерывания кнопки
        self._btn_pressed = False

        # кнопка на GPIO0
        self.btn = Pin(0, Pin.IN, Pin.PULL_UP)
        self.btn.irq(trigger=Pin.IRQ_FALLING, handler=self._btn_irq)

        # первый раз обновим всё
        self.outer.update(self.speed_kmh, force=True)

    # ================= IRQ =================

    def _btn_irq(self, pin):
        self._btn_pressed = True

    # ================= Логика: кнопка + затухание =================

    def process(self):
        changed = False
        now = time.ticks_ms()

        # кнопка повышает скорость
        if self._btn_pressed:
            self._btn_pressed = False
            if self.speed_kmh < self.outer.max_speed:
                self.speed_kmh += 5
                if self.speed_kmh > self.outer.max_speed:
                    self.speed_kmh = self.outer.max_speed
                changed = True

        # затухание
        if time.ticks_diff(now, self.last_decay_ms) >= self.DECAY_INTERVAL_MS:
            self.last_decay_ms = now
            if self.speed_kmh > 0:
                self.speed_kmh -= self.DECAY_STEP_KMH
                if self.speed_kmh < 0:
                    self.speed_kmh = 0
                changed = True

        if changed:
            # вот главный момент: просто передаём скорость
            self.outer.update(self.speed_kmh)


if __name__ == "__main__":
    outer = OuterDisplay()
    esp = ESP32(outer_display=outer)
    while True:
        esp.process()
        time.sleep_ms(10)
