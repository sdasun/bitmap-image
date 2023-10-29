from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QDial, QLabel, QPushButton, QScrollArea
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QPaintEvent
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, Qt
from copy import deepcopy
BITMAP_IMAGE = "image.bmp"
FILE_HEADER_SIZE = 14
BITMAP_HEADER_SIZE = 40
class BitmapImage(QObject): # noqa
    pixal_array_changed = pyqtSignal(list, name="pixalArrayChanged")
    pixal_array: list[list[int]] = []
    original_pixel_array: list[list[int]] = []
    hue = 0
    saturation = 50
    lightness = 0
    app = None

    def __init__(self, filepath: str, app: QApplication | None = None):
        """initialize the class with a filepath to a bitmap image"""
        super().__init__()
        self.filepath = filepath
        self.load_image_into_array()
        self.app = app

    def set_loading_cursor(self):
        """set the cursor to the loading cursor"""
        if self.app:
            self.app.setOverrideCursor(Qt.CursorShape.WaitCursor)

    def set_default_cursor(self):
        """set the cursor to the default cursor"""
        if self.app:
            self.app.restoreOverrideCursor()

    def load_image_into_array(self):
        """
        This function loads a bitmap image into an array of pixels.

        First it will read header information from the bitmap file.
        Then it will read the pixel data from the bitmap file.
        """
        self.set_loading_cursor()
        with open(self.filepath, "rb") as f:
            # Read the header information from the bitmap file
            self.file_header = f.read(FILE_HEADER_SIZE)
            self.bitmap_header = f.read(BITMAP_HEADER_SIZE)
            self.pixel_data = f.read()

        # Read the pixel data from the bitmap file
        pixel_array: list[list[int]] = []
        for i in range(0, len(self.pixel_data), 3):
            # add BRG values to the pixel array
            pixel_array.append(
                [
                    int(self.pixel_data[i]), # blue
                    int(self.pixel_data[i+1]), # green
                    int(self.pixel_data[i+2]) # red
                ]
            )

        self.original_pixel_array = deepcopy(pixel_array)
        self.pixel_array = pixel_array

        # integers are stored as signged in the bitmap header
        height = int.from_bytes(
            self.bitmap_header[8:12],
            "little", signed=True
        )
        width = int.from_bytes(self.bitmap_header[4:8], "little", signed=True)
        # save the height and width of the image only as positive integers
        self.height = abs(height)
        self.width = abs(width)

    def _hue_to_rgb(self, p: float, q: float, t: float):
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1/6:
            return p + (q - p) * 6 * t
        if t < 1/2:
            return q
        if t < 2/3:
            return p + (q - p) * (2/3 - t) * 6
        return p

    def _hsl_to_rgb(self, hb: int, sb: int, lb: int):
        h = hb / 360
        s = sb / 100
        lgt = lb / 100
        r = 0
        g = 0
        b = 0
        if s == 0:
            r = g = b = lgt
        else:
            q = 0
            if lgt < 0.5:
                q = lgt * (1 + s)
            else:
                q = lgt + s - lgt * s

            p = 2 * lgt - q

            r = self._hue_to_rgb(p, q, h + 1/3)
            g = self._hue_to_rgb(p, q, h)
            b = self._hue_to_rgb(p, q, h - 1/3)

        r = round(r * 255)
        g = round(g * 255)
        b = round(b * 255)

        return int(r), int(g), int(b)

    def _rgb_to_hsl(self, rb: int, gb: int, bb: int):
        r = rb / 255
        g = gb / 255
        b = bb / 255

        h = 0
        s = 0
        lgt = 0

        cmax = max(r, g, b)
        cmin = min(r, g, b)

        delta = cmax - cmin

        if delta == 0:
            h = 0
        elif cmax == r:
            h = ((g - b) / delta) % 6
        elif cmax == g:
            h = ((b - r) / delta) + 2
        elif cmax == b:
            h = ((r - g) / delta) + 4

        h = round(h * 60)

        if h < 0:
            h += 360

        lgt = (cmax + cmin) / 2

        if delta == 0:
            s = 0
        else:
            s = delta / (1 - abs(2 * lgt - 1))

        s = round(s * 100)
        lgt = round(lgt * 100)

        return h, s, lgt

    def change_hsl(self, hue: int, saturation: int, lightness: int):
        self.set_loading_cursor()
        self.hue = hue
        self.saturation = saturation
        self.lightness = lightness

        print(hue, saturation, lightness)
        pixel_array = deepcopy(self.original_pixel_array)

        for i in range(len(pixel_array)):
            r = pixel_array[i][2]
            g = pixel_array[i][1]
            b = pixel_array[i][0]
            h, s, lgt = self._rgb_to_hsl(r, g, b)
            h = (h + hue) % 360
            s = s * (1 + saturation / 100)
            s = min(100, s)

            lgt = lgt * (1 + lightness / 100)
            if lgt > 100:
                lgt = 100
            if lgt < 0:
                lgt = 0
            r, g, b = self._hsl_to_rgb(h, s, lgt)
            pixel_array[i][2] = r
            pixel_array[i][1] = g
            pixel_array[i][0] = b
        self.emit_signal(pixel_array)

    def invert(self):
        self.set_loading_cursor()
        working_array = self.original_pixel_array.copy()
        for i in range(len(working_array)):
            working_array[i][0] = 255 - working_array[i][0]
            working_array[i][1] = 255 - working_array[i][1]
            working_array[i][2] = 255 - working_array[i][2]
        self.original_pixel_array = deepcopy(working_array)
        self.change_hsl(self.hue, self.saturation, self.lightness)

    def rotate_clockwise(self):
        self.set_loading_cursor()
        working_array = self.original_pixel_array.copy()
        new_array = []
        for i in range(self.width):
            for j in range(self.height):
                new_array.append(working_array[(self.width - i - 1) * self.height + j])
        self.original_pixel_array = deepcopy(new_array)
        self.width, self.height = self.height, self.width
        self.change_hsl(self.hue, self.saturation, self.lightness)

    def rotate_counter_clockwise(self):
        self.set_loading_cursor()
        working_array = self.original_pixel_array.copy()
        new_array: list[list[int]] = []
        for i in range(self.width):
            for j in range(self.height):
                new_array.append(
                    working_array[i * self.height + self.height - j - 1]
                )
        self.original_pixel_array = deepcopy(new_array)
        self.width, self.height = self.height, self.width
        self.change_hsl(self.hue, self.saturation, self.lightness)

    def flip_horizontal(self):
        self.set_loading_cursor()
        working_array = self.original_pixel_array
        new_array: list[list[int]] = []
        for i in range(self.width):
            for j in range(self.height):
                new_array.append(
                    working_array[i * self.height + self.height - j - 1]
                )
        self.original_pixel_array = deepcopy(new_array)
        self.change_hsl(self.hue, self.saturation, self.lightness)

    def flip_vertical(self):
        self.set_loading_cursor()
        working_array = self.original_pixel_array
        new_array: list[list[int]] = []
        for i in range(self.width):
            for j in range(self.height):
                new_array.append(
                    working_array[(self.width - i - 1) * self.height + j]
                )
        self.original_pixel_array = deepcopy(new_array)
        self.change_hsl(self.hue, self.saturation, self.lightness)

    # create emit sinal that pixal array has changed
    def emit_signal(self, pixel_array: list[list[int]]):
        self.pixal_array_changed.emit(pixel_array)

