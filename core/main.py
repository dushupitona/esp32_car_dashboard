from machine import Pin
import time
import math
import st7789
import gc

from ili9341 import color565
from config import display_lilygo_config, display_ili9341_config


from icons import gas

# --- цвета для ILI9341 ---
BLACK = color565(0, 0, 0)
GREEN = color565(0, 255, 0)
WHITE = color565(255, 255, 255)

GREEN_TICK = color565(0, 255, 0)
PURPLE_TICK = color565(139, 0, 255)

SPEED_COLOR = color565(199, 0, 56)


class OuterDisplay:
    def __init__(self):
        # сам создаёт дисплей
        self.display = display_ili9341_config()   # 240x320, rotation=0
        self.display.clear(BLACK)

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

        # состояния поворотников (для отрисовки на экране)
        self.prev_left_on = None
        self.prev_right_on = None

        # геометрия индикаторов поворотников — размещение стрелок
        self.turn_led_radius = 6

        # левая стрелка — справа сверху
        self.turn_left_x  = 200
        self.turn_left_y  = 20

        # правая стрелка — справа снизу
        self.turn_right_x = 200
        self.turn_right_y = 300


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
        # рамка круга — сейчас тем же цветом, что и стрелка скорости
        self.draw_circle_outline(cx, cy, self.radius_outer + 8, SPEED_COLOR)

        # подпись снизу, в свободных 90°
        tw = len(label) * 8
        angle_text = math.radians(180)

        text_radius = self.radius_outer + 12
        text_x = int(cx + text_radius * math.cos(angle_text)) - tw // 2
        text_y = int(cy + text_radius * math.sin(angle_text)) - 4

        self.display.draw_text8x8(
            text_x,
            text_y,
            label,
            SPEED_COLOR,
            BLACK,
            rotate=90
        )

        # риски
        self.draw_ticks(cx, cy)

    def draw_ticks(self, cx, cy,
                   num_major=13,   # количество больших рисок
                   num_minor=4):   # мелких между ними

        start_angle = 225
        total_span = 270

        if num_major < 2:
            return

        step_major = total_span / (num_major - 1)

        for i in range(num_major):
            angle_deg = start_angle + i * step_major
            rad = math.radians(angle_deg)

            # --- большие риски ---
            inner_r = self.radius_outer - 18
            outer_r = self.radius_outer - 2

            x1 = int(cx + inner_r * math.cos(rad))
            y1 = int(cy + inner_r * math.sin(rad))
            x2 = int(cx + outer_r * math.cos(rad))
            y2 = int(cy + outer_r * math.sin(rad))

            self.display.draw_line(x1, y1, x2, y2, PURPLE_TICK)

            # --- мелкие риски между большими ---
            if i < num_major - 1 and num_minor > 0:
                step_minor = step_major / (num_minor + 1)

                for j in range(1, num_minor + 1):
                    a = angle_deg + j * step_minor
                    arad = math.radians(a)

                    inner_m = self.radius_outer - 12
                    outer_m = self.radius_outer - 4

                    mx1 = int(cx + inner_m * math.cos(arad))
                    my1 = int(cy + inner_m * math.sin(arad))
                    mx2 = int(cx + outer_m * math.cos(arad))
                    my2 = int(cy + outer_m * math.sin(arad))

                    self.display.draw_line(mx1, my1, mx2, my2, GREEN_TICK)

    def draw_background(self):
        self.display.clear(BLACK)
        # верхний прибор — скорость
        self.draw_one_background(self.cx_speed, self.cy_speed, "KM/H")
        # нижний прибор — обороты
        self.draw_one_background(self.cx_rpm, self.cy_rpm, "RPM")

        # индикаторы поворотников (выключены)
        self.draw_turn_signals(False, False)

    def draw_number_center(self, cx, cy, text):
        """Стираем прямоугольник в центре и пишем число."""
        w = len(text) * 8
        h = 8
        x0 = cx - w // 2
        y0 = cy - h // 2
        self.fill_rect_fast(x0 - 2, y0 - 2, w + 4, h + 4, BLACK)
        self.display.draw_text8x8(x0, y0, text, GREEN, BLACK, rotate=90)

    # ---------- поворотники на экране ----------

    def _draw_turn_arrow(self, x, y, on, is_left, prev_attr_name):
        """Рисует индикатор поворотника в виде стрелки."""
        prev = getattr(self, prev_attr_name)

        # если состояние не изменилось — не перерисовываем
        if prev is not None and prev == on:
            return

        # размеры стрелки
        w = 10   # длина
        h = 6    # полувысота

        # очищаем область вокруг стрелки
        self.fill_rect_fast(x - w - 3, y - h - 3, 2 * (w + 3), 2 * (h + 3), BLACK)

        # цвет включён/выключен
        color_on = GREEN_TICK
        color_off = color565(40, 40, 40)
        col = color_on if on else color_off

        # координаты треугольника
        if is_left:
            p1 = (x,     y - h)   # острие ВВЕРХ
            p2 = (x - w, y + h)   # левый нижний
            p3 = (x + w, y + h)   # правый нижний
        else:
            # такая же, просто другая запись — обе вниз
            p1 = (x,     y + h)
            p2 = (x - w, y - h)
            p3 = (x + w, y - h)


        # рисуем контур треугольника (3 линии)
        self.display.draw_line(p1[0], p1[1], p2[0], p2[1], col)
        self.display.draw_line(p2[0], p2[1], p3[0], p3[1], col)
        self.display.draw_line(p3[0], p3[1], p1[0], p1[1], col)

        setattr(self, prev_attr_name, on)


    def draw_turn_signals(self, left_on, right_on):
        self._draw_turn_arrow(self.turn_left_x,  self.turn_left_y,  left_on,  True,  "prev_left_on")
        self._draw_turn_arrow(self.turn_right_x, self.turn_right_y, right_on, False, "prev_right_on")


    # ---------- стрелки ----------

    def _value_to_angle_deg(self, value, max_value):
        """
        Преобразуем значение (0..max_value) в угол стрелки,
        направление инвертировано (двигается в противоположную сторону).
        """
        if max_value <= 0:
            return 225

        ratio = value / max_value
        ratio = max(0, min(1, ratio))

        start_angle = 225       # начальная точка
        total_span = 270        # полный ход

        # инвертированное направление
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

    def update(self, speed, rpm, max_speed, max_rpm):
        # ограничения (можно и тут, но лучше в ESP32)
        if speed < 0: speed = 0
        if rpm < 0: rpm = 0
        if speed > max_speed: speed = max_speed
        if rpm > max_rpm: rpm = max_rpm

        # SPEED
        self._draw_needle(self.cx_speed, self.cy_speed, speed, max_speed,
                          SPEED_COLOR, "prev_speed_value")
        self.draw_number_center(self.cx_speed, self.cy_speed, "{:3d}".format(int(speed)))

        # RPM
        self._draw_needle(self.cx_rpm, self.cy_rpm, rpm, max_rpm,
                          WHITE, "prev_rpm_value")
        self.draw_number_center(self.cx_rpm, self.cy_rpm, "{:4d}".format(int(rpm)))


