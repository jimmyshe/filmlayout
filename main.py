import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QLabel, 
                             QFileDialog, QScrollArea, QSpinBox)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from PIL import Image

import processor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("35mm 胶片排版工具")
        self.resize(1000, 800)

        self.image_paths = []
        self.preview_pages = []

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left side: Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(300)

        self.btn_add = QPushButton("添加照片")
        self.btn_add.clicked.connect(self.add_photos)
        left_layout.addWidget(self.btn_add)

        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self.clear_photos)
        left_layout.addWidget(self.btn_clear)

        left_layout.addWidget(QLabel("已添加照片:"))
        self.list_widget = QListWidget()
        left_layout.addWidget(self.list_widget)

        left_layout.addWidget(QLabel("页边距 (mm):"))
        self.spin_margin = QSpinBox()
        self.spin_margin.setRange(0, 50)
        self.spin_margin.setValue(10)
        self.spin_margin.valueChanged.connect(self.update_preview)
        left_layout.addWidget(self.spin_margin)

        left_layout.addWidget(QLabel("胶片间隙 (mm):"))
        self.spin_gap = QSpinBox()
        self.spin_gap.setRange(0, 20)
        self.spin_gap.setValue(2)
        self.spin_gap.valueChanged.connect(self.update_preview)
        left_layout.addWidget(self.spin_gap)

        self.btn_export = QPushButton("导出为 PDF")
        self.btn_export.clicked.connect(self.export_pdf)
        left_layout.addWidget(self.btn_export)

        main_layout.addWidget(left_panel)

        # Right side: Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("预览 (第一页):"))
        self.scroll_area = QScrollArea()
        self.preview_label = QLabel("添加照片后显示预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.preview_label)
        self.scroll_area.setWidgetResizable(True)
        right_layout.addWidget(self.scroll_area)

        main_layout.addWidget(right_panel)

    def add_photos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择照片", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if files:
            self.image_paths.extend(files)
            for f in files:
                self.list_widget.addItem(os.path.basename(f))
            self.update_preview()

    def clear_photos(self):
        self.image_paths = []
        self.list_widget.clear()
        self.preview_label.setText("添加照片后显示预览")
        self.preview_label.setPixmap(QPixmap())

    def update_preview(self):
        if not self.image_paths:
            return

        # Create film frames
        frames = []
        for path in self.image_paths:
            frame = processor.create_film_frame(path)
            frames.append(frame)

        # Layout on A4
        margin = self.spin_margin.value()
        gap = self.spin_gap.value()
        self.preview_pages = processor.layout_on_a4(frames, margin_mm=margin, gap_mm=gap)

        if self.preview_pages:
            # Show first page
            pil_img = self.preview_pages[0]
            qimg = self.pil_to_qimage(pil_img)
            pixmap = QPixmap.fromImage(qimg)
            
            # Use fixed width for preview to avoid infinite layout loops, or just scale to container
            view_w = self.scroll_area.viewport().width() - 10
            view_h = self.scroll_area.viewport().height() - 10
            
            if view_w > 0 and view_h > 0:
                scaled_pixmap = pixmap.scaled(
                    view_w, 
                    view_h, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                # Fallback if UI not yet fully laid out
                self.preview_label.setPixmap(pixmap.scaled(800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def pil_to_qimage(self, pil_img):
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        
        data = pil_img.tobytes("raw", "RGB")
        qimage = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGB888)
        return qimage

    def export_pdf(self):
        if not self.preview_pages:
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF", "", "PDF Files (*.pdf)"
        )
        if save_path:
            if not save_path.lower().endswith(".pdf"):
                save_path += ".pdf"
            
            try:
                # Save using Pillow
                # Need to convert to RGB for PDF if not already
                pages_to_save = [p.convert("RGB") for p in self.preview_pages]
                pages_to_save[0].save(
                    save_path, 
                    save_all=True, 
                    append_images=pages_to_save[1:],
                    resolution=processor.DPI
                )
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "成功", f"已成功导出到: {save_path}")
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "错误", f"导出失败: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
