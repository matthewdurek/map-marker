import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
                             QFileDialog, QGraphicsView, QGraphicsScene,
                             QInputDialog, QGraphicsItem, QDialog, QHBoxLayout,
                             QGridLayout, QListWidget, QListWidgetItem, QGraphicsTextItem,)
from PyQt6.QtGui import QPixmap, QImage, QBrush, QPainter, QIcon, QFont
from PyQt6.QtCore import Qt, QRectF, QSize

from PIL import Image, ImageDraw

class MarkerEditDialog(QDialog):
    def __init__(self, marker, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.parentApp = parent
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Edit Marker')
        layout = QVBoxLayout()

        shapeLayout = QHBoxLayout()
        shapes = {
            '●': 'circle',
            '■': 'square',
            '✖': 'X',
            '▲': 'triangle',
            '↑': 'up_arrow',
            '→': 'right_arrow',
            '↓': 'down_arrow',
            '←': 'left_arrow',
        }
        for char, shape in shapes.items():
            btn = QPushButton(char)
            btn.clicked.connect(lambda _, s=char: self.changeShape(s))
            shapeLayout.addWidget(btn)
            self.shapeButtons = {shape: btn}
        layout.addLayout(shapeLayout)

        # Color selection
        colorLayout = QGridLayout()
        colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'black', 'white']
        for i, color in enumerate(colors):
            colorBtn = QPushButton()
            colorBtn.setStyleSheet(f"background-color: {color};")
            colorBtn.clicked.connect(lambda _, color=color: self.changeColor(color))
            colorLayout.addWidget(colorBtn, i // 4, i % 4)
        layout.addLayout(colorLayout)

        # Edit comment button
        editCommentBtn = QPushButton('Save Changes')
        editCommentBtn.clicked.connect(self.editComment)
        layout.addWidget(editCommentBtn)

        # Delete marker button
        deleteMarkerBtn = QPushButton('Delete Marker')
        deleteMarkerBtn.clicked.connect(self.deleteMarker)
        layout.addWidget(deleteMarkerBtn)

        self.setLayout(layout)

    def changeShape(self, shape):
        self.marker.shapeType = shape
        self.marker.updateShape(shape)
        self.marker.update()
        self.parentApp.updateMarkerList()
        self.close()

    def changeColor(self, color):
        self.marker.setDefaultTextColor(Qt.GlobalColor.__dict__[color])
        self.marker.update()
        self.marker.setColor(Qt.GlobalColor.__dict__[color])
        self.parentApp.updateMarkerList()
        self.close()

    def editComment(self):
        comment, ok = QInputDialog.getText(self, "Edit Comment", "Enter a new comment for this marker:", text=self.marker.comment)
        if ok and comment:
            self.marker.comment = comment
            self.marker.setToolTip(comment)
            self.parentApp.updateMarkerList()

    def deleteMarker(self):
        self.marker.scene().removeItem(self.marker)
        self.parentApp.markers.remove(self.marker)
        self.parentApp.updateMarkerList()
        self.close()

class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.parent = parent

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scenePos = self.mapToScene(event.pos())
            self.parent.addMarker(scenePos)
        super().mousePressEvent(event)

class CommentMarker(QGraphicsTextItem):
    def __init__(self, window_parent, x, y, comment, shape='●', parent=None):
        super().__init__(shape, parent)
        self.color = Qt.GlobalColor.red
        self.setPos(x, y)
        self.setFont(QFont('Arial', 24))
        self.setDefaultTextColor(Qt.GlobalColor.red)
        self.setToolTip(comment)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.window_parent = window_parent
        self.comment = comment

    def setComment(self, comment):
        self.comment = comment
        self.setToolTip(comment)

    def updateShape(self, shape):
        self.setPlainText(shape)

    def deleteMarker(self):
        self.scene().removeItem(self)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            MarkerEditDialog(self, self.window_parent).exec()

    def setColor(self, color):
        self.color = color

class MapMarkerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Marker Tool")
        self.setGeometry(100, 100, 1200, 600)  # Adjusted width to accommodate marker list

        self.markers = []
        self.initUI()

    def initUI(self):
        mainLayout = QHBoxLayout()

        # Scene and view setup
        self.scene = QGraphicsScene()
        self.graphicsView = CustomGraphicsView(self.scene, self)
        self.scene.setSceneRect(0, 0, 800, 600)
        self.graphicsView.setScene(self.scene)
        mainLayout.addWidget(self.graphicsView)

        # Right panel for marker list
        self.markerListWidget = QListWidget()
        mainLayout.addWidget(self.markerListWidget)

        # Buttons layout
        buttonsLayout = QHBoxLayout()
        self.clearButton = QPushButton("Clear Markers")
        self.clearButton.clicked.connect(self.clearMarkers)
        buttonsLayout.addWidget(self.clearButton)

        self.loadButton = QPushButton("Load Map")
        self.loadButton.clicked.connect(self.loadMap)
        buttonsLayout.addWidget(self.loadButton)

        self.saveMapButton = QPushButton("Save Map")
        self.saveMapButton.clicked.connect(self.saveMap)
        buttonsLayout.addWidget(self.saveMapButton)

        # Main widget setup
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self.layout = QVBoxLayout(self.centralWidget)
        self.layout.addLayout(mainLayout)
        self.layout.addLayout(buttonsLayout)

    def loadMap(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select Map Image", "", "Image Files (*.png *.jpg *.jpeg);;All Files (*)")
        if fileName:
            self.displayMap(fileName)

    def displayMap(self, imagePath):
        image = Image.open(imagePath)
        image = image.convert("RGBA")
        data = image.tobytes("raw", "RGBA")
        qim = QImage(data, image.size[0], image.size[1], QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qim)

        self.scene.clear()
        self.scene.addPixmap(pixmap)
        self.graphicsView.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.markers.clear()
        self.updateMarkerList()

    def addMarker(self, scenePos):
        items = self.scene.items(scenePos)
        if not any(isinstance(item, CommentMarker) for item in items):
            comment, ok = QInputDialog.getText(self, "Comment", "Enter a comment for this marker:")
            if ok and comment:
                marker = CommentMarker(self, scenePos.x(), scenePos.y(), comment)
                self.scene.addItem(marker)
                self.markers.append(marker)
                self.updateMarkerList()

    def clearMarkers(self):
        for item in self.scene.items():
            if isinstance(item, CommentMarker):
                self.scene.removeItem(item)
        self.markers.clear()
        self.updateMarkerList()

    def saveMap(self):
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Map", "", "PNG files (*.png)")
        if filePath:
            rect = self.scene.itemsBoundingRect()
            image = QImage(rect.size().toSize(), QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)

            painter = QPainter(image)
            self.scene.render(painter, QRectF(image.rect()), rect)
            painter.end()

            image.save(filePath)

    def updateMarkerList(self):
        self.markerListWidget.clear()
        for marker in self.markers:
            listItem = QListWidgetItem()
            icon = QPixmap(10, 10)
            icon.fill(marker.color)
            listItem.setIcon(QIcon(icon))
            listItem.setText(marker.comment)
            self.markerListWidget.addItem(listItem)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapMarkerApp()
    window.show()
    sys.exit(app.exec())
