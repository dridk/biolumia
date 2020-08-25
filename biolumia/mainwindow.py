from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import os
import seaborn as sns


def section(self, x, y, width, height):
    self.data = self.hdu.data
    return self.data[x:width, y:height]


def distribution(array):
    pass


def seuillage(array):

    x = []
    y = []
    for i in range(0, np.max(array)):
        x.append(i)
        y.append(np.sum(array > i))

    return (x, y)


class FitsImage:
    def __init__(self, filename=None):

        self.brightness = 1

        if filename:
            self.load(filename)

    def load(self, filename):
        self.hdu_list = fits.open(filename)
        self.hdu_list.info()
        self.hdu = self.hdu_list[0]
        self.width, self.height = self.hdu.data.shape

    def to_image(self):
        self.data = self.hdu.data
        x1 = np.min(self.data)
        x2 = np.max(self.data)
        dx = x2 - x1
        dy = 255.0

        factor = (dy / dx) + self.brightness
        self.data = self.data * factor

        self.data[self.data > 255] = 255.0
        self.data[self.data < 0] = 0.0

        # if self.R:
        #     self.data[
        #         self.R.top() : self.R.bottom(), self.R.left() : self.R.right()
        #     ] = 255

        self.data = self.data.astype("uint8")
        img = QImage(self.data, self.width, self.height, QImage.Format_Indexed8)
        return img

    def to_pixmap(self):
        return QPixmap.fromImage(self.to_image())


class FitsImageItem(QGraphicsPixmapItem):
    def __init__(self):
        super().__init__()
        filename = "C:/sacha/Dev/biolumia/data/s998dd.fts"
        self.img = FitsImage(filename)
        self.refresh()

    def refresh(self):
        self.setPixmap(self.img.to_pixmap())


"""END CLASS"""


class BoxItem(QGraphicsObject):

    rectChanged = Signal(QRect)

    def __init__(self):
        super().__init__()
        self.mousePressPos = None
        self.mousePressRect = None
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        # self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        # self.setFlag(QGraphicsItem.ItemIsFocusable, True)

        self.rect = QRect(0, 0, 100, 100)

        self.moving = False
        self.origin = QPoint()

        # # Resizer actions
        # self.resizer.setPos(self.boundingRect().bottomRight() - self.r_offset)
        # self.resizer.resizeSignal.connect(self.resize)

    def corner_rect(self) -> QRect:
        """ Return corner rect geometry """
        return QRect(self.rect.right() - 10, self.rect.bottom() - 10, 10, 10)

    def boundingRect(self) -> QRectF:
        """ Override boundingRect """
        return self.rect.adjusted(-10, -10, 10, 10)

    def paint(self, painter, option, widget=None):
        """ OVerride paint  """

        brush = QBrush(QColor(255, 100, 100, 200))
        brush.setStyle(Qt.Dense7Pattern)
        painter.setBrush(brush)
        painter.drawRect(self.rect)

        if self.isSelected():
            painter.setBrush(QBrush(QColor(Qt.red)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.corner_rect())

            # Draw selection
            pen = QPen(QColor(Qt.green))
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect)

        self.update()

    def hoverMoveEvent(self, event: QMouseEvent):
        """ Override hover move Event : Display cursor """

        pos = event.pos()

        if self.isSelected() & self.corner_rect().contains(event.pos().toPoint()):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """ override mouse Press Event """
        if self.isSelected() & self.corner_rect().contains(
            QPoint(event.pos().toPoint())
        ):
            self.moving = True
            self.origin = self.rect.topLeft()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """ Override mouse release event """
        self.moving = False
        self.rectChanged.emit(self.rect)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """ Override mouse move event """
        if self.moving:
            # If moving is set from mousePressEvent , change geometry
            self.prepareGeometryChange()

            pos = event.pos().toPoint()

            if pos.x() >= self.origin.x():
                self.rect.setRight(pos.x())
            else:
                self.rect.setLeft(pos.x())

            if pos.y() >= self.origin.y():
                self.rect.setBottom(pos.y())
            else:
                self.rect.setTop(pos.y())
            self.rect = self.rect.normalized()
            self.update()
            return
        else:
            super().mouseMoveEvent(event)


class ImageViewer(QGraphicsView):

    rectChanged = Signal(QRect)

    def __init__(self):
        super().__init__()

        self.setScene(QGraphicsScene())
        self.imgitem = FitsImageItem()
        self.scene().addItem(self.imgitem)

        self.boxitem = BoxItem()
        self.scene().addItem(self.boxitem)

        self.boxitem.rectChanged.connect(self.rectChanged)

    def setBrightness(self, value):
        self.imgitem.img.brightness = value
        self.imgitem.refresh()


class AbstractPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vlayout = QVBoxLayout()
        self.fig = Figure(
            figsize=(7, 5), dpi=65, facecolor=(1, 1, 1), edgecolor=(0, 0, 0)
        )
        self.canvas = FigureCanvas(self.fig)

        self.vlayout.addWidget(self.canvas)
        self.setLayout(self.vlayout)

    def refresh(self):
        self.fig.clf()
        self.plot(self.fig)
        self.canvas.draw()

    def plot(self, figure):
        pass
        # ax = figure.add_subplot(111)
        # x = np.linspace(0, 1, 100)
        # y = x ** 2
        # sns.scatterplot(x, y, ax=ax)

        # self.canvas.draw()


class HistogramWidget(AbstractPlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.data = None

    def plot(self, figure):
        ax = figure.add_subplot(111)
        sns.scatterplot(x=self.data[0], y=self.data[1], ax=ax)

        ax.plot(self.data[0], self.data[1], linestyle="-", marker="o")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        toolbar = self.addToolBar("main")

        toolbar.addAction("Open")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 20)
        toolbar.addWidget(self.slider)

        self.splitter = QSplitter(Qt.Vertical)

        self.image_view = ImageViewer()
        self.histo_view = HistogramWidget()

        self.addWidget(self.histo_view)

        self.slider.valueChanged.connect(self.image_view.setBrightness)

        # fig.canvas.draw()
        # a = np.array(fig.canvas.renderer.buffer_rgba())

        # img = QImage(
        #     fig.canvas.renderer.buffer_rgba(),
        #     a.shape[0],
        #     a.shape[1],
        #     QImage.Format_ARGB32,
        # )

        # self.label = QLabel()
        # self.label.setPixmap(QPixmap.fromImage(img))

        self.setCentralWidget(self.image_view)
        self.resize(1280, 800)

        self.image_view.rectChanged.connect(self.on_rect_changed)

    def addWidget(self, widget, area=Qt.BottomDockWidgetArea):

        dock = QDockWidget()
        dock.setWidget(widget)

        self.addDockWidget(area, dock)

    def on_rect_changed(self, rect):

        rect.moveTo(self.image_view.boxitem.pos().toPoint())

        data = self.image_view.imgitem.img.hdu.data

        subdata = data[
            rect.top() : rect.bottom(), rect.left() : rect.right(),
        ]

        print(np.mean(subdata))
        # print(rect)

        self.histo_view.data = seuillage(subdata.flatten())

        self.histo_view.refresh()
