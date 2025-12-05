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
        segments=12,
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

        # сегменты и геометрия
        self.SEGMENTS = segments
        self.radius_outer = 70
        self.radius_inner = 50

        self.cx_speed = 120
        self.cy_speed = 80

        self.cx_rpm = 120
        self.cy_rpm = 240

        # прошлые уровни, чтобы знать, что тушить/зажигать
        self.prev_speed_level = 0
        self.prev_rpm_level = 0

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

    def draw_segment(self, cx, cy, index, color):
        """
        Один сегмент дуги слева.
        index: 0 (нижний) .. SEGMENTS-1 (верхний).
        """
        start_angle = 225   # низ-слева
        end_angle = 135     # верх-слева
        total_span = start_angle - end_angle  # 90°

        if self.SEGMENTS > 1:
            step = total_span / (self.SEGMENTS - 1)
        else:
            step = 0

        angle_center = start_angle - index * step
        half_width = 4  # «толщина» сегмента по углу

        for ang in range(int(angle_center - half_width),
                         int(angle_center + half_width) + 1):
            rad = math.radians(ang)
            x1 = int(cx + self.radius_inner * math.cos(rad))
            y1 = int(cy + self.radius_inner * math.sin(rad))
            x2 = int(cx + self.radius_outer * math.cos(rad))
            y2 = int(cy + self.radius_outer * math.sin(rad))
            self.display.draw_line(x1, y1, x2, y2, color)

    def draw_one_background(self, cx, cy, label):
        # рамка
        self.draw_circle_outline(cx, cy, self.radius_outer + 8, GREEN)
        # подпись (RPM / KMH) под центром
        tw = len(label) * 8
        self.display.draw_text8x8(cx - tw // 2,
                                  cy + 30,
                                  label,
                                  GREEN,
                                  BLACK,
                                  rotate=90)

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

    # ---------- публичный метод: обновить по скорости ----------

    def update(self, speed_kmh, force=False):
        """
        Обновить оба прибора исходя из скорости.
        ESP32 просто зовёт .update(speed_kmh).
        """
        # --- SPEED ---
        speed_level = int(speed_kmh * self.SEGMENTS / self.max_speed)
        if speed_level < 0:
            speed_level = 0
        if speed_level > self.SEGMENTS:
            speed_level = self.SEGMENTS

        if force:
            # гасим все и зажигаем нужные
            for i in range(self.SEGMENTS):
                self.draw_segment(self.cx_speed, self.cy_speed, i, BLACK)
            for i in range(speed_level):
                self.draw_segment(self.cx_speed, self.cy_speed, i, GREEN)
        else:
            if speed_level > self.prev_speed_level:
                for i in range(self.prev_speed_level, speed_level):
                    self.draw_segment(self.cx_speed, self.cy_speed, i, GREEN)
            elif speed_level < self.prev_speed_level:
                for i in range(speed_level, self.prev_speed_level):
                    self.draw_segment(self.cx_speed, self.cy_speed, i, BLACK)
        self.prev_speed_level = speed_level

        # число скорости
        speed_str = "{:3d}".format(int(speed_kmh))
        self.draw_number_center(self.cx_speed, self.cy_speed, speed_str)

        # --- RPM (из скорости) ---
        rpm = self.compute_rpm(speed_kmh)
        rpm_level = int(rpm * self.SEGMENTS / self.max_rpm)
        if rpm_level < 0:
            rpm_level = 0
        if rpm_level > self.SEGMENTS:
            rpm_level = self.SEGMENTS

        if force:
            for i in range(self.SEGMENTS):
                self.draw_segment(self.cx_rpm, self.cy_rpm, i, BLACK)
            for i in range(rpm_level):
                self.draw_segment(self.cx_rpm, self.cy_rpm, i, GREEN)
        else:
            if rpm_level > self.prev_rpm_level:
                for i in range(self.prev_rpm_level, rpm_level):
                    self.draw_segment(self.cx_rpm, self.cy_rpm, i, GREEN)
            elif rpm_level < self.prev_rpm_level:
                for i in range(rpm_level, self.prev_rpm_level):
                    self.draw_segment(self.cx_rpm, self.cy_rpm, i, BLACK)
        self.prev_rpm_level = rpm_level

        # число оборотов
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
