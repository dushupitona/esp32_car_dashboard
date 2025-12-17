from machine import Pin
import time
import math
import st7789

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
    def __init__(
        self,
        max_speed=200,
        max_rpm=8000,
        idle_rpm=800,
    ):
        # сам создаёт дисплей
        self.display = display_ili9341_config()   # 240x320, rotation=0
        self.display.clear(BLACK)

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



    # ---------- математика приборов ----------

    def compute_rpm(self, speed_kmh):
        if speed_kmh <= 0:
            return 0
        ratio = speed_kmh / self.max_speed
        ratio = max(0, min(1, ratio))
        rpm = self.idle_rpm + ratio * (self.max_rpm - self.idle_rpm)
        return int(rpm)

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
                          SPEED_COLOR,              # цвет стрелки скорости
                          "prev_speed_value")

        speed_str = "{:3d}".format(int(speed_kmh))
        self.draw_number_center(self.cx_speed, self.cy_speed, speed_str)

        # --- RPM: считаем из скорости, рисуем стрелку другим цветом ---
        rpm = self.compute_rpm(speed_kmh)
        rpm = max(0, min(self.max_rpm, rpm))

        self._draw_needle(self.cx_rpm,
                          self.cy_rpm,
                          rpm,
                          self.max_rpm,
                          WHITE,             # цвет стрелки оборотов
                          "prev_rpm_value")

        rpm_str = "{:4d}".format(rpm)
        self.draw_number_center(self.cx_rpm, self.cy_rpm, rpm_str)

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

        # ---------- иконка газа ----------
        # очистить экран
        try:
            self.display1.fill(0)   # ST7789
        except AttributeError:
            self.display1.clear(0)

        sw = 240
        sh = 135


        x = (sw // 2) - 24
        y = (sh // 2) - 24

        draw_icon_48x48(self.display1, gas, x, y)


        # внешний дисплей с приборами
        self.outer = outer_display

        # физические значения
        self.speed_kmh = 0

        # затухание скорости
        self.DECAY_INTERVAL_MS = 200
        self.DECAY_STEP_KMH = 1
        self.last_decay_ms = time.ticks_ms()

        # кнопка "газ" (увеличение скорости)
        self._btn_turn_pressed = False
        self.btn_turn = Pin(12, Pin.IN, Pin.PULL_UP)
        self.btn_turn.irq(trigger=Pin.IRQ_FALLING, handler=self._btn_turn_irq)

        # --- поворотники: светодиоды ---
        self.led_right = Pin(25, Pin.OUT)
        self.led_left = Pin(26, Pin.OUT)

        # изначально выключены
        self.led_right.off()
        self.led_left.off()

        # --- поворотники: кнопки ---
        self.btn_left = Pin(0, Pin.IN, Pin.PULL_UP)
        self.btn_right = Pin(35, Pin.IN, Pin.PULL_UP)

        # --- мигание поворотников ---
        self.BLINK_INTERVAL_MS = 500  # период мигания, мс
        self.last_blink_ms = time.ticks_ms()
        self.blink_state = False      # False = выключено, True = включено

        # первый раз обновим всё
        self.outer.update(self.speed_kmh, force=True)

    # ================= IRQ =================

    def _btn_turn_irq(self, pin):
        self._btn_turn_pressed = True

    # ================= Логика: кнопка + затухание + поворотники =================

    def process(self):
        changed = False
        now = time.ticks_ms()

        # --- газ: кнопка увеличивает скорость ---
        if self._btn_turn_pressed:
            self._btn_turn_pressed = False
            if self.speed_kmh < self.outer.max_speed:
                self.speed_kmh += 5
                if self.speed_kmh > self.outer.max_speed:
                    self.speed_kmh = self.outer.max_speed
                changed = True

        # --- затухание скорости ---
        if time.ticks_diff(now, self.last_decay_ms) >= self.DECAY_INTERVAL_MS:
            self.last_decay_ms = now
            if self.speed_kmh > 0:
                self.speed_kmh -= self.DECAY_STEP_KMH
                if self.speed_kmh < 0:
                    self.speed_kmh = 0
                changed = True

        # --- чтение кнопок поворотников (активный уровень: 0 = нажата) ---
        left_pressed = (self.btn_left.value() == 0)
        right_pressed = (self.btn_right.value() == 0)

        # если хотя бы один поворотник активен — обновляем фазу мигания
        if left_pressed or right_pressed:
            if time.ticks_diff(now, self.last_blink_ms) >= self.BLINK_INTERVAL_MS:
                self.last_blink_ms = now
                self.blink_state = not self.blink_state
        else:
            # если кнопки отпущены — поворотники гасим и сбрасываем фазу
            self.blink_state = False

        # --- управление светодиодами поворотников ---
        if left_pressed:
            if self.blink_state:
                self.led_left.on()
            else:
                self.led_left.off()
        else:
            self.led_left.off()

        if right_pressed:
            if self.blink_state:
                self.led_right.on()
            else:
                self.led_right.off()
        else:
            self.led_right.off()

        # --- вывод состояния поворотников на внешний дисплей ---
        self.outer.draw_turn_signals(
            left_on=(left_pressed and self.blink_state),
            right_on=(right_pressed and self.blink_state)
        )

        # --- обновление приборов ---
        if changed:
            self.outer.update(self.speed_kmh)


if __name__ == "__main__":
    outer = OuterDisplay()
    esp = ESP32(outer_display=outer)
    while True:
        esp.process()
        time.sleep_ms(10)