class CustomPixelWindow(QWidget): # noqa
    def __init__(self, pixal_array: list[list[int]], width: int = 500, height: int = 500, app: QApplication | None = None):
        super().__init__()
        self.pixal_array = pixal_array
        self.setFixedSize(width, height)
        self.app = app
        
    def set_loading_cursor(self):
        """set the cursor to the loading cursor"""
        if self.app:
            self.app.setOverrideCursor(Qt.CursorShape.WaitCursor)

    def set_default_cursor(self):
        """set the cursor to the default cursor"""
        if self.app:
            print("restoring cursor")
            self.app.setOverrideCursor(Qt.CursorShape.ArrowCursor)

    @pyqtSlot(list)
    def update_image(self, pixal_array: list[list[int]]):
        # change mouse cursor to wait cursor
        self.set_loading_cursor()
        self.pixal_array = pixal_array
        self.update()
        # change mouse cursor back to arrow cursor
        self.set_default_cursor()

    def paintEvent(self, a0: QPaintEvent | None):
        """paint the image onto the widget"""
        painter = QPainter()
        painter.begin(self)
        width = self.width()
        for i in range(len(self.pixal_array)):
            y = i // width
            x = i % width
            r = self.pixal_array[i][2]
            g = self.pixal_array[i][1]
            b = self.pixal_array[i][0]
            color = QColor(r, g, b)
            painter.setPen(QPen(QBrush(color), 1))
            painter.drawPoint(x, y)
        painter.end()
        super().paintEvent(a0)


