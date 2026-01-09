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
        self.current_page = 0

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

        self.btn_remove = QPushButton("移除选中照片")
        self.btn_remove.clicked.connect(self.remove_photo)
        left_layout.addWidget(self.btn_remove)

        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self.clear_photos)
        left_layout.addWidget(self.btn_clear)

        left_layout.addWidget(QLabel("已添加照片 (可拖动排序):"))
        self.list_widget = QListWidget()
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDropIndicatorShown(True)
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.model().rowsMoved.connect(self.on_rows_moved)
        self.list_widget.currentRowChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.list_widget)

        # Per-image settings group
        self.group_settings = QGroupBox("选中照片设置")
        settings_layout = QVBoxLayout(self.group_settings)
        self.group_settings.setEnabled(False)

        settings_layout.addWidget(QLabel("裁切方式:"))
        crop_layout = QHBoxLayout()
        self.combo_crop = QComboBox()
        self.combo_crop.addItems(["短边对齐 (填充)", "长边对齐 (适应)"])
        self.combo_crop.currentIndexChanged.connect(self.update_image_settings)
        crop_layout.addWidget(self.combo_crop)
        self.btn_apply_crop_all = QPushButton("应用全部")
        self.btn_apply_crop_all.clicked.connect(self.apply_crop_to_all)
        crop_layout.addWidget(self.btn_apply_crop_all)
        settings_layout.addLayout(crop_layout)

        settings_layout.addWidget(QLabel("色彩模式:"))
        color_layout = QHBoxLayout()
        self.combo_color = QComboBox()
        self.combo_color.addItems(["彩色", "黑白"])
        self.combo_color.currentIndexChanged.connect(self.update_image_settings)
        color_layout.addWidget(self.combo_color)
        self.btn_apply_color_all = QPushButton("应用全部")
        self.btn_apply_color_all.clicked.connect(self.apply_color_to_all)
        color_layout.addWidget(self.btn_apply_color_all)
        settings_layout.addLayout(color_layout)

        settings_layout.addWidget(QLabel("胶片类型:"))
        type_layout = QHBoxLayout()
        self.combo_type = QComboBox()
        self.combo_type.addItems(["正片", "负片 (反相)"])
        self.combo_type.currentIndexChanged.connect(self.update_image_settings)
        type_layout.addWidget(self.combo_type)
        self.btn_apply_type_all = QPushButton("应用全部")
        self.btn_apply_type_all.clicked.connect(self.apply_type_to_all)
        type_layout.addWidget(self.btn_apply_type_all)
        settings_layout.addLayout(type_layout)

        settings_layout.addWidget(QLabel("旋转角度:"))
        rotate_layout = QHBoxLayout()
        self.combo_rotate = QComboBox()
        self.combo_rotate.addItems(["0°", "90°", "180°", "270°"])
        self.combo_rotate.currentIndexChanged.connect(self.update_image_settings)
        rotate_layout.addWidget(self.combo_rotate)
        self.btn_apply_rotate_all = QPushButton("应用全部")
        self.btn_apply_rotate_all.clicked.connect(self.apply_rotate_to_all)
        rotate_layout.addWidget(self.btn_apply_rotate_all)
        settings_layout.addLayout(rotate_layout)

        left_layout.addWidget(self.group_settings)

        # Layout settings
        layout_group = QGroupBox("全局排版设置")
        layout_vbox = QVBoxLayout(layout_group)

        layout_vbox.addWidget(QLabel("纸张大小:"))
        self.combo_paper_size = QComboBox()
        self.combo_paper_size.addItems(["A4", "A5", "A6"])
        self.combo_paper_size.currentIndexChanged.connect(self.update_preview)
        layout_vbox.addWidget(self.combo_paper_size)

        layout_vbox.addWidget(QLabel("纸张方向:"))
        self.combo_orientation = QComboBox()
        self.combo_orientation.addItems(["自动 (Auto)", "纵向 (Portrait)", "横向 (Landscape)"])
        self.combo_orientation.currentIndexChanged.connect(self.update_preview)
        layout_vbox.addWidget(self.combo_orientation)

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

        layout_vbox.addWidget(QLabel("导出分辨率 (DPI):"))
        self.combo_export_dpi = QComboBox()
        self.combo_export_dpi.addItems(["300", "600", "1200", "2400", "3600"])
        self.combo_export_dpi.setCurrentIndex(2) # Default 1200
        layout_vbox.addWidget(self.combo_export_dpi)
        
        left_layout.addWidget(layout_group)

        self.btn_export = QPushButton("导出为 PDF")
        self.btn_export.clicked.connect(self.export_pdf)
        left_layout.addWidget(self.btn_export)

        main_layout.addWidget(left_panel)

        # Right side: Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("预览 (点击照片可选择):"))
        header_layout.addStretch()
        
        self.btn_prev = QPushButton("<")
        self.btn_prev.setFixedWidth(30)
        self.btn_prev.clicked.connect(self.prev_page)
        header_layout.addWidget(self.btn_prev)
        
        self.lbl_page = QLabel("第 0 / 0 页")
        header_layout.addWidget(self.lbl_page)
        
        self.btn_next = QPushButton(">")
        self.btn_next.setFixedWidth(30)
        self.btn_next.clicked.connect(self.next_page)
        header_layout.addWidget(self.btn_next)
        
        right_layout.addLayout(header_layout)

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
                    "type": "positive",
                    "rotation": 0
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
        self.current_page = 0
        self.lbl_page.setText("第 0 / 0 页")

    def remove_photo(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        
        self.images_data.pop(row)
        self.list_widget.takeItem(row)
        
        if not self.images_data:
            self.clear_photos()
        else:
            self.update_preview()

    def on_rows_moved(self, parent, start, end, destination, row):
        # destination is the parent of the move (None for top level)
        # row is the index where items were moved to.
        # But wait, QListWidget internal move is easier to sync by just rebuilding from the list widget
        # because the internal logic of destination/row can be tricky.
        
        # Let's rebuild images_data based on list_widget items' original positions?
        # No, better way: each item should have its original data or we just sync carefully.
        # Since we just have paths and settings, we can reorder self.images_data.
        
        # Actually, when items move, we need to know where they came from and where they went.
        # A simpler way for QListWidget is to store the data in the Item itself.
        
        # Alternatively, use the moved signals:
        if start == row: # No real move
            return
            
        # destination_row is where it ended up
        dest_row = row
        if dest_row > start:
            dest_row -= 1 # Adjust for the fact that removing the item shifts indices
            
        item_data = self.images_data.pop(start)
        self.images_data.insert(dest_row, item_data)
        
        self.update_preview()

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
        self.combo_rotate.setCurrentIndex(data["rotation"] // 90)
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
        self.images_data[row]["rotation"] = self.combo_rotate.currentIndex() * 90
        
        self.update_preview()

    def apply_color_to_all(self):
        color = "color" if self.combo_color.currentIndex() == 0 else "bw"
        for data in self.images_data:
            data["color"] = color
        self.update_preview()

    def apply_type_to_all(self):
        film_type = "positive" if self.combo_type.currentIndex() == 0 else "negative"
        for data in self.images_data:
            data["type"] = film_type
        self.update_preview()

    def apply_crop_to_all(self):
        crop = "short" if self.combo_crop.currentIndex() == 0 else "long"
        for data in self.images_data:
            data["crop"] = crop
        self.update_preview()

    def apply_rotate_to_all(self):
        rotation = self.combo_rotate.currentIndex() * 90
        for data in self.images_data:
            data["rotation"] = rotation
        self.update_preview()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_preview()

    def next_page(self):
        if self.current_page < len(self.preview_pages) - 1:
            self.current_page += 1
            self.update_preview()

    def update_preview(self):
        if not self.images_data:
            return

        # Create film frames
        frames = []
        for data in self.images_data:
            # We don't draw holes here because layout_on_paper will draw them continuously
            frame = processor.create_film_frame(
                data["path"], 
                crop_mode=data["crop"],
                color_mode=data["color"],
                film_type=data["type"],
                rotation=data["rotation"],
                draw_holes=False
            )
            frames.append(frame)

        # Layout on paper
        paper_size = self.combo_paper_size.currentText()
        orientation_idx = self.combo_orientation.currentIndex()
        orientation = ["Auto", "Portrait", "Landscape"][orientation_idx]
        margin = self.spin_margin.value()
        gap = self.spin_gap.value()
        self.preview_pages, self.layout_info = processor.layout_on_paper(
            frames, 
            paper_size=paper_size, 
            orientation=orientation,
            margin_mm=margin, 
            gap_mm=gap
        )

        if not self.preview_pages:
            self.lbl_page.setText("第 0 / 0 页")
            return

        # Ensure current_page is valid
        if self.current_page >= len(self.preview_pages):
            self.current_page = len(self.preview_pages) - 1
        if self.current_page < 0:
            self.current_page = 0
            
        self.lbl_page.setText(f"第 {self.current_page + 1} / {len(self.preview_pages)} 页")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < len(self.preview_pages) - 1)

        # Show current page
        pil_img = self.preview_pages[self.current_page]
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

        # Update list widget items to show which ones are NOT on the current page
        current_page_indices = {info["index"] for info in self.layout_info[self.current_page]}
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if i in current_page_indices:
                item.setForeground(Qt.black)
                # Maybe add a small indicator?
                text = os.path.basename(self.images_data[i]["path"])
                item.setText(text)
            else:
                item.setForeground(Qt.gray)
                text = os.path.basename(self.images_data[i]["path"]) + " (不在当前页)"
                item.setText(text)

    def on_preview_clicked(self, pos):
        if not self.layout_info or not self.preview_pages:
            return
        
        # Use the current page info
        page_info = self.layout_info[self.current_page]
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
        if not self.images_data:
            return

        export_dpi = int(self.combo_export_dpi.currentText())

        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF", "", "PDF Files (*.pdf)"
        )
        if save_path:
            if not save_path.lower().endswith(".pdf"):
                save_path += ".pdf"
            
            try:
                # Re-generate frames and layout at the chosen resolution
                high_res_frames = []
                for data in self.images_data:
                    frame = processor.create_film_frame(
                        data["path"], 
                        crop_mode=data["crop"],
                        color_mode=data["color"],
                        film_type=data["type"],
                        rotation=data["rotation"],
                        draw_holes=False,
                        dpi=export_dpi
                    )
                    high_res_frames.append(frame)
                
                paper_size = self.combo_paper_size.currentText()
                orientation_idx = self.combo_orientation.currentIndex()
                orientation = ["Auto", "Portrait", "Landscape"][orientation_idx]
                margin = self.spin_margin.value()
                gap = self.spin_gap.value()
                high_res_pages, _ = processor.layout_on_paper(
                    high_res_frames, 
                    paper_size=paper_size, 
                    orientation=orientation,
                    margin_mm=margin, 
                    gap_mm=gap, 
                    dpi=export_dpi
                )
                
                if not high_res_pages:
                    return

                pages_to_save = [p.convert("RGB") for p in high_res_pages]
                pages_to_save[0].save(
                    save_path, 
                    save_all=True, 
                    append_images=pages_to_save[1:],
                    resolution=export_dpi
                )
                QMessageBox.information(self, "完成", f"PDF 已成功导出 (分辨率: {export_dpi} DPI)。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出 PDF 失败: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
