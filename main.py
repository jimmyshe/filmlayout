import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QLabel, 
                             QFileDialog, QScrollArea, QSpinBox, QComboBox, QGroupBox, QMessageBox)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, Signal, QPoint
from PIL import Image

import processor

class ClickableLabel(QLabel):
    clicked = Signal(QPoint)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # In PySide6, position() returns QPointF
            self.clicked.emit(event.position().toPoint())
        super().mousePressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("35mm 胶片排版工具")
        self.resize(1100, 900)

        self.images_data = [] # List of dict: {"path": str, "crop": str, "color": str, "type": str}
        self.preview_pages = []
        self.layout_info = []

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
        self.list_widget.currentRowChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.list_widget)

        # Per-image settings group
        self.group_settings = QGroupBox("选中照片设置")
        settings_layout = QVBoxLayout(self.group_settings)
        self.group_settings.setEnabled(False)

        settings_layout.addWidget(QLabel("裁切方式:"))
        self.combo_crop = QComboBox()
        self.combo_crop.addItems(["短边对齐 (填充)", "长边对齐 (适应)"])
        self.combo_crop.currentIndexChanged.connect(self.update_image_settings)
        settings_layout.addWidget(self.combo_crop)

        settings_layout.addWidget(QLabel("色彩模式:"))
        self.combo_color = QComboBox()
        self.combo_color.addItems(["彩色", "黑白"])
        self.combo_color.currentIndexChanged.connect(self.update_image_settings)
        settings_layout.addWidget(self.combo_color)

        settings_layout.addWidget(QLabel("胶片类型:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["正片", "负片 (反相)"])
        self.combo_type.currentIndexChanged.connect(self.update_image_settings)
        settings_layout.addWidget(self.combo_type)

        left_layout.addWidget(self.group_settings)

        # Layout settings
        layout_group = QGroupBox("全局排版设置")
        layout_vbox = QVBoxLayout(layout_group)

        layout_vbox.addWidget(QLabel("页边距 (mm):"))
        self.spin_margin = QSpinBox()
        self.spin_margin.setRange(0, 50)
        self.spin_margin.setValue(10)
        self.spin_margin.valueChanged.connect(self.update_preview)
        layout_vbox.addWidget(self.spin_margin)

        layout_vbox.addWidget(QLabel("胶片间隙 (mm):"))
        self.spin_gap = QSpinBox()
        self.spin_gap.setRange(0, 20)
        self.spin_gap.setValue(2)
        self.spin_gap.valueChanged.connect(self.update_preview)
        layout_vbox.addWidget(self.spin_gap)
        
        left_layout.addWidget(layout_group)

        self.btn_export = QPushButton("导出为 PDF")
        self.btn_export.clicked.connect(self.export_pdf)
        left_layout.addWidget(self.btn_export)

        main_layout.addWidget(left_panel)

        # Right side: Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("预览 (第一页 - 点击照片可选择):"))
        self.scroll_area = QScrollArea()
        self.preview_label = ClickableLabel("添加照片后显示预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.clicked.connect(self.on_preview_clicked)
        self.scroll_area.setWidget(self.preview_label)
        self.scroll_area.setWidgetResizable(True)
        right_layout.addWidget(self.scroll_area)

        main_layout.addWidget(right_panel)

        self._updating_ui = False

    def add_photos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择照片", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if files:
            for f in files:
                self.images_data.append({
                    "path": f,
                    "crop": "short",
                    "color": "color",
                    "type": "positive"
                })
                self.list_widget.addItem(os.path.basename(f))
            self.update_preview()

    def clear_photos(self):
        self.images_data = []
        self.list_widget.clear()
        self.preview_label.setText("添加照片后显示预览")
        self.preview_label.setPixmap(QPixmap())
        self.group_settings.setEnabled(False)
        self.preview_pages = []
        self.layout_info = []

    def on_selection_changed(self, row):
        if row < 0 or row >= len(self.images_data):
            self.group_settings.setEnabled(False)
            return
        
        self.group_settings.setEnabled(True)
        data = self.images_data[row]
        
        self._updating_ui = True
        self.combo_crop.setCurrentIndex(0 if data["crop"] == "short" else 1)
        self.combo_color.setCurrentIndex(0 if data["color"] == "color" else 1)
        self.combo_type.setCurrentIndex(0 if data["type"] == "positive" else 1)
        self._updating_ui = False

    def update_image_settings(self):
        if self._updating_ui:
            return
        
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.images_data):
            return
        
        self.images_data[row]["crop"] = "short" if self.combo_crop.currentIndex() == 0 else "long"
        self.images_data[row]["color"] = "color" if self.combo_color.currentIndex() == 0 else "bw"
        self.images_data[row]["type"] = "positive" if self.combo_type.currentIndex() == 0 else "negative"
        
        self.update_preview()

    def update_preview(self):
        if not self.images_data:
            return

        # Create film frames
        frames = []
        for data in self.images_data:
            # We don't draw holes here because layout_on_a4 will draw them continuously
            frame = processor.create_film_frame(
                data["path"], 
                crop_mode=data["crop"],
                color_mode=data["color"],
                film_type=data["type"],
                draw_holes=False
            )
            frames.append(frame)

        # Layout on A4
        margin = self.spin_margin.value()
        gap = self.spin_gap.value()
        self.preview_pages, self.layout_info = processor.layout_on_a4(frames, margin_mm=margin, gap_mm=gap)

        if self.preview_pages:
            # Show first page
            pil_img = self.preview_pages[0]
            qimg = self.pil_to_qimage(pil_img)
            pixmap = QPixmap.fromImage(qimg)
            
            # Scale to container
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
                self.preview_label.setPixmap(pixmap.scaled(800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def on_preview_clicked(self, pos):
        if not self.layout_info or not self.preview_pages:
            return
        
        # We only show first page in preview
        page_info = self.layout_info[0]
        pixmap = self.preview_label.pixmap()
        if not pixmap or pixmap.isNull():
            return
            
        lbl_w = self.preview_label.width()
        lbl_h = self.preview_label.height()
        pix_w = pixmap.width()
        pix_h = pixmap.height()
        
        # Calculate offset due to alignment
        offset_x = (lbl_w - pix_w) / 2
        offset_y = (lbl_h - pix_h) / 2
        
        rel_x = pos.x() - offset_x
        rel_y = pos.y() - offset_y
        
        if rel_x < 0 or rel_x >= pix_w or rel_y < 0 or rel_y >= pix_h:
            return
            
        # Map to original image coordinates
        orig_w = self.preview_pages[0].width
        orig_h = self.preview_pages[0].height
        
        scale_x = orig_w / pix_w
        scale_y = orig_h / pix_h
        
        orig_x = rel_x * scale_x
        orig_y = rel_y * scale_y
        
        # Check which frame was clicked
        for item in page_info:
            x1, y1, x2, y2 = item["rect"]
            if x1 <= orig_x <= x2 and y1 <= orig_y <= y2:
                self.list_widget.setCurrentRow(item["index"])
                break

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
                pages_to_save = [p.convert("RGB") for p in self.preview_pages]
                pages_to_save[0].save(
                    save_path, 
                    save_all=True, 
                    append_images=pages_to_save[1:],
                    resolution=processor.DPI
                )
                QMessageBox.information(self, "成功", f"已成功导出到: {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
