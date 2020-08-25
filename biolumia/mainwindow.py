from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import numpy as np
from astropy.io import fits
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import os
import seaborn as sns
import sys

from biolumia.project import Project


class FilesWidget(QTreeWidget):

    fileChanged = Signal(str)

    def __init__(self, parent = None):
        super().__init__(parent)
        self.itemSelectionChanged.connect(self.on_item_changed)


    def load(self, groups):
        
        self.clear()
        self.file_items = []
        for group in groups:
            item = QTreeWidgetItem()
            item.setText(0, group.get("name",""))

            for file in group.get("files",[]):
                fitem = QTreeWidgetItem()
                fitem.setText(0, file)
                fitem.setData(0, Qt.UserRole, file)
                fitem.setCheckState(0,Qt.Unchecked)
                self.file_items.append(fitem)
                item.addChild(fitem)

            self.addTopLevelItem(item)

    def selected_files(self):
        for item in self.file_items:
            if item.checkState(0) == Qt.Checked:
                yield item.data(0, Qt.UserRole)

    @Slot()
    def on_item_changed(self):
        """ override """ 

        items = self.selectedItems()
        if items:
            filename = items[0].data(0, Qt.UserRole)
            if os.path.exists(filename):
                print(filename)
                self.fileChanged.emit(filename)
    

def compute_curves(filename , areas: list, max = 255):

    x = np.arange(0, max)

    hdu_list = fits.open(filename)
    hdu = hdu_list[0]
    subdata = []

    for rect in areas:
        subdata.append(hdu.data[rect.top():rect.bottom(), rect.left():rect.right()].flatten())
    subdata = np.concatenate(subdata)

    y = []
    for i in x:
        y.append(np.sum(subdata > i))

    return y 



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




"""END CLASS"""


class BoxItem(QGraphicsObject):

    rectChanged = Signal(QRect)

    def __init__(self, rect : QRect()):
        super().__init__()
        self.mousePressPos = None
        self.mousePressRect = None
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        # self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        # self.setFlag(QGraphicsItem.ItemIsFocusable, True)

        self.rect = rect

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
        print(self.pos())
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

        self.img = FitsImage()

        self.box_items = []
        self.setScene(QGraphicsScene())

        self.imgitem = QGraphicsPixmapItem()
        self.scene().addItem(self.imgitem)

        #self.add_area(QRect(0, 0, 10, 100))

        #self.boxitem.rectChanged.connect(self.rectChanged)

    def add_area(self, rect: QRect):
        item = BoxItem(rect)
        self.scene().addItem(item)
        self.box_items.append(item)

    def rem_selected_areas(self):

        for item in self.box_items:
            if item.isSelected():
                self.scene().removeItem(item)
                del item

        self.box_items = [ i for i in self.box_items if not i.isSelected()]


    def keyPressEvent(self, event : QKeyEvent):

        if event.key() == Qt.Key_Delete:
            self.rem_selected_areas()

    def set_image(self, filename):
        print("set ", filename)
        self.img.load(filename)
        self.imgitem.setPixmap(self.img.to_pixmap())


    def get_areas(self):
        for item in self.box_items:
            rect = QRect(item.rect)
            rect.moveTo(item.pos().toPoint())
            yield rect





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
        ax.grid(True)
        print(self.data)
        sns.lineplot(x="index", y="value", data=self.data, ax=ax)

        #ax.plot(self.data[0], self.data[1], linestyle="-", marker="o")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        toolbar = self.addToolBar("main")

        toolbar.addAction("Open project", self.on_open_project)
        toolbar.addAction("Save project")

        toolbar.addAction("add area", self.on_add_area)
        toolbar.addAction("rem area", self.on_rem_area)
        toolbar.addAction("Compute", self.on_compute)



        self.prj = Project()
        self.image_view = ImageViewer()
        self.histo_view = HistogramWidget()
        self.files_view = FilesWidget()


        self.addWidget(self.files_view, Qt.LeftDockWidgetArea)
        self.addWidget(self.histo_view)


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

        self.files_view.fileChanged.connect(self.image_view.set_image)


    def addWidget(self, widget, area=Qt.BottomDockWidgetArea):

        dock = QDockWidget()
        dock.setWidget(widget)

        self.addDockWidget(area, dock)


    def on_open_project(self):

        filename, _ = QFileDialog.getOpenFileName(self,"","")
        if filename:
            self.load(filename)

    def load(self, filename):
        self.prj.load(filename)
        self.files_view.load(self.prj.get_groups())


    def on_compute(self):
        files = list(self.files_view.selected_files())
        areas = list(self.image_view.get_areas())

        y = []
        x = []
        max_index = 100
        for file in files:
            x += list(range(0, max_index))
            y += compute_curves(file, areas, max_index)
        
        self.df = pd.DataFrame({"index":x, "value":y})
        self.histo_view.data = self.df
        self.histo_view.refresh()



    def on_add_area(self):
        self.image_view.add_area(QRect(0,0,100,100)) 

    def on_rem_area(self):
        self.image_view.rem_selected_areas()

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


if __name__ == '__main__':
    

    from glob import glob 

    # files = [file for file in glob("../data/*.fts")]
    # areas = [ QRect(253,350, 10, 10)]
    # compute_curves(files, areas )
        

    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    w.load("../project_example.json")

    # prj = Project("../project_example.json")

    # p = FilesWidget()
    # p.set_groups(prj.get_groups())
    # p.show()
    app.exec_()