def draw_icon_48x48(display, icon_u16, x, y, w=48, h=48):
    """
    icon_u16: список/array из RGB565 uint16 (len = 48*48)
    """
    buf = bytearray(w * h * 2)
    i = 0
    for c in icon_u16:
        buf[i]     = (c >> 8) & 0xFF   # старший байт
        buf[i + 1] = c & 0xFF          # младший байт
        i += 2

    display.blit_buffer(buf, x, y, w, h)


class ESP32:
    def __init__(self, outer_display, max_speed, max_rpm, idle_rpm):
        # ---------- встроенный ST7789 ----------
        gc.collect()
        self.display1 = display_lilygo_config()
        self.display1.init()
        try:
            self.display1.backlight_on()
        except AttributeError:
            try:
                self.display1.backlight.on()
            except:
                pass

        # очистка
        self._d1_clear(0x0000)

        # размеры экрана (безопасно для разных драйверов)
        sw, sh = self._disp_size()

        # ---------- состояния ----------
        self.outer = outer_display

        self.curr_speed = 0
        self.curr_fuel = 0
        self.curr_rpm = 0

        self.max_speed = max_speed
        self.max_rpm = max_rpm
        self.idle_rpm = idle_rpm

        # ---------- иконка газа ----------
        self.icon_x = (sw // 2) - 24
        self.icon_y = (sh // 2) - 24
        draw_icon_48x48(self.display1, gas, self.icon_x, self.icon_y)

        # ---------- индикатор топлива (3 палочки рядом с иконкой) ----------
        self.prev_fuel_bars = None
        self._fuel_ui_init(sw, sh)
        self._draw_fuel_bars(self.curr_fuel)

        # --- заправка ---
        self.REFUEL_RATE_PER_SEC = 10
        self.last_refuel_ms = time.ticks_ms()

        # --- расход топлива от RPM ---
        self.FUEL_BASE_PER_SEC = 0.04
        self.FUEL_MAX_PER_SEC  = 0.60
        self.last_fuel_ms = time.ticks_ms()
        self.NO_FUEL_DECAY_STEP = 3

        # затухание скорости
        self.DECAY_INTERVAL_MS = 200
        self.DECAY_STEP_KMH = 1
        self.last_decay_ms = time.ticks_ms()

        # кнопка "газ" (разгон)
        self._btn_turn_pressed = False
        self.btn_turn = Pin(12, Pin.IN, Pin.PULL_UP)
        self.btn_turn.irq(trigger=Pin.IRQ_FALLING, handler=self._btn_turn_irq)

        # кнопка "заправки"
        self.btn_gas = Pin(32, Pin.IN, Pin.PULL_UP)

        # --- пищалка (buzzer) ---
        self.buzzer = Pin(17, Pin.OUT)
        self.buzzer.off()

        self.BUZZER_INTERVAL_MS = 400   # период бипа
        self.last_buzzer_ms = time.ticks_ms()
        self.buzzer_state = False


        # --- поворотники: светодиоды ---
        self.led_right = Pin(25, Pin.OUT)
        self.led_left = Pin(26, Pin.OUT)
        self.led_right.off()
        self.led_left.off()

        # --- поворотники: кнопки ---
        self.btn_left = Pin(0, Pin.IN, Pin.PULL_UP)
        self.btn_right = Pin(35, Pin.IN, Pin.PULL_UP)

        # --- мигание поворотников ---
        self.BLINK_INTERVAL_MS = 500
        self.last_blink_ms = time.ticks_ms()
        self.blink_state = False

        # стартовый вывод приборов
        self.curr_rpm = self.compute_rpm(self.curr_speed)
        self.outer.update(self.curr_speed, self.curr_rpm, self.max_speed, self.max_rpm)

    # =================== утилиты дисплея ST7789 ===================

    def _disp_size(self):
        d = self.display1
        if hasattr(d, "width") and callable(d.width):
            w = d.width()
        else:
            w = getattr(d, "width", 240)

        if hasattr(d, "height") and callable(d.height):
            h = d.height()
        else:
            h = getattr(d, "height", 135)

        return int(w), int(h)

    def _d1_clear(self, color=0x0000):
        d = self.display1
        try:
            d.fill(color)
        except AttributeError:
            try:
                d.clear(color)
            except:
                pass

    def _d1_fill_rect(self, x, y, w, h, color):
        x = int(x); y = int(y); w = int(w); h = int(h)
        if w <= 0 or h <= 0:
            return
        d = self.display1
        if hasattr(d, "fill_rect"):
            d.fill_rect(x, y, w, h, color)
        elif hasattr(d, "hline"):
            for yy in range(y, y + h):
                d.hline(x, yy, w, color)
        else:
            for yy in range(y, y + h):
                d.draw_hline(x, yy, w, color)

    # =================== топливо: 3 палочки ===================

    def _fuel_ui_init(self, sw, sh):
        # справа от иконки
        self.fuel_x = self.icon_x + 48 + 8
        # по центру иконки
        self.fuel_y = self.icon_y + 18

        # --- ГОРИЗОНТАЛЬНЫЕ палочки ---
        self.fuel_bar_w = 14   # ширина (СДЕЛАЛИ ШИРЕ)
        self.fuel_bar_h = 6    # высота
        self.fuel_gap = 4      # расстояние между палочками

        self.FUEL_ON  = 0x07E0   # зелёный
        self.FUEL_OFF = 0x2104   # тёмно-серый
        self.FUEL_BG  = 0x0000   # чёрный
        self.FUEL_OUT = 0xFFFF   # рамка


    def _fuel_to_bars(self, fuel_percent):
        if fuel_percent <= 0:
            return 0
        if fuel_percent <= 33:
            return 1
        if fuel_percent <= 66:
            return 2
        return 3

    def _draw_fuel_bars(self, fuel_percent):
        bars = self._fuel_to_bars(fuel_percent)
        if self.prev_fuel_bars is not None and bars == self.prev_fuel_bars:
            return

        # очистить область
        total_w = 3 * self.fuel_bar_w + 2 * self.fuel_gap + 6
        total_h = self.fuel_bar_h + 6
        self._d1_fill_rect(
            self.fuel_x - 3,
            self.fuel_y - 3,
            total_w,
            total_h,
            self.FUEL_BG
        )

        d = self.display1

        for i in range(3):
            # --- ГОРИЗОНТАЛЬНО ---
            x = self.fuel_x + i * (self.fuel_bar_w + self.fuel_gap)
            y = self.fuel_y

            # выключенная палочка
            self._d1_fill_rect(
                x, y,
                self.fuel_bar_w,
                self.fuel_bar_h,
                self.FUEL_OFF
            )

            # включенная
            if i < bars:
                self._d1_fill_rect(
                    x, y,
                    self.fuel_bar_w,
                    self.fuel_bar_h,
                    self.FUEL_ON
                )

            # рамка
            if hasattr(d, "rect"):
                d.rect(x, y, self.fuel_bar_w, self.fuel_bar_h, self.FUEL_OUT)

        self.prev_fuel_bars = bars


    # =================== IRQ ===================

    def _btn_turn_irq(self, pin):
        self._btn_turn_pressed = True

    # =================== логика ===================

    def compute_rpm(self, curr_speed):
        if curr_speed <= 0:
            return 0
        ratio = curr_speed / self.max_speed
        ratio = max(0, min(1, ratio))
        rpm = self.idle_rpm + ratio * (self.max_rpm - self.idle_rpm)
        return int(rpm)

    def process(self):
        changed = False
        now = time.ticks_ms()

        # --- кнопки поворотников (0 = нажата) ---
        left_pressed = (self.btn_left.value() == 0)
        right_pressed = (self.btn_right.value() == 0)

        # --- кнопка заправки ---
        gas_pressed = (self.btn_gas.value() == 0)

        # 0) если бак пустой — разгон запрещён (но скорость НЕ обнуляем резко)
        if self.curr_fuel <= 0:
            self._btn_turn_pressed = False

        # =========================
        # 1) Взаимоисключение: заправка VS движение
        #    Заправка ТОЛЬКО при speed==0
        # =========================
        if gas_pressed:
            # разгон игнорируем
            self._btn_turn_pressed = False

            if self.curr_speed > 0:
                # едем -> заправка запрещена, только тормозим к 0
                self.curr_speed -= 2
                if self.curr_speed < 0:
                    self.curr_speed = 0
                changed = True

                # не накапливаем время "заправки" пока тормозим
                self.last_refuel_ms = now
            else:
                # стоим -> можно заправляться
                dt_ms = time.ticks_diff(now, self.last_refuel_ms)
                if dt_ms >= 1000:
                    steps = dt_ms // 1000
                    self.last_refuel_ms = time.ticks_add(self.last_refuel_ms, steps * 1000)

                    self.curr_fuel += steps * self.REFUEL_RATE_PER_SEC
                    if self.curr_fuel > 100:
                        self.curr_fuel = 100

                    changed = True
        else:
            # не заправляемся — сбрасываем таймер заправки
            self.last_refuel_ms = now

            # =========================
            # 2) Газ: кнопка увеличивает скорость (ТОЛЬКО если есть топливо)
            # =========================
            if self._btn_turn_pressed:
                self._btn_turn_pressed = False

                # если топлива нет — просто игнорируем разгон (без резкого stop)
                if self.curr_fuel > 0:
                    if self.curr_speed < self.max_speed:
                        self.curr_speed += 5
                        if self.curr_speed > self.max_speed:
                            self.curr_speed = self.max_speed
                        changed = True

        # =========================
        # 3) Затухание скорости
        # =========================
        if time.ticks_diff(now, self.last_decay_ms) >= self.DECAY_INTERVAL_MS:
            self.last_decay_ms = now

            if self.curr_speed > 0:
                step = self.NO_FUEL_DECAY_STEP if (self.curr_fuel <= 0) else self.DECAY_STEP_KMH
                self.curr_speed -= step
                if self.curr_speed < 0:
                    self.curr_speed = 0
                changed = True

        # =========================
        # 4) Расход топлива от RPM (только если НЕ заправляемся и едем)
        # =========================
        if (not gas_pressed) and self.curr_speed > 0 and self.curr_fuel > 0:
            self.curr_rpm = self.compute_rpm(self.curr_speed)

            rpm_ratio = self.curr_rpm / self.max_rpm
            rpm_ratio = 0 if rpm_ratio < 0 else (1 if rpm_ratio > 1 else rpm_ratio)

            burn_per_sec = self.FUEL_BASE_PER_SEC + rpm_ratio * (self.FUEL_MAX_PER_SEC - self.FUEL_BASE_PER_SEC)

            dt_ms = time.ticks_diff(now, self.last_fuel_ms)
            if dt_ms > 0:
                self.last_fuel_ms = now

                self.curr_fuel -= burn_per_sec * (dt_ms / 1000.0)
                if self.curr_fuel < 0:
                    self.curr_fuel = 0

                # ВАЖНО: НЕ обнуляем скорость мгновенно — докатываемся через затухание
                changed = True
        else:
            # чтобы не накапливался dt, когда стоим/заправляемся
            self.last_fuel_ms = now

    
        # =========================
        # 4.5) Пищалка при пустом баке
        # =========================
        if self.curr_fuel <= 0:
            if time.ticks_diff(now, self.last_buzzer_ms) >= self.BUZZER_INTERVAL_MS:
                self.last_buzzer_ms = now
                self.buzzer_state = not self.buzzer_state
                self.buzzer.value(1 if self.buzzer_state else 0)
        else:
            # топливо появилось — пищалку выключаем
            self.buzzer_state = False
            self.buzzer.off()


        # =========================
        # 5) Поворотники
        # =========================
        if left_pressed or right_pressed:
            if time.ticks_diff(now, self.last_blink_ms) >= self.BLINK_INTERVAL_MS:
                self.last_blink_ms = now
                self.blink_state = not self.blink_state
        else:
            self.blink_state = False

        if left_pressed:
            self.led_left.on() if self.blink_state else self.led_left.off()
        else:
            self.led_left.off()

        if right_pressed:
            self.led_right.on() if self.blink_state else self.led_right.off()
        else:
            self.led_right.off()

        self.outer.draw_turn_signals(
            left_on=(left_pressed and self.blink_state),
            right_on=(right_pressed and self.blink_state)
        )

        # =========================
        # 6) Обновление приборов + палочки топлива
        # =========================
        if changed:
            if self.curr_fuel <= 0:
                self.curr_rpm = 0
            else:
                self.curr_rpm = self.compute_rpm(self.curr_speed)

            self.outer.update(self.curr_speed, self.curr_rpm, self.max_speed, self.max_rpm)
            self._draw_fuel_bars(self.curr_fuel)




if __name__ == "__main__":
    outer = OuterDisplay()
    esp = ESP32(
        outer_display=outer,
        max_speed=200,
        max_rpm=8000,
        idle_rpm=800,
    )

    while True:
        esp.process()
        time.sleep_ms(10)