def main():

    app = QApplication([])

    # current directory image.bmp
    image = BitmapImage(BITMAP_IMAGE, app)
    image_widget = CustomPixelWindow(image.pixel_array, image.width, image.height, app)
    window = QWidget()
    window.setWindowTitle("My Bitmap Image Viewer: Code With Dasun")

    layout = QHBoxLayout()
    scroll_area = QScrollArea()
    scroll_area.setWidget(image_widget)
    scroll_area.setMinimumHeight(550)
    scroll_area.setMinimumWidth(550)
    # set widget centered
    scroll_area.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(scroll_area)

    hsl_layout = QHBoxLayout()

    hue_layout = QVBoxLayout()
    hue_layout.addWidget(QLabel("Hue", alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter))
    hue_dial = QDial(minimum=0, maximum=360)
    hue_value = QLabel("0", alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    hue_layout.addWidget(hue_dial)
    hue_layout.addWidget(hue_value)
    hsl_layout.addLayout(hue_layout)
    hue_dial.valueChanged.connect(lambda value: hue_value.setText(str(value)))

    saturation_layout = QVBoxLayout()
    saturation_layout.addWidget(QLabel("Saturation"), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    saturation_dial = QDial(value=0, minimum=-100, maximum=100)
    saturation_label = QLabel("50", alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    saturation_layout.addWidget(saturation_dial)
    saturation_layout.addWidget(saturation_label)
    hsl_layout.addLayout(saturation_layout)
    saturation_dial.valueChanged.connect(lambda value: saturation_label.setText(str(value)))

    lightness_layout = QVBoxLayout()
    lightness_layout.addWidget(QLabel("Lightness", alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter))
    lightness_dial = QDial(value=0, minimum=-100, maximum=100)
    lightness_label = QLabel("0", alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    lightness_layout.addWidget(lightness_dial)
    lightness_layout.addWidget(lightness_label)
    hsl_layout.addLayout(lightness_layout)
    lightness_dial.valueChanged.connect(lambda value: lightness_label.setText(str(value)))

    operations_layout = QVBoxLayout()
    layout.addLayout(operations_layout)
    operations_layout.addLayout(hsl_layout)
    action_buttons = QHBoxLayout()
    invert_button = QPushButton("Invert")
    action_buttons.addWidget(invert_button)
    rotate_counter_clockwise = QPushButton("Rotate ⟲")
    action_buttons.addWidget(rotate_counter_clockwise)
    rotate_button = QPushButton("Rotate ⟳")
    action_buttons.addWidget(rotate_button)
    flip_h = QPushButton("Flip ⇆")
    action_buttons.addWidget(flip_h)
    flip_v = QPushButton("Flip ⇅")
    action_buttons.addWidget(flip_v)
    operations_layout.addLayout(action_buttons)

    # add stretch to the bottom of the layout
    operations_layout.addStretch()

    # connect signal to slot
    image.pixal_array_changed.connect(image_widget.update_image)

    invert_button.clicked.connect(image.invert)
    rotate_button.clicked.connect(image.rotate_clockwise)
    rotate_counter_clockwise.clicked.connect(image.rotate_counter_clockwise)
    flip_h.clicked.connect(image.flip_horizontal)
    flip_v.clicked.connect(image.flip_vertical)

    hue_dial.sliderReleased.connect(lambda:  image.change_hsl(hue_dial.value(), saturation_dial.value(), lightness_dial.value()))
    saturation_dial.sliderReleased.connect(lambda:  image.change_hsl(hue_dial.value(), saturation_dial.value(), lightness_dial.value()))
    lightness_dial.sliderReleased.connect(lambda:  image.change_hsl(hue_dial.value(), saturation_dial.value(), lightness_dial.value()))

    window.setLayout(layout)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